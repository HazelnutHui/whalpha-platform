import { fetchJson } from './client';
import { parseSnapshotManifest } from './market';

export type StrategyChannel = 'momentum_breakout' | 'strong_stock_pullback' | 'trend_continuation' | 'technical_reversal' | 'fundamental_value_reversal' | 'defensive_rotation';
export type StrategyChannelStatus = 'advance_to_research' | 'watch_for_trigger' | 'deprioritized' | 'unavailable';
export type StrategyMarketFit = 'supportive' | 'neutral' | 'adverse' | 'unavailable';

export interface StrategyEvidence {
  evidence_id: string; evidence_kind: 'supporting' | 'counterevidence'; role: 'primary' | 'context';
  source_kind: string; evidence_type: string; availability: 'available' | 'unavailable';
  observed_value: string | null; raw_unit: string; source_session: string | null;
  missing_reason_code: string | null; reason_codes: string[];
}
export interface StrategyAssessment {
  as_of_session: string; universe_id: string; instrument_id: string; ticker: string;
  security_type: 'CS' | 'ADRC'; channel: StrategyChannel; status: StrategyChannelStatus;
  channel_score: string | null; within_channel_rank: number | null;
  market_fit: StrategyMarketFit; market_fit_reason_codes: string[];
  evidence: StrategyEvidence[]; missing_required_evidence_codes: string[];
  why_surfaced_codes: string[]; first_rejection_code: string;
  what_would_make_researchable_codes: string[]; invalidation_codes: string[];
  required_manual_check_codes: string[]; warning_codes: string[];
  logical_fingerprint: string;
}
export interface StrategyChannelView {
  channel: StrategyChannel; status_counts: Record<string, number>; qualifying_count: number;
  display_cap: number; displayed_records: StrategyAssessment[]; logical_fingerprint: string;
}
export interface StrategyUniverse {
  universe_id: string; channels: StrategyChannelView[]; logical_fingerprint: string;
}
export interface CandidateStrategyResponse {
  as_of_session: string; default_universe_id: string; selected_universe_id: string;
  universe_order: string[]; channel_order: StrategyChannel[]; source: Record<string, unknown>;
  universe: StrategyUniverse; warnings: string[]; logical_fingerprint: string;
  fixed_baseline_not_chronologically_validated: true;
}

const CHANNELS: StrategyChannel[] = ['momentum_breakout', 'strong_stock_pullback', 'trend_continuation', 'technical_reversal', 'fundamental_value_reversal', 'defensive_rotation'];
const STATUSES = new Set<StrategyChannelStatus>(['advance_to_research', 'watch_for_trigger', 'deprioritized', 'unavailable']);
const MARKET_FITS = new Set<StrategyMarketFit>(['supportive', 'neutral', 'adverse', 'unavailable']);
const TECHNICAL_SETUPS = new Set(['breakout_confirmed', 'breakout_watch', 'pullback', 'strong_but_extended', 'no_viable_setup', 'unavailable']);
const EXTENSION_RISKS = new Set(['low', 'moderate', 'high', 'extreme', 'unavailable']);
const DISPLAY_REASON_CODES = new Set([
  'bounded_breakout_confirmed', 'bounded_breakout_or_near_trigger_structure_required',
  'breakout_may_fail_or_reverse', 'breakout_not_confirmed',
  'candidate_state_and_trend_components_aligned', 'candidate_state_invalidated',
  'candidate_state_must_requalify', 'candidate_state_or_continuation_evidence_must_advance',
  'channel_primary_evidence_breaks', 'channel_specific_market_fit_not_validated',
  'chase_risk_high', 'close_above_prior_high_with_volume_confirmation',
  'company_event_and_earnings_timing', 'continuation_state_not_fully_confirmed',
  'extension_must_reset_before_breakout_review', 'extension_must_reset_below_high_threshold',
  'extension_reset_into_labelled_support_zone', 'extension_reset_required',
  'fixed_baseline_not_chronologically_validated', 'leader_extended_before_possible_pullback',
  'leadership_and_trend_quality_remain_researchable', 'leadership_near_breakout_or_reset_trigger',
  'news_and_thesis_evidence', 'option_liquidity_iv_greeks_and_spread',
  'orderly_pullback_not_yet_formed', 'orderly_pullback_structure_present',
  'orderly_pullback_toward_support_required', 'position_risk_and_execution_quality',
  'price_volume_not_fund_flow', 'pullback_may_break_support',
  'relative_strength_trend_and_state_must_align', 'research_priority_not_recommendation',
  'source_or_corporate_action_quarantine', 'trend_may_be_late_cycle_or_crowded',
  'underlying_stock_result_not_option_return',
]);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const SHA = /^[0-9a-f]{64}$/;
const DECIMAL = /^(?:0|[1-9]\d*)(?:\.\d+)?$/;

function record(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new Error(`Invalid strategy payload: ${label}`);
  return value as Record<string, unknown>;
}
function strings(value: unknown, label: string): string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) throw new Error(`Invalid strategy payload: ${label}`);
  return value;
}
function displayCodes(value: unknown, label: string): string[] {
  const result = strings(value, label);
  if (result.some((item) => !DISPLAY_REASON_CODES.has(item))) throw new Error(`Unknown strategy display reason: ${label}`);
  return result;
}
function digest(value: unknown, label: string): void {
  if (typeof value !== 'string' || !SHA.test(value)) throw new Error(`Invalid strategy fingerprint: ${label}`);
}
function count(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < 0) throw new Error(`Invalid strategy count: ${label}`);
  return value;
}

export function parseCandidateStrategyProduct(value: unknown, universeId?: string): CandidateStrategyResponse {
  const product = record(value, 'product');
  if (product.schema_version !== '1.0' || product.contract_version !== 'candidate-strategy-channel-product/1.0'
    || product.language_neutral !== true || product.research_priority_only !== true
    || product.fixed_baseline_not_chronologically_validated !== true
    || product.cross_channel_score_comparison_prohibited !== true
    || product.market_fit_separate_and_unvalidated !== true
    || product.event_context_auxiliary !== true
    || product.underlying_stock_result_not_option_return !== true
    || product.price_volume_not_fund_flow !== true
    || product.guest_and_credential_capability_identical !== true) throw new Error('Unsupported strategy-channel product contract');
  digest(product.logical_fingerprint, 'product');
  const source = record(product.source, 'source');
  [
    'strategy_audit_manifest_sha256', 'strategy_audit_logical_fingerprint',
    'strategy_parameter_fingerprint', 'candidate_analytics_logical_fingerprint',
    'candidate_audit_logical_fingerprint', 'entry_geometry_audit_logical_fingerprint',
  ].forEach((key) => digest(source[key], key));
  if (source.strategy_audit_contract_version !== 'candidate-strategy-channel-audit/1.0'
    || source.strategy_contract_version !== 'candidate-strategy-channel-shadow/1.0'
    || source.strategy_consumer_contract_version !== 'candidate-strategy-channel-consumer/1.0'
    || source.candidate_publication_contract_version !== 'opportunity-candidate-publication/1.1'
    || source.strategy_oracle_mismatch_count !== 0 || source.strategy_input_permutation_match !== true
    || source.strategy_oracle_production_calculator_imported !== false
    || source.external_request_count !== 0 || source.production_write_count !== 0) throw new Error('Strategy-channel source gates differ');
  const order = strings(product.universe_order, 'Universe order');
  const channelOrder = strings(product.channel_order, 'channel order') as StrategyChannel[];
  if (order.length !== 2 || product.default_universe_id !== order[0]
    || channelOrder.join('|') !== CHANNELS.join('|')) throw new Error('Strategy-channel product order differs');
  const batchFingerprints = strings(source.strategy_batch_fingerprints, 'strategy batch fingerprints');
  const consumerFingerprints = strings(source.strategy_consumer_fingerprints, 'strategy consumer fingerprints');
  [
    ...strings(source.source_candidate_batch_fingerprints, 'Candidate batch fingerprints'),
    ...strings(source.source_entry_geometry_batch_fingerprints, 'entry batch fingerprints'),
    ...batchFingerprints, ...consumerFingerprints,
  ].forEach((item) => digest(item, 'source list'));
  if (batchFingerprints.length !== 2 || consumerFingerprints.length !== 2 || !Array.isArray(product.universes) || product.universes.length !== 2) throw new Error('Strategy-channel Universe sources are incomplete');
  const universes = product.universes.map((item, index) => parseUniverse(item, order[index], String(product.as_of_session), batchFingerprints[index], consumerFingerprints[index]));
  const selected = universeId ?? String(product.default_universe_id);
  const universe = universes.find((item) => item.universe_id === selected);
  if (!universe) throw new Error('Selected strategy-channel Universe is unavailable');
  return {
    as_of_session: String(product.as_of_session), default_universe_id: String(product.default_universe_id),
    selected_universe_id: selected, universe_order: order, channel_order: CHANNELS,
    source, universe, warnings: strings(product.warnings, 'warnings'),
    logical_fingerprint: String(product.logical_fingerprint),
    fixed_baseline_not_chronologically_validated: true,
  };
}

function parseUniverse(value: unknown, universeId: string, session: string, batchFingerprint: string, consumerFingerprint: string): StrategyUniverse {
  const universe = record(value, 'Universe');
  if (universe.schema_version !== '1.0' || universe.contract_version !== 'candidate-strategy-channel-consumer/1.0'
    || universe.universe_id !== universeId || universe.as_of_session !== session
    || universe.source_batch_logical_fingerprint !== batchFingerprint
    || universe.cross_channel_score_prohibited !== true || universe.shadow_only !== true) throw new Error('Strategy-channel consumer binding differs');
  digest(universe.logical_fingerprint, 'consumer');
  if (universe.logical_fingerprint !== consumerFingerprint) throw new Error('Strategy-channel consumer fingerprint differs');
  const order = strings(universe.channel_order, 'consumer channel order');
  if (order.join('|') !== CHANNELS.join('|') || !Array.isArray(universe.channels) || universe.channels.length !== CHANNELS.length) throw new Error('Strategy-channel consumer order differs');
  const channels = universe.channels.map((item, index) => parseChannel(item, CHANNELS[index], universeId, session));
  return { universe_id: universeId, channels, logical_fingerprint: String(universe.logical_fingerprint) };
}

function parseChannel(value: unknown, channel: StrategyChannel, universeId: string, session: string): StrategyChannelView {
  const view = record(value, 'channel view'); const counts = record(view.status_counts, 'status counts');
  if (view.schema_version !== '1.0' || view.channel !== channel || view.display_cap !== 8 || !Array.isArray(view.displayed_records)) throw new Error('Strategy-channel view differs');
  digest(view.logical_fingerprint, 'channel view');
  Object.entries(counts).forEach(([status, value]) => { if (!STATUSES.has(status as StrategyChannelStatus)) throw new Error('Strategy status count is unknown'); count(value, 'status count'); });
  const qualifying = count(view.qualifying_count, 'qualifying count');
  if (qualifying !== Number(counts.advance_to_research ?? 0) + Number(counts.watch_for_trigger ?? 0)
    || view.displayed_records.length !== Math.min(qualifying, 8)) throw new Error('Strategy-channel display count differs');
  const displayed = view.displayed_records.map((item, index) => parseAssessment(item, channel, universeId, session, index + 1));
  return { channel, status_counts: counts as Record<string, number>, qualifying_count: qualifying, display_cap: 8, displayed_records: displayed, logical_fingerprint: String(view.logical_fingerprint) };
}

function parseAssessment(value: unknown, channel: StrategyChannel, universeId: string, session: string, rank: number): StrategyAssessment {
  const item = record(value, 'assessment');
  if (item.schema_version !== '1.0' || item.contract_version !== 'candidate-strategy-channel-shadow/1.0'
    || item.as_of_session !== session || item.universe_id !== universeId || item.channel !== channel
    || typeof item.instrument_id !== 'string' || !UUID.test(item.instrument_id)
    || typeof item.ticker !== 'string' || !['CS', 'ADRC'].includes(String(item.security_type))
    || !STATUSES.has(item.status as StrategyChannelStatus) || !MARKET_FITS.has(item.market_fit as StrategyMarketFit)
    || !['advance_to_research', 'watch_for_trigger'].includes(String(item.status))
    || item.within_channel_rank !== rank || typeof item.channel_score !== 'string' || !DECIMAL.test(item.channel_score)
    || item.score_meaning !== 'within_channel_research_priority_not_return_probability'
    || item.market_fit_separate_from_channel_score !== true || item.first_rejection_is_risk_not_status_reason !== true) throw new Error('Strategy assessment identity or decision boundary differs');
  digest(item.parameter_fingerprint, 'assessment parameter'); digest(item.source_candidate_fingerprint, 'assessment Candidate'); digest(item.source_entry_geometry_fingerprint, 'assessment entry'); digest(item.logical_fingerprint, 'assessment');
  if (typeof item.first_rejection_code !== 'string' || !DISPLAY_REASON_CODES.has(item.first_rejection_code)
    || !Array.isArray(item.evidence)) throw new Error('Strategy assessment explanation is incomplete');
  const evidence = item.evidence.map((value) => parseEvidence(value));
  return {
    ...(item as unknown as StrategyAssessment), evidence,
    market_fit_reason_codes: displayCodes(item.market_fit_reason_codes, 'market fit reasons'),
    missing_required_evidence_codes: displayCodes(item.missing_required_evidence_codes, 'missing evidence'),
    why_surfaced_codes: displayCodes(item.why_surfaced_codes, 'why surfaced'),
    what_would_make_researchable_codes: displayCodes(item.what_would_make_researchable_codes, 'reviewability'),
    invalidation_codes: displayCodes(item.invalidation_codes, 'invalidation'),
    required_manual_check_codes: displayCodes(item.required_manual_check_codes, 'manual checks'),
    warning_codes: displayCodes(item.warning_codes, 'warnings'),
  };
}

function parseEvidence(value: unknown): StrategyEvidence {
  const item = record(value, 'evidence');
  if (typeof item.evidence_id !== 'string' || !['supporting', 'counterevidence'].includes(String(item.evidence_kind))
    || !['primary', 'context'].includes(String(item.role)) || !['available', 'unavailable'].includes(String(item.availability))
    || typeof item.source_kind !== 'string' || typeof item.evidence_type !== 'string' || typeof item.raw_unit !== 'string'
    || !(item.observed_value === null || typeof item.observed_value === 'string')
    || !(item.source_session === null || typeof item.source_session === 'string')
    || !(item.missing_reason_code === null || typeof item.missing_reason_code === 'string')
    || (item.evidence_id === 'entry_technical_setup' && !TECHNICAL_SETUPS.has(String(item.observed_value)))
    || (item.evidence_id === 'entry_extension_risk' && !EXTENSION_RISKS.has(String(item.observed_value)))) throw new Error('Strategy evidence differs');
  strings(item.reason_codes, 'evidence reasons');
  return item as unknown as StrategyEvidence;
}

export async function getCandidateStrategies(universeId?: string, signal?: AbortSignal): Promise<CandidateStrategyResponse> {
  if (import.meta.env.VITE_MARKET_DATA_MODE !== 'snapshot') throw new Error('Strategy-channel API is not enabled');
  const manifest = parseSnapshotManifest(await fetchJson<unknown>('/private-data/v1/manifest.json', signal));
  if (manifest.snapshot_contract_version !== '1.9' || manifest.dashboard_contract_version !== '2.6'
    || manifest.candidate_strategy_file !== 'candidate-strategy-channels.json') throw new Error('Strategy-channel snapshot is unavailable');
  const raw = await fetchJson<unknown>(`/private-data/v1/${manifest.candidate_strategy_file}`, signal);
  const parsed = parseCandidateStrategyProduct(raw, universeId);
  if (parsed.logical_fingerprint !== manifest.candidate_strategy_logical_fingerprint
    || parsed.source.strategy_audit_manifest_sha256 !== manifest.candidate_strategy_audit_manifest_sha256
    || parsed.source.strategy_audit_logical_fingerprint !== manifest.candidate_strategy_audit_logical_fingerprint
    || parsed.source.strategy_parameter_fingerprint !== manifest.candidate_strategy_parameter_fingerprint
    || parsed.source.candidate_analytics_logical_fingerprint !== manifest.candidate_analytics_logical_fingerprint
    || parsed.source.candidate_audit_logical_fingerprint !== manifest.candidate_audit_logical_fingerprint
    || parsed.source.entry_geometry_audit_logical_fingerprint !== manifest.entry_geometry_audit_logical_fingerprint) throw new Error('Strategy-channel Snapshot manifest binding differs');
  return parsed;
}
