# PrintBill

WhatsApp-first billing, catalog and payment system for a 3D printing business.

Customers browse your products inside WhatsApp, send a cart, pay through a
hosted checkout, and receive a GST-compliant PDF invoice back in the same chat —
automatically, within seconds of the payment clearing. You run the workshop from
a small admin console.

```
Customer's WhatsApp                    PrintBill                     Gateway
────────────────────                   ─────────                     ───────
  "hi"              ──────────────▶  main menu
  taps Browse       ──────────────▶  catalog message
  adds to cart      ──────────────▶  order created, GST computed
  sends address     ──────────────▶  payment link  ────────────────▶  checkout
                                                                        │
                    ◀── invoice PDF ── invoice issued ◀── webhook ◀──── paid
```

---

## What it does

**Sells on WhatsApp.** Your product catalog is pushed to Meta Commerce Manager,
so customers browse a real storefront with images and prices inside the chat,
add to a cart, and send it. No website needed.

**Bills correctly.** Every invoice is a proper Indian tax invoice: consecutive
Rule 46 numbering per financial year, HSN codes, CGST+SGST or IGST decided by
place of supply, an HSN summary table, amount in words, and a round-off line.
All money is integer paise — the totals always reconcile to the paise.

**Takes payment.** Razorpay payment links cover UPI, cards, net banking and
wallets. Webhooks are HMAC-verified and deduplicated, so a replayed or retried
webhook can never charge or invoice a customer twice.

**Delivers the invoice.** The PDF is generated, uploaded to WhatsApp and sent as
a document message. Delivery goes through a durable outbox with exponential
backoff, so a WhatsApp API outage delays the invoice rather than losing it.

**Quotes custom jobs.** Customers send an STL and get a price built from real
inputs — grams of material, machine hours, finishing time, rush level, volume
breaks — not a guess.

---

## Quick start

```bash
cd printbill
npm install
cp .env.example .env        # then edit it — at minimum the seller block
npm run migrate             # create the database
npm run seed                # load a starter catalog of 12 products
npm run dev                 # http://localhost:3000
```

Open **http://localhost:3000/admin** and paste your `ADMIN_API_KEY`.

Out of the box `PAYMENT_PROVIDER=mock`, which gives you a local test checkout
that moves no money but exercises the entire real path — signature verification,
settlement, invoice issue, WhatsApp delivery. Create an order from the admin
console, click the payment link, pay, and watch the invoice appear in the outbox.

To go live, work through the two setup guides:

| Guide | What it covers |
|---|---|
| [docs/WHATSAPP_SETUP.md](docs/WHATSAPP_SETUP.md) | Meta app, phone number, permanent token, webhook, catalog |
| [docs/PAYMENTS_SETUP.md](docs/PAYMENTS_SETUP.md) | Razorpay keys, webhook secret, going live |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the pieces fit, and why they are built this way |
| [docs/GST_NOTES.md](docs/GST_NOTES.md) | What the invoice contains and which rules it follows |

---

## The conversation

Everything a customer can do, they do by chatting:

| They send | They get |
|---|---|
| `hi`, `menu` | Main menu — browse, custom quote, my orders, add GSTIN, talk to a human |
| Taps **Browse products** | Your storefront, in chat, with a working cart |
| A cart | Priced order, address prompt if needed, then a payment link |
| An STL / OBJ / 3MF file | Material picker → quantity → an indicative quote you can confirm |
| An address | Saved; state detected so GST splits correctly; payment link follows |
| A GSTIN | Validated (including check digit) and added to future invoices |
| `ORD-20260808-0042` | That order's status, with buttons to pay or fetch the invoice |

Free-text `menu` always works, from any point in any flow.

---

## The admin console

`/admin` gives you:

- **Dashboard** — collected revenue, orders awaiting payment, jobs in the
  workshop, and a system checklist showing exactly what is not yet configured
- **Orders** — full detail, tax breakdown, payment history, an event timeline,
  and status transitions that message the customer as the job progresses
- **Catalog** — add and edit products, then push them to WhatsApp with one click
- **Quote calculator** — price a job from slicer numbers, with the cost breakdown
- **Outbox** — every queued WhatsApp message, with retry

---

## Pricing model

A custom job is priced from what it actually consumes:

```
material    = (grams ÷ 1000) × material cost per kg
wastage     = material × wastage factor            (failed prints, purge)
machine     = print hours × machine rate × material difficulty
labour      = finishing minutes ÷ 60 × labour rate
─────────────────────────────────────────────────────────────
direct cost = material + wastage + machine + labour + hardware
× margin multiplier
× rush multiplier                                  (1.0 / 1.25 / 1.6)
− volume discount                                  (5 % at 5, up to 20 % at 50)
+ setup fee ÷ quantity                             (charged once per job)
= unit price, exclusive of GST
```

Every rate is an environment variable, and the whole breakdown is returned so
you can show a customer why a print costs what it costs.

---

## Commands

```bash
npm run dev              # development server, reloads on change
npm run build            # compile to dist/
npm start                # run the compiled build
npm run migrate          # create/upgrade the database
npm run seed             # load the starter catalog
npm run catalog:sync     # push products to WhatsApp Commerce Manager
npm run invoice:preview  # render a sample invoice PDF to inspect the layout
npm test                 # 90 tests
npm run typecheck        # strict TypeScript, no emit
```

---

## Safety properties

These are the ones worth knowing about, because they are what stops a billing
system from quietly losing money:

- **Money never touches a float.** Everything is integer paise; rupees exist only
  when parsing operator input and rendering output.
- **An order is credited once.** Payments are unique on `(provider, payment_id)`,
  so a duplicate webhook is recorded and ignored rather than re-applied.
- **An invoice number is issued once.** Allocation happens inside an IMMEDIATE
  transaction with the invoice insert, so a crash cannot skip or reuse a number.
- **A failed webhook is retried, a processed one is not.** Events are claimed by
  id; an event whose processing errored can be re-claimed, one that succeeded
  cannot.
- **Unverified webhooks change nothing.** Both WhatsApp and the payment gateway
  are HMAC-verified over the raw request bytes, compared in constant time,
  before the body is parsed.
- **The cart does not set the price.** Prices come from your product table, so a
  stale or tampered cart cannot buy a ₹2000 item for ₹1.
- **Order numbers are not a credential.** Every order lookup checks that the
  requesting phone owns the order.

---

## Deployment notes

- Put it behind HTTPS. Meta will not deliver webhooks to plain HTTP.
- `PUBLIC_BASE_URL` must be the externally reachable URL — invoice links and
  gateway callbacks are built from it.
- Back up `data/printbill.db` and `data/invoices/`. Those are your books.
- The database is SQLite in WAL mode, which comfortably handles a workshop's
  volume on a single small VM. Moving to Postgres later means rewriting
  `src/db/repositories.ts` and nothing else.
