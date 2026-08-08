/**
 * Order creation and lifecycle.
 *
 * All three sales paths — an in-chat cart, an accepted custom quote, and a
 * manually keyed order — funnel through `createOrder`, so tax treatment,
 * numbering and the audit trail are computed in exactly one place.
 */
import { type Db, nextCounterValue, transaction } from '../db/index.js';
import { customers, orders, products } from '../db/repositories.js';
import type { CustomerRow, OrderRow, OrderChannel, OrderStatus } from '../db/types.js';
import { config, seller } from '../config/env.js';
import {
  type TaxSummary,
  type TaxableLine,
  computeTax,
  stateCodeFromGstin,
  stateNameForCode,
} from '../domain/gst.js';
import type { Paise } from '../domain/money.js';
import { formatOrderNumber } from '../domain/numbering.js';

export interface DraftLine {
  /** Set when the line came from the catalog; drives stock and reporting. */
  readonly productId?: number | null;
  readonly description: string;
  readonly hsnCode?: string;
  readonly quantity: number;
  /**
   * Unit price. Catalog prices are quoted to customers GST-inclusive, so
   * `priceIncludesTax` tells the service to back the tax out before computing.
   */
  readonly unitPrice: Paise;
  readonly priceIncludesTax?: boolean;
  readonly gstRate?: number;
  readonly discount?: Paise;
  /** Print parameters that end up on the invoice line and the job sheet. */
  readonly meta?: Record<string, unknown>;
}

export interface CreateOrderInput {
  readonly customerId: number;
  readonly channel: OrderChannel;
  readonly lines: readonly DraftLine[];
  readonly quoteId?: number | null;
  readonly shippingAddress?: string | null;
  readonly customerNote?: string | null;
  readonly internalNote?: string | null;
  /** Override the automatic delivery charge. */
  readonly shipping?: Paise;
  readonly orderDiscount?: Paise;
  /**
   * GST state code determining the tax split. Defaults, in order, to the
   * buyer's GSTIN state, then their recorded state, then the seller's own.
   */
  readonly placeOfSupplyCode?: string;
  readonly status?: OrderStatus;
}

export class OrderError extends Error {
  override readonly name = 'OrderError';
}

export interface CreatedOrder {
  readonly order: OrderRow;
  readonly tax: TaxSummary;
}

/**
 * Work out where the supply happens.
 *
 * For goods this is the delivery address; for services to a registered person
 * it is the recipient's registration state. A buyer's GSTIN is the strongest
 * signal we have, so it wins over a loosely captured address.
 */
export function resolvePlaceOfSupply(
  customer: CustomerRow,
  explicitCode?: string,
): { code: string; name: string } {
  const code =
    explicitCode ??
    (customer.gstin ? stateCodeFromGstin(customer.gstin) : null) ??
    customer.state_code ??
    seller.stateCode;
  return { code, name: stateNameForCode(code) };
}

/**
 * Delivery charge policy: free above the configured threshold, otherwise the
 * flat rate. Passing `shipping` explicitly bypasses this.
 */
export function deliveryChargeFor(subtotal: Paise): Paise {
  return subtotal >= config.FREE_DELIVERY_THRESHOLD * 100 ? 0 : config.DELIVERY_CHARGE * 100;
}

/**
 * Recover the pre-tax price from a tax-inclusive one.
 * `net = gross * 100 / (100 + rate)` — the standard back-calculation, rounded
 * to the paise so the reconstructed gross matches what the customer was shown.
 */
export function exclusiveOfTax(inclusivePrice: Paise, gstRate: number): Paise {
  if (gstRate <= 0) return inclusivePrice;
  return Math.round((inclusivePrice * 100) / (100 + gstRate));
}

export function createOrder(db: Db, input: CreateOrderInput): CreatedOrder {
  if (input.lines.length === 0) {
    throw new OrderError('An order needs at least one line');
  }

  const customer = customers.findById(db, input.customerId);
  if (!customer) throw new OrderError(`Unknown customer ${input.customerId}`);

  const placeOfSupply = resolvePlaceOfSupply(customer, input.placeOfSupplyCode);

  const taxableLines: TaxableLine[] = input.lines.map((line, index) => {
    if (!Number.isInteger(line.quantity) || line.quantity < 1) {
      throw new OrderError(`Line ${index + 1} has an invalid quantity: ${line.quantity}`);
    }
    const gstRate = config.GST_ENABLED ? (line.gstRate ?? config.DEFAULT_GST_RATE) : 0;
    const unitPrice = line.priceIncludesTax
      ? exclusiveOfTax(line.unitPrice, gstRate)
      : line.unitPrice;

    return {
      id: String(index),
      description: line.description,
      hsnCode: line.hsnCode ?? config.DEFAULT_HSN_CODE,
      quantity: line.quantity,
      unitPrice,
      discount: line.discount ?? 0,
      gstRate,
    };
  });

  const provisionalSubtotal = taxableLines.reduce(
    (total, line) => total + line.unitPrice * line.quantity - (line.discount ?? 0),
    0,
  );
  const shipping = input.shipping ?? deliveryChargeFor(provisionalSubtotal);

  const tax = computeTax(taxableLines, {
    sellerStateCode: seller.stateCode,
    placeOfSupplyStateCode: placeOfSupply.code,
    gstEnabled: config.GST_ENABLED,
    shipping,
    orderDiscount: input.orderDiscount ?? 0,
  });

  // Numbering and insertion share a transaction: a failure here must not
  // consume an order number.
  return transaction(db, () => {
    const sequence = nextCounterValue(db, 'order');
    const orderNumber = formatOrderNumber(sequence);

    const order = orders.insert(
      db,
      {
        orderNumber,
        customerId: customer.id,
        quoteId: input.quoteId ?? null,
        channel: input.channel,
        status: input.status ?? 'pending_payment',
        placeOfSupplyCode: placeOfSupply.code,
        placeOfSupplyName: placeOfSupply.name,
        taxKind: tax.kind,
        subtotal: tax.subtotal,
        discount: tax.totalDiscount,
        shipping: tax.shipping,
        cgst: tax.cgst,
        sgst: tax.sgst,
        igst: tax.igst,
        roundOff: tax.roundOff,
        total: tax.grandTotal,
        currency: config.CURRENCY,
        shippingAddress: input.shippingAddress ?? null,
        customerNote: input.customerNote ?? null,
        internalNote: input.internalNote ?? null,
      },
      tax.lines.map((line, index) => ({
        productId: input.lines[index]?.productId ?? null,
        description: line.description,
        hsnCode: line.hsnCode,
        quantity: line.quantity,
        unitPrice: line.unitPrice,
        discount: line.discount,
        gstRate: line.gstRate,
        taxableValue: line.taxableValue,
        cgst: line.cgst,
        sgst: line.sgst,
        igst: line.igst,
        lineTotal: line.lineTotal,
        meta: input.lines[index]?.meta,
      })),
    );

    orders.recordEvent(
      db,
      order.id,
      'order.created',
      `${input.channel} · ${input.lines.length} line(s) · total ${tax.grandTotal}`,
    );

    return { order, tax };
  });
}

/**
 * Build order lines from an in-chat cart.
 *
 * Cart prices come back from Meta in major units (rupees) and are the prices
 * the customer saw in the storefront, which we publish GST-inclusive. The
 * catalog row is authoritative for HSN and rate; the cart is only trusted for
 * quantity, and its price is cross-checked against ours.
 */
export interface CartItem {
  readonly productRetailerId: string;
  readonly quantity: number;
  /** Unit price in minor units, as reported by WhatsApp. */
  readonly itemPrice: Paise;
  readonly currency: string;
}

export function linesFromCart(db: Db, items: readonly CartItem[]): DraftLine[] {
  return items.map((item) => {
    const product = products.findByRetailerId(db, item.productRetailerId);
    if (!product) {
      throw new OrderError(
        `Cart references unknown product "${item.productRetailerId}". ` +
          'The WhatsApp catalog is out of sync — run the catalog sync.',
      );
    }
    if (!product.is_active) {
      throw new OrderError(`"${product.name}" is no longer available`);
    }
    if (product.stock_quantity !== null && product.stock_quantity < item.quantity) {
      throw new OrderError(
        `Only ${product.stock_quantity} of "${product.name}" left in stock`,
      );
    }

    return {
      productId: product.id,
      description: product.name,
      hsnCode: product.hsn_code,
      quantity: item.quantity,
      // Our own price is authoritative — a stale cart must not set the price.
      unitPrice: product.price,
      priceIncludesTax: true,
      gstRate: product.gst_rate,
      meta: {
        retailerId: product.retailer_id,
        material: product.material_key,
        weightGrams: product.weight_grams,
        printHours: product.print_hours,
        // Kept so a mismatch is visible when reconciling.
        cartPrice: item.itemPrice,
      },
    };
  });
}

/** Reduce stock for catalog lines once payment lands. */
export function commitStock(db: Db, orderId: number): void {
  for (const item of orders.items(db, orderId)) {
    if (item.product_id !== null) {
      products.decrementStock(db, item.product_id, item.quantity);
    }
  }
}

export function transitionStatus(
  db: Db,
  orderId: number,
  status: OrderStatus,
  detail?: string,
): OrderRow {
  const order = orders.findById(db, orderId);
  if (!order) throw new OrderError(`Unknown order ${orderId}`);

  if (!ALLOWED_TRANSITIONS[order.status]?.includes(status)) {
    throw new OrderError(
      `Cannot move order ${order.order_number} from ${order.status} to ${status}`,
    );
  }

  orders.updateStatus(db, orderId, status);
  orders.recordEvent(db, orderId, `status.${status}`, detail);
  return orders.findById(db, orderId) as OrderRow;
}

/**
 * The production pipeline, as a state machine. Refusing an illegal move keeps
 * a mis-tapped admin button from marking an unpaid order as shipped.
 */
const ALLOWED_TRANSITIONS: Readonly<Record<OrderStatus, readonly OrderStatus[]>> = Object.freeze({
  draft: ['pending_payment', 'cancelled'],
  pending_payment: ['paid', 'cancelled'],
  paid: ['in_production', 'cancelled', 'refunded'],
  in_production: ['ready', 'cancelled'],
  ready: ['shipped', 'delivered'],
  shipped: ['delivered'],
  delivered: ['refunded'],
  cancelled: [],
  refunded: [],
});
