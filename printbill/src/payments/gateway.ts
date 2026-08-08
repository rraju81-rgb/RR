/**
 * Payment gateway abstraction.
 *
 * Everything upstream of this file talks in terms of "create a link for this
 * order" and "here is a verified event". Swapping Razorpay for Cashfree, PhonePe
 * or Stripe means adding one file that satisfies this interface — the order and
 * invoice services never learn which gateway is in use.
 */
import type { Paise } from '../domain/money.js';

export interface CreateLinkRequest {
  readonly orderId: number;
  readonly orderNumber: string;
  readonly amount: Paise;
  readonly currency: string;
  readonly description: string;
  readonly customer: {
    readonly name?: string | null;
    readonly email?: string | null;
    /** E.164 with the leading '+', as gateways expect. */
    readonly contact: string;
  };
  /** Where the gateway sends the customer after payment. */
  readonly callbackUrl?: string;
  readonly expiresInMinutes?: number;
  /** Round-trip metadata; the webhook must return our order number here. */
  readonly notes?: Readonly<Record<string, string>>;
}

export interface PaymentLink {
  readonly providerLinkId: string;
  readonly shortUrl: string;
  readonly amount: Paise;
  readonly status: string;
  readonly expiresAt: string | null;
  readonly raw: unknown;
}

export type PaymentEventKind =
  | 'payment.captured'
  | 'payment.failed'
  | 'link.paid'
  | 'refund.processed'
  | 'ignored';

/** A gateway webhook, normalised to the shape the order service understands. */
export interface PaymentEvent {
  readonly kind: PaymentEventKind;
  /** Unique per event — the idempotency key for webhook replay. */
  readonly eventId: string;
  readonly providerPaymentId: string | null;
  readonly providerLinkId: string | null;
  /** Our order number, recovered from the gateway's notes. */
  readonly orderNumber: string | null;
  readonly amount: Paise | null;
  readonly currency: string | null;
  readonly method: string | null;
  readonly raw: unknown;
}

export interface PaymentGateway {
  readonly name: string;
  createPaymentLink(request: CreateLinkRequest): Promise<PaymentLink>;
  /**
   * Verify the signature over the *raw* request body and parse the event.
   * Throws `SignatureVerificationError` when the signature does not match —
   * an unverified webhook must never be allowed to mark an order paid.
   */
  parseWebhook(rawBody: Buffer, headers: Record<string, string | undefined>): PaymentEvent;
  /** Optional out-of-band check for reconciliation. */
  fetchPaymentStatus?(providerPaymentId: string): Promise<{ status: string; amount: Paise }>;
}

export class SignatureVerificationError extends Error {
  override readonly name = 'SignatureVerificationError';
}

export class GatewayError extends Error {
  override readonly name = 'GatewayError';
  constructor(
    message: string,
    readonly status?: number,
    readonly body?: unknown,
  ) {
    super(message);
  }
}
