import { describe, expect, it } from 'vitest';

import { clamp, formatCompact, formatCurrencyCompact, formatNumber, formatPercent, formatRatio, parseDecimal } from './format';

describe('format utilities', () => {
  it('parses finite decimal strings', () => {
    expect(parseDecimal('0.0125')).toBe(0.0125);
  });

  it('rejects invalid decimal strings', () => {
    expect(() => parseDecimal('NaN')).toThrow('Invalid decimal');
  });

  it('formats percentages and nullable ratios', () => {
    expect(formatPercent('0.01234', { signed: true })).toBe('+1.23%');
    expect(formatPercent('-0.02345', { signed: true })).toBe('-2.35%');
    expect(formatPercent('0', { signed: true })).toBe('0.00%');
    expect(formatPercent(null)).toBe('—');
  });

  it('formats large numbers', () => {
    expect(formatNumber(1234567)).toBe('1,234,567');
    expect(formatCompact('5000000')).toBe('5.00M');
    expect(formatCompact('9386830217.702339')).toBe('9.39B');
  });

  it('formats ratios and compact currency without long decimals', () => {
    expect(formatRatio('1.80456789')).toBe('1.80×');
    expect(formatRatio(null)).toBe('—');
    expect(() => formatRatio('Infinity')).toThrow('Invalid ratio');
    expect(formatCurrencyCompact('1250000000')).toBe('$1.25B');
    expect(formatCurrencyCompact('123.456')).toBe('$123.46');
  });

  it('clamps values for chart colors', () => {
    expect(clamp(10, -1, 1)).toBe(1);
    expect(clamp(-10, -1, 1)).toBe(-1);
  });
});
