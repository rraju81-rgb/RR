/**
 * The conversation.
 *
 * This is the shop floor: everything a customer can do — browse, ask for a
 * custom quote, pay, chase an order, get their invoice again — happens through
 * the handlers below. It is written as an explicit state machine because chat
 * is inherently resumable: a customer can vanish mid-order and come back three
 * days later, and the reply has to still make sense.
 *
 * Two rules shape the design:
 *   1. Nothing here sends a message directly; everything is queued on the
 *      outbox, so a slow WhatsApp API never stalls a webhook.
 *   2. The customer is never asked for something we can infer.
 */
import type { Db } from '../db/index.js';
import { conversations, customers, inboundMessages, orders, products, quotes } from '../db/repositories.js';
import type { CustomerRow, OrderRow } from '../db/types.js';
import { config, seller } from '../config/env.js';
import { GST_STATE_CODES, isValidGstin, stateCodeFromGstin, stateNameForCode } from '../domain/gst.js';
import { formatINR, toPaise } from '../domain/money.js';
import {
  MATERIALS,
  type PostProcessing,
  type QuoteRequest,
  explainQuote,
  findMaterial,
  quotePrintJob,
} from '../domain/pricing.js';
import { formatQuoteNumber } from '../domain/numbering.js';
import { nextCounterValue, transaction } from '../db/index.js';
import { enqueueMessage } from '../services/messaging.js';
import { buildProductSections } from '../services/catalog.js';
import { createOrder, linesFromCart } from '../services/orders.js';
import { requestPayment } from '../services/checkout.js';
import { invoiceDownloadUrl } from '../services/invoices.js';
import { invoices as invoiceRepo } from '../db/repositories.js';
import { logger } from '../lib/logger.js';
import type { CartEvent, InboundEvent, InteractiveEvent, MediaEvent, TextEvent } from './webhook.js';

/** Where a customer is in the conversation. */
export type ConversationState =
  | 'idle'
  | 'awaiting_address'
  | 'awaiting_gstin'
  | 'quote_material'
  | 'quote_quantity'
  | 'quote_notes'
  | 'quote_review'
  | 'human_handoff';

interface ConversationContext {
  /** Order waiting on an address before a payment link can go out. */
  pendingOrderId?: number;
  /** Custom-quote answers gathered so far. */
  quote?: {
    materialKey?: string;
    quantity?: number;
    notes?: string;
    mediaId?: string;
    filename?: string;
  };
}

interface Session {
  readonly customer: CustomerRow;
  readonly state: ConversationState;
  readonly context: ConversationContext;
}

export interface HandleOptions {
  /** Injected so tests can drive time-dependent behaviour. */
  readonly now?: Date;
}

/**
 * Entry point for one inbound event.
 *
 * Returns quietly for events that need no reply (delivery receipts, a message
 * we have already handled), so the caller can always answer Meta with a 200.
 */
export async function handleEvent(
  db: Db,
  event: InboundEvent,
  options: HandleOptions = {},
): Promise<void> {
  if (event.type === 'status') {
    if (event.status === 'failed') {
      logger.warn('whatsapp.delivery_failed', {
        messageId: event.messageId,
        recipient: event.recipient,
        error: event.errorMessage,
      });
    }
    return;
  }

  // Meta redelivers on any non-200, so the same message can arrive twice.
  const isNew = inboundMessages.recordIfNew(db, {
    waMessageId: event.messageId,
    fromPhone: event.from,
    messageType: event.type,
    body: 'text' in event ? event.text : null,
    payload: event.raw,
  });
  if (!isNew) {
    logger.debug('whatsapp.duplicate_inbound', { messageId: event.messageId });
    return;
  }

  const customer = customers.upsertByPhone(db, {
    waPhone: event.from,
    name: event.contactName,
  });
  conversations.touchInbound(db, event.from);

  const session = loadSession(db, customer);

  switch (event.type) {
    case 'order':
      await handleCart(db, session, event);
      return;
    case 'interactive':
      await handleInteractive(db, session, event, options);
      return;
    case 'text':
      await handleText(db, session, event, options);
      return;
    case 'media':
      handleMedia(db, session, event);
      return;
    case 'location':
      // A pinned location is a usable delivery address.
      saveAddressAndContinue(db, session, event.address ?? `${event.latitude}, ${event.longitude}`);
      return;
    default:
      sendMainMenu(db, session.customer, 'Sorry, I can only read text, buttons and files here.');
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Session
// ─────────────────────────────────────────────────────────────────────────────

function loadSession(db: Db, customer: CustomerRow): Session {
  const row = conversations.get(db, customer.wa_phone);
  let context: ConversationContext = {};
  if (row?.context_json) {
    try {
      context = JSON.parse(row.context_json) as ConversationContext;
    } catch {
      context = {};
    }
  }
  return {
    customer,
    state: (row?.state as ConversationState) ?? 'idle',
    context,
  };
}

function saveSession(
  db: Db,
  session: Session,
  state: ConversationState,
  context: ConversationContext = session.context,
): Session {
  conversations.save(db, session.customer.wa_phone, state, context);
  return { ...session, state, context };
}

// ─────────────────────────────────────────────────────────────────────────────
// Cart orders — the main sales path
// ─────────────────────────────────────────────────────────────────────────────

/**
 * A cart arrived from the in-chat storefront.
 *
 * Turn it into a priced order immediately, then either ask for the missing
 * delivery address or go straight to payment. The customer should never have to
 * repeat anything they have already told us.
 */
async function handleCart(db: Db, session: Session, event: CartEvent): Promise<void> {
  const { customer } = session;

  if (event.products.length === 0) {
    sendText(db, customer, 'That cart came through empty — please add an item and send it again.');
    return;
  }

  let order: OrderRow;
  try {
    const lines = linesFromCart(db, event.products);
    const created = createOrder(db, {
      customerId: customer.id,
      channel: 'whatsapp_cart',
      lines,
      customerNote: event.note,
      shippingAddress: formattedAddress(customer),
    });
    order = created.order;
  } catch (error) {
    logger.warn('cart.rejected', {
      from: event.from,
      error: error instanceof Error ? error.message : String(error),
    });
    enqueueMessage(db, customer.wa_phone, {
      kind: 'buttons',
      body:
        `We could not place that order:\n\n_${
          error instanceof Error ? error.message : 'Unknown error'
        }_\n\nShall we take a look together?`,
      buttons: [
        { id: 'catalog', title: 'Browse again' },
        { id: 'support', title: 'Talk to us' },
      ],
    });
    return;
  }

  const summary = orderSummary(db, order);

  if (!hasDeliverableAddress(customer)) {
    saveSession(db, session, 'awaiting_address', {
      ...session.context,
      pendingOrderId: order.id,
    });
    enqueueMessage(db, customer.wa_phone, {
      kind: 'text',
      text:
        `${summary}\n\n` +
        '📍 *Where should we deliver this?*\n' +
        'Send your full address in one message — house/flat, street, area, city, ' +
        'state and PIN code.\n\n' +
        '_You can also share your location pin instead._',
    });
    return;
  }

  sendText(db, customer, summary);
  await startPayment(db, customer, order);
}

/**
 * Create the payment link and hand it over.
 * Failures here are recoverable — the order exists and can be retried — so the
 * customer gets a retry button rather than an error.
 */
async function startPayment(db: Db, customer: CustomerRow, order: OrderRow): Promise<void> {
  try {
    await requestPayment(db, order.id);
  } catch (error) {
    logger.error('payment.link_failed', {
      order: order.order_number,
      error: error instanceof Error ? error.message : String(error),
    });
    enqueueMessage(db, customer.wa_phone, {
      kind: 'buttons',
      body:
        `Your order *${order.order_number}* is saved, but the payment link did not ` +
        'generate. Tap below and I will try again.',
      buttons: [
        { id: `pay:${order.order_number}`, title: 'Retry payment' },
        { id: 'support', title: 'Talk to us' },
      ],
    });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Interactive replies
// ─────────────────────────────────────────────────────────────────────────────

async function handleInteractive(
  db: Db,
  session: Session,
  event: InteractiveEvent,
  options: HandleOptions,
): Promise<void> {
  const [command = '', argument = ''] = splitOnce(event.replyId, ':');

  switch (command) {
    case 'catalog':
      sendCatalog(db, session.customer);
      return;

    case 'cat':
      sendCategory(db, session.customer, argument);
      return;

    case 'quote':
      startQuoteFlow(db, session);
      return;

    case 'material':
      await captureQuoteMaterial(db, session, argument);
      return;

    case 'qty':
      await captureQuoteQuantity(db, session, Number(argument), options);
      return;

    case 'pay': {
      const order = orders.findByNumber(db, argument);
      if (!order) {
        sendText(db, session.customer, `I could not find order ${argument}.`);
        return;
      }
      if (order.customer_id !== session.customer.id) {
        // Order numbers are guessable; never leak another customer's order.
        sendText(db, session.customer, `I could not find order ${argument}.`);
        return;
      }
      await startPayment(db, session.customer, order);
      return;
    }

    case 'status':
      sendOrderStatus(db, session.customer, argument);
      return;

    case 'invoice':
      sendInvoiceLink(db, session.customer, argument);
      return;

    case 'orders':
      sendRecentOrders(db, session.customer);
      return;

    case 'gstin':
      saveSession(db, session, 'awaiting_gstin');
      sendText(
        db,
        session.customer,
        'Send your GSTIN and I will put it on your invoices from now on.\n\n' +
          '_Format: 29ABCDE1234F1ZW_',
      );
      return;

    case 'accept_quote':
      await acceptQuote(db, session, argument);
      return;

    case 'support':
      saveSession(db, session, 'human_handoff');
      sendText(
        db,
        session.customer,
        `Sure — someone from ${seller.tradeName} will reply here shortly.\n\n` +
          (seller.phone ? `In a hurry? Call us on ${seller.phone}.` : '') +
          '\n\n_Send *menu* any time to go back._',
      );
      return;

    case 'menu':
      sendMainMenu(db, session.customer);
      return;

    default:
      sendMainMenu(db, session.customer);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Free text
// ─────────────────────────────────────────────────────────────────────────────

async function handleText(
  db: Db,
  session: Session,
  event: TextEvent,
  options: HandleOptions,
): Promise<void> {
  const text = event.text.trim();
  const normalised = text.toLowerCase();

  // A few words always work, whatever state the conversation is in — an escape
  // hatch matters when someone is stuck mid-flow.
  if (['menu', 'hi', 'hello', 'hey', 'start', 'namaste'].includes(normalised)) {
    saveSession(db, session, 'idle');
    sendMainMenu(db, session.customer);
    return;
  }
  if (['catalog', 'catalogue', 'products', 'shop', 'buy'].includes(normalised)) {
    sendCatalog(db, session.customer);
    return;
  }
  if (['quote', 'custom', 'print my file'].includes(normalised)) {
    startQuoteFlow(db, session);
    return;
  }

  switch (session.state) {
    case 'awaiting_address':
      saveAddressAndContinue(db, session, text);
      return;

    case 'awaiting_gstin':
      captureGstin(db, session, text);
      return;

    case 'quote_quantity': {
      const quantity = Number.parseInt(text, 10);
      if (!Number.isFinite(quantity) || quantity < 1) {
        sendText(db, session.customer, 'Please send just a number, for example: 5');
        return;
      }
      await captureQuoteQuantity(db, session, quantity, options);
      return;
    }

    case 'quote_notes':
      await captureQuoteNotes(db, session, text, options);
      return;

    case 'human_handoff':
      // Stay quiet: a human is answering. Auto-replies here are noise.
      logger.info('whatsapp.handoff_message', { from: event.from, text });
      return;

    default:
      break;
  }

  // An order number typed on its own is a status request.
  const orderMatch = /\b(ORD-\d{8}-\d{4})\b/i.exec(text);
  if (orderMatch?.[1]) {
    sendOrderStatus(db, session.customer, orderMatch[1].toUpperCase());
    return;
  }

  sendMainMenu(
    db,
    session.customer,
    "I did not quite catch that — here's what I can help with:",
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Media — a customer sending a model to be printed
// ─────────────────────────────────────────────────────────────────────────────

function handleMedia(db: Db, session: Session, event: MediaEvent): void {
  const filename = event.filename ?? '';
  const isModel = /\.(stl|obj|3mf|step|stp|gcode|f3d|ipt|sldprt)$/i.test(filename);

  const context: ConversationContext = {
    ...session.context,
    quote: {
      ...session.context.quote,
      mediaId: event.mediaId,
      filename: filename || `${event.mediaKind}-${event.mediaId}`,
    },
  };
  saveSession(db, session, 'quote_material', context);

  const acknowledgement = isModel
    ? `Got your file *${filename}* 📐`
    : 'Got your reference 👍 We can work from a photo or sketch too.';

  enqueueMessage(db, session.customer.wa_phone, {
    kind: 'list',
    header: 'Custom print',
    body:
      `${acknowledgement}\n\n` +
      'Which material should we print it in? Not sure — pick PLA and we will ' +
      'suggest a better fit if it needs one.',
    buttonText: 'Choose material',
    sections: [
      {
        title: 'Everyday',
        rows: MATERIALS.slice(0, 4).map((material) => ({
          id: `material:${material.key}`,
          title: material.name,
          description: material.notes ?? '',
        })),
      },
      {
        title: 'Engineering & detail',
        rows: MATERIALS.slice(4, 9).map((material) => ({
          id: `material:${material.key}`,
          title: material.name,
          description: material.notes ?? '',
        })),
      },
    ],
    footer: 'Prices are confirmed after we check the model',
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom quote flow
// ─────────────────────────────────────────────────────────────────────────────

function startQuoteFlow(db: Db, session: Session): void {
  saveSession(db, session, 'quote_material', { ...session.context, quote: {} });
  enqueueMessage(db, session.customer.wa_phone, {
    kind: 'text',
    text:
      '*Custom 3D printing* 🖨️\n\n' +
      'Send me your 3D model file and I will quote it — STL, OBJ, 3MF or STEP.\n\n' +
      'No model yet? Send a photo or a sketch with rough dimensions and we will ' +
      'design it for you.',
  });
}

async function captureQuoteMaterial(db: Db, session: Session, materialKey: string): Promise<void> {
  const material = findMaterial(materialKey);
  if (!material) {
    sendText(db, session.customer, 'That material is not on our list — please pick one from the menu.');
    return;
  }

  const context: ConversationContext = {
    ...session.context,
    quote: { ...session.context.quote, materialKey },
  };
  saveSession(db, session, 'quote_quantity', context);

  enqueueMessage(db, session.customer.wa_phone, {
    kind: 'buttons',
    body: `*${material.name}* it is.\n\n${material.notes ?? ''}\n\nHow many do you need?`,
    buttons: [
      { id: 'qty:1', title: 'Just 1' },
      { id: 'qty:5', title: '5 pieces' },
      { id: 'qty:10', title: '10 pieces' },
    ],
    footer: 'Or type any number',
  });
}

async function captureQuoteQuantity(
  db: Db,
  session: Session,
  quantity: number,
  _options: HandleOptions,
): Promise<void> {
  if (!Number.isFinite(quantity) || quantity < 1) {
    sendText(db, session.customer, 'Please send a whole number, for example: 3');
    return;
  }

  const context: ConversationContext = {
    ...session.context,
    quote: { ...session.context.quote, quantity: Math.floor(quantity) },
  };
  saveSession(db, session, 'quote_notes', context);

  enqueueMessage(db, session.customer.wa_phone, {
    kind: 'text',
    text:
      `${quantity} piece${quantity > 1 ? 's' : ''} noted.\n\n` +
      'Anything else we should know? Colour, size, deadline, finishing — send it ' +
      'all in one message.\n\n' +
      '_Nothing to add? Just reply *no*._',
  });
}

/**
 * Final step: price an indicative quote from the answers.
 *
 * The model has not been sliced yet, so the estimate uses conservative
 * placeholder figures and is labelled as such. The operator confirms the real
 * numbers from the admin console, which reprices and resends.
 */
async function captureQuoteNotes(
  db: Db,
  session: Session,
  notes: string,
  options: HandleOptions,
): Promise<void> {
  const draft = session.context.quote ?? {};
  const materialKey = draft.materialKey ?? 'pla';
  const quantity = draft.quantity ?? 1;
  const cleanedNotes = /^(no|nope|nothing|na|n\/a)$/i.test(notes.trim()) ? '' : notes.trim();

  // Placeholder geometry until the file is sliced: a small functional part.
  const request: QuoteRequest = {
    materialKey,
    weightGrams: 60,
    printHours: 3.5,
    quantity,
    postProcessing: ['support_removal'] as PostProcessing[],
    rush: 'standard',
  };

  const quote = quotePrintJob(request, {
    machineRatePerHour: toPaise(config.PRICING_MACHINE_RATE_PER_HOUR),
    labourRatePerHour: toPaise(config.PRICING_LABOUR_RATE_PER_HOUR),
    setupFee: toPaise(config.PRICING_SETUP_FEE),
    marginMultiplier: config.PRICING_MARGIN_MULTIPLIER,
    wastageFactor: config.PRICING_WASTAGE_FACTOR,
  });

  const now = options.now ?? new Date();
  const stored = transaction(db, () => {
    const sequence = nextCounterValue(db, 'quote');
    return quotes.insert(db, {
      quoteNumber: formatQuoteNumber(sequence, now),
      customerId: session.customer.id,
      request: { ...request, notes: cleanedNotes, mediaId: draft.mediaId },
      result: quote,
      unitPrice: quote.unitPrice,
      total: quote.total,
      status: 'sent',
      mediaId: draft.mediaId ?? null,
      mediaFilename: draft.filename ?? null,
      expiresAt: new Date(now.getTime() + 7 * 24 * 3600 * 1000).toISOString(),
    });
  });

  saveSession(db, session, 'quote_review', { ...session.context, quote: undefined });

  const gstNote = config.GST_ENABLED ? `\n_GST at ${config.DEFAULT_GST_RATE}% extra._` : '';

  enqueueMessage(db, session.customer.wa_phone, {
    kind: 'buttons',
    header: `Estimate ${stored.quote_number}`,
    body:
      `${explainQuote(quote, formatINR)}${gstNote}\n\n` +
      '⚠️ _This is an indicative estimate. We will check your model and confirm ' +
      'the final price — usually within a couple of hours._',
    buttons: [
      { id: `accept_quote:${stored.quote_number}`, title: 'Looks good' },
      { id: 'support', title: 'Discuss it' },
    ],
    footer: 'Valid for 7 days',
  });

  logger.info('quote.created', {
    quote: stored.quote_number,
    customer: session.customer.wa_phone,
    total: stored.total,
  });
}

/** Customer accepted an estimate — turn it into a payable order. */
async function acceptQuote(db: Db, session: Session, quoteNumber: string): Promise<void> {
  const quote = quotes.findByNumber(db, quoteNumber);
  if (!quote || quote.customer_id !== session.customer.id) {
    sendText(db, session.customer, `I could not find quote ${quoteNumber}.`);
    return;
  }
  if (quote.status === 'accepted') {
    const existing = orders.list(db, { customerId: session.customer.id, limit: 5 })
      .find((order) => order.quote_id === quote.id);
    if (existing) {
      await startPayment(db, session.customer, existing);
      return;
    }
  }

  const request = JSON.parse(quote.request_json) as QuoteRequest & { notes?: string };
  const material = findMaterial(request.materialKey);

  const created = createOrder(db, {
    customerId: session.customer.id,
    channel: 'whatsapp_quote',
    quoteId: quote.id,
    lines: [
      {
        description: `Custom 3D print — ${material?.name ?? request.materialKey}`,
        hsnCode: config.DEFAULT_HSN_CODE,
        quantity: request.quantity,
        unitPrice: quote.unit_price,
        priceIncludesTax: false,
        gstRate: config.DEFAULT_GST_RATE,
        meta: {
          material: request.materialKey,
          materialName: material?.name,
          weightGrams: request.weightGrams,
          printHours: request.printHours,
          quoteNumber: quote.quote_number,
          notes: request.notes,
        },
      },
    ],
    shippingAddress: formattedAddress(session.customer),
    customerNote: request.notes ?? null,
  });

  quotes.updateStatus(db, quote.id, 'accepted');

  if (!hasDeliverableAddress(session.customer)) {
    saveSession(db, session, 'awaiting_address', {
      ...session.context,
      pendingOrderId: created.order.id,
    });
    sendText(
      db,
      session.customer,
      `${orderSummary(db, created.order)}\n\n📍 *Where should we deliver this?*\n` +
        'Send your full address with the PIN code.',
    );
    return;
  }

  sendText(db, session.customer, orderSummary(db, created.order));
  await startPayment(db, session.customer, created.order);
}

// ─────────────────────────────────────────────────────────────────────────────
// Address and GSTIN capture
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Store a free-text address and resume whatever it was blocking.
 *
 * Rather than interrogating the customer field by field, we keep the address as
 * they wrote it and pull out the PIN code and state, which is all the tax
 * calculation actually needs.
 */
function saveAddressAndContinue(db: Db, session: Session, address: string): void {
  const pincode = /\b(\d{6})\b/.exec(address)?.[1] ?? null;
  const stateCode = detectStateCode(address);

  const updated = customers.upsertByPhone(db, {
    waPhone: session.customer.wa_phone,
    addressLine1: address.split('\n')[0]?.slice(0, 200) ?? address.slice(0, 200),
    addressLine2: address.split('\n').slice(1).join(', ').slice(0, 200) || null,
    pincode,
    ...(stateCode ? { stateCode, state: stateNameForCode(stateCode) } : {}),
  });

  const pendingOrderId = session.context.pendingOrderId;
  saveSession(db, { ...session, customer: updated }, 'idle', {
    ...session.context,
    pendingOrderId: undefined,
  });

  if (!pendingOrderId) {
    sendText(db, updated, 'Address saved ✅');
    return;
  }

  const order = orders.findById(db, pendingOrderId);
  if (!order) return;

  orders.setShippingAddress(db, order.id, address);

  // A different state changes the tax split, so the order is re-priced rather
  // than invoiced against a stale assumption.
  const detected = stateCode ?? updated.state_code;
  if (detected && detected !== order.place_of_supply_code) {
    logger.info('order.place_of_supply_changed', {
      order: order.order_number,
      from: order.place_of_supply_code,
      to: detected,
    });
    enqueueMessage(db, updated.wa_phone, {
      kind: 'text',
      text:
        'Address saved ✅\n\n_Delivering to ' +
        `${stateNameForCode(detected)} — your invoice will show the correct GST split._`,
    });
  } else {
    sendText(db, updated, 'Address saved ✅');
  }

  void requestPayment(db, order.id).catch((error: unknown) => {
    logger.error('payment.link_failed', {
      order: order.order_number,
      error: error instanceof Error ? error.message : String(error),
    });
  });
}

function captureGstin(db: Db, session: Session, text: string): void {
  const candidate = text.trim().toUpperCase().replace(/\s+/g, '');
  if (!isValidGstin(candidate)) {
    sendText(
      db,
      session.customer,
      "That does not look like a valid GSTIN. It is 15 characters, like *29ABCDE1234F1ZW*.\n\n" +
        '_Send *menu* to skip._',
    );
    return;
  }

  const stateCode = stateCodeFromGstin(candidate);
  const updated = customers.upsertByPhone(db, {
    waPhone: session.customer.wa_phone,
    gstin: candidate,
    ...(stateCode ? { stateCode, state: stateNameForCode(stateCode) } : {}),
  });

  saveSession(db, { ...session, customer: updated }, 'idle');
  sendText(
    db,
    updated,
    `GSTIN saved ✅\n\n*${candidate}*\n${stateCode ? stateNameForCode(stateCode) : ''}\n\n` +
      'Future invoices will carry it so you can claim input tax credit.',
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Outgoing messages
// ─────────────────────────────────────────────────────────────────────────────

export function sendMainMenu(db: Db, customer: CustomerRow, prefix?: string): void {
  const greeting = customer.name ? `Hi ${customer.name.split(' ')[0]}! 👋` : 'Hi! 👋';
  const body = [
    prefix ?? `${greeting}\n\nWelcome to *${seller.tradeName}* — 3D printing on demand.`,
    '',
    'What would you like to do?',
  ].join('\n');

  enqueueMessage(db, customer.wa_phone, {
    kind: 'list',
    header: seller.tradeName.slice(0, 60),
    body,
    buttonText: 'Open menu',
    sections: [
      {
        title: 'Shop',
        rows: [
          { id: 'catalog', title: '🛍️ Browse products', description: 'Ready-to-ship 3D printed items' },
          { id: 'quote', title: '📐 Custom print', description: 'Send your STL and get a quote' },
        ],
      },
      {
        title: 'My orders',
        rows: [
          { id: 'orders', title: '📦 My orders', description: 'Track a recent order' },
          { id: 'gstin', title: '🧾 Add GSTIN', description: 'For business invoices with ITC' },
        ],
      },
      {
        title: 'Help',
        rows: [{ id: 'support', title: '💬 Talk to a human', description: 'We usually reply in minutes' }],
      },
    ],
    footer: 'Reply *menu* any time',
  });
}

function sendCatalog(db: Db, customer: CustomerRow): void {
  const categories = products.categories(db);

  // With a live catalog id the native storefront is a far better experience
  // than a list of names — it carries images, prices and a real cart.
  if (config.WHATSAPP_CATALOG_ID) {
    enqueueMessage(db, customer.wa_phone, {
      kind: 'catalog',
      body:
        `*${seller.tradeName}* 🛍️\n\n` +
        'Tap below to browse everything we print, add what you like to your cart ' +
        'and send it back to me. I will take care of the invoice and delivery.',
      footer: 'Free delivery above ' + formatINR(config.FREE_DELIVERY_THRESHOLD * 100),
    });
    return;
  }

  // Fallback before Commerce Manager is connected.
  if (categories.length === 0) {
    sendText(db, customer, 'Our catalog is being updated right now — please check back shortly.');
    return;
  }

  enqueueMessage(db, customer.wa_phone, {
    kind: 'list',
    header: 'Our collections',
    body: 'Pick a collection to see what we have.',
    buttonText: 'View collections',
    sections: [
      {
        title: 'Collections',
        rows: categories.slice(0, 10).map((category) => ({
          id: `cat:${category}`,
          title: humanise(category).slice(0, 24),
        })),
      },
    ],
  });
}

function sendCategory(db: Db, customer: CustomerRow, category: string): void {
  const sections = buildProductSections(db, category);
  if (sections.length === 0) {
    sendText(db, customer, 'Nothing in that collection just now — try another one.');
    return;
  }

  if (config.WHATSAPP_CATALOG_ID) {
    enqueueMessage(db, customer.wa_phone, {
      kind: 'product_list',
      headerText: humanise(category),
      body: 'Tap any item to see details and add it to your cart.',
      sections,
      footer: seller.tradeName,
    });
    return;
  }

  const rows = products.listActive(db, category);
  const listing = rows
    .slice(0, 15)
    .map((product) => `• *${product.name}* — ${formatINR(product.price)}`)
    .join('\n');
  sendText(db, customer, `*${humanise(category)}*\n\n${listing}\n\n_Reply with a name to order._`);
}

function sendRecentOrders(db: Db, customer: CustomerRow): void {
  const recent = orders.list(db, { customerId: customer.id, limit: 5 });
  if (recent.length === 0) {
    sendMainMenu(db, customer, 'You have no orders with us yet — shall we fix that?');
    return;
  }

  enqueueMessage(db, customer.wa_phone, {
    kind: 'list',
    header: 'Your orders',
    body: 'Pick an order to see where it has reached.',
    buttonText: 'View orders',
    sections: [
      {
        title: 'Recent',
        rows: recent.map((order) => ({
          id: `status:${order.order_number}`,
          title: order.order_number.replace('ORD-', ''),
          description: `${formatINR(order.total)} · ${humanise(order.status)}`,
        })),
      },
    ],
  });
}

function sendOrderStatus(db: Db, customer: CustomerRow, orderNumber: string): void {
  const order = orders.findByNumber(db, orderNumber);
  if (!order || order.customer_id !== customer.id) {
    sendText(db, customer, `I could not find order ${orderNumber}.`);
    return;
  }

  const invoice = invoiceRepo.findByOrderId(db, order.id);
  const stage = STATUS_NARRATIVE[order.status] ?? order.status;

  const buttons: { id: string; title: string }[] = [];
  if (order.status === 'pending_payment') {
    buttons.push({ id: `pay:${order.order_number}`, title: 'Pay now' });
  }
  if (invoice) {
    buttons.push({ id: `invoice:${order.order_number}`, title: 'Get invoice' });
  }
  buttons.push({ id: 'support', title: 'Talk to us' });

  enqueueMessage(db, customer.wa_phone, {
    kind: 'buttons',
    header: order.order_number,
    body: `${orderSummary(db, order)}\n\n*Status:* ${stage}`,
    buttons: buttons.slice(0, 3),
  });
}

function sendInvoiceLink(db: Db, customer: CustomerRow, orderNumber: string): void {
  const order = orders.findByNumber(db, orderNumber);
  if (!order || order.customer_id !== customer.id) {
    sendText(db, customer, `I could not find order ${orderNumber}.`);
    return;
  }

  const invoice = invoiceRepo.findByOrderId(db, order.id);
  if (!invoice) {
    sendText(
      db,
      customer,
      'The invoice is raised once payment is confirmed. Pay for the order and it ' +
        'will arrive here automatically.',
    );
    return;
  }

  // Reuse the stored media id where we have one — no re-upload needed.
  enqueueMessage(
    db,
    customer.wa_phone,
    {
      kind: 'document',
      ...(invoice.whatsapp_media_id
        ? { mediaId: invoice.whatsapp_media_id }
        : { link: invoiceDownloadUrl(invoice) }),
      filename: `${invoice.invoice_number.replace(/[^A-Za-z0-9._-]/g, '-')}.pdf`,
      caption: `Invoice *${invoice.invoice_number}* for order ${order.order_number}`,
      invoiceId: invoice.id,
    },
    { dedupeKey: `invoice-resend:${invoice.invoice_number}:${Date.now()}`, orderId: order.id },
  );
}

const STATUS_NARRATIVE: Readonly<Record<string, string>> = Object.freeze({
  draft: 'Being prepared',
  pending_payment: '⏳ Waiting for payment',
  paid: '✅ Paid — queued for printing',
  in_production: '🖨️ On the printer',
  ready: '📦 Printed and packed',
  shipped: '🚚 On its way to you',
  delivered: '🎉 Delivered',
  cancelled: '❌ Cancelled',
  refunded: '↩️ Refunded',
});

function orderSummary(db: Db, order: OrderRow): string {
  const items = orders.items(db, order.id);
  const lines = items
    .map((item) => `• ${item.description} × ${item.quantity} — ${formatINR(item.line_total)}`)
    .join('\n');

  const parts = [`*Order ${order.order_number}*`, '', lines, ''];
  if (order.shipping > 0) parts.push(`Delivery: ${formatINR(order.shipping)}`);
  if (order.cgst + order.sgst > 0) {
    parts.push(`GST (CGST + SGST): ${formatINR(order.cgst + order.sgst)}`);
  } else if (order.igst > 0) {
    parts.push(`GST (IGST): ${formatINR(order.igst)}`);
  }
  parts.push(`*Total: ${formatINR(order.total)}*`);
  return parts.join('\n');
}

function sendText(db: Db, customer: CustomerRow, text: string): void {
  enqueueMessage(db, customer.wa_phone, { kind: 'text', text });
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function hasDeliverableAddress(customer: CustomerRow): boolean {
  return Boolean(customer.address_line1 && customer.pincode);
}

function formattedAddress(customer: CustomerRow): string | null {
  if (!customer.address_line1) return null;
  return [
    customer.legal_name ?? customer.name,
    customer.address_line1,
    customer.address_line2,
    [customer.city, customer.state, customer.pincode].filter(Boolean).join(', '),
  ]
    .filter(Boolean)
    .join('\n');
}

/**
 * Best-effort state detection from a free-text address, so the GST split is
 * right without asking the customer to pick from a 37-entry dropdown.
 */
function detectStateCode(address: string): string | null {
  const haystack = address.toLowerCase();
  let bestCode: string | null = null;
  let bestLength = 0;

  for (const [code, name] of Object.entries(GST_STATE_CODES)) {
    const needle = name.toLowerCase();
    // Longest match wins so "Andhra Pradesh" is not shadowed by "Pradesh".
    if (haystack.includes(needle) && needle.length > bestLength) {
      bestCode = code;
      bestLength = needle.length;
    }
  }

  // A handful of common city names carry their state unambiguously.
  if (!bestCode) {
    for (const [city, code] of Object.entries(CITY_STATE_HINTS)) {
      if (haystack.includes(city)) return code;
    }
  }
  return bestCode;
}

const CITY_STATE_HINTS: Readonly<Record<string, string>> = Object.freeze({
  bengaluru: '29',
  bangalore: '29',
  mysuru: '29',
  mysore: '29',
  mumbai: '27',
  pune: '27',
  nagpur: '27',
  chennai: '33',
  coimbatore: '33',
  hyderabad: '36',
  kolkata: '19',
  ahmedabad: '24',
  surat: '24',
  jaipur: '08',
  lucknow: '09',
  noida: '09',
  gurugram: '06',
  gurgaon: '06',
  kochi: '32',
  cochin: '32',
  thiruvananthapuram: '32',
  bhubaneswar: '21',
  indore: '23',
  bhopal: '23',
  chandigarh: '04',
  patna: '10',
  guwahati: '18',
  raipur: '22',
  dehradun: '05',
  ranchi: '20',
  goa: '30',
  panaji: '30',
  vijayawada: '37',
  visakhapatnam: '37',
});

function humanise(value: string): string {
  return value.replace(/[_-]+/g, ' ').replace(/\b\w/g, (character) => character.toUpperCase());
}

function splitOnce(value: string, separator: string): [string, string] {
  const index = value.indexOf(separator);
  if (index === -1) return [value, ''];
  return [value.slice(0, index), value.slice(index + separator.length)];
}
