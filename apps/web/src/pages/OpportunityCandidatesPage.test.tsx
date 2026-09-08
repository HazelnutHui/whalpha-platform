import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { I18nProvider } from '../i18n/I18nProvider';
import { OpportunityCandidatesPage } from './OpportunityCandidatesPage';

const { getOpportunityCandidates, getOpportunityCandidateDetail, getCandidateStrategies } = vi.hoisted(() => ({
  getOpportunityCandidates: vi.fn(),
  getOpportunityCandidateDetail: vi.fn(),
  getCandidateStrategies: vi.fn(),
}));

vi.mock('../api/opportunityCandidates', () => ({
  getOpportunityCandidates,
  getOpportunityCandidateDetail,
}));
vi.mock('../api/candidateStrategies', () => ({ getCandidateStrategies }));

const channels = [
  'momentum_breakout', 'strong_stock_pullback', 'trend_continuation',
  'technical_reversal', 'fundamental_value_reversal', 'defensive_rotation',
] as const;
const parameterFingerprint = '13312df3e5b132223878582b8cd3af533a880e9f2f0d520f8520b46b97138ac9';
const instrumentId = '11111111-1111-4111-8111-111111111111';
const candidateSummary = {
  instrument_id: instrumentId, ticker: 'ABCD', security_type: 'CS', base_score: '82.0000', latest_price: '101.0000',
  median_dollar_volume_20: '50000000.0000', data_quality_status: 'passed', score_logical_fingerprint: '8'.repeat(64),
  confidence: { source_completeness: '1.0000', history_completeness: '1.0000', relationship_support: '1.0000', state_confirmation_support: '1.0000', confirmation_session_count: 2, confidence: '1.0000', disclaimer: 'data_support_not_success_probability' },
  state: { final_stage: 'prepare' }, detail_file: 'detail.json', detail_shard_id: '0',
  risk_dispositions: ['conservative', 'balanced', 'aggressive'].map((risk_mode) => ({ risk_mode, eligible: true, risk_adjusted_rank: 1, rejection_reason_codes: [] })),
  entry_summary: { review_posture: 'technical_review_ready', technical_setup: 'breakout_confirmed', extension_risk: 'low', reference_support_distance_pct: '0.0200' },
};
const componentIds = ['market_alignment', 'etf_sector_alignment', 'stock_relative_strength', 'trend_quality', 'volume_participation', 'volatility_risk', 'liquidity_suitability'];
const candidateDetail = {
  ...candidateSummary, adjusted_score: '82.0000', configured_weight_available: '100.0000', missingness_penalty: '0.0000',
  annualized_volatility_10: '0.2500', maximum_absolute_open_gap_5: '0.0300', current_volume_ratio: '1.2000',
  primary_driver_instrument_id: null, primary_driver_ticker: 'SMH', driver_correlation_20: '0.6700', relationship_kind: 'price_derived_exposure_proxy',
  components: componentIds.map((component_id, index) => ({ component_id, configured_weight: index === 2 ? '25.0000' : '12.5000', effective_weight: index === 2 ? '25.0000' : '12.5000', score: index === 2 ? '88.0000' : '70.0000', contribution: index === 2 ? '22.0000' : '10.0000', availability: 'available', cap_applied: null, reason_codes: [], metrics: [{ metric_id: component_id === 'market_alignment' ? 'regime_score' : 'current_volume_ratio', raw_value: component_id === 'market_alignment' ? '55.0000' : '1.2000', raw_unit: component_id === 'market_alignment' ? 'score' : 'ratio', normalized_value: '70.0000', availability: 'available', missing_reason: null, evidence_type: 'fact', source_sessions: ['2026-08-26'], reason_codes: [] }] })),
  evidence: [], invalidation_condition_codes: [], reason_codes: [], warning_codes: [],
  state: { final_stage: 'prepare', transition_status: 'held', transition_rule_id: 'fixed', pending_target_stage: null, stage_confirmation_count: 2, required_confirmation_sessions: 2, breakout_triggered: true, stale_state: false, manual_review_required: false, gate_results: [], reason_codes: [], logical_fingerprint: '9'.repeat(64) },
  entry_geometry: { as_of_session: '2026-08-26', universe_id: 'provider_classified_common_shares_v1', instrument_id: instrumentId, ticker: 'ABCD', security_type: 'CS', candidate_stage: 'prepare', candidate_base_score: '82.0000', relative_strength_component_score: '88.0000', trend_component_score: '70.0000', volume_climax_risk_candidate: false, extension_risk: 'low', technical_setup: 'breakout_confirmed', review_posture: 'technical_review_ready', first_rejection_code: null, why_now_codes: [], supporting_fact_codes: [], counterevidence_codes: [], what_would_make_reviewable_codes: [], technical_invalidation_codes: ['close_below_reference_support_requires_reunderwrite'], required_manual_check_codes: [], warnings: [], logical_fingerprint: '7'.repeat(64), metrics: { availability: 'available', close: '101.0000', sma_10: '99.0000', sma_20: '96.0000', atr_14: '2.0000', return_3: '0.0200', return_5: '0.0400', close_to_sma_10_atr: '1.0000', close_to_sma_20_atr: '2.5000', move_5_volatility_units: '1.1000', consecutive_up_sessions: 2, current_gap_atr: '0.1000', current_range_atr: '0.8000', current_close_location: '0.7000', current_volume_ratio: '1.2000', prior_five_session_close_high: '100.0000', prior_five_session_close_low: '94.0000', breakout_distance_atr: '0.5000', pullback_from_prior_high_atr: '-0.5000', reference_support_kind: 'sma20', reference_support_value: '96.0000', reference_support_distance_pct: '0.0521', missing_reason_codes: [] } },
};

function candidateResponse(summary: Record<string, unknown> = candidateSummary) {
  return {
    as_of_session: '2026-08-26', default_universe_id: 'provider_classified_common_shares_v1',
    selected_universe_id: 'provider_classified_common_shares_v1',
    universe_order: ['provider_classified_common_shares_v1', 'provider_classified_common_shares_plus_adrs_v1'],
    risk_mode_order: ['conservative', 'balanced', 'aggressive'], source: {}, warnings: [],
    logical_fingerprint: 'a'.repeat(64), publication_contract_version: 'opportunity-candidate-publication/1.1',
    snapshot_contract_version: 'opportunity-candidate-summary-snapshot/1.0', publication_id: 'review',
    detail_files: [], strategy_available: true,
    universe: {
      universe_id: 'provider_classified_common_shares_v1', universe_member_count: 1718,
      membership_fingerprint: 'b'.repeat(64), bar_covered_member_count: 1716, missing_member_count: 2,
      quality_counts: {}, stage_counts: {}, candidates: [summary], candidate_batch_logical_fingerprint: 'c'.repeat(64),
      risk_modes: ['conservative', 'balanced', 'aggressive'].map((risk_mode) => ({
        risk_mode, eligible_count: 0, rejected_count: 0, display_cap: 30,
        displayed_instrument_ids: [], logical_fingerprint: 'd'.repeat(64),
      })),
    },
  };
}

function strategyAssessment(channel: typeof channels[number]) {
  return {
    as_of_session: '2026-08-26', universe_id: 'provider_classified_common_shares_v1',
    instrument_id: instrumentId, ticker: 'ABCD', security_type: 'CS',
    channel, status: 'advance_to_research', channel_score: '85.0000', within_channel_rank: 1,
    parameter_fingerprint: parameterFingerprint,
    market_fit: 'neutral', market_fit_reason_codes: [], evidence: [
      ...['stock_relative_strength', 'trend_quality', 'volume_participation'].map((component) => ({
        evidence_id: `component_${component}`, evidence_kind: 'supporting', role: 'primary', source_kind: 'price_volume', evidence_type: 'statistical_inference', availability: 'available', observed_value: '80.0000', raw_unit: 'component_score_0_100', source_session: '2026-08-26', missing_reason_code: null, reason_codes: [],
      })),
      { evidence_id: 'entry_technical_setup', evidence_kind: 'supporting', role: 'primary', source_kind: 'price_volume', evidence_type: 'statistical_inference', availability: 'available', observed_value: 'breakout_confirmed', raw_unit: 'technical_setup', source_session: '2026-08-26', missing_reason_code: null, reason_codes: [] },
      { evidence_id: 'entry_extension_risk', evidence_kind: 'counterevidence', role: 'primary', source_kind: 'price_volume', evidence_type: 'statistical_inference', availability: 'available', observed_value: 'low', raw_unit: 'extension_risk', source_session: '2026-08-26', missing_reason_code: null, reason_codes: [] },
    ], missing_required_evidence_codes: [],
    why_surfaced_codes: ['bounded_breakout_confirmed'], first_rejection_code: channel === 'strong_stock_pullback' ? 'pullback_may_break_support' : channel === 'trend_continuation' ? 'trend_may_be_late_cycle_or_crowded' : 'breakout_may_fail_or_reverse',
    what_would_make_researchable_codes: [], invalidation_codes: [], required_manual_check_codes: [],
    warning_codes: [], logical_fingerprint: '2'.repeat(64),
  };
}

function strategyResponse(overlap = false) {
  return {
    as_of_session: '2026-08-26', default_universe_id: 'provider_classified_common_shares_v1',
    selected_universe_id: 'provider_classified_common_shares_v1',
    universe_order: ['provider_classified_common_shares_v1', 'provider_classified_common_shares_plus_adrs_v1'],
    channel_order: channels, source: { strategy_parameter_fingerprint: parameterFingerprint }, warnings: [], logical_fingerprint: 'e'.repeat(64),
    fixed_baseline_not_chronologically_validated: true,
    universe: {
      universe_id: 'provider_classified_common_shares_v1', logical_fingerprint: 'f'.repeat(64),
      channels: channels.map((channel) => {
        const displayed = channel === 'momentum_breakout' || (overlap && channel === 'trend_continuation');
        return {
          channel, status_counts: displayed ? { advance_to_research: 1 } : { unavailable: 1718 },
          qualifying_count: displayed ? 1 : 0, display_cap: 8,
          logical_fingerprint: '1'.repeat(64),
          displayed_records: displayed ? [strategyAssessment(channel)] : [],
        };
      }),
    },
  };
}

describe('strategy-channel workspace', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, '', '/dashboard/?view=candidates&lang=en');
    getOpportunityCandidates.mockResolvedValue(candidateResponse());
    getCandidateStrategies.mockResolvedValue(strategyResponse());
    getOpportunityCandidateDetail.mockResolvedValue(candidateDetail);
  });

  afterEach(() => { cleanup(); vi.clearAllMocks(); });

  it('keeps the strategy payload lazy and presents same-channel reasons separately from trade decisions', async () => {
    render(<I18nProvider><OpportunityCandidatesPage /></I18nProvider>);
    await screen.findByRole('button', { name: 'Strategy channels' });
    expect(getCandidateStrategies).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Strategy channels' }));
    await waitFor(() => expect(getCandidateStrategies).toHaveBeenCalledTimes(1));
    expect(new URL(window.location.href).searchParams.get('candidateView')).toBe('strategy');
    expect(screen.queryByRole('button', { name: 'Balanced' })).not.toBeInTheDocument();
    expect(screen.getByText('Advance + Watch pool')).toBeInTheDocument();
    expect((await screen.findAllByText('ABCD')).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole('heading', { name: "Today's cross-channel decision desk" })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Overlap and trade-readiness check' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Research priority versus chase risk' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'ABCD, rank 1, score 85.0, extension risk Low' })).toBeInTheDocument();
    expect(screen.getByText('1 / 6')).toBeInTheDocument();
    expect(screen.getAllByText('Technical review may proceed').length).toBeGreaterThan(0);
    expect(screen.getByText('Open the complete price-and-evidence review →')).toBeInTheDocument();
    expect(screen.getByText('Compare like with like')).toBeInTheDocument();
    expect(screen.getByText('Human review remains required')).toBeInTheDocument();
    expect(screen.getAllByText('Momentum breakout').length).toBeGreaterThan(1);
    expect(screen.getAllByText('Triggered · review').length).toBe(2);
    expect(screen.getByText(/not a list of completed breakouts/)).toBeInTheDocument();
    fireEvent.click(screen.getByText('How this channel ranks'));
    expect(screen.getByText('35%')).toBeInTheDocument();
    expect(screen.getByText(/current trend-continuation baseline overlaps heavily/)).toBeInTheDocument();
    expect(screen.getByText(/separate audited shadow layer now describes the prior 10-session base/)).toBeInTheDocument();
    expect(screen.getByText(/45% normalized 5-session stock return versus SPY/)).toBeInTheDocument();
    expect(screen.getByText('All Advance results come before all Watch results. Within each status: channel score descending, then ticker and stable instrument ID as deterministic tie-breakers.')).toBeInTheDocument();
    fireEvent.click(screen.getAllByText('ABCD')[0].closest('button')!);
    expect(await screen.findByRole('dialog')).toHaveTextContent('ABCD · Momentum breakout');
    expect(getOpportunityCandidateDetail).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('dialog')).toHaveTextContent('Triggered · review');
    expect(screen.getByRole('dialog')).toHaveTextContent('The breakout can fail or reverse.');
    expect(screen.getByRole('dialog')).toHaveTextContent('Why this exact score');
    expect(screen.getByRole('dialog')).toHaveTextContent('Research priority versus trade-review readiness');
    expect(screen.getByRole('dialog')).toHaveTextContent('Event timing');
    expect(screen.getByRole('dialog')).toHaveTextContent('Position / chase-risk review');
    expect(screen.getByRole('dialog')).toHaveTextContent('The browser independently reconstructs the published score');
    expect(screen.getByRole('dialog')).toHaveTextContent('Complete technical trade review');
    expect(screen.getByRole('dialog')).toHaveTextContent('From market context to trade review');
    expect(screen.getByRole('dialog')).toHaveTextContent('Where price sits now');
    expect(screen.getByRole('dialog')).toHaveTextContent('Why it ranks here');
  });

  it('restores a directly linked strategy channel and makes unavailable evidence explicit', async () => {
    window.history.replaceState({}, '', '/dashboard/?view=candidates&lang=en&candidateView=strategy&candidateStrategy=technical_reversal');
    render(<I18nProvider><OpportunityCandidatesPage /></I18nProvider>);
    await waitFor(() => expect(getCandidateStrategies).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole('button', { name: /^Oversold technical reversal/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /^Oversold technical reversal/ })).toHaveTextContent('Evidence pending · 1,718');
    expect(screen.getByText('Stabilization and reclaim facts are not yet governed, so no proxy result is shown.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /^Strong-stock pullback/ }));
    expect(new URL(window.location.href).searchParams.get('candidateStrategy')).toBe('strong_stock_pullback');
  });

  it('renders the decision desk in Chinese without changing its evidence scope', async () => {
    window.history.replaceState({}, '', '/dashboard/?view=candidates&lang=zh');
    render(<I18nProvider><OpportunityCandidatesPage /></I18nProvider>);
    fireEvent.click(await screen.findByRole('button', { name: '策略通道' }));
    expect(await screen.findByRole('heading', { name: '今日跨策略决策台' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '研究优先级与追高风险图' })).toBeInTheDocument();
    expect(screen.getByText('通道内第 1 名')).toBeInTheDocument();
    expect(screen.getByText(/不会计算跨策略总分/)).toBeInTheDocument();
  });

  it('shows stable-ID overlap without presenting it as formal sector concentration', async () => {
    getCandidateStrategies.mockResolvedValueOnce(strategyResponse(true));
    render(<I18nProvider><OpportunityCandidatesPage /></I18nProvider>);
    fireEvent.click(await screen.findByRole('button', { name: 'Strategy channels' }));
    expect(await screen.findByText('2 / 6')).toBeInTheDocument();
    expect(screen.getByText('Repeated display tickers: ABCD')).toBeInTheDocument();
    expect(screen.getByText(/not formal sector concentration/)).toBeInTheDocument();
    expect(screen.getAllByText(/Also appears in:/).length).toBeGreaterThan(0);
    expect(document.querySelector('.strategy-map-point-repeated')).toBeInTheDocument();
  });

  it('keeps research rank visible while all Candidate risk modes reject the trade review', async () => {
    const rejectedDispositions = ['conservative', 'balanced', 'aggressive'].map((risk_mode) => ({
      risk_mode, eligible: false, risk_adjusted_rank: null,
      rejection_reason_codes: ['risk_mode_volatility_ceiling_failed', 'risk_mode_gap_ceiling_failed'],
    }));
    const rejectedSummary = {
      ...candidateSummary,
      risk_dispositions: rejectedDispositions,
      entry_summary: { ...candidateSummary.entry_summary, review_posture: 'monitor_for_trigger', technical_setup: 'no_viable_setup', extension_risk: 'moderate' },
    };
    getOpportunityCandidates.mockResolvedValueOnce(candidateResponse(rejectedSummary));
    getOpportunityCandidateDetail.mockResolvedValueOnce({
      ...candidateDetail,
      risk_dispositions: rejectedDispositions,
      state: candidateDetail.state,
      entry_geometry: { ...candidateDetail.entry_geometry, review_posture: 'monitor_for_trigger', technical_setup: 'no_viable_setup', extension_risk: 'moderate' },
    });
    render(<I18nProvider><OpportunityCandidatesPage /></I18nProvider>);
    fireEvent.click(await screen.findByRole('button', { name: 'Strategy channels' }));
    expect((await screen.findAllByText('Risk gates reject')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Gap / realized-volatility risk requires explicit review.').length).toBeGreaterThan(0);
    fireEvent.click(screen.getAllByText('ABCD')[0].closest('button')!);
    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('Research priority versus trade-review readiness');
    expect(dialog).toHaveTextContent('All three Candidate risk modes reject the security');
    expect(dialog).toHaveTextContent('Realized volatility exceeds one or more risk-mode ceilings.');
    expect(dialog).toHaveTextContent('The recent maximum opening gap exceeds one or more risk-mode ceilings.');
  });

  it('fails closed if the bound Candidate detail stable ID differs', async () => {
    getOpportunityCandidateDetail.mockResolvedValueOnce({ ...candidateDetail, instrument_id: '22222222-2222-4222-8222-222222222222' });
    render(<I18nProvider><OpportunityCandidatesPage /></I18nProvider>);
    fireEvent.click(await screen.findByRole('button', { name: 'Strategy channels' }));
    await screen.findByRole('heading', { name: "Today's cross-channel decision desk" });
    fireEvent.click(screen.getAllByText('ABCD')[0].closest('button')!);
    expect(await screen.findByRole('alert')).toHaveTextContent('The requested data could not be loaded');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
