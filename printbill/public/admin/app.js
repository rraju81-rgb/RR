/**
 * PrintBill admin console.
 *
 * Plain ES modules, no build step — the operator opens /admin, pastes the API
 * key, and works. The key lives in sessionStorage so it is gone when the tab
 * closes rather than sitting in localStorage indefinitely.
 */
'use strict';

const state = {
  key: sessionStorage.getItem('printbill_key') || '',
  materials: [],
};

// ── API ─────────────────────────────────────────────────────────────────────

async function api(path, options = {}) {
  const response = await fetch(`/api/admin${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': state.key,
      ...(options.headers || {}),
    },
  });

  if (response.status === 401) {
    lock();
    throw new Error('Unauthorized');
  }
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(body?.error || `Request failed (${response.status})`);
  }
  return body;
}

// ── Formatting ──────────────────────────────────────────────────────────────

/** Paise → "₹1,234.56", with Indian digit grouping. */
function money(paise) {
  const value = (paise || 0) / 100;
  return `₹${value.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function when(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function humanise(value) {
  return String(value || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character],
  );
}

function badge(status) {
  return `<span class="badge ${escapeHtml(status)}">${humanise(status)}</span>`;
}

function toast(message, bad = false) {
  const element = document.getElementById('toast');
  element.textContent = message;
  element.className = `toast${bad ? ' bad' : ''}`;
  element.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => {
    element.hidden = true;
  }, 3200);
}

function table(headers, rows) {
  if (rows.length === 0) return '<div class="empty">Nothing here yet.</div>';
  return `<div class="table-wrap"><table>
    <thead><tr>${headers.map((header) => `<th>${header}</th>`).join('')}</tr></thead>
    <tbody>${rows.join('')}</tbody>
  </table></div>`;
}

// ── Auth ────────────────────────────────────────────────────────────────────

function unlock() {
  document.getElementById('gate').hidden = true;
  document.getElementById('app').hidden = false;
  refresh();
}

function lock() {
  sessionStorage.removeItem('printbill_key');
  state.key = '';
  document.getElementById('gate').hidden = false;
  document.getElementById('app').hidden = true;
}

document.getElementById('key-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const error = document.getElementById('gate-error');
  error.hidden = true;
  state.key = document.getElementById('api-key').value.trim();

  try {
    await api('/summary');
    sessionStorage.setItem('printbill_key', state.key);
    unlock();
  } catch {
    error.textContent = 'That key was not accepted.';
    error.hidden = false;
  }
});

document.getElementById('lock').addEventListener('click', lock);

// ── Navigation ──────────────────────────────────────────────────────────────

const LOADERS = {
  dashboard: loadDashboard,
  orders: loadOrders,
  products: loadProducts,
  quotes: loadQuotes,
  pricing: loadPricing,
  outbox: loadOutbox,
};

function show(view) {
  for (const tab of document.querySelectorAll('.tab')) {
    tab.classList.toggle('active', tab.dataset.view === view);
  }
  for (const section of document.querySelectorAll('.view')) {
    section.classList.toggle('active', section.id === `view-${view}`);
  }
  LOADERS[view]?.();
}

for (const tab of document.querySelectorAll('.tab')) {
  tab.addEventListener('click', () => show(tab.dataset.view));
}
document.addEventListener('click', (event) => {
  const link = event.target.closest('[data-view-link]');
  if (link) show(link.dataset.viewLink);
});

function refresh() {
  loadDashboard();
  loadMaterials();
}

// ── Dashboard ───────────────────────────────────────────────────────────────

async function loadDashboard() {
  const summary = await api('/summary');

  const pending = summary.byStatus.find((row) => row.status === 'pending_payment');
  const production = summary.byStatus.filter((row) =>
    ['paid', 'in_production'].includes(row.status),
  );

  document.getElementById('stats').innerHTML = [
    stat('Collected', money(summary.revenue.paid)),
    stat('Today', `${summary.today.orders} order${summary.today.orders === 1 ? '' : 's'}`),
    stat('Awaiting payment', pending ? pending.count : 0),
    stat('In the workshop', production.reduce((total, row) => total + row.count, 0)),
  ].join('');

  const outboxPending =
    summary.outbox.find((row) => row.status === 'pending')?.count || 0;
  const outboxFailed =
    summary.outbox.find((row) => row.status === 'abandoned')?.count || 0;

  document.getElementById('checks').innerHTML = [
    check(summary.whatsappConnected, 'WhatsApp Business API', 'Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID'),
    check(summary.catalogConnected, 'Commerce catalog', 'Set WHATSAPP_CATALOG_ID to enable the in-chat storefront'),
    check(summary.gateway !== 'mock', `Payment gateway (${summary.gateway})`, 'Running on the mock gateway — no real money moves'),
    check(summary.gstEnabled, 'GST invoicing', 'Issuing bills of supply (GST disabled)'),
    check(summary.pendingInvoices === 0, 'Invoices up to date', `${summary.pendingInvoices} paid order(s) without an invoice`),
    check(outboxFailed === 0, `Message queue (${outboxPending} pending)`, `${outboxFailed} message(s) abandoned`),
  ].join('');

  const orders = await api('/orders?limit=8');
  document.getElementById('recent-orders').innerHTML = ordersTable(orders);
}

function stat(label, value) {
  return `<div class="stat"><div class="label">${label}</div><div class="value">${value}</div></div>`;
}

function check(ok, label, hint) {
  return `<div class="check">
    <span class="dot ${ok ? 'on' : 'off'}"></span>
    <span>${escapeHtml(label)}</span>
    ${ok ? '' : `<span class="muted small">— ${escapeHtml(hint)}</span>`}
  </div>`;
}

// ── Orders ──────────────────────────────────────────────────────────────────

function ordersTable(orders) {
  return table(
    ['Order', 'Customer', 'Total', 'Status', 'Invoice', 'Placed', ''],
    orders.map(
      (order) => `<tr>
        <td><strong>${escapeHtml(order.order_number)}</strong></td>
        <td>${escapeHtml(order.customer?.name || `+${order.customer?.wa_phone || ''}`)}</td>
        <td class="num">${money(order.total)}</td>
        <td>${badge(order.status)}</td>
        <td class="small">${
          order.invoice
            ? `<a href="/invoices/${order.invoice.download_token}" target="_blank" rel="noopener">${escapeHtml(order.invoice.invoice_number)}</a>`
            : '—'
        }</td>
        <td class="small muted">${when(order.created_at)}</td>
        <td><button class="btn small" data-order="${order.id}">Open</button></td>
      </tr>`,
    ),
  );
}

async function loadOrders() {
  const status = document.getElementById('order-filter').value;
  const orders = await api(`/orders?limit=100${status ? `&status=${status}` : ''}`);
  document.getElementById('orders-list').innerHTML = ordersTable(orders);
}

document.getElementById('order-filter').addEventListener('change', loadOrders);

document.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-order]');
  if (button) await openOrder(button.dataset.order);
});

const NEXT_STATUS = {
  pending_payment: ['paid', 'cancelled'],
  paid: ['in_production', 'cancelled'],
  in_production: ['ready', 'cancelled'],
  ready: ['shipped', 'delivered'],
  shipped: ['delivered'],
  delivered: [],
  cancelled: [],
  refunded: [],
  draft: ['pending_payment', 'cancelled'],
};

async function openOrder(id) {
  const data = await api(`/orders/${id}`);
  const { order, items, customer, invoice, payments, events } = data;

  const actions = (NEXT_STATUS[order.status] || [])
    .map(
      (status) =>
        `<button class="btn small" data-set-status="${order.id}" data-status="${status}">
           Mark ${humanise(status)}
         </button>`,
    )
    .join('');

  openModal(
    order.order_number,
    `
    <dl class="kv">
      <dt>Customer</dt><dd>${escapeHtml(customer?.name || '')} · +${escapeHtml(customer?.wa_phone || '')}</dd>
      <dt>Status</dt><dd>${badge(order.status)}</dd>
      <dt>Place of supply</dt><dd>${escapeHtml(order.place_of_supply_name)} (${escapeHtml(order.place_of_supply_code)}) · ${humanise(order.tax_kind)}</dd>
      <dt>Delivery address</dt><dd>${escapeHtml(order.shipping_address || '—').replace(/\n/g, '<br>')}</dd>
      ${customer?.gstin ? `<dt>Buyer GSTIN</dt><dd>${escapeHtml(customer.gstin)}</dd>` : ''}
    </dl>

    <h3 style="margin-top:16px">Items</h3>
    ${table(
      ['Description', 'HSN', 'Qty', 'Rate', 'Taxable', 'Tax', 'Total'],
      items.map(
        (item) => `<tr>
          <td>${escapeHtml(item.description)}</td>
          <td class="small">${escapeHtml(item.hsn_code)}</td>
          <td class="num">${item.quantity}</td>
          <td class="num">${money(item.unit_price)}</td>
          <td class="num">${money(item.taxable_value)}</td>
          <td class="num">${money(item.cgst + item.sgst + item.igst)}</td>
          <td class="num">${money(item.line_total)}</td>
        </tr>`,
      ),
    )}

    <dl class="kv" style="margin-top:14px">
      <dt>Taxable value</dt><dd>${money(order.subtotal)}</dd>
      ${order.shipping ? `<dt>Delivery</dt><dd>${money(order.shipping)}</dd>` : ''}
      ${order.cgst ? `<dt>CGST + SGST</dt><dd>${money(order.cgst + order.sgst)}</dd>` : ''}
      ${order.igst ? `<dt>IGST</dt><dd>${money(order.igst)}</dd>` : ''}
      ${order.round_off ? `<dt>Round off</dt><dd>${money(order.round_off)}</dd>` : ''}
      <dt><strong>Total</strong></dt><dd><strong>${money(order.total)}</strong></dd>
      <dt>Paid</dt><dd>${money(order.amount_paid)}</dd>
    </dl>

    ${
      payments.length > 0
        ? `<h3 style="margin-top:16px">Payments</h3>${table(
            ['Provider', 'Reference', 'Method', 'Amount', 'When'],
            payments.map(
              (payment) => `<tr>
                <td>${escapeHtml(payment.provider)}</td>
                <td class="small">${escapeHtml(payment.provider_payment_id)}</td>
                <td>${escapeHtml(payment.method || '—')}</td>
                <td class="num">${money(payment.amount)}</td>
                <td class="small muted">${when(payment.created_at)}</td>
              </tr>`,
            ),
          )}`
        : ''
    }

    <h3 style="margin-top:16px">History</h3>
    <ul class="timeline">
      ${events
        .map(
          (item) =>
            `<li><strong>${humanise(item.event)}</strong>
             ${item.detail ? `<span class="muted">— ${escapeHtml(item.detail)}</span>` : ''}
             <span class="muted small"> · ${when(item.created_at)}</span></li>`,
        )
        .join('')}
    </ul>

    <div class="row" style="margin-top:18px">
      ${actions}
      ${
        order.status === 'pending_payment'
          ? `<button class="btn small" data-paylink="${order.id}">Resend payment link</button>
             <button class="btn small" data-markpaid="${order.id}">Record offline payment</button>`
          : ''
      }
      ${
        invoice
          ? `<a class="btn small" href="/invoices/${invoice.download_token}" target="_blank" rel="noopener">Open invoice</a>
             <button class="btn small" data-resend-invoice="${invoice.id}">Resend on WhatsApp</button>`
          : ''
      }
    </div>
  `,
  );
}

document.addEventListener('click', async (event) => {
  const setStatus = event.target.closest('[data-set-status]');
  if (setStatus) {
    const status = setStatus.dataset.status;
    let detail;
    if (status === 'shipped') {
      detail = prompt('Tracking details to send the customer (optional):') || undefined;
    }
    await guard(async () => {
      await api(`/orders/${setStatus.dataset.setStatus}/status`, {
        method: 'POST',
        body: JSON.stringify({ status, detail }),
      });
      toast(`Order marked ${humanise(status)}`);
      closeModal();
      loadOrders();
      loadDashboard();
    });
  }

  const payLink = event.target.closest('[data-paylink]');
  if (payLink) {
    await guard(async () => {
      const link = await api(`/orders/${payLink.dataset.paylink}/payment-link`, {
        method: 'POST',
        body: JSON.stringify({ force: true }),
      });
      toast(`Payment link sent: ${link.shortUrl}`);
    });
  }

  const markPaid = event.target.closest('[data-markpaid]');
  if (markPaid) {
    const method = prompt('Payment method (cash / upi / bank transfer):', 'upi');
    if (!method) return;
    await guard(async () => {
      await api(`/orders/${markPaid.dataset.markpaid}/mark-paid`, {
        method: 'POST',
        body: JSON.stringify({ method }),
      });
      toast('Payment recorded — invoice issued and queued for WhatsApp');
      closeModal();
      loadOrders();
      loadDashboard();
    });
  }

  const resend = event.target.closest('[data-resend-invoice]');
  if (resend) {
    await guard(async () => {
      await api(`/invoices/${resend.dataset.resendInvoice}/resend`, { method: 'POST' });
      toast('Invoice queued for delivery');
    });
  }
});

// ── Products ────────────────────────────────────────────────────────────────

async function loadProducts() {
  const products = await api('/products');
  document.getElementById('products-list').innerHTML = table(
    ['Product', 'Category', 'Price', 'HSN', 'GST', 'Stock', 'Synced', ''],
    products.map(
      (product) => `<tr>
        <td>
          <strong>${escapeHtml(product.name)}</strong>
          <div class="muted small">${escapeHtml(product.retailer_id)}</div>
        </td>
        <td class="small">${humanise(product.category)}</td>
        <td class="num">${money(product.price)}</td>
        <td class="small">${escapeHtml(product.hsn_code)}</td>
        <td class="num small">${product.gst_rate}%</td>
        <td class="num small">${product.stock_quantity ?? 'Made to order'}</td>
        <td class="small muted">${product.catalog_synced_at ? when(product.catalog_synced_at) : 'Not synced'}</td>
        <td>
          <button class="btn small" data-toggle-product="${product.id}" data-active="${product.is_active}">
            ${product.is_active ? 'Hide' : 'Show'}
          </button>
        </td>
      </tr>`,
    ),
  );
}

document.addEventListener('click', async (event) => {
  const toggle = event.target.closest('[data-toggle-product]');
  if (toggle) {
    await guard(async () => {
      await api(`/products/${toggle.dataset.toggleProduct}/active`, {
        method: 'POST',
        body: JSON.stringify({ isActive: toggle.dataset.active !== '1' }),
      });
      loadProducts();
    });
  }
});

document.getElementById('sync-catalog').addEventListener('click', async () => {
  await guard(async () => {
    const result = await api('/catalog/sync', { method: 'POST', body: '{}' });
    toast(`Catalog synced — ${result.pushed} live, ${result.removed} removed`);
    loadProducts();
  });
});

document.getElementById('new-product-btn').addEventListener('click', () => {
  openModal(
    'Add product',
    `<form id="product-form" class="grid">
      <label class="span">Name<input name="name" required placeholder="Custom Name Plate"></label>
      <label class="span">Description<textarea name="description" rows="2"></textarea></label>
      <label>Product ID<input name="retailerId" required placeholder="nameplate-classic" pattern="[a-z0-9_-]+"></label>
      <label>Category<input name="category" value="general"></label>
      <label>Price ₹ (incl. GST)<input name="price" type="number" step="1" min="0" required></label>
      <label>GST %<input name="gstRate" type="number" step="0.5" value="18"></label>
      <label>HSN<input name="hsnCode" value="3926"></label>
      <label>Stock (blank = made to order)<input name="stockQuantity" type="number" min="0"></label>
      <label class="span">Image URL<input name="imageUrl" type="url" placeholder="https://..."></label>
      <button class="btn primary span" type="submit">Save product</button>
    </form>`,
  );

  document.getElementById('product-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const payload = {
      retailerId: form.get('retailerId'),
      name: form.get('name'),
      description: form.get('description') || '',
      category: form.get('category') || 'general',
      price: Number(form.get('price')),
      gstRate: Number(form.get('gstRate')),
      hsnCode: form.get('hsnCode'),
      stockQuantity: form.get('stockQuantity') === '' ? null : Number(form.get('stockQuantity')),
      imageUrl: form.get('imageUrl') || null,
    };
    await guard(async () => {
      await api('/products', { method: 'POST', body: JSON.stringify(payload) });
      toast('Product saved — remember to sync the catalog');
      closeModal();
      loadProducts();
    });
  });
});

// ── New order ───────────────────────────────────────────────────────────────

document.getElementById('new-order-btn').addEventListener('click', () => {
  openModal(
    'New order',
    `<form id="order-form" class="grid">
      <label>WhatsApp number<input name="waPhone" required placeholder="9876543210"></label>
      <label>Customer name<input name="name" placeholder="Optional"></label>
      <label class="span">Description<input name="description" required placeholder="Custom print — PETG, 320 g"></label>
      <label>Quantity<input name="quantity" type="number" min="1" value="1" required></label>
      <label>Unit price ₹<input name="unitPrice" type="number" step="0.01" min="0" required></label>
      <label>Price includes GST?
        <select name="priceIncludesTax"><option value="false">No</option><option value="true">Yes</option></select>
      </label>
      <label class="span"><span class="row" style="gap:6px">
        <input type="checkbox" name="sendPaymentLink" checked style="width:auto">
        Send the payment link on WhatsApp straight away
      </span></label>
      <button class="btn primary span" type="submit">Create order</button>
    </form>`,
  );

  document.getElementById('order-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const payload = {
      waPhone: form.get('waPhone'),
      name: form.get('name') || undefined,
      sendPaymentLink: form.get('sendPaymentLink') === 'on',
      lines: [
        {
          description: form.get('description'),
          quantity: Number(form.get('quantity')),
          unitPrice: Number(form.get('unitPrice')),
          priceIncludesTax: form.get('priceIncludesTax') === 'true',
        },
      ],
    };
    await guard(async () => {
      const result = await api('/orders', { method: 'POST', body: JSON.stringify(payload) });
      toast(`Created ${result.order.order_number}`);
      closeModal();
      show('orders');
    });
  });
});

// ── Quotes ──────────────────────────────────────────────────────────────────

async function loadQuotes() {
  const quotes = await api('/quotes?limit=50');
  document.getElementById('quotes-list').innerHTML = table(
    ['Quote', 'Customer', 'Unit', 'Total', 'Status', 'File', 'When'],
    quotes.map(
      (quote) => `<tr>
        <td><strong>${escapeHtml(quote.quote_number)}</strong></td>
        <td>${escapeHtml(quote.customer?.name || `+${quote.customer?.wa_phone || ''}`)}</td>
        <td class="num">${money(quote.unit_price)}</td>
        <td class="num">${money(quote.total)}</td>
        <td>${badge(quote.status)}</td>
        <td class="small">${escapeHtml(quote.media_filename || '—')}</td>
        <td class="small muted">${when(quote.created_at)}</td>
      </tr>`,
    ),
  );
}

// ── Quote calculator ────────────────────────────────────────────────────────

const FINISHING = [
  'support_removal',
  'sanding',
  'priming',
  'painting',
  'polishing',
  'assembly',
  'uv_curing',
  'threaded_inserts',
];

async function loadMaterials() {
  if (state.materials.length > 0) return;
  try {
    state.materials = await api('/materials');
  } catch {
    return;
  }

  document.getElementById('material-select').innerHTML = state.materials
    .map((material) => `<option value="${material.key}">${escapeHtml(material.name)}</option>`)
    .join('');

  document.getElementById('post-processing').innerHTML = FINISHING.map(
    (step) =>
      `<label class="chip"><input type="checkbox" name="postProcessing" value="${step}">${humanise(step)}</label>`,
  ).join('');
}

function loadPricing() {
  loadMaterials();
}

document.getElementById('pricing-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = {
    materialKey: form.get('materialKey'),
    weightGrams: Number(form.get('weightGrams')),
    printHours: Number(form.get('printHours')),
    quantity: Number(form.get('quantity')),
    rush: form.get('rush'),
    hardwareCost: Number(form.get('hardwareCost')) || 0,
    postProcessing: form.getAll('postProcessing'),
  };

  await guard(async () => {
    const quote = await api('/quotes/price', { method: 'POST', body: JSON.stringify(payload) });
    const b = quote.breakdown;
    document.getElementById('pricing-result').innerHTML = `
      <div class="panel" style="margin-top:16px">
        <h3>${escapeHtml(quote.material.name)} · ${quote.quantity} unit(s)</h3>
        <dl class="kv" style="margin-top:10px">
          <dt>Material</dt><dd>${money(b.materialCost)}</dd>
          <dt>Wastage allowance</dt><dd>${money(b.wastageCost)}</dd>
          <dt>Machine time</dt><dd>${money(b.machineCost)}</dd>
          <dt>Labour</dt><dd>${money(b.labourCost)}</dd>
          ${b.hardwareCost ? `<dt>Hardware</dt><dd>${money(b.hardwareCost)}</dd>` : ''}
          <dt>Direct cost</dt><dd><strong>${money(b.directCost)}</strong></dd>
          <dt>Margin</dt><dd>${money(b.margin)}</dd>
          ${b.rushSurcharge ? `<dt>Rush surcharge</dt><dd>${money(b.rushSurcharge)}</dd>` : ''}
          ${b.quantityDiscount ? `<dt>Volume discount</dt><dd>−${money(b.quantityDiscount)}</dd>` : ''}
          <dt>Setup fee</dt><dd>${money(b.setupFee)}</dd>
        </dl>
        <hr style="border:0;border-top:1px solid var(--line);margin:14px 0">
        <dl class="kv">
          <dt>Unit price (ex GST)</dt><dd><strong>${money(quote.unitPrice)}</strong></dd>
          <dt>Total (ex GST)</dt><dd><strong style="font-size:1.2rem">${money(quote.total)}</strong></dd>
          <dt>Machine hours</dt><dd>${quote.totalPrintHours} h</dd>
          <dt>Ready in</dt><dd>~${quote.estimatedReadyInDays} day(s)</dd>
        </dl>
      </div>`;
  });
});

// ── Outbox ──────────────────────────────────────────────────────────────────

async function loadOutbox() {
  const status = document.getElementById('outbox-filter').value;
  const rows = await api(`/outbox?status=${status}`);
  document.getElementById('outbox-list').innerHTML = table(
    ['To', 'Kind', 'Attempts', 'Next attempt', 'Last error', ''],
    rows.map(
      (row) => `<tr>
        <td>+${escapeHtml(row.to_phone)}</td>
        <td>${humanise(row.kind)}</td>
        <td class="num">${row.attempts}</td>
        <td class="small muted">${when(row.next_attempt_at)}</td>
        <td class="small error">${escapeHtml(row.last_error || '')}</td>
        <td>${
          row.status !== 'sent'
            ? `<button class="btn small" data-retry="${row.id}">Retry</button>`
            : ''
        }</td>
      </tr>`,
    ),
  );
}

document.getElementById('outbox-filter').addEventListener('change', loadOutbox);

document.getElementById('flush-outbox').addEventListener('click', async () => {
  await guard(async () => {
    const result = await api('/outbox/flush', { method: 'POST', body: '{}' });
    toast(`Sent ${result.sent}, failed ${result.failed}`);
    loadOutbox();
  });
});

document.addEventListener('click', async (event) => {
  const retry = event.target.closest('[data-retry]');
  if (retry) {
    await guard(async () => {
      await api(`/outbox/${retry.dataset.retry}/retry`, { method: 'POST' });
      toast('Requeued');
      loadOutbox();
    });
  }
});

// ── Modal ───────────────────────────────────────────────────────────────────

function openModal(title, html) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = html;
  document.getElementById('modal').hidden = false;
}

function closeModal() {
  document.getElementById('modal').hidden = true;
}

document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('modal').addEventListener('click', (event) => {
  if (event.target.id === 'modal') closeModal();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeModal();
});

/** Run an action, surfacing any failure as a toast rather than a silent stall. */
async function guard(action) {
  try {
    await action();
  } catch (error) {
    toast(error.message || 'Something went wrong', true);
  }
}

// ── Boot ────────────────────────────────────────────────────────────────────

if (state.key) {
  api('/summary')
    .then(unlock)
    .catch(() => lock());
}
