/**
 * Tax invoice renderer.
 *
 * Produces an A4 PDF carrying every particular Rule 46 of the CGST Rules
 * requires: supplier name/address/GSTIN, a consecutive invoice number, date of
 * issue, recipient details, HSN codes, taxable value, the rate and amount of tax
 * split by head, place of supply, whether tax is payable on reverse charge, and
 * a signature.
 *
 * Layout is hand-placed rather than flowed: an invoice is a fixed form, and
 * column positions that never move are easier to reason about than a layout
 * engine when a description wraps onto a third line.
 */
import fs from 'node:fs';
import path from 'node:path';
import PDFDocument from 'pdfkit';
import QRCode from 'qrcode';
import { seller } from '../config/env.js';
import {
  type Paise,
  amountInWords,
  formatAmount,
} from '../domain/money.js';
import type { TaxSummary } from '../domain/gst.js';

export interface InvoiceParty {
  readonly name: string;
  readonly legalName?: string | null;
  readonly gstin?: string | null;
  readonly addressLine1?: string | null;
  readonly addressLine2?: string | null;
  readonly city?: string | null;
  readonly state?: string | null;
  readonly stateCode?: string | null;
  readonly pincode?: string | null;
  readonly phone?: string | null;
  readonly email?: string | null;
}

export interface InvoiceDocument {
  readonly invoiceNumber: string;
  readonly issuedAt: Date;
  readonly orderNumber: string;
  readonly documentType: 'tax_invoice' | 'bill_of_supply' | 'credit_note';
  readonly buyer: InvoiceParty;
  readonly shippingAddress?: string | null;
  readonly placeOfSupply: { readonly code: string; readonly name: string };
  readonly tax: TaxSummary;
  readonly amountPaid: Paise;
  readonly paymentMethod?: string | null;
  readonly notes?: string | null;
  /** Production details printed under the line items. */
  readonly itemNotes?: Readonly<Record<string, string>>;
}

// ── Page geometry ────────────────────────────────────────────────────────────
const PAGE_MARGIN = 36;
const PAGE_WIDTH = 595.28; // A4 at 72 dpi
const PAGE_HEIGHT = 841.89;
const CONTENT_WIDTH = PAGE_WIDTH - PAGE_MARGIN * 2;

const INK = '#1a1a1a';
const MUTED = '#6b7280';
const RULE = '#d1d5db';
const ACCENT = '#0f766e';
const BAND = '#f3f4f6';

/** Column layout for the line-item table, as x offset + width. */
interface Column {
  readonly key: string;
  readonly label: string;
  readonly width: number;
  readonly align: 'left' | 'right' | 'center';
}

function itemColumns(intraState: boolean, gstEnabled: boolean): Column[] {
  if (!gstEnabled) {
    return [
      { key: 'sr', label: '#', width: 22, align: 'left' },
      { key: 'description', label: 'Description', width: 275, align: 'left' },
      { key: 'hsn', label: 'HSN', width: 52, align: 'left' },
      { key: 'qty', label: 'Qty', width: 34, align: 'right' },
      { key: 'rate', label: 'Rate', width: 68, align: 'right' },
      { key: 'amount', label: 'Amount', width: 72, align: 'right' },
    ];
  }
  if (intraState) {
    return [
      { key: 'sr', label: '#', width: 18, align: 'left' },
      { key: 'description', label: 'Description', width: 158, align: 'left' },
      { key: 'hsn', label: 'HSN', width: 42, align: 'left' },
      { key: 'qty', label: 'Qty', width: 26, align: 'right' },
      { key: 'rate', label: 'Rate', width: 54, align: 'right' },
      { key: 'taxable', label: 'Taxable', width: 60, align: 'right' },
      { key: 'cgst', label: 'CGST', width: 55, align: 'right' },
      { key: 'sgst', label: 'SGST', width: 55, align: 'right' },
      { key: 'amount', label: 'Total', width: 55, align: 'right' },
    ];
  }
  return [
    { key: 'sr', label: '#', width: 20, align: 'left' },
    { key: 'description', label: 'Description', width: 196, align: 'left' },
    { key: 'hsn', label: 'HSN', width: 46, align: 'left' },
    { key: 'qty', label: 'Qty', width: 30, align: 'right' },
    { key: 'rate', label: 'Rate', width: 62, align: 'right' },
    { key: 'taxable', label: 'Taxable', width: 68, align: 'right' },
    { key: 'igst', label: 'IGST', width: 68, align: 'right' },
    { key: 'amount', label: 'Total', width: 33, align: 'right' },
  ];
}

type Doc = PDFKit.PDFDocument;

/** Render the invoice and resolve with the complete PDF bytes. */
export async function renderInvoicePdf(invoice: InvoiceDocument): Promise<Buffer> {
  const doc = new PDFDocument({
    size: 'A4',
    margin: PAGE_MARGIN,
    info: {
      Title: `${titleFor(invoice.documentType)} ${invoice.invoiceNumber}`,
      Author: seller.legalName,
      Subject: `Invoice for order ${invoice.orderNumber}`,
      Creator: 'PrintBill',
    },
    // Every page gets the same frame; suppress the automatic first page so
    // header drawing stays in one place.
    autoFirstPage: true,
  });

  const chunks: Buffer[] = [];
  doc.on('data', (chunk: Buffer) => chunks.push(chunk));
  const finished = new Promise<Buffer>((resolve, reject) => {
    doc.on('end', () => resolve(Buffer.concat(chunks)));
    doc.on('error', reject);
  });

  const upiQr = await buildUpiQr(invoice);

  let cursor = drawHeader(doc, invoice);
  cursor = drawMetaBlock(doc, invoice, cursor);
  cursor = drawParties(doc, invoice, cursor);
  cursor = drawItems(doc, invoice, cursor);
  cursor = drawTotals(doc, invoice, cursor);
  cursor = drawHsnSummary(doc, invoice, cursor);
  drawFooter(doc, invoice, cursor, upiQr);

  doc.end();
  return finished;
}

/** Write the PDF to disk and return its path plus digest. */
export async function writeInvoicePdf(
  invoice: InvoiceDocument,
  directory: string,
): Promise<{ filePath: string; bytes: Buffer }> {
  const bytes = await renderInvoicePdf(invoice);
  fs.mkdirSync(directory, { recursive: true });
  // Slashes in the invoice number would create directories.
  const safeName = invoice.invoiceNumber.replace(/[^A-Za-z0-9._-]/g, '-');
  const filePath = path.join(directory, `${safeName}.pdf`);
  fs.writeFileSync(filePath, bytes);
  return { filePath, bytes };
}

function titleFor(documentType: InvoiceDocument['documentType']): string {
  switch (documentType) {
    case 'bill_of_supply':
      return 'BILL OF SUPPLY';
    case 'credit_note':
      return 'CREDIT NOTE';
    default:
      return 'TAX INVOICE';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Sections
// ─────────────────────────────────────────────────────────────────────────────

function drawHeader(doc: Doc, invoice: InvoiceDocument): number {
  const top = PAGE_MARGIN;

  // Accent bar across the top edge — the one piece of brand on the page.
  doc.rect(0, 0, PAGE_WIDTH, 6).fill(ACCENT);

  let textX = PAGE_MARGIN;
  const logoSize = 54;
  if (seller.logoPath && fs.existsSync(seller.logoPath)) {
    try {
      doc.image(seller.logoPath, PAGE_MARGIN, top + 6, { fit: [logoSize, logoSize] });
      textX = PAGE_MARGIN + logoSize + 12;
    } catch {
      // A corrupt logo must not stop an invoice going out.
    }
  }

  doc
    .fillColor(INK)
    .font('Helvetica-Bold')
    .fontSize(16)
    .text(seller.tradeName, textX, top + 8, { width: 300 });

  const sellerLines = [
    seller.legalName !== seller.tradeName ? seller.legalName : '',
    seller.addressLine1,
    seller.addressLine2,
    [seller.city, seller.state, seller.pincode].filter(Boolean).join(', '),
    seller.phone ? `Phone: ${seller.phone}` : '',
    seller.email ? `Email: ${seller.email}` : '',
    seller.gstin ? `GSTIN: ${seller.gstin}` : '',
    seller.pan ? `PAN: ${seller.pan}` : '',
  ].filter((line) => Boolean(line && line.trim()));

  doc.font('Helvetica').fontSize(8).fillColor(MUTED);
  let y = doc.y + 2;
  for (const line of sellerLines) {
    doc.text(line, textX, y, { width: 300 });
    y = doc.y;
  }

  // Document title, right aligned.
  doc
    .font('Helvetica-Bold')
    .fontSize(18)
    .fillColor(ACCENT)
    .text(titleFor(invoice.documentType), PAGE_WIDTH / 2, top + 10, {
      width: CONTENT_WIDTH / 2,
      align: 'right',
    });

  doc
    .font('Helvetica')
    .fontSize(7.5)
    .fillColor(MUTED)
    .text('ORIGINAL FOR RECIPIENT', PAGE_WIDTH / 2, top + 32, {
      width: CONTENT_WIDTH / 2,
      align: 'right',
    });

  const bottom = Math.max(y, top + 74);
  return rule(doc, bottom + 6);
}

function drawMetaBlock(doc: Doc, invoice: InvoiceDocument, top: number): number {
  const rowHeight = 13;
  const left: [string, string][] = [
    ['Invoice No.', invoice.invoiceNumber],
    ['Invoice Date', formatDate(invoice.issuedAt)],
    ['Order Ref.', invoice.orderNumber],
  ];
  const right: [string, string][] = [
    ['Place of Supply', `${invoice.placeOfSupply.name} (${invoice.placeOfSupply.code})`],
    ['Reverse Charge', 'No'],
    [
      'Supply Type',
      invoice.tax.kind === 'intra_state' ? 'Intra-State (CGST + SGST)' : 'Inter-State (IGST)',
    ],
  ];

  const columnWidth = CONTENT_WIDTH / 2;
  drawKeyValues(doc, left, PAGE_MARGIN, top, columnWidth - 10, rowHeight);
  drawKeyValues(doc, right, PAGE_MARGIN + columnWidth, top, columnWidth, rowHeight);

  return rule(doc, top + rowHeight * Math.max(left.length, right.length) + 6);
}

function drawKeyValues(
  doc: Doc,
  rows: readonly [string, string][],
  x: number,
  top: number,
  width: number,
  rowHeight: number,
): void {
  const labelWidth = 78;
  rows.forEach(([label, value], index) => {
    const y = top + index * rowHeight;
    doc.font('Helvetica').fontSize(8).fillColor(MUTED).text(`${label}`, x, y, { width: labelWidth });
    doc
      .font('Helvetica-Bold')
      .fontSize(8.5)
      .fillColor(INK)
      .text(value, x + labelWidth, y, { width: width - labelWidth });
  });
}

function drawParties(doc: Doc, invoice: InvoiceDocument, top: number): number {
  const columnWidth = CONTENT_WIDTH / 2 - 6;
  const buyer = invoice.buyer;

  const billTo = [
    buyer.legalName || buyer.name,
    buyer.addressLine1,
    buyer.addressLine2,
    [buyer.city, buyer.state, buyer.pincode].filter(Boolean).join(', '),
    buyer.phone ? `Phone: ${buyer.phone}` : '',
    buyer.email ? `Email: ${buyer.email}` : '',
    buyer.gstin ? `GSTIN: ${buyer.gstin}` : '',
    buyer.stateCode ? `State Code: ${buyer.stateCode}` : '',
  ].filter((line) => Boolean(line && String(line).trim()));

  const shipTo = invoice.shippingAddress
    ? invoice.shippingAddress.split('\n').filter((line) => line.trim())
    : billTo;

  const startY = top + 4;
  doc.font('Helvetica-Bold').fontSize(8).fillColor(ACCENT).text('BILL TO', PAGE_MARGIN, startY);
  doc
    .font('Helvetica-Bold')
    .fontSize(8)
    .fillColor(ACCENT)
    .text('SHIP TO', PAGE_MARGIN + CONTENT_WIDTH / 2, startY);

  let leftY = startY + 12;
  doc.font('Helvetica').fontSize(8.5).fillColor(INK);
  for (const [index, line] of billTo.entries()) {
    doc
      .font(index === 0 ? 'Helvetica-Bold' : 'Helvetica')
      .fillColor(index === 0 ? INK : MUTED)
      .text(String(line), PAGE_MARGIN, leftY, { width: columnWidth });
    leftY = doc.y;
  }

  let rightY = startY + 12;
  for (const [index, line] of shipTo.entries()) {
    doc
      .font(index === 0 ? 'Helvetica-Bold' : 'Helvetica')
      .fontSize(8.5)
      .fillColor(index === 0 ? INK : MUTED)
      .text(String(line), PAGE_MARGIN + CONTENT_WIDTH / 2, rightY, { width: columnWidth });
    rightY = doc.y;
  }

  return rule(doc, Math.max(leftY, rightY) + 6);
}

function drawItems(doc: Doc, invoice: InvoiceDocument, top: number): number {
  const intraState = invoice.tax.kind === 'intra_state';
  const columns = itemColumns(intraState, invoice.tax.gstEnabled);
  const headerHeight = 18;

  let y = drawItemsHeader(doc, columns, top, headerHeight);

  invoice.tax.lines.forEach((line, index) => {
    const note = invoice.itemNotes?.[line.id];
    const descriptionColumn = columns.find((column) => column.key === 'description');
    const descriptionWidth = (descriptionColumn?.width ?? 160) - 6;

    // Measure before drawing so a wrapped description can trigger a page break
    // rather than run off the bottom of the sheet.
    doc.font('Helvetica').fontSize(8);
    const descriptionHeight = doc.heightOfString(line.description, { width: descriptionWidth });
    const noteHeight = note
      ? doc.fontSize(7).heightOfString(note, { width: descriptionWidth }) + 1
      : 0;
    const rowHeight = Math.max(18, descriptionHeight + noteHeight + 8);

    if (y + rowHeight > PAGE_HEIGHT - 140) {
      doc.addPage();
      y = drawItemsHeader(doc, columns, PAGE_MARGIN + 10, headerHeight);
    }

    // Zebra striping keeps long tables readable.
    if (index % 2 === 1) {
      doc.rect(PAGE_MARGIN, y, CONTENT_WIDTH, rowHeight).fill('#fafafa');
    }

    const values: Record<string, string> = {
      sr: String(index + 1),
      description: line.description,
      hsn: line.hsnCode,
      qty: String(line.quantity),
      rate: formatAmount(line.unitPrice),
      taxable: formatAmount(line.taxableValue),
      cgst: `${formatAmount(line.cgst)}\n@${line.gstRate / 2}%`,
      sgst: `${formatAmount(line.sgst)}\n@${line.gstRate / 2}%`,
      igst: `${formatAmount(line.igst)}\n@${line.gstRate}%`,
      amount: formatAmount(line.lineTotal),
    };

    let x = PAGE_MARGIN;
    for (const column of columns) {
      const value = values[column.key] ?? '';
      if (column.key === 'description') {
        doc
          .font('Helvetica')
          .fontSize(8)
          .fillColor(INK)
          .text(value, x + 3, y + 4, { width: column.width - 6 });
        if (note) {
          doc
            .font('Helvetica-Oblique')
            .fontSize(7)
            .fillColor(MUTED)
            .text(note, x + 3, doc.y + 1, { width: column.width - 6 });
        }
      } else if (column.key === 'cgst' || column.key === 'sgst' || column.key === 'igst') {
        // Amount on the first line, rate beneath it in a smaller face.
        const [amount, rate] = value.split('\n');
        doc
          .font('Helvetica')
          .fontSize(8)
          .fillColor(INK)
          .text(amount ?? '', x + 3, y + 4, { width: column.width - 6, align: 'right' });
        doc
          .fontSize(6.5)
          .fillColor(MUTED)
          .text(rate ?? '', x + 3, y + 13, { width: column.width - 6, align: 'right' });
      } else {
        doc
          .font('Helvetica')
          .fontSize(8)
          .fillColor(INK)
          .text(value, x + 3, y + 4, { width: column.width - 6, align: column.align });
      }
      x += column.width;
    }

    y += rowHeight;
    doc.moveTo(PAGE_MARGIN, y).lineTo(PAGE_MARGIN + CONTENT_WIDTH, y).strokeColor('#eceff1').lineWidth(0.5).stroke();
  });

  return y + 4;
}

function drawItemsHeader(doc: Doc, columns: readonly Column[], top: number, height: number): number {
  doc.rect(PAGE_MARGIN, top, CONTENT_WIDTH, height).fill(ACCENT);
  let x = PAGE_MARGIN;
  for (const column of columns) {
    doc
      .font('Helvetica-Bold')
      .fontSize(7.5)
      .fillColor('#ffffff')
      .text(column.label.toUpperCase(), x + 3, top + 5.5, {
        width: column.width - 6,
        align: column.align,
      });
    x += column.width;
  }
  return top + height;
}

function drawTotals(doc: Doc, invoice: InvoiceDocument, top: number): number {
  const tax = invoice.tax;
  const boxWidth = 216;
  const boxX = PAGE_MARGIN + CONTENT_WIDTH - boxWidth;

  const rows: [string, string, boolean][] = [['Taxable Value', formatAmount(tax.subtotal), false]];
  if (tax.totalDiscount > 0) rows.push(['Discount', `-${formatAmount(tax.totalDiscount)}`, false]);
  if (tax.shipping > 0) rows.push(['Delivery Charges', formatAmount(tax.shipping), false]);
  if (tax.gstEnabled) {
    if (tax.kind === 'intra_state') {
      rows.push(['CGST', formatAmount(tax.cgst), false]);
      rows.push(['SGST', formatAmount(tax.sgst), false]);
    } else {
      rows.push(['IGST', formatAmount(tax.igst), false]);
    }
  }
  if (tax.roundOff !== 0) {
    const sign = tax.roundOff > 0 ? '+' : '-';
    rows.push(['Round Off', `${sign}${formatAmount(Math.abs(tax.roundOff))}`, false]);
  }
  rows.push(['Grand Total', `Rs. ${formatAmount(tax.grandTotal)}`, true]);

  const rowHeight = 15;
  let y = top + 6;

  // Amount in words sits to the left of the totals box.
  doc
    .font('Helvetica-Bold')
    .fontSize(7.5)
    .fillColor(MUTED)
    .text('AMOUNT IN WORDS', PAGE_MARGIN, y);
  doc
    .font('Helvetica-Bold')
    .fontSize(8.5)
    .fillColor(INK)
    .text(amountInWords(tax.grandTotal), PAGE_MARGIN, y + 11, { width: CONTENT_WIDTH - boxWidth - 14 });

  const balance = tax.grandTotal - invoice.amountPaid;
  const paymentLines = [
    `Amount Paid: Rs. ${formatAmount(invoice.amountPaid)}`,
    balance > 0 ? `Balance Due: Rs. ${formatAmount(balance)}` : 'Status: PAID IN FULL',
    invoice.paymentMethod ? `Paid via: ${invoice.paymentMethod.toUpperCase()}` : '',
  ].filter(Boolean);

  doc.font('Helvetica').fontSize(8).fillColor(balance > 0 ? '#b91c1c' : '#15803d');
  let paymentY = doc.y + 6;
  for (const line of paymentLines) {
    doc.text(line, PAGE_MARGIN, paymentY, { width: CONTENT_WIDTH - boxWidth - 14 });
    paymentY = doc.y;
  }

  for (const [label, value, emphasised] of rows) {
    if (emphasised) {
      doc.rect(boxX, y - 2, boxWidth, rowHeight + 4).fill(ACCENT);
      doc
        .font('Helvetica-Bold')
        .fontSize(10)
        .fillColor('#ffffff')
        .text(label, boxX + 8, y + 2, { width: boxWidth / 2 });
      doc
        .font('Helvetica-Bold')
        .fontSize(10)
        .fillColor('#ffffff')
        .text(value, boxX + boxWidth / 2, y + 2, { width: boxWidth / 2 - 8, align: 'right' });
    } else {
      doc
        .font('Helvetica')
        .fontSize(8.5)
        .fillColor(MUTED)
        .text(label, boxX + 8, y, { width: boxWidth / 2 });
      doc
        .font('Helvetica')
        .fontSize(8.5)
        .fillColor(INK)
        .text(value, boxX + boxWidth / 2, y, { width: boxWidth / 2 - 8, align: 'right' });
    }
    y += emphasised ? rowHeight + 6 : rowHeight;
  }

  return Math.max(y, paymentY) + 6;
}

function drawHsnSummary(doc: Doc, invoice: InvoiceDocument, top: number): number {
  if (!invoice.tax.gstEnabled || invoice.tax.hsnSummary.length === 0) return top;

  let y = top + 4;
  if (y > PAGE_HEIGHT - 190) {
    doc.addPage();
    y = PAGE_MARGIN + 10;
  }

  const intraState = invoice.tax.kind === 'intra_state';
  const columns: Column[] = intraState
    ? [
        { key: 'hsn', label: 'HSN/SAC', width: 90, align: 'left' },
        { key: 'taxable', label: 'Taxable Value', width: 100, align: 'right' },
        { key: 'cgstRate', label: 'CGST Rate', width: 70, align: 'right' },
        { key: 'cgst', label: 'CGST Amt', width: 82, align: 'right' },
        { key: 'sgstRate', label: 'SGST Rate', width: 70, align: 'right' },
        { key: 'sgst', label: 'SGST Amt', width: 111, align: 'right' },
      ]
    : [
        { key: 'hsn', label: 'HSN/SAC', width: 120, align: 'left' },
        { key: 'taxable', label: 'Taxable Value', width: 140, align: 'right' },
        { key: 'igstRate', label: 'IGST Rate', width: 120, align: 'right' },
        { key: 'igst', label: 'IGST Amount', width: 143, align: 'right' },
      ];

  doc.font('Helvetica-Bold').fontSize(7.5).fillColor(MUTED).text('HSN / SAC SUMMARY', PAGE_MARGIN, y);
  y += 12;

  doc.rect(PAGE_MARGIN, y, CONTENT_WIDTH, 15).fill(BAND);
  let x = PAGE_MARGIN;
  for (const column of columns) {
    doc
      .font('Helvetica-Bold')
      .fontSize(7)
      .fillColor(INK)
      .text(column.label, x + 4, y + 4.5, { width: column.width - 8, align: column.align });
    x += column.width;
  }
  y += 15;

  for (const row of invoice.tax.hsnSummary) {
    const values: Record<string, string> = {
      hsn: row.hsnCode,
      taxable: formatAmount(row.taxableValue),
      cgstRate: `${row.gstRate / 2}%`,
      cgst: formatAmount(row.cgst),
      sgstRate: `${row.gstRate / 2}%`,
      sgst: formatAmount(row.sgst),
      igstRate: `${row.gstRate}%`,
      igst: formatAmount(row.igst),
    };
    x = PAGE_MARGIN;
    for (const column of columns) {
      doc
        .font('Helvetica')
        .fontSize(7.5)
        .fillColor(INK)
        .text(values[column.key] ?? '', x + 4, y + 3.5, {
          width: column.width - 8,
          align: column.align,
        });
      x += column.width;
    }
    y += 14;
    doc
      .moveTo(PAGE_MARGIN, y)
      .lineTo(PAGE_MARGIN + CONTENT_WIDTH, y)
      .strokeColor('#eceff1')
      .lineWidth(0.5)
      .stroke();
  }

  return y + 4;
}

function drawFooter(
  doc: Doc,
  invoice: InvoiceDocument,
  top: number,
  upiQr: Buffer | null,
): void {
  let y = top + 6;
  if (y > PAGE_HEIGHT - 150) {
    doc.addPage();
    y = PAGE_MARGIN + 10;
  }
  y = rule(doc, y);

  const columnWidth = (CONTENT_WIDTH - 130) / 2;

  // Bank details
  const bankLines = [
    seller.bank.accountName ? `A/c Name: ${seller.bank.accountName}` : '',
    seller.bank.name ? `Bank: ${seller.bank.name}` : '',
    seller.bank.accountNumber ? `A/c No: ${seller.bank.accountNumber}` : '',
    seller.bank.ifsc ? `IFSC: ${seller.bank.ifsc}` : '',
    seller.upiId ? `UPI: ${seller.upiId}` : '',
  ].filter(Boolean);

  if (bankLines.length > 0) {
    doc.font('Helvetica-Bold').fontSize(7.5).fillColor(MUTED).text('PAYMENT DETAILS', PAGE_MARGIN, y + 6);
    let bankY = y + 18;
    for (const line of bankLines) {
      doc.font('Helvetica').fontSize(7.5).fillColor(INK).text(line, PAGE_MARGIN, bankY, {
        width: columnWidth,
      });
      bankY = doc.y;
    }
  }

  // Terms
  const terms = [
    'Goods once sold are accepted for return only if defective, within 7 days of delivery.',
    'Custom printed items are made to order and are not returnable.',
    'Colour and finish may vary slightly between batches.',
    'Subject to local jurisdiction.',
  ];
  doc
    .font('Helvetica-Bold')
    .fontSize(7.5)
    .fillColor(MUTED)
    .text('TERMS & CONDITIONS', PAGE_MARGIN + columnWidth + 20, y + 6);
  let termsY = y + 18;
  for (const [index, term] of terms.entries()) {
    doc
      .font('Helvetica')
      .fontSize(6.8)
      .fillColor(MUTED)
      .text(`${index + 1}. ${term}`, PAGE_MARGIN + columnWidth + 20, termsY, {
        width: columnWidth,
      });
    termsY = doc.y + 1;
  }

  // UPI QR, only useful while money is still owed.
  const qrX = PAGE_MARGIN + CONTENT_WIDTH - 110;
  if (upiQr) {
    doc.image(upiQr, qrX, y + 14, { fit: [72, 72] });
    doc
      .font('Helvetica')
      .fontSize(6.5)
      .fillColor(MUTED)
      .text('Scan to pay via UPI', qrX - 10, y + 90, { width: 92, align: 'center' });
  }

  const signatureY = Math.max(termsY, y + 96);
  doc
    .font('Helvetica')
    .fontSize(7.5)
    .fillColor(MUTED)
    .text(`For ${seller.tradeName}`, PAGE_MARGIN + CONTENT_WIDTH - 160, signatureY + 6, {
      width: 160,
      align: 'right',
    });
  doc
    .moveTo(PAGE_MARGIN + CONTENT_WIDTH - 150, signatureY + 44)
    .lineTo(PAGE_MARGIN + CONTENT_WIDTH, signatureY + 44)
    .strokeColor(RULE)
    .lineWidth(0.7)
    .stroke();
  doc
    .font('Helvetica')
    .fontSize(7)
    .fillColor(MUTED)
    .text('Authorised Signatory', PAGE_MARGIN + CONTENT_WIDTH - 160, signatureY + 47, {
      width: 160,
      align: 'right',
    });

  if (invoice.notes) {
    doc
      .font('Helvetica-Oblique')
      .fontSize(7)
      .fillColor(MUTED)
      .text(invoice.notes, PAGE_MARGIN, signatureY + 24, { width: CONTENT_WIDTH - 180 });
  }

  doc
    .font('Helvetica')
    .fontSize(6.5)
    .fillColor(MUTED)
    .text(
      'This is a computer generated invoice and does not require a physical signature.',
      PAGE_MARGIN,
      PAGE_HEIGHT - PAGE_MARGIN - 8,
      { width: CONTENT_WIDTH, align: 'center' },
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function rule(doc: Doc, y: number): number {
  doc
    .moveTo(PAGE_MARGIN, y)
    .lineTo(PAGE_MARGIN + CONTENT_WIDTH, y)
    .strokeColor(RULE)
    .lineWidth(0.8)
    .stroke();
  return y + 4;
}

function formatDate(date: Date): string {
  const day = String(date.getDate()).padStart(2, '0');
  const month = date.toLocaleString('en-IN', { month: 'short' });
  return `${day} ${month} ${date.getFullYear()}`;
}

/**
 * UPI deep-link QR for the outstanding balance.
 *
 * Only rendered when money is still due — a QR on a settled invoice invites an
 * accidental second payment.
 */
async function buildUpiQr(invoice: InvoiceDocument): Promise<Buffer | null> {
  const balance = invoice.tax.grandTotal - invoice.amountPaid;
  if (!seller.upiId || balance <= 0) return null;

  const params = new URLSearchParams({
    pa: seller.upiId,
    pn: seller.tradeName,
    am: (balance / 100).toFixed(2),
    cu: 'INR',
    tn: `Invoice ${invoice.invoiceNumber}`,
  });

  try {
    return await QRCode.toBuffer(`upi://pay?${params.toString()}`, {
      type: 'png',
      margin: 1,
      width: 200,
      errorCorrectionLevel: 'M',
    });
  } catch {
    return null;
  }
}
