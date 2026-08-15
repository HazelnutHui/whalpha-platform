import { fetchJson } from './client';
import type { DashboardData, EodReturnResponse, LiquidityMapNodeResponse, LiquidityMapResponse, MarketSummaryResponse, MoversResponse, SnapshotManifestResponse } from './types';

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

function requireHashRecord(value: Record<string, unknown>, key: string): Record<string, string> {
  const candidate = value[key];
  if (!isRecord(candidate)) {
    throw new Error(`Invalid market API payload: ${key}`);
  }
  const entries = Object.entries(candidate);
  if (entries.some(([, item]) => typeof item !== 'string' || !/^[0-9a-f]{64}$/.test(item))) {
    throw new Error(`Invalid market API payload: ${key}`);
  }
  return Object.fromEntries(entries) as Record<string, string>;
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

export function parseSnapshotManifest(value: unknown): SnapshotManifestResponse {
  if (!isRecord(value)) {
    throw new Error('Invalid snapshot manifest');
  }
  const manifest = {
    snapshot_contract_version: requireString(value, 'snapshot_contract_version'),
    release_id: requireString(value, 'release_id'),
    generated_at: requireString(value, 'generated_at'),
    current_session_date: requireString(value, 'current_session_date'),
    previous_session_date: requireString(value, 'previous_session_date'),
    data_status: requireString(value, 'data_status'),
    summary_file: requireString(value, 'summary_file'),
    movers_file: requireString(value, 'movers_file'),
    liquidity_map_file: requireString(value, 'liquidity_map_file'),
    file_sha256: requireHashRecord(value, 'file_sha256'),
    summary_node_count: requireNumber(value, 'summary_node_count'),
    mover_gainer_count: requireNumber(value, 'mover_gainer_count'),
    mover_loser_count: requireNumber(value, 'mover_loser_count'),
    liquidity_node_count: requireNumber(value, 'liquidity_node_count'),
    warning_count: requireNumber(value, 'warning_count'),
    is_real_provider_backed: requireBoolean(value, 'is_real_provider_backed'),
    access_classification: requireString(value, 'access_classification'),
    contains_raw_provider_data: requireBoolean(value, 'contains_raw_provider_data'),
    contains_credentials: requireBoolean(value, 'contains_credentials'),
  };
  if (manifest.snapshot_contract_version !== '1' || manifest.access_classification !== 'private') {
    throw new Error('Unsupported private dashboard snapshot');
  }
  if (manifest.contains_credentials || manifest.contains_raw_provider_data) {
    throw new Error('Unsafe private dashboard snapshot');
  }
  return manifest;
}

function assertSnapshotConsistency(manifest: SnapshotManifestResponse, data: DashboardData): void {
  const current = manifest.current_session_date;
  const previous = manifest.previous_session_date;
  if (
    data.summary.current_session_date !== current ||
    data.movers.current_session_date !== current ||
    data.liquidityMap.current_session_date !== current ||
    data.summary.previous_session_date !== previous ||
    data.movers.previous_session_date !== previous ||
    data.liquidityMap.previous_session_date !== previous
  ) {
    throw new Error('Private dashboard snapshot session dates are inconsistent');
  }
  if (data.movers.top_gainers.length !== manifest.mover_gainer_count || data.movers.top_losers.length !== manifest.mover_loser_count || data.liquidityMap.nodes.length !== manifest.liquidity_node_count) {
    throw new Error('Private dashboard snapshot counts are inconsistent');
  }
}

export async function getMarketDashboardData(signal?: AbortSignal): Promise<DashboardData> {
  const [summary, movers, liquidityMap] = await Promise.all([
    fetchJson<unknown>('/api/v1/private/market/summary/latest', signal).then(parseSummary),
    fetchJson<unknown>('/api/v1/private/market/movers/latest?per_side=10', signal).then(parseMovers),
    fetchJson<unknown>('/api/v1/private/market/liquidity-map/latest?limit=300', signal).then(parseLiquidityMap),
  ]);

  return { summary, movers, liquidityMap };
}

export async function getSnapshotDashboardData(signal?: AbortSignal): Promise<{ data: DashboardData; manifest: SnapshotManifestResponse }> {
  const manifest = await fetchJson<unknown>('/private-data/v1/manifest.json', signal).then(parseSnapshotManifest);
  const [summary, movers, liquidityMap] = await Promise.all([
    fetchJson<unknown>(`/private-data/v1/${manifest.summary_file}`, signal).then(parseSummary),
    fetchJson<unknown>(`/private-data/v1/${manifest.movers_file}`, signal).then(parseMovers),
    fetchJson<unknown>(`/private-data/v1/${manifest.liquidity_map_file}`, signal).then(parseLiquidityMap),
  ]);
  const data = { summary, movers, liquidityMap };
  assertSnapshotConsistency(manifest, data);
  return { data, manifest };
}
