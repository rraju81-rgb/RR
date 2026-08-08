/**
 * WhatsApp Cloud API client (Meta Graph API).
 *
 * Covers the three things this business needs: showing the catalog in chat,
 * carrying on a conversation with interactive replies, and delivering the
 * invoice PDF as a document message.
 *
 * The transport is injectable so the flow logic can be tested without a network
 * or a live business account.
 */
import { config } from '../config/env.js';

export interface WhatsAppSendResult {
  readonly messageId: string | null;
  readonly raw: unknown;
}

export class WhatsAppApiError extends Error {
  override readonly name = 'WhatsAppApiError';
  constructor(
    message: string,
    readonly status: number,
    readonly body: unknown,
    /** Meta error codes that will never succeed on retry. */
    readonly permanent: boolean,
  ) {
    super(message);
  }
}

/**
 * Meta error codes worth distinguishing.
 *   131_047 — outside the 24h customer service window; needs a template
 *   131_026 — undeliverable (not a WhatsApp user, or blocked)
 *   131_051 — unsupported message type
 *   132_xxx — template problems
 *   100     — malformed request
 * Retrying any of these unchanged just burns quota.
 */
const PERMANENT_ERROR_CODES = new Set([100, 131_026, 131_047, 131_051, 132_000, 132_001, 132_005]);

export interface HttpTransport {
  (url: string, init: RequestInit): Promise<Response>;
}

export interface WhatsAppClientOptions {
  accessToken?: string;
  phoneNumberId?: string;
  businessAccountId?: string;
  catalogId?: string;
  apiVersion?: string;
  transport?: HttpTransport;
}

export class WhatsAppClient {
  private readonly accessToken: string;
  private readonly phoneNumberId: string;
  private readonly businessAccountId: string;
  private readonly catalogId: string;
  private readonly apiVersion: string;
  private readonly transport: HttpTransport;

  constructor(options: WhatsAppClientOptions = {}) {
    this.accessToken = options.accessToken ?? config.WHATSAPP_ACCESS_TOKEN;
    this.phoneNumberId = options.phoneNumberId ?? config.WHATSAPP_PHONE_NUMBER_ID;
    this.businessAccountId =
      options.businessAccountId ?? config.WHATSAPP_BUSINESS_ACCOUNT_ID;
    this.catalogId = options.catalogId ?? config.WHATSAPP_CATALOG_ID;
    this.apiVersion = options.apiVersion ?? config.WHATSAPP_API_VERSION;
    this.transport = options.transport ?? ((url, init) => fetch(url, init));
  }

  get isConfigured(): boolean {
    return Boolean(this.accessToken && this.phoneNumberId);
  }

  private url(path: string): string {
    return `https://graph.facebook.com/${this.apiVersion}/${path}`;
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const response = await this.transport(this.url(path), {
      ...init,
      headers: {
        Authorization: `Bearer ${this.accessToken}`,
        ...(init.headers ?? {}),
      },
    });

    const text = await response.text();
    const body: unknown = text ? safeJsonParse(text) : null;

    if (!response.ok) {
      const code = extractErrorCode(body);
      const detail = extractErrorMessage(body) ?? text;
      throw new WhatsAppApiError(
        `WhatsApp API ${response.status}: ${detail}`,
        response.status,
        body,
        // 4xx other than 429 will not fix itself; so will specific Meta codes.
        (response.status >= 400 && response.status < 500 && response.status !== 429) ||
          (code !== null && PERMANENT_ERROR_CODES.has(code)),
      );
    }

    return body as T;
  }

  /** POST to /{phone-number-id}/messages with an already-built message body. */
  private async sendMessage(payload: Record<string, unknown>): Promise<WhatsAppSendResult> {
    const body = {
      messaging_product: 'whatsapp',
      recipient_type: 'individual',
      ...payload,
    };
    const raw = await this.request<{ messages?: { id: string }[] }>(
      `${this.phoneNumberId}/messages`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
    );
    return { messageId: raw?.messages?.[0]?.id ?? null, raw };
  }

  // ── Plain messages ────────────────────────────────────────────────────────

  async sendText(to: string, text: string, previewUrl = false): Promise<WhatsAppSendResult> {
    return this.sendMessage({
      to,
      type: 'text',
      text: { body: truncate(text, 4096), preview_url: previewUrl },
    });
  }

  async sendImage(to: string, link: string, caption?: string): Promise<WhatsAppSendResult> {
    return this.sendMessage({
      to,
      type: 'image',
      image: { link, ...(caption ? { caption: truncate(caption, 1024) } : {}) },
    });
  }

  /**
   * Send a document by media id (uploaded first) or by public link.
   * Invoices go by media id: the PDF never has to be publicly reachable.
   */
  async sendDocument(
    to: string,
    document: { mediaId?: string; link?: string; filename: string; caption?: string },
  ): Promise<WhatsAppSendResult> {
    if (!document.mediaId && !document.link) {
      throw new Error('sendDocument requires either mediaId or link');
    }
    return this.sendMessage({
      to,
      type: 'document',
      document: {
        ...(document.mediaId ? { id: document.mediaId } : { link: document.link }),
        filename: document.filename,
        ...(document.caption ? { caption: truncate(document.caption, 1024) } : {}),
      },
    });
  }

  // ── Interactive messages ──────────────────────────────────────────────────

  /**
   * Up to three reply buttons. Button ids come back on the webhook as
   * `interactive.button_reply.id`, which is how the flow router advances.
   */
  async sendButtons(
    to: string,
    options: {
      body: string;
      buttons: readonly { id: string; title: string }[];
      header?: string;
      footer?: string;
    },
  ): Promise<WhatsAppSendResult> {
    if (options.buttons.length === 0 || options.buttons.length > 3) {
      throw new Error('WhatsApp allows between 1 and 3 reply buttons');
    }
    return this.sendMessage({
      to,
      type: 'interactive',
      interactive: {
        type: 'button',
        ...(options.header ? { header: { type: 'text', text: truncate(options.header, 60) } } : {}),
        body: { text: truncate(options.body, 1024) },
        ...(options.footer ? { footer: { text: truncate(options.footer, 60) } } : {}),
        action: {
          buttons: options.buttons.map((button) => ({
            type: 'reply',
            reply: { id: button.id, title: truncate(button.title, 20) },
          })),
        },
      },
    });
  }

  /** A tap-to-open list — up to 10 rows across all sections. */
  async sendList(
    to: string,
    options: {
      body: string;
      buttonText: string;
      sections: readonly {
        title: string;
        rows: readonly { id: string; title: string; description?: string }[];
      }[];
      header?: string;
      footer?: string;
    },
  ): Promise<WhatsAppSendResult> {
    const rowCount = options.sections.reduce((total, s) => total + s.rows.length, 0);
    if (rowCount > 10) {
      throw new Error(`A list message allows at most 10 rows, got ${rowCount}`);
    }
    return this.sendMessage({
      to,
      type: 'interactive',
      interactive: {
        type: 'list',
        ...(options.header ? { header: { type: 'text', text: truncate(options.header, 60) } } : {}),
        body: { text: truncate(options.body, 1024) },
        ...(options.footer ? { footer: { text: truncate(options.footer, 60) } } : {}),
        action: {
          button: truncate(options.buttonText, 20),
          sections: options.sections.map((section) => ({
            title: truncate(section.title, 24),
            rows: section.rows.map((row) => ({
              id: row.id,
              title: truncate(row.title, 24),
              ...(row.description ? { description: truncate(row.description, 72) } : {}),
            })),
          })),
        },
      },
    });
  }

  /**
   * Open the full storefront in chat. The customer browses the linked catalog,
   * adds to cart and sends the cart back as an `order` webhook.
   */
  async sendCatalog(
    to: string,
    options: { body: string; footer?: string; thumbnailProductRetailerId?: string },
  ): Promise<WhatsAppSendResult> {
    return this.sendMessage({
      to,
      type: 'interactive',
      interactive: {
        type: 'catalog_message',
        body: { text: truncate(options.body, 1024) },
        ...(options.footer ? { footer: { text: truncate(options.footer, 60) } } : {}),
        action: {
          name: 'catalog_message',
          ...(options.thumbnailProductRetailerId
            ? {
                parameters: {
                  thumbnail_product_retailer_id: options.thumbnailProductRetailerId,
                },
              }
            : {}),
        },
      },
    });
  }

  /** A single product card, for "here is the one you asked about". */
  async sendProduct(
    to: string,
    options: { body?: string; footer?: string; productRetailerId: string; catalogId?: string },
  ): Promise<WhatsAppSendResult> {
    return this.sendMessage({
      to,
      type: 'interactive',
      interactive: {
        type: 'product',
        ...(options.body ? { body: { text: truncate(options.body, 1024) } } : {}),
        ...(options.footer ? { footer: { text: truncate(options.footer, 60) } } : {}),
        action: {
          catalog_id: options.catalogId ?? this.catalogId,
          product_retailer_id: options.productRetailerId,
        },
      },
    });
  }

  /**
   * A curated multi-product message — up to 30 products across 10 sections.
   * This is the workhorse for "show me nameplates": a filtered storefront that
   * still feeds the same cart.
   */
  async sendProductList(
    to: string,
    options: {
      headerText: string;
      body: string;
      footer?: string;
      catalogId?: string;
      sections: readonly { title: string; productRetailerIds: readonly string[] }[];
    },
  ): Promise<WhatsAppSendResult> {
    const total = options.sections.reduce((sum, s) => sum + s.productRetailerIds.length, 0);
    if (total === 0) throw new Error('A product list needs at least one product');
    if (total > 30) throw new Error(`A product list allows at most 30 products, got ${total}`);
    if (options.sections.length > 10) {
      throw new Error(`A product list allows at most 10 sections, got ${options.sections.length}`);
    }

    return this.sendMessage({
      to,
      type: 'interactive',
      interactive: {
        type: 'product_list',
        header: { type: 'text', text: truncate(options.headerText, 60) },
        body: { text: truncate(options.body, 1024) },
        ...(options.footer ? { footer: { text: truncate(options.footer, 60) } } : {}),
        action: {
          catalog_id: options.catalogId ?? this.catalogId,
          sections: options.sections.map((section) => ({
            title: truncate(section.title, 24),
            product_items: section.productRetailerIds.map((id) => ({
              product_retailer_id: id,
            })),
          })),
        },
      },
    });
  }

  /**
   * A pre-approved template. Required to open a conversation, or to reply after
   * the 24-hour customer service window has closed.
   */
  async sendTemplate(
    to: string,
    options: {
      name: string;
      languageCode?: string;
      components?: readonly unknown[];
    },
  ): Promise<WhatsAppSendResult> {
    return this.sendMessage({
      to,
      type: 'template',
      template: {
        name: options.name,
        language: { code: options.languageCode ?? 'en' },
        ...(options.components ? { components: options.components } : {}),
      },
    });
  }

  /** Blue ticks on the customer's message. Cheap courtesy, no quota cost. */
  async markRead(messageId: string): Promise<void> {
    await this.request(`${this.phoneNumberId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messaging_product: 'whatsapp',
        status: 'read',
        message_id: messageId,
      }),
    });
  }

  // ── Media ─────────────────────────────────────────────────────────────────

  /**
   * Upload a file and get a media id back. Ids are valid for 30 days, so a
   * resend of the same invoice reuses the id rather than re-uploading.
   */
  async uploadMedia(
    file: Uint8Array | Buffer,
    filename: string,
    mimeType: string,
  ): Promise<string> {
    const form = new FormData();
    form.append('messaging_product', 'whatsapp');
    form.append('type', mimeType);
    // Copy into a fresh ArrayBuffer: a Buffer is often a view onto a larger
    // pooled allocation, and passing that raw would upload the whole pool.
    const bytes = new Uint8Array(file.byteLength);
    bytes.set(file);
    form.append('file', new Blob([bytes], { type: mimeType }), filename);

    const result = await this.request<{ id: string }>(`${this.phoneNumberId}/media`, {
      method: 'POST',
      body: form,
    });
    if (!result?.id) throw new Error('Media upload returned no id');
    return result.id;
  }

  /** Resolve a media id to a short-lived download URL. */
  async getMediaUrl(mediaId: string): Promise<{ url: string; mimeType: string; sha256: string }> {
    const result = await this.request<{ url: string; mime_type: string; sha256: string }>(
      mediaId,
      { method: 'GET' },
    );
    return { url: result.url, mimeType: result.mime_type, sha256: result.sha256 };
  }

  /**
   * Download media the customer sent us (their STL, a reference photo).
   * The URL from `getMediaUrl` still requires the bearer token.
   */
  async downloadMedia(url: string): Promise<Buffer> {
    const response = await this.transport(url, {
      method: 'GET',
      headers: { Authorization: `Bearer ${this.accessToken}` },
    });
    if (!response.ok) {
      throw new WhatsAppApiError(
        `Media download failed with ${response.status}`,
        response.status,
        await response.text(),
        response.status >= 400 && response.status < 500,
      );
    }
    return Buffer.from(await response.arrayBuffer());
  }

  // ── Catalog management ────────────────────────────────────────────────────

  /**
   * Push products into the Commerce Manager catalog.
   *
   * The batch endpoint takes up to 5 000 requests per call; each item is an
   * UPDATE, which upserts on `retailer_id`. Prices go up as integer minor units
   * with the currency stated separately.
   */
  async upsertCatalogItems(
    items: readonly CatalogItem[],
    catalogId = this.catalogId,
  ): Promise<{ handles: string[] }> {
    if (!catalogId) throw new Error('No catalog id configured');
    if (items.length === 0) return { handles: [] };

    const requests = items.map((item) => ({
      method: 'UPDATE',
      retailer_id: item.retailerId,
      data: {
        name: item.name,
        description: item.description,
        // Graph expects the price as minor units in a string with the currency.
        price: item.priceMinorUnits,
        currency: item.currency,
        availability: item.availability,
        condition: 'new',
        image_url: item.imageUrl,
        url: item.url,
        brand: item.brand,
        ...(item.category ? { category: item.category } : {}),
      },
    }));

    const result = await this.request<{ handles: string[] }>(`${catalogId}/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_type: 'PRODUCT_ITEM', requests }),
    });
    return { handles: result?.handles ?? [] };
  }

  async deleteCatalogItems(
    retailerIds: readonly string[],
    catalogId = this.catalogId,
  ): Promise<void> {
    if (retailerIds.length === 0) return;
    await this.request(`${catalogId}/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        item_type: 'PRODUCT_ITEM',
        requests: retailerIds.map((retailerId) => ({ method: 'DELETE', retailer_id: retailerId })),
      }),
    });
  }
}

export interface CatalogItem {
  readonly retailerId: string;
  readonly name: string;
  readonly description: string;
  /** Price in minor units (paise) — Graph wants an integer, not rupees. */
  readonly priceMinorUnits: number;
  readonly currency: string;
  readonly availability: string;
  readonly imageUrl: string;
  readonly url: string;
  readonly brand: string;
  readonly category?: string;
}

function truncate(value: string, max: number): string {
  return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function extractErrorCode(body: unknown): number | null {
  if (typeof body !== 'object' || body === null) return null;
  const error = (body as { error?: { code?: unknown } }).error;
  return typeof error?.code === 'number' ? error.code : null;
}

function extractErrorMessage(body: unknown): string | null {
  if (typeof body !== 'object' || body === null) return null;
  const error = (body as { error?: { message?: unknown } }).error;
  return typeof error?.message === 'string' ? error.message : null;
}

let shared: WhatsAppClient | null = null;

export function getWhatsAppClient(): WhatsAppClient {
  shared ??= new WhatsAppClient();
  return shared;
}

/** Test seam — replaces the process-wide client. */
export function setWhatsAppClient(client: WhatsAppClient | null): void {
  shared = client;
}
