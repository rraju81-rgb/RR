/**
 * Customer-facing routes: invoice download, the payment return page, and the
 * mock checkout used before a real gateway is connected.
 */
import fs from 'node:fs';
import type { Express } from 'express';
import type { Db } from '../../db/index.js';
import { invoices, orders, products } from '../../db/repositories.js';
import { config, seller } from '../../config/env.js';
import { formatINR } from '../../domain/money.js';
import { MockGateway } from '../../payments/mock.js';
import { renderInvoice } from '../../services/invoices.js';
import { logger } from '../../lib/logger.js';
import { escapeHtml, page } from '../views.js';

export function registerPublicRoutes(app: Express, db: Db): void {
  /**
   * Invoice download by token.
   *
   * The token is 24 random bytes, so the URL is safe to paste into a chat, but
   * it is still a bearer credential: no directory listing, no enumeration, and
   * the PDF is streamed rather than redirected to a file path.
   */
  app.get('/invoices/:token', async (request, response) => {
    const invoice = invoices.findByToken(db, request.params.token);
    if (!invoice) {
      response.status(404).type('html').send(page('Invoice not found', notFoundBody()));
      return;
    }

    try {
      const { filePath } = await renderInvoice(db, invoice);
      if (!fs.existsSync(filePath)) {
        response.status(500).json({ error: 'invoice_render_failed' });
        return;
      }
      response.setHeader('Content-Type', 'application/pdf');
      response.setHeader(
        'Content-Disposition',
        `inline; filename="${invoice.invoice_number.replace(/[^A-Za-z0-9._-]/g, '-')}.pdf"`,
      );
      // Tokens are permanent; the document never changes once issued.
      response.setHeader('Cache-Control', 'private, max-age=86400');
      fs.createReadStream(filePath).pipe(response);
    } catch (error) {
      logger.error('invoice.download_failed', {
        invoice: invoice.invoice_number,
        error: error instanceof Error ? error.message : String(error),
      });
      response.status(500).json({ error: 'invoice_render_failed' });
    }
  });

  /** Product landing page — the `url` each catalog item points at. */
  app.get('/p/:retailerId', (request, response) => {
    const product = products.findByRetailerId(db, request.params.retailerId);
    if (!product || !product.is_active) {
      response.status(404).type('html').send(page('Not found', notFoundBody()));
      return;
    }

    const waLink = seller.phone
      ? `https://wa.me/${seller.phone.replace(/\D/g, '')}?text=${encodeURIComponent(
          `Hi! I'd like to order: ${product.name}`,
        )}`
      : '#';

    response.type('html').send(
      page(
        product.name,
        `<article class="card">
          ${
            product.image_url
              ? `<img class="hero" src="${escapeHtml(product.image_url)}" alt="${escapeHtml(product.name)}">`
              : ''
          }
          <h1>${escapeHtml(product.name)}</h1>
          <p class="price">${formatINR(product.price)} <span class="muted">incl. GST</span></p>
          <p>${escapeHtml(product.description)}</p>
          <a class="button" href="${waLink}">Order on WhatsApp</a>
          <p class="muted small">Sold by ${escapeHtml(seller.tradeName)}</p>
        </article>`,
      ),
    );
  });

  /** Where the gateway sends the customer back after paying. */
  app.get('/pay/return', (request, response) => {
    const orderNumber = String(request.query.order ?? '');
    response.type('html').send(
      page(
        'Payment received',
        `<article class="card center">
          <div class="tick">✓</div>
          <h1>Thank you!</h1>
          <p>We are confirming your payment${
            orderNumber ? ` for <strong>${escapeHtml(orderNumber)}</strong>` : ''
          }.</p>
          <p class="muted">Your GST invoice will arrive on WhatsApp within a few moments.
          You can close this window.</p>
        </article>`,
      ),
    );
  });

  // ── Mock checkout ────────────────────────────────────────────────────────
  // Only mounted when the mock gateway is active, so it can never become a way
  // to mark a real order paid.
  if (config.PAYMENT_PROVIDER !== 'mock') return;

  app.get('/pay/mock/:orderNumber', (request, response) => {
    const order = orders.findByNumber(db, request.params.orderNumber);
    if (!order) {
      response.status(404).type('html').send(page('Order not found', notFoundBody()));
      return;
    }

    const due = order.total - order.amount_paid;
    response.type('html').send(
      page(
        `Pay ${order.order_number}`,
        `<article class="card">
          <p class="muted small">TEST CHECKOUT — no money moves</p>
          <h1>${formatINR(due)}</h1>
          <p>Order <strong>${escapeHtml(order.order_number)}</strong> · ${escapeHtml(
            seller.tradeName,
          )}</p>
          <form method="POST" action="/pay/mock/${encodeURIComponent(order.order_number)}/confirm">
            <label>Payment method
              <select name="method">
                <option value="upi">UPI</option>
                <option value="card">Card</option>
                <option value="netbanking">Net banking</option>
                <option value="wallet">Wallet</option>
              </select>
            </label>
            <button class="button" type="submit">Pay now</button>
          </form>
          <form method="POST" action="/pay/mock/${encodeURIComponent(order.order_number)}/confirm">
            <input type="hidden" name="outcome" value="fail">
            <button class="button ghost" type="submit">Simulate failure</button>
          </form>
        </article>`,
      ),
    );
  });

  /**
   * Post a correctly signed webhook to our own endpoint, exercising the real
   * verification and settlement path rather than shortcutting it.
   */
  app.post('/pay/mock/:orderNumber/confirm', async (request, response) => {
    const order = orders.findByNumber(db, request.params.orderNumber);
    if (!order) {
      response.status(404).json({ error: 'unknown_order' });
      return;
    }

    const body = request.body as { method?: string; outcome?: string };
    const gateway = new MockGateway();
    const payload = {
      event: body.outcome === 'fail' ? 'payment.failed' : 'payment.captured',
      eventId: `mock_evt_${Date.now()}_${order.order_number}`,
      paymentId: `pay_mock_${Date.now()}`,
      orderNumber: order.order_number,
      amount: order.total - order.amount_paid,
      method: body.method ?? 'upi',
    };
    const signed = gateway.signPayload(payload);

    const result = await fetch(`${config.PUBLIC_BASE_URL}/webhooks/payments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Mock-Signature': signed.signature,
      },
      body: signed.body,
    });

    if (!result.ok) {
      response.status(502).type('html').send(
        page('Payment failed', `<article class="card center"><h1>Something went wrong</h1>
          <p class="muted">The webhook was rejected (${result.status}).</p></article>`),
      );
      return;
    }

    response.redirect(`/pay/return?order=${encodeURIComponent(order.order_number)}`);
  });
}

function notFoundBody(): string {
  return `<article class="card center">
    <h1>Not found</h1>
    <p class="muted">This link may have expired. Message us on WhatsApp and we will help.</p>
  </article>`;
}
