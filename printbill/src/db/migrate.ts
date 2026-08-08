/** Create the database file and apply the schema. Safe to re-run. */
import { closeDb, getDb } from './index.js';
import { config } from '../config/env.js';
import { logger } from '../lib/logger.js';

const db = getDb();
const tables = db
  .prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
  .all() as { name: string }[];

logger.info('db.migrated', {
  path: config.DATABASE_PATH,
  tables: tables.map((table) => table.name),
});

closeDb();
