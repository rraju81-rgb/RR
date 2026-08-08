# WhatsApp setup

Getting from "code runs locally" to "customers can buy from you in WhatsApp".

Budget about 90 minutes for the first pass, plus 1–3 days of waiting if your
business needs Meta verification.

---

## What you need before starting

- A **Facebook Business Manager** account
- A **phone number** that is *not* currently registered on any WhatsApp account
  (personal or Business app). If it is, delete that account first and wait ~20
  minutes. This is the single most common thing that blocks people.
- Your business documents (GST certificate, utility bill) for verification
- An **HTTPS URL** pointing at this service. For local development:
  `npx cloudflared tunnel --url http://localhost:3000`

---

## 1. Create the app

1. Go to <https://developers.facebook.com/apps> → **Create App**
2. Use case: **Other** → type: **Business** → pick your Business Manager account
3. On the app dashboard, find **WhatsApp** and click **Set up**

This creates a test phone number you can use immediately, before your real
number is verified.

## 2. Collect the four identifiers

From **WhatsApp → API Setup**:

| Field on the page | `.env` variable |
|---|---|
| Phone number ID | `WHATSAPP_PHONE_NUMBER_ID` |
| WhatsApp Business Account ID | `WHATSAPP_BUSINESS_ACCOUNT_ID` |
| Temporary access token | `WHATSAPP_ACCESS_TOKEN` — replace this in step 3 |

From **App Settings → Basic**, reveal **App Secret**:

| | |
|---|---|
| App Secret | `WHATSAPP_APP_SECRET` |

The App Secret is what proves a webhook genuinely came from Meta. Without it
this service rejects every webhook in production.

## 3. Get a permanent token

The token on the API Setup page expires in 24 hours. For a real deployment:

1. **Business Settings → Users → System Users → Add**
   Name it `printbill`, role **Admin**
2. **Add Assets** → WhatsApp Accounts → your account → toggle **Full control**
3. **Generate New Token** → select your app → tick these permissions:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
   - `catalog_management`
   - `business_management`
4. Set expiry to **Never**, generate, and copy it into `WHATSAPP_ACCESS_TOKEN`

Copy it immediately — Meta shows it exactly once.

## 4. Point the webhook at this service

Set `WHATSAPP_VERIFY_TOKEN` in `.env` to any random string, and start the
service so it can answer the handshake.

In **WhatsApp → Configuration → Webhook → Edit**:

- Callback URL: `https://your-domain.example.com/webhooks/whatsapp`
- Verify token: the same string you just set

Click **Verify and Save**. If it fails, the service is not reachable at that URL
or the token does not match — the server log prints which.

Then **Manage** the webhook fields and subscribe to:

- `messages` — required; this is every inbound message, cart and button tap

Verify it end to end:

```bash
curl "https://your-domain.example.com/webhooks/whatsapp?hub.mode=subscribe\
&hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=test123"
# → test123
```

## 5. Build the catalog — this is what makes selling work

Without a catalog, customers get a text list. With one, they get a real
storefront with images, prices and a cart, inside the chat.

1. Go to <https://business.facebook.com/commerce> → **Add catalog**
2. Type: **E-commerce**, owned by your Business Manager
3. Open the catalog → **Settings** → copy the **Catalog ID** into
   `WHATSAPP_CATALOG_ID`
4. Connect it: **WhatsApp Manager → your account → Catalog → Connect catalog**

Now push your products:

```bash
npm run catalog:sync
```

Products come from your `products` table — edit them in `/admin`, then sync.
Check `npm run catalog:sync -- --dry-run` first if you want to see what would go.

**Product images matter.** `image_url` must be a publicly reachable HTTPS URL of
at least 500×500 px. Meta rejects items without a usable image, and a storefront
of grey placeholders does not sell. Photograph each product against a plain
background and host the files anywhere public.

Meta reviews new catalog items; most are approved within a few hours.

## 6. Enable the cart

In **WhatsApp Manager → Catalog settings**, turn on:

- **Show catalog in chat**
- **Allow customers to add items to cart**

Without the cart toggle, customers can browse but never send an order, and no
`order` webhook will ever arrive.

## 7. Message templates

You can reply freely for 24 hours after a customer messages you. Outside that
window, only pre-approved templates are allowed.

Create these under **WhatsApp Manager → Message Templates**. Category matters:
`UTILITY` templates are cheaper and approve faster than `MARKETING`.

**`order_confirmation`** (Utility)
```
Hi {{1}}, your order {{2}} is confirmed. 🖨️
Total paid: ₹{{3}}
Your GST invoice is attached. We'll message you when it ships.
```

**`order_shipped`** (Utility)
```
Good news {{1}} — order {{2}} has been dispatched. 🚚
Tracking: {{3}}
```

**`payment_reminder`** (Utility)
```
Hi {{1}}, your order {{2}} for ₹{{3}} is still awaiting payment.
Tap below to complete it — we'll start printing right away.
```

Send one with:

```ts
await client.sendTemplate(phone, {
  name: 'order_shipped',
  components: [{ type: 'body', parameters: [
    { type: 'text', text: 'Ananya' },
    { type: 'text', text: 'ORD-20260808-0042' },
    { type: 'text', text: 'BLR123456789' },
  ]}],
});
```

## 8. Verify your business and go live

1. **Business Settings → Business Info → Start Verification** — upload your GST
   certificate and a utility bill in the business's name
2. **WhatsApp → API Setup → Add phone number** — register your real number and
   verify it by SMS or call
3. Set a display name (it needs approval), profile photo, business description
   and address — this is what customers see, so it is worth doing properly
4. **App Dashboard → toggle the app from Development to Live**

Unverified accounts are capped at 250 business-initiated conversations per day.
Verification lifts that to 1 000, then higher as your quality rating holds up.

---

## Testing before you go live

Add your own number under **API Setup → recipient phone numbers** (up to 5 test
numbers), then message the test number from WhatsApp. You should get the main
menu back within a second or two.

If nothing arrives, check in this order:

```bash
# Is the service getting the webhook at all?
tail -f /path/to/logs | grep whatsapp

# Did the message get queued?
curl -H "X-API-Key: $ADMIN_API_KEY" localhost:3000/api/admin/outbox?status=pending

# Force a send and read the error
curl -X POST -H "X-API-Key: $ADMIN_API_KEY" localhost:3000/api/admin/outbox/flush
```

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| Webhook verification fails | Service not reachable over HTTPS, or `WHATSAPP_VERIFY_TOKEN` mismatch |
| Every webhook returns 401 | `WHATSAPP_APP_SECRET` is wrong — copy it again from App Settings → Basic |
| Messages queue but never send | Token expired or lacks `whatsapp_business_messaging`; check `last_error` in the outbox |
| Error code 131047 | The 24-hour window closed — you must use an approved template |
| Error code 131026 | That number is not on WhatsApp, or blocked you |
| Catalog message sends but is empty | Catalog not connected to the WhatsApp account, or items still under review |
| Cart never arrives as an order | "Allow customers to add items to cart" is off |
| `Cart references unknown product` | A product was deleted locally but not in the catalog — run `npm run catalog:sync` |
