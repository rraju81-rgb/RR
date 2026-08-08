/** Process entrypoint: open the database, start the server and the outbox worker. */
import { closeDb, getDb } from './db/index.js';
import { config } from './config/env.js';
import { createApp } from './http/app.js';
import { startOutboxWorker } from './services/messaging.js';
import { logger } from './lib/logger.js';

const db = getDb();
const app = createApp(db);
const stopWorker = startOutboxWorker(db);

const server = app.listen(config.PORT, () => {
  logger.info('server.started', {
    port: config.PORT,
    baseUrl: config.PUBLIC_BASE_URL,
    gateway: config.PAYMENT_PROVIDER,
    gstEnabled: config.GST_ENABLED,
    whatsapp: config.WHATSAPP_PHONE_NUMBER_ID ? 'configured' : 'not configured',
  });
});

/**
 * Drain in-flight requests before exiting. A webhook cut off mid-settlement
 * would be retried by the gateway, but a clean close avoids the duplicate.
 */
function shutdown(signal: string): void {
  logger.info('server.shutting_down', { signal });
  stopWorker();
  server.close(() => {
    closeDb();
    process.exit(0);
  });
  // Do not hang forever on a stuck connection.
  setTimeout(() => process.exit(1), 10_000).unref();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

process.on('unhandledRejection', (reason) => {
  logger.error('process.unhandled_rejection', { reason: String(reason) });
});
