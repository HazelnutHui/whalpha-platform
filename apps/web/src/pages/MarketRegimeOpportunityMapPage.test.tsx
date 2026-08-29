import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MarketRegimeOpportunityMapPage } from './MarketRegimeOpportunityMapPage';
import { marketRegimeFixture, PRIMARY_UNIVERSE, SECONDARY_UNIVERSE } from '../test/marketRegimeFixture';
import { I18nProvider } from '../i18n/I18nProvider';
import { LanguageSelector } from '../i18n/LanguageSelector';

const getPreview = vi.fn((universe?: string, _signal?: AbortSignal) => Promise.resolve(marketRegimeFixture(universe === SECONDARY_UNIVERSE ? SECONDARY_UNIVERSE : PRIMARY_UNIVERSE)));
vi.mock('../api/marketRegime', async (original) => ({ ...(await original<typeof import('../api/marketRegime')>()), getMarketRegimePreview: (universe?: string, signal?: AbortSignal) => getPreview(universe, signal) }));

describe('Market Regime Opportunity Map desktop preview', () => {
  beforeEach(() => { getPreview.mockClear(); window.history.replaceState({}, '', '/?view=regime'); });

  it('makes the confirmed state primary while preserving exact audit values and all pairs', async () => {
    render(<MarketRegimeOpportunityMapPage />);
    expect(await screen.findByText('Mixed but constructive')).toBeInTheDocument();
    expect(document.querySelector('[data-exact-value="63.9102"]')).toHaveTextContent('63.9 / 100');
    expect(screen.getByText('Candidate matches the confirmed state.')).toBeInTheDocument();
    expect(screen.getByText('What the market supports now')).toBeInTheDocument();
    expect(screen.getByText('Broad risk-on not confirmed')).toBeInTheDocument();
    expect(screen.getByText('+1.9')).toBeInTheDocument();
    expect(screen.getAllByText('Support')).toHaveLength(3);
    expect(screen.getByText('Drag')).toBeInTheDocument();
    expect(screen.getAllByText('Neutral').length).toBeGreaterThan(0);
    expect(screen.getByText('63.9102 = 63.9102')).toBeInTheDocument();
    expect(screen.getAllByRole('button').filter((item) => /L\d+ \/ R\d+|IGV \/ QQQ/.test(item.textContent ?? '')).length).toBe(22);
    fireEvent.click(screen.getByText('All 16 preregistered pairs'));
    expect(screen.getAllByRole('button').filter((item) => /L\d+ \/ R\d+|IGV \/ QQQ/.test(item.textContent ?? '')).length).toBe(22);
    expect(screen.getByText(/Only 26 completed XNYS sessions/)).toBeInTheDocument();
    expect(screen.getByText('Research context, not a trade recommendation.')).toBeInTheDocument();
  });

  it('switches windows, filters, preserves relative spread and opens detail', async () => {
    render(<MarketRegimeOpportunityMapPage />); await screen.findByText('Mixed but constructive');
    fireEvent.click(screen.getByText('All 16 preregistered pairs'));
    fireEvent.click(screen.getByRole('button', { name: '20 sessions' }));
    expect(window.location.search).toContain('window=20');
    fireEvent.click(screen.getByLabelText('Only non-neutral'));
    expect(screen.getByText(/Showing 12 of 16/)).toBeInTheDocument();
    const igv = screen.getAllByRole('button').find((item) => item.textContent?.includes('IGV / QQQ')) as HTMLElement;
    expect(within(igv).getByText('+2.00%')).toBeInTheDocument();
    fireEvent.click(igv);
    expect(screen.getByRole('heading', { name: 'IGV / QQQ' })).toBeInTheDocument();
    expect(screen.getByText('Both ETFs declined over 20 sessions.')).toBeInTheDocument();
    expect(screen.getAllByText(/IGV held up 2.00 percentage points better than QQQ/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/IGV leadership is strengthening/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/State held for 3 sessions/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Recent relationship path')).toBeInTheDocument();
    expect(screen.getByText('10 shown · 21 retained sessions')).toBeInTheDocument();
    expect(screen.getAllByText('State change').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('20-session relative return')).toBeInTheDocument();
    expect(screen.getAllByText('Synchronous Weakening').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Close IGV / QQQ details' })).toBeInTheDocument();
    expect(screen.getByText(/needs at least 60 sessions/)).toBeInTheDocument();
    expect(screen.getByText('Price relationship, not fund flow.')).toBeInTheDocument();
  });

  it('isolates Universe state while keeping ETF metrics and supports history navigation', async () => {
    render(<MarketRegimeOpportunityMapPage />); await screen.findByText('Mixed but constructive');
    fireEvent.change(screen.getByLabelText('Universe'), { target: { value: SECONDARY_UNIVERSE } });
    await waitFor(() => expect(document.querySelector('[data-exact-value="64.8167"]')).toHaveTextContent('64.8 / 100'));
    expect(window.location.search).toContain(encodeURIComponent(SECONDARY_UNIVERSE));
    expect(getPreview).toHaveBeenLastCalledWith(SECONDARY_UNIVERSE, expect.anything());
    act(() => { window.history.pushState({}, '', `/?view=regime&universe=${PRIMARY_UNIVERSE}`); window.dispatchEvent(new PopStateEvent('popstate')); });
    await waitFor(() => expect(document.querySelector('[data-exact-value="63.9102"]')).toHaveTextContent('63.9 / 100'));
  });

  it('fails closed when the API is unavailable', async () => {
    getPreview.mockRejectedValueOnce(new Error('Request failed with status 503'));
    render(<MarketRegimeOpportunityMapPage />);
    expect(await screen.findByText('Market Regime preview unavailable')).toBeInTheDocument();
    expect(screen.getByText(/No partial or mixed-version analytics/)).toBeInTheDocument();
  });

  it('shows the explicit stale-review banner without changing analytics', async () => {
    const payload = marketRegimeFixture();
    payload.data_status = 'stale_review';
    payload.review_deployment = {
      contract_version: 'production-review-deployment/1.0', review_mode: true,
      normal_freshness: false, data_status: 'stale_review',
      approved_as_of_session: '2026-08-24', expected_latest_session: '2026-08-25',
      expected_lag_sessions: 1,
      explicit_user_acknowledgement: 'I_ACKNOWLEDGE_2026_08_24_STALE_REVIEW_LAG_1',
    };
    getPreview.mockResolvedValueOnce(payload);
    render(<MarketRegimeOpportunityMapPage />);
    expect(await screen.findByText(
      'Review deployment · Data as of 2026-08-24 · 1 completed session behind',
    )).toBeInTheDocument();
    expect(document.querySelector('[data-exact-value="63.9102"]')).toBeInTheDocument();
  });

  it('shows zero remaining distance after a threshold is crossed', async () => {
    const payload = marketRegimeFixture();
    payload.regime.current_state.confirmed_state = 'risk_on';
    payload.regime.current_state.instantaneous_candidate_state = 'risk_on';
    payload.regime.current_state.composite = '72.0000';
    payload.regime.current_state.conflicting_dimension_ids = [];
    payload.regime.current_state.threshold_distances = [
      { threshold_id: 'balanced_to_risk_on', threshold: '70.0000', signed_distance: '2.0000', boundary_operator: '>=' },
      { threshold_id: 'balanced_to_defensive', threshold: '45.0000', signed_distance: '27.0000', boundary_operator: '<' },
    ];
    getPreview.mockResolvedValueOnce(payload);
    render(<MarketRegimeOpportunityMapPage />);
    const brief = (await screen.findByRole('heading', { name: 'What the market supports now' })).closest('section') as HTMLElement;
    expect(within(brief).getByText('Broad risk-on supported')).toBeInTheDocument();
    expect(within(brief).getByText('0.0')).toBeInTheDocument();
    expect(within(brief).getByText('27.0')).toBeInTheDocument();
  });

  it('changes only presentation language while preserving the analytics payload and exact values', async () => {
    window.localStorage.clear();
    window.history.replaceState({}, '', '/?view=regime&universe=provider_classified_common_shares_v1&lang=en');
    render(<I18nProvider><LanguageSelector /><MarketRegimeOpportunityMapPage /></I18nProvider>);
    expect(await screen.findByText('Mixed but constructive')).toBeInTheDocument();
    expect(document.querySelector('[data-exact-value="63.9102"]')).toHaveTextContent('63.9 / 100');
    expect(screen.getAllByRole('button').filter((item) => /L\d+ \/ R\d+|IGV \/ QQQ/.test(item.textContent ?? '')).length).toBe(22);
    expect(getPreview).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: '中文' }));
    expect(await screen.findByText('分化但总体偏积极')).toBeInTheDocument();
    expect(document.querySelector('[data-exact-value="63.9102"]')).toHaveTextContent('63.9 / 100');
    expect(screen.getByText('均衡')).toBeInTheDocument();
    expect(screen.getByText('全部16组预登记关系')).toBeInTheDocument();
    fireEvent.click(screen.getByText('全部16组预登记关系'));
    expect(screen.getAllByRole('button').filter((item) => /L\d+ \/ R\d+|IGV \/ QQQ/.test(item.textContent ?? '')).length).toBe(22);
    expect(getPreview).toHaveBeenCalledTimes(1);
    expect(new URLSearchParams(window.location.search).get('universe')).toBe(PRIMARY_UNIVERSE);
    expect(new URLSearchParams(window.location.search).get('lang')).toBe('zh');
  });
});
