/**
 * Checkout and fulfilment: the path from "customer owes money" to "customer has
 * a PDF invoice in their WhatsApp".
 *
 * `settlePayment` is the critical routine. It is called from a webhook that any
 * gateway may deliver more than once, so every step is idempotent: the payment
 * row is unique per gateway id, the invoice is unique per order, and the
 * WhatsApp send is deduped on the invoice number.
 */
import { type Db, transaction } from '../db/index.js';
import {
  customers,
  invoices as invoiceRepo,
  orders,
  paymentLinks,
  payments,
} from '../db/repositories.js';
import type { InvoiceRow, OrderRow } from '../db/types.js';
import { config, seller } from '../config/env.js';
import { formatINR } from '../domain/money.js';
import type { PaymentEvent, PaymentGateway } from '../payments/gateway.js';
import { getGateway } from '../payments/index.js';
import { logger } from '../lib/logger.js';
import { enqueueMessage } from './messaging.js';
import { commitStock } from './orders.js';
import { issueInvoice, renderInvoice, invoiceDownloadUrl } from './invoices.js';

export class CheckoutError extends Error {
  override readonly name = 'CheckoutError';
}

/**
 * Create a hosted payment link for an order and push it into the chat.
 *
 * A link already created for this order is reused: generating a second link for
 * the same amount invites the customer to pay twice.
 */
export async function requestPayment(
  db: Db,
  orderId: number,
  options: { gateway?: PaymentGateway; force?: boolean } = {},
): Promise<{ shortUrl: string; providerLinkId: string }> {
  const order = orders.findById(db, orderId);
  if (!order) throw new CheckoutError(`Unknown order ${orderId}`);
  if (order.status === 'paid') throw new CheckoutError(`Order ${order.order_number} is already paid`);
  if (order.status === 'cancelled') {
    throw new CheckoutError(`Order ${order.order_number} is cancelled`);
  }

  const customer = customers.findById(db, order.customer_id);
  if (!customer) throw new CheckoutError(`Customer ${order.customer_id} vanished`);

  const existing = paymentLinks.latestForOrder(db, orderId);
  if (existing && !options.force && existing.status === 'created') {
    sendPaymentLinkMessage(db, order, customer.wa_phone, existing.short_url);
    return { shortUrl: existing.short_url, providerLinkId: existing.provider_link_id };
  }

  const gateway = options.gateway ?? getGateway();
  const due = order.total - order.amount_paid;

  const link = await gateway.createPaymentLink({
    orderId: order.id,
    orderNumber: order.order_number,
    amount: due,
    currency: order.currency,
    description: `${seller.tradeName} · Order ${order.order_number}`,
    customer: {
      name: customer.name,
      email: customer.email,
      contact: `+${customer.wa_phone}`,
    },
    callbackUrl: `${config.PUBLIC_BASE_URL}/pay/return?order=${encodeURIComponent(
      order.order_number,
    )}`,
    expiresInMinutes: 60 * 24 * 2,
    notes: { order_number: order.order_number },
  });

  paymentLinks.insert(db, {
    orderId: order.id,
    provider: gateway.name,
    providerLinkId: link.providerLinkId,
    shortUrl: link.shortUrl,
    amount: due,
    status: link.status,
    expiresAt: link.expiresAt,
    raw: link.raw,
  });

  orders.recordEvent(db, order.id, 'payment.link_created', link.shortUrl);
  sendPaymentLinkMessage(db, order, customer.wa_phone, link.shortUrl);

  return { shortUrl: link.shortUrl, providerLinkId: link.providerLinkId };
}

function sendPaymentLinkMessage(
  db: Db,
  order: OrderRow,
  waPhone: string,
  shortUrl: string,
): void {
  const due = order.total - order.amount_paid;
  const lines = [
    `*Order ${order.order_number}*`,
    '',
    `Amount payable: *${formatINR(due)}*`,
    '',
    'Tap below to pay securely with UPI, card, net banking or a wallet:',
    shortUrl,
    '',
    '_Your GST invoice will arrive here automatically the moment payment is confirmed._',
  ];

  enqueueMessage(
    db,
    waPhone,
    { kind: 'text', text: lines.join('\n'), previewUrl: true },
    // One link message per link — a repeat request reuses the same key.
    { dedupeKey: `paylink:${order.order_number}:${shortUrl}`, orderId: order.id },
  );
}

export interface SettlementResult {
  readonly status: 'settled' | 'duplicate' | 'partial' | 'ignored' | 'unmatched';
  readonly order?: OrderRow;
  readonly invoice?: InvoiceRow;
}

/**
 * Apply a verified gateway event.
 *
 * The database work runs in one transaction so a crash between "money recorded"
 * and "invoice issued" cannot leave a paid order without a document. The PDF
 * render and the WhatsApp send happen after the commit — both are retryable,
 * and neither should hold a write lock.
 */
export async function settlePayment(db: Db, event: PaymentEvent): Promise<SettlementResult> {
  if (event.kind === 'ignored') return { status: 'ignored' };

  const order = findOrderForEvent(db, event);
  if (!order) {
    logger.warn('payment.unmatched', {
      eventId: event.eventId,
      orderNumber: event.orderNumber,
      providerLinkId: event.providerLinkId,
    });
    return { status: 'unmatched' };
  }

  if (event.kind === 'payment.failed') {
    orders.recordEvent(db, order.id, 'payment.failed', event.providerPaymentId ?? undefined);
    const customer = customers.findById(db, order.customer_id);
    if (customer) {
      enqueueMessage(
        db,
        customer.wa_phone,
        {
          kind: 'buttons',
          body:
            `We could not confirm your payment for order *${order.order_number}*.\n\n` +
            'No money has been deducted. If your bank shows a debit it will be reversed ' +
            'automatically within 3–5 working days.',
          buttons: [
            { id: `pay:${order.order_number}`, title: 'Try again' },
            { id: 'support', title: 'Talk to us' },
          ],
        },
        { dedupeKey: `payfail:${event.eventId}`, orderId: order.id },
      );
    }
    return { status: 'ignored', order };
  }

  if (event.kind === 'refund.processed') {
    orders.recordEvent(db, order.id, 'payment.refunded', String(event.amount ?? ''));
    return { status: 'ignored', order };
  }

  const amount = event.amount ?? 0;
  if (amount <= 0) return { status: 'ignored', order };

  // ── One transaction: record the money, issue the invoice ──────────────────
  const outcome = transaction(db, () => {
    const payment = payments.insertIfNew(db, {
      orderId: order.id,
      provider: gatewayNameFor(event),
      providerPaymentId: event.providerPaymentId ?? `link:${event.providerLinkId}`,
      providerLinkId: event.providerLinkId,
      amount,
      currency: event.currency ?? 'INR',
      status: 'captured',
      method: event.method,
      raw: event.raw,
    });

    // Already recorded: this is a redelivery. Return the existing invoice so
    // the caller can still (idempotently) resend it.
    if (!payment) {
      return {
        duplicate: true,
        order: orders.findById(db, order.id) as OrderRow,
        invoice: invoiceRepo.findByOrderId(db, order.id),
      };
    }

    const updated = orders.applyPayment(db, order.id, amount);
    orders.recordEvent(
      db,
      order.id,
      'payment.captured',
      `${event.method ?? 'unknown'} · ${amount}`,
    );

    if (event.providerLinkId) {
      paymentLinks.updateStatus(db, gatewayNameFor(event), event.providerLinkId, 'paid');
    }

    // Only invoice once the order is fully settled. A part payment is recorded
    // but does not produce a tax invoice.
    if (updated.amount_paid < updated.total) {
      return { duplicate: false, order: updated, invoice: undefined };
    }

    commitStock(db, order.id);
    const invoice = issueInvoice(db, order.id);
    return { duplicate: false, order: updated, invoice };
  });

  if (outcome.duplicate) {
    logger.info('payment.duplicate_event', { eventId: event.eventId, order: order.order_number });
    if (outcome.invoice) {
      await deliverInvoice(db, outcome.order, outcome.invoice);
    }
    return { status: 'duplicate', order: outcome.order, invoice: outcome.invoice };
  }

  if (!outcome.invoice) {
    logger.info('payment.partial', {
      order: order.order_number,
      paid: outcome.order.amount_paid,
      total: outcome.order.total,
    });
    return { status: 'partial', order: outcome.order };
  }

  await deliverInvoice(db, outcome.order, outcome.invoice);
  return { status: 'settled', order: outcome.order, invoice: outcome.invoice };
}

/**
 * Render the invoice PDF and queue it for WhatsApp delivery.
 *
 * Deduped on the invoice number, so calling this again — from a duplicate
 * webhook, an admin "resend", or a restart — never sends a second copy unless
 * the first was already delivered and the operator asks explicitly.
 */
export async function deliverInvoice(
  db: Db,
  order: OrderRow,
  invoice: InvoiceRow,
  options: { force?: boolean } = {},
): Promise<void> {
  const customer = customers.findById(db, order.customer_id);
  if (!customer) throw new CheckoutError(`Customer ${order.customer_id} vanished`);

  const { filePath } = await renderInvoice(db, invoice, { force: options.force ?? false });

  const caption = [
    `*${config.GST_ENABLED ? 'Tax Invoice' : 'Bill of Supply'} ${invoice.invoice_number}*`,
    `Order ${order.order_number} · ${formatINR(order.total)}`,
    '',
    'Thank you for your order! We have started work on it.',
    `You can also download it any time: ${invoiceDownloadUrl(invoice)}`,
  ].join('\n');

  const filename = `${invoice.invoice_number.replace(/[^A-Za-z0-9._-]/g, '-')}.pdf`;

  enqueueMessage(
    db,
    customer.wa_phone,
    {
      kind: 'document',
      filePath,
      filename,
      caption,
      invoiceId: invoice.id,
      ...(invoice.whatsapp_media_id && !options.force
        ? { mediaId: invoice.whatsapp_media_id }
        : {}),
    },
    {
      dedupeKey: options.force
        ? `invoice:${invoice.invoice_number}:${Date.now()}`
        : `invoice:${invoice.invoice_number}`,
      orderId: order.id,
    },
  );

  // A short follow-up with the production ETA reads better than a long caption.
  enqueueMessage(
    db,
    customer.wa_phone,
    {
      kind: 'buttons',
      body:
        `Payment received for *${order.order_number}* ✅\n\n` +
        'Your print is queued. We will message you here when it moves into ' +
        'production and again when it ships.',
      buttons: [
        { id: `status:${order.order_number}`, title: 'Track order' },
        { id: 'catalog', title: 'Browse more' },
      ],
    },
    { dedupeKey: `paid-ack:${order.order_number}`, orderId: order.id },
  );

  logger.info('invoice.queued', {
    invoice: invoice.invoice_number,
    order: order.order_number,
    to: customer.wa_phone,
  });
}

function gatewayNameFor(event: PaymentEvent): string {
  // The raw payload carries the provider's own shape; the configured gateway is
  // the one that verified the signature, so its name is the correct label.
  return getGateway().name === 'mock' && event.providerPaymentId?.startsWith('pay_')
    ? 'razorpay'
    : getGateway().name;
}

/**
 * Match an event to an order: by our order number from the gateway's notes
 * first, then by the payment link we created.
 */
function findOrderForEvent(db: Db, event: PaymentEvent): OrderRow | undefined {
  if (event.orderNumber) {
    const byNumber = orders.findByNumber(db, event.orderNumber);
    if (byNumber) return byNumber;
  }
  if (event.providerLinkId) {
    const link = paymentLinks.findByProviderId(db, gatewayNameFor(event), event.providerLinkId);
    if (link) return orders.findById(db, link.order_id);
  }
  return undefined;
}
