/**
 * Money is stored and computed as an integer number of paise (1/100 rupee).
 *
 * Floating point rupees silently drift — 0.1 + 0.2 !== 0.3 — and a billing
 * system that drifts by a paise produces invoices whose line items do not sum
 * to their own total. Every amount that crosses a module boundary or hits the
 * database is an integer paise value; rupees exist only at the edges (parsing
 * operator input, rendering a PDF, calling a gateway).
 */

export type Paise = number;

const PAISE_PER_UNIT = 100;

/** Rupees (possibly fractional, from operator input) → paise. */
export function toPaise(rupees: number): Paise {
  if (!Number.isFinite(rupees)) {
    throw new TypeError(`Cannot convert non-finite value to paise: ${rupees}`);
  }
  return Math.round(rupees * PAISE_PER_UNIT);
}

/** Paise → rupees as a number. Display only — never feed this back into maths. */
export function toRupees(paise: Paise): number {
  assertPaise(paise);
  return paise / PAISE_PER_UNIT;
}

export function assertPaise(value: unknown): asserts value is Paise {
  if (typeof value !== 'number' || !Number.isInteger(value)) {
    throw new TypeError(`Expected an integer paise amount, received: ${String(value)}`);
  }
}

/**
 * Multiply a paise amount by a decimal factor (a tax rate, a margin, a
 * quantity) and round half-up to the nearest paise.
 *
 * Half-up matches how Indian invoicing software and auditors expect rounding
 * to behave. `Math.round` in JS is half-up for positives but rounds -0.5 to -0,
 * so negatives are handled explicitly to keep credit notes symmetric.
 */
export function multiply(paise: Paise, factor: number): Paise {
  assertPaise(paise);
  if (!Number.isFinite(factor)) {
    throw new TypeError(`Cannot multiply by non-finite factor: ${factor}`);
  }
  const product = paise * factor;
  return product < 0 ? -Math.round(Math.abs(product)) : Math.round(product);
}

/** Percentage of an amount, e.g. `percentOf(10000, 18)` → 1800. */
export function percentOf(paise: Paise, percent: number): Paise {
  return multiply(paise, percent / 100);
}

export function sum(amounts: readonly Paise[]): Paise {
  return amounts.reduce<Paise>((total, amount) => {
    assertPaise(amount);
    return total + amount;
  }, 0);
}

/**
 * Split an amount into `parts` shares that sum exactly back to the original.
 * The remainder paise are distributed one each to the leading shares, so
 * splitting ₹10.00 three ways yields 334 + 333 + 333, not 333 x 3 with a paise
 * lost to rounding.
 */
export function allocate(paise: Paise, parts: number): Paise[] {
  assertPaise(paise);
  if (!Number.isInteger(parts) || parts <= 0) {
    throw new RangeError(`Cannot allocate across ${parts} parts`);
  }
  const base = Math.trunc(paise / parts);
  let remainder = paise - base * parts;
  const step = remainder < 0 ? -1 : 1;
  return Array.from({ length: parts }, () => {
    if (remainder !== 0) {
      remainder -= step;
      return base + step;
    }
    return base;
  });
}

/**
 * Round a total to the nearest rupee, returning the adjustment applied.
 *
 * Indian tax invoices customarily show a "Round Off" line so the payable amount
 * is a whole rupee. The adjustment is signed and always within ±50 paise.
 */
export function roundToRupee(paise: Paise): { rounded: Paise; adjustment: Paise } {
  assertPaise(paise);
  const rounded = Math.round(paise / PAISE_PER_UNIT) * PAISE_PER_UNIT;
  return { rounded, adjustment: rounded - paise };
}

/** `123456` → `"1,234.56"` — Indian digit grouping, no currency symbol. */
export function formatAmount(paise: Paise): string {
  assertPaise(paise);
  const negative = paise < 0;
  const absolute = Math.abs(paise);
  const rupees = Math.trunc(absolute / PAISE_PER_UNIT);
  const fraction = String(absolute % PAISE_PER_UNIT).padStart(2, '0');
  return `${negative ? '-' : ''}${groupIndian(rupees)}.${fraction}`;
}

/** `formatAmount` with the rupee sign, for PDFs and chat messages. */
export function formatINR(paise: Paise): string {
  return `₹${formatAmount(paise)}`;
}

/**
 * Indian grouping: last three digits, then pairs.
 * 1234567 → "12,34,567"
 */
function groupIndian(value: number): string {
  const digits = String(value);
  if (digits.length <= 3) return digits;
  const last3 = digits.slice(-3);
  const rest = digits.slice(0, -3);
  return `${rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',')},${last3}`;
}

const ONES = [
  '',
  'One',
  'Two',
  'Three',
  'Four',
  'Five',
  'Six',
  'Seven',
  'Eight',
  'Nine',
  'Ten',
  'Eleven',
  'Twelve',
  'Thirteen',
  'Fourteen',
  'Fifteen',
  'Sixteen',
  'Seventeen',
  'Eighteen',
  'Nineteen',
];
const TENS = [
  '',
  '',
  'Twenty',
  'Thirty',
  'Forty',
  'Fifty',
  'Sixty',
  'Seventy',
  'Eighty',
  'Ninety',
];

function twoDigitsToWords(value: number): string {
  if (value < 20) return ONES[value] ?? '';
  const tens = TENS[Math.floor(value / 10)] ?? '';
  const ones = ONES[value % 10] ?? '';
  return ones ? `${tens} ${ones}` : tens;
}

function integerToWords(value: number): string {
  if (value === 0) return 'Zero';
  const crore = Math.floor(value / 10_000_000);
  const lakh = Math.floor((value % 10_000_000) / 100_000);
  const thousand = Math.floor((value % 100_000) / 1000);
  const hundred = Math.floor((value % 1000) / 100);
  const rest = value % 100;

  const segments: string[] = [];
  if (crore) segments.push(`${integerToWords(crore)} Crore`);
  if (lakh) segments.push(`${twoDigitsToWords(lakh)} Lakh`);
  if (thousand) segments.push(`${twoDigitsToWords(thousand)} Thousand`);
  if (hundred) segments.push(`${ONES[hundred]} Hundred`);
  if (rest) segments.push(twoDigitsToWords(rest));
  return segments.join(' ');
}

/**
 * "Amount in words" line required on Indian tax invoices.
 * `123456` → "Rupees One Thousand Two Hundred Thirty Four and Fifty Six Paise Only"
 */
export function amountInWords(paise: Paise): string {
  assertPaise(paise);
  const negative = paise < 0;
  const absolute = Math.abs(paise);
  const rupees = Math.trunc(absolute / PAISE_PER_UNIT);
  const fraction = absolute % PAISE_PER_UNIT;

  let words = `Rupees ${integerToWords(rupees)}`;
  if (fraction > 0) {
    words += ` and ${twoDigitsToWords(fraction)} Paise`;
  }
  return `${negative ? 'Minus ' : ''}${words} Only`;
}
