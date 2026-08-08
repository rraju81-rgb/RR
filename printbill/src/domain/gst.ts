/**
 * GST computation for Indian tax invoices.
 *
 * The one rule that drives everything: if the place of supply is the seller's
 * own state the tax splits into CGST + SGST at half the rate each; otherwise
 * the whole rate is charged as IGST. Getting this backwards is the single most
 * common defect in home-grown Indian billing software, so the decision lives in
 * one function with the state codes as its only input.
 */
import { type Paise, allocate, percentOf, roundToRupee, sum } from './money.js';

export const GST_STATE_CODES: Readonly<Record<string, string>> = Object.freeze({
  '01': 'Jammu and Kashmir',
  '02': 'Himachal Pradesh',
  '03': 'Punjab',
  '04': 'Chandigarh',
  '05': 'Uttarakhand',
  '06': 'Haryana',
  '07': 'Delhi',
  '08': 'Rajasthan',
  '09': 'Uttar Pradesh',
  '10': 'Bihar',
  '11': 'Sikkim',
  '12': 'Arunachal Pradesh',
  '13': 'Nagaland',
  '14': 'Manipur',
  '15': 'Mizoram',
  '16': 'Tripura',
  '17': 'Meghalaya',
  '18': 'Assam',
  '19': 'West Bengal',
  '20': 'Jharkhand',
  '21': 'Odisha',
  '22': 'Chhattisgarh',
  '23': 'Madhya Pradesh',
  '24': 'Gujarat',
  '26': 'Dadra and Nagar Haveli and Daman and Diu',
  '27': 'Maharashtra',
  '29': 'Karnataka',
  '30': 'Goa',
  '31': 'Lakshadweep',
  '32': 'Kerala',
  '33': 'Tamil Nadu',
  '34': 'Puducherry',
  '35': 'Andaman and Nicobar Islands',
  '36': 'Telangana',
  '37': 'Andhra Pradesh',
  '38': 'Ladakh',
  '97': 'Other Territory',
});

export type TaxKind = 'intra_state' | 'inter_state';

export interface TaxableLine {
  /** Stable identifier so callers can map results back to their own items. */
  readonly id: string;
  readonly description: string;
  readonly hsnCode: string;
  readonly quantity: number;
  /** Price for one unit, before discount and before tax. */
  readonly unitPrice: Paise;
  /** Absolute discount on this line (not a percentage), already computed. */
  readonly discount?: Paise;
  readonly gstRate: number;
}

export interface ComputedLine extends TaxableLine {
  readonly discount: Paise;
  /** quantity x unitPrice - discount. The value GST is charged on. */
  readonly taxableValue: Paise;
  readonly cgst: Paise;
  readonly sgst: Paise;
  readonly igst: Paise;
  readonly totalTax: Paise;
  readonly lineTotal: Paise;
}

export interface HsnSummaryRow {
  readonly hsnCode: string;
  readonly gstRate: number;
  readonly taxableValue: Paise;
  readonly cgst: Paise;
  readonly sgst: Paise;
  readonly igst: Paise;
}

export interface TaxSummary {
  readonly kind: TaxKind;
  readonly gstEnabled: boolean;
  readonly lines: readonly ComputedLine[];
  /** Sum of line taxable values, after line discounts. */
  readonly subtotal: Paise;
  readonly totalDiscount: Paise;
  readonly shipping: Paise;
  readonly cgst: Paise;
  readonly sgst: Paise;
  readonly igst: Paise;
  readonly totalTax: Paise;
  /** Signed rounding adjustment shown as the "Round Off" line. */
  readonly roundOff: Paise;
  /** What the customer actually pays. Always a whole number of rupees. */
  readonly grandTotal: Paise;
  readonly hsnSummary: readonly HsnSummaryRow[];
}

export function stateNameForCode(code: string): string {
  return GST_STATE_CODES[code] ?? 'Unknown';
}

/** First two characters of a GSTIN are the state code of the registration. */
export function stateCodeFromGstin(gstin: string): string | null {
  const normalised = gstin.trim().toUpperCase();
  if (!isValidGstin(normalised)) return null;
  return normalised.slice(0, 2);
}

const GSTIN_PATTERN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z{1}[0-9A-Z]{1}$/;
const GSTIN_CHECKSUM_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';

/**
 * Structural + checksum validation of a GSTIN.
 *
 * The 15th character is a mod-36 check digit computed over the first 14, with
 * alternating weights of 1 and 2. A typo'd buyer GSTIN on an outward invoice is
 * a mismatch in GSTR-1, so it is worth rejecting at entry rather than at filing.
 */
export function isValidGstin(gstin: string): boolean {
  const value = gstin.trim().toUpperCase();
  if (!GSTIN_PATTERN.test(value)) return false;
  if (!(value.slice(0, 2) in GST_STATE_CODES)) return false;

  let total = 0;
  for (let i = 0; i < 14; i += 1) {
    const codePoint = GSTIN_CHECKSUM_ALPHABET.indexOf(value[i] as string);
    if (codePoint < 0) return false;
    const weighted = codePoint * (i % 2 === 0 ? 1 : 2);
    total += Math.floor(weighted / 36) + (weighted % 36);
  }
  const checkDigit = GSTIN_CHECKSUM_ALPHABET[(36 - (total % 36)) % 36];
  return checkDigit === value[14];
}

/**
 * Intra-state (CGST + SGST) when buyer and seller sit in the same state,
 * inter-state (IGST) otherwise.
 */
export function determineTaxKind(
  sellerStateCode: string,
  placeOfSupplyStateCode: string,
): TaxKind {
  return sellerStateCode === placeOfSupplyStateCode ? 'intra_state' : 'inter_state';
}

export interface ComputeOptions {
  readonly sellerStateCode: string;
  readonly placeOfSupplyStateCode: string;
  readonly gstEnabled: boolean;
  /** Shipping/delivery charge, taxed at the highest rate present on the order. */
  readonly shipping?: Paise;
  /**
   * Order-level discount spread proportionally across lines before tax.
   * Applying it after tax would over-collect GST on value never received.
   */
  readonly orderDiscount?: Paise;
}

/**
 * Compute a complete tax breakdown for a set of lines.
 *
 * Order of operations matters and follows the invoice rules:
 *   1. line discount   → 2. proportional order discount   → 3. taxable value
 *   4. GST per line    → 5. shipping (taxed)              → 6. round off
 */
export function computeTax(
  lines: readonly TaxableLine[],
  options: ComputeOptions,
): TaxSummary {
  const kind = determineTaxKind(options.sellerStateCode, options.placeOfSupplyStateCode);
  const shipping = options.shipping ?? 0;
  const orderDiscount = options.orderDiscount ?? 0;

  // Gross value per line, after any line-level discount.
  const grossValues = lines.map((line) => {
    const gross = line.unitPrice * line.quantity;
    const lineDiscount = line.discount ?? 0;
    if (lineDiscount > gross) {
      throw new RangeError(
        `Discount ${lineDiscount} exceeds line value ${gross} on "${line.description}"`,
      );
    }
    return gross - lineDiscount;
  });

  const grossTotal = sum(grossValues);
  if (orderDiscount > grossTotal) {
    throw new RangeError(
      `Order discount ${orderDiscount} exceeds order value ${grossTotal}`,
    );
  }

  // Spread the order discount proportionally, then hand any rounding remainder
  // to the largest line so the shares sum back to exactly `orderDiscount`.
  const discountShares = proportionalShares(grossValues, orderDiscount);

  const computed: ComputedLine[] = lines.map((line, index) => {
    const gross = grossValues[index] as Paise;
    const share = discountShares[index] as Paise;
    const taxableValue = gross - share;
    const rate = options.gstEnabled ? line.gstRate : 0;

    const cgst = kind === 'intra_state' ? percentOf(taxableValue, rate / 2) : 0;
    const sgst = kind === 'intra_state' ? percentOf(taxableValue, rate / 2) : 0;
    const igst = kind === 'inter_state' ? percentOf(taxableValue, rate) : 0;
    const totalTax = cgst + sgst + igst;

    return {
      ...line,
      discount: (line.discount ?? 0) + share,
      taxableValue,
      cgst,
      sgst,
      igst,
      totalTax,
      lineTotal: taxableValue + totalTax,
    };
  });

  // Delivery is a composite supply: it carries the rate of the principal
  // supply, which we take as the highest rate on the order.
  const shippingRate = options.gstEnabled
    ? lines.reduce((highest, line) => Math.max(highest, line.gstRate), 0)
    : 0;
  const shippingCgst = kind === 'intra_state' ? percentOf(shipping, shippingRate / 2) : 0;
  const shippingSgst = kind === 'intra_state' ? percentOf(shipping, shippingRate / 2) : 0;
  const shippingIgst = kind === 'inter_state' ? percentOf(shipping, shippingRate) : 0;

  const subtotal = sum(computed.map((line) => line.taxableValue));
  const cgst = sum(computed.map((line) => line.cgst)) + shippingCgst;
  const sgst = sum(computed.map((line) => line.sgst)) + shippingSgst;
  const igst = sum(computed.map((line) => line.igst)) + shippingIgst;
  const totalTax = cgst + sgst + igst;

  const beforeRounding = subtotal + shipping + totalTax;
  const { rounded, adjustment } = roundToRupee(beforeRounding);

  return {
    kind,
    gstEnabled: options.gstEnabled,
    lines: computed,
    subtotal,
    totalDiscount: sum(computed.map((line) => line.discount)),
    shipping,
    cgst,
    sgst,
    igst,
    totalTax,
    roundOff: adjustment,
    grandTotal: rounded,
    hsnSummary: summariseByHsn(computed, {
      shipping,
      shippingRate,
      shippingCgst,
      shippingSgst,
      shippingIgst,
    }),
  };
}

/**
 * Distribute `total` across `weights` proportionally, with the remainder given
 * to the heaviest entry so the shares always sum to `total` exactly.
 */
function proportionalShares(weights: readonly Paise[], total: Paise): Paise[] {
  if (total === 0 || weights.length === 0) return weights.map(() => 0);
  const weightTotal = sum(weights);
  if (weightTotal === 0) return allocate(total, weights.length);

  const shares = weights.map((weight) => Math.floor((weight * total) / weightTotal));
  let remainder = total - sum(shares);

  // Hand out leftover paise starting from the largest line.
  const order = weights
    .map((weight, index) => ({ weight, index }))
    .sort((a, b) => b.weight - a.weight);
  let cursor = 0;
  while (remainder > 0 && order.length > 0) {
    const target = order[cursor % order.length] as { index: number };
    shares[target.index] = (shares[target.index] as number) + 1;
    remainder -= 1;
    cursor += 1;
  }
  return shares;
}

interface ShippingTax {
  shipping: Paise;
  shippingRate: number;
  shippingCgst: Paise;
  shippingSgst: Paise;
  shippingIgst: Paise;
}

/**
 * The HSN-wise summary table that GSTR-1 expects on the face of the invoice.
 * Lines sharing an HSN *and* a rate collapse into one row.
 */
function summariseByHsn(
  lines: readonly ComputedLine[],
  shippingTax: ShippingTax,
): HsnSummaryRow[] {
  const rows = new Map<string, HsnSummaryRow>();

  const add = (row: HsnSummaryRow): void => {
    const key = `${row.hsnCode}|${row.gstRate}`;
    const existing = rows.get(key);
    rows.set(
      key,
      existing
        ? {
            ...existing,
            taxableValue: existing.taxableValue + row.taxableValue,
            cgst: existing.cgst + row.cgst,
            sgst: existing.sgst + row.sgst,
            igst: existing.igst + row.igst,
          }
        : row,
    );
  };

  for (const line of lines) {
    add({
      hsnCode: line.hsnCode,
      gstRate: line.gstRate,
      taxableValue: line.taxableValue,
      cgst: line.cgst,
      sgst: line.sgst,
      igst: line.igst,
    });
  }

  if (shippingTax.shipping > 0) {
    // SAC 996812 — courier / delivery services.
    add({
      hsnCode: '996812',
      gstRate: shippingTax.shippingRate,
      taxableValue: shippingTax.shipping,
      cgst: shippingTax.shippingCgst,
      sgst: shippingTax.shippingSgst,
      igst: shippingTax.shippingIgst,
    });
  }

  return [...rows.values()].sort((a, b) => a.hsnCode.localeCompare(b.hsnCode));
}
