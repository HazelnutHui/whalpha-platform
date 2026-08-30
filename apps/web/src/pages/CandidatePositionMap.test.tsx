import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import type { CandidateEntryGeometry, CandidateItem } from '../api/opportunityCandidates';
import { I18nProvider } from '../i18n/I18nProvider';
import { CandidatePositionMap } from './OpportunityCandidatesPage';

const entry = {
  as_of_session: '2026-08-28', universe_id: 'provider_classified_common_shares_v1',
  instrument_id: '11111111-1111-4111-8111-111111111111', ticker: 'TEST', security_type: 'CS',
  candidate_stage: 'prepare', candidate_base_score: '78.0000', relative_strength_component_score: '82.0000',
  trend_component_score: '76.0000', volume_climax_risk_candidate: false, extension_risk: 'moderate',
  technical_setup: 'breakout_watch', review_posture: 'monitor_for_trigger', first_rejection_code: 'breakout_not_confirmed',
  why_now_codes: [], supporting_fact_codes: [], counterevidence_codes: [], what_would_make_reviewable_codes: [],
  technical_invalidation_codes: [], required_manual_check_codes: [], warnings: [], logical_fingerprint: 'a'.repeat(64),
  metrics: {
    availability: 'available', close: '104.0000000000', sma_10: '101.0000000000', sma_20: '98.0000000000',
    atr_14: '2.0000000000', return_3: '0.0300000000', return_5: '0.0500000000',
    close_to_sma_10_atr: '1.5000000000', close_to_sma_20_atr: '3.0000000000', move_5_volatility_units: '1.2000000000',
    consecutive_up_sessions: 2, current_gap_atr: '0.1000000000', current_range_atr: '0.8000000000',
    current_close_location: '0.7000000000', current_volume_ratio: '1.1000000000',
    prior_five_session_close_high: '105.0000000000', prior_five_session_close_low: '99.0000000000',
    breakout_distance_atr: '-0.5000000000', pullback_from_prior_high_atr: '0.5000000000',
    reference_support_kind: 'sma20', reference_support_value: '98.0000000000', reference_support_distance_pct: '0.0576923077',
    missing_reason_codes: [],
  },
} satisfies CandidateEntryGeometry;

const state = {
  final_stage: 'prepare', transition_status: 'confirmed', transition_rule_id: 'prepare_confirmed', pending_target_stage: null,
  stage_confirmation_count: 2, required_confirmation_sessions: 3, breakout_triggered: false, stale_state: false,
  manual_review_required: false, gate_results: [], reason_codes: [], logical_fingerprint: 'b'.repeat(64),
} satisfies CandidateItem['state'];

describe('CandidatePositionMap', () => {
  beforeEach(() => { window.localStorage.clear(); window.history.replaceState({}, '', '/dashboard/?lang=en'); });
  afterEach(cleanup);

  it('shows only published reference levels and distinguishes confirmation from signal age', () => {
    render(<I18nProvider><CandidatePositionMap entry={entry} state={state} /></I18nProvider>);
    expect(screen.getByRole('heading', { name: 'Where price sits now' })).toBeInTheDocument();
    expect(screen.getByText('Prior 5-session close high')).toBeInTheDocument();
    expect(screen.getByText('Selected reference support')).toBeInTheDocument();
    expect(screen.getByText('2 / 3')).toBeInTheDocument();
    expect(screen.getByText(/not signal age/)).toBeInTheDocument();
    expect(screen.getByText(/does not reconstruct a price path/)).toBeInTheDocument();
  });

  it('fails closed when the entry-geometry facts are unavailable', () => {
    const unavailable = { ...entry, metrics: { ...entry.metrics, availability: 'unavailable' as const } };
    render(<I18nProvider><CandidatePositionMap entry={unavailable} state={state} /></I18nProvider>);
    expect(screen.getByText('The published facts are not sufficient to draw a reliable position map.')).toBeInTheDocument();
    expect(screen.queryByText('Prior 5-session close high')).not.toBeInTheDocument();
  });
});
