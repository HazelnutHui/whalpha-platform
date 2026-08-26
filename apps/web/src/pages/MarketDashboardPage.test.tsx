import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

import { MarketDashboardPage } from './MarketDashboardPage';
import { demoDashboardData } from '../fixtures/marketDemo';
import { I18nProvider } from '../i18n/I18nProvider';
import { LanguageSelector } from '../i18n/LanguageSelector';

const dispose = vi.fn();
const setOption = vi.fn();
const originalLocation = window.location;

vi.mock('echarts/core', () => ({
  use: vi.fn(),
  init: vi.fn(() => ({ setOption, resize: vi.fn(), dispose, on: vi.fn(), off: vi.fn() })),
}));
vi.mock('echarts/charts', () => ({ TreemapChart: {} }));
vi.mock('echarts/components', () => ({ AriaComponent: {}, TooltipComponent: {}, VisualMapComponent: {} }));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

function okResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } });
}

function formalDashboardOverview() {
  const overview = structuredClone(demoDashboardData.overview);
  overview.data_status = 'complete';
  return overview;
}

describe('MarketDashboardPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, '', '/dashboard/');
    vi.stubEnv('VITE_MARKET_DATA_MODE', 'api');
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes('/overview/')) return Promise.resolve(okResponse(formalDashboardOverview()));
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
        overview_file: 'market-overview.json',
        file_sha256: { 'market-summary.json': 'a'.repeat(64), 'movers.json': 'b'.repeat(64), 'liquidity-map.json': 'c'.repeat(64), 'market-overview.json': 'd'.repeat(64) },
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
      if (path.endsWith('/private-data/v1/market-overview.json')) return Promise.resolve(okResponse(formalDashboardOverview()));
      return Promise.resolve(new Response('{}', { status: 404 }));
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    if (window.location !== originalLocation) {
      Object.defineProperty(window, 'location', { value: originalLocation, writable: true });
    }
  });

  it('uses API mode by default and renders summary cards', async () => {
    render(<MarketDashboardPage />);
    expect(screen.getByText(/Loading market overview/)).toBeInTheDocument();
    expect(await screen.findByText('Close-to-close structure')).toBeInTheDocument();
    expect(screen.getByLabelText('Market benchmarks')).toBeInTheDocument();
    expect(screen.getByText('SPY')).toBeInTheDocument();
    expect(screen.getByText('EQW')).toBeInTheDocument();
    expect(screen.getAllByText('+0.64%').length).toBeGreaterThan(0);
    expect(screen.getAllByText('1.40×').length).toBeGreaterThan(0);
    expect(screen.getByText('Advancers / Decliners')).toBeInTheDocument();
    expect(screen.getAllByText('1 session stale').length).toBeGreaterThan(0);
    expect(screen.getByText('Breadth and share-volume participation leaned positive.')).toBeInTheDocument();
    expect(screen.getByText('136 advanced / 91 declined · 56.67% positive')).toBeInTheDocument();
  });

  it('renders fresh calendar status independently from validation status', async () => {
    const fresh = {
      ...formalDashboardOverview(),
      freshness_status: 'fresh',
      expected_latest_completed_session: '2026-08-14',
      actual_latest_completed_session: '2026-08-14',
      session_lag: 0,
    };
    vi.mocked(fetch).mockResolvedValue(okResponse(fresh));
    render(<MarketDashboardPage />);
    await waitFor(() => expect(screen.getAllByText('Fresh').length).toBeGreaterThan(0));
  });

  it('shows the exact review-deployment banner in both languages', async () => {
    const review = {
      ...formalDashboardOverview(),
      data_status: 'stale_review', review_mode: true,
      current_session_date: '2026-08-24', previous_session_date: '2026-08-21',
      actual_latest_completed_session: '2026-08-24', expected_latest_completed_session: '2026-08-25',
      session_lag: 1, freshness_status: 'stale',
      review_contract_version: 'production-review-deployment/1.0',
      review_approved_as_of_session: '2026-08-24',
      review_expected_latest_session: '2026-08-25', review_expected_lag_sessions: 1,
    };
    vi.mocked(fetch).mockResolvedValue(okResponse(review));
    render(<I18nProvider><LanguageSelector /><MarketDashboardPage /></I18nProvider>);
    expect(await screen.findByText(
      'Review deployment · Data as of 2026-08-24 · 1 completed session behind',
    )).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '中文' }));
    expect(screen.getByText('审核预览 · 数据截至2026-08-24 · 落后1个已完成交易日')).toBeInTheDocument();
  });

  it('does not fall back to demo fixtures when API fails', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('failure', { status: 503 }));
    render(<MarketDashboardPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('The requested data could not be loaded (HTTP 503).');
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
      if (path.includes('/overview/')) return Promise.resolve(okResponse(formalDashboardOverview()));
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
        overview_file: 'market-overview.json',
        file_sha256: { 'market-summary.json': 'a'.repeat(64), 'movers.json': 'b'.repeat(64), 'liquidity-map.json': 'c'.repeat(64), 'market-overview.json': 'd'.repeat(64) },
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
      if (path.endsWith('/private-data/v1/market-overview.json')) return Promise.resolve(okResponse(formalDashboardOverview()));
      return Promise.resolve(new Response('{}', { status: 404 }));
    });
    render(<MarketDashboardPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('Close-to-close structure')).toBeInTheDocument();
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
    expect(screen.getByText('Trading Activity Map')).toBeInTheDocument();
    expect(screen.getByLabelText('Top N')).toHaveValue('50');
    expect(screen.getAllByText(/not a market-cap heatmap/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/^Live$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Realtime$/i)).not.toBeInTheDocument();
  });

  it('renders data quality and session metadata', async () => {
    render(<MarketDashboardPage />);
    expect(await screen.findByText('Data Details')).toBeInTheDocument();
    expect(screen.getAllByText('2026-08-13').length).toBeGreaterThan(0);
    expect(screen.getByText('Snapshot Status')).toBeInTheDocument();
    expect(screen.getByText('Universe Funnel')).toBeInTheDocument();
    expect(screen.getByText('Methodology Notes')).toBeInTheDocument();
    expect(screen.getByText('Data Limitations')).toBeInTheDocument();
    expect(screen.getByText('Material Warnings')).toBeInTheDocument();
    expect(screen.getAllByText('Provisional classification').length).toBeGreaterThan(0);
    expect(screen.getByText(/issuer domicile and structure remain provisional/)).toBeInTheDocument();
    expect(screen.queryByText(/No material warnings/)).not.toBeInTheDocument();
    expect(screen.getByText(/EOD market structure; not real-time/)).toBeInTheDocument();
    expect(screen.queryByText(/1,876 warnings/)).not.toBeInTheDocument();
  });

  it('defaults to Common Shares and exposes only the two activated universes', async () => {
    render(<MarketDashboardPage />);
    const selector=await screen.findByLabelText('Dashboard universe');
    expect(selector).toHaveValue('provider_classified_common_shares_v1');
    expect(Array.from((selector as HTMLSelectElement).options).map((item)=>item.textContent)).toEqual(['Common Shares','Common Shares + ADRs']);
    expect(screen.queryByRole('option',{name:/Legacy/})).not.toBeInTheDocument();
  });

  it('preserves the real Activation V2 Primary-first catalog, labels, and URL keys', async () => {
    const v2 = formalDashboardOverview();
    v2.universe_definition_id = 'dashboard-universe-activation-v2';
    v2.universe_version = '2.0';
    v2.default_universe_id = 'provider_classified_common_shares_v1';
    v2.selected_universe_id = 'provider_classified_common_shares_v1';
    v2.universes = [
      {
        ...v2.universes.find((item) => item.definition.universe_id === 'provider_classified_common_shares_v1')!,
        definition: {
          ...v2.universes.find((item) => item.definition.universe_id === 'provider_classified_common_shares_v1')!.definition,
          display_name: 'Common Shares',
          member_count: 1718,
          security_type_composition: { CS: 1718 },
        },
        funnel: [],
      },
      {
        ...v2.universes.find((item) => item.definition.universe_id === 'provider_classified_common_shares_plus_adrs_v1')!,
        definition: {
          ...v2.universes.find((item) => item.definition.universe_id === 'provider_classified_common_shares_plus_adrs_v1')!.definition,
          display_name: 'Common Shares + ADRs',
          member_count: 1831,
          security_type_composition: { CS: 1718, ADRC: 113 },
        },
        funnel: [],
      },
    ];
    vi.mocked(fetch).mockResolvedValue(okResponse(v2));
    window.history.replaceState({}, '', '/dashboard/?universe=provider_classified_common_shares_v1');
    render(<MarketDashboardPage />);
    const selector = await screen.findByLabelText('Dashboard universe');
    expect(Array.from((selector as HTMLSelectElement).options).map((item) => [item.value, item.textContent])).toEqual([
      ['provider_classified_common_shares_v1', 'Common Shares'],
      ['provider_classified_common_shares_plus_adrs_v1', 'Common Shares + ADRs'],
    ]);
    expect(selector).toHaveValue('provider_classified_common_shares_v1');
    expect(screen.queryByRole('option', { name: /Legacy/ })).not.toBeInTheDocument();
  });

  it('switches every view with a stable URL universe value', async () => {
    render(<MarketDashboardPage />);
    const selector=await screen.findByLabelText('Dashboard universe');
    expect(screen.getByLabelText('Common Shares screening Funnel').children).toHaveLength(10);
    fireEvent.change(selector,{target:{value:'provider_classified_common_shares_plus_adrs_v1'}});
    expect(selector).toHaveValue('provider_classified_common_shares_plus_adrs_v1');
    expect(window.location.search).toContain('universe=provider_classified_common_shares_plus_adrs_v1');
    expect(screen.getByText(/Market Pulse · Common Shares \+ ADRs/)).toBeInTheDocument();
    expect(screen.getByText(/Market Breadth · Common Shares \+ ADRs/)).toBeInTheDocument();
    expect(screen.getByLabelText('Common Shares + ADRs screening Funnel').children).toHaveLength(10);
    expect(screen.queryByLabelText('Common Shares screening Funnel')).not.toBeInTheDocument();
  });

  it('normalizes an invalid URL universe to the activated default', async () => {
    window.history.replaceState({},'', '/dashboard/?universe=..%2F..%2Fetc');
    render(<MarketDashboardPage />);
    const selector=await screen.findByLabelText('Dashboard universe');
    expect(selector).toHaveValue('provider_classified_common_shares_v1');
    expect(window.location.search).toContain('universe=provider_classified_common_shares_v1');
  });

  it('explains Universe membership versus same-session comparison coverage', async () => {
    const custom = formalDashboardOverview();
    custom.universes[0].definition.member_count = 1718;
    custom.universes[0].definition.security_type_composition = { CS: 1718 };
    custom.universes[0].audit.final_count = 1718;
    custom.universes[0].funnel = custom.universes[0].funnel.map((stage, index) => ({
      ...stage,
      input_count: index === 0 ? 1758 : 1718,
      excluded_count: index === 0 ? 40 : 0,
      remaining_count: 1718,
    }));
    custom.universes[0].summary.comparable_instrument_count = 1716;
    vi.mocked(fetch).mockResolvedValue(okResponse(custom));
    render(<MarketDashboardPage />);
    expect(await screen.findByText('1,716 comparable of 1,718 Universe members')).toBeInTheDocument();
    expect(screen.getByText('2 members are outside this same-session comparison.')).toBeInTheDocument();
    expect(screen.getByText(/requires valid observations in both completed sessions/)).toBeInTheDocument();
  });

  it('renders sector benchmark relative performance without price columns', async () => {
    const custom = structuredClone(demoDashboardData);
    custom.overview.data_status = 'complete';
    custom.overview.sector_benchmarks[0] = {
      ...custom.overview.sector_benchmarks[0],
      available: true,
      previous_close: '100',
      current_close: '103',
      close_to_close_return: '0.03',
      relative_to_spy_return: '0.02',
    };
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => String(input).includes('/overview/')
      ? Promise.resolve(okResponse(custom.overview))
      : Promise.resolve(new Response('{}', { status: 404 })));
    render(<MarketDashboardPage />);
    expect(await screen.findByText('S&P 500 Select Sector SPDR 1D performance')).toBeInTheDocument();
    expect(screen.getByText('vs SPY +2.00%')).toBeInTheDocument();
  });

  it('supports case-insensitive map search and selectable detail panel', async () => {
    render(<MarketDashboardPage />);
    await screen.findByText('Trading Activity Map');
    fireEvent.change(screen.getByLabelText('Search'), { target: { value: ' testa ' } });
    expect(screen.queryByText(/Ticker TESTA is not/)).not.toBeInTheDocument();
  });


  it('renders snapshot mode with private snapshot badge', async () => {
    vi.unstubAllEnvs();
    vi.stubEnv('VITE_MARKET_DATA_MODE', 'snapshot');
    render(<MarketDashboardPage />);
    expect(await screen.findByText('Close-to-close structure')).toBeInTheDocument();
    expect(screen.queryByText('DEMO DATA')).not.toBeInTheDocument();
    expect(screen.getByText('Data Details')).toBeInTheDocument();
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
    expect(assign).toHaveBeenCalledWith('/?lang=en');
  });

  it('snapshot mode failure does not fall back to demo', async () => {
    vi.unstubAllEnvs();
    vi.stubEnv('VITE_MARKET_DATA_MODE', 'snapshot');
    vi.mocked(fetch).mockResolvedValue(new Response('missing', { status: 404 }));
    render(<MarketDashboardPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('The requested data could not be loaded (HTTP 404).');
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

  it('renders the identical dashboard data in Chinese without issuing new analytics requests', async () => {
    window.history.replaceState({}, '', '/dashboard/?universe=provider_classified_common_shares_v1&lang=en');
    render(<I18nProvider><LanguageSelector /><MarketDashboardPage /></I18nProvider>);
    expect(await screen.findByText('Close-to-close structure')).toBeInTheDocument();
    const requestsBeforeSwitch = vi.mocked(fetch).mock.calls.length;
    expect(screen.getAllByText('+0.64%').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('Dashboard universe')).toHaveValue('provider_classified_common_shares_v1');

    fireEvent.click(screen.getByRole('button', { name: '中文' }));
    expect(screen.getByText('收盘价对比结构')).toBeInTheDocument();
    expect(screen.getByText('交易活跃度集中在哪里')).toBeInTheDocument();
    expect(screen.getAllByText('+0.64%').length).toBeGreaterThan(0);
    const selector = screen.getByLabelText('仪表盘股票池') as HTMLSelectElement;
    expect(selector).toHaveValue('provider_classified_common_shares_v1');
    expect(Array.from(selector.options).map((item) => item.textContent)).toEqual(['普通股', '普通股 + 美国存托凭证']);
    expect(vi.mocked(fetch).mock.calls.length).toBe(requestsBeforeSwitch);
    expect(new URLSearchParams(window.location.search).get('lang')).toBe('zh');
    expect(new URLSearchParams(window.location.search).get('universe')).toBe('provider_classified_common_shares_v1');
  });
});
