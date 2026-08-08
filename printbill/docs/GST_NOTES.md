# GST notes

What the invoice contains, which rules it follows, and the decisions you should
confirm with your own accountant.

> This is a description of how the software behaves, not tax advice. Rates and
> classifications change; your CA is the authority on your specific products.

---

## The one rule that drives everything

**Place of supply decides the tax split.**

| Condition | Tax charged |
|---|---|
| Place of supply is in your own state | CGST at half the rate + SGST at half the rate |
| Place of supply is in another state | IGST at the full rate |

At 18 %, an intra-state supply is CGST 9 % + SGST 9 %; an inter-state supply is
IGST 18 %. The customer pays the same total either way — but the split must be
right, because it determines which government gets the money and whether your
buyer can claim input credit.

Getting this backwards is the most common defect in home-grown Indian billing
software, so the decision lives in a single function (`determineTaxKind`) whose
only inputs are two state codes.

### How the place of supply is determined

In order of confidence:

1. The buyer's **GSTIN** — its first two characters are the state of
   registration, and that is the strongest signal available
2. The state recorded on their **address**
3. Your own state, as a fallback

The address the customer types in chat is parsed for a state name, and for a set
of unambiguous city names (Bengaluru → 29, Mumbai → 27, and so on). If they later
give a GSTIN from a different state, it takes precedence.

**Set `SELLER_STATE_CODE` correctly.** Everything above is relative to it.

---

## What appears on the invoice

Rule 46 of the CGST Rules lists the required particulars. The renderer includes
all of them:

| Requirement | Where it appears |
|---|---|
| Supplier name, address, GSTIN | Header |
| Consecutive serial number, ≤16 chars | `INV/2026-27/0001` |
| Date of issue | Meta block |
| Recipient name, address, GSTIN | Bill To |
| HSN / SAC per line | Items table |
| Description, quantity, unit, value | Items table |
| Taxable value after discount | Items table + totals |
| Rate and amount of tax, per head | Items table + totals |
| Place of supply | Meta block |
| Whether tax is payable on reverse charge | Meta block ("No") |
| Signature | Footer |

Plus the things that are conventional rather than mandatory but that every
Indian buyer and auditor expects: amount in words, an HSN-wise summary table, a
round-off line, and bank/UPI payment details.

### Numbering

`INV/{financial-year}/{0001}` — 16 characters exactly.

- Consecutive, with no gaps: the number is allocated in the same transaction
  that writes the invoice, so a failure rolls it back rather than skipping it
- Unique within the financial year
- Restarts at 0001 each 1 April, automatically
- Supports 9 999 invoices per year before the width needs to grow

### Rounding

Tax is computed per line, then summed. The payable total is rounded to the
nearest rupee and the difference shown as a signed **Round Off** line, so the
invoice always adds up and the amount payable is always a whole rupee.

### Discounts

An order-level discount is spread across lines **before** tax, proportionally to
line value, with the remainder given to the largest line so the shares sum
exactly. Applying a discount after tax would over-collect GST on value you never
received.

---

## Classification for 3D printing

The defaults, which you should confirm:

| What you are selling | Code | Typical rate |
|---|---|---|
| 3D printed articles of plastic | HSN **3926** | 18 % |
| Printing / job work on a customer's design | SAC **998912** | 18 % |
| Delivery charges | SAC **996812** | Rate of the principal supply |

Delivery is treated as part of a composite supply and taxed at the highest rate
on the order, rather than at its own rate — which is the standard treatment when
goods and their delivery are supplied together.

Some finished goods fall elsewhere: toys and games are often HSN 9503 at 12 %,
and lamps and lighting HSN 9405. Set `hsn_code` and `gst_rate` per product in the
admin console when they differ from your default.

---

## Goods or services?

Worth understanding, because it changes the place-of-supply rule.

- **You print your own designs and sell the object** → supply of *goods*. Place
  of supply is where the goods are delivered.
- **The customer sends a model and you print it** → supply of *services* (job
  work). For a registered recipient the place of supply is their registration
  state; for an unregistered one it is the address on record.

For a workshop selling mostly finished items, the goods treatment covers most
orders. Ask your CA how to treat your custom-print jobs, and set the HSN/SAC on
those products accordingly.

---

## If you are not registered for GST

Set `GST_ENABLED=false`. The system then:

- Charges no tax
- Issues a **Bill of Supply** instead of a Tax Invoice, which is the correct
  document for an unregistered or composition supplier
- Keeps consecutive numbering, since that requirement is unchanged

Registration is mandatory above ₹40 lakh of turnover for goods (₹20 lakh for
services) in most states, and immediately for inter-state supply of goods. Once
you register, set `GST_ENABLED=true` and `SELLER_GSTIN`, and the next invoice
issues as a tax invoice.

---

## Filing

This system produces invoices; it does not file returns. What it gives you:

- **GSTR-1** (outward supplies) — every invoice with its taxable value, rate and
  tax split, per HSN. `GET /api/admin/invoices` and the `orders` table have
  everything your filing software or CA needs.
- **GSTR-3B** (summary) — totals of outward supply and tax by head.

Two things to keep on top of:

- **Buyer GSTINs must be correct.** A typo is a mismatch in GSTR-1 and your
  buyer loses their input credit. The system validates the checksum on entry,
  which catches most typos.
- **Keep the PDFs.** Back up `data/invoices/` along with the database — records
  must be retained for 72 months from the due date of the annual return.

---

## E-invoicing (IRN)

Businesses above the e-invoicing turnover threshold must register each B2B
invoice with the Invoice Registration Portal and print the IRN and signed QR
code on the document.

This system does not do that yet. The `invoices` table has room for it, and the
integration point would be a step in `issueInvoice` that calls an IRP provider
and stores the returned IRN and QR before the PDF is rendered. If your turnover
approaches the threshold, plan for that work — an invoice without an IRN is not
valid for a buyer's input credit once you are covered by the mandate.
