/**
 * End-to-end: a customer browses on WhatsApp, sends a cart, gives an address,
 * pays, and receives a GST invoice PDF back in the chat.
 *
 * The WhatsApp API is replaced by a recording fake, so every message the system
 * would send is asserted on. The payment gateway is the mock — which signs and
 * verifies real HMACs, so the signature path is genuinely exercised.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterAll, beforeEach, describe, expect, it } from 'vitest';
import { openDatabase } from '../src/db/index.js';
import type { Db } from '../src/db/index.js';
import {
  customers,
  invoices as invoiceRepo,
  orders,
  outbox,
  products,
} from '../src/db/repositories.js';
import { toPaise } from '../src/domain/money.js';
import { MockGateway } from '../src/payments/mock.js';
import { setGateway } from '../src/payments/index.js';
import { WhatsAppClient, setWhatsAppClient } from '../src/whatsapp/client.js';
import { handleEvent } from '../src/whatsapp/flows.js';
import type { CartEvent, InboundEvent, TextEvent } from '../src/whatsapp/webhook.js';
import { dispatchOutbox } from '../src/services/messaging.js';
import { settlePayment } from '../src/services/checkout.js';
import { issueInvoice, renderInvoice } from '../src/services/invoices.js';

// ── A WhatsApp client that records instead of calling Meta ──────────────────

interface SentMessage {
  url: string;
  body: Record<string, unknown>;
}

const sent: SentMessage[] = [];
let mediaCounter = 0;

function fakeClient(): WhatsAppClient {
  return new WhatsAppClient({
    accessToken: 'test-token',
    phoneNumberId: '1234567890',
    catalogId: 'catalog-1',
    transport: async (url, init) => {
      // Media upload arrives as multipart; everything else as JSON.
      if (url.endsWith('/media')) {
        mediaCounter += 1;
        return jsonResponse({ id: `media_${mediaCounter}` });
      }
      const body = init.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : {};
      sent.push({ url, body });
      return jsonResponse({ messages: [{ id: `wamid.${sent.length}` }] });
    },
  });
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Messages of a given interactive/plain kind that were actually delivered. */
function sentOfType(type: string): SentMessage[] {
  return sent.filter((message) => message.body.type === type);
}

function sentText(): string[] {
  return sentOfType('text').map(
    (message) => (message.body.text as { body: string }).body,
  );
}

// ── Fixtures ────────────────────────────────────────────────────────────────

const CUSTOMER_PHONE = '919876543210';
const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'printbill-test-'));

let db: Db;
let client: WhatsAppClient;
let gateway: MockGateway;

beforeEach(() => {
  db = openDatabase(':memory:');
  sent.length = 0;
  mediaCounter = 0;
  client = fakeClient();
  setWhatsAppClient(client);
  gateway = new MockGateway('test-secret-key');
  setGateway(gateway);

  products.upsert(db, {
    retailerId: 'nameplate-classic',
    name: 'Custom Name Plate — Classic',
    description: 'Personalised door name plate',
    category: 'nameplates',
    price: toPaise(649),
    hsnCode: '3926',
    gstRate: 18,
    materialKey: 'pla',
    weightGrams: 85,
    printHours: 4.5,
    stockQuantity: 10,
  });
  products.upsert(db, {
    retailerId: 'phone-stand-adjustable',
    name: 'Adjustable Phone Stand',
    description: 'Folding desk stand',
    category: 'desk',
    price: toPaise(349),
    hsnCode: '3926',
    gstRate: 18,
    stockQuantity: 5,
  });
});

afterAll(() => {
  setWhatsAppClient(null);
  setGateway(null);
  fs.rmSync(workDir, { recursive: true, force: true });
});

// ── Event builders ──────────────────────────────────────────────────────────

let messageCounter = 0;

function textEvent(text: string): TextEvent {
  messageCounter += 1;
  return {
    type: 'text',
    messageId: `wamid.in.${messageCounter}`,
    from: CUSTOMER_PHONE,
    timestamp: '1800000000',
    contactName: 'Ananya Sharma',
    raw: {},
    text,
  };
}

function cartEvent(
  items: { productRetailerId: string; quantity: number; itemPrice: number }[],
): CartEvent {
  messageCounter += 1;
  return {
    type: 'order',
    messageId: `wamid.in.${messageCounter}`,
    from: CUSTOMER_PHONE,
    timestamp: '1800000000',
    contactName: 'Ananya Sharma',
    raw: {},
    catalogId: 'catalog-1',
    note: null,
    products: items.map((item) => ({
      productRetailerId: item.productRetailerId,
      quantity: item.quantity,
      itemPrice: toPaise(item.itemPrice),
      currency: 'INR',
    })),
  };
}

function interactiveEvent(replyId: string): InboundEvent {
  messageCounter += 1;
  return {
    type: 'interactive',
    messageId: `wamid.in.${messageCounter}`,
    from: CUSTOMER_PHONE,
    timestamp: '1800000000',
    contactName: 'Ananya Sharma',
    raw: {},
    replyId,
    title: replyId,
  };
}

/** Build and settle a signed gateway webhook for an order. */
async function payOrder(orderNumber: string, amount: number): Promise<void> {
  const payload = {
    event: 'payment.captured',
    eventId: `evt_${orderNumber}`,
    paymentId: `pay_${orderNumber}`,
    orderNumber,
    amount,
    method: 'upi',
  };
  const signed = gateway.signPayload(payload);
  const event = gateway.parseWebhook(Buffer.from(signed.body), {
    'x-mock-signature': signed.signature,
  });
  await settlePayment(db, event);
}

// ─────────────────────────────────────────────────────────────────────────────

describe('greeting', () => {
  it('answers a first message with the main menu', async () => {
    await handleEvent(db, textEvent('hi'));
    await dispatchOutbox(db, { client });

    const lists = sentOfType('interactive');
    expect(lists).toHaveLength(1);
    const interactive = lists[0]?.body.interactive as { type: string; action: { sections: unknown[] } };
    expect(interactive.type).toBe('list');
    expect(interactive.action.sections.length).toBeGreaterThan(0);
  });

  it('creates the customer record from the contact profile', async () => {
    await handleEvent(db, textEvent('hi'));
    const customer = customers.findByPhone(db, CUSTOMER_PHONE);
    expect(customer?.name).toBe('Ananya Sharma');
  });

  it('ignores a redelivered message', async () => {
    const event = textEvent('hi');
    await handleEvent(db, event);
    await handleEvent(db, event); // Meta retry
    await dispatchOutbox(db, { client });
    expect(sent).toHaveLength(1);
  });
});

describe('cart to invoice', () => {
  it('walks the full path and delivers a PDF invoice on WhatsApp', async () => {
    // 1. Customer sends a cart from the in-chat storefront.
    await handleEvent(db, cartEvent([{ productRetailerId: 'nameplate-classic', quantity: 2, itemPrice: 649 }]));

    const order = orders.list(db, { limit: 1 })[0];
    expect(order).toBeDefined();
    expect(order?.status).toBe('pending_payment');
    expect(order?.channel).toBe('whatsapp_cart');

    // Catalog prices are GST-inclusive: 2 x ₹649 = ₹1298 gross.
    // Delivery is free above the threshold, so the total is exactly ₹1298.
    expect(order?.total).toBe(toPaise(1298));
    expect(order?.cgst).toBe(order?.sgst);
    expect(order?.igst).toBe(0);

    // 2. No address on file, so the bot asks for one before payment.
    await dispatchOutbox(db, { client });
    expect(sentText().join('\n')).toContain('Where should we deliver this?');

    // 3. Customer sends an address; the payment link follows.
    await handleEvent(db, textEvent('402 Sunrise Residency, HSR Layout, Bengaluru, Karnataka 560102'));
    await dispatchOutbox(db, { client });

    const linkMessage = sentText().find((text) => text.includes('/pay/mock/'));
    expect(linkMessage).toBeDefined();
    expect(linkMessage).toContain(order?.order_number);

    // 4. Gateway confirms the payment.
    await payOrder(order!.order_number, order!.total);

    const paid = orders.findById(db, order!.id);
    expect(paid?.status).toBe('paid');
    expect(paid?.amount_paid).toBe(paid?.total);
    expect(paid?.paid_at).not.toBeNull();

    // 5. An invoice exists, numbered for the financial year.
    const invoice = invoiceRepo.findByOrderId(db, order!.id);
    expect(invoice).toBeDefined();
    expect(invoice?.invoice_number).toMatch(/^INV\/\d{4}-\d{2}\/0001$/);
    expect(invoice?.document_type).toBe('tax_invoice');

    // 6. The PDF goes out as a document message.
    await dispatchOutbox(db, { client });
    const documents = sentOfType('document');
    expect(documents).toHaveLength(1);
    const document = documents[0]?.body.document as { id: string; filename: string; caption: string };
    expect(document.filename).toMatch(/\.pdf$/);
    expect(document.caption).toContain(invoice?.invoice_number);
    // Uploaded first, then sent by media id — never as a public link.
    expect(document.id).toMatch(/^media_/);

    // 7. Stock was reduced only once payment landed.
    expect(products.findByRetailerId(db, 'nameplate-classic')?.stock_quantity).toBe(8);
  });

  it('charges IGST when the delivery address is in another state', async () => {
    await handleEvent(db, cartEvent([{ productRetailerId: 'nameplate-classic', quantity: 1, itemPrice: 649 }]));
    await handleEvent(db, textEvent('12 Marine Drive, Mumbai, Maharashtra 400020'));

    const customer = customers.findByPhone(db, CUSTOMER_PHONE);
    expect(customer?.state_code).toBe('27');
    expect(customer?.pincode).toBe('400020');
  });

  it('rejects a cart for a product that is not in our catalog', async () => {
    await handleEvent(db, cartEvent([{ productRetailerId: 'ghost-product', quantity: 1, itemPrice: 100 }]));
    await dispatchOutbox(db, { client });

    expect(orders.list(db)).toHaveLength(0);
    const bodies = sentOfType('interactive').map(
      (message) => (message.body.interactive as { body: { text: string } }).body.text,
    );
    expect(bodies.join('\n')).toContain('could not place that order');
  });

  it('refuses to oversell tracked stock', async () => {
    await handleEvent(db, cartEvent([{ productRetailerId: 'phone-stand-adjustable', quantity: 99, itemPrice: 349 }]));
    expect(orders.list(db)).toHaveLength(0);
  });

  it('ignores the price the cart reports and uses our own', async () => {
    // A stale or tampered cart claiming ₹1 must not set the price.
    await handleEvent(db, cartEvent([{ productRetailerId: 'nameplate-classic', quantity: 1, itemPrice: 1 }]));

    const order = orders.list(db, { limit: 1 })[0]!;
    const [item] = orders.items(db, order.id);

    // ₹649 shelf price is GST-inclusive, so the taxable unit price is ₹550.
    expect(item?.unit_price).toBe(toPaise(550));
    expect(item?.line_total).toBe(toPaise(649));
  });

  it('adds delivery below the free-delivery threshold and drops it above', async () => {
    await handleEvent(db, cartEvent([{ productRetailerId: 'nameplate-classic', quantity: 1, itemPrice: 649 }]));
    const small = orders.list(db, { limit: 1 })[0]!;
    // ₹649 < ₹999 threshold: ₹79 delivery, taxed at the order's 18%.
    expect(small.shipping).toBe(toPaise(79));
    expect(small.total).toBe(toPaise(742));

    await handleEvent(db, cartEvent([{ productRetailerId: 'nameplate-classic', quantity: 2, itemPrice: 649 }]));
    const large = orders.list(db, { limit: 1 })[0]!;
    expect(large.shipping).toBe(0);
    expect(large.total).toBe(toPaise(1298));
  });
});

describe('payment webhook safety', () => {
  async function placeOrder(): Promise<{ id: number; order_number: string; total: number }> {
    customers.upsertByPhone(db, {
      waPhone: CUSTOMER_PHONE,
      addressLine1: '402 Sunrise Residency',
      pincode: '560102',
      stateCode: '29',
    });
    await handleEvent(db, cartEvent([{ productRetailerId: 'nameplate-classic', quantity: 1, itemPrice: 649 }]));
    const order = orders.list(db, { limit: 1 })[0]!;
    return { id: order.id, order_number: order.order_number, total: order.total };
  }

  it('rejects a webhook with a bad signature', async () => {
    const payload = { event: 'payment.captured', orderNumber: 'ORD-1', amount: 100 };
    expect(() =>
      gateway.parseWebhook(Buffer.from(JSON.stringify(payload)), {
        'x-mock-signature': 'deadbeef',
      }),
    ).toThrow(/signature/i);
  });

  it('rejects a webhook with no signature at all', async () => {
    expect(() => gateway.parseWebhook(Buffer.from('{}'), {})).toThrow(/Missing/i);
  });

  it('rejects a tampered body even with a valid-looking signature', async () => {
    const signed = gateway.signPayload({ orderNumber: 'ORD-1', amount: 100 });
    const tampered = signed.body.replace('100', '999999');
    expect(() =>
      gateway.parseWebhook(Buffer.from(tampered), { 'x-mock-signature': signed.signature }),
    ).toThrow(/signature/i);
  });

  it('credits an order exactly once when the webhook is delivered twice', async () => {
    const order = await placeOrder();

    await payOrder(order.order_number, order.total);
    await payOrder(order.order_number, order.total); // gateway retry

    const settled = orders.findById(db, order.id);
    expect(settled?.amount_paid).toBe(order.total);

    // One invoice, one number, one document queued.
    const allInvoices = invoiceRepo.list(db);
    expect(allInvoices).toHaveLength(1);

    await dispatchOutbox(db, { client });
    expect(sentOfType('document')).toHaveLength(1);
  });

  it('records a part payment without issuing an invoice', async () => {
    const order = await placeOrder();
    await payOrder(order.order_number, Math.floor(order.total / 2));

    const partial = orders.findById(db, order.id);
    expect(partial?.status).toBe('pending_payment');
    expect(invoiceRepo.findByOrderId(db, order.id)).toBeUndefined();
  });

  it('does not match an event to an unknown order', async () => {
    const payload = {
      event: 'payment.captured',
      eventId: 'evt_ghost',
      paymentId: 'pay_ghost',
      orderNumber: 'ORD-99999999-9999',
      amount: 10_000,
    };
    const signed = gateway.signPayload(payload);
    const event = gateway.parseWebhook(Buffer.from(signed.body), {
      'x-mock-signature': signed.signature,
    });
    const result = await settlePayment(db, event);
    expect(result.status).toBe('unmatched');
  });
});

describe('invoice numbering under load', () => {
  it('never reuses a number across many orders', async () => {
    const customer = customers.upsertByPhone(db, { waPhone: '919000000001', stateCode: '29' });

    const numbers = new Set<string>();
    for (let index = 0; index < 25; index += 1) {
      const { createOrder } = await import('../src/services/orders.js');
      const created = createOrder(db, {
        customerId: customer.id,
        channel: 'manual',
        lines: [{ description: `Job ${index}`, quantity: 1, unitPrice: toPaise(100) }],
      });
      const invoice = issueInvoice(db, created.order.id);
      expect(numbers.has(invoice.invoice_number)).toBe(false);
      numbers.add(invoice.invoice_number);
    }
    expect(numbers.size).toBe(25);
  });

  it('returns the same invoice when issued twice for one order', async () => {
    const customer = customers.upsertByPhone(db, { waPhone: '919000000002', stateCode: '29' });
    const { createOrder } = await import('../src/services/orders.js');
    const created = createOrder(db, {
      customerId: customer.id,
      channel: 'manual',
      lines: [{ description: 'Job', quantity: 1, unitPrice: toPaise(100) }],
    });

    const first = issueInvoice(db, created.order.id);
    const second = issueInvoice(db, created.order.id);
    expect(second.id).toBe(first.id);
    expect(second.invoice_number).toBe(first.invoice_number);
  });
});

describe('invoice PDF', () => {
  it('renders a real PDF whose totals match the order', async () => {
    const customer = customers.upsertByPhone(db, {
      waPhone: '919000000003',
      name: 'Test Buyer',
      addressLine1: '1 Test Street',
      city: 'Bengaluru',
      stateCode: '29',
      pincode: '560001',
    });
    const { createOrder } = await import('../src/services/orders.js');
    const created = createOrder(db, {
      customerId: customer.id,
      channel: 'manual',
      lines: [
        { description: 'Custom print', quantity: 3, unitPrice: toPaise(500), gstRate: 18 },
      ],
    });

    const invoice = issueInvoice(db, created.order.id);
    const { bytes } = await renderInvoice(db, invoice);

    expect(bytes.subarray(0, 5).toString()).toBe('%PDF-');
    expect(bytes.length).toBeGreaterThan(1000);

    const stored = invoiceRepo.findByOrderId(db, created.order.id);
    expect(stored?.pdf_sha256).toMatch(/^[a-f0-9]{64}$/);
    expect(stored?.total).toBe(created.order.total);
  });
});

describe('outbox resilience', () => {
  it('retries a transient failure with backoff, then succeeds', async () => {
    let attempts = 0;
    const flaky = new WhatsAppClient({
      accessToken: 'x',
      phoneNumberId: '1',
      transport: async () => {
        attempts += 1;
        if (attempts === 1) return jsonResponse({ error: { message: 'upstream' } }, 503);
        return jsonResponse({ messages: [{ id: 'wamid.ok' }] });
      },
    });

    await handleEvent(db, textEvent('hi'));

    const first = await dispatchOutbox(db, { client: flaky });
    expect(first.failed).toBe(1);

    // Backed off, so nothing is due yet.
    expect(outbox.due(db)).toHaveLength(0);

    // Fast-forward the retry time.
    db.prepare(
      "UPDATE message_outbox SET next_attempt_at = '2000-01-01T00:00:00.000Z' WHERE status = 'pending'",
    ).run();

    const second = await dispatchOutbox(db, { client: flaky });
    expect(second.sent).toBe(1);
  });

  it('abandons a permanent failure without retrying', async () => {
    const rejecting = new WhatsAppClient({
      accessToken: 'x',
      phoneNumberId: '1',
      transport: async () =>
        jsonResponse({ error: { message: 'not a WhatsApp user', code: 131_026 } }, 400),
    });

    await handleEvent(db, textEvent('hi'));
    await dispatchOutbox(db, { client: rejecting });

    const row = db
      .prepare("SELECT status FROM message_outbox WHERE id = 1")
      .get() as { status: string };
    expect(row.status).toBe('abandoned');
  });

  it('does not queue the same invoice twice', async () => {
    const customer = customers.upsertByPhone(db, { waPhone: CUSTOMER_PHONE, stateCode: '29' });
    const { createOrder } = await import('../src/services/orders.js');
    const created = createOrder(db, {
      customerId: customer.id,
      channel: 'manual',
      lines: [{ description: 'Job', quantity: 1, unitPrice: toPaise(100) }],
    });
    const invoice = issueInvoice(db, created.order.id);

    const { deliverInvoice } = await import('../src/services/checkout.js');
    await deliverInvoice(db, created.order, invoice);
    await deliverInvoice(db, created.order, invoice);

    const queued = db
      .prepare("SELECT COUNT(*) AS count FROM message_outbox WHERE kind = 'document'")
      .get() as { count: number };
    expect(queued.count).toBe(1);
  });
});

describe('order tracking', () => {
  it('will not reveal another customer\'s order', async () => {
    const other = customers.upsertByPhone(db, { waPhone: '919111111111', stateCode: '29' });
    const { createOrder } = await import('../src/services/orders.js');
    const created = createOrder(db, {
      customerId: other.id,
      channel: 'manual',
      lines: [{ description: 'Secret job', quantity: 1, unitPrice: toPaise(9999) }],
    });

    await handleEvent(db, interactiveEvent(`status:${created.order.order_number}`));
    await dispatchOutbox(db, { client });

    const texts = sentText().join('\n');
    expect(texts).toContain('could not find order');
    expect(texts).not.toContain('Secret job');
  });

  it('shows the customer their own order', async () => {
    customers.upsertByPhone(db, { waPhone: CUSTOMER_PHONE, stateCode: '29' });
    await handleEvent(db, cartEvent([{ productRetailerId: 'nameplate-classic', quantity: 1, itemPrice: 649 }]));
    const order = orders.list(db, { limit: 1 })[0]!;

    sent.length = 0;
    await handleEvent(db, interactiveEvent(`status:${order.order_number}`));
    await dispatchOutbox(db, { client });

    const bodies = sentOfType('interactive').map(
      (message) => (message.body.interactive as { body: { text: string } }).body.text,
    );
    expect(bodies.join('\n')).toContain(order.order_number);
    expect(bodies.join('\n')).toContain('Waiting for payment');
  });
});

describe('GSTIN capture', () => {
  it('stores a valid GSTIN and sets the state from it', async () => {
    await handleEvent(db, interactiveEvent('gstin'));
    await handleEvent(db, textEvent('27AAFCS1234R1ZY'));

    const customer = customers.findByPhone(db, CUSTOMER_PHONE);
    expect(customer?.gstin).toBe('27AAFCS1234R1ZY');
    expect(customer?.state_code).toBe('27');
  });

  it('rejects an invalid GSTIN and stays in the same state', async () => {
    await handleEvent(db, interactiveEvent('gstin'));
    await handleEvent(db, textEvent('29INVALIDGSTIN1'));

    const customer = customers.findByPhone(db, CUSTOMER_PHONE);
    expect(customer?.gstin).toBeNull();

    await dispatchOutbox(db, { client });
    expect(sentText().join('\n')).toContain('does not look like a valid GSTIN');
  });
});
