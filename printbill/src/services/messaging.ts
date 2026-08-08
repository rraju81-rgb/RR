/**
 * Outbound WhatsApp messaging, via a durable outbox.
 *
 * Nothing sends inline. A payment webhook that tried to call the WhatsApp API
 * directly would either block the gateway's retry timeout or lose the invoice
 * when Meta returns a 503. Instead the webhook commits a row and returns 200;
 * the worker delivers it, with backoff, and keeps trying across restarts.
 */
import { type Db, nowIso } from '../db/index.js';
import { outbox } from '../db/repositories.js';
import type { OutboxRow } from '../db/types.js';
import { WhatsAppApiError, type WhatsAppClient, getWhatsAppClient } from '../whatsapp/client.js';
import { logger } from '../lib/logger.js';

/** The message shapes the worker knows how to deliver. */
export type OutboundMessage =
  | { kind: 'text'; text: string; previewUrl?: boolean }
  | {
      kind: 'buttons';
      body: string;
      buttons: { id: string; title: string }[];
      header?: string;
      footer?: string;
    }
  | {
      kind: 'list';
      body: string;
      buttonText: string;
      sections: { title: string; rows: { id: string; title: string; description?: string }[] }[];
      header?: string;
      footer?: string;
    }
  | { kind: 'catalog'; body: string; footer?: string; thumbnailProductRetailerId?: string }
  | { kind: 'product'; productRetailerId: string; body?: string; footer?: string }
  | {
      kind: 'product_list';
      headerText: string;
      body: string;
      footer?: string;
      sections: { title: string; productRetailerIds: string[] }[];
    }
  | { kind: 'image'; link: string; caption?: string }
  | {
      kind: 'document';
      /** Local file to upload at send time. Preferred for invoices. */
      filePath?: string;
      mediaId?: string;
      link?: string;
      filename: string;
      caption?: string;
      /** Written back onto the invoice so a resend skips the upload. */
      invoiceId?: number;
    }
  | { kind: 'template'; name: string; languageCode?: string; components?: unknown[] };

export interface EnqueueOptions {
  /** Suppresses a duplicate enqueue of the same logical message. */
  readonly dedupeKey?: string;
  readonly orderId?: number;
}

/** Queue a message. Returns null when `dedupeKey` matched an existing row. */
export function enqueueMessage(
  db: Db,
  toPhone: string,
  message: OutboundMessage,
  options: EnqueueOptions = {},
): OutboxRow | null {
  return outbox.enqueue(db, {
    toPhone: normalisePhone(toPhone),
    kind: message.kind,
    payload: message,
    dedupeKey: options.dedupeKey ?? null,
    orderId: options.orderId ?? null,
  });
}

/**
 * WhatsApp wants an E.164 number with no '+' and no separators.
 * Indian numbers keyed without a country code get 91 prefixed — a 10-digit
 * number is otherwise silently undeliverable.
 */
export function normalisePhone(input: string): string {
  const digits = input.replace(/\D/g, '');
  if (digits.length === 10) return `91${digits}`;
  if (digits.length === 11 && digits.startsWith('0')) return `91${digits.slice(1)}`;
  return digits;
}

const MAX_ATTEMPTS = 6;

/** Exponential backoff with a ceiling: 30s, 1m, 2m, 4m, 8m, 15m. */
function backoffSeconds(attempt: number): number {
  return Math.min(30 * 2 ** attempt, 900);
}

export interface DispatchResult {
  readonly processed: number;
  readonly sent: number;
  readonly failed: number;
}

/**
 * Deliver every message whose retry time has come.
 *
 * Permanent failures (a malformed payload, a number that is not on WhatsApp,
 * a closed 24-hour window) are abandoned immediately rather than retried —
 * repeating them cannot succeed and costs API quota.
 */
export async function dispatchOutbox(
  db: Db,
  options: { client?: WhatsAppClient; limit?: number } = {},
): Promise<DispatchResult> {
  const client = options.client ?? getWhatsAppClient();
  const due = outbox.due(db, options.limit ?? 20);

  let sent = 0;
  let failed = 0;

  for (const row of due) {
    try {
      const message = JSON.parse(row.payload_json) as OutboundMessage;
      const result = await deliver(db, client, row.to_phone, message);
      outbox.markSent(db, row.id, result.messageId);
      sent += 1;
    } catch (error) {
      failed += 1;
      const permanent =
        error instanceof WhatsAppApiError ? error.permanent : error instanceof SyntaxError;
      const attempts = row.attempts + 1;
      const giveUp = permanent || attempts >= MAX_ATTEMPTS;

      const nextAttemptAt = giveUp
        ? null
        : new Date(Date.now() + backoffSeconds(attempts) * 1000).toISOString();

      outbox.markFailed(db, row.id, describeError(error), nextAttemptAt);
      logger.warn('outbox.delivery_failed', {
        id: row.id,
        to: row.to_phone,
        kind: row.kind,
        attempts,
        giveUp,
        error: describeError(error),
      });
    }
  }

  return { processed: due.length, sent, failed };
}

async function deliver(
  db: Db,
  client: WhatsAppClient,
  to: string,
  message: OutboundMessage,
): Promise<{ messageId: string | null }> {
  switch (message.kind) {
    case 'text':
      return client.sendText(to, message.text, message.previewUrl ?? false);

    case 'buttons':
      return client.sendButtons(to, {
        body: message.body,
        buttons: message.buttons,
        ...(message.header ? { header: message.header } : {}),
        ...(message.footer ? { footer: message.footer } : {}),
      });

    case 'list':
      return client.sendList(to, {
        body: message.body,
        buttonText: message.buttonText,
        sections: message.sections,
        ...(message.header ? { header: message.header } : {}),
        ...(message.footer ? { footer: message.footer } : {}),
      });

    case 'catalog':
      return client.sendCatalog(to, {
        body: message.body,
        ...(message.footer ? { footer: message.footer } : {}),
        ...(message.thumbnailProductRetailerId
          ? { thumbnailProductRetailerId: message.thumbnailProductRetailerId }
          : {}),
      });

    case 'product':
      return client.sendProduct(to, {
        productRetailerId: message.productRetailerId,
        ...(message.body ? { body: message.body } : {}),
        ...(message.footer ? { footer: message.footer } : {}),
      });

    case 'product_list':
      return client.sendProductList(to, {
        headerText: message.headerText,
        body: message.body,
        sections: message.sections,
        ...(message.footer ? { footer: message.footer } : {}),
      });

    case 'image':
      return client.sendImage(to, message.link, message.caption);

    case 'document': {
      let mediaId = message.mediaId;
      if (!mediaId && message.filePath) {
        // Upload lazily, at delivery time, so a queued invoice picks up a
        // re-rendered PDF rather than a stale upload.
        const { readFileSync } = await import('node:fs');
        const bytes = readFileSync(message.filePath);
        mediaId = await client.uploadMedia(bytes, message.filename, 'application/pdf');

        if (message.invoiceId) {
          db.prepare('UPDATE invoices SET whatsapp_media_id = ? WHERE id = ?').run(
            mediaId,
            message.invoiceId,
          );
        }
      }

      const result = await client.sendDocument(to, {
        ...(mediaId ? { mediaId } : { link: message.link }),
        filename: message.filename,
        ...(message.caption ? { caption: message.caption } : {}),
      });

      if (message.invoiceId) {
        db.prepare('UPDATE invoices SET sent_at = ?, whatsapp_media_id = ? WHERE id = ?').run(
          nowIso(),
          mediaId ?? null,
          message.invoiceId,
        );
      }
      return result;
    }

    case 'template':
      return client.sendTemplate(to, {
        name: message.name,
        ...(message.languageCode ? { languageCode: message.languageCode } : {}),
        ...(message.components ? { components: message.components } : {}),
      });

    default: {
      const exhaustive: never = message;
      throw new Error(`Unsupported outbound message: ${JSON.stringify(exhaustive)}`);
    }
  }
}

function describeError(error: unknown): string {
  if (error instanceof Error) return `${error.name}: ${error.message}`;
  return String(error);
}

/** Background loop that drains the outbox. Returns a stop function. */
export function startOutboxWorker(
  db: Db,
  options: { intervalMs?: number; client?: WhatsAppClient } = {},
): () => void {
  const intervalMs = options.intervalMs ?? 5000;
  let stopped = false;
  let running = false;

  const tick = async (): Promise<void> => {
    if (stopped || running) return;
    running = true;
    try {
      const result = await dispatchOutbox(db, options.client ? { client: options.client } : {});
      if (result.processed > 0) {
        logger.info('outbox.dispatched', result);
      }
    } catch (error) {
      logger.error('outbox.worker_error', { error: describeError(error) });
    } finally {
      running = false;
    }
  };

  const timer = setInterval(() => void tick(), intervalMs);
  // Do not hold the process open purely for the poll timer.
  timer.unref?.();

  return () => {
    stopped = true;
    clearInterval(timer);
  };
}
