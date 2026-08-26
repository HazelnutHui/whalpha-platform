import { fetchJson } from './client';
import { parseSnapshotManifest } from './market';

export type CandidateRiskMode = 'conservative' | 'balanced' | 'aggressive';
export type CandidateStage = 'watch' | 'prepare' | 'enter' | 'invalidated';
export type CandidateQuality = 'passed' | 'degraded' | 'quarantined' | 'failed';

export interface CandidateMetric {
  metric_id: string; raw_value: string | null; raw_unit: string; normalized_value: string | null;
  availability: 'available' | 'unavailable'; missing_reason: string | null; evidence_type: string;
  source_sessions: string[]; reason_codes: string[];
}
export interface CandidateComponent {
  component_id: string; configured_weight: string; effective_weight: string; score: string | null;
  contribution: string | null; availability: 'available' | 'unavailable'; cap_applied: string | null;
  metrics: CandidateMetric[]; reason_codes: string[];
}
export interface CandidateRiskDisposition {
  risk_mode: CandidateRiskMode; eligible: boolean; risk_adjusted_rank: number | null;
  rejection_reason_codes: string[];
}
export interface CandidateItem {
  instrument_id: string; ticker: string; security_type: 'CS' | 'ADRC'; base_score: string | null;
  adjusted_score: string | null; configured_weight_available: string; missingness_penalty: string;
  confidence: { source_completeness: string; history_completeness: string; relationship_support: string;
    state_confirmation_support: string; confirmation_session_count: number; confidence: string;
    disclaimer: 'data_support_not_success_probability' };
  latest_price: string; median_dollar_volume_20: string | null; annualized_volatility_10: string | null;
  maximum_absolute_open_gap_5: string | null; current_volume_ratio: string | null;
  primary_driver_instrument_id: string | null; primary_driver_ticker: string | null;
  driver_correlation_20: string | null; relationship_kind: 'price_derived_exposure_proxy' | null;
  data_quality_status: CandidateQuality; components: CandidateComponent[];
  evidence: Array<{ evidence_kind: 'supporting' | 'counterevidence'; evidence_id: string;
    component_id: string; observed_value: string | null }>;
  invalidation_condition_codes: string[]; reason_codes: string[]; warning_codes: string[];
  state: { final_stage: CandidateStage | null; transition_status: string; transition_rule_id: string;
    pending_target_stage: CandidateStage | null; stage_confirmation_count: number;
    required_confirmation_sessions: number; breakout_triggered: boolean | null; stale_state: boolean;
    manual_review_required: boolean; gate_results: Array<{ gate_id: string; passed: boolean | null;
      actual_value: string | null; threshold: string | null; boundary_operator: string | null;
      reason_codes: string[] }>; reason_codes: string[]; logical_fingerprint: string };
  risk_dispositions: CandidateRiskDisposition[]; score_logical_fingerprint: string;
}
export interface CandidateRiskResult {
  risk_mode: CandidateRiskMode; eligible_count: number; rejected_count: number; display_cap: number;
  displayed_instrument_ids: string[]; logical_fingerprint: string;
}
export interface CandidateUniverse {
  universe_id: string; universe_member_count: number; membership_fingerprint: string;
  bar_covered_member_count: number; missing_member_count: number;
  quality_counts: Record<string, number>; stage_counts: Record<string, number>;
  risk_modes: CandidateRiskResult[]; candidates: CandidateItem[];
  candidate_batch_logical_fingerprint: string;
}
export interface OpportunityCandidateResponse {
  as_of_session: string; default_universe_id: string; selected_universe_id: string;
  universe_order: string[]; risk_mode_order: CandidateRiskMode[]; source: Record<string, unknown>;
  universe: CandidateUniverse; warnings: string[]; logical_fingerprint: string;
}

const MODES: CandidateRiskMode[] = ['conservative', 'balanced', 'aggressive'];
const COMPONENTS = ['market_alignment', 'etf_sector_alignment', 'stock_relative_strength', 'trend_quality', 'volume_participation', 'volatility_risk', 'liquidity_suitability'];
const STAGES = new Set(['watch', 'prepare', 'enter', 'invalidated']);
const QUALITIES = new Set(['passed', 'degraded', 'quarantined', 'failed']);
const DECIMAL = /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/;
const SHA = /^[0-9a-f]{64}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function record(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new Error(`Invalid Candidate payload: ${label}`);
  return value as Record<string, unknown>;
}
function strings(value: unknown, label: string): string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) throw new Error(`Invalid Candidate payload: ${label}`);
  return value;
}
function number(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || !Number.isInteger(value) || value < 0) throw new Error(`Invalid Candidate payload: ${label}`);
  return value;
}
function decimal(value: unknown, label: string, nullable = false): void {
  if (nullable && value === null) return;
  if (typeof value !== 'string' || !DECIMAL.test(value)) throw new Error(`Invalid Candidate decimal: ${label}`);
}
function digest(value: unknown, label: string): void {
  if (typeof value !== 'string' || !SHA.test(value)) throw new Error(`Invalid Candidate fingerprint: ${label}`);
}

export function parseOpportunityCandidateSnapshot(value: unknown, universeId?: string): OpportunityCandidateResponse {
  const envelope = record(value, 'snapshot');
  if (envelope.schema_version !== '1.0' || envelope.contract_version !== 'opportunity-candidate-snapshot/1.0') throw new Error('Unsupported Candidate snapshot contract');
  const analytics = record(envelope.analytics, 'analytics');
  if (analytics.schema_version !== '1.0' || analytics.contract_version !== 'opportunity-candidate-publication/1.0'
    || analytics.language_neutral !== true || analytics.research_priority_only !== true
    || analytics.underlying_stock_result_not_option_return !== true || analytics.price_volume_not_fund_flow !== true) {
    throw new Error('Unsupported Candidate publication contract');
  }
  digest(analytics.logical_fingerprint, 'analytics');
  if (analytics.logical_fingerprint !== envelope.candidate_analytics_logical_fingerprint) throw new Error('Candidate snapshot analytics binding differs');
  const order = strings(analytics.universe_order, 'Universe order');
  const envelopeOrder = strings(envelope.universe_order, 'snapshot Universe order');
  if (order.length !== 2 || order.join('|') !== envelopeOrder.join('|') || analytics.default_universe_id !== order[0]) throw new Error('Candidate Universe order differs');
  const modes = strings(analytics.risk_mode_order, 'risk modes');
  if (modes.join('|') !== MODES.join('|')) throw new Error('Candidate risk mode order differs');
  if (!Array.isArray(analytics.universes) || analytics.universes.length !== 2) throw new Error('Candidate Universe catalog is incomplete');
  const universes = analytics.universes.map((item, index) => parseUniverse(item, order[index]));
  const selected = universeId ?? String(analytics.default_universe_id);
  const universe = universes.find((item) => item.universe_id === selected);
  if (!universe) throw new Error('Selected Candidate Universe is unavailable');
  return {
    as_of_session: String(analytics.as_of_session), default_universe_id: String(analytics.default_universe_id),
    selected_universe_id: selected, universe_order: order, risk_mode_order: MODES,
    source: record(analytics.source, 'source'), universe, warnings: strings(analytics.warnings, 'warnings'),
    logical_fingerprint: String(analytics.logical_fingerprint),
  };
}

function parseUniverse(value: unknown, expectedId: string): CandidateUniverse {
  const universe = record(value, 'Universe');
  if (universe.universe_id !== expectedId) throw new Error('Candidate Universe identity differs');
  number(universe.universe_member_count, 'member count'); number(universe.bar_covered_member_count, 'covered count'); number(universe.missing_member_count, 'missing count');
  digest(universe.membership_fingerprint, 'membership'); digest(universe.candidate_batch_logical_fingerprint, 'batch');
  if (Number(universe.bar_covered_member_count) + Number(universe.missing_member_count) !== Number(universe.universe_member_count)) throw new Error('Candidate coverage does not reconcile');
  if (!Array.isArray(universe.risk_modes) || universe.risk_modes.length !== 3) throw new Error('Candidate risk results are incomplete');
  const riskModes = universe.risk_modes.map((item, index) => parseRiskResult(item, MODES[index]));
  if (!Array.isArray(universe.candidates)) throw new Error('Candidate cards are unavailable');
  const candidates = universe.candidates.map(parseCandidate);
  const ids = candidates.map((item) => item.instrument_id);
  if (new Set(ids).size !== ids.length || [...ids].sort().join('|') !== ids.join('|')) throw new Error('Candidate stable IDs are duplicated or unordered');
  const published = new Set(ids);
  riskModes.forEach((mode) => mode.displayed_instrument_ids.forEach((id) => { if (!published.has(id)) throw new Error('Candidate rank references an unpublished card'); }));
  return value as CandidateUniverse;
}

function parseRiskResult(value: unknown, mode: CandidateRiskMode): CandidateRiskResult {
  const row = record(value, 'risk result');
  if (row.risk_mode !== mode) throw new Error('Candidate risk mode order differs');
  const eligible = number(row.eligible_count, 'eligible count'); number(row.rejected_count, 'rejected count');
  const cap = number(row.display_cap, 'display cap'); const ids = strings(row.displayed_instrument_ids, 'display IDs'); digest(row.logical_fingerprint, 'risk result');
  if (ids.length !== Math.min(eligible, cap) || new Set(ids).size !== ids.length) throw new Error('Candidate risk display count differs');
  return value as CandidateRiskResult;
}

function parseCandidate(value: unknown): CandidateItem {
  const item = record(value, 'candidate');
  if (typeof item.instrument_id !== 'string' || !UUID.test(item.instrument_id) || typeof item.ticker !== 'string' || !['CS', 'ADRC'].includes(String(item.security_type))) throw new Error('Candidate identity is invalid');
  if (!QUALITIES.has(String(item.data_quality_status))) throw new Error('Candidate quality is unknown');
  decimal(item.base_score, 'base score', true); decimal(item.adjusted_score, 'adjusted score', true); decimal(item.latest_price, 'latest price');
  const state = record(item.state, 'state');
  if (state.final_stage !== null && !STAGES.has(String(state.final_stage))) throw new Error('Candidate stage is unknown');
  digest(state.logical_fingerprint, 'state'); digest(item.score_logical_fingerprint, 'score');
  if (!Array.isArray(item.components) || item.components.length !== COMPONENTS.length) throw new Error('Candidate component ledger is incomplete');
  item.components.forEach((component, index) => {
    const row = record(component, 'component'); if (row.component_id !== COMPONENTS[index]) throw new Error('Candidate component order differs');
    decimal(row.configured_weight, 'configured weight'); decimal(row.effective_weight, 'effective weight'); decimal(row.score, 'component score', true); decimal(row.contribution, 'component contribution', true);
    if (!Array.isArray(row.metrics)) throw new Error('Candidate metrics are unavailable');
  });
  if (!Array.isArray(item.risk_dispositions) || item.risk_dispositions.length !== 3) throw new Error('Candidate dispositions are incomplete');
  item.risk_dispositions.forEach((disposition, index) => {
    const row = record(disposition, 'disposition'); if (row.risk_mode !== MODES[index] || typeof row.eligible !== 'boolean') throw new Error('Candidate disposition order differs');
    const rank = row.risk_adjusted_rank; if (row.eligible ? typeof rank !== 'number' || !Number.isInteger(rank) || rank < 1 : rank !== null) throw new Error('Candidate eligibility and rank differ');
  });
  return value as CandidateItem;
}

export async function getOpportunityCandidates(universeId: string | undefined, signal?: AbortSignal): Promise<OpportunityCandidateResponse> {
  if (import.meta.env.VITE_MARKET_DATA_MODE !== 'snapshot') throw new Error('Candidate API is not enabled');
  const manifest = parseSnapshotManifest(await fetchJson<unknown>('/private-data/v1/manifest.json', signal));
  if (manifest.snapshot_contract_version !== '1.6' || manifest.dashboard_contract_version !== '2.3'
    || manifest.opportunity_candidates_file !== 'opportunity-candidates.json') throw new Error('Candidate snapshot is unavailable');
  const raw = await fetchJson<unknown>(`/private-data/v1/${manifest.opportunity_candidates_file}`, signal);
  const envelope = record(raw, 'snapshot');
  if (envelope.publication_id !== manifest.market_intelligence_publication_id
    || envelope.payload_sha256 !== manifest.market_intelligence_payload_sha256
    || envelope.payload_logical_fingerprint !== manifest.market_intelligence_logical_fingerprint
    || envelope.candidate_analytics_logical_fingerprint !== manifest.candidate_analytics_logical_fingerprint) {
    throw new Error('Candidate Snapshot manifest binding differs');
  }
  const analytics = record(envelope.analytics, 'analytics');
  const source = record(analytics.source, 'source');
  const universes = analytics.universes;
  if (!Array.isArray(universes) || universes.length !== 2) throw new Error('Candidate Snapshot Universe binding differs');
  const primary = record(universes[0], 'Primary'); const secondary = record(universes[1], 'Secondary');
  if (!Array.isArray(primary.candidates) || !Array.isArray(secondary.candidates)
    || primary.candidates.length !== manifest.candidate_primary_display_count
    || secondary.candidates.length !== manifest.candidate_secondary_display_count
    || source.candidate_audit_logical_fingerprint !== manifest.candidate_audit_logical_fingerprint
    || source.candidate_parameter_fingerprint !== manifest.candidate_parameter_fingerprint
    || source.candidate_state_parameter_fingerprint !== manifest.candidate_state_parameter_fingerprint) {
    throw new Error('Candidate Snapshot source or display-count binding differs');
  }
  return parseOpportunityCandidateSnapshot(raw, universeId);
}
