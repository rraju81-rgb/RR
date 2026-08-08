/**
 * SQLite connection and schema bootstrap.
 *
 * better-sqlite3 is synchronous, which suits this workload: the write paths are
 * short transactions triggered by webhooks, and synchronous access removes a
 * whole class of interleaving bug from the payment → invoice sequence.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Database from 'better-sqlite3';
import { config } from '../config/env.js';

const here = path.dirname(fileURLToPath(import.meta.url));

export type Db = Database.Database;

let instance: Db | null = null;

export function getDb(): Db {
  if (instance) return instance;
  instance = openDatabase(config.DATABASE_PATH);
  return instance;
}

export function openDatabase(databasePath: string): Db {
  if (databasePath !== ':memory:') {
    fs.mkdirSync(path.dirname(path.resolve(databasePath)), { recursive: true });
  }
  const db = new Database(databasePath);

  // WAL lets the outbox worker read while a webhook writes.
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  // Wait rather than throw SQLITE_BUSY when two writers collide.
  db.pragma('busy_timeout = 5000');

  applySchema(db);
  return db;
}

export function applySchema(db: Db): void {
  const schemaPath = path.join(here, 'schema.sql');
  const schema = fs.readFileSync(schemaPath, 'utf8');
  db.exec(schema);
}

/** Close the shared connection. Used by tests and graceful shutdown. */
export function closeDb(): void {
  instance?.close();
  instance = null;
}

/**
 * Run `fn` inside an IMMEDIATE transaction.
 *
 * IMMEDIATE takes the write lock up front, so two concurrent webhook handlers
 * allocating an invoice number cannot both read the same counter value and then
 * fight over the write.
 */
export function transaction<T>(db: Db, fn: () => T): T {
  const run = db.transaction(fn);
  return run.immediate();
}

/**
 * Allocate the next value of a named counter.
 * Must be called inside a transaction that also persists whatever consumes it,
 * otherwise a failure downstream leaves a gap in the sequence.
 */
export function nextCounterValue(db: Db, name: string): number {
  db.prepare(
    `INSERT INTO counters (name, value) VALUES (?, 0)
     ON CONFLICT (name) DO NOTHING`,
  ).run(name);

  const row = db
    .prepare(
      `UPDATE counters SET value = value + 1 WHERE name = ?
       RETURNING value`,
    )
    .get(name) as { value: number } | undefined;

  if (!row) throw new Error(`Failed to allocate counter "${name}"`);
  return row.value;
}

export function getSetting(db: Db, key: string): string | null {
  const row = db.prepare('SELECT value FROM settings WHERE key = ?').get(key) as
    | { value: string }
    | undefined;
  return row?.value ?? null;
}

export function setSetting(db: Db, key: string, value: string): void {
  db.prepare(
    `INSERT INTO settings (key, value, updated_at)
     VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
     ON CONFLICT (key) DO UPDATE SET
       value = excluded.value,
       updated_at = excluded.updated_at`,
  ).run(key, value);
}

/** ISO-8601 UTC, matching the format SQLite writes for defaults. */
export function nowIso(): string {
  return new Date().toISOString();
}
