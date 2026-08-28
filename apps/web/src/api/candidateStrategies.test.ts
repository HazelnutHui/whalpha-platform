import { describe, expect, it } from 'vitest';

import { parseCandidateStrategyProduct } from './candidateStrategies';

const SHA = 'a'.repeat(64);
const PARAMETER = '13312df3e5b132223878582b8cd3af533a880e9f2f0d520f8520b46b97138ac9';
const ID = '00000000-0000-4000-8000-000000000001';
const CHANNELS = ['momentum_breakout', 'strong_stock_pullback', 'trend_continuation', 'technical_reversal', 'fundamental_value_reversal', 'defensive_rotation'];

function assessment(channel: string) {
  return {
    schema_version: '1.0', contract_version: 'candidate-strategy-channel-shadow/1.0',
    calculation_version: 'candidate-strategy-channel-shadow-v1.1.0', parameter_set_id: 'fixed',
    parameter_fingerprint: PARAMETER, as_of_session: '2026-08-26', universe_id: 'primary',
    instrument_id: ID, ticker: 'TEST', security_type: 'CS', channel,
    status: 'advance_to_research', channel_score: '85.0000', within_channel_rank: 1,
    score_meaning: 'within_channel_research_priority_not_return_probability', market_fit: 'unavailable',
    market_fit_reason_codes: ['channel_specific_market_fit_not_validated'], market_fit_separate_from_channel_score: true,
    first_rejection_is_risk_not_status_reason: true, source_candidate_fingerprint: SHA,
    source_entry_geometry_fingerprint: SHA,
    evidence: [
      ...['stock_relative_strength', 'trend_quality', 'volume_participation'].map((component) => ({ evidence_id: `component_${component}`, evidence_kind: 'supporting', role: 'primary',
        source_kind: 'price_volume', evidence_type: 'statistical_inference', availability: 'available',
        observed_value: '80.0000', raw_unit: 'component_score_0_100', source_session: '2026-08-26',
        missing_reason_code: null, reason_codes: ['existing_candidate_component_reused'] })),
      { evidence_id: 'entry_technical_setup', evidence_kind: 'supporting', role: 'primary',
        source_kind: 'price_volume', evidence_type: 'statistical_inference', availability: 'available',
        observed_value: 'breakout_confirmed', raw_unit: 'technical_setup', source_session: '2026-08-26',
        missing_reason_code: null, reason_codes: ['entry_geometry_reused_without_browser_reclassification'] },
    ],
    missing_required_evidence_codes: [], why_surfaced_codes: ['bounded_breakout_confirmed'],
    first_rejection_code: 'breakout_may_fail_or_reverse', what_would_make_researchable_codes: [],
    invalidation_codes: ['candidate_state_invalidated'], required_manual_check_codes: ['company_event_and_earnings_timing'],
    warning_codes: ['fixed_baseline_not_chronologically_validated'], logical_fingerprint: SHA,
  };
}

function universe(id: string, index: number) {
  return {
    schema_version: '1.0', contract_version: 'candidate-strategy-channel-consumer/1.0',
    as_of_session: '2026-08-26', universe_id: id, source_batch_logical_fingerprint: `${index + 1}`.repeat(64),
    channel_order: CHANNELS,
    channels: CHANNELS.map((channel, channelIndex) => ({
      schema_version: '1.0', channel,
      status_counts: channelIndex === 0 ? { advance_to_research: 1 } : { unavailable: 1 },
      qualifying_count: channelIndex === 0 ? 1 : 0, display_cap: 8,
      displayed_records: channelIndex === 0 ? [{ ...assessment(channel), universe_id: id }] : [],
      logical_fingerprint: SHA,
    })),
    cross_channel_score_prohibited: true, shadow_only: true, warnings: ['shadow_only_not_publication_input'],
    logical_fingerprint: `${index + 3}`.repeat(64),
  };
}

function payload() {
  return {
    schema_version: '1.0', contract_version: 'candidate-strategy-channel-product/1.0',
    as_of_session: '2026-08-26', default_universe_id: 'primary', universe_order: ['primary', 'secondary'],
    channel_order: CHANNELS,
    source: {
      strategy_audit_manifest_sha256: SHA, strategy_audit_logical_fingerprint: SHA,
      strategy_audit_contract_version: 'candidate-strategy-channel-audit/1.0',
      strategy_contract_version: 'candidate-strategy-channel-shadow/1.0',
      strategy_consumer_contract_version: 'candidate-strategy-channel-consumer/1.0',
      strategy_parameter_fingerprint: PARAMETER, strategy_oracle_mismatch_count: 0,
      strategy_input_permutation_match: true, strategy_oracle_production_calculator_imported: false,
      external_request_count: 0, production_write_count: 0,
      candidate_publication_contract_version: 'opportunity-candidate-publication/1.1',
      candidate_analytics_logical_fingerprint: SHA, candidate_audit_logical_fingerprint: SHA,
      entry_geometry_audit_logical_fingerprint: SHA,
      source_candidate_batch_fingerprints: [SHA, SHA], source_entry_geometry_batch_fingerprints: [SHA, SHA],
      strategy_batch_fingerprints: ['1'.repeat(64), '2'.repeat(64)],
      strategy_consumer_fingerprints: ['3'.repeat(64), '4'.repeat(64)],
    },
    universes: [universe('primary', 0), universe('secondary', 1)], language_neutral: true,
    research_priority_only: true, fixed_baseline_not_chronologically_validated: true,
    cross_channel_score_comparison_prohibited: true, market_fit_separate_and_unvalidated: true,
    event_context_auxiliary: true, underlying_stock_result_not_option_return: true,
    price_volume_not_fund_flow: true, guest_and_credential_capability_identical: true,
    warnings: ['fixed_baseline_not_chronologically_validated'], logical_fingerprint: SHA,
  };
}

describe('Candidate strategy-channel product parser', () => {
  it('keeps channel order, bounded ranks, and explicit unavailable channels', () => {
    const parsed = parseCandidateStrategyProduct(payload(), 'secondary');

    expect(parsed.selected_universe_id).toBe('secondary');
    expect(parsed.channel_order).toEqual(CHANNELS);
    expect(parsed.universe.channels[0].displayed_records[0].within_channel_rank).toBe(1);
    expect(parsed.universe.channels[3].qualifying_count).toBe(0);
    expect(parsed.fixed_baseline_not_chronologically_validated).toBe(true);
  });

  it('fails closed if cross-channel comparison is enabled', () => {
    expect(() => parseCandidateStrategyProduct({
      ...payload(), cross_channel_score_comparison_prohibited: false,
    })).toThrow('Unsupported strategy-channel product contract');
  });

  it('fails closed before the UI can render an untranslated explanation code', () => {
    const changed = payload();
    changed.universes[0].channels[0].displayed_records[0].why_surfaced_codes = ['unknown_reason'];
    expect(() => parseCandidateStrategyProduct(changed)).toThrow('Unknown strategy display reason');
  });
});
