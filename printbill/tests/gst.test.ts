import { describe, expect, it } from 'vitest';
import {
  computeTax,
  determineTaxKind,
  isValidGstin,
  stateCodeFromGstin,
  stateNameForCode,
} from '../src/domain/gst.js';
import { sum, toPaise } from '../src/domain/money.js';

const KARNATAKA = '29';
const MAHARASHTRA = '27';

function line(overrides: Partial<Parameters<typeof computeTax>[0][number]> = {}) {
  return {
    id: '1',
    description: 'Custom name plate',
    hsnCode: '3926',
    quantity: 1,
    unitPrice: toPaise(1000),
    gstRate: 18,
    ...overrides,
  };
}

describe('tax kind', () => {
  it('is intra-state when the place of supply matches the seller', () => {
    expect(determineTaxKind(KARNATAKA, KARNATAKA)).toBe('intra_state');
  });

  it('is inter-state otherwise', () => {
    expect(determineTaxKind(KARNATAKA, MAHARASHTRA)).toBe('inter_state');
  });
});

describe('computeTax — intra-state', () => {
  const result = computeTax([line()], {
    sellerStateCode: KARNATAKA,
    placeOfSupplyStateCode: KARNATAKA,
    gstEnabled: true,
  });

  it('splits 18% into CGST 9% + SGST 9% and charges no IGST', () => {
    expect(result.cgst).toBe(toPaise(90));
    expect(result.sgst).toBe(toPaise(90));
    expect(result.igst).toBe(0);
  });

  it('produces a grand total of taxable value plus tax', () => {
    expect(result.subtotal).toBe(toPaise(1000));
    expect(result.grandTotal).toBe(toPaise(1180));
  });
});

describe('computeTax — inter-state', () => {
  const result = computeTax([line()], {
    sellerStateCode: KARNATAKA,
    placeOfSupplyStateCode: MAHARASHTRA,
    gstEnabled: true,
  });

  it('charges the full rate as IGST', () => {
    expect(result.igst).toBe(toPaise(180));
    expect(result.cgst).toBe(0);
    expect(result.sgst).toBe(0);
  });

  it('reaches the same grand total as the intra-state case', () => {
    expect(result.grandTotal).toBe(toPaise(1180));
  });
});

describe('computeTax — internal consistency', () => {
  it('always has line totals that sum to the pre-rounding total', () => {
    const result = computeTax(
      [
        line({ id: 'a', unitPrice: toPaise(333.33), quantity: 3 }),
        line({ id: 'b', unitPrice: toPaise(19.99), quantity: 7, gstRate: 12 }),
        line({ id: 'c', unitPrice: toPaise(1249.5), quantity: 1, gstRate: 5 }),
      ],
      {
        sellerStateCode: KARNATAKA,
        placeOfSupplyStateCode: KARNATAKA,
        gstEnabled: true,
      },
    );

    const lineSum = sum(result.lines.map((entry) => entry.lineTotal));
    expect(lineSum).toBe(result.subtotal + result.totalTax);
    expect(result.grandTotal).toBe(result.subtotal + result.totalTax + result.roundOff);
  });

  it('always returns a whole-rupee grand total', () => {
    for (const price of [1, 7, 33, 99.99, 1234.56, 45_678.9]) {
      const result = computeTax([line({ unitPrice: toPaise(price) })], {
        sellerStateCode: KARNATAKA,
        placeOfSupplyStateCode: KARNATAKA,
        gstEnabled: true,
      });
      expect(result.grandTotal % 100).toBe(0);
    }
  });

  it('splits CGST and SGST into equal halves', () => {
    const result = computeTax([line({ unitPrice: toPaise(777.77) })], {
      sellerStateCode: KARNATAKA,
      placeOfSupplyStateCode: KARNATAKA,
      gstEnabled: true,
    });
    expect(result.cgst).toBe(result.sgst);
  });
});

describe('computeTax — discounts', () => {
  it('spreads an order discount across lines so the shares sum exactly', () => {
    const result = computeTax(
      [
        line({ id: 'a', unitPrice: toPaise(100) }),
        line({ id: 'b', unitPrice: toPaise(200) }),
        line({ id: 'c', unitPrice: toPaise(300) }),
      ],
      {
        sellerStateCode: KARNATAKA,
        placeOfSupplyStateCode: KARNATAKA,
        gstEnabled: true,
        orderDiscount: toPaise(100),
      },
    );

    expect(result.totalDiscount).toBe(toPaise(100));
    expect(result.subtotal).toBe(toPaise(500));
  });

  it('handles a discount that does not divide evenly', () => {
    const result = computeTax(
      [
        line({ id: 'a', unitPrice: toPaise(10) }),
        line({ id: 'b', unitPrice: toPaise(10) }),
        line({ id: 'c', unitPrice: toPaise(10) }),
      ],
      {
        sellerStateCode: KARNATAKA,
        placeOfSupplyStateCode: KARNATAKA,
        gstEnabled: true,
        orderDiscount: 1, // one paise across three equal lines
      },
    );
    expect(result.totalDiscount).toBe(1);
    expect(result.subtotal).toBe(toPaise(30) - 1);
  });

  it('rejects a discount larger than the order', () => {
    expect(() =>
      computeTax([line({ unitPrice: toPaise(100) })], {
        sellerStateCode: KARNATAKA,
        placeOfSupplyStateCode: KARNATAKA,
        gstEnabled: true,
        orderDiscount: toPaise(200),
      }),
    ).toThrow(RangeError);
  });

  it('rejects a line discount larger than the line', () => {
    expect(() =>
      computeTax([line({ unitPrice: toPaise(100), discount: toPaise(200) })], {
        sellerStateCode: KARNATAKA,
        placeOfSupplyStateCode: KARNATAKA,
        gstEnabled: true,
      }),
    ).toThrow(RangeError);
  });
});

describe('computeTax — shipping', () => {
  it('taxes delivery at the highest rate on the order', () => {
    const result = computeTax(
      [line({ id: 'a', gstRate: 5 }), line({ id: 'b', gstRate: 18 })],
      {
        sellerStateCode: KARNATAKA,
        placeOfSupplyStateCode: KARNATAKA,
        gstEnabled: true,
        shipping: toPaise(100),
      },
    );

    const shippingRow = result.hsnSummary.find((row) => row.hsnCode === '996812');
    expect(shippingRow?.gstRate).toBe(18);
    expect(shippingRow?.taxableValue).toBe(toPaise(100));
  });
});

describe('computeTax — GST disabled', () => {
  it('charges nothing when the seller is unregistered', () => {
    const result = computeTax([line()], {
      sellerStateCode: KARNATAKA,
      placeOfSupplyStateCode: MAHARASHTRA,
      gstEnabled: false,
    });
    expect(result.totalTax).toBe(0);
    expect(result.grandTotal).toBe(toPaise(1000));
  });
});

describe('HSN summary', () => {
  it('collapses lines that share an HSN and a rate', () => {
    const result = computeTax(
      [
        line({ id: 'a', hsnCode: '3926', gstRate: 18 }),
        line({ id: 'b', hsnCode: '3926', gstRate: 18 }),
        line({ id: 'c', hsnCode: '998912', gstRate: 18 }),
      ],
      {
        sellerStateCode: KARNATAKA,
        placeOfSupplyStateCode: KARNATAKA,
        gstEnabled: true,
      },
    );

    expect(result.hsnSummary).toHaveLength(2);
    const plastics = result.hsnSummary.find((row) => row.hsnCode === '3926');
    expect(plastics?.taxableValue).toBe(toPaise(2000));
  });

  it('sums to the order totals', () => {
    const result = computeTax(
      [line({ id: 'a', gstRate: 18 }), line({ id: 'b', gstRate: 12, hsnCode: '9503' })],
      {
        sellerStateCode: KARNATAKA,
        placeOfSupplyStateCode: KARNATAKA,
        gstEnabled: true,
        shipping: toPaise(50),
      },
    );

    expect(sum(result.hsnSummary.map((row) => row.cgst))).toBe(result.cgst);
    expect(sum(result.hsnSummary.map((row) => row.taxableValue))).toBe(
      result.subtotal + result.shipping,
    );
  });
});

describe('GSTIN validation', () => {
  it('accepts valid GSTINs with correct check digits', () => {
    // Real-format identifiers with valid mod-36 check characters.
    expect(isValidGstin('27AAFCS1234R1ZY')).toBe(true);
    expect(isValidGstin('29AABCU9603R1ZJ')).toBe(true);
  });

  it('rejects a wrong check digit', () => {
    expect(isValidGstin('27AAFCS1234R1ZA')).toBe(false);
  });

  it('rejects malformed input', () => {
    expect(isValidGstin('')).toBe(false);
    expect(isValidGstin('29AABCU9603R1Z')).toBe(false); // too short
    expect(isValidGstin('99AABCU9603R1ZM')).toBe(false); // no such state
    expect(isValidGstin('29aabcu9603r1zx')).toBe(false); // wrong check for lowercase input
  });

  it('extracts the state code', () => {
    expect(stateCodeFromGstin('29AABCU9603R1ZJ')).toBe('29');
    expect(stateCodeFromGstin('not-a-gstin')).toBeNull();
  });

  it('names states from their codes', () => {
    expect(stateNameForCode('29')).toBe('Karnataka');
    expect(stateNameForCode('99')).toBe('Unknown');
  });
});
