-- PrintBill schema.
--
-- Conventions:
--   * every money column is an INTEGER number of paise (see domain/money.ts)
--   * timestamps are ISO-8601 UTC strings, so they sort lexicographically
--   * JSON blobs hold provider payloads verbatim for audit and replay

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Customers
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  -- E.164 without the '+', matching what the WhatsApp webhook delivers.
  wa_phone          TEXT    NOT NULL UNIQUE,
  name              TEXT,
  email             TEXT,
  gstin             TEXT,
  -- Populated for B2B buyers who need input tax credit.
  legal_name        TEXT,
  address_line1     TEXT,
  address_line2     TEXT,
  city              TEXT,
  state             TEXT,
  state_code        TEXT,
  pincode           TEXT,
  notes             TEXT,
  created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers (wa_phone);

-- ─────────────────────────────────────────────────────────────────────────────
-- Catalog
--
-- `retailer_id` is the identifier Meta Commerce Manager uses for the product in
-- the WhatsApp catalog; it is what arrives on an in-chat cart order.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  retailer_id       TEXT    NOT NULL UNIQUE,
  name              TEXT    NOT NULL,
  description       TEXT    NOT NULL DEFAULT '',
  category          TEXT    NOT NULL DEFAULT 'general',
  -- Price shown in the WhatsApp storefront, GST inclusive.
  price             INTEGER NOT NULL,
  currency          TEXT    NOT NULL DEFAULT 'INR',
  hsn_code          TEXT    NOT NULL DEFAULT '3926',
  gst_rate          REAL    NOT NULL DEFAULT 18,
  material_key      TEXT,
  weight_grams      REAL,
  print_hours       REAL,
  image_url         TEXT,
  -- 'in stock' | 'out of stock' | 'preorder', mirroring the catalog vocabulary.
  availability      TEXT    NOT NULL DEFAULT 'in stock',
  -- Made to order items have no stock count; NULL means "always available".
  stock_quantity    INTEGER,
  is_active         INTEGER NOT NULL DEFAULT 1,
  -- Set once the row has been pushed to Meta, to detect drift.
  catalog_synced_at TEXT,
  created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_products_active ON products (is_active, category);

-- ─────────────────────────────────────────────────────────────────────────────
-- Quotes for custom print jobs
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quotes (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  quote_number      TEXT    NOT NULL UNIQUE,
  customer_id       INTEGER NOT NULL REFERENCES customers (id) ON DELETE CASCADE,
  -- The QuoteRequest as submitted, so a quote can be recomputed or explained.
  request_json      TEXT    NOT NULL,
  -- The computed Quote, frozen at the moment it was sent to the customer.
  result_json       TEXT    NOT NULL,
  unit_price        INTEGER NOT NULL,
  total             INTEGER NOT NULL,
  status            TEXT    NOT NULL DEFAULT 'draft'
                      CHECK (status IN ('draft', 'sent', 'accepted', 'rejected', 'expired')),
  -- Customer's uploaded model, held as a WhatsApp media id plus a local copy.
  media_id          TEXT,
  media_path        TEXT,
  media_filename    TEXT,
  expires_at        TEXT,
  created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_quotes_customer ON quotes (customer_id, status);

-- ─────────────────────────────────────────────────────────────────────────────
-- Orders
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  order_number      TEXT    NOT NULL UNIQUE,
  customer_id       INTEGER NOT NULL REFERENCES customers (id) ON DELETE RESTRICT,
  quote_id          INTEGER REFERENCES quotes (id) ON DELETE SET NULL,
  -- Where the order came in from. 'whatsapp_cart' is the in-chat storefront.
  channel           TEXT    NOT NULL DEFAULT 'whatsapp_cart'
                      CHECK (channel IN ('whatsapp_cart', 'whatsapp_quote', 'manual', 'web')),
  status            TEXT    NOT NULL DEFAULT 'pending_payment'
                      CHECK (status IN (
                        'draft', 'pending_payment', 'paid', 'in_production',
                        'ready', 'shipped', 'delivered', 'cancelled', 'refunded'
                      )),
  -- Frozen at order time: the tax treatment must not shift if settings change.
  place_of_supply_code TEXT NOT NULL,
  place_of_supply_name TEXT NOT NULL,
  tax_kind          TEXT    NOT NULL CHECK (tax_kind IN ('intra_state', 'inter_state')),
  subtotal          INTEGER NOT NULL DEFAULT 0,
  discount          INTEGER NOT NULL DEFAULT 0,
  shipping          INTEGER NOT NULL DEFAULT 0,
  cgst              INTEGER NOT NULL DEFAULT 0,
  sgst              INTEGER NOT NULL DEFAULT 0,
  igst              INTEGER NOT NULL DEFAULT 0,
  round_off         INTEGER NOT NULL DEFAULT 0,
  total             INTEGER NOT NULL DEFAULT 0,
  amount_paid       INTEGER NOT NULL DEFAULT 0,
  currency          TEXT    NOT NULL DEFAULT 'INR',
  shipping_address  TEXT,
  customer_note     TEXT,
  internal_note     TEXT,
  created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  paid_at           TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status, created_at);

CREATE TABLE IF NOT EXISTS order_items (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id          INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
  product_id        INTEGER REFERENCES products (id) ON DELETE SET NULL,
  description       TEXT    NOT NULL,
  hsn_code          TEXT    NOT NULL,
  quantity          INTEGER NOT NULL CHECK (quantity > 0),
  unit_price        INTEGER NOT NULL,
  discount          INTEGER NOT NULL DEFAULT 0,
  gst_rate          REAL    NOT NULL,
  taxable_value     INTEGER NOT NULL,
  cgst              INTEGER NOT NULL DEFAULT 0,
  sgst              INTEGER NOT NULL DEFAULT 0,
  igst              INTEGER NOT NULL DEFAULT 0,
  line_total        INTEGER NOT NULL,
  -- Print parameters (material, weight, colour) for the production floor.
  meta_json         TEXT
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items (order_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- Invoices
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invoices (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_number    TEXT    NOT NULL UNIQUE,
  -- Indian financial year the number belongs to, e.g. '2026-27'.
  financial_year    TEXT    NOT NULL,
  sequence_number   INTEGER NOT NULL,
  order_id          INTEGER NOT NULL UNIQUE REFERENCES orders (id) ON DELETE RESTRICT,
  document_type     TEXT    NOT NULL DEFAULT 'tax_invoice'
                      CHECK (document_type IN ('tax_invoice', 'bill_of_supply', 'credit_note')),
  issued_at         TEXT    NOT NULL,
  total             INTEGER NOT NULL,
  pdf_path          TEXT,
  pdf_sha256        TEXT,
  -- Random token so a customer can fetch their PDF without authentication.
  download_token    TEXT    NOT NULL UNIQUE,
  -- Media id returned by WhatsApp after upload; lets us resend without re-upload.
  whatsapp_media_id TEXT,
  sent_at           TEXT,
  cancelled_at      TEXT,
  created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_fy_seq
  ON invoices (financial_year, sequence_number);

-- ─────────────────────────────────────────────────────────────────────────────
-- Payments
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payment_links (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id          INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
  provider          TEXT    NOT NULL,
  provider_link_id  TEXT    NOT NULL,
  short_url         TEXT    NOT NULL,
  amount            INTEGER NOT NULL,
  status            TEXT    NOT NULL DEFAULT 'created',
  expires_at        TEXT,
  raw_json          TEXT,
  created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_links_provider
  ON payment_links (provider, provider_link_id);
CREATE INDEX IF NOT EXISTS idx_payment_links_order ON payment_links (order_id);

CREATE TABLE IF NOT EXISTS payments (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id            INTEGER NOT NULL REFERENCES orders (id) ON DELETE RESTRICT,
  provider            TEXT    NOT NULL,
  provider_payment_id TEXT    NOT NULL,
  provider_link_id    TEXT,
  amount              INTEGER NOT NULL,
  currency            TEXT    NOT NULL DEFAULT 'INR',
  status              TEXT    NOT NULL
                        CHECK (status IN ('created', 'authorized', 'captured', 'failed', 'refunded')),
  method              TEXT,
  raw_json            TEXT,
  created_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- One row per gateway payment: the guard against double-crediting an order
-- when a gateway retries its webhook.
CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_provider
  ON payments (provider, provider_payment_id);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments (order_id);

-- Every webhook we accept is recorded before it is acted on. A repeat delivery
-- of the same event id is recognised and skipped.
CREATE TABLE IF NOT EXISTS webhook_events (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  provider          TEXT    NOT NULL,
  event_id          TEXT    NOT NULL,
  event_type        TEXT,
  payload_json      TEXT    NOT NULL,
  received_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  processed_at      TEXT,
  error             TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_webhook_events_unique
  ON webhook_events (provider, event_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- WhatsApp messaging
-- ─────────────────────────────────────────────────────────────────────────────

-- Outbound messages are queued rather than sent inline, so a WhatsApp API blip
-- never costs a customer their invoice. The worker drains this with backoff.
CREATE TABLE IF NOT EXISTS message_outbox (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  to_phone          TEXT    NOT NULL,
  kind              TEXT    NOT NULL,
  payload_json      TEXT    NOT NULL,
  status            TEXT    NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'sent', 'failed', 'abandoned')),
  attempts          INTEGER NOT NULL DEFAULT 0,
  next_attempt_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  last_error        TEXT,
  provider_message_id TEXT,
  -- Set by callers that must not enqueue the same message twice.
  dedupe_key        TEXT,
  order_id          INTEGER REFERENCES orders (id) ON DELETE SET NULL,
  created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  sent_at           TEXT
);

CREATE INDEX IF NOT EXISTS idx_outbox_pending
  ON message_outbox (status, next_attempt_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_dedupe
  ON message_outbox (dedupe_key) WHERE dedupe_key IS NOT NULL;

-- Inbound messages, kept for audit and for the "did we already answer this"
-- check when Meta redelivers a webhook.
CREATE TABLE IF NOT EXISTS inbound_messages (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  wa_message_id     TEXT    NOT NULL UNIQUE,
  from_phone        TEXT    NOT NULL,
  message_type      TEXT    NOT NULL,
  body              TEXT,
  payload_json      TEXT    NOT NULL,
  received_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_inbound_from ON inbound_messages (from_phone, received_at);

-- One row per customer conversation: where they are in the flow and what they
-- have told us so far.
CREATE TABLE IF NOT EXISTS conversations (
  wa_phone          TEXT    PRIMARY KEY,
  state             TEXT    NOT NULL DEFAULT 'idle',
  context_json      TEXT    NOT NULL DEFAULT '{}',
  -- Meta only allows free-form replies within 24h of the last customer message.
  last_inbound_at   TEXT,
  updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Counters and settings
-- ─────────────────────────────────────────────────────────────────────────────

-- Gapless sequences (invoice numbers, order numbers) allocated under a write
-- transaction. A UNIQUE index alone would let numbers skip on rollback.
CREATE TABLE IF NOT EXISTS counters (
  name              TEXT    PRIMARY KEY,
  value             INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
  key               TEXT    PRIMARY KEY,
  value             TEXT    NOT NULL,
  updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Append-only trail of status changes, for answering "when did this order move".
CREATE TABLE IF NOT EXISTS order_events (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id          INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
  event             TEXT    NOT NULL,
  detail            TEXT,
  created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_order_events_order ON order_events (order_id, created_at);
