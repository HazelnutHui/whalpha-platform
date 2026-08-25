import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MarketRegimeOpportunityMapPage } from './MarketRegimeOpportunityMapPage';
import { marketRegimeFixture, PRIMARY_UNIVERSE, SECONDARY_UNIVERSE } from '../test/marketRegimeFixture';

const getPreview = vi.fn((universe?: string, _signal?: AbortSignal) => Promise.resolve(marketRegimeFixture(universe === SECONDARY_UNIVERSE ? SECONDARY_UNIVERSE : PRIMARY_UNIVERSE)));
vi.mock('../api/marketRegime', async (original) => ({ ...(await original<typeof import('../api/marketRegime')>()), getMarketRegimePreview: (universe?: string, signal?: AbortSignal) => getPreview(universe, signal) }));

describe('Market Regime Opportunity Map desktop preview', () => {
  beforeEach(() => { getPreview.mockClear(); window.history.replaceState({}, '', '/?view=regime'); });

  it('makes the confirmed state primary while preserving exact audit values and all pairs', async () => {
    render(<MarketRegimeOpportunityMapPage />);
    expect(await screen.findByText('Mixed but constructive')).toBeInTheDocument();
    expect(document.querySelector('[data-exact-value="63.9102"]')).toHaveTextContent('63.9 / 100');
    expect(screen.getByText('Candidate matches the confirmed state.')).toBeInTheDocument();
    expect(screen.getAllByText('Support')).toHaveLength(3);
    expect(screen.getByText('Drag')).toBeInTheDocument();
    expect(screen.getAllByText('Neutral').length).toBeGreaterThan(0);
    expect(screen.getByText('63.9102 = 63.9102')).toBeInTheDocument();
    expect(screen.getAllByRole('button').filter((item) => /L\d+ \/ R\d+|IGV \/ QQQ/.test(item.textContent ?? '')).length).toBe(20);
    expect(screen.getByText(/Only 26 completed XNYS sessions/)).toBeInTheDocument();
    expect(screen.getByText('Research context, not a trade recommendation.')).toBeInTheDocument();
  });

  it('switches windows, filters, preserves relative spread and opens detail', async () => {
    render(<MarketRegimeOpportunityMapPage />); await screen.findByText('Mixed but constructive');
    fireEvent.click(screen.getByRole('button', { name: '20 sessions' }));
    expect(window.location.search).toContain('window=20');
    fireEvent.click(screen.getByLabelText('Only non-neutral'));
    expect(screen.getByText(/Showing 12 of 16/)).toBeInTheDocument();
    const igv = screen.getAllByRole('button').find((item) => item.textContent?.includes('IGV / QQQ')) as HTMLElement;
    expect(within(igv).getByText('+2.00%')).toBeInTheDocument();
    fireEvent.click(igv);
    expect(screen.getByRole('heading', { name: 'IGV / QQQ' })).toBeInTheDocument();
    expect(screen.getByText('Both ETFs declined over 20 sessions.')).toBeInTheDocument();
    expect(screen.getByText(/IGV held up 2.00 percentage points better than QQQ/)).toBeInTheDocument();
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
});
