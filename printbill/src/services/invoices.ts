/**
 * Invoice issuing.
 *
 * An invoice number is allocated exactly once per order, inside a transaction,
 * and never reused — this is the record the tax authority sees. The PDF is
 * rendered from the *stored* order lines rather than recomputed from current
 * prices, so reissuing a document years later reproduces the original.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import { type Db, nextCounterValue, transaction } from '../db/index.js';
import { customers, invoices, orders } from '../db/repositories.js';
import type { InvoiceRow, OrderRow } from '../db/types.js';
import { config } from '../config/env.js';
import type { ComputedLine, TaxSummary } from '../domain/gst.js';
import type { Paise } from '../domain/money.js';
import {
  financialYearOf,
  formatInvoiceNumber,
  invoiceCounterName,
} from '../domain/numbering.js';
import { type InvoiceDocument, writeInvoicePdf } from '../pdf/invoice.js';

export class InvoiceError extends Error {
  override readonly name = 'InvoiceError';
}

/**
 * Issue an invoice for an order, or return the one already issued.
 *
 * Idempotent by design: the payment webhook may fire more than once, and the
 * second call must hand back the first invoice rather than mint a new number.
 */
export function issueInvoice(db: Db, orderId: number, issuedAt = new Date()): InvoiceRow {
  const existing = invoices.findByOrderId(db, orderId);
  if (existing) return existing;

  const order = orders.findById(db, orderId);
  if (!order) throw new InvoiceError(`Unknown order ${orderId}`);
  if (order.status === 'cancelled') {
    throw new InvoiceError(`Refusing to invoice cancelled order ${order.order_number}`);
  }

  return transaction(db, () => {
    // Re-check inside the lock: two webhooks can reach the guard above together.
    const raced = invoices.findByOrderId(db, orderId);
    if (raced) return raced;

    const financialYear = financialYearOf(issuedAt);
    const sequence = nextCounterValue(db, invoiceCounterName(financialYear));

    return invoices.insert(db, {
      invoiceNumber: formatInvoiceNumber(financialYear, sequence),
      financialYear,
      sequenceNumber: sequence,
      orderId,
      // Without GST registration the correct document is a bill of supply.
      documentType: config.GST_ENABLED ? 'tax_invoice' : 'bill_of_supply',
      issuedAt: issuedAt.toISOString(),
      total: order.total,
      downloadToken: crypto.randomBytes(24).toString('base64url'),
    });
  });
}

/** Rebuild the tax summary from stored line rows, without recomputation. */
export function taxSummaryFromOrder(db: Db, order: OrderRow): TaxSummary {
  const items = orders.items(db, order.id);

  const lines: ComputedLine[] = items.map((item) => ({
    id: String(item.id),
    description: item.description,
    hsnCode: item.hsn_code,
    quantity: item.quantity,
    unitPrice: item.unit_price,
    discount: item.discount,
    gstRate: item.gst_rate,
    taxableValue: item.taxable_value,
    cgst: item.cgst,
    sgst: item.sgst,
    igst: item.igst,
    totalTax: item.cgst + item.sgst + item.igst,
    lineTotal: item.line_total,
  }));

  const hsnMap = new Map<string, { hsnCode: string; gstRate: number; taxableValue: Paise; cgst: Paise; sgst: Paise; igst: Paise }>();
  for (const line of lines) {
    const key = `${line.hsnCode}|${line.gstRate}`;
    const existing = hsnMap.get(key);
    if (existing) {
      existing.taxableValue += line.taxableValue;
      existing.cgst += line.cgst;
      existing.sgst += line.sgst;
      existing.igst += line.igst;
    } else {
      hsnMap.set(key, {
        hsnCode: line.hsnCode,
        gstRate: line.gstRate,
        taxableValue: line.taxableValue,
        cgst: line.cgst,
        sgst: line.sgst,
        igst: line.igst,
      });
    }
  }

  // Shipping tax lives on the order rather than any line, so recover it as the
  // difference between the order totals and the sum of the lines.
  const lineCgst = lines.reduce((total, line) => total + line.cgst, 0);
  const lineSgst = lines.reduce((total, line) => total + line.sgst, 0);
  const lineIgst = lines.reduce((total, line) => total + line.igst, 0);
  const shippingCgst = order.cgst - lineCgst;
  const shippingSgst = order.sgst - lineSgst;
  const shippingIgst = order.igst - lineIgst;

  if (order.shipping > 0) {
    const shippingRate = lines.reduce((highest, line) => Math.max(highest, line.gstRate), 0);
    hsnMap.set('996812|shipping', {
      hsnCode: '996812',
      gstRate: shippingRate,
      taxableValue: order.shipping,
      cgst: shippingCgst,
      sgst: shippingSgst,
      igst: shippingIgst,
    });
  }

  return {
    kind: order.tax_kind,
    gstEnabled: order.cgst + order.sgst + order.igst > 0 || config.GST_ENABLED,
    lines,
    subtotal: order.subtotal,
    totalDiscount: order.discount,
    shipping: order.shipping,
    cgst: order.cgst,
    sgst: order.sgst,
    igst: order.igst,
    totalTax: order.cgst + order.sgst + order.igst,
    roundOff: order.round_off,
    grandTotal: order.total,
    hsnSummary: [...hsnMap.values()].sort((a, b) => a.hsnCode.localeCompare(b.hsnCode)),
  };
}

/**
 * Render (or re-render) the PDF for an invoice and record its path and digest.
 * An already-rendered PDF is returned as-is unless `force` is set.
 */
export async function renderInvoice(
  db: Db,
  invoice: InvoiceRow,
  options: { force?: boolean } = {},
): Promise<{ filePath: string; bytes: Buffer }> {
  if (!options.force && invoice.pdf_path && fs.existsSync(invoice.pdf_path)) {
    return { filePath: invoice.pdf_path, bytes: fs.readFileSync(invoice.pdf_path) };
  }

  const order = orders.findById(db, invoice.order_id);
  if (!order) throw new InvoiceError(`Order ${invoice.order_id} vanished`);
  const customer = customers.findById(db, order.customer_id);
  if (!customer) throw new InvoiceError(`Customer ${order.customer_id} vanished`);

  const items = orders.items(db, order.id);
  const itemNotes: Record<string, string> = {};
  for (const item of items) {
    const note = describePrintSpec(item.meta_json);
    if (note) itemNotes[String(item.id)] = note;
  }

  const paymentMethod = latestPaymentMethod(db, order.id);

  const document: InvoiceDocument = {
    invoiceNumber: invoice.invoice_number,
    issuedAt: new Date(invoice.issued_at),
    orderNumber: order.order_number,
    documentType: invoice.document_type,
    buyer: {
      name: customer.name ?? `+${customer.wa_phone}`,
      legalName: customer.legal_name,
      gstin: customer.gstin,
      addressLine1: customer.address_line1,
      addressLine2: customer.address_line2,
      city: customer.city,
      state: customer.state,
      stateCode: customer.state_code,
      pincode: customer.pincode,
      phone: `+${customer.wa_phone}`,
      email: customer.email,
    },
    shippingAddress: order.shipping_address,
    placeOfSupply: { code: order.place_of_supply_code, name: order.place_of_supply_name },
    tax: taxSummaryFromOrder(db, order),
    amountPaid: order.amount_paid,
    paymentMethod,
    notes: order.customer_note,
    itemNotes,
  };

  const { filePath, bytes } = await writeInvoicePdf(document, config.INVOICE_DIR);
  const sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
  invoices.attachPdf(db, invoice.id, filePath, sha256);
  return { filePath, bytes };
}

function latestPaymentMethod(db: Db, orderId: number): string | null {
  const row = db
    .prepare(
      `SELECT method FROM payments
       WHERE order_id = ? AND status = 'captured' AND method IS NOT NULL
       ORDER BY created_at DESC LIMIT 1`,
    )
    .get(orderId) as { method: string } | undefined;
  return row?.method ?? null;
}

/** Turn stored print parameters into the one-line spec shown under the item. */
function describePrintSpec(metaJson: string | null): string | null {
  if (!metaJson) return null;
  try {
    const meta = JSON.parse(metaJson) as Record<string, unknown>;
    const parts: string[] = [];
    if (typeof meta.material === 'string' && meta.material) parts.push(meta.material.toUpperCase());
    if (typeof meta.materialName === 'string') parts.push(meta.materialName);
    if (typeof meta.colour === 'string') parts.push(meta.colour);
    if (typeof meta.weightGrams === 'number') parts.push(`${meta.weightGrams} g`);
    if (typeof meta.printHours === 'number') parts.push(`${meta.printHours} h print`);
    if (typeof meta.finish === 'string') parts.push(meta.finish);
    return parts.length > 0 ? parts.join(' · ') : null;
  } catch {
    return null;
  }
}

/** Public, unguessable URL the customer can open from the chat. */
export function invoiceDownloadUrl(invoice: InvoiceRow): string {
  return `${config.PUBLIC_BASE_URL}/invoices/${invoice.download_token}`;
}
