import { fetchJson } from './client';
import { parseSnapshotManifest } from './market';

export type CandidateRiskMode = 'conservative' | 'balanced' | 'aggressive';
export type CandidateStage = 'watch' | 'prepare' | 'enter' | 'invalidated';
export type CandidateQuality = 'passed' | 'degraded' | 'quarantined' | 'failed';
export type CandidateEntryLane = 'review_now' | 'watch_trigger' | 'wait_reset' | 'other_research';
export type CandidateEntryPosture = 'technical_review_ready' | 'monitor_for_trigger' | 'wait_for_reset' | 'deprioritized' | 'not_assessable';
export type CandidateExtensionRisk = 'low' | 'moderate' | 'high' | 'extreme' | 'unavailable';
export type CandidateTechnicalSetup = 'breakout_confirmed' | 'breakout_watch' | 'pullback' | 'strong_but_extended' | 'no_viable_setup' | 'unavailable';

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
export interface CandidateEntryGeometry {
  as_of_session: string; universe_id: string; instrument_id: string; ticker: string;
  security_type: 'CS' | 'ADRC'; candidate_stage: CandidateStage | null;
  candidate_base_score: string | null; relative_strength_component_score: string | null;
  trend_component_score: string | null; volume_climax_risk_candidate: boolean | null;
  extension_risk: CandidateExtensionRisk; technical_setup: CandidateTechnicalSetup;
  review_posture: CandidateEntryPosture; first_rejection_code: string | null;
  why_now_codes: string[]; supporting_fact_codes: string[]; counterevidence_codes: string[];
  what_would_make_reviewable_codes: string[]; technical_invalidation_codes: string[];
  required_manual_check_codes: string[]; warnings: string[]; logical_fingerprint: string;
  metrics: { availability: 'available' | 'unavailable'; close: string | null; sma_10: string | null;
    sma_20: string | null; atr_14: string | null; return_3: string | null; return_5: string | null;
    close_to_sma_10_atr: string | null; close_to_sma_20_atr: string | null;
    move_5_volatility_units: string | null; consecutive_up_sessions: number | null;
    current_gap_atr: string | null; current_range_atr: string | null;
    current_close_location: string | null; current_volume_ratio: string | null;
    prior_five_session_close_high: string | null; prior_five_session_close_low: string | null;
    breakout_distance_atr: string | null; pullback_from_prior_high_atr: string | null;
    reference_support_kind: 'sma20' | 'prior_five_session_close_low' | null;
    reference_support_value: string | null; reference_support_distance_pct: string | null;
    missing_reason_codes: string[] };
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
  entry_geometry?: CandidateEntryGeometry;
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
  entry_risk_modes?: Array<{ risk_mode: CandidateRiskMode; hard_risk_gate_qualified_count: number;
    lanes: Array<{ lane: CandidateEntryLane; qualifying_count: number; display_cap: number;
      displayed_instrument_ids: string[] }>; logical_fingerprint: string }>;
}
export interface OpportunityCandidateResponse {
  as_of_session: string; default_universe_id: string; selected_universe_id: string;
  universe_order: string[]; risk_mode_order: CandidateRiskMode[]; source: Record<string, unknown>;
  universe: CandidateUniverse; warnings: string[]; logical_fingerprint: string;
  publication_contract_version: 'opportunity-candidate-publication/1.0' | 'opportunity-candidate-publication/1.1';
}

const MODES: CandidateRiskMode[] = ['conservative', 'balanced', 'aggressive'];
const COMPONENTS = ['market_alignment', 'etf_sector_alignment', 'stock_relative_strength', 'trend_quality', 'volume_participation', 'volatility_risk', 'liquidity_suitability'];
const STAGES = new Set(['watch', 'prepare', 'enter', 'invalidated']);
const QUALITIES = new Set(['passed', 'degraded', 'quarantined', 'failed']);
const ENTRY_LANES: CandidateEntryLane[] = ['review_now', 'watch_trigger', 'wait_reset', 'other_research'];
const ENTRY_POSTURES = new Set(['technical_review_ready', 'monitor_for_trigger', 'wait_for_reset', 'deprioritized', 'not_assessable']);
const EXTENSIONS = new Set(['low', 'moderate', 'high', 'extreme', 'unavailable']);
const SETUPS = new Set(['breakout_confirmed', 'breakout_watch', 'pullback', 'strong_but_extended', 'no_viable_setup', 'unavailable']);
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
  if (envelope.schema_version !== '1.0' || !['opportunity-candidate-snapshot/1.0', 'opportunity-candidate-snapshot/1.1'].includes(String(envelope.contract_version))) throw new Error('Unsupported Candidate snapshot contract');
  const analytics = record(envelope.analytics, 'analytics');
  const hasEntry = envelope.contract_version === 'opportunity-candidate-snapshot/1.1';
  const expectedPublication = hasEntry ? 'opportunity-candidate-publication/1.1' : 'opportunity-candidate-publication/1.0';
  if (analytics.schema_version !== '1.0' || analytics.contract_version !== expectedPublication
    || analytics.language_neutral !== true || analytics.research_priority_only !== true
    || analytics.underlying_stock_result_not_option_return !== true || analytics.price_volume_not_fund_flow !== true) {
    throw new Error('Unsupported Candidate publication contract');
  }
  if (hasEntry && (analytics.leadership_rank_preserved !== true
    || analytics.entry_location_separate_from_leadership !== true
    || analytics.reference_support_not_stop_price !== true)) throw new Error('Candidate entry decision boundary is incomplete');
  digest(analytics.logical_fingerprint, 'analytics');
  if (analytics.logical_fingerprint !== envelope.candidate_analytics_logical_fingerprint) throw new Error('Candidate snapshot analytics binding differs');
  const order = strings(analytics.universe_order, 'Universe order');
  const envelopeOrder = strings(envelope.universe_order, 'snapshot Universe order');
  if (order.length !== 2 || order.join('|') !== envelopeOrder.join('|') || analytics.default_universe_id !== order[0]) throw new Error('Candidate Universe order differs');
  const modes = strings(analytics.risk_mode_order, 'risk modes');
  if (modes.join('|') !== MODES.join('|')) throw new Error('Candidate risk mode order differs');
  if (!Array.isArray(analytics.universes) || analytics.universes.length !== 2) throw new Error('Candidate Universe catalog is incomplete');
  const universes = analytics.universes.map((item, index) => parseUniverse(item, order[index], hasEntry));
  const selected = universeId ?? String(analytics.default_universe_id);
  const universe = universes.find((item) => item.universe_id === selected);
  if (!universe) throw new Error('Selected Candidate Universe is unavailable');
  return {
    as_of_session: String(analytics.as_of_session), default_universe_id: String(analytics.default_universe_id),
    selected_universe_id: selected, universe_order: order, risk_mode_order: MODES,
    source: record(analytics.source, 'source'), universe, warnings: strings(analytics.warnings, 'warnings'),
    logical_fingerprint: String(analytics.logical_fingerprint), publication_contract_version: expectedPublication,
  };
}

function parseUniverse(value: unknown, expectedId: string, hasEntry: boolean): CandidateUniverse {
  const universe = record(value, 'Universe');
  if (universe.universe_id !== expectedId) throw new Error('Candidate Universe identity differs');
  number(universe.universe_member_count, 'member count'); number(universe.bar_covered_member_count, 'covered count'); number(universe.missing_member_count, 'missing count');
  digest(universe.membership_fingerprint, 'membership'); digest(universe.candidate_batch_logical_fingerprint, 'batch');
  if (Number(universe.bar_covered_member_count) + Number(universe.missing_member_count) !== Number(universe.universe_member_count)) throw new Error('Candidate coverage does not reconcile');
  if (!Array.isArray(universe.risk_modes) || universe.risk_modes.length !== 3) throw new Error('Candidate risk results are incomplete');
  const riskModes = universe.risk_modes.map((item, index) => parseRiskResult(item, MODES[index]));
  if (!Array.isArray(universe.candidates)) throw new Error('Candidate cards are unavailable');
  const candidates = universe.candidates.map((item) => parseCandidate(item, hasEntry, expectedId));
  const ids = candidates.map((item) => item.instrument_id);
  if (new Set(ids).size !== ids.length || [...ids].sort().join('|') !== ids.join('|')) throw new Error('Candidate stable IDs are duplicated or unordered');
  const published = new Set(ids);
  riskModes.forEach((mode) => mode.displayed_instrument_ids.forEach((id) => { if (!published.has(id)) throw new Error('Candidate rank references an unpublished card'); }));
  if (hasEntry) {
    if (!Array.isArray(universe.entry_risk_modes) || universe.entry_risk_modes.length !== 3) throw new Error('Candidate entry risk modes are incomplete');
    universe.entry_risk_modes.forEach((item, index) => {
      const entry = record(item, 'entry risk mode');
      if (entry.risk_mode !== MODES[index] || !Array.isArray(entry.lanes) || entry.lanes.length !== 4) throw new Error('Candidate entry risk mode order differs');
      digest(entry.logical_fingerprint, 'entry risk mode'); number(entry.hard_risk_gate_qualified_count, 'hard risk qualified count');
      let qualifying = 0;
      entry.lanes.forEach((laneValue, laneIndex) => {
        const lane = record(laneValue, 'entry lane');
        if (lane.lane !== ENTRY_LANES[laneIndex]) throw new Error('Candidate entry lane order differs');
        qualifying += number(lane.qualifying_count, 'lane qualifying count');
        const cap = number(lane.display_cap, 'lane display cap'); const laneIds = strings(lane.displayed_instrument_ids, 'lane IDs');
        if (laneIds.length > cap || new Set(laneIds).size !== laneIds.length || laneIds.some((id) => !published.has(id))) throw new Error('Candidate entry lane display differs');
      });
      if (qualifying !== entry.hard_risk_gate_qualified_count) throw new Error('Candidate entry lane counts do not reconcile');
    });
  }
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

function parseCandidate(value: unknown, hasEntry: boolean, universeId: string): CandidateItem {
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
  if (hasEntry) parseEntryGeometry(item.entry_geometry, item, universeId);
  else if (item.entry_geometry !== undefined) throw new Error('Legacy Candidate publication cannot carry entry geometry');
  return value as CandidateItem;
}

function parseEntryGeometry(value: unknown, item: Record<string, unknown>, universeId: string): void {
  const entry = record(value, 'entry geometry'); const metrics = record(entry.metrics, 'entry metrics');
  if (entry.contract_version !== 'candidate-entry-geometry/1.0'
    || entry.instrument_id !== item.instrument_id || entry.ticker !== item.ticker
    || entry.security_type !== item.security_type || entry.universe_id !== universeId
    || !ENTRY_POSTURES.has(String(entry.review_posture)) || !EXTENSIONS.has(String(entry.extension_risk))
    || !SETUPS.has(String(entry.technical_setup))) throw new Error('Candidate entry geometry identity or enum differs');
  digest(entry.parameter_fingerprint, 'entry parameter'); digest(entry.source_candidate_fingerprint, 'entry Candidate source');
  digest(entry.source_state_fingerprint, 'entry state source'); digest(entry.logical_fingerprint, 'entry geometry');
  ['why_now_codes', 'supporting_fact_codes', 'counterevidence_codes', 'what_would_make_reviewable_codes',
    'technical_invalidation_codes', 'required_manual_check_codes', 'warnings'].forEach((key) => strings(entry[key], key));
  if (!['available', 'unavailable'].includes(String(metrics.availability))) throw new Error('Candidate entry metric availability differs');
  strings(metrics.missing_reason_codes, 'entry missing reasons');
  ['close', 'sma_10', 'sma_20', 'atr_14', 'return_3', 'return_5', 'close_to_sma_10_atr',
    'close_to_sma_20_atr', 'move_5_volatility_units', 'current_gap_atr', 'current_range_atr',
    'current_close_location', 'current_volume_ratio', 'prior_five_session_close_high',
    'prior_five_session_close_low', 'breakout_distance_atr', 'pullback_from_prior_high_atr',
    'reference_support_value', 'reference_support_distance_pct'].forEach((key) => decimal(metrics[key], `entry ${key}`, true));
  if (metrics.consecutive_up_sessions !== null) number(metrics.consecutive_up_sessions, 'consecutive up sessions');
}

export async function getOpportunityCandidates(universeId: string | undefined, signal?: AbortSignal): Promise<OpportunityCandidateResponse> {
  if (import.meta.env.VITE_MARKET_DATA_MODE !== 'snapshot') throw new Error('Candidate API is not enabled');
  const manifest = parseSnapshotManifest(await fetchJson<unknown>('/private-data/v1/manifest.json', signal));
  if (!['1.6', '1.7'].includes(manifest.snapshot_contract_version)
    || manifest.dashboard_contract_version !== (manifest.snapshot_contract_version === '1.7' ? '2.4' : '2.3')
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
  if (manifest.snapshot_contract_version === '1.7' && (
    envelope.contract_version !== 'opportunity-candidate-snapshot/1.1'
    || analytics.contract_version !== manifest.candidate_publication_contract_version
    || source.entry_geometry_contract_version !== manifest.entry_geometry_contract_version
    || source.entry_geometry_audit_logical_fingerprint !== manifest.entry_geometry_audit_logical_fingerprint
    || source.entry_geometry_parameter_fingerprint !== manifest.entry_geometry_parameter_fingerprint
    || source.entry_lane_consumer_parameter_fingerprint !== manifest.entry_lane_consumer_parameter_fingerprint
  )) throw new Error('Candidate Snapshot entry-geometry binding differs');
  return parseOpportunityCandidateSnapshot(raw, universeId);
}
