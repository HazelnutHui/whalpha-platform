import { describe, expect, it } from 'vitest';

import { clamp, formatCompact, formatNumber, formatPercent, parseDecimal } from './format';

describe('format utilities', () => {
  it('parses finite decimal strings', () => {
    expect(parseDecimal('0.0125')).toBe(0.0125);
  });

  it('rejects invalid decimal strings', () => {
    expect(() => parseDecimal('NaN')).toThrow('Invalid decimal');
  });

  it('formats percentages and nullable ratios', () => {
    expect(formatPercent('0.01234', { signed: true })).toBe('+1.23%');
    expect(formatPercent(null)).toBe('—');
  });

  it('formats large numbers', () => {
    expect(formatNumber(1234567)).toBe('1,234,567');
    expect(formatCompact('5000000')).toBe('5M');
  });

  it('clamps values for chart colors', () => {
    expect(clamp(10, -1, 1)).toBe(1);
    expect(clamp(-10, -1, 1)).toBe(-1);
  });
});
