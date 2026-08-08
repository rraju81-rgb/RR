/**
 * A gateway that takes no money.
 *
 * It exists so the whole order → pay → invoice → WhatsApp path can be exercised
 * end to end before Razorpay credentials are issued, and so the test suite has a
 * deterministic gateway. It signs its own webhooks with APP_SECRET, using the
 * same HMAC discipline as the real thing, so the verification path is genuinely
 * covered rather than stubbed out.
 */
import crypto from 'node:crypto';
import { config } from '../config/env.js';
import type { Paise } from '../domain/money.js';
import {
  type CreateLinkRequest,
  type PaymentEvent,
  type PaymentGateway,
  type PaymentLink,
  SignatureVerificationError,
} from './gateway.js';

export class MockGateway implements PaymentGateway {
  readonly name = 'mock';
  private counter = 0;

  constructor(private readonly secret: string = config.APP_SECRET) {}

  async createPaymentLink(request: CreateLinkRequest): Promise<PaymentLink> {
    this.counter += 1;
    const id = `plink_mock_${Date.now()}_${this.counter}`;
    // Points at the local simulator page, which posts a signed webhook back.
    const shortUrl = `${config.PUBLIC_BASE_URL}/pay/mock/${encodeURIComponent(
      request.orderNumber,
    )}`;
    return {
      providerLinkId: id,
      shortUrl,
      amount: request.amount,
      status: 'created',
      expiresAt: null,
      raw: { mock: true, orderNumber: request.orderNumber },
    };
  }

  parseWebhook(rawBody: Buffer, headers: Record<string, string | undefined>): PaymentEvent {
    const signature = headers['x-mock-signature'];
    if (!signature) throw new SignatureVerificationError('Missing X-Mock-Signature header');

    const expected = crypto.createHmac('sha256', this.secret).update(rawBody).digest('hex');
    const a = Buffer.from(expected, 'utf8');
    const b = Buffer.from(signature, 'utf8');
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
      throw new SignatureVerificationError('Mock webhook signature mismatch');
    }

    const body = JSON.parse(rawBody.toString('utf8')) as {
      event?: string;
      eventId?: string;
      paymentId?: string;
      linkId?: string;
      orderNumber?: string;
      amount?: number;
      method?: string;
    };

    return {
      kind: body.event === 'payment.failed' ? 'payment.failed' : 'payment.captured',
      eventId: body.eventId ?? `mock:${body.paymentId ?? crypto.randomUUID()}`,
      providerPaymentId: body.paymentId ?? null,
      providerLinkId: body.linkId ?? null,
      orderNumber: body.orderNumber ?? null,
      amount: (body.amount ?? null) as Paise | null,
      currency: 'INR',
      method: body.method ?? 'upi',
      raw: body,
    };
  }

  /** Helper for tests and the simulator page: build a correctly signed body. */
  signPayload(payload: unknown): { body: string; signature: string } {
    const body = JSON.stringify(payload);
    const signature = crypto.createHmac('sha256', this.secret).update(body).digest('hex');
    return { body, signature };
  }
}
