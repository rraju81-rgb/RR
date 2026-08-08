/**
 * Razorpay gateway: payment links + webhook verification.
 *
 * Payment Links are the right primitive for WhatsApp selling — a link is a URL
 * we can paste into a chat, it renders a hosted checkout covering UPI, cards,
 * netbanking and wallets, and it reports back over a webhook. No SDK is used;
 * the two endpoints involved are simple enough that owning the calls keeps the
 * dependency surface (and its supply chain) small.
 */
import crypto from 'node:crypto';
import { config } from '../config/env.js';
import type { Paise } from '../domain/money.js';
import {
  type CreateLinkRequest,
  GatewayError,
  type PaymentEvent,
  type PaymentGateway,
  type PaymentLink,
  SignatureVerificationError,
} from './gateway.js';

const API_BASE = 'https://api.razorpay.com/v1';

export interface RazorpayOptions {
  keyId?: string;
  keySecret?: string;
  webhookSecret?: string;
  transport?: (url: string, init: RequestInit) => Promise<Response>;
}

interface RazorpayLinkResponse {
  id: string;
  short_url: string;
  amount: number;
  status: string;
  expire_by?: number;
}

export class RazorpayGateway implements PaymentGateway {
  readonly name = 'razorpay';

  private readonly keyId: string;
  private readonly keySecret: string;
  private readonly webhookSecret: string;
  private readonly transport: (url: string, init: RequestInit) => Promise<Response>;

  constructor(options: RazorpayOptions = {}) {
    this.keyId = options.keyId ?? config.RAZORPAY_KEY_ID;
    this.keySecret = options.keySecret ?? config.RAZORPAY_KEY_SECRET;
    this.webhookSecret = options.webhookSecret ?? config.RAZORPAY_WEBHOOK_SECRET;
    this.transport = options.transport ?? ((url, init) => fetch(url, init));
  }

  private get authHeader(): string {
    const token = Buffer.from(`${this.keyId}:${this.keySecret}`).toString('base64');
    return `Basic ${token}`;
  }

  async createPaymentLink(request: CreateLinkRequest): Promise<PaymentLink> {
    if (!this.keyId || !this.keySecret) {
      throw new GatewayError('Razorpay credentials are not configured');
    }

    const body: Record<string, unknown> = {
      // Razorpay works in paise, which is exactly how we store money.
      amount: request.amount,
      currency: request.currency,
      accept_partial: false,
      description: request.description.slice(0, 2048),
      customer: {
        name: request.customer.name ?? undefined,
        email: request.customer.email ?? undefined,
        contact: request.customer.contact,
      },
      // The customer is already in WhatsApp; a duplicate SMS is noise.
      notify: { sms: false, email: Boolean(request.customer.email) },
      reminder_enable: true,
      // Notes survive the round trip and carry our order number back.
      notes: {
        order_number: request.orderNumber,
        order_id: String(request.orderId),
        ...request.notes,
      },
      ...(request.callbackUrl
        ? { callback_url: request.callbackUrl, callback_method: 'get' }
        : {}),
    };

    if (request.expiresInMinutes) {
      // expire_by is a Unix timestamp in seconds; Razorpay requires >= 15 min out.
      const minimumMinutes = Math.max(15, request.expiresInMinutes);
      body.expire_by = Math.floor(Date.now() / 1000) + minimumMinutes * 60;
    }

    const response = await this.transport(`${API_BASE}/payment_links`, {
      method: 'POST',
      headers: {
        Authorization: this.authHeader,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const text = await response.text();
    const parsed: unknown = text ? safeJsonParse(text) : null;

    if (!response.ok) {
      throw new GatewayError(
        `Razorpay payment link failed: ${describeError(parsed) ?? text}`,
        response.status,
        parsed,
      );
    }

    const link = parsed as RazorpayLinkResponse;
    return {
      providerLinkId: link.id,
      shortUrl: link.short_url,
      amount: link.amount as Paise,
      status: link.status,
      expiresAt: link.expire_by ? new Date(link.expire_by * 1000).toISOString() : null,
      raw: parsed,
    };
  }

  /**
   * Verify `X-Razorpay-Signature`, an HMAC-SHA256 of the raw request body keyed
   * with the webhook secret.
   *
   * The signature is computed over the exact bytes Razorpay sent, so the route
   * must hand us the raw buffer — re-serialising a parsed body reorders keys and
   * invalidates the digest.
   */
  parseWebhook(rawBody: Buffer, headers: Record<string, string | undefined>): PaymentEvent {
    if (!this.webhookSecret) {
      throw new SignatureVerificationError('RAZORPAY_WEBHOOK_SECRET is not configured');
    }

    const signature = headers['x-razorpay-signature'];
    if (!signature) {
      throw new SignatureVerificationError('Missing X-Razorpay-Signature header');
    }

    const expected = crypto
      .createHmac('sha256', this.webhookSecret)
      .update(rawBody)
      .digest('hex');

    if (!timingSafeEqualHex(expected, signature)) {
      throw new SignatureVerificationError('Razorpay webhook signature mismatch');
    }

    const payload = JSON.parse(rawBody.toString('utf8')) as RazorpayWebhookBody;
    return normaliseEvent(payload, headers);
  }

  async fetchPaymentStatus(providerPaymentId: string): Promise<{ status: string; amount: Paise }> {
    const response = await this.transport(`${API_BASE}/payments/${providerPaymentId}`, {
      method: 'GET',
      headers: { Authorization: this.authHeader },
    });
    if (!response.ok) {
      throw new GatewayError(`Razorpay payment fetch failed`, response.status, await response.text());
    }
    const payment = (await response.json()) as { status: string; amount: number };
    return { status: payment.status, amount: payment.amount as Paise };
  }
}

interface RazorpayEntity {
  id?: string;
  amount?: number;
  amount_paid?: number;
  currency?: string;
  method?: string;
  status?: string;
  notes?: Record<string, string>;
  order_id?: string;
  payment_id?: string;
}

interface RazorpayWebhookBody {
  event?: string;
  created_at?: number;
  payload?: {
    payment?: { entity?: RazorpayEntity };
    payment_link?: { entity?: RazorpayEntity };
    refund?: { entity?: RazorpayEntity };
  };
}

/**
 * Map a Razorpay event onto the gateway-neutral shape.
 *
 * `payment_link.paid` and `payment.captured` both fire for a link payment; both
 * are translated, and the dedupe on `provider_payment_id` downstream ensures the
 * order is credited exactly once regardless of which lands first.
 */
function normaliseEvent(
  body: RazorpayWebhookBody,
  headers: Record<string, string | undefined>,
): PaymentEvent {
  const event = body.event ?? 'unknown';
  const payment = body.payload?.payment?.entity;
  const link = body.payload?.payment_link?.entity;
  const refund = body.payload?.refund?.entity;

  const orderNumber =
    link?.notes?.order_number ?? payment?.notes?.order_number ?? refund?.notes?.order_number ?? null;

  // Razorpay sends an event id header on every delivery; fall back to a
  // deterministic composite so a redelivery without it still dedupes.
  const eventId =
    headers['x-razorpay-event-id'] ??
    `${event}:${payment?.id ?? link?.id ?? refund?.id ?? 'unknown'}`;

  const base = {
    eventId,
    providerPaymentId: payment?.id ?? refund?.payment_id ?? null,
    providerLinkId: link?.id ?? null,
    orderNumber,
    currency: payment?.currency ?? link?.currency ?? 'INR',
    method: payment?.method ?? null,
    raw: body,
  };

  switch (event) {
    case 'payment.captured':
      return { ...base, kind: 'payment.captured', amount: (payment?.amount ?? 0) as Paise };
    case 'payment.failed':
      return { ...base, kind: 'payment.failed', amount: (payment?.amount ?? 0) as Paise };
    case 'payment_link.paid':
      return {
        ...base,
        kind: 'link.paid',
        // amount_paid is authoritative on a link; amount is what was asked for.
        amount: (link?.amount_paid ?? link?.amount ?? payment?.amount ?? 0) as Paise,
      };
    case 'refund.processed':
    case 'refund.created':
      return { ...base, kind: 'refund.processed', amount: (refund?.amount ?? 0) as Paise };
    default:
      return { ...base, kind: 'ignored', amount: null };
  }
}

/** Constant-time comparison that tolerates a length mismatch without throwing. */
function timingSafeEqualHex(expected: string, received: string): boolean {
  const a = Buffer.from(expected, 'utf8');
  const b = Buffer.from(received, 'utf8');
  if (a.length !== b.length) {
    // Still burn a comparison so the timing does not reveal the length.
    crypto.timingSafeEqual(a, a);
    return false;
  }
  return crypto.timingSafeEqual(a, b);
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function describeError(body: unknown): string | null {
  if (typeof body !== 'object' || body === null) return null;
  const error = (body as { error?: { description?: unknown } }).error;
  return typeof error?.description === 'string' ? error.description : null;
}
