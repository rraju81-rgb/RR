/** Push the local product table to the WhatsApp Commerce catalog. */
import { closeDb, getDb } from '../db/index.js';
import { config } from '../config/env.js';
import { syncCatalog } from '../services/catalog.js';
import { logger } from '../lib/logger.js';

const dryRun = process.argv.includes('--dry-run') || !config.WHATSAPP_CATALOG_ID;

if (!config.WHATSAPP_CATALOG_ID) {
  logger.warn('catalog.no_catalog_id', {
    hint: 'Set WHATSAPP_CATALOG_ID to push for real. Running as a dry run.',
  });
}

const db = getDb();

try {
  const result = await syncCatalog(db, { dryRun });
  logger.info('catalog.sync_complete', { dryRun, ...result });
} catch (error) {
  logger.error('catalog.sync_failed', {
    error: error instanceof Error ? error.message : String(error),
  });
  process.exitCode = 1;
} finally {
  closeDb();
}
