/**
 * WhatsApp webhook: signature verification and payload normalisation.
 *
 * Meta's envelope is deeply nested and every field is optional, so this module
 * flattens a delivery into a list of plain events. Parsing lives apart from the
 * conversation logic, which lets the flow tests feed events directly.
 */
import crypto from 'node:crypto';
import { config } from '../config/env.js';
import type { Paise } from '../domain/money.js';

export class WebhookSignatureError extends Error {
  override readonly name = 'WebhookSignatureError';
}

/**
 * Verify `X-Hub-Signature-256`: `sha256=<hmac of the raw body with the app secret>`.
 *
 * Must run against the exact bytes received. Express's JSON parser would give
 * us a re-serialised object whose key order and whitespace differ, producing a
 * different digest, so the route captures the raw buffer.
 */
export function verifySignature(
  rawBody: Buffer,
  signatureHeader: string | undefined,
  appSecret: string = config.WHATSAPP_APP_SECRET,
): void {
  if (!appSecret) {
    throw new WebhookSignatureError('WHATSAPP_APP_SECRET is not configured');
  }
  if (!signatureHeader) {
    throw new WebhookSignatureError('Missing X-Hub-Signature-256 header');
  }

  const expected = `sha256=${crypto
    .createHmac('sha256', appSecret)
    .update(rawBody)
    .digest('hex')}`;

  const a = Buffer.from(expected, 'utf8');
  const b = Buffer.from(signatureHeader, 'utf8');
  if (a.length !== b.length) {
    crypto.timingSafeEqual(a, a);
    throw new WebhookSignatureError('Signature length mismatch');
  }
  if (!crypto.timingSafeEqual(a, b)) {
    throw new WebhookSignatureError('Signature mismatch');
  }
}

/** Meta's subscription handshake: echo `hub.challenge` when the token matches. */
export function verifySubscription(query: Record<string, unknown>): string {
  const mode = query['hub.mode'];
  const token = query['hub.verify_token'];
  const challenge = query['hub.challenge'];

  if (mode === 'subscribe' && token === config.WHATSAPP_VERIFY_TOKEN) {
    return String(challenge ?? '');
  }
  throw new WebhookSignatureError('Webhook verification token mismatch');
}

// ─────────────────────────────────────────────────────────────────────────────
// Normalised events
// ─────────────────────────────────────────────────────────────────────────────

export interface InboundBase {
  readonly messageId: string;
  readonly from: string;
  readonly timestamp: string;
  readonly contactName: string | null;
  readonly raw: unknown;
}

export interface TextEvent extends InboundBase {
  readonly type: 'text';
  readonly text: string;
}

/** A tapped reply button or list row. `id` is what we set when sending. */
export interface InteractiveEvent extends InboundBase {
  readonly type: 'interactive';
  readonly replyId: string;
  readonly title: string;
}

export interface OrderProduct {
  readonly productRetailerId: string;
  readonly quantity: number;
  /** Minor units. Meta sends major units, converted here at the boundary. */
  readonly itemPrice: Paise;
  readonly currency: string;
}

/** A cart submitted from the in-chat storefront. */
export interface CartEvent extends InboundBase {
  readonly type: 'order';
  readonly catalogId: string;
  readonly products: readonly OrderProduct[];
  readonly note: string | null;
}

/** A model file or reference image sent for a custom quote. */
export interface MediaEvent extends InboundBase {
  readonly type: 'media';
  readonly mediaKind: 'document' | 'image' | 'video' | 'audio';
  readonly mediaId: string;
  readonly filename: string | null;
  readonly mimeType: string | null;
  readonly caption: string | null;
}

export interface LocationEvent extends InboundBase {
  readonly type: 'location';
  readonly latitude: number;
  readonly longitude: number;
  readonly address: string | null;
}

/** Delivery/read receipts for messages we sent. */
export interface StatusEvent {
  readonly type: 'status';
  readonly messageId: string;
  readonly recipient: string;
  readonly status: string;
  readonly timestamp: string;
  readonly errorMessage: string | null;
  readonly raw: unknown;
}

export interface UnsupportedEvent extends InboundBase {
  readonly type: 'unsupported';
  readonly messageType: string;
}

export type InboundEvent =
  | TextEvent
  | InteractiveEvent
  | CartEvent
  | MediaEvent
  | LocationEvent
  | StatusEvent
  | UnsupportedEvent;

interface MetaValue {
  contacts?: { profile?: { name?: string }; wa_id?: string }[];
  messages?: MetaMessage[];
  statuses?: MetaStatus[];
}

interface MetaMessage {
  id?: string;
  from?: string;
  timestamp?: string;
  type?: string;
  text?: { body?: string };
  interactive?: {
    type?: string;
    button_reply?: { id?: string; title?: string };
    list_reply?: { id?: string; title?: string; description?: string };
  };
  button?: { payload?: string; text?: string };
  order?: {
    catalog_id?: string;
    text?: string;
    product_items?: {
      product_retailer_id?: string;
      quantity?: number | string;
      item_price?: number | string;
      currency?: string;
    }[];
  };
  document?: { id?: string; filename?: string; mime_type?: string; caption?: string };
  image?: { id?: string; mime_type?: string; caption?: string };
  video?: { id?: string; mime_type?: string; caption?: string };
  audio?: { id?: string; mime_type?: string };
  location?: { latitude?: number; longitude?: number; address?: string; name?: string };
}

interface MetaStatus {
  id?: string;
  recipient_id?: string;
  status?: string;
  timestamp?: string;
  errors?: { title?: string; message?: string }[];
}

/** Flatten a webhook delivery into normalised events. */
export function parseWebhookPayload(payload: unknown): InboundEvent[] {
  const events: InboundEvent[] = [];
  const body = payload as {
    entry?: { changes?: { value?: MetaValue }[] }[];
  };

  for (const entry of body?.entry ?? []) {
    for (const change of entry.changes ?? []) {
      const value = change.value;
      if (!value) continue;

      const contactName = value.contacts?.[0]?.profile?.name ?? null;

      for (const message of value.messages ?? []) {
        const parsed = parseMessage(message, contactName);
        if (parsed) events.push(parsed);
      }

      for (const status of value.statuses ?? []) {
        events.push({
          type: 'status',
          messageId: status.id ?? '',
          recipient: status.recipient_id ?? '',
          status: status.status ?? 'unknown',
          timestamp: status.timestamp ?? '',
          errorMessage: status.errors?.[0]?.message ?? null,
          raw: status,
        });
      }
    }
  }

  return events;
}

function parseMessage(message: MetaMessage, contactName: string | null): InboundEvent | null {
  const base: InboundBase = {
    messageId: message.id ?? '',
    from: message.from ?? '',
    timestamp: message.timestamp ?? '',
    contactName,
    raw: message,
  };
  if (!base.messageId || !base.from) return null;

  switch (message.type) {
    case 'text':
      return { ...base, type: 'text', text: message.text?.body ?? '' };

    case 'interactive': {
      const reply = message.interactive?.button_reply ?? message.interactive?.list_reply;
      if (!reply?.id) return { ...base, type: 'unsupported', messageType: 'interactive' };
      return { ...base, type: 'interactive', replyId: reply.id, title: reply.title ?? '' };
    }

    // A tap on a template's quick-reply button.
    case 'button':
      return {
        ...base,
        type: 'interactive',
        replyId: message.button?.payload ?? message.button?.text ?? '',
        title: message.button?.text ?? '',
      };

    case 'order': {
      const items = message.order?.product_items ?? [];
      return {
        ...base,
        type: 'order',
        catalogId: message.order?.catalog_id ?? '',
        note: message.order?.text ?? null,
        products: items.map((item) => ({
          productRetailerId: String(item.product_retailer_id ?? ''),
          quantity: Number(item.quantity ?? 1),
          // Meta reports item_price in major units ("249.00"); we store paise.
          itemPrice: Math.round(Number(item.item_price ?? 0) * 100) as Paise,
          currency: item.currency ?? 'INR',
        })),
      };
    }

    case 'document':
      return {
        ...base,
        type: 'media',
        mediaKind: 'document',
        mediaId: message.document?.id ?? '',
        filename: message.document?.filename ?? null,
        mimeType: message.document?.mime_type ?? null,
        caption: message.document?.caption ?? null,
      };

    case 'image':
      return {
        ...base,
        type: 'media',
        mediaKind: 'image',
        mediaId: message.image?.id ?? '',
        filename: null,
        mimeType: message.image?.mime_type ?? null,
        caption: message.image?.caption ?? null,
      };

    case 'location':
      return {
        ...base,
        type: 'location',
        latitude: Number(message.location?.latitude ?? 0),
        longitude: Number(message.location?.longitude ?? 0),
        address: message.location?.address ?? message.location?.name ?? null,
      };

    default:
      return { ...base, type: 'unsupported', messageType: message.type ?? 'unknown' };
  }
}
