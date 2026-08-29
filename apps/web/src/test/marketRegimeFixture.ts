import type { MarketRegimePreviewResponse, Relationship } from '../api/marketRegime';

const PRIMARY = 'provider_classified_common_shares_v1';
const SECONDARY = 'provider_classified_common_shares_plus_adrs_v1';
const states = ['divergence', 'synchronous_weakening', 'synchronous_strengthening', 'neutral'];

function relationship(index: number): Relationship {
  const pairId = `pair_${String(index + 1).padStart(2, '0')}`;
  const state = states[index % states.length];
  return {
    definition: { pair_id: pairId, registry_order: index, left_ticker: index === 1 ? 'IGV' : `L${index + 1}`, right_ticker: index === 1 ? 'QQQ' : `R${index + 1}`, relationship_family: index % 2 ? 'sector_vs_broad' : 'style', economic_rationale: `Economic rationale ${index + 1}.`, expected_interpretation: 'Relative performance is descriptive.', forbidden_interpretation: 'No causality or capital flow inference.', availability_requirement: 'complete paired closes' },
    current: {
      relationship_state: state, previous_relationship_state: index % 5 === 0 ? 'neutral' : state,
      confidence: 'low', availability: 'available', missing_reason: null,
      windows: ([5, 10, 20] as const).map((window) => ({ window_sessions: window, start_session: '2026-07-17', end_session: '2026-08-21', left_return: index === 1 ? '-0.0100000000' : '0.0200000000', right_return: index === 1 ? '-0.0300000000' : '0.0100000000', relative_return: '0.0200000000', rolling_correlation: '0.5000000000', daily_return_observation_count: window, direction_combination: 'both_positive', availability: 'available', missing_reason: null, reason_codes: ['window_available'] })),
      ratio_level: '1.1000000000', ratio_robust_z: null, ratio_percentile: null, correlation_20_prior_5: '0.6000000000', correlation_change_5: '-0.1000000000', reason_codes: ['short_history_low_confidence'], warnings: ['short_history'],
    },
    explanation: { left_observation: 'Left leg moved.', right_observation: 'Right leg moved.', relative_strength_observation: 'The left leg was relatively stronger.', correlation_observation: 'Correlation declined.', cross_window_observation: 'Windows agree.', supporting_evidence: ['Relative spread is positive.'], counterevidence: index % 3 ? [] : ['History is short.'], reason_codes: ['short_history_low_confidence'], disclaimers: ['statistical_relationship_not_causal'] },
    change_summary: {
      contract_version: 'relationship-change-summary/1.0', pair_id: pairId,
      as_of_session: '2026-08-21', current_state_run_started_session: '2026-08-19',
      current_state_run_session_count: 3, state_run_reaches_history_start: false,
      state_changed_this_session: index % 5 === 0, current_5_session_leader: 'left',
      windows: ([5, 10, 20] as const).map((window) => ({
        window_sessions: window, current_relative_return: '0.0200000000',
        prior_1_session_relative_return: '0.0150000000', change_1_session: '0.0050000000',
        prior_5_session_relative_return: '0.0100000000', change_5_sessions: '0.0100000000',
        leadership_change_1: 'strengthening', leadership_change_5: 'strengthening',
      })),
      reason_codes: ['state_run_derived_from_retained_relationship_history'],
      disclaimer: 'descriptive_change_not_predictive_signal',
    },
    state_timeline: {
      contract_version: 'relationship-state-timeline/1.0', pair_id: pairId,
      as_of_session: '2026-08-21', retained_first_session: '2026-07-24',
      retained_session_count: 21, displayed_session_count: 10, truncated_before: true,
      points: Array.from({ length: 10 }, (_, pointIndex) => ({
        as_of_session: `2026-08-${String(12 + pointIndex).padStart(2, '0')}`,
        relationship_state: pointIndex < 7 ? 'neutral' : state,
        confidence: 'low', changed_from_prior_retained_session: pointIndex === 0
          ? false : pointIndex === 7 && state !== 'neutral',
        windows: ([5, 10, 20] as const).map((window) => ({
          window_sessions: window, relative_return: ((pointIndex - 7) / 100).toFixed(10),
          availability: 'available',
        })),
      })),
      reason_codes: ['recent_points_derived_from_retained_relationship_history', 'older_points_compacted'],
      disclaimer: 'descriptive_history_not_predictive_signal',
    },
  };
}

function universe(id: string, display: string, count: number, score: string) {
  const contributions = ['21.0000', '16.2500', '12.0000', '8.2500', (Number(score) - 57.5).toFixed(4)];
  const dimensions = ['trend', 'breadth', 'volatility', 'liquidity_participation', 'leadership_dispersion'].map((dimension, index) => ({
    dimension_id: dimension, score: String(70 - index * 5) + '.0000', configured_weight: ['0.3000', '0.2500', '0.2000', '0.1500', '0.1000'][index], effective_weight: ['0.3000', '0.2500', '0.2000', '0.1500', '0.1000'][index], score_contribution: contributions[index], support_status: index === 3 ? 'conflicting' : 'supporting', rendered_explanation: `${dimension} fixed-rule explanation.`, raw_metrics: [{ metric_id: `${dimension}_metric`, lookback_sessions: 20, raw_value: '0.1234', raw_unit: 'ratio', normalized_value: '55.0000', configured_weight: '1.0000', effective_weight: '1.0000', weighted_contribution: '55.0000', availability: 'available', missing_reason: null, reason_codes: ['metric_available'] }], reason_codes: ['dimension_available'],
  }));
  const definition = { universe_id: id, display_name: display, catalog_order: id === PRIMARY ? 0 : 1, is_default: id === PRIMARY, member_count: count, membership_fingerprint: (id === PRIMARY ? 'a' : 'b').repeat(64) };
  const currentState = { composite: score, instantaneous_candidate_state: 'balanced', confirmed_state: 'balanced', transition_status: 'held', pending_target_state: null, confirmation_sessions_remaining: 0, in_hysteresis_band: false, supporting_dimension_ids: ['trend', 'volatility', 'leadership_dispersion'], conflicting_dimension_ids: ['liquidity_participation'], threshold_distances: [{ threshold_id: 'balanced_to_risk_on', threshold: '70.0000', signed_distance: '-6.0898', boundary_operator: '>=' }, { threshold_id: 'balanced_to_defensive', threshold: '45.0000', signed_distance: '18.9102', boundary_operator: '<' }], reason_codes: ['state_input_available', 'candidate_band_balanced', 'confirmed_state_held'] };
  const historyScores = ['55.0000', '57.0000', '59.0000', '61.0000', '62.0000', score];
  return { definition, composite: { regime_score: score, dimensions, reason_codes: ['composite_available'], logical_fingerprint: 'c'.repeat(64) }, current_state: currentState, current_state_explanation: { candidate_band_text: 'Composite maps to Balanced.', transition_text: 'Confirmed state held.', disclaimers: ['Not a recommendation.'], reason_codes: ['confirmed_state_held'] }, state_history: historyScores.map((value, index) => ({ ...currentState, as_of_session: `2026-08-${String(16 + index).padStart(2, '0')}`, composite: value })), dimension_explanations: [] };
}

export function marketRegimeFixture(selected = PRIMARY): MarketRegimePreviewResponse {
  const definitions = [{ universe_id: PRIMARY, display_name: 'Common Shares', catalog_order: 0, is_default: true, member_count: 1718, membership_fingerprint: 'a'.repeat(64) }, { universe_id: SECONDARY, display_name: 'Common Shares + ADRs', catalog_order: 1, is_default: false, member_count: 1831, membership_fingerprint: 'b'.repeat(64) }];
  return {
    schema_version: '1.0', contract_version: 'market-regime-opportunity-map-api/1.0', bundle_logical_fingerprint: 'd'.repeat(64), as_of_session: '2026-08-21', data_status: 'degraded_short_history', input_first_session: '2026-07-17', input_last_session: '2026-08-21', input_session_count: 26, default_universe_id: PRIMARY, selected_universe_id: selected, available_universes: definitions, source_logical_fingerprints: { phase1a: '1'.repeat(64), phase1b: '2'.repeat(64), phase2: '3'.repeat(64) }, regime: selected === PRIMARY ? universe(PRIMARY, 'Common Shares', 1718, '63.9102') : universe(SECONDARY, 'Common Shares + ADRs', 1831, '64.8167'), relationships: Array.from({ length: 16 }, (_, index) => relationship(index)), relationship_comparisons: Array.from({ length: 16 }, (_, index) => ({ pair_id: `pair_${String(index + 1).padStart(2, '0')}`, alignment: 'neutral', reason_codes: ['contemporaneous_only'] })), warnings: ['Only 26 completed XNYS sessions are available.'], quality_gates: [{ gate_id: 'source_custody', status: 'passed', reason_codes: ['verified'] }],
  };
}

export const PRIMARY_UNIVERSE = PRIMARY;
export const SECONDARY_UNIVERSE = SECONDARY;
