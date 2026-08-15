import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

import { MarketDashboardPage } from './MarketDashboardPage';
import { demoDashboardData } from '../fixtures/marketDemo';

const dispose = vi.fn();
const setOption = vi.fn();

vi.mock('echarts/core', () => ({
  use: vi.fn(),
  init: vi.fn(() => ({ setOption, resize: vi.fn(), dispose })),
}));
vi.mock('echarts/charts', () => ({ TreemapChart: {} }));
vi.mock('echarts/components', () => ({ AriaComponent: {}, TooltipComponent: {}, VisualMapComponent: {} }));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

function okResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } });
}

describe('MarketDashboardPage', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_MARKET_DATA_MODE', 'api');
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes('/summary/')) return Promise.resolve(okResponse(demoDashboardData.summary));
      if (path.includes('/movers/')) return Promise.resolve(okResponse(demoDashboardData.movers));
      if (path.includes('/liquidity-map/')) return Promise.resolve(okResponse(demoDashboardData.liquidityMap));
      if (path.endsWith('/private-data/v1/manifest.json')) return Promise.resolve(okResponse({
        snapshot_contract_version: '1',
        release_id: '2026-08-13T120000Z-abcdef0',
        generated_at: '2026-08-15T12:00:00Z',
        current_session_date: '2026-08-13',
        previous_session_date: '2026-08-12',
        data_status: 'complete',
        summary_file: 'market-summary.json',
        movers_file: 'movers.json',
        liquidity_map_file: 'liquidity-map.json',
        file_sha256: { 'market-summary.json': 'a'.repeat(64), 'movers.json': 'b'.repeat(64), 'liquidity-map.json': 'c'.repeat(64) },
        summary_node_count: 1,
        mover_gainer_count: 10,
        mover_loser_count: 10,
        liquidity_node_count: 20,
        warning_count: 4,
        is_real_provider_backed: true,
        access_classification: 'private',
        contains_raw_provider_data: false,
        contains_credentials: false,
      }));
      if (path.endsWith('/private-data/v1/market-summary.json')) return Promise.resolve(okResponse(demoDashboardData.summary));
      if (path.endsWith('/private-data/v1/movers.json')) return Promise.resolve(okResponse(demoDashboardData.movers));
      if (path.endsWith('/private-data/v1/liquidity-map.json')) return Promise.resolve(okResponse(demoDashboardData.liquidityMap));
      return Promise.resolve(new Response('{}', { status: 404 }));
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('uses API mode by default and renders summary cards', async () => {
    render(<MarketDashboardPage />);
    expect(screen.getByText(/Loading market dashboard/)).toBeInTheDocument();
    expect(await screen.findByText('Market Pulse')).toBeInTheDocument();
    expect(screen.getByText('+0.64%')).toBeInTheDocument();
    expect(screen.getAllByText('1.40×').length).toBeGreaterThan(0);
    expect(screen.getByText('Advancers / Decliners')).toBeInTheDocument();
  });

  it('does not fall back to demo fixtures when API fails', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('failure', { status: 503 }));
    render(<MarketDashboardPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Request failed with status 503');
    expect(screen.queryByText('DEMO DATA')).not.toBeInTheDocument();
  });

  it('supports retry after an API error', async () => {
    let shouldFail = true;
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      if (shouldFail) {
        shouldFail = false;
        return Promise.resolve(new Response('failure', { status: 503 }));
      }
      const path = String(input);
      if (path.includes('/summary/')) return Promise.resolve(okResponse(demoDashboardData.summary));
      if (path.includes('/movers/')) return Promise.resolve(okResponse(demoDashboardData.movers));
      if (path.includes('/liquidity-map/')) return Promise.resolve(okResponse(demoDashboardData.liquidityMap));
      if (path.endsWith('/private-data/v1/manifest.json')) return Promise.resolve(okResponse({
        snapshot_contract_version: '1',
        release_id: '2026-08-13T120000Z-abcdef0',
        generated_at: '2026-08-15T12:00:00Z',
        current_session_date: '2026-08-13',
        previous_session_date: '2026-08-12',
        data_status: 'complete',
        summary_file: 'market-summary.json',
        movers_file: 'movers.json',
        liquidity_map_file: 'liquidity-map.json',
        file_sha256: { 'market-summary.json': 'a'.repeat(64), 'movers.json': 'b'.repeat(64), 'liquidity-map.json': 'c'.repeat(64) },
        summary_node_count: 1,
        mover_gainer_count: 10,
        mover_loser_count: 10,
        liquidity_node_count: 20,
        warning_count: 4,
        is_real_provider_backed: true,
        access_classification: 'private',
        contains_raw_provider_data: false,
        contains_credentials: false,
      }));
      if (path.endsWith('/private-data/v1/market-summary.json')) return Promise.resolve(okResponse(demoDashboardData.summary));
      if (path.endsWith('/private-data/v1/movers.json')) return Promise.resolve(okResponse(demoDashboardData.movers));
      if (path.endsWith('/private-data/v1/liquidity-map.json')) return Promise.resolve(okResponse(demoDashboardData.liquidityMap));
      return Promise.resolve(new Response('{}', { status: 404 }));
    });
    render(<MarketDashboardPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('Market Pulse')).toBeInTheDocument();
  });

  it('renders demo mode with a permanent synthetic banner', async () => {
    vi.unstubAllEnvs();
    vi.stubEnv('VITE_MARKET_DATA_MODE', 'demo');
    render(<MarketDashboardPage />);
    expect(await screen.findByText('DEMO DATA')).toBeInTheDocument();
    expect(screen.getAllByText(/TEST/).length).toBeGreaterThan(0);
  });

  it('renders breadth labels and counts', async () => {
    render(<MarketDashboardPage />);
    expect(await screen.findByText('Advancers')).toBeInTheDocument();
    expect(screen.getByText('136')).toBeInTheDocument();
    expect(screen.getByText('Decliners')).toBeInTheDocument();
  });

  it('renders movers and liquidity map limitations without false claims', async () => {
    render(<MarketDashboardPage />);
    expect(await screen.findByText('Top Gainers')).toBeInTheDocument();
    expect(screen.getByText('Top Losers')).toBeInTheDocument();
    expect(screen.getByText('Not Market-Cap Weighted')).toBeInTheDocument();
    expect(screen.getByText('Not Sector Grouped')).toBeInTheDocument();
    expect(screen.queryByText(/^Live$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Realtime$/i)).not.toBeInTheDocument();
  });

  it('renders data quality and session metadata', async () => {
    render(<MarketDashboardPage />);
    expect(await screen.findByText('Session metadata')).toBeInTheDocument();
    expect(screen.getAllByText('2026-08-13').length).toBeGreaterThan(0);
    expect(screen.getByText(/EOD market structure; not real-time/)).toBeInTheDocument();
  });


  it('renders snapshot mode with private snapshot badge', async () => {
    vi.unstubAllEnvs();
    vi.stubEnv('VITE_MARKET_DATA_MODE', 'snapshot');
    render(<MarketDashboardPage />);
    expect(await screen.findByText('PRIVATE EOD SNAPSHOT')).toBeInTheDocument();
    expect(screen.queryByText('DEMO DATA')).not.toBeInTheDocument();
    expect(screen.getByText('Release 2026-08-13T120000Z-abcdef0')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Logout' })).toBeInTheDocument();
  });

  it('posts logout and navigates to login in snapshot mode', async () => {
    vi.unstubAllEnvs();
    vi.stubEnv('VITE_MARKET_DATA_MODE', 'snapshot');
    const assign = vi.fn();
    Object.defineProperty(window, 'location', {
      value: { assign },
      writable: true,
    });
    render(<MarketDashboardPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Logout' }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/auth/logout', { method: 'POST', credentials: 'same-origin' }));
    expect(assign).toHaveBeenCalledWith('/');
  });

  it('snapshot mode failure does not fall back to demo', async () => {
    vi.unstubAllEnvs();
    vi.stubEnv('VITE_MARKET_DATA_MODE', 'snapshot');
    vi.mocked(fetch).mockResolvedValue(new Response('missing', { status: 404 }));
    render(<MarketDashboardPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Request failed with status 404');
    expect(screen.queryByText('DEMO DATA')).not.toBeInTheDocument();
  });

  it('cancels requests on unmount', async () => {
    let observedSignal: AbortSignal | undefined;
    vi.mocked(fetch).mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
      observedSignal = init?.signal ?? undefined;
      return new Promise<Response>(() => undefined);
    });
    const { unmount } = render(<MarketDashboardPage />);
    await waitFor(() => expect(observedSignal).toBeDefined());
    unmount();
    expect(observedSignal?.aborted).toBe(true);
  });
});
