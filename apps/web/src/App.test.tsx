import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import { I18nProvider } from './i18n/I18nProvider';

vi.mock('./pages/MarketDashboardPage', () => ({
  MarketDashboardPage: ({ withinWorkspaceShell }: { withinWorkspaceShell?: boolean }) => <main data-testid="market-workspace">market:{String(withinWorkspaceShell)}</main>,
}));
vi.mock('./pages/MarketRegimeOpportunityMapPage', () => ({
  MarketRegimeOpportunityMapPage: ({ withinWorkspaceShell }: { withinWorkspaceShell?: boolean }) => <main data-testid="regime-workspace">regime:{String(withinWorkspaceShell)}</main>,
}));
vi.mock('./pages/OpportunityCandidatesPage', () => ({
  OpportunityCandidatesPage: () => <main data-testid="candidate-workspace">candidates</main>,
}));
vi.mock('./pages/SectorRotationPage', () => ({
  SectorRotationPage: () => <main data-testid="sector-workspace">sector</main>,
}));
vi.mock('./pages/QuantResearchLabPage', () => ({
  QuantResearchLabPage: () => <main data-testid="research-workspace">research</main>,
}));
vi.mock('./pages/ChinaAshareResearchPage', () => ({
  ChinaAshareResearchPage: ({ view }: { view: 'research' | 'candidates' }) => <main data-testid="ashare-workspace">ashare:{view}</main>,
}));

describe('primary workspace shell', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, '', '/dashboard/?lang=en&universe=provider_classified_common_shares_v1');
    vi.stubEnv('VITE_MARKET_DATA_MODE', 'api');
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
  });

  it('presents persistent first-level workspaces and shared utility controls', async () => {
    render(<I18nProvider><App /></I18nProvider>);
    expect(screen.getByRole('navigation', { name: 'Research and market tools' })).toBeInTheDocument();
    const workspaceButtons = screen.getByRole('navigation', { name: 'Research and market tools' }).querySelectorAll('button');
    expect(workspaceButtons).toHaveLength(5);
    expect(workspaceButtons[0]).toHaveTextContent('Quant Research Lab');
    expect(workspaceButtons[1]).toHaveTextContent('Model-Driven Equity Selection');
    expect(workspaceButtons[2]).toHaveTextContent('Regime & Opportunities');
    expect(workspaceButtons[3]).toHaveTextContent('Sector Rotation');
    expect(workspaceButtons[4]).toHaveTextContent('Market Structure & Activity');
    expect(screen.getByRole('button', { name: /Quant Research Lab/ })).toHaveAttribute('aria-current', 'page');
    expect(await screen.findByTestId('research-workspace')).toHaveTextContent('research');
    expect(screen.getAllByText('Research system')).toHaveLength(2);
    expect(screen.getByText('Free market tools')).toBeInTheDocument();
    expect(screen.getByLabelText('Research market and Universe')).toHaveValue('provider_classified_common_shares_v1');
    expect(screen.getByRole('option', { name: 'China A-shares · foundation (not admitted)' })).toBeInTheDocument();
    expect(screen.getByText('Protected Session')).toBeInTheDocument();
    expect(document.querySelector('.workspace-brand img')).toHaveAttribute('src', '/favicon.png');
  });

  it('opens the research workspace through the same shell without an account-role branch', async () => {
    window.history.replaceState({}, '', '/dashboard/?view=regime&lang=en&universe=provider_classified_common_shares_v1');
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.click(screen.getByRole('button', { name: /Quant Research Lab/ }));
    expect(await screen.findByTestId('research-workspace')).toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get('view')).toBe('research');
    expect(screen.getByLabelText('Research market and Universe')).toHaveValue('provider_classified_common_shares_v1');
  });

  it('preserves Universe across workspace navigation and browser history', async () => {
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.change(screen.getByLabelText('Research market and Universe'), { target: { value: 'provider_classified_common_shares_plus_adrs_v1' } });
    expect(new URLSearchParams(window.location.search).get('universe')).toBe('provider_classified_common_shares_plus_adrs_v1');
    fireEvent.click(screen.getByRole('button', { name: /Market Structure & Activity/ }));
    expect(await screen.findByTestId('market-workspace')).toHaveTextContent('market:true');
    expect(new URLSearchParams(window.location.search).get('view')).toBe('market');
    expect(new URLSearchParams(window.location.search).get('universe')).toBe('provider_classified_common_shares_plus_adrs_v1');

    act(() => {
      window.history.pushState({}, '', '/dashboard/?view=regime&lang=en&universe=provider_classified_common_shares_v1');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    expect(await screen.findByTestId('regime-workspace')).toBeInTheDocument();
    expect(screen.getByLabelText('Research market and Universe')).toHaveValue('provider_classified_common_shares_v1');
  });

  it('keeps Sector Rotation in the free market-tool group', async () => {
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.click(screen.getByRole('button', { name: /Sector Rotation/ }));
    expect(await screen.findByTestId('sector-workspace')).toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get('view')).toBe('sector');
  });

  it('uses the natural Chinese workspace name without changing query state', () => {
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.click(screen.getByRole('button', { name: '中文' }));
    expect(screen.getByRole('button', { name: /市场风向与机会/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /量化研究实验室/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /模型驱动美股筛选/ })).toBeInTheDocument();
    expect(screen.getByText('免费市场工具')).toBeInTheDocument();
    expect(screen.getByLabelText('研究市场与股票池')).toHaveValue('provider_classified_common_shares_v1');
    expect(new URLSearchParams(window.location.search).get('lang')).toBe('zh');
  });

  it('loads the Spanish workspace language on demand', async () => {
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.click(screen.getByRole('button', { name: 'Español' }));
    await waitFor(() => expect(screen.getByRole('button', { name: /Laboratorio de investigación cuantitativa/ })).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Selección de acciones basada en modelos/ })).toBeInTheDocument();
    expect(screen.getByText('Herramientas de mercado gratuitas')).toBeInTheDocument();
    expect(screen.getByLabelText('Mercado y Universo de investigación')).toHaveValue('provider_classified_common_shares_v1');
    expect(new URLSearchParams(window.location.search).get('lang')).toBe('es');
  });

  it('shows the cumulative guest-entry count in the production workspace footer', async () => {
    vi.stubEnv('VITE_MARKET_DATA_MODE', 'snapshot');
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        metric: 'cumulative_guest_entries',
        count: 1051,
        counted: true,
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<I18nProvider><App /></I18nProvider>);

    expect(await screen.findByText(/Cumulative guest entries/)).toBeInTheDocument();
    expect(screen.getByText('1,051')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/auth/visit', expect.objectContaining({
      method: 'POST',
      credentials: 'same-origin',
    }));
  });

  it('routes the A-share market to its isolated research pages without loading U.S. workspaces', async () => {
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.click(screen.getByRole('button', { name: /Market Structure & Activity/ }));
    expect(await screen.findByTestId('market-workspace')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Research market and Universe'), { target: { value: 'china_a_share_research_foundation_v1' } });
    expect(await screen.findByTestId('ashare-workspace')).toHaveTextContent('ashare:research');
    expect(screen.queryByTestId('market-workspace')).not.toBeInTheDocument();
    expect(screen.queryByTestId('candidate-workspace')).not.toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get('view')).toBe('research');
    expect(new URLSearchParams(window.location.search).get('universe')).toBe('china_a_share_research_foundation_v1');
    expect(screen.getByRole('button', { name: /Regime & Opportunities/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Sector Rotation/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Market Structure & Activity/ })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: /Model-Driven Equity Selection/ }));
    expect(await screen.findByTestId('ashare-workspace')).toHaveTextContent('ashare:candidates');
    expect(screen.queryByTestId('candidate-workspace')).not.toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get('view')).toBe('candidates');
  });

  it('normalizes a direct A-share free-tool URL before any U.S. page is rendered', async () => {
    window.history.replaceState({}, '', '/dashboard/?view=sector&lang=en&universe=china_a_share_research_foundation_v1');
    render(<I18nProvider><App /></I18nProvider>);
    expect(await screen.findByTestId('ashare-workspace')).toHaveTextContent('ashare:research');
    expect(screen.queryByTestId('sector-workspace')).not.toBeInTheDocument();
    await waitFor(() => expect(new URLSearchParams(window.location.search).get('view')).toBe('research'));
  });
});
