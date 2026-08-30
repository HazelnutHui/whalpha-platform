export type DecimalString = string;

export type InstrumentType = 'common_stock' | 'etf';

export interface EodReturnResponse {
  instrument_id: string;
  ticker: string;
  name: string;
  instrument_type: string;
  current_session_date: string;
  previous_session_date: string;
  previous_close: DecimalString;
  current_close: DecimalString;
  close_to_close_return: DecimalString;
  current_volume: DecimalString;
  current_vwap: DecimalString | null;
  current_dollar_volume_proxy: DecimalString;
  quality_status: string;
  quality_flags: string[];
}

export interface MarketSummaryResponse {
  current_session_date: string;
  previous_session_date: string;
  comparable_instrument_count: number;
  current_only_count: number;
  previous_only_count: number;
  advancer_count: number;
  decliner_count: number;
  unchanged_count: number;
  advance_decline_ratio: DecimalString | null;
  advance_decline_net: number;
  advancer_volume: DecimalString;
  decliner_volume: DecimalString;
  up_down_volume_ratio: DecimalString | null;
  equal_weight_return: DecimalString | null;
  median_return: DecimalString | null;
  positive_return_share: DecimalString | null;
  negative_return_share: DecimalString | null;
  common_stock_comparable_count: number;
  etf_comparable_count: number;
  quality_warning_count: number;
  data_status: string;
}

export interface MoversResponse {
  current_session_date: string;
  previous_session_date: string;
  threshold: DecimalString;
  top_gainers: EodReturnResponse[];
  top_losers: EodReturnResponse[];
}

export interface LiquidityMapNodeResponse {
  instrument_id: string;
  ticker: string;
  name: string;
  instrument_type: string;
  size_value: DecimalString;
  color_value: DecimalString;
  current_close: DecimalString;
  current_volume: DecimalString;
  rank: number;
  quality_flags: string[];
}

export interface LiquidityMapResponse {
  map_type: string;
  size_metric: string;
  color_metric: string;
  is_market_cap_weighted: boolean;
  is_sector_grouped: boolean;
  threshold: DecimalString;
  current_session_date: string;
  previous_session_date: string;
  nodes: LiquidityMapNodeResponse[];
}

export interface DashboardUniverseDefinitionResponse {
  universe_id: string;
  name: string;
  display_name: string;
  description: string;
  long_display_name: string;
  provisional: boolean;
  member_count: number;
  security_type_composition: Record<string, number>;
  membership_fingerprint: string;
}

export interface DashboardUniverseAuditResponse {
  raw_comparable_count: number;
  common_stock_count: number;
  adr_count: number | null;
  etf_count: number;
  other_excluded_type_count: number;
  major_exchange_count: number;
  price_gate_count: number;
  final_count: number;
  exclusion_counts: Record<string, number>;
}

export interface DashboardUniverseFunnelStageResponse {
  universe_id: string;
  stage_index: number;
  stage_id: string;
  display_label: string;
  input_count: number;
  excluded_count: number;
  remaining_count: number;
  source_revision: string;
  source_session: string;
  source_fingerprint: string;
}

export interface DashboardUniverseViewResponse {
  definition: DashboardUniverseDefinitionResponse;
  audit: DashboardUniverseAuditResponse;
  summary: MarketSummaryResponse;
  movers: MoversResponse;
  trading_activity_map: LiquidityMapResponse;
  outlier_review_count: number;
  quality_flag_counts: Record<string, number>;
  equal_weight_benchmark: MarketBenchmarkResponse;
  funnel: DashboardUniverseFunnelStageResponse[];
}

export interface SectorBenchmarkEtfResponse {
  ticker: string;
  sector: string;
  available: boolean;
  current_session_date: string;
  previous_session_date: string;
  previous_close: DecimalString | null;
  current_close: DecimalString | null;
  close_to_close_return: DecimalString | null;
  relative_to_spy_return: DecimalString | null;
  quality_flags: string[];
}

export interface MarketBenchmarkResponse {
  benchmark_id: string;
  label: string;
  ticker: string | null;
  available: boolean;
  current_session_date: string;
  previous_session_date: string;
  previous_close: DecimalString | null;
  current_close: DecimalString | null;
  close_to_close_return: DecimalString | null;
  quality_flags: string[];
}

export interface DashboardOverviewResponse {
  contract_version: string;
  default_universe_id: string;
  selected_universe_id: string;
  universe_definition_id: string;
  universe_version: string;
  governance_status: string;
  classification_as_of_date: string;
  trailing_window_start: string;
  trailing_window_end: string;
  trailing_window_session_count: number;
  reviewed_override_count: number;
  activation_fingerprint: string;
  legacy_rollback_available: boolean;
  evidence_coverage_status: string;
  current_session_date: string;
  previous_session_date: string;
  data_as_of_label: string;
  snapshot_generated_at: string | null;
  snapshot_validation_status: string;
  freshness_status: string;
  expected_latest_completed_session: string | null;
  actual_latest_completed_session: string | null;
  session_lag: number | null;
  calendar_id: string;
  freshness_checked_at: string;
  universes: DashboardUniverseViewResponse[];
  market_benchmarks: MarketBenchmarkResponse[];
  sector_benchmarks: SectorBenchmarkEtfResponse[];
  data_status: 'complete' | 'insufficient_data' | 'synthetic_demo' | 'file_schema_consistency_checks_passed' | 'stale_review';
  review_mode?: boolean;
  review_contract_version?: string | null;
  review_approved_as_of_session?: string | null;
  review_expected_latest_session?: string | null;
  review_expected_lag_sessions?: number | null;
}

export interface SnapshotManifestResponse {
  snapshot_contract_version: string;
  release_id: string;
  generated_at: string;
  current_session_date: string;
  previous_session_date: string;
  expected_latest_completed_session?: string | null;
  actual_latest_completed_session?: string | null;
  session_lag?: number | null;
  freshness_status?: string | null;
  calendar_id?: string | null;
  freshness_checked_at?: string | null;
  data_status: 'complete' | 'insufficient_data' | 'stale_review';
  overview_file?: string;
  summary_file: string;
  movers_file: string;
  liquidity_map_file: string;
  file_sha256: Record<string, string>;
  summary_node_count: number;
  mover_gainer_count: number;
  mover_loser_count: number;
  liquidity_node_count: number;
  warning_count: number;
  universe_definition_id?: string;
  universe_version?: string;
  governance_status?: string;
  classification_as_of_date?: string | null;
  evidence_coverage_status?: string;
  selected_universe_id?: string;
  available_universe_ids?: string[];
  activation_fingerprint?: string;
  membership_evidence_as_of?: string;
  funnel_stage_count?: number;
  funnel_source_fingerprint?: string;
  dashboard_contract_version?: string;
  default_universe_id?: string;
  market_intelligence_file?: string | null;
  market_intelligence_publication_id?: string | null;
  market_intelligence_payload_sha256?: string | null;
  market_intelligence_logical_fingerprint?: string | null;
  analytics_payload_logical_fingerprint?: string | null;
  opportunity_candidates_file?: string | null;
  candidate_contract_version?: string | null;
  candidate_analytics_logical_fingerprint?: string | null;
  candidate_audit_logical_fingerprint?: string | null;
  candidate_parameter_fingerprint?: string | null;
  candidate_state_parameter_fingerprint?: string | null;
  candidate_primary_display_count?: number | null;
  candidate_secondary_display_count?: number | null;
  candidate_publication_contract_version?: string | null;
  entry_geometry_contract_version?: string | null;
  entry_geometry_audit_logical_fingerprint?: string | null;
  entry_geometry_parameter_fingerprint?: string | null;
  entry_lane_consumer_parameter_fingerprint?: string | null;
  candidate_summary_contract_version?: string | null;
  candidate_summary_logical_fingerprint?: string | null;
  candidate_detail_contract_version?: string | null;
  candidate_detail_files?: string[];
  candidate_strategy_file?: string | null;
  candidate_strategy_contract_version?: string | null;
  candidate_strategy_audit_manifest_sha256?: string | null;
  candidate_strategy_audit_logical_fingerprint?: string | null;
  candidate_strategy_parameter_fingerprint?: string | null;
  candidate_strategy_logical_fingerprint?: string | null;
  candidate_visual_context_contract_version?: string | null;
  candidate_visual_context_audit_manifest_sha256?: string | null;
  candidate_visual_context_audit_logical_fingerprint?: string | null;
  candidate_visual_context_batch_fingerprints?: string[];
  sector_rotation_file?: string | null;
  sector_rotation_snapshot_contract_version?: string | null;
  sector_rotation_snapshot_logical_fingerprint?: string | null;
  sector_rotation_audit_manifest_sha256?: string | null;
  sector_rotation_audit_logical_fingerprint?: string | null;
  sector_rotation_parameter_fingerprint?: string | null;
  sector_rotation_history_source_fingerprint?: string | null;
  sector_rotation_product_logical_fingerprint?: string | null;
  review_mode?: boolean;
  review_contract_version?: string | null;
  review_approved_as_of_session?: string | null;
  review_expected_latest_session?: string | null;
  review_expected_lag_sessions?: number | null;
  is_real_provider_backed: boolean;
  access_classification: string;
  contains_raw_provider_data: boolean;
  contains_credentials: boolean;
}

export interface DashboardData {
  overview: DashboardOverviewResponse;
}
