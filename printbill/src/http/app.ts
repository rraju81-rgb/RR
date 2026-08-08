/**
 * HTTP surface.
 *
 * Four kinds of route, with deliberately different trust levels:
 *   /webhooks/*   — unauthenticated but cryptographically verified
 *   /invoices/:token — unauthenticated, guarded by an unguessable token
 *   /api/admin/*  — API-key protected
 *   /admin, /pay  — static pages
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express, { type NextFunction, type Request, type Response } from 'express';
import type { Db } from '../db/index.js';
import { config } from '../config/env.js';
import { logger } from '../lib/logger.js';
import { registerWhatsAppWebhook } from './routes/whatsapp.js';
import { registerPaymentWebhook } from './routes/payments.js';
import { registerAdminRoutes } from './routes/admin.js';
import { registerPublicRoutes } from './routes/public.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.resolve(here, '../../public');

export function createApp(db: Db): express.Express {
  const app = express();

  app.disable('x-powered-by');
  // Behind a reverse proxy (ngrok, nginx, Fly) so req.ip and req.protocol are honest.
  app.set('trust proxy', true);

  app.use((request, response, next) => {
    const startedAt = Date.now();
    response.on('finish', () => {
      // Webhook bodies carry customer data; log the shape, not the contents.
      logger.debug('http.request', {
        method: request.method,
        path: request.path,
        status: response.statusCode,
        ms: Date.now() - startedAt,
      });
    });
    next();
  });

  app.get('/health', (_request, response) => {
    response.json({ status: 'ok', time: new Date().toISOString() });
  });

  // Webhooks are registered before the JSON body parser: signature checks need
  // the raw bytes, and a parsed-then-reserialised body will not verify.
  registerWhatsAppWebhook(app, db);
  registerPaymentWebhook(app, db);

  app.use(express.json({ limit: '1mb' }));
  app.use(express.urlencoded({ extended: false }));

  registerPublicRoutes(app, db);
  registerAdminRoutes(app, db);

  app.use('/static', express.static(path.join(PUBLIC_DIR, 'static'), { maxAge: '1h' }));
  app.use('/admin', express.static(path.join(PUBLIC_DIR, 'admin')));

  app.use((_request, response) => {
    response.status(404).json({ error: 'not_found' });
  });

  app.use((error: Error, _request: Request, response: Response, _next: NextFunction) => {
    logger.error('http.unhandled', { error: error.message, stack: error.stack });
    response.status(500).json({
      error: 'internal_error',
      // Never leak internals to a caller in production.
      ...(config.isProduction ? {} : { message: error.message }),
    });
  });

  return app;
}
