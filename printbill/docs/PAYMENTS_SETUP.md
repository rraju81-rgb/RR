# Payments setup

PrintBill ships with two gateways: `mock` for development, `razorpay` for
production. Razorpay is the default choice here because it settles UPI — which
is how most Indian customers will actually pay you — and its payment links are a
plain URL you can paste into a WhatsApp message.

---

## Development: the mock gateway

With `PAYMENT_PROVIDER=mock`, payment links point at a local checkout page that
moves no money but posts a correctly HMAC-signed webhook back to this service.
The signature check, settlement, invoice issue and WhatsApp delivery are all the
real code paths — only the money is missing.

Use it to test the whole flow before touching real credentials:

```bash
# create an order and get its payment link
curl -X POST localhost:3000/api/admin/orders \
  -H "X-API-Key: $ADMIN_API_KEY" -H "Content-Type: application/json" \
  -d '{"waPhone":"9876543210","name":"Test Customer",
       "lines":[{"description":"Test print","quantity":1,"unitPrice":500}]}'
```

Open the returned link, click **Pay now**, and the invoice will be issued and
queued for WhatsApp delivery.

The mock routes are only mounted when `PAYMENT_PROVIDER=mock`, so they cannot
exist in a production deployment.

---

## Production: Razorpay

### 1. Account and KYC

Sign up at <https://dashboard.razorpay.com>. Submit KYC — PAN, GST certificate,
bank proof and business address. Approval usually takes 1–2 working days, and
until it completes you can only use test mode.

### 2. Keys

**Settings → API Keys → Generate Key**

```bash
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxx
PAYMENT_PROVIDER=razorpay
```

The secret is shown exactly once. Test keys are prefixed `rzp_test_` — develop
against those first.

### 3. Webhook

**Settings → Webhooks → Add New Webhook**

- URL: `https://your-domain.example.com/webhooks/payments`
- Secret: generate one (`openssl rand -hex 24`) and put the same value in
  `RAZORPAY_WEBHOOK_SECRET`
- Active events:
  - `payment.captured`
  - `payment.failed`
  - `payment_link.paid`
  - `refund.processed`

The webhook secret is what makes payment confirmation trustworthy. This service
refuses to start with `PAYMENT_PROVIDER=razorpay` and no
`RAZORPAY_WEBHOOK_SECRET`, because without it anyone who finds your webhook URL
could mark orders paid.

### 4. Enable the methods you want

**Settings → Payment Methods.** Turn on UPI, cards, net banking and wallets as
suits you. UPI has the lowest transaction cost and the highest success rate for
consumer payments in India; for B2B, net banking matters more.

### 5. Verify before trusting it

Razorpay's dashboard can replay a webhook to your endpoint. Send a
`payment.captured` and confirm:

```bash
# 200 with a status, not 401
# then the order should be paid and an invoice issued
curl -H "X-API-Key: $ADMIN_API_KEY" localhost:3000/api/admin/orders?status=paid
```

A `401` means the secret does not match. A `500` means settlement failed — the
error is stored on the `webhook_events` row and the event can be retried.

---

## How settlement works

Understanding this matters, because it is where a billing system goes wrong.

```
webhook arrives
   │
   ├─ signature verified over the RAW bytes, compared in constant time
   │     └─ fails → 401, nothing happens
   │
   ├─ event claimed by id
   │     └─ already processed successfully → 200, nothing happens
   │     └─ previously failed → re-claimed and retried
   │
   └─ ONE transaction:
        ├─ insert payment, unique on (provider, payment_id)
        │     └─ already present → duplicate; order untouched
        ├─ add the amount to the order
        ├─ if fully paid: reduce stock, issue the invoice number
        └─ commit
      then, outside the transaction:
        ├─ render the PDF
        └─ queue the WhatsApp document, deduped on the invoice number
```

The consequences worth stating plainly:

- Razorpay sending both `payment.captured` and `payment_link.paid` for one
  payment credits the order **once**, because both carry the same payment id.
- A webhook retried five times still produces **one** invoice and **one**
  WhatsApp message.
- A part payment is recorded but does **not** produce a tax invoice — the
  invoice is raised only when the order is settled in full.
- If PDF generation fails, the money is still recorded and the invoice number is
  still issued; re-render it from the admin console.

---

## Taking payment outside the gateway

Cash, a direct bank transfer, or a UPI paid straight to your own ID:

```bash
curl -X POST localhost:3000/api/admin/orders/42/mark-paid \
  -H "X-API-Key: $ADMIN_API_KEY" -H "Content-Type: application/json" \
  -d '{"method":"cash","reference":"received in person 08-Aug"}'
```

This records the payment, issues the invoice and sends it on WhatsApp exactly as
a gateway payment would. The admin console exposes it as **Record offline
payment** on any unpaid order.

---

## Using a different gateway

`src/payments/gateway.ts` defines the whole contract — two methods:

```ts
createPaymentLink(request): Promise<PaymentLink>
parseWebhook(rawBody, headers): PaymentEvent   // must verify the signature
```

Cashfree, PhonePe, Paytm and Stripe all fit this shape. Add a file implementing
the interface, register it in `src/payments/index.ts`, and nothing else in the
codebase changes — the order and invoice services never learn which gateway is
in use.

Two rules any implementation must honour:

1. **Verify the signature over the raw bytes.** Re-serialising a parsed body
   changes key order and whitespace, and the digest will not match.
2. **Return a stable `eventId`.** It is the idempotency key; without it a
   retried webhook will be treated as a new payment.

---

## Charges to expect

Razorpay's standard pricing at the time of writing is 2 % + GST on cards and net
banking, and lower on UPI (frequently zero for small-value UPI). Settlement is
T+2 by default. Confirm current rates on your own dashboard — they vary by
account and negotiate downward with volume.
