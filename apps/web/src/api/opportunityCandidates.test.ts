import { describe, expect, it } from 'vitest';

import { parseOpportunityCandidateSnapshot } from './opportunityCandidates';

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
    candidates: [candidate], candidate_batch_logical_fingerprint: 'f'.repeat(64),
  });
  const analytics = { schema_version: '1.0', contract_version: 'opportunity-candidate-publication/1.0', as_of_session: '2026-08-24', default_universe_id: PRIMARY, universe_order: [PRIMARY, SECONDARY], risk_mode_order: MODES, source: {}, universes: [universe(PRIMARY), universe(SECONDARY)], language_neutral: true, research_priority_only: true, underlying_stock_result_not_option_return: true, price_volume_not_fund_flow: true, warnings: ['short_candidate_state_history'], logical_fingerprint: '9'.repeat(64) };
  return { schema_version: '1.0', contract_version: 'opportunity-candidate-snapshot/1.0', publication_id: '2026-08-24T120000Z-abcdef0', payload_sha256: '1'.repeat(64), payload_logical_fingerprint: '2'.repeat(64), candidate_analytics_logical_fingerprint: analytics.logical_fingerprint, default_universe_id: PRIMARY, universe_order: [PRIMARY, SECONDARY], analytics };
}

describe('Opportunity Candidate snapshot parser', () => {
  it('accepts the fixed language-neutral contract and selected Universe', () => {
    const parsed = parseOpportunityCandidateSnapshot(fixture(), SECONDARY);
    expect(parsed.selected_universe_id).toBe(SECONDARY);
    expect(parsed.universe.candidates[0].ticker).toBe('TEST');
    expect(parsed.universe.risk_modes[1].displayed_instrument_ids).toHaveLength(1);
  });

  it('fails closed on version, rank, stage, component, or fingerprint drift', () => {
    const version = fixture(); version.contract_version = 'opportunity-candidate-snapshot/1.1';
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
});
