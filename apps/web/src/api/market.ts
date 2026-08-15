import { fetchJson } from './client';
import type { DashboardData, EodReturnResponse, LiquidityMapNodeResponse, LiquidityMapResponse, MarketSummaryResponse, MoversResponse } from './types';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requireString(value: Record<string, unknown>, key: string): string {
  const candidate = value[key];
  if (typeof candidate !== 'string' || candidate.length === 0) {
    throw new Error(`Invalid market API payload: ${key}`);
  }
  return candidate;
}

function requireNullableString(value: Record<string, unknown>, key: string): string | null {
  const candidate = value[key];
  if (candidate === null) {
    return null;
  }
  if (typeof candidate !== 'string') {
    throw new Error(`Invalid market API payload: ${key}`);
  }
  return candidate;
}

function requireNumber(value: Record<string, unknown>, key: string): number {
  const candidate = value[key];
  if (typeof candidate !== 'number' || !Number.isFinite(candidate)) {
    throw new Error(`Invalid market API payload: ${key}`);
  }
  return candidate;
}

function requireBoolean(value: Record<string, unknown>, key: string): boolean {
  const candidate = value[key];
  if (typeof candidate !== 'boolean') {
    throw new Error(`Invalid market API payload: ${key}`);
  }
  return candidate;
}

function requireStringArray(value: Record<string, unknown>, key: string): string[] {
  const candidate = value[key];
  if (!Array.isArray(candidate) || candidate.some((item) => typeof item !== 'string')) {
    throw new Error(`Invalid market API payload: ${key}`);
  }
  return candidate;
}

export function parseReturn(value: unknown): EodReturnResponse {
  if (!isRecord(value)) {
    throw new Error('Invalid market API payload: return item');
  }
  return {
    instrument_id: requireString(value, 'instrument_id'),
    ticker: requireString(value, 'ticker'),
    name: requireString(value, 'name'),
    instrument_type: requireString(value, 'instrument_type'),
    current_session_date: requireString(value, 'current_session_date'),
    previous_session_date: requireString(value, 'previous_session_date'),
    previous_close: requireString(value, 'previous_close'),
    current_close: requireString(value, 'current_close'),
    close_to_close_return: requireString(value, 'close_to_close_return'),
    current_volume: requireString(value, 'current_volume'),
    current_vwap: requireNullableString(value, 'current_vwap'),
    current_dollar_volume_proxy: requireString(value, 'current_dollar_volume_proxy'),
    quality_status: requireString(value, 'quality_status'),
    quality_flags: requireStringArray(value, 'quality_flags'),
  };
}

export function parseSummary(value: unknown): MarketSummaryResponse {
  if (!isRecord(value)) {
    throw new Error('Invalid market API payload: summary');
  }
  return {
    current_session_date: requireString(value, 'current_session_date'),
    previous_session_date: requireString(value, 'previous_session_date'),
    comparable_instrument_count: requireNumber(value, 'comparable_instrument_count'),
    current_only_count: requireNumber(value, 'current_only_count'),
    previous_only_count: requireNumber(value, 'previous_only_count'),
    advancer_count: requireNumber(value, 'advancer_count'),
    decliner_count: requireNumber(value, 'decliner_count'),
    unchanged_count: requireNumber(value, 'unchanged_count'),
    advance_decline_ratio: requireNullableString(value, 'advance_decline_ratio'),
    advance_decline_net: requireNumber(value, 'advance_decline_net'),
    advancer_volume: requireString(value, 'advancer_volume'),
    decliner_volume: requireString(value, 'decliner_volume'),
    up_down_volume_ratio: requireNullableString(value, 'up_down_volume_ratio'),
    equal_weight_return: requireNullableString(value, 'equal_weight_return'),
    median_return: requireNullableString(value, 'median_return'),
    positive_return_share: requireNullableString(value, 'positive_return_share'),
    negative_return_share: requireNullableString(value, 'negative_return_share'),
    common_stock_comparable_count: requireNumber(value, 'common_stock_comparable_count'),
    etf_comparable_count: requireNumber(value, 'etf_comparable_count'),
    quality_warning_count: requireNumber(value, 'quality_warning_count'),
    data_status: requireString(value, 'data_status'),
  };
}

export function parseMovers(value: unknown): MoversResponse {
  if (!isRecord(value) || !Array.isArray(value.top_gainers) || !Array.isArray(value.top_losers)) {
    throw new Error('Invalid market API payload: movers');
  }
  return {
    current_session_date: requireString(value, 'current_session_date'),
    previous_session_date: requireString(value, 'previous_session_date'),
    threshold: requireString(value, 'threshold'),
    top_gainers: value.top_gainers.map(parseReturn),
    top_losers: value.top_losers.map(parseReturn),
  };
}

export function parseLiquidityMapNode(value: unknown): LiquidityMapNodeResponse {
  if (!isRecord(value)) {
    throw new Error('Invalid market API payload: liquidity node');
  }
  return {
    instrument_id: requireString(value, 'instrument_id'),
    ticker: requireString(value, 'ticker'),
    name: requireString(value, 'name'),
    instrument_type: requireString(value, 'instrument_type'),
    size_value: requireString(value, 'size_value'),
    color_value: requireString(value, 'color_value'),
    current_close: requireString(value, 'current_close'),
    current_volume: requireString(value, 'current_volume'),
    rank: requireNumber(value, 'rank'),
    quality_flags: requireStringArray(value, 'quality_flags'),
  };
}

export function parseLiquidityMap(value: unknown): LiquidityMapResponse {
  if (!isRecord(value) || !Array.isArray(value.nodes)) {
    throw new Error('Invalid market API payload: liquidity map');
  }
  return {
    map_type: requireString(value, 'map_type'),
    size_metric: requireString(value, 'size_metric'),
    color_metric: requireString(value, 'color_metric'),
    is_market_cap_weighted: requireBoolean(value, 'is_market_cap_weighted'),
    is_sector_grouped: requireBoolean(value, 'is_sector_grouped'),
    threshold: requireString(value, 'threshold'),
    current_session_date: requireString(value, 'current_session_date'),
    previous_session_date: requireString(value, 'previous_session_date'),
    nodes: value.nodes.map(parseLiquidityMapNode),
  };
}

export async function getMarketDashboardData(signal?: AbortSignal): Promise<DashboardData> {
  const [summary, movers, liquidityMap] = await Promise.all([
    fetchJson<unknown>('/api/v1/private/market/summary/latest', signal).then(parseSummary),
    fetchJson<unknown>('/api/v1/private/market/movers/latest?per_side=10', signal).then(parseMovers),
    fetchJson<unknown>('/api/v1/private/market/liquidity-map/latest?limit=300', signal).then(parseLiquidityMap),
  ]);

  return { summary, movers, liquidityMap };
}
