import { describe, expect, it } from 'vitest';

import type { StrategyAssessment, StrategyEvidence } from './candidateStrategies';
import {
  STRATEGY_METHOD_PARAMETER_FINGERPRINT,
  strategyMethod,
  strategyScoreBreakdown,
} from './candidateStrategyMethods';

function evidence(evidence_id: string, observed_value: string): StrategyEvidence {
  return {
    evidence_id, evidence_kind: 'supporting', role: 'primary', source_kind: 'price_volume',
    evidence_type: 'statistical_inference', availability: 'available', observed_value,
    raw_unit: 'component_score_0_100', source_session: '2026-08-26',
    missing_reason_code: null, reason_codes: [],
  };
}

function assessment(score = '85.0000'): StrategyAssessment {
  return {
    as_of_session: '2026-08-26', universe_id: 'primary',
    instrument_id: '11111111-1111-4111-8111-111111111111', ticker: 'TEST', security_type: 'CS',
    channel: 'momentum_breakout', status: 'advance_to_research', channel_score: score,
    within_channel_rank: 1, parameter_fingerprint: STRATEGY_METHOD_PARAMETER_FINGERPRINT,
    market_fit: 'unavailable', market_fit_reason_codes: [],
    evidence: [
      evidence('component_stock_relative_strength', '80.0000'),
      evidence('component_trend_quality', '80.0000'),
      evidence('component_volume_participation', '80.0000'),
      { ...evidence('entry_technical_setup', 'breakout_confirmed'), raw_unit: 'technical_setup' },
    ],
    missing_required_evidence_codes: [], why_surfaced_codes: [],
    first_rejection_code: 'breakout_may_fail_or_reverse', what_would_make_researchable_codes: [],
    invalidation_codes: [], required_manual_check_codes: [], warning_codes: [],
    logical_fingerprint: 'a'.repeat(64),
  };
}

describe('strategy methodology reconstruction', () => {
  it('exposes the exact frozen formula and reconstructs the server score', () => {
    const method = strategyMethod('momentum_breakout', STRATEGY_METHOD_PARAMETER_FINGERPRINT);
    const rows = strategyScoreBreakdown(assessment(), STRATEGY_METHOD_PARAMETER_FINGERPRINT);

    expect(method?.components.map((item) => item.weight_bps)).toEqual([3500, 2500, 1500, 2500]);
    expect(rows.map((item) => item.contribution)).toEqual(['28.0000', '20.0000', '12.0000', '25.0000']);
  });

  it('fails closed on an unknown parameter set or a non-reconstructing score', () => {
    expect(() => strategyMethod('momentum_breakout', 'a'.repeat(64))).toThrow('Unsupported strategy methodology');
    expect(() => strategyScoreBreakdown(assessment('84.9999'), STRATEGY_METHOD_PARAMETER_FINGERPRINT)).toThrow('does not reconstruct');
  });
});
