/**
 * Admin API — the operator's control surface.
 *
 * Protected by a single API key rather than user accounts: this is a one- or
 * two-person workshop, and a shared secret over TLS is proportionate. Every
 * route that changes money or state is a POST, so nothing destructive can be
 * triggered by a link.
 */
import type { Express, NextFunction, Request, Response } from 'express';
import crypto from 'node:crypto';
import { z } from 'zod';
import type { Db } from '../../db/index.js';
import {
  customers,
  invoices as invoiceRepo,
  orders,
  outbox,
  payments,
  products,
  quotes,
} from '../../db/repositories.js';
import { config } from '../../config/env.js';
import { toPaise } from '../../domain/money.js';
import { MATERIALS, quotePrintJob } from '../../domain/pricing.js';
import { isValidGstin } from '../../domain/gst.js';
import { createOrder, transitionStatus } from '../../services/orders.js';
import { deliverInvoice, requestPayment } from '../../services/checkout.js';
import { issueInvoice, renderInvoice } from '../../services/invoices.js';
import { syncCatalog } from '../../services/catalog.js';
import { dispatchOutbox, enqueueMessage } from '../../services/messaging.js';
import { sendMainMenu } from '../../whatsapp/flows.js';
import { logger } from '../../lib/logger.js';

/** Constant-time API key check, so the key cannot be discovered by timing. */
function requireApiKey(request: Request, response: Response, next: NextFunction): void {
  const provided = request.get('x-api-key') ?? '';
  const expected = config.ADMIN_API_KEY;
  const a = Buffer.from(provided, 'utf8');
  const b = Buffer.from(expected, 'utf8');

  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
    response.status(401).json({ error: 'unauthorized' });
    return;
  }
  next();
}

/** Wrap an async handler so a rejection reaches the error middleware. */
function wrap(
  handler: (request: Request, response: Response) => Promise<void>,
): (request: Request, response: Response, next: NextFunction) => void {
  return (request, response, next) => {
    handler(request, response).catch(next);
  };
}

export function registerAdminRoutes(app: Express, db: Db): void {
  const api = '/api/admin';
  app.use(api, requireApiKey);

  // ── Dashboard ─────────────────────────────────────────────────────────────

  app.get(`${api}/summary`, (_request, response) => {
    const counts = db
      .prepare('SELECT status, COUNT(*) AS count, SUM(total) AS value FROM orders GROUP BY status')
      .all() as { status: string; count: number; value: number }[];

    const revenue = db
      .prepare(
        `SELECT COALESCE(SUM(amount_paid), 0) AS paid,
                COUNT(*) AS orders
         FROM orders WHERE status NOT IN ('cancelled', 'draft')`,
      )
      .get() as { paid: number; orders: number };

    const today = db
      .prepare(
        `SELECT COALESCE(SUM(amount_paid), 0) AS paid, COUNT(*) AS orders
         FROM orders WHERE date(created_at) = date('now')`,
      )
      .get() as { paid: number; orders: number };

    const pendingInvoices = db
      .prepare(
        `SELECT COUNT(*) AS count FROM orders o
         LEFT JOIN invoices i ON i.order_id = o.id
         WHERE o.status = 'paid' AND i.id IS NULL`,
      )
      .get() as { count: number };

    response.json({
      byStatus: counts,
      revenue,
      today,
      pendingInvoices: pendingInvoices.count,
      outbox: outbox.stats(db),
      gateway: config.PAYMENT_PROVIDER,
      gstEnabled: config.GST_ENABLED,
      catalogConnected: Boolean(config.WHATSAPP_CATALOG_ID),
      whatsappConnected: Boolean(config.WHATSAPP_ACCESS_TOKEN && config.WHATSAPP_PHONE_NUMBER_ID),
    });
  });

  // ── Products ──────────────────────────────────────────────────────────────

  const productSchema = z.object({
    retailerId: z.string().min(1).max(100),
    name: z.string().min(1).max(200),
    description: z.string().max(4000).optional(),
    category: z.string().max(60).optional(),
    /** Rupees from the UI; stored as paise. */
    price: z.number().nonnegative(),
    hsnCode: z.string().max(10).optional(),
    gstRate: z.number().min(0).max(28).optional(),
    materialKey: z.string().max(40).nullable().optional(),
    weightGrams: z.number().nonnegative().nullable().optional(),
    printHours: z.number().nonnegative().nullable().optional(),
    imageUrl: z.string().url().nullable().optional(),
    availability: z.enum(['in stock', 'out of stock', 'preorder']).optional(),
    stockQuantity: z.number().int().nonnegative().nullable().optional(),
    isActive: z.boolean().optional(),
  });

  app.get(`${api}/products`, (_request, response) => {
    response.json(products.listAll(db));
  });

  app.post(
    `${api}/products`,
    wrap(async (request, response) => {
      const parsed = productSchema.safeParse(request.body);
      if (!parsed.success) {
        response.status(400).json({ error: 'invalid_product', issues: parsed.error.issues });
        return;
      }
      const input = parsed.data;
      const saved = products.upsert(db, {
        ...input,
        price: toPaise(input.price),
        gstRate: input.gstRate ?? config.DEFAULT_GST_RATE,
        hsnCode: input.hsnCode ?? config.DEFAULT_HSN_CODE,
      });
      response.json(saved);
    }),
  );

  app.post(
    `${api}/products/:id/active`,
    wrap(async (request, response) => {
      const isActive = Boolean((request.body as { isActive?: boolean }).isActive);
      products.setActive(db, Number(request.params.id), isActive);
      response.json({ ok: true });
    }),
  );

  app.post(
    `${api}/catalog/sync`,
    wrap(async (request, response) => {
      const dryRun = Boolean((request.body as { dryRun?: boolean })?.dryRun);
      const result = await syncCatalog(db, { dryRun });
      response.json(result);
    }),
  );

  // ── Customers ─────────────────────────────────────────────────────────────

  app.get(`${api}/customers`, (request, response) => {
    response.json(customers.list(db, Number(request.query.limit ?? 100)));
  });

  app.post(
    `${api}/customers`,
    wrap(async (request, response) => {
      const schema = z.object({
        waPhone: z.string().min(8),
        name: z.string().max(120).optional(),
        email: z.string().email().optional(),
        gstin: z.string().max(15).optional(),
        legalName: z.string().max(200).optional(),
        addressLine1: z.string().max(200).optional(),
        addressLine2: z.string().max(200).optional(),
        city: z.string().max(80).optional(),
        state: z.string().max(80).optional(),
        stateCode: z.string().length(2).optional(),
        pincode: z.string().max(10).optional(),
      });
      const parsed = schema.safeParse(request.body);
      if (!parsed.success) {
        response.status(400).json({ error: 'invalid_customer', issues: parsed.error.issues });
        return;
      }
      if (parsed.data.gstin && !isValidGstin(parsed.data.gstin)) {
        response.status(400).json({ error: 'invalid_gstin' });
        return;
      }
      response.json(customers.upsertByPhone(db, parsed.data));
    }),
  );

  // ── Orders ────────────────────────────────────────────────────────────────

  app.get(`${api}/orders`, (request, response) => {
    const status = request.query.status as string | undefined;
    const rows = orders.list(db, {
      ...(status ? { status: status as never } : {}),
      limit: Number(request.query.limit ?? 50),
    });
    response.json(
      rows.map((order) => ({
        ...order,
        customer: customers.findById(db, order.customer_id),
        invoice: invoiceRepo.findByOrderId(db, order.id),
      })),
    );
  });

  app.get(`${api}/orders/:id`, (request, response) => {
    const order = orders.findById(db, Number(request.params.id));
    if (!order) {
      response.status(404).json({ error: 'not_found' });
      return;
    }
    response.json({
      order,
      items: orders.items(db, order.id),
      customer: customers.findById(db, order.customer_id),
      invoice: invoiceRepo.findByOrderId(db, order.id),
      payments: payments.listForOrder(db, order.id),
      events: orders.events(db, order.id),
    });
  });

  /** Manually key an order — phone orders, walk-ins, repeat jobs. */
  app.post(
    `${api}/orders`,
    wrap(async (request, response) => {
      const schema = z.object({
        waPhone: z.string().min(8),
        name: z.string().max(120).optional(),
        lines: z
          .array(
            z.object({
              description: z.string().min(1).max(300),
              quantity: z.number().int().positive(),
              /** Rupees. */
              unitPrice: z.number().nonnegative(),
              priceIncludesTax: z.boolean().optional(),
              hsnCode: z.string().max(10).optional(),
              gstRate: z.number().min(0).max(28).optional(),
              meta: z.record(z.string(), z.unknown()).optional(),
            }),
          )
          .min(1),
        shipping: z.number().nonnegative().optional(),
        orderDiscount: z.number().nonnegative().optional(),
        placeOfSupplyCode: z.string().length(2).optional(),
        customerNote: z.string().max(1000).optional(),
        internalNote: z.string().max(1000).optional(),
        sendPaymentLink: z.boolean().optional(),
      });

      const parsed = schema.safeParse(request.body);
      if (!parsed.success) {
        response.status(400).json({ error: 'invalid_order', issues: parsed.error.issues });
        return;
      }
      const input = parsed.data;

      const customer = customers.upsertByPhone(db, {
        waPhone: input.waPhone,
        name: input.name ?? null,
      });

      const created = createOrder(db, {
        customerId: customer.id,
        channel: 'manual',
        lines: input.lines.map((line) => ({
          description: line.description,
          quantity: line.quantity,
          unitPrice: toPaise(line.unitPrice),
          priceIncludesTax: line.priceIncludesTax ?? false,
          ...(line.hsnCode ? { hsnCode: line.hsnCode } : {}),
          ...(line.gstRate !== undefined ? { gstRate: line.gstRate } : {}),
          ...(line.meta ? { meta: line.meta } : {}),
        })),
        ...(input.shipping !== undefined ? { shipping: toPaise(input.shipping) } : {}),
        ...(input.orderDiscount !== undefined
          ? { orderDiscount: toPaise(input.orderDiscount) }
          : {}),
        ...(input.placeOfSupplyCode ? { placeOfSupplyCode: input.placeOfSupplyCode } : {}),
        customerNote: input.customerNote ?? null,
        internalNote: input.internalNote ?? null,
      });

      if (input.sendPaymentLink !== false) {
        await requestPayment(db, created.order.id);
      }

      response.json({ order: created.order, tax: created.tax });
    }),
  );

  app.post(
    `${api}/orders/:id/status`,
    wrap(async (request, response) => {
      const status = (request.body as { status?: string }).status;
      const detail = (request.body as { detail?: string }).detail;
      if (!status) {
        response.status(400).json({ error: 'status_required' });
        return;
      }

      const order = transitionStatus(db, Number(request.params.id), status as never, detail);
      const customer = customers.findById(db, order.customer_id);

      // Keep the customer informed at the moments that matter to them.
      const narrative = CUSTOMER_STATUS_MESSAGE[status];
      if (customer && narrative) {
        enqueueMessage(
          db,
          customer.wa_phone,
          { kind: 'text', text: narrative(order.order_number, detail) },
          { dedupeKey: `status:${order.order_number}:${status}`, orderId: order.id },
        );
      }

      response.json(order);
    }),
  );

  app.post(
    `${api}/orders/:id/payment-link`,
    wrap(async (request, response) => {
      const force = Boolean((request.body as { force?: boolean })?.force);
      const link = await requestPayment(db, Number(request.params.id), { force });
      response.json(link);
    }),
  );

  /**
   * Issue an invoice without a gateway payment — for cash, bank transfer or a
   * UPI paid directly to the seller.
   */
  app.post(
    `${api}/orders/:id/mark-paid`,
    wrap(async (request, response) => {
      const body = request.body as { method?: string; reference?: string };
      const orderId = Number(request.params.id);
      const order = orders.findById(db, orderId);
      if (!order) {
        response.status(404).json({ error: 'not_found' });
        return;
      }

      const due = order.total - order.amount_paid;
      if (due <= 0) {
        response.status(400).json({ error: 'already_paid' });
        return;
      }

      payments.insertIfNew(db, {
        orderId,
        provider: 'offline',
        providerPaymentId: body.reference ?? `offline_${Date.now()}`,
        amount: due,
        status: 'captured',
        method: body.method ?? 'cash',
      });

      const updated = orders.applyPayment(db, orderId, due);
      orders.recordEvent(db, orderId, 'payment.offline', body.method ?? 'cash');

      const invoice = issueInvoice(db, orderId);
      await deliverInvoice(db, updated, invoice);

      response.json({ order: updated, invoice });
    }),
  );

  // ── Invoices ──────────────────────────────────────────────────────────────

  app.get(`${api}/invoices`, (request, response) => {
    response.json(invoiceRepo.list(db, Number(request.query.limit ?? 50)));
  });

  app.post(
    `${api}/invoices/:id/resend`,
    wrap(async (request, response) => {
      const invoice = db
        .prepare('SELECT * FROM invoices WHERE id = ?')
        .get(Number(request.params.id)) as never;
      if (!invoice) {
        response.status(404).json({ error: 'not_found' });
        return;
      }
      const order = orders.findById(db, (invoice as { order_id: number }).order_id);
      if (!order) {
        response.status(404).json({ error: 'order_not_found' });
        return;
      }
      await deliverInvoice(db, order, invoice, { force: true });
      response.json({ ok: true });
    }),
  );

  app.post(
    `${api}/invoices/:id/rerender`,
    wrap(async (request, response) => {
      const invoice = db
        .prepare('SELECT * FROM invoices WHERE id = ?')
        .get(Number(request.params.id)) as never;
      if (!invoice) {
        response.status(404).json({ error: 'not_found' });
        return;
      }
      const { filePath } = await renderInvoice(db, invoice, { force: true });
      response.json({ ok: true, filePath });
    }),
  );

  // ── Quotes ────────────────────────────────────────────────────────────────

  app.get(`${api}/quotes`, (request, response) => {
    response.json(
      quotes.list(db, Number(request.query.limit ?? 50)).map((quote) => ({
        ...quote,
        customer: customers.findById(db, quote.customer_id),
      })),
    );
  });

  app.get(`${api}/materials`, (_request, response) => {
    response.json(MATERIALS);
  });

  /**
   * Re-price a job with the real slicer numbers and send the confirmed quote.
   * This is the step that turns the chat's indicative estimate into a firm one.
   */
  app.post(
    `${api}/quotes/price`,
    wrap(async (request, response) => {
      const schema = z.object({
        materialKey: z.string().min(1),
        weightGrams: z.number().positive().optional(),
        volumeCm3: z.number().positive().optional(),
        printHours: z.number().positive(),
        quantity: z.number().int().positive(),
        postProcessing: z.array(z.string()).optional(),
        rush: z.enum(['standard', 'priority', 'same_day']).optional(),
        extraLabourMinutes: z.number().nonnegative().optional(),
        hardwareCost: z.number().nonnegative().optional(),
      });

      const parsed = schema.safeParse(request.body);
      if (!parsed.success) {
        response.status(400).json({ error: 'invalid_quote', issues: parsed.error.issues });
        return;
      }
      const input = parsed.data;

      const quote = quotePrintJob(
        {
          materialKey: input.materialKey,
          ...(input.weightGrams !== undefined ? { weightGrams: input.weightGrams } : {}),
          ...(input.volumeCm3 !== undefined ? { volumeCm3: input.volumeCm3 } : {}),
          printHours: input.printHours,
          quantity: input.quantity,
          ...(input.postProcessing ? { postProcessing: input.postProcessing as never } : {}),
          ...(input.rush ? { rush: input.rush } : {}),
          ...(input.extraLabourMinutes !== undefined
            ? { extraLabourMinutes: input.extraLabourMinutes }
            : {}),
          ...(input.hardwareCost !== undefined
            ? { hardwareCost: toPaise(input.hardwareCost) }
            : {}),
        },
        {
          machineRatePerHour: toPaise(config.PRICING_MACHINE_RATE_PER_HOUR),
          labourRatePerHour: toPaise(config.PRICING_LABOUR_RATE_PER_HOUR),
          setupFee: toPaise(config.PRICING_SETUP_FEE),
          marginMultiplier: config.PRICING_MARGIN_MULTIPLIER,
          wastageFactor: config.PRICING_WASTAGE_FACTOR,
        },
      );

      response.json(quote);
    }),
  );

  // ── Messaging ─────────────────────────────────────────────────────────────

  app.post(
    `${api}/messages/send`,
    wrap(async (request, response) => {
      const schema = z.object({
        waPhone: z.string().min(8),
        text: z.string().min(1).max(4000),
      });
      const parsed = schema.safeParse(request.body);
      if (!parsed.success) {
        response.status(400).json({ error: 'invalid_message', issues: parsed.error.issues });
        return;
      }
      const row = enqueueMessage(db, parsed.data.waPhone, {
        kind: 'text',
        text: parsed.data.text,
      });
      response.json({ queued: Boolean(row), id: row?.id ?? null });
    }),
  );

  app.post(
    `${api}/messages/menu`,
    wrap(async (request, response) => {
      const waPhone = (request.body as { waPhone?: string }).waPhone;
      if (!waPhone) {
        response.status(400).json({ error: 'waPhone_required' });
        return;
      }
      const customer = customers.upsertByPhone(db, { waPhone });
      sendMainMenu(db, customer);
      response.json({ ok: true });
    }),
  );

  app.get(`${api}/outbox`, (request, response) => {
    const status = (request.query.status as string) ?? 'pending';
    response.json(
      db
        .prepare('SELECT * FROM message_outbox WHERE status = ? ORDER BY id DESC LIMIT 100')
        .all(status),
    );
  });

  /** Drain the queue on demand, rather than waiting for the worker tick. */
  app.post(
    `${api}/outbox/flush`,
    wrap(async (_request, response) => {
      const result = await dispatchOutbox(db, { limit: 50 });
      logger.info('outbox.manual_flush', result);
      response.json(result);
    }),
  );

  /** Requeue an abandoned message after the underlying problem is fixed. */
  app.post(
    `${api}/outbox/:id/retry`,
    wrap(async (request, response) => {
      db.prepare(
        `UPDATE message_outbox
         SET status = 'pending', attempts = 0,
             next_attempt_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
         WHERE id = ?`,
      ).run(Number(request.params.id));
      response.json({ ok: true });
    }),
  );
}

/** Customer-facing wording for the status changes worth announcing. */
const CUSTOMER_STATUS_MESSAGE: Readonly<
  Record<string, ((orderNumber: string, detail?: string) => string) | undefined>
> = Object.freeze({
  in_production: (orderNumber) =>
    `🖨️ Your order *${orderNumber}* is on the printer now. We will let you know the moment it is packed.`,
  ready: (orderNumber) =>
    `📦 Order *${orderNumber}* is printed, finished and packed. Dispatching shortly!`,
  shipped: (orderNumber, detail) =>
    `🚚 Order *${orderNumber}* has been dispatched.` +
    (detail ? `\n\nTracking: ${detail}` : ''),
  delivered: (orderNumber) =>
    `🎉 Order *${orderNumber}* has been delivered. We would love to hear how it turned out!`,
  cancelled: (orderNumber, detail) =>
    `Order *${orderNumber}* has been cancelled.` +
    (detail ? `\n\n${detail}` : '') +
    '\n\nAny amount paid will be refunded within 5–7 working days.',
});
