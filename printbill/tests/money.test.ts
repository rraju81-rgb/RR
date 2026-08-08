import { describe, expect, it } from 'vitest';
import {
  allocate,
  amountInWords,
  formatAmount,
  formatINR,
  multiply,
  percentOf,
  roundToRupee,
  sum,
  toPaise,
  toRupees,
} from '../src/domain/money.js';

describe('paise conversion', () => {
  it('round-trips whole and fractional rupees', () => {
    expect(toPaise(1)).toBe(100);
    expect(toPaise(1234.56)).toBe(123_456);
    expect(toRupees(123_456)).toBe(1234.56);
  });

  it('avoids the float error that plain arithmetic would introduce', () => {
    // 0.1 + 0.2 === 0.30000000000000004 in float rupees.
    expect(toPaise(0.1) + toPaise(0.2)).toBe(toPaise(0.3));
  });

  it('rejects non-integer paise', () => {
    expect(() => multiply(10.5 as never, 2)).toThrow(TypeError);
  });
});

describe('multiply', () => {
  it('rounds half up', () => {
    expect(multiply(100, 0.185)).toBe(19); // 18.5 → 19
    expect(multiply(100, 0.184)).toBe(18);
  });

  it('is symmetric for negatives, so credit notes mirror invoices', () => {
    expect(multiply(-100, 0.185)).toBe(-19);
    expect(multiply(-100, 0.185)).toBe(-multiply(100, 0.185));
  });

  it('computes percentages', () => {
    expect(percentOf(10_000, 18)).toBe(1800);
    expect(percentOf(10_000, 9)).toBe(900);
  });
});

describe('allocate', () => {
  it('distributes remainders so the parts sum to the whole', () => {
    const parts = allocate(1000, 3);
    expect(parts).toEqual([334, 333, 333]);
    expect(sum(parts)).toBe(1000);
  });

  it('handles exact divisions', () => {
    expect(allocate(900, 3)).toEqual([300, 300, 300]);
  });

  it('handles negative amounts without losing a paise', () => {
    const parts = allocate(-1000, 3);
    expect(sum(parts)).toBe(-1000);
  });

  it('rejects a non-positive part count', () => {
    expect(() => allocate(100, 0)).toThrow(RangeError);
  });
});

describe('roundToRupee', () => {
  it('rounds up and reports the adjustment', () => {
    expect(roundToRupee(10_060)).toEqual({ rounded: 10_100, adjustment: 40 });
  });

  it('rounds down and reports a negative adjustment', () => {
    expect(roundToRupee(10_022)).toEqual({ rounded: 10_000, adjustment: -22 });
  });

  it('leaves whole rupees untouched', () => {
    expect(roundToRupee(10_000)).toEqual({ rounded: 10_000, adjustment: 0 });
  });

  it('keeps the adjustment within half a rupee', () => {
    for (let paise = 0; paise < 500; paise += 1) {
      expect(Math.abs(roundToRupee(paise).adjustment)).toBeLessThanOrEqual(50);
    }
  });
});

describe('formatting', () => {
  it('groups digits the Indian way', () => {
    expect(formatAmount(100)).toBe('1.00');
    expect(formatAmount(123_456)).toBe('1,234.56');
    expect(formatAmount(12_345_678)).toBe('1,23,456.78');
    expect(formatAmount(1_234_567_890)).toBe('1,23,45,678.90');
  });

  it('handles negatives and the rupee sign', () => {
    expect(formatAmount(-123_456)).toBe('-1,234.56');
    expect(formatINR(50_000)).toBe('₹500.00');
  });
});

describe('amountInWords', () => {
  it('writes whole rupees', () => {
    expect(amountInWords(506_000)).toBe('Rupees Five Thousand Sixty Only');
  });

  it('includes paise when present', () => {
    expect(amountInWords(123_456)).toBe(
      'Rupees One Thousand Two Hundred Thirty Four and Fifty Six Paise Only',
    );
  });

  it('uses lakh and crore', () => {
    expect(amountInWords(1_000_000_00)).toContain('Ten Lakh');
    expect(amountInWords(10_000_000_00)).toContain('One Crore');
  });

  it('handles zero', () => {
    expect(amountInWords(0)).toBe('Rupees Zero Only');
  });
});
