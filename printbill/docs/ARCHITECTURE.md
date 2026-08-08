# Architecture

How the pieces fit together, and the reasoning behind the choices that are not
obvious.

---

## Layers

```
                      ┌──────────────────────────────────┐
   WhatsApp ─────────▶│  http/routes/whatsapp.ts         │  verify → 200 → process
                      ├──────────────────────────────────┤
   Gateway  ─────────▶│  http/routes/payments.ts         │  verify → claim → settle
                      ├──────────────────────────────────┤
   Operator ─────────▶│  http/routes/admin.ts            │  API key
                      └───────────────┬──────────────────┘
                                      │
                      ┌───────────────▼──────────────────┐
                      │  services/                       │
                      │  orders · checkout · invoices    │  business decisions
                      │  messaging · catalog             │
                      └───────────────┬──────────────────┘
                                      │
                      ┌───────────────▼──────────────────┐
                      │  domain/                         │
                      │  money · gst · pricing           │  pure functions,
                      │  numbering                       │  no I/O
                      └───────────────┬──────────────────┘
                                      │
                      ┌───────────────▼──────────────────┐
                      │  db/repositories.ts              │  every SQL statement
                      └──────────────────────────────────┘
```

`domain/` holds pure functions with no database or network access, which is why
the tax and pricing rules can be tested exhaustively without fixtures. Anything
that touches the outside world is behind an injectable client, so the end-to-end
test drives the entire purchase flow with no network at all.

---

## Why these choices

### Integer paise, everywhere

A billing system that stores rupees as floats produces invoices whose line items
do not sum to their own total. `0.1 + 0.2 !== 0.3`, and after a few thousand
invoices the discrepancy becomes a reconciliation problem with your accountant.
All money is an integer number of paise from the moment it enters the system;
`domain/money.ts` is the only place conversion happens.

The same module owns rounding. `multiply` rounds half-up in both directions so
a credit note is the exact mirror of the invoice it reverses, and `allocate`
distributes remainders so split amounts always sum back to the original.

### SQLite, synchronously

The write paths here are short transactions triggered by webhooks. Synchronous
access removes an entire class of interleaving bug from the payment → invoice
sequence: there is no `await` between reading the invoice counter and writing the
invoice row, so nothing can slip in between.

WAL mode lets the outbox worker read while a webhook writes. `busy_timeout`
makes concurrent writers wait rather than fail.

A workshop doing a few hundred orders a month will not outgrow this. If it ever
does, `db/repositories.ts` is the only file that speaks SQL.

### An outbox instead of direct sends

A payment webhook that called the WhatsApp API inline would either block until
the gateway's retry timeout, or lose the customer's invoice when Meta returns a
503. Instead the webhook commits a row and returns 200; a worker delivers it with
exponential backoff, surviving restarts.

Failures are classified. A 503 is retried; "not a WhatsApp user" and "outside the
24-hour window" are abandoned immediately, because retrying them cannot succeed
and only burns API quota.

### The state machine in `whatsapp/flows.ts`

Chat is resumable in a way a web checkout is not — a customer can abandon an
order mid-address and return three days later. Conversation state is persisted
per phone number, so the reply still makes sense when they do. `menu` always
works as an escape hatch, from any state.

---

## The two critical paths

### Payment settlement

Everything about `settlePayment` is shaped by one fact: **the gateway will
sometimes deliver the same event twice**, and may deliver two different events
for the same payment.

Three independent guards:

1. `webhook_events` — unique on `(provider, event_id)`. A repeat of an event that
   was already processed successfully is acknowledged and dropped. An event whose
   processing *failed* can be re-claimed, so a genuine retry still settles.
2. `payments` — unique on `(provider, provider_payment_id)`. Even if two
   different event types arrive for one payment, the order is credited once.
3. `invoices` — unique on `order_id`. `issueInvoice` returns the existing invoice
   rather than minting a second number.

The database work is one transaction. The PDF render and WhatsApp send happen
after the commit, because both are retryable and neither should hold a lock.

### Invoice numbering

Rule 46 requires a consecutive series, unique within the financial year, at most
16 characters. `INV/2026-27/0001` is exactly 16.

The counter is allocated with `UPDATE ... RETURNING` inside an IMMEDIATE
transaction that also inserts the invoice. IMMEDIATE takes the write lock up
front, so two concurrent webhooks cannot read the same counter value and then
fight over the write. If anything downstream throws, the transaction rolls back
and the number is not consumed — no gaps.

The counter name is scoped to the financial year, so numbering restarts at 0001
each April automatically.

---

## Data model

| Table | Holds | Note |
|---|---|---|
| `customers` | One row per WhatsApp number | Merged on update — a cart order never wipes a stored GSTIN |
| `products` | Your catalog | `retailer_id` is the id Meta uses in cart orders |
| `orders` / `order_items` | Priced orders | Tax treatment frozen at order time |
| `invoices` | Issued documents | Unique per order; carries the download token and WhatsApp media id |
| `payments` | Gateway payments | Unique per provider payment id — the double-credit guard |
| `payment_links` | Hosted checkout links | Reused rather than regenerated |
| `webhook_events` | Every webhook accepted | The replay guard |
| `message_outbox` | Queued WhatsApp messages | With attempts, backoff and a dedupe key |
| `inbound_messages` | Every message received | Guards against Meta redelivery |
| `conversations` | Chat state per number | Survives restarts |
| `counters` | Gapless sequences | Order, quote, invoice-per-FY |
| `order_events` | Append-only audit trail | "When did this order move" |

Money columns are integer paise. Timestamps are ISO-8601 UTC strings, so they
sort lexicographically.

---

## Security posture

| Surface | Control |
|---|---|
| WhatsApp webhook | HMAC-SHA256 over raw bytes (`X-Hub-Signature-256`), constant-time compare |
| Payment webhook | HMAC-SHA256 over raw bytes, constant-time compare, then event dedupe |
| Admin API | Shared key, constant-time compare |
| Invoice download | 24 random bytes in the URL; no enumeration, no directory listing |
| Order lookup in chat | Ownership checked against the requesting phone number |
| Cart pricing | Prices read from the product table, never from the cart payload |
| Logs | Tokens, secrets and signatures redacted centrally |
| Mock checkout | Routes only mounted when `PAYMENT_PROVIDER=mock` |

Both webhook routes are registered *before* `express.json()`, because the
signature covers the exact bytes received and a re-serialised body will not
verify.

---

## Testing

90 tests, no network, no fixtures beyond an in-memory database.

- `money.test.ts` — rounding, allocation, Indian digit grouping, amount in words
- `gst.test.ts` — intra/inter-state splits, discount spreading, HSN summary,
  GSTIN checksum, plus invariants (line totals always sum to the order total;
  the grand total is always a whole rupee)
- `pricing.test.ts` — the quote engine, financial years, invoice number format
- `flow.e2e.test.ts` — the entire purchase: cart → address → payment link →
  signed webhook → invoice → PDF → WhatsApp document, with the WhatsApp API
  replaced by a recording fake and every message asserted on

The e2e suite also covers what should *not* happen: tampered signatures rejected,
duplicate webhooks credited once, another customer's order not revealed, a stale
cart price ignored, oversold stock refused.
