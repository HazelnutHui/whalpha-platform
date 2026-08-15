export function parseDecimal(value: string, fieldName = 'decimal'): number {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`Invalid ${fieldName}`);
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(`Invalid ${fieldName}`);
  }
  return parsed;
}

export function formatPercent(decimal: string | null, options: { signed?: boolean } = {}): string {
  if (decimal === null) {
    return '—';
  }
  const value = parseDecimal(decimal, 'percent') * 100;
  const sign = options.signed && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function formatNumber(value: number | string | null, maximumFractionDigits = 0): string {
  if (value === null) {
    return '—';
  }
  const parsed = typeof value === 'string' ? parseDecimal(value, 'number') : value;
  return new Intl.NumberFormat('en-US', { maximumFractionDigits }).format(parsed);
}

export function formatPrice(decimal: string | null): string {
  if (decimal === null) {
    return '—';
  }
  return `$${formatNumber(decimal, 2)}`;
}

export function formatCompact(decimal: string | number | null): string {
  if (decimal === null) {
    return '—';
  }
  const parsed = typeof decimal === 'string' ? parseDecimal(decimal, 'compact number') : decimal;
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 2,
  }).format(parsed);
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
