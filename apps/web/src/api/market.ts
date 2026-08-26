import { fetchJson } from './client';
import type { DashboardData, DashboardOverviewResponse, DashboardUniverseAuditResponse, DashboardUniverseDefinitionResponse, DashboardUniverseFunnelStageResponse, DashboardUniverseViewResponse, EodReturnResponse, LiquidityMapNodeResponse, LiquidityMapResponse, MarketBenchmarkResponse, MarketSummaryResponse, MoversResponse, SectorBenchmarkEtfResponse, SnapshotManifestResponse } from './types';

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

function requireNullableNumber(value: Record<string, unknown>, key: string): number | null {
  return value[key] === null ? null : requireNumber(value, key);
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
  const manifest: SnapshotManifestResponse = {
    snapshot_contract_version: requireString(value, 'snapshot_contract_version'),
    release_id: requireString(value, 'release_id'),
    generated_at: requireString(value, 'generated_at'),
    current_session_date: requireString(value, 'current_session_date'),
    previous_session_date: requireString(value, 'previous_session_date'),
    expected_latest_completed_session: value.expected_latest_completed_session === undefined ? undefined : requireNullableString(value, 'expected_latest_completed_session'),
    actual_latest_completed_session: value.actual_latest_completed_session === undefined ? undefined : requireNullableString(value, 'actual_latest_completed_session'),
    session_lag: value.session_lag === undefined ? undefined : requireNullableNumber(value, 'session_lag'),
    freshness_status: value.freshness_status === undefined ? undefined : requireNullableString(value, 'freshness_status'),
    calendar_id: value.calendar_id === undefined ? undefined : requireNullableString(value, 'calendar_id'),
    freshness_checked_at: value.freshness_checked_at === undefined ? undefined : requireNullableString(value, 'freshness_checked_at'),
    data_status: requireString(value, 'data_status'),
    overview_file: typeof value.overview_file === 'string' ? value.overview_file : undefined,
    summary_file: requireString(value, 'summary_file'),
    movers_file: requireString(value, 'movers_file'),
    liquidity_map_file: requireString(value, 'liquidity_map_file'),
    file_sha256: requireHashRecord(value, 'file_sha256'),
    summary_node_count: requireNumber(value, 'summary_node_count'),
    mover_gainer_count: requireNumber(value, 'mover_gainer_count'),
    mover_loser_count: requireNumber(value, 'mover_loser_count'),
    liquidity_node_count: requireNumber(value, 'liquidity_node_count'),
    warning_count: requireNumber(value, 'warning_count'),
    universe_definition_id: typeof value.universe_definition_id === 'string' ? value.universe_definition_id : undefined,
    universe_version: typeof value.universe_version === 'string' ? value.universe_version : undefined,
    governance_status: typeof value.governance_status === 'string' ? value.governance_status : undefined,
    classification_as_of_date: value.classification_as_of_date === undefined ? undefined : requireNullableString(value, 'classification_as_of_date'),
    evidence_coverage_status: typeof value.evidence_coverage_status === 'string' ? value.evidence_coverage_status : undefined,
    funnel_stage_count: value.funnel_stage_count === undefined ? undefined : requireNumber(value, 'funnel_stage_count'),
    funnel_source_fingerprint: typeof value.funnel_source_fingerprint === 'string' ? value.funnel_source_fingerprint : undefined,
    is_real_provider_backed: requireBoolean(value, 'is_real_provider_backed'),
    access_classification: requireString(value, 'access_classification'),
    contains_raw_provider_data: requireBoolean(value, 'contains_raw_provider_data'),
    contains_credentials: requireBoolean(value, 'contains_credentials'),
  };
  if (!['1', '1.1', '1.2', '1.3', '1.4'].includes(manifest.snapshot_contract_version) || manifest.access_classification !== 'private') {
    throw new Error('Unsupported private dashboard snapshot');
  }
  if (manifest.snapshot_contract_version === '1.1' && (
    manifest.expected_latest_completed_session === undefined ||
    manifest.actual_latest_completed_session === undefined ||
    manifest.session_lag === undefined ||
    manifest.freshness_status === undefined ||
    manifest.calendar_id === undefined ||
    manifest.freshness_checked_at === undefined
  )) {
    throw new Error('Private dashboard snapshot is missing freshness metadata');
  }
  if (manifest.snapshot_contract_version === '1.2' && (
    !manifest.universe_definition_id || !manifest.universe_version ||
    manifest.governance_status !== 'provisional_classification' ||
    !manifest.classification_as_of_date || manifest.evidence_coverage_status !== 'incomplete'
  )) {
    throw new Error('Private dashboard snapshot is missing governance metadata');
  }
  if (['1.3', '1.4'].includes(manifest.snapshot_contract_version)) {
    const ids = value.available_universe_ids;
    if (!Array.isArray(ids) || ids.length !== 2 || ids.some((item) => typeof item !== 'string')) throw new Error('Private dashboard snapshot activation catalog is invalid');
    manifest.selected_universe_id = requireString(value, 'selected_universe_id');
    manifest.available_universe_ids = ids as string[];
    manifest.activation_fingerprint = requireString(value, 'activation_fingerprint');
    manifest.membership_evidence_as_of = requireString(value, 'membership_evidence_as_of');
  }
  if (manifest.snapshot_contract_version === '1.4' && (
    manifest.funnel_stage_count !== 20 ||
    !manifest.funnel_source_fingerprint ||
    !/^[0-9a-f]{64}$/.test(manifest.funnel_source_fingerprint)
  )) throw new Error('Private dashboard snapshot Funnel metadata is invalid');
  if (manifest.contains_credentials || manifest.contains_raw_provider_data) {
    throw new Error('Unsafe private dashboard snapshot');
  }
  return manifest;
}

function parseUniverseDefinition(value: unknown): DashboardUniverseDefinitionResponse {
  if (!isRecord(value)) {
    throw new Error('Invalid market API payload: universe definition');
  }
  return {
    universe_id: requireString(value, 'universe_id'),
    name: requireString(value, 'name'),
    display_name: requireString(value, 'display_name'),
    description: requireString(value, 'description'),
    long_display_name: requireString(value, 'long_display_name'),
    provisional: requireBoolean(value, 'provisional'),
    member_count: requireNumber(value, 'member_count'),
    security_type_composition: Object.fromEntries(Object.entries(value.security_type_composition as Record<string, unknown>).map(([key,item])=>[key,Number(item)])),
    membership_fingerprint: requireString(value, 'membership_fingerprint'),
  };
}

function parseUniverseAudit(value: unknown): DashboardUniverseAuditResponse {
  if (!isRecord(value)) {
    throw new Error('Invalid market API payload: universe audit');
  }
  const exclusion = value.exclusion_counts;
  if (!isRecord(exclusion) || Object.values(exclusion).some((item) => typeof item !== 'number')) {
    throw new Error('Invalid market API payload: exclusion_counts');
  }
  return {
    raw_comparable_count: requireNumber(value, 'raw_comparable_count'),
    common_stock_count: requireNumber(value, 'common_stock_count'),
    adr_count: value.adr_count === null ? null : requireNumber(value, 'adr_count'),
    etf_count: requireNumber(value, 'etf_count'),
    other_excluded_type_count: requireNumber(value, 'other_excluded_type_count'),
    major_exchange_count: requireNumber(value, 'major_exchange_count'),
    price_gate_count: requireNumber(value, 'price_gate_count'),
    final_count: requireNumber(value, 'final_count'),
    exclusion_counts: Object.fromEntries(Object.entries(exclusion).map(([key, item]) => [key, item as number])),
  };
}

function parseFunnelStage(value: unknown): DashboardUniverseFunnelStageResponse {
  if (!isRecord(value)) throw new Error('Invalid market API payload: Funnel stage');
  const stage = {
    universe_id: requireString(value, 'universe_id'), stage_index: requireNumber(value, 'stage_index'),
    stage_id: requireString(value, 'stage_id'), display_label: requireString(value, 'display_label'),
    input_count: requireNumber(value, 'input_count'), excluded_count: requireNumber(value, 'excluded_count'),
    remaining_count: requireNumber(value, 'remaining_count'), source_revision: requireString(value, 'source_revision'),
    source_session: requireString(value, 'source_session'), source_fingerprint: requireString(value, 'source_fingerprint'),
  };
  if (stage.input_count - stage.excluded_count !== stage.remaining_count) {
    throw new Error('Invalid market API payload: Funnel stage does not close');
  }
  return stage;
}

function parseUniverseView(value: unknown): DashboardUniverseViewResponse {
  if (!isRecord(value)) {
    throw new Error('Invalid market API payload: universe view');
  }
  const quality = value.quality_flag_counts;
  if (!isRecord(quality) || Object.values(quality).some((item) => typeof item !== 'number')) {
    throw new Error('Invalid market API payload: quality_flag_counts');
  }
  const view = {
    definition: parseUniverseDefinition(value.definition),
    audit: parseUniverseAudit(value.audit),
    summary: parseSummary(value.summary),
    movers: parseMovers(value.movers),
    trading_activity_map: parseLiquidityMap(value.trading_activity_map),
    outlier_review_count: requireNumber(value, 'outlier_review_count'),
    quality_flag_counts: Object.fromEntries(Object.entries(quality).map(([key, item]) => [key, item as number])),
    equal_weight_benchmark: parseMarketBenchmark(value.equal_weight_benchmark),
    funnel: Array.isArray(value.funnel) ? value.funnel.map(parseFunnelStage) : [],
  };
  if (view.funnel.length > 0) {
    if (view.funnel.length !== 10 || view.funnel.some((stage, index) =>
      stage.stage_index !== index + 1 || stage.universe_id !== view.definition.universe_id ||
      (index > 0 && view.funnel[index - 1].remaining_count !== stage.input_count)
    ) || view.funnel[9].remaining_count !== view.definition.member_count) {
      throw new Error('Invalid market API payload: formal Universe Funnel');
    }
  }
  return view;
}

function parseSectorBenchmark(value: unknown): SectorBenchmarkEtfResponse {
  if (!isRecord(value)) {
    throw new Error('Invalid market API payload: sector benchmark');
  }
  return {
    ticker: requireString(value, 'ticker'),
    sector: requireString(value, 'sector'),
    available: requireBoolean(value, 'available'),
    current_session_date: requireString(value, 'current_session_date'),
    previous_session_date: requireString(value, 'previous_session_date'),
    previous_close: requireNullableString(value, 'previous_close'),
    current_close: requireNullableString(value, 'current_close'),
    close_to_close_return: requireNullableString(value, 'close_to_close_return'),
    relative_to_spy_return: requireNullableString(value, 'relative_to_spy_return'),
    quality_flags: requireStringArray(value, 'quality_flags'),
  };
}

function parseMarketBenchmark(value: unknown): MarketBenchmarkResponse {
  if (!isRecord(value)) {
    throw new Error('Invalid market API payload: market benchmark');
  }
  return {
    benchmark_id: requireString(value, 'benchmark_id'),
    label: requireString(value, 'label'),
    ticker: requireNullableString(value, 'ticker'),
    available: requireBoolean(value, 'available'),
    current_session_date: requireString(value, 'current_session_date'),
    previous_session_date: requireString(value, 'previous_session_date'),
    previous_close: requireNullableString(value, 'previous_close'),
    current_close: requireNullableString(value, 'current_close'),
    close_to_close_return: requireNullableString(value, 'close_to_close_return'),
    quality_flags: requireStringArray(value, 'quality_flags'),
  };
}

export function parseDashboardOverview(value: unknown): DashboardOverviewResponse {
  if (!isRecord(value) || !Array.isArray(value.universes) || !Array.isArray(value.market_benchmarks) || !Array.isArray(value.sector_benchmarks)) {
    throw new Error('Invalid market API payload: dashboard overview');
  }
  const reviewMode = value.review_mode === undefined ? false : requireBoolean(value, 'review_mode');
  const reviewContract = value.review_contract_version === undefined ? null : requireNullableString(value, 'review_contract_version');
  const reviewAsOf = value.review_approved_as_of_session === undefined ? null : requireNullableString(value, 'review_approved_as_of_session');
  const reviewExpected = value.review_expected_latest_session === undefined ? null : requireNullableString(value, 'review_expected_latest_session');
  const reviewLag = value.review_expected_lag_sessions === undefined ? null : requireNullableNumber(value, 'review_expected_lag_sessions');
  if (reviewMode && (value.data_status !== 'stale_review' || reviewContract !== 'production-review-deployment/1.0'
    || reviewAsOf === null || reviewExpected === null || reviewLag !== 1)) {
    throw new Error('Invalid market API payload: review deployment');
  }
  if (!reviewMode && [reviewContract, reviewAsOf, reviewExpected, reviewLag].some((item) => item !== null)) {
    throw new Error('Invalid market API payload: unexpected review deployment');
  }
  return {
    contract_version: requireString(value, 'contract_version'),
    default_universe_id: requireString(value, 'default_universe_id'),
    selected_universe_id: requireString(value, 'selected_universe_id'),
    universe_definition_id: requireString(value, 'universe_definition_id'),
    universe_version: requireString(value, 'universe_version'),
    governance_status: requireString(value, 'governance_status'),
    classification_as_of_date: requireString(value, 'classification_as_of_date'),
    trailing_window_start: requireString(value, 'trailing_window_start'),
    trailing_window_end: requireString(value, 'trailing_window_end'),
    trailing_window_session_count: requireNumber(value, 'trailing_window_session_count'),
    reviewed_override_count: requireNumber(value, 'reviewed_override_count'),
    activation_fingerprint: requireString(value, 'activation_fingerprint'),
    legacy_rollback_available: requireBoolean(value, 'legacy_rollback_available'),
    evidence_coverage_status: requireString(value, 'evidence_coverage_status'),
    current_session_date: requireString(value, 'current_session_date'),
    previous_session_date: requireString(value, 'previous_session_date'),
    data_as_of_label: requireString(value, 'data_as_of_label'),
    snapshot_generated_at: requireNullableString(value, 'snapshot_generated_at'),
    snapshot_validation_status: requireString(value, 'snapshot_validation_status'),
    freshness_status: requireString(value, 'freshness_status'),
    expected_latest_completed_session: requireNullableString(value, 'expected_latest_completed_session'),
    actual_latest_completed_session: requireNullableString(value, 'actual_latest_completed_session'),
    session_lag: requireNullableNumber(value, 'session_lag'),
    calendar_id: requireString(value, 'calendar_id'),
    freshness_checked_at: requireString(value, 'freshness_checked_at'),
    universes: value.universes.map(parseUniverseView),
    market_benchmarks: value.market_benchmarks.map(parseMarketBenchmark),
    sector_benchmarks: value.sector_benchmarks.map(parseSectorBenchmark),
    data_status: requireString(value, 'data_status'),
    review_mode: reviewMode,
    review_contract_version: reviewContract,
    review_approved_as_of_session: reviewAsOf,
    review_expected_latest_session: reviewExpected,
    review_expected_lag_sessions: reviewLag,
  };
}

function assertSnapshotConsistency(manifest: SnapshotManifestResponse, data: DashboardData): void {
  const current = manifest.current_session_date;
  const previous = manifest.previous_session_date;
  if (
    data.overview.current_session_date !== current ||
    data.overview.previous_session_date !== previous
  ) {
    throw new Error('Private dashboard snapshot session dates are inconsistent');
  }
}

export async function getMarketDashboardData(signal?: AbortSignal, universeId?: string): Promise<DashboardData> {
  const query = universeId ? `?universe_id=${encodeURIComponent(universeId)}` : '';
  const overview = await fetchJson<unknown>(`/api/v1/private/market/overview/latest${query}`, signal).then(parseDashboardOverview);
  return { overview };
}

export async function getSnapshotDashboardData(signal?: AbortSignal): Promise<{ data: DashboardData; manifest: SnapshotManifestResponse }> {
  const manifest = await fetchJson<unknown>('/private-data/v1/manifest.json', signal).then(parseSnapshotManifest);
  if (!manifest.overview_file) {
    throw new Error('Private dashboard snapshot is missing Dashboard V1.1 overview');
  }
  const overview = await fetchJson<unknown>(`/private-data/v1/${manifest.overview_file}`, signal).then(parseDashboardOverview);
  const data = { overview };
  assertSnapshotConsistency(manifest, data);
  return { data, manifest };
}
