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
    expect(screen.getByTestId('regime-workspace')).toHaveTextContent('regime:true');
    expect(screen.getByLabelText('Active Universe')).toHaveValue('provider_classified_common_shares_v1');
    expect(screen.getByText('Private Session')).toBeInTheDocument();
  });

  it('preserves Universe across workspace navigation and browser history', () => {
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.change(screen.getByLabelText('Active Universe'), { target: { value: 'provider_classified_common_shares_plus_adrs_v1' } });
    expect(new URLSearchParams(window.location.search).get('universe')).toBe('provider_classified_common_shares_plus_adrs_v1');
    fireEvent.click(screen.getByRole('button', { name: /Market Dashboard/ }));
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

  it('uses the natural Chinese workspace name without changing query state', () => {
    render(<I18nProvider><App /></I18nProvider>);
    fireEvent.click(screen.getByRole('button', { name: '中文' }));
    expect(screen.getByRole('button', { name: /市场风向与机会/ })).toBeInTheDocument();
    expect(screen.getByLabelText('当前股票池')).toHaveValue('provider_classified_common_shares_v1');
    expect(new URLSearchParams(window.location.search).get('lang')).toBe('zh');
  });
});
