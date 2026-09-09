import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { I18nProvider } from '../i18n/I18nProvider';
import { marketRegimeFixture, PRIMARY_UNIVERSE } from '../test/marketRegimeFixture';
import { SectorRotationPage } from './SectorRotationPage';

const { getSectorRotation, getMarketRegimePreview, getOpportunityCandidates } = vi.hoisted(() => ({
  getSectorRotation: vi.fn(), getMarketRegimePreview: vi.fn(), getOpportunityCandidates: vi.fn(),
}));

vi.mock('../api/sectorRotation', async (original) => ({ ...(await original<typeof import('../api/sectorRotation')>()), getSectorRotation }));
vi.mock('../api/marketRegime', async (original) => ({ ...(await original<typeof import('../api/marketRegime')>()), getMarketRegimePreview }));
vi.mock('../api/opportunityCandidates', async (original) => ({ ...(await original<typeof import('../api/opportunityCandidates')>()), getOpportunityCandidates }));

const publicationId = '2026-08-21T120000Z-abcdef012345';

function rotation() {
  const tickers = ['XLC', 'XLY', 'XLP', 'XLE', 'XLF', 'XLV', 'XLI', 'XLB', 'XLRE', 'XLK', 'XLU'];
  return {
    publication_id: publicationId, payload_sha256: '1'.repeat(64), payload_logical_fingerprint: '2'.repeat(64),
    audit_logical_fingerprint: '3'.repeat(64), parameter_fingerprint: '4'.repeat(64), history_source_fingerprint: '5'.repeat(64),
    product_logical_fingerprint: '6'.repeat(64), snapshot_logical_fingerprint: '7'.repeat(64), as_of_session: '2026-08-21',
    input_session_count: 26, theme_status: 'unavailable_no_governed_membership', warnings: [],
    records: tickers.map((ticker, index) => ({
      ticker, sector: ['Communication Services', 'Consumer Discretionary', 'Consumer Staples', 'Energy', 'Financials', 'Health Care', 'Industrials', 'Materials', 'Real Estate', 'Technology', 'Utilities'][index],
      registry_order: index, as_of_session: '2026-08-21', five_day_relative_acceleration: '0.0020',
      posture: 'leading_improving', five_day_leadership_run_sessions: 3, run_reaches_history_start: false,
      availability: 'available', missing_reason: null, supporting_fact_codes: [], counterevidence_codes: [], warnings: [], logical_fingerprint: '8'.repeat(64),
      windows: ([5, 10, 20] as const).map((window) => ({
        window_sessions: window, start_session: '2026-07-17', end_session: '2026-08-21', etf_return: '0.0200', spy_return: '0.0100',
        relative_return: String((11 - index) / 1000), relative_rank: index + 1, available_peer_count: 11, availability: 'available', missing_reason: null,
      })),
    })),
  };
}

function candidates(session = '2026-08-21') {
  const records = Array.from({ length: 10 }, (_, index) => ({
    instrument_id: `${String(index).padStart(8, '0')}-1111-4111-8111-111111111111`, ticker: `NAME${index}`, security_type: 'CS',
    base_score: String(90 - index), latest_price: '100.0000', median_dollar_volume_20: '50000000.0000', data_quality_status: 'passed',
    score_logical_fingerprint: '9'.repeat(64), entry_geometry_logical_fingerprint: 'a'.repeat(64),
    confidence: { source_completeness: '1.0000', history_completeness: '1.0000', relationship_support: '0.0000', state_confirmation_support: '1.0000', confirmation_session_count: 2, confidence: '1.0000', disclaimer: 'data_support_not_success_probability' },
    state: { final_stage: index % 2 ? 'prepare' : 'watch' }, risk_dispositions: [],
    entry_summary: { review_posture: 'monitor_for_trigger', technical_setup: 'breakout_watch', extension_risk: index % 2 ? 'moderate' : 'low', reference_support_distance_pct: '0.0200' },
  }));
  return {
    as_of_session: session, default_universe_id: PRIMARY_UNIVERSE, selected_universe_id: PRIMARY_UNIVERSE,
    universe_order: [PRIMARY_UNIVERSE, 'provider_classified_common_shares_plus_adrs_v1'], risk_mode_order: ['conservative', 'balanced', 'aggressive'],
    source: {}, warnings: [], logical_fingerprint: 'b'.repeat(64), publication_contract_version: 'opportunity-candidate-publication/1.1',
    snapshot_contract_version: 'opportunity-candidate-summary-snapshot/1.0', publication_id: publicationId, detail_files: [],
    universe: { universe_id: PRIMARY_UNIVERSE, universe_member_count: 1718, membership_fingerprint: 'c'.repeat(64), bar_covered_member_count: 1716, missing_member_count: 2, quality_counts: {}, stage_counts: {}, candidates: records, candidate_batch_logical_fingerprint: 'd'.repeat(64), risk_modes: [{ risk_mode: 'conservative', displayed_instrument_ids: [] }, { risk_mode: 'balanced', displayed_instrument_ids: records.map((item) => item.instrument_id) }, { risk_mode: 'aggressive', displayed_instrument_ids: [] }] },
  };
}

describe('Sector Rotation decision chain', () => {
  beforeEach(() => {
    window.localStorage.clear(); window.history.replaceState({}, '', '/dashboard/?view=sector&lang=en');
    getSectorRotation.mockResolvedValue(rotation()); getMarketRegimePreview.mockResolvedValue(marketRegimeFixture());
    getOpportunityCandidates.mockResolvedValue(candidates());
  });
  afterEach(() => { cleanup(); vi.clearAllMocks(); });

  it('loads a same-session concise chain and changes windows without refetching summaries', async () => {
    render(<I18nProvider><SectorRotationPage universeId={PRIMARY_UNIVERSE} /></I18nProvider>);
    expect(await screen.findByRole('heading', { name: 'Sector Rotation' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'From market state to the next review' })).toBeInTheDocument();
    expect(await screen.findByText('Top 5 ETF price proxies · 20D')).toBeInTheDocument();
    expect(screen.getByText('NAME0')).toBeInTheDocument();
    expect(screen.getByText(/Evidence hand-off/)).toBeInTheDocument();
    expect(getMarketRegimePreview).toHaveBeenCalledWith(PRIMARY_UNIVERSE, expect.any(AbortSignal));
    fireEvent.click(screen.getByRole('button', { name: '5D' }));
    expect(await screen.findByText('Top 5 ETF price proxies · 5D')).toBeInTheDocument();
    expect(getMarketRegimePreview).toHaveBeenCalledTimes(1);
    expect(getOpportunityCandidates).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Open complete Candidate review →' }));
    await waitFor(() => expect(new URLSearchParams(window.location.search).get('view')).toBe('candidates'));
    expect(new URLSearchParams(window.location.search).get('candidateRisk')).toBe('balanced');
  });

  it('fails only the joined view closed when source sessions differ', async () => {
    getOpportunityCandidates.mockResolvedValue(candidates('2026-08-20'));
    render(<I18nProvider><SectorRotationPage universeId={PRIMARY_UNIVERSE} /></I18nProvider>);
    expect(await screen.findByRole('heading', { name: 'Sector Rotation' })).toBeInTheDocument();
    expect(await screen.findByText('The cross-workspace decision chain is unavailable')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Leadership and acceleration map' })).toBeInTheDocument();
  });
});
