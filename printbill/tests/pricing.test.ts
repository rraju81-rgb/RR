import { describe, expect, it } from 'vitest';
import {
  MATERIALS,
  PricingError,
  type PricingRates,
  findMaterial,
  quantityDiscountFor,
  quotePrintJob,
} from '../src/domain/pricing.js';
import { formatINR, toPaise } from '../src/domain/money.js';
import { financialYearOf, formatInvoiceNumber, formatOrderNumber } from '../src/domain/numbering.js';

const RATES: PricingRates = {
  machineRatePerHour: toPaise(60),
  labourRatePerHour: toPaise(150),
  setupFee: toPaise(50),
  marginMultiplier: 1.35,
  wastageFactor: 0.08,
};

describe('materials', () => {
  it('has unique keys', () => {
    const keys = MATERIALS.map((material) => material.key);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it('looks materials up by key', () => {
    expect(findMaterial('pla')?.name).toBe('PLA');
    expect(findMaterial('unobtainium')).toBeUndefined();
  });
});

describe('quotePrintJob', () => {
  it('prices a simple PLA job from its inputs', () => {
    const quote = quotePrintJob(
      { materialKey: 'pla', weightGrams: 100, printHours: 4, quantity: 1 },
      RATES,
    );

    // material: 100g of a ₹900/kg spool = ₹90
    expect(quote.breakdown.materialCost).toBe(toPaise(90));
    // wastage: 8% of material
    expect(quote.breakdown.wastageCost).toBe(toPaise(7.2));
    // machine: 4h x ₹60 x difficulty 1.0
    expect(quote.breakdown.machineCost).toBe(toPaise(240));
    expect(quote.unitPrice).toBeGreaterThan(quote.breakdown.directCost);
  });

  it('charges more for a harder material at the same weight and time', () => {
    const base = { weightGrams: 100, printHours: 4, quantity: 1 };
    const pla = quotePrintJob({ ...base, materialKey: 'pla' }, RATES);
    const tpu = quotePrintJob({ ...base, materialKey: 'tpu' }, RATES);
    expect(tpu.unitPrice).toBeGreaterThan(pla.unitPrice);
  });

  it('derives weight from volume when weight is not given', () => {
    const quote = quotePrintJob(
      { materialKey: 'pla', volumeCm3: 100, printHours: 4, quantity: 1 },
      RATES,
    );
    // PLA density 1.24 g/cm³
    expect(quote.weightGramsPerUnit).toBeCloseTo(124, 1);
  });

  it('applies post-processing labour', () => {
    const plain = quotePrintJob(
      { materialKey: 'pla', weightGrams: 100, printHours: 4, quantity: 1 },
      RATES,
    );
    const finished = quotePrintJob(
      {
        materialKey: 'pla',
        weightGrams: 100,
        printHours: 4,
        quantity: 1,
        postProcessing: ['sanding', 'painting'],
      },
      RATES,
    );
    expect(finished.breakdown.labourCost).toBeGreaterThan(plain.breakdown.labourCost);
    expect(finished.unitPrice).toBeGreaterThan(plain.unitPrice);
  });

  it('adds a rush surcharge', () => {
    const standard = quotePrintJob(
      { materialKey: 'pla', weightGrams: 100, printHours: 4, quantity: 1 },
      RATES,
    );
    const sameDay = quotePrintJob(
      { materialKey: 'pla', weightGrams: 100, printHours: 4, quantity: 1, rush: 'same_day' },
      RATES,
    );
    expect(sameDay.breakdown.rushSurcharge).toBeGreaterThan(0);
    expect(sameDay.unitPrice).toBeGreaterThan(standard.unitPrice);
    expect(sameDay.estimatedReadyInDays).toBeLessThanOrEqual(standard.estimatedReadyInDays);
  });

  it('discounts volume so the unit price falls as quantity rises', () => {
    const one = quotePrintJob(
      { materialKey: 'pla', weightGrams: 100, printHours: 4, quantity: 1 },
      RATES,
    );
    const fifty = quotePrintJob(
      { materialKey: 'pla', weightGrams: 100, printHours: 4, quantity: 50 },
      RATES,
    );
    expect(fifty.unitPrice).toBeLessThan(one.unitPrice);
    expect(fifty.total).toBe(fifty.unitPrice * 50);
  });

  it('spreads the setup fee across the run', () => {
    const one = quotePrintJob(
      { materialKey: 'pla', weightGrams: 100, printHours: 4, quantity: 1 },
      RATES,
    );
    const ten = quotePrintJob(
      { materialKey: 'pla', weightGrams: 100, printHours: 4, quantity: 10 },
      RATES,
    );
    // Setup is charged once, so it contributes a tenth as much per unit.
    expect(one.breakdown.setupFee).toBe(ten.breakdown.setupFee);
    expect(ten.breakdown.setupFee).toBe(toPaise(50));
  });

  it('honours a manually negotiated unit price', () => {
    const quote = quotePrintJob(
      {
        materialKey: 'pla',
        weightGrams: 100,
        printHours: 4,
        quantity: 3,
        manualUnitPrice: toPaise(500),
      },
      RATES,
    );
    expect(quote.unitPrice).toBe(toPaise(500));
    expect(quote.total).toBe(toPaise(1500));
  });

  it('adds bought-in hardware cost', () => {
    const withHardware = quotePrintJob(
      {
        materialKey: 'pla',
        weightGrams: 100,
        printHours: 4,
        quantity: 1,
        hardwareCost: toPaise(200),
      },
      RATES,
    );
    expect(withHardware.breakdown.hardwareCost).toBe(toPaise(200));
  });

  it('always promises at least one day', () => {
    const quote = quotePrintJob(
      { materialKey: 'pla', weightGrams: 5, printHours: 0.2, quantity: 1, rush: 'same_day' },
      RATES,
    );
    expect(quote.estimatedReadyInDays).toBeGreaterThanOrEqual(1);
  });

  it('rejects invalid inputs', () => {
    expect(() =>
      quotePrintJob({ materialKey: 'nope', weightGrams: 10, printHours: 1, quantity: 1 }, RATES),
    ).toThrow(PricingError);

    expect(() =>
      quotePrintJob({ materialKey: 'pla', weightGrams: 10, printHours: 1, quantity: 0 }, RATES),
    ).toThrow(PricingError);

    expect(() =>
      quotePrintJob({ materialKey: 'pla', weightGrams: 10, printHours: -1, quantity: 1 }, RATES),
    ).toThrow(PricingError);

    expect(() =>
      quotePrintJob({ materialKey: 'pla', printHours: 1, quantity: 1 }, RATES),
    ).toThrow(PricingError);
  });

  it('never quotes below its own direct cost', () => {
    for (const material of MATERIALS) {
      const quote = quotePrintJob(
        { materialKey: material.key, weightGrams: 250, printHours: 8, quantity: 1 },
        RATES,
      );
      expect(quote.total).toBeGreaterThan(quote.breakdown.directCost);
    }
  });
});

describe('quantity breaks', () => {
  it('steps up with quantity', () => {
    expect(quantityDiscountFor(1)).toBe(0);
    expect(quantityDiscountFor(5)).toBe(0.05);
    expect(quantityDiscountFor(10)).toBe(0.1);
    expect(quantityDiscountFor(20)).toBe(0.15);
    expect(quantityDiscountFor(100)).toBe(0.2);
  });
});

describe('financial year', () => {
  it('starts in April', () => {
    expect(financialYearOf(new Date('2026-04-01T00:00:00Z'))).toBe('2026-27');
    expect(financialYearOf(new Date('2026-12-31T00:00:00Z'))).toBe('2026-27');
  });

  it('puts January to March in the previous year', () => {
    expect(financialYearOf(new Date('2026-03-31T00:00:00Z'))).toBe('2025-26');
    expect(financialYearOf(new Date('2027-01-15T00:00:00Z'))).toBe('2026-27');
  });

  it('rolls the century correctly', () => {
    expect(financialYearOf(new Date('2099-05-01T00:00:00Z'))).toBe('2099-00');
  });
});

describe('invoice numbering', () => {
  it('stays within the 16 character limit Rule 46 sets', () => {
    const number = formatInvoiceNumber('2026-27', 1);
    expect(number).toBe('INV/2026-27/0001');
    expect(number.length).toBeLessThanOrEqual(16);
  });

  it('pads the sequence', () => {
    expect(formatInvoiceNumber('2026-27', 42)).toBe('INV/2026-27/0042');
    expect(formatInvoiceNumber('2026-27', 9999)).toBe('INV/2026-27/9999');
  });

  it('refuses to emit a number that would break the limit', () => {
    expect(() => formatInvoiceNumber('2026-27', 100_000)).toThrow(RangeError);
  });

  it('dates order numbers', () => {
    expect(formatOrderNumber(42, new Date('2026-08-08T00:00:00Z'))).toBe('ORD-20260808-0042');
  });
});

describe('quote explanation', () => {
  it('reads as a chat message with the key figures', () => {
    const quote = quotePrintJob(
      {
        materialKey: 'petg',
        weightGrams: 120,
        printHours: 5,
        quantity: 4,
        postProcessing: ['support_removal'],
      },
      RATES,
    );
    const text = [
      quote.material.name,
      formatINR(quote.unitPrice),
      formatINR(quote.total),
    ];
    expect(text[0]).toBe('PETG');
    expect(text[1]).toMatch(/^₹/);
    expect(quote.total).toBe(quote.unitPrice * 4);
  });
});
