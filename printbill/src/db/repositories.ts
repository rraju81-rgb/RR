/**
 * Data access. Every query the app runs lives here, so the SQL surface is small
 * enough to audit and the services stay free of statement text.
 */
import type { Db } from './index.js';
import { nowIso } from './index.js';
import type {
  ConversationRow,
  CustomerRow,
  InvoiceRow,
  OrderChannel,
  OrderItemRow,
  OrderRow,
  OrderStatus,
  OutboxRow,
  PaymentLinkRow,
  PaymentRow,
  ProductRow,
  QuoteRow,
} from './types.js';
import type { Paise } from '../domain/money.js';

// ─────────────────────────────────────────────────────────────────────────────
// Customers
// ─────────────────────────────────────────────────────────────────────────────

export interface CustomerInput {
  waPhone: string;
  name?: string | null;
  email?: string | null;
  gstin?: string | null;
  legalName?: string | null;
  addressLine1?: string | null;
  addressLine2?: string | null;
  city?: string | null;
  state?: string | null;
  stateCode?: string | null;
  pincode?: string | null;
  notes?: string | null;
}

export const customers = {
  findByPhone(db: Db, waPhone: string): CustomerRow | undefined {
    return db.prepare('SELECT * FROM customers WHERE wa_phone = ?').get(waPhone) as
      | CustomerRow
      | undefined;
  },

  findById(db: Db, id: number): CustomerRow | undefined {
    return db.prepare('SELECT * FROM customers WHERE id = ?').get(id) as
      | CustomerRow
      | undefined;
  },

  /** Get or create by phone — the entry point for every inbound message. */
  upsertByPhone(db: Db, input: CustomerInput): CustomerRow {
    const existing = this.findByPhone(db, input.waPhone);
    if (!existing) {
      db.prepare(
        `INSERT INTO customers
           (wa_phone, name, email, gstin, legal_name, address_line1, address_line2,
            city, state, state_code, pincode, notes)
         VALUES (@waPhone, @name, @email, @gstin, @legalName, @addressLine1,
                 @addressLine2, @city, @state, @stateCode, @pincode, @notes)`,
      ).run(normaliseCustomer(input));
      return this.findByPhone(db, input.waPhone) as CustomerRow;
    }

    // Only overwrite fields the caller actually supplied; a cart order carrying
    // no GSTIN must not wipe one the customer gave us last week.
    const merged = {
      ...normaliseCustomer(input),
      name: input.name ?? existing.name,
      email: input.email ?? existing.email,
      gstin: input.gstin ?? existing.gstin,
      legalName: input.legalName ?? existing.legal_name,
      addressLine1: input.addressLine1 ?? existing.address_line1,
      addressLine2: input.addressLine2 ?? existing.address_line2,
      city: input.city ?? existing.city,
      state: input.state ?? existing.state,
      stateCode: input.stateCode ?? existing.state_code,
      pincode: input.pincode ?? existing.pincode,
      notes: input.notes ?? existing.notes,
    };

    db.prepare(
      `UPDATE customers SET
         name = @name, email = @email, gstin = @gstin, legal_name = @legalName,
         address_line1 = @addressLine1, address_line2 = @addressLine2,
         city = @city, state = @state, state_code = @stateCode,
         pincode = @pincode, notes = @notes,
         updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
       WHERE wa_phone = @waPhone`,
    ).run(merged);
    return this.findByPhone(db, input.waPhone) as CustomerRow;
  },

  list(db: Db, limit = 100, offset = 0): CustomerRow[] {
    return db
      .prepare('SELECT * FROM customers ORDER BY created_at DESC LIMIT ? OFFSET ?')
      .all(limit, offset) as CustomerRow[];
  },
};

function normaliseCustomer(input: CustomerInput): Record<string, unknown> {
  return {
    waPhone: input.waPhone,
    name: input.name ?? null,
    email: input.email ?? null,
    gstin: input.gstin ? input.gstin.trim().toUpperCase() : null,
    legalName: input.legalName ?? null,
    addressLine1: input.addressLine1 ?? null,
    addressLine2: input.addressLine2 ?? null,
    city: input.city ?? null,
    state: input.state ?? null,
    stateCode: input.stateCode ?? null,
    pincode: input.pincode ?? null,
    notes: input.notes ?? null,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Products
// ─────────────────────────────────────────────────────────────────────────────

export interface ProductInput {
  retailerId: string;
  name: string;
  description?: string;
  category?: string;
  price: Paise;
  currency?: string;
  hsnCode?: string;
  gstRate?: number;
  materialKey?: string | null;
  weightGrams?: number | null;
  printHours?: number | null;
  imageUrl?: string | null;
  availability?: string;
  stockQuantity?: number | null;
  isActive?: boolean;
}

export const products = {
  findByRetailerId(db: Db, retailerId: string): ProductRow | undefined {
    return db.prepare('SELECT * FROM products WHERE retailer_id = ?').get(retailerId) as
      | ProductRow
      | undefined;
  },

  findById(db: Db, id: number): ProductRow | undefined {
    return db.prepare('SELECT * FROM products WHERE id = ?').get(id) as
      | ProductRow
      | undefined;
  },

  listActive(db: Db, category?: string): ProductRow[] {
    if (category) {
      return db
        .prepare(
          'SELECT * FROM products WHERE is_active = 1 AND category = ? ORDER BY name',
        )
        .all(category) as ProductRow[];
    }
    return db
      .prepare('SELECT * FROM products WHERE is_active = 1 ORDER BY category, name')
      .all() as ProductRow[];
  },

  listAll(db: Db): ProductRow[] {
    return db.prepare('SELECT * FROM products ORDER BY category, name').all() as ProductRow[];
  },

  categories(db: Db): string[] {
    const rows = db
      .prepare(
        'SELECT DISTINCT category FROM products WHERE is_active = 1 ORDER BY category',
      )
      .all() as { category: string }[];
    return rows.map((row) => row.category);
  },

  upsert(db: Db, input: ProductInput): ProductRow {
    db.prepare(
      `INSERT INTO products
         (retailer_id, name, description, category, price, currency, hsn_code,
          gst_rate, material_key, weight_grams, print_hours, image_url,
          availability, stock_quantity, is_active)
       VALUES (@retailerId, @name, @description, @category, @price, @currency,
               @hsnCode, @gstRate, @materialKey, @weightGrams, @printHours,
               @imageUrl, @availability, @stockQuantity, @isActive)
       ON CONFLICT (retailer_id) DO UPDATE SET
         name = excluded.name,
         description = excluded.description,
         category = excluded.category,
         price = excluded.price,
         currency = excluded.currency,
         hsn_code = excluded.hsn_code,
         gst_rate = excluded.gst_rate,
         material_key = excluded.material_key,
         weight_grams = excluded.weight_grams,
         print_hours = excluded.print_hours,
         image_url = excluded.image_url,
         availability = excluded.availability,
         stock_quantity = excluded.stock_quantity,
         is_active = excluded.is_active,
         updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')`,
    ).run({
      retailerId: input.retailerId,
      name: input.name,
      description: input.description ?? '',
      category: input.category ?? 'general',
      price: input.price,
      currency: input.currency ?? 'INR',
      hsnCode: input.hsnCode ?? '3926',
      gstRate: input.gstRate ?? 18,
      materialKey: input.materialKey ?? null,
      weightGrams: input.weightGrams ?? null,
      printHours: input.printHours ?? null,
      imageUrl: input.imageUrl ?? null,
      availability: input.availability ?? 'in stock',
      stockQuantity: input.stockQuantity ?? null,
      isActive: input.isActive === false ? 0 : 1,
    });
    return this.findByRetailerId(db, input.retailerId) as ProductRow;
  },

  markSynced(db: Db, retailerIds: readonly string[]): void {
    if (retailerIds.length === 0) return;
    const statement = db.prepare(
      `UPDATE products SET catalog_synced_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
       WHERE retailer_id = ?`,
    );
    for (const id of retailerIds) statement.run(id);
  },

  setActive(db: Db, id: number, isActive: boolean): void {
    db.prepare(
      `UPDATE products SET is_active = ?,
         updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?`,
    ).run(isActive ? 1 : 0, id);
  },

  /** Decrement stock for tracked items. Made-to-order rows (NULL) are skipped. */
  decrementStock(db: Db, productId: number, quantity: number): void {
    db.prepare(
      `UPDATE products
       SET stock_quantity = MAX(0, stock_quantity - ?),
           availability = CASE WHEN stock_quantity - ? <= 0 THEN 'out of stock'
                               ELSE availability END,
           updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
       WHERE id = ? AND stock_quantity IS NOT NULL`,
    ).run(quantity, quantity, productId);
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Orders
// ─────────────────────────────────────────────────────────────────────────────

export interface OrderInsert {
  orderNumber: string;
  customerId: number;
  quoteId?: number | null;
  channel: OrderChannel;
  status: OrderStatus;
  placeOfSupplyCode: string;
  placeOfSupplyName: string;
  taxKind: 'intra_state' | 'inter_state';
  subtotal: Paise;
  discount: Paise;
  shipping: Paise;
  cgst: Paise;
  sgst: Paise;
  igst: Paise;
  roundOff: Paise;
  total: Paise;
  currency?: string;
  shippingAddress?: string | null;
  customerNote?: string | null;
  internalNote?: string | null;
}

export interface OrderItemInsert {
  productId?: number | null;
  description: string;
  hsnCode: string;
  quantity: number;
  unitPrice: Paise;
  discount: Paise;
  gstRate: number;
  taxableValue: Paise;
  cgst: Paise;
  sgst: Paise;
  igst: Paise;
  lineTotal: Paise;
  meta?: unknown;
}

export const orders = {
  insert(db: Db, input: OrderInsert, items: readonly OrderItemInsert[]): OrderRow {
    const result = db
      .prepare(
        `INSERT INTO orders
           (order_number, customer_id, quote_id, channel, status,
            place_of_supply_code, place_of_supply_name, tax_kind,
            subtotal, discount, shipping, cgst, sgst, igst, round_off, total,
            currency, shipping_address, customer_note, internal_note)
         VALUES (@orderNumber, @customerId, @quoteId, @channel, @status,
                 @placeOfSupplyCode, @placeOfSupplyName, @taxKind,
                 @subtotal, @discount, @shipping, @cgst, @sgst, @igst,
                 @roundOff, @total, @currency, @shippingAddress,
                 @customerNote, @internalNote)`,
      )
      .run({
        orderNumber: input.orderNumber,
        customerId: input.customerId,
        quoteId: input.quoteId ?? null,
        channel: input.channel,
        status: input.status,
        placeOfSupplyCode: input.placeOfSupplyCode,
        placeOfSupplyName: input.placeOfSupplyName,
        taxKind: input.taxKind,
        subtotal: input.subtotal,
        discount: input.discount,
        shipping: input.shipping,
        cgst: input.cgst,
        sgst: input.sgst,
        igst: input.igst,
        roundOff: input.roundOff,
        total: input.total,
        currency: input.currency ?? 'INR',
        shippingAddress: input.shippingAddress ?? null,
        customerNote: input.customerNote ?? null,
        internalNote: input.internalNote ?? null,
      });

    const orderId = Number(result.lastInsertRowid);
    const itemStatement = db.prepare(
      `INSERT INTO order_items
         (order_id, product_id, description, hsn_code, quantity, unit_price,
          discount, gst_rate, taxable_value, cgst, sgst, igst, line_total, meta_json)
       VALUES (@orderId, @productId, @description, @hsnCode, @quantity, @unitPrice,
               @discount, @gstRate, @taxableValue, @cgst, @sgst, @igst,
               @lineTotal, @metaJson)`,
    );

    for (const item of items) {
      itemStatement.run({
        orderId,
        productId: item.productId ?? null,
        description: item.description,
        hsnCode: item.hsnCode,
        quantity: item.quantity,
        unitPrice: item.unitPrice,
        discount: item.discount,
        gstRate: item.gstRate,
        taxableValue: item.taxableValue,
        cgst: item.cgst,
        sgst: item.sgst,
        igst: item.igst,
        lineTotal: item.lineTotal,
        metaJson: item.meta === undefined ? null : JSON.stringify(item.meta),
      });
    }

    return this.findById(db, orderId) as OrderRow;
  },

  findById(db: Db, id: number): OrderRow | undefined {
    return db.prepare('SELECT * FROM orders WHERE id = ?').get(id) as OrderRow | undefined;
  },

  findByNumber(db: Db, orderNumber: string): OrderRow | undefined {
    return db.prepare('SELECT * FROM orders WHERE order_number = ?').get(orderNumber) as
      | OrderRow
      | undefined;
  },

  items(db: Db, orderId: number): OrderItemRow[] {
    return db
      .prepare('SELECT * FROM order_items WHERE order_id = ? ORDER BY id')
      .all(orderId) as OrderItemRow[];
  },

  list(
    db: Db,
    filter: { status?: OrderStatus; customerId?: number; limit?: number; offset?: number } = {},
  ): OrderRow[] {
    const clauses: string[] = [];
    const params: unknown[] = [];
    if (filter.status) {
      clauses.push('status = ?');
      params.push(filter.status);
    }
    if (filter.customerId) {
      clauses.push('customer_id = ?');
      params.push(filter.customerId);
    }
    const where = clauses.length > 0 ? `WHERE ${clauses.join(' AND ')}` : '';
    params.push(filter.limit ?? 50, filter.offset ?? 0);
    return db
      .prepare(`SELECT * FROM orders ${where} ORDER BY created_at DESC LIMIT ? OFFSET ?`)
      .all(...params) as OrderRow[];
  },

  updateStatus(db: Db, orderId: number, status: OrderStatus): void {
    db.prepare(
      `UPDATE orders SET status = ?,
         updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?`,
    ).run(status, orderId);
  },

  /**
   * Record a payment against the order and mark it paid once the full amount is
   * in. Returns the updated row so callers can act on the new status.
   */
  applyPayment(db: Db, orderId: number, amount: Paise): OrderRow {
    db.prepare(
      `UPDATE orders SET
         amount_paid = amount_paid + ?,
         status = CASE
           WHEN amount_paid + ? >= total AND status IN ('draft', 'pending_payment')
             THEN 'paid'
           ELSE status
         END,
         paid_at = CASE
           WHEN amount_paid + ? >= total AND paid_at IS NULL
             THEN strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
           ELSE paid_at
         END,
         updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
       WHERE id = ?`,
    ).run(amount, amount, amount, orderId);
    return this.findById(db, orderId) as OrderRow;
  },

  setShippingAddress(db: Db, orderId: number, address: string): void {
    db.prepare(
      `UPDATE orders SET shipping_address = ?,
         updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?`,
    ).run(address, orderId);
  },

  recordEvent(db: Db, orderId: number, event: string, detail?: string): void {
    db.prepare('INSERT INTO order_events (order_id, event, detail) VALUES (?, ?, ?)').run(
      orderId,
      event,
      detail ?? null,
    );
  },

  events(db: Db, orderId: number): { event: string; detail: string | null; created_at: string }[] {
    return db
      .prepare(
        'SELECT event, detail, created_at FROM order_events WHERE order_id = ? ORDER BY id',
      )
      .all(orderId) as { event: string; detail: string | null; created_at: string }[];
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Invoices
// ─────────────────────────────────────────────────────────────────────────────

export const invoices = {
  insert(
    db: Db,
    input: {
      invoiceNumber: string;
      financialYear: string;
      sequenceNumber: number;
      orderId: number;
      documentType: 'tax_invoice' | 'bill_of_supply' | 'credit_note';
      issuedAt: string;
      total: Paise;
      downloadToken: string;
    },
  ): InvoiceRow {
    db.prepare(
      `INSERT INTO invoices
         (invoice_number, financial_year, sequence_number, order_id, document_type,
          issued_at, total, download_token)
       VALUES (@invoiceNumber, @financialYear, @sequenceNumber, @orderId,
               @documentType, @issuedAt, @total, @downloadToken)`,
    ).run(input);
    return this.findByNumber(db, input.invoiceNumber) as InvoiceRow;
  },

  findByNumber(db: Db, invoiceNumber: string): InvoiceRow | undefined {
    return db.prepare('SELECT * FROM invoices WHERE invoice_number = ?').get(invoiceNumber) as
      | InvoiceRow
      | undefined;
  },

  findByOrderId(db: Db, orderId: number): InvoiceRow | undefined {
    return db.prepare('SELECT * FROM invoices WHERE order_id = ?').get(orderId) as
      | InvoiceRow
      | undefined;
  },

  findByToken(db: Db, token: string): InvoiceRow | undefined {
    return db.prepare('SELECT * FROM invoices WHERE download_token = ?').get(token) as
      | InvoiceRow
      | undefined;
  },

  attachPdf(db: Db, invoiceId: number, pdfPath: string, sha256: string): void {
    db.prepare('UPDATE invoices SET pdf_path = ?, pdf_sha256 = ? WHERE id = ?').run(
      pdfPath,
      sha256,
      invoiceId,
    );
  },

  markSent(db: Db, invoiceId: number, mediaId: string | null): void {
    db.prepare('UPDATE invoices SET sent_at = ?, whatsapp_media_id = ? WHERE id = ?').run(
      nowIso(),
      mediaId,
      invoiceId,
    );
  },

  list(db: Db, limit = 50, offset = 0): InvoiceRow[] {
    return db
      .prepare('SELECT * FROM invoices ORDER BY issued_at DESC LIMIT ? OFFSET ?')
      .all(limit, offset) as InvoiceRow[];
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Payments
// ─────────────────────────────────────────────────────────────────────────────

export const payments = {
  /**
   * Insert a payment, ignoring a repeat of one already recorded.
   * Returns null when the payment was already known — the caller's signal that
   * this webhook is a duplicate and the order must not be credited again.
   */
  insertIfNew(
    db: Db,
    input: {
      orderId: number;
      provider: string;
      providerPaymentId: string;
      providerLinkId?: string | null;
      amount: Paise;
      currency?: string;
      status: PaymentRow['status'];
      method?: string | null;
      raw?: unknown;
    },
  ): PaymentRow | null {
    const result = db
      .prepare(
        `INSERT INTO payments
           (order_id, provider, provider_payment_id, provider_link_id, amount,
            currency, status, method, raw_json)
         VALUES (@orderId, @provider, @providerPaymentId, @providerLinkId, @amount,
                 @currency, @status, @method, @rawJson)
         ON CONFLICT (provider, provider_payment_id) DO NOTHING`,
      )
      .run({
        orderId: input.orderId,
        provider: input.provider,
        providerPaymentId: input.providerPaymentId,
        providerLinkId: input.providerLinkId ?? null,
        amount: input.amount,
        currency: input.currency ?? 'INR',
        status: input.status,
        method: input.method ?? null,
        rawJson: input.raw === undefined ? null : JSON.stringify(input.raw),
      });

    if (result.changes === 0) return null;
    return db
      .prepare('SELECT * FROM payments WHERE provider = ? AND provider_payment_id = ?')
      .get(input.provider, input.providerPaymentId) as PaymentRow;
  },

  findByProviderId(db: Db, provider: string, providerPaymentId: string): PaymentRow | undefined {
    return db
      .prepare('SELECT * FROM payments WHERE provider = ? AND provider_payment_id = ?')
      .get(provider, providerPaymentId) as PaymentRow | undefined;
  },

  listForOrder(db: Db, orderId: number): PaymentRow[] {
    return db
      .prepare('SELECT * FROM payments WHERE order_id = ? ORDER BY created_at')
      .all(orderId) as PaymentRow[];
  },
};

export const paymentLinks = {
  insert(
    db: Db,
    input: {
      orderId: number;
      provider: string;
      providerLinkId: string;
      shortUrl: string;
      amount: Paise;
      status?: string;
      expiresAt?: string | null;
      raw?: unknown;
    },
  ): PaymentLinkRow {
    db.prepare(
      `INSERT INTO payment_links
         (order_id, provider, provider_link_id, short_url, amount, status, expires_at, raw_json)
       VALUES (@orderId, @provider, @providerLinkId, @shortUrl, @amount, @status,
               @expiresAt, @rawJson)
       ON CONFLICT (provider, provider_link_id) DO UPDATE SET
         short_url = excluded.short_url,
         status = excluded.status`,
    ).run({
      orderId: input.orderId,
      provider: input.provider,
      providerLinkId: input.providerLinkId,
      shortUrl: input.shortUrl,
      amount: input.amount,
      status: input.status ?? 'created',
      expiresAt: input.expiresAt ?? null,
      rawJson: input.raw === undefined ? null : JSON.stringify(input.raw),
    });
    return db
      .prepare('SELECT * FROM payment_links WHERE provider = ? AND provider_link_id = ?')
      .get(input.provider, input.providerLinkId) as PaymentLinkRow;
  },

  findByProviderId(db: Db, provider: string, providerLinkId: string): PaymentLinkRow | undefined {
    return db
      .prepare('SELECT * FROM payment_links WHERE provider = ? AND provider_link_id = ?')
      .get(provider, providerLinkId) as PaymentLinkRow | undefined;
  },

  latestForOrder(db: Db, orderId: number): PaymentLinkRow | undefined {
    return db
      .prepare('SELECT * FROM payment_links WHERE order_id = ? ORDER BY id DESC LIMIT 1')
      .get(orderId) as PaymentLinkRow | undefined;
  },

  updateStatus(db: Db, provider: string, providerLinkId: string, status: string): void {
    db.prepare(
      'UPDATE payment_links SET status = ? WHERE provider = ? AND provider_link_id = ?',
    ).run(status, provider, providerLinkId);
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Webhook idempotency
// ─────────────────────────────────────────────────────────────────────────────

export const webhookEvents = {
  /**
   * Claim an event for processing.
   *
   * Returns false when the event was already handled successfully — the signal
   * to acknowledge the delivery and do nothing else.
   *
   * An event whose previous attempt *failed* is re-claimable. Without that, a
   * gateway retry after a transient error would be mistaken for a duplicate and
   * the order would never settle.
   */
  claim(db: Db, provider: string, eventId: string, eventType: string, payload: unknown): boolean {
    const result = db
      .prepare(
        `INSERT INTO webhook_events (provider, event_id, event_type, payload_json)
         VALUES (?, ?, ?, ?)
         ON CONFLICT (provider, event_id) DO NOTHING`,
      )
      .run(provider, eventId, eventType, JSON.stringify(payload));

    if (result.changes > 0) return true;

    // Already present: re-claim only if the last attempt recorded an error.
    const retaken = db
      .prepare(
        `UPDATE webhook_events
         SET error = NULL, received_at = ?
         WHERE provider = ? AND event_id = ?
           AND processed_at IS NOT NULL AND error IS NOT NULL`,
      )
      .run(nowIso(), provider, eventId);

    return retaken.changes > 0;
  },

  markProcessed(db: Db, provider: string, eventId: string, error?: string): void {
    db.prepare(
      `UPDATE webhook_events SET processed_at = ?, error = ?
       WHERE provider = ? AND event_id = ?`,
    ).run(nowIso(), error ?? null, provider, eventId);
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Outbox
// ─────────────────────────────────────────────────────────────────────────────

export const outbox = {
  /**
   * Queue an outbound WhatsApp message.
   * With a `dedupeKey`, a second enqueue of the same logical message is a no-op
   * — how "send the invoice once" survives a webhook retry.
   */
  enqueue(
    db: Db,
    input: {
      toPhone: string;
      kind: string;
      payload: unknown;
      dedupeKey?: string | null;
      orderId?: number | null;
    },
  ): OutboxRow | null {
    const result = db
      .prepare(
        // The dedupe index is partial (dedupe_key IS NOT NULL), so the upsert
        // target must restate that predicate or SQLite cannot match the index.
        `INSERT INTO message_outbox (to_phone, kind, payload_json, dedupe_key, order_id)
         VALUES (?, ?, ?, ?, ?)
         ON CONFLICT (dedupe_key) WHERE dedupe_key IS NOT NULL DO NOTHING`,
      )
      .run(
        input.toPhone,
        input.kind,
        JSON.stringify(input.payload),
        input.dedupeKey ?? null,
        input.orderId ?? null,
      );

    if (result.changes === 0) return null;
    return db
      .prepare('SELECT * FROM message_outbox WHERE id = ?')
      .get(Number(result.lastInsertRowid)) as OutboxRow;
  },

  /** Messages whose retry time has arrived, oldest first. */
  due(db: Db, limit = 20, now: string = nowIso()): OutboxRow[] {
    return db
      .prepare(
        `SELECT * FROM message_outbox
         WHERE status = 'pending' AND next_attempt_at <= ?
         ORDER BY next_attempt_at LIMIT ?`,
      )
      .all(now, limit) as OutboxRow[];
  },

  markSent(db: Db, id: number, providerMessageId: string | null): void {
    db.prepare(
      `UPDATE message_outbox
       SET status = 'sent', sent_at = ?, provider_message_id = ?, attempts = attempts + 1
       WHERE id = ?`,
    ).run(nowIso(), providerMessageId, id);
  },

  markFailed(db: Db, id: number, error: string, nextAttemptAt: string | null): void {
    if (nextAttemptAt === null) {
      db.prepare(
        `UPDATE message_outbox
         SET status = 'abandoned', last_error = ?, attempts = attempts + 1
         WHERE id = ?`,
      ).run(error, id);
      return;
    }
    db.prepare(
      `UPDATE message_outbox
       SET last_error = ?, attempts = attempts + 1, next_attempt_at = ?
       WHERE id = ?`,
    ).run(error, nextAttemptAt, id);
  },

  stats(db: Db): { status: string; count: number }[] {
    return db
      .prepare('SELECT status, COUNT(*) as count FROM message_outbox GROUP BY status')
      .all() as { status: string; count: number }[];
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Conversations and inbound messages
// ─────────────────────────────────────────────────────────────────────────────

export const conversations = {
  get(db: Db, waPhone: string): ConversationRow | undefined {
    return db.prepare('SELECT * FROM conversations WHERE wa_phone = ?').get(waPhone) as
      | ConversationRow
      | undefined;
  },

  save(db: Db, waPhone: string, state: string, context: unknown): void {
    db.prepare(
      `INSERT INTO conversations (wa_phone, state, context_json, updated_at)
       VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
       ON CONFLICT (wa_phone) DO UPDATE SET
         state = excluded.state,
         context_json = excluded.context_json,
         updated_at = excluded.updated_at`,
    ).run(waPhone, state, JSON.stringify(context ?? {}));
  },

  touchInbound(db: Db, waPhone: string): void {
    db.prepare(
      `INSERT INTO conversations (wa_phone, last_inbound_at, updated_at)
       VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
               strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
       ON CONFLICT (wa_phone) DO UPDATE SET
         last_inbound_at = excluded.last_inbound_at,
         updated_at = excluded.updated_at`,
    ).run(waPhone);
  },
};

export const inboundMessages = {
  /** False when this message id was already stored — Meta redelivered it. */
  recordIfNew(
    db: Db,
    input: {
      waMessageId: string;
      fromPhone: string;
      messageType: string;
      body?: string | null;
      payload: unknown;
    },
  ): boolean {
    const result = db
      .prepare(
        `INSERT INTO inbound_messages
           (wa_message_id, from_phone, message_type, body, payload_json)
         VALUES (?, ?, ?, ?, ?)
         ON CONFLICT (wa_message_id) DO NOTHING`,
      )
      .run(
        input.waMessageId,
        input.fromPhone,
        input.messageType,
        input.body ?? null,
        JSON.stringify(input.payload),
      );
    return result.changes > 0;
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Quotes
// ─────────────────────────────────────────────────────────────────────────────

export const quotes = {
  insert(
    db: Db,
    input: {
      quoteNumber: string;
      customerId: number;
      request: unknown;
      result: unknown;
      unitPrice: Paise;
      total: Paise;
      status?: QuoteRow['status'];
      mediaId?: string | null;
      mediaPath?: string | null;
      mediaFilename?: string | null;
      expiresAt?: string | null;
    },
  ): QuoteRow {
    const result = db
      .prepare(
        `INSERT INTO quotes
           (quote_number, customer_id, request_json, result_json, unit_price, total,
            status, media_id, media_path, media_filename, expires_at)
         VALUES (@quoteNumber, @customerId, @requestJson, @resultJson, @unitPrice,
                 @total, @status, @mediaId, @mediaPath, @mediaFilename, @expiresAt)`,
      )
      .run({
        quoteNumber: input.quoteNumber,
        customerId: input.customerId,
        requestJson: JSON.stringify(input.request),
        resultJson: JSON.stringify(input.result),
        unitPrice: input.unitPrice,
        total: input.total,
        status: input.status ?? 'draft',
        mediaId: input.mediaId ?? null,
        mediaPath: input.mediaPath ?? null,
        mediaFilename: input.mediaFilename ?? null,
        expiresAt: input.expiresAt ?? null,
      });
    return this.findById(db, Number(result.lastInsertRowid)) as QuoteRow;
  },

  findById(db: Db, id: number): QuoteRow | undefined {
    return db.prepare('SELECT * FROM quotes WHERE id = ?').get(id) as QuoteRow | undefined;
  },

  findByNumber(db: Db, quoteNumber: string): QuoteRow | undefined {
    return db.prepare('SELECT * FROM quotes WHERE quote_number = ?').get(quoteNumber) as
      | QuoteRow
      | undefined;
  },

  updateStatus(db: Db, id: number, status: QuoteRow['status']): void {
    db.prepare(
      `UPDATE quotes SET status = ?,
         updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?`,
    ).run(status, id);
  },

  list(db: Db, limit = 50, offset = 0): QuoteRow[] {
    return db
      .prepare('SELECT * FROM quotes ORDER BY created_at DESC LIMIT ? OFFSET ?')
      .all(limit, offset) as QuoteRow[];
  },
};
