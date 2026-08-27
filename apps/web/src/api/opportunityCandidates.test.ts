import { describe, expect, it } from 'vitest';

import { parseOpportunityCandidateDetailShard, parseOpportunityCandidateSnapshot, parseOpportunityCandidateSummarySnapshot } from './opportunityCandidates';

const PRIMARY = 'provider_classified_common_shares_v1';
const SECONDARY = 'provider_classified_common_shares_plus_adrs_v1';
const MODES = ['conservative', 'balanced', 'aggressive'];
const COMPONENTS = ['market_alignment', 'etf_sector_alignment', 'stock_relative_strength', 'trend_quality', 'volume_participation', 'volatility_risk', 'liquidity_suitability'];

function fixture() {
  const candidate = {
    instrument_id: '11111111-1111-5111-8111-111111111111', ticker: 'TEST', security_type: 'CS',
    base_score: '70.0000', adjusted_score: '70.0000', configured_weight_available: '100.0000', missingness_penalty: '0.0000',
    confidence: { source_completeness: '1.0000', history_completeness: '1.0000', relationship_support: '0.5000', state_confirmation_support: '0.3333', confirmation_session_count: 1, prior_state_record_fingerprint: 'a'.repeat(64), confidence: '0.8000', disclaimer: 'data_support_not_success_probability' },
    latest_price: '25.0000', median_dollar_volume_20: '50000000.0000', annualized_volatility_10: '0.3000', maximum_absolute_open_gap_5: '0.0400', current_volume_ratio: '1.2000',
    primary_driver_instrument_id: null, primary_driver_ticker: null, driver_correlation_20: null, relationship_kind: null,
    data_quality_status: 'degraded', components: COMPONENTS.map((component_id) => ({ component_id, configured_weight: '10.0000', effective_weight: '10.0000', score: '70.0000', contribution: component_id === 'market_alignment' ? '10.0000' : '0.0000', availability: 'available', cap_applied: null, metrics: [], reason_codes: [] })),
    evidence: [{ evidence_kind: 'supporting', evidence_id: 'positive_component', component_id: 'trend_quality', observed_value: '12.0000' }],
    invalidation_condition_codes: ['base_score_below_45'], reason_codes: [], warning_codes: [],
    state: { final_stage: 'watch', transition_status: 'held', transition_rule_id: 'stage_hold', pending_target_stage: null, stage_confirmation_count: 2, required_confirmation_sessions: 0, breakout_triggered: false, stale_state: false, manual_review_required: false, gate_results: [], reason_codes: [], logical_fingerprint: 'b'.repeat(64) },
    risk_dispositions: MODES.map((risk_mode) => ({ risk_mode, eligible: true, risk_adjusted_rank: 1, rejection_reason_codes: [] })), score_logical_fingerprint: 'c'.repeat(64),
  };
  const universe = (universe_id: string) => ({
    universe_id, universe_member_count: 1, membership_fingerprint: 'd'.repeat(64), bar_covered_member_count: 1, missing_member_count: 0,
    quality_counts: { degraded: 1 }, stage_counts: { watch: 1 }, risk_modes: MODES.map((risk_mode) => ({ risk_mode, eligible_count: 1, rejected_count: 0, display_cap: 1, displayed_instrument_ids: [candidate.instrument_id], logical_fingerprint: 'e'.repeat(64) })),
    candidates: [{ ...candidate }], candidate_batch_logical_fingerprint: 'f'.repeat(64),
  });
  const analytics = { schema_version: '1.0', contract_version: 'opportunity-candidate-publication/1.0', as_of_session: '2026-08-24', default_universe_id: PRIMARY, universe_order: [PRIMARY, SECONDARY], risk_mode_order: MODES, source: {}, universes: [universe(PRIMARY), universe(SECONDARY)], language_neutral: true, research_priority_only: true, underlying_stock_result_not_option_return: true, price_volume_not_fund_flow: true, warnings: ['short_candidate_state_history'], logical_fingerprint: '9'.repeat(64) };
  return { schema_version: '1.0', contract_version: 'opportunity-candidate-snapshot/1.0', publication_id: '2026-08-24T120000Z-abcdef0', payload_sha256: '1'.repeat(64), payload_logical_fingerprint: '2'.repeat(64), candidate_analytics_logical_fingerprint: analytics.logical_fingerprint, default_universe_id: PRIMARY, universe_order: [PRIMARY, SECONDARY], analytics };
}

function entryFixture() {
  const value = fixture();
  value.contract_version = 'opportunity-candidate-snapshot/1.1';
  value.analytics.contract_version = 'opportunity-candidate-publication/1.1';
  Object.assign(value.analytics, { leadership_rank_preserved: true, entry_location_separate_from_leadership: true, reference_support_not_stop_price: true });
  value.analytics.universes.forEach((universe) => {
    const mutableUniverse = universe as typeof universe & { entry_risk_modes: Array<Record<string, unknown>> };
    const candidate = universe.candidates[0] as typeof universe.candidates[0] & Record<string, unknown>;
    candidate.entry_geometry = {
      contract_version: 'candidate-entry-geometry/1.0', parameter_fingerprint: '1'.repeat(64),
      as_of_session: '2026-08-24', universe_id: universe.universe_id, instrument_id: candidate.instrument_id,
      ticker: candidate.ticker, security_type: candidate.security_type, candidate_stage: 'watch', candidate_base_score: '70.0000',
      relative_strength_component_score: '70.0000', trend_component_score: '70.0000', source_candidate_fingerprint: candidate.score_logical_fingerprint,
      source_state_fingerprint: 'b'.repeat(64), volume_climax_risk_candidate: false, extension_risk: 'low',
      technical_setup: 'breakout_confirmed', review_posture: 'technical_review_ready', first_rejection_code: null,
      why_now_codes: ['bounded_breakout_confirmed'], supporting_fact_codes: ['prior_close_high_exceeded'], counterevidence_codes: [],
      what_would_make_reviewable_codes: ['complete_company_event_options_and_execution_review'], technical_invalidation_codes: [],
      required_manual_check_codes: [], warnings: [], logical_fingerprint: '3'.repeat(64),
      metrics: { availability: 'available', close: '25.0000000000', sma_10: '24.0000000000', sma_20: '23.0000000000', atr_14: '1.0000000000',
        return_3: '0.0300000000', return_5: '0.0500000000', close_to_sma_10_atr: '1.0000000000', close_to_sma_20_atr: '2.0000000000',
        move_5_volatility_units: '0.5000000000', consecutive_up_sessions: 2, current_gap_atr: '0.1000000000', current_range_atr: '1.0000000000',
        current_close_location: '0.8000000000', current_volume_ratio: '1.2000000000', prior_five_session_close_high: '24.5000000000',
        prior_five_session_close_low: '22.0000000000', breakout_distance_atr: '0.5000000000', pullback_from_prior_high_atr: '-0.5000000000',
        reference_support_kind: 'sma20', reference_support_value: '23.0000000000', reference_support_distance_pct: '0.0800000000', missing_reason_codes: [] },
    };
    mutableUniverse.entry_risk_modes = MODES.map((risk_mode) => ({ risk_mode, hard_risk_gate_qualified_count: 1,
      lanes: [
        { lane: 'review_now', qualifying_count: 1, display_cap: 8, displayed_instrument_ids: [candidate.instrument_id] },
        { lane: 'watch_trigger', qualifying_count: 0, display_cap: 8, displayed_instrument_ids: [] },
        { lane: 'wait_reset', qualifying_count: 0, display_cap: 8, displayed_instrument_ids: [] },
        { lane: 'other_research', qualifying_count: 0, display_cap: 8, displayed_instrument_ids: [] },
      ], logical_fingerprint: '4'.repeat(64) }));
  });
  return value;
}

function summaryFixture() {
  const full = entryFixture();
  const descriptors: Array<Record<string, unknown>> = [];
  const universes = full.analytics.universes.map((universe, index) => {
    const source = universe.candidates[0] as typeof universe.candidates[0] & Record<string, any>;
    const shardId = `u${index}-1`; const filename = `opportunity-candidate-details-${shardId}.json`;
    descriptors.push({ shard_id: shardId, universe_id: universe.universe_id, stable_id_prefix: '1', filename, item_count: 1, logical_fingerprint: `${index + 5}`.repeat(64) });
    return { ...universe, candidates: [{ instrument_id: source.instrument_id, ticker: source.ticker, security_type: source.security_type,
      base_score: source.base_score, confidence: source.confidence, latest_price: source.latest_price,
      median_dollar_volume_20: source.median_dollar_volume_20, data_quality_status: source.data_quality_status,
      final_stage: source.state.final_stage, risk_dispositions: source.risk_dispositions,
      entry_summary: { review_posture: source.entry_geometry.review_posture, technical_setup: source.entry_geometry.technical_setup,
        extension_risk: source.entry_geometry.extension_risk, reference_support_distance_pct: source.entry_geometry.metrics.reference_support_distance_pct },
      score_logical_fingerprint: source.score_logical_fingerprint, entry_geometry_logical_fingerprint: source.entry_geometry.logical_fingerprint,
      detail_shard_id: shardId }] };
  });
  const analytics = { schema_version: '1.0', contract_version: 'opportunity-candidate-summary/1.0',
    full_publication_contract_version: 'opportunity-candidate-publication/1.1', full_candidate_analytics_logical_fingerprint: full.analytics.logical_fingerprint,
    as_of_session: full.analytics.as_of_session, default_universe_id: PRIMARY, universe_order: [PRIMARY, SECONDARY], risk_mode_order: MODES,
    source: full.analytics.source, universes, detail_shards: descriptors, language_neutral: true, research_priority_only: true,
    underlying_stock_result_not_option_return: true, price_volume_not_fund_flow: true, leadership_rank_preserved: true,
    entry_location_separate_from_leadership: true, reference_support_not_stop_price: true, warnings: full.analytics.warnings,
    logical_fingerprint: '7'.repeat(64) };
  return { schema_version: '1.0', contract_version: 'opportunity-candidate-summary-snapshot/1.0', publication_id: full.publication_id,
    payload_sha256: full.payload_sha256, payload_logical_fingerprint: full.payload_logical_fingerprint,
    candidate_analytics_logical_fingerprint: full.analytics.logical_fingerprint, default_universe_id: PRIMARY,
    universe_order: [PRIMARY, SECONDARY], analytics };
}

describe('Opportunity Candidate snapshot parser', () => {
  it('accepts the fixed language-neutral contract and selected Universe', () => {
    const parsed = parseOpportunityCandidateSnapshot(fixture(), SECONDARY);
    expect(parsed.selected_universe_id).toBe(SECONDARY);
    expect(parsed.universe.candidates[0].ticker).toBe('TEST');
    expect(parsed.universe.risk_modes[1].displayed_instrument_ids).toHaveLength(1);
  });

  it('fails closed on version, rank, stage, component, or fingerprint drift', () => {
    const version = fixture(); version.contract_version = 'opportunity-candidate-snapshot/2.0';
    expect(() => parseOpportunityCandidateSnapshot(version)).toThrow('Unsupported');
    const rank = fixture(); rank.analytics.universes[0].risk_modes[0].displayed_instrument_ids = [];
    expect(() => parseOpportunityCandidateSnapshot(rank)).toThrow('display count');
    const stage = fixture(); stage.analytics.universes[0].candidates[0].state.final_stage = 'sell';
    expect(() => parseOpportunityCandidateSnapshot(stage)).toThrow('stage');
    const component = fixture(); component.analytics.universes[0].candidates[0].components.reverse();
    expect(() => parseOpportunityCandidateSnapshot(component)).toThrow('component order');
    const stableId = fixture(); stableId.analytics.universes[0].candidates[0].instrument_id = 'ticker-is-not-an-id';
    expect(() => parseOpportunityCandidateSnapshot(stableId)).toThrow('identity');
    const fractionalRank = fixture(); fractionalRank.analytics.universes[0].candidates[0].risk_dispositions[0].risk_adjusted_rank = 1.5;
    expect(() => parseOpportunityCandidateSnapshot(fractionalRank)).toThrow('rank');
    const fingerprint = fixture(); fingerprint.candidate_analytics_logical_fingerprint = '0'.repeat(64);
    expect(() => parseOpportunityCandidateSnapshot(fingerprint)).toThrow('binding');
  });

  it('accepts the additive entry-geometry contract and fails closed on lane drift', () => {
    const parsed = parseOpportunityCandidateSnapshot(entryFixture());
    expect(parsed.publication_contract_version).toBe('opportunity-candidate-publication/1.1');
    expect(parsed.universe.entry_risk_modes?.[1].lanes[0].displayed_instrument_ids).toHaveLength(1);
    expect(parsed.universe.candidates[0].entry_geometry?.review_posture).toBe('technical_review_ready');
    const drift = entryFixture(); const entryModes = (drift.analytics.universes[0] as typeof drift.analytics.universes[0] & { entry_risk_modes: Array<{ lanes: unknown[] }> }).entry_risk_modes; entryModes[0].lanes.reverse();
    expect(() => parseOpportunityCandidateSnapshot(drift)).toThrow('lane order');
  });

  it('accepts the split summary contract and binds each row to one declared detail shard', () => {
    const parsed = parseOpportunityCandidateSummarySnapshot(summaryFixture(), SECONDARY);
    expect(parsed.snapshot_contract_version).toBe('opportunity-candidate-summary-snapshot/1.0');
    expect(parsed.universe.candidates[0].detail_file).toBe('opportunity-candidate-details-u1-1.json');
    expect(parsed.universe.candidates[0].entry_summary?.review_posture).toBe('technical_review_ready');
    const drift = summaryFixture(); drift.analytics.universes[0].candidates[0].detail_shard_id = 'u0-f';
    expect(() => parseOpportunityCandidateSummarySnapshot(drift)).toThrow('shard binding');
  });

  it('accepts only a full detail row bound to the selected summary', () => {
    const response = parseOpportunityCandidateSummarySnapshot(summaryFixture(), SECONDARY);
    const item = response.universe.candidates[0]; const full = entryFixture();
    const detail = full.analytics.universes[1].candidates[0];
    const shard = { schema_version: '1.0', contract_version: 'opportunity-candidate-detail-shard/1.0',
      publication_id: response.publication_id, candidate_analytics_logical_fingerprint: response.logical_fingerprint,
      shard_id: item.detail_shard_id, universe_id: SECONDARY, stable_id_prefix: '1', candidates: [detail], item_count: 1,
      logical_fingerprint: '8'.repeat(64) };
    expect(parseOpportunityCandidateDetailShard(shard, response, item).ticker).toBe('TEST');
    const drift = { ...shard, universe_id: PRIMARY };
    expect(() => parseOpportunityCandidateDetailShard(drift, response, item)).toThrow('binding');
  });
});
