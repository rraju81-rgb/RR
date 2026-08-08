/**
 * Payment gateway webhook.
 *
 * This is the most security-sensitive route in the system: whoever can post a
 * convincing body here can mark orders paid. Three defences, in order:
 *   1. HMAC signature over the raw bytes, verified before anything is parsed
 *   2. event-id deduplication, so a replay of a *valid* body is inert
 *   3. amount and order matching inside the settlement service
 */
import express, { type Express } from 'express';
import type { Db } from '../../db/index.js';
import { webhookEvents } from '../../db/repositories.js';
import { SignatureVerificationError } from '../../payments/gateway.js';
import { getGateway } from '../../payments/index.js';
import { settlePayment } from '../../services/checkout.js';
import { logger } from '../../lib/logger.js';

export function registerPaymentWebhook(app: Express, db: Db): void {
  app.post(
    '/webhooks/payments',
    express.raw({ type: '*/*', limit: '1mb' }),
    async (request, response) => {
      const rawBody = Buffer.isBuffer(request.body) ? request.body : Buffer.from('');
      const gateway = getGateway();

      let event;
      try {
        event = gateway.parseWebhook(rawBody, request.headers as Record<string, string | undefined>);
      } catch (error) {
        if (error instanceof SignatureVerificationError) {
          logger.warn('payment.bad_signature', { error: error.message, ip: request.ip });
          response.sendStatus(401);
          return;
        }
        logger.warn('payment.unparseable', {
          error: error instanceof Error ? error.message : String(error),
        });
        // Valid signature but unreadable body — retrying will not help.
        response.sendStatus(400);
        return;
      }

      // Claim the event. A repeat delivery of an event we already handled is
      // acknowledged without touching the order again.
      const claimed = webhookEvents.claim(db, gateway.name, event.eventId, event.kind, event.raw);
      if (!claimed) {
        logger.info('payment.event_replayed', { eventId: event.eventId });
        response.status(200).json({ status: 'already_processed' });
        return;
      }

      try {
        const result = await settlePayment(db, event);
        webhookEvents.markProcessed(db, gateway.name, event.eventId);
        logger.info('payment.settled', {
          eventId: event.eventId,
          kind: event.kind,
          status: result.status,
          order: result.order?.order_number,
          invoice: result.invoice?.invoice_number,
        });
        response.status(200).json({ status: result.status });
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        webhookEvents.markProcessed(db, gateway.name, event.eventId, message);
        logger.error('payment.settlement_failed', { eventId: event.eventId, error: message });
        // 500 asks the gateway to retry; the claim row is already marked with
        // the error, and `settlePayment` is idempotent, so a retry is safe.
        response.status(500).json({ error: 'settlement_failed' });
      }
    },
  );
}
