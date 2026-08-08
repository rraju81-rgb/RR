/**
 * Structured logging.
 *
 * One line of JSON per event in production so a log shipper can index it;
 * something readable at a terminal in development. Values known to carry
 * secrets are redacted centrally rather than at each call site.
 */
import { config } from '../config/env.js';

/** Any plain object of structured fields; readonly result types qualify. */
export type LogContext = object;

type Level = 'debug' | 'info' | 'warn' | 'error';

const LEVEL_ORDER: Record<Level, number> = { debug: 10, info: 20, warn: 30, error: 40 };
const MINIMUM: Level = config.isProduction ? 'info' : 'debug';

const REDACT_KEYS = new Set([
  'access_token',
  'accessToken',
  'authorization',
  'password',
  'secret',
  'signature',
  'key_secret',
  'webhookSecret',
  'download_token',
  'downloadToken',
]);

function redact(value: unknown, depth = 0): unknown {
  if (depth > 4 || value === null || typeof value !== 'object') return value;
  if (Array.isArray(value)) return value.map((entry) => redact(entry, depth + 1));

  const output: Record<string, unknown> = {};
  for (const [key, entry] of Object.entries(value)) {
    output[key] = REDACT_KEYS.has(key) ? '[redacted]' : redact(entry, depth + 1);
  }
  return output;
}

function emit(level: Level, event: string, context?: LogContext): void {
  if (LEVEL_ORDER[level] < LEVEL_ORDER[MINIMUM]) return;

  const payload = {
    time: new Date().toISOString(),
    level,
    event,
    ...(context ? (redact(context) as Record<string, unknown>) : {}),
  };

  const line = config.isProduction
    ? JSON.stringify(payload)
    : `${payload.time} ${level.toUpperCase().padEnd(5)} ${event}${
        context ? ` ${JSON.stringify(redact(context))}` : ''
      }`;

  if (level === 'error') console.error(line);
  else if (level === 'warn') console.warn(line);
  else console.log(line);
}

export const logger = {
  debug: (event: string, context?: LogContext) => emit('debug', event, context),
  info: (event: string, context?: LogContext) => emit('info', event, context),
  warn: (event: string, context?: LogContext) => emit('warn', event, context),
  error: (event: string, context?: LogContext) => emit('error', event, context),
};
