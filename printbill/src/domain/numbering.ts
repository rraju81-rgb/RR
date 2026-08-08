/**
 * Document numbering.
 *
 * Rule 46 of the CGST Rules requires an invoice number that is consecutive,
 * unique within the financial year, at most 16 characters, and built only from
 * letters, digits, hyphen and slash. The format below is `INV/2026-27/0001` —
 * exactly 16 characters at four digits of sequence, which covers 9 999 invoices
 * in a year before the width has to grow.
 */

export const INVOICE_PREFIX = 'INV';
export const ORDER_PREFIX = 'ORD';
export const QUOTE_PREFIX = 'QTN';

/**
 * The Indian financial year containing `date`, as `2026-27`.
 * The year runs 1 April → 31 March, so January–March belong to the year before.
 */
export function financialYearOf(date: Date = new Date()): string {
  const year = date.getUTCFullYear();
  const month = date.getUTCMonth(); // 0 = January
  const startYear = month >= 3 ? year : year - 1;
  const endYear = (startYear + 1) % 100;
  return `${startYear}-${String(endYear).padStart(2, '0')}`;
}

/** `INV/2026-27/0001` */
export function formatInvoiceNumber(financialYear: string, sequence: number): string {
  const padded = String(sequence).padStart(4, '0');
  const number = `${INVOICE_PREFIX}/${financialYear}/${padded}`;
  if (number.length > 16) {
    throw new RangeError(
      `Invoice number "${number}" exceeds the 16 character limit set by Rule 46`,
    );
  }
  return number;
}

/**
 * Order and quote numbers are internal, so they are free of the Rule 46 limit
 * and carry the date for readability: `ORD-20260808-0042`.
 */
export function formatOrderNumber(sequence: number, date: Date = new Date()): string {
  return `${ORDER_PREFIX}-${compactDate(date)}-${String(sequence).padStart(4, '0')}`;
}

export function formatQuoteNumber(sequence: number, date: Date = new Date()): string {
  return `${QUOTE_PREFIX}-${compactDate(date)}-${String(sequence).padStart(4, '0')}`;
}

function compactDate(date: Date): string {
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  return `${year}${month}${day}`;
}

/** Counter name for the invoice sequence, scoped so it restarts each April. */
export function invoiceCounterName(financialYear: string): string {
  return `invoice:${financialYear}`;
}
