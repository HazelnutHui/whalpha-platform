import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
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

  it('presents persistent first-level workspaces and shared utility controls', () => {
    render(<I18nProvider><App /></I18nProvider>);
    expect(screen.getByRole('navigation', { name: 'Primary workspaces' })).toBeInTheDocument();
    const workspaceButtons = screen.getByRole('navigation', { name: 'Primary workspaces' }).querySelectorAll('button');
    expect(workspaceButtons[0]).toHaveTextContent('Regime & Opportunities');
    expect(screen.getByRole('button', { name: /Regime & Opportunities/ })).toHaveAttribute('aria-current', 'page');
    expect(workspaceButtons[1]).toHaveTextContent('Sector Rotation');
    expect(workspaceButtons[3]).toHaveTextContent('Stock Candidates');
    expect(workspaceButtons[4]).toHaveTextContent('Quant Research Lab');
    expect(screen.getByTestId('regime-workspace')).toHaveTextContent('regime:true');
    expect(screen.getByLabelText('Active Universe')).toHaveValue('provider_classified_common_shares_v1');
    expect(screen.getByText('Protected Session')).toBeInTheDocument();
    expect(document.querySelector('.workspace-brand img')).toHaveAttribute('src', '/favicon.png');
  });

  it('opens the research workspace through the same shell without an account-role branch', () => {
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.click(screen.getByRole('button', { name: /Quant Research Lab/ }));
    expect(screen.getByTestId('research-workspace')).toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get('view')).toBe('research');
    expect(screen.getByLabelText('Active Universe')).toHaveValue('provider_classified_common_shares_v1');
  });

  it('preserves Universe across workspace navigation and browser history', () => {
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.change(screen.getByLabelText('Active Universe'), { target: { value: 'provider_classified_common_shares_plus_adrs_v1' } });
    expect(new URLSearchParams(window.location.search).get('universe')).toBe('provider_classified_common_shares_plus_adrs_v1');
    fireEvent.click(screen.getByRole('button', { name: /Market Structure & Activity/ }));
    expect(screen.getByTestId('market-workspace')).toHaveTextContent('market:true');
    expect(new URLSearchParams(window.location.search).get('view')).toBe('market');
    expect(new URLSearchParams(window.location.search).get('universe')).toBe('provider_classified_common_shares_plus_adrs_v1');

    act(() => {
      window.history.pushState({}, '', '/dashboard/?view=regime&lang=en&universe=provider_classified_common_shares_v1');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    expect(screen.getByTestId('regime-workspace')).toBeInTheDocument();
    expect(screen.getByLabelText('Active Universe')).toHaveValue('provider_classified_common_shares_v1');
  });

  it('opens Sector Rotation as the second market-wide workspace', () => {
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.click(screen.getByRole('button', { name: /Sector Rotation/ }));
    expect(screen.getByTestId('sector-workspace')).toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get('view')).toBe('sector');
  });

  it('uses the natural Chinese workspace name without changing query state', () => {
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.click(screen.getByRole('button', { name: '中文' }));
    expect(screen.getByRole('button', { name: /市场风向与机会/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /量化研究实验室/ })).toBeInTheDocument();
    expect(screen.getByLabelText('当前股票池')).toHaveValue('provider_classified_common_shares_v1');
    expect(new URLSearchParams(window.location.search).get('lang')).toBe('zh');
  });
});
