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

function finiteNumber(value: number | string | null, fieldName: string): number | null {
  if (value === null) {
    return null;
  }
  const parsed = typeof value === 'string' ? parseDecimal(value, fieldName) : value;
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
  const rounded = Math.round((value + Math.sign(value) * 1e-10) * 100) / 100;
  return `${sign}${rounded.toFixed(2)}%`;
}

export function formatRatio(decimal: string | number | null): string {
  const value = finiteNumber(decimal, 'ratio');
  if (value === null || !Number.isFinite(value)) {
    return '—';
  }
  if (Math.abs(value) >= 1000) {
    return `${formatCompact(value)}×`;
  }
  return `${value.toFixed(2)}×`;
}

export function formatNumber(value: number | string | null, maximumFractionDigits = 0): string {
  if (value === null) {
    return '—';
  }
  const parsed = finiteNumber(value, 'number');
  if (parsed === null) {
    return '—';
  }
  return new Intl.NumberFormat('en-US', { maximumFractionDigits }).format(parsed);
}

export function formatPrice(decimal: string | null): string {
  if (decimal === null) {
    return '—';
  }
  return `$${formatNumber(decimal, 2)}`;
}

export function formatCompact(decimal: string | number | null): string {
  const parsed = finiteNumber(decimal, 'compact number');
  if (parsed === null) {
    return '—';
  }
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    minimumFractionDigits: Math.abs(parsed) >= 1000000 ? 2 : 0,
    maximumFractionDigits: 2,
  }).format(parsed);
}

export function formatCurrencyCompact(decimal: string | number | null): string {
  const parsed = finiteNumber(decimal, 'currency');
  if (parsed === null) {
    return '—';
  }
  if (Math.abs(parsed) >= 1000000) {
    return `$${formatCompact(parsed)}`;
  }
  return `$${formatNumber(parsed, 2)}`;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
