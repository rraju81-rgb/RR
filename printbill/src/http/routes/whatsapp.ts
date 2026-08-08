/**
 * WhatsApp webhook route.
 *
 * Meta retries any delivery that is not answered with a 200 within a few
 * seconds, and repeated failures get the subscription disabled. So this handler
 * verifies, acknowledges, and only then processes — the conversation logic runs
 * after the response has been sent, backed by the outbox for anything outbound.
 */
import express, { type Express } from 'express';
import type { Db } from '../../db/index.js';
import { config } from '../../config/env.js';
import { logger } from '../../lib/logger.js';
import { handleEvent } from '../../whatsapp/flows.js';
import {
  WebhookSignatureError,
  parseWebhookPayload,
  verifySignature,
  verifySubscription,
} from '../../whatsapp/webhook.js';

export function registerWhatsAppWebhook(app: Express, db: Db): void {
  // Subscription handshake performed once, when the webhook URL is saved in the
  // Meta app dashboard.
  app.get('/webhooks/whatsapp', (request, response) => {
    try {
      const challenge = verifySubscription(request.query as Record<string, unknown>);
      logger.info('whatsapp.webhook_verified');
      response.status(200).type('text/plain').send(challenge);
    } catch (error) {
      logger.warn('whatsapp.webhook_verification_failed', {
        error: error instanceof Error ? error.message : String(error),
      });
      response.sendStatus(403);
    }
  });

  app.post(
    '/webhooks/whatsapp',
    express.raw({ type: '*/*', limit: '5mb' }),
    (request, response) => {
      const rawBody = Buffer.isBuffer(request.body) ? request.body : Buffer.from('');

      try {
        verifySignature(rawBody, request.get('x-hub-signature-256'));
      } catch (error) {
        // In development the signature is skipped only when no secret is set,
        // so a misconfigured production deployment still rejects.
        if (config.WHATSAPP_APP_SECRET || config.isProduction) {
          logger.warn('whatsapp.bad_signature', {
            error: error instanceof WebhookSignatureError ? error.message : String(error),
          });
          response.sendStatus(401);
          return;
        }
        logger.warn('whatsapp.signature_skipped', { reason: 'WHATSAPP_APP_SECRET not set' });
      }

      let payload: unknown;
      try {
        payload = JSON.parse(rawBody.toString('utf8'));
      } catch {
        // Malformed JSON will never parse on retry; 200 stops the redelivery loop.
        logger.warn('whatsapp.malformed_payload');
        response.sendStatus(200);
        return;
      }

      // Acknowledge first. Anything slower risks a duplicate delivery, and the
      // inbound message table already guards against processing one twice.
      response.sendStatus(200);

      const events = parseWebhookPayload(payload);
      void (async () => {
        for (const event of events) {
          try {
            await handleEvent(db, event);
          } catch (error) {
            logger.error('whatsapp.handler_error', {
              type: event.type,
              error: error instanceof Error ? error.message : String(error),
              stack: error instanceof Error ? error.stack : undefined,
            });
          }
        }
      })();
    },
  );
}
