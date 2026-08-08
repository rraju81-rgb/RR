/**
 * Catalog synchronisation.
 *
 * The products table is the source of truth; Meta's Commerce Manager catalog is
 * a projection of it. Sync pushes every active product up and removes ones that
 * have been deactivated, so the in-chat storefront can never offer something we
 * no longer sell.
 */
import type { Db } from '../db/index.js';
import { products } from '../db/repositories.js';
import type { ProductRow } from '../db/types.js';
import { config, seller } from '../config/env.js';
import { type CatalogItem, type WhatsAppClient, getWhatsAppClient } from '../whatsapp/client.js';
import { logger } from '../lib/logger.js';

export interface SyncResult {
  readonly pushed: number;
  readonly removed: number;
  readonly retailerIds: readonly string[];
}

export function toCatalogItem(product: ProductRow): CatalogItem {
  const description = [
    product.description,
    product.material_key ? `Material: ${product.material_key.toUpperCase()}` : '',
    product.weight_grams ? `Approx. weight: ${product.weight_grams} g` : '',
  ]
    .filter(Boolean)
    .join('\n')
    .slice(0, 9999);

  return {
    retailerId: product.retailer_id,
    name: product.name.slice(0, 200),
    description: description || product.name,
    // Catalog prices are the GST-inclusive shelf price, in paise.
    priceMinorUnits: product.price,
    currency: product.currency,
    availability: product.availability,
    imageUrl: product.image_url ?? `${config.PUBLIC_BASE_URL}/static/placeholder.png`,
    url: `${config.PUBLIC_BASE_URL}/p/${encodeURIComponent(product.retailer_id)}`,
    brand: seller.tradeName,
    category: product.category,
  };
}

/**
 * Push the catalog to Meta.
 *
 * Deactivated products are deleted rather than marked out of stock: a product
 * that is gone should not linger in the storefront at all.
 */
export async function syncCatalog(
  db: Db,
  options: { client?: WhatsAppClient; dryRun?: boolean } = {},
): Promise<SyncResult> {
  const client = options.client ?? getWhatsAppClient();
  const all = products.listAll(db);
  const active = all.filter((product) => product.is_active === 1);
  const inactive = all.filter((product) => product.is_active !== 1);

  if (options.dryRun) {
    return {
      pushed: active.length,
      removed: inactive.length,
      retailerIds: active.map((product) => product.retailer_id),
    };
  }

  const items = active.map(toCatalogItem);
  // The batch endpoint accepts far more, but smaller batches make a partial
  // failure easier to attribute to a specific product.
  const BATCH_SIZE = 100;
  for (let index = 0; index < items.length; index += BATCH_SIZE) {
    await client.upsertCatalogItems(items.slice(index, index + BATCH_SIZE));
  }

  if (inactive.length > 0) {
    await client.deleteCatalogItems(inactive.map((product) => product.retailer_id));
  }

  products.markSynced(db, active.map((product) => product.retailer_id));

  logger.info('catalog.synced', { pushed: active.length, removed: inactive.length });
  return {
    pushed: active.length,
    removed: inactive.length,
    retailerIds: active.map((product) => product.retailer_id),
  };
}

/**
 * Group products into the sections of a multi-product message.
 *
 * WhatsApp caps a product list at 30 items over 10 sections, so the newest
 * products in each category win when a category overflows.
 */
export function buildProductSections(
  db: Db,
  category?: string,
): { title: string; productRetailerIds: string[] }[] {
  const rows = products.listActive(db, category);
  const grouped = new Map<string, string[]>();

  for (const product of rows) {
    const bucket = grouped.get(product.category) ?? [];
    bucket.push(product.retailer_id);
    grouped.set(product.category, bucket);
  }

  const sections: { title: string; productRetailerIds: string[] }[] = [];
  let budget = 30;

  for (const [title, ids] of grouped) {
    if (budget <= 0 || sections.length >= 10) break;
    const take = ids.slice(0, Math.min(budget, 30));
    sections.push({ title: humanise(title), productRetailerIds: take });
    budget -= take.length;
  }

  return sections;
}

function humanise(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase());
}
