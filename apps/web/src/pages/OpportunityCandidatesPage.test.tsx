import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { I18nProvider } from '../i18n/I18nProvider';
import { OpportunityCandidatesPage } from './OpportunityCandidatesPage';

const { getOpportunityCandidates, getCandidateStrategies } = vi.hoisted(() => ({
  getOpportunityCandidates: vi.fn(),
  getCandidateStrategies: vi.fn(),
}));

vi.mock('../api/opportunityCandidates', () => ({
  getOpportunityCandidates,
  getOpportunityCandidateDetail: vi.fn(),
}));
vi.mock('../api/candidateStrategies', () => ({ getCandidateStrategies }));

const channels = [
  'momentum_breakout', 'strong_stock_pullback', 'trend_continuation',
  'technical_reversal', 'fundamental_value_reversal', 'defensive_rotation',
] as const;

describe('strategy-channel workspace', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, '', '/dashboard/?view=candidates&lang=en');
    getOpportunityCandidates.mockResolvedValue({
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
        quality_counts: {}, stage_counts: {}, candidates: [], candidate_batch_logical_fingerprint: 'c'.repeat(64),
        risk_modes: ['conservative', 'balanced', 'aggressive'].map((risk_mode) => ({
          risk_mode, eligible_count: 0, rejected_count: 0, display_cap: 30,
          displayed_instrument_ids: [], logical_fingerprint: 'd'.repeat(64),
        })),
      },
    });
    getCandidateStrategies.mockResolvedValue({
      as_of_session: '2026-08-26', default_universe_id: 'provider_classified_common_shares_v1',
      selected_universe_id: 'provider_classified_common_shares_v1',
      universe_order: ['provider_classified_common_shares_v1', 'provider_classified_common_shares_plus_adrs_v1'],
      channel_order: channels, source: {}, warnings: [], logical_fingerprint: 'e'.repeat(64),
      fixed_baseline_not_chronologically_validated: true,
      universe: {
        universe_id: 'provider_classified_common_shares_v1', logical_fingerprint: 'f'.repeat(64),
        channels: channels.map((channel) => ({
          channel, status_counts: channel === 'momentum_breakout' ? { advance_to_research: 1 } : { unavailable: 1718 },
          qualifying_count: channel === 'momentum_breakout' ? 1 : 0, display_cap: 8,
          logical_fingerprint: '1'.repeat(64),
          displayed_records: channel === 'momentum_breakout' ? [{
            as_of_session: '2026-08-26', universe_id: 'provider_classified_common_shares_v1',
            instrument_id: '11111111-1111-4111-8111-111111111111', ticker: 'ABCD', security_type: 'CS',
            channel, status: 'advance_to_research', channel_score: '82.5', within_channel_rank: 1,
            market_fit: 'neutral', market_fit_reason_codes: [], evidence: [], missing_required_evidence_codes: [],
            why_surfaced_codes: ['bounded_breakout_confirmed'], first_rejection_code: 'breakout_may_fail_or_reverse',
            what_would_make_researchable_codes: [], invalidation_codes: [], required_manual_check_codes: [],
            warning_codes: [], logical_fingerprint: '2'.repeat(64),
          }] : [],
        })),
      },
    });
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
    expect(await screen.findByText('ABCD')).toBeInTheDocument();
    expect(screen.getByText('Compare like with like')).toBeInTheDocument();
    expect(screen.getByText('Human review remains required')).toBeInTheDocument();
    expect(screen.getAllByText('Momentum breakout').length).toBeGreaterThan(1);
    fireEvent.click(screen.getByText('ABCD').closest('button')!);
    expect(screen.getByRole('dialog')).toHaveTextContent('ABCD · Momentum breakout');
    expect(screen.getByRole('dialog')).toHaveTextContent('The breakout can fail or reverse.');
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
});
