import { lazy, Suspense, useEffect, useState } from 'react';

import { recordGuestWorkspaceEntry } from './api/visitorCount';
import { LanguageSelector } from './i18n/LanguageSelector';
import { useI18n } from './i18n/I18nProvider';
import type { MessageKey } from './i18n/catalog';
import { universeName } from './i18n/domain';

const loadMarketDashboard = () => import('./pages/MarketDashboardPage');
const loadMarketRegime = () => import('./pages/MarketRegimeOpportunityMapPage');
const loadOpportunityCandidates = () => import('./pages/OpportunityCandidatesPage');
const loadSectorRotation = () => import('./pages/SectorRotationPage');
const loadQuantResearchLab = () => import('./pages/QuantResearchLabPage');

const MarketDashboardPage = lazy(() => loadMarketDashboard().then((module) => ({ default: module.MarketDashboardPage })));
const MarketRegimeOpportunityMapPage = lazy(() => loadMarketRegime().then((module) => ({ default: module.MarketRegimeOpportunityMapPage })));
const OpportunityCandidatesPage = lazy(() => loadOpportunityCandidates().then((module) => ({ default: module.OpportunityCandidatesPage })));
const SectorRotationPage = lazy(() => loadSectorRotation().then((module) => ({ default: module.SectorRotationPage })));
const QuantResearchLabPage = lazy(() => loadQuantResearchLab().then((module) => ({ default: module.QuantResearchLabPage })));

type Workspace = 'market' | 'regime' | 'sector' | 'candidates' | 'research';

const WORKSPACE_PRELOADERS: Record<Workspace, () => Promise<unknown>> = {
  market: loadMarketDashboard,
  regime: loadMarketRegime,
  sector: loadSectorRotation,
  candidates: loadOpportunityCandidates,
  research: loadQuantResearchLab,
};

const WORKSPACE_LABELS: Record<Workspace, MessageKey> = {
  market: 'app.marketDashboard',
  regime: 'app.regimeMap',
  sector: 'app.sectorRotation',
  candidates: 'app.stockCandidates',
  research: 'app.quantResearch',
};

const PRIMARY_UNIVERSE = 'provider_classified_common_shares_v1';
const SECONDARY_UNIVERSE = 'provider_classified_common_shares_plus_adrs_v1';
const UNIVERSES = [PRIMARY_UNIVERSE, SECONDARY_UNIVERSE] as const;
type UniverseId = (typeof UNIVERSES)[number];

function requestedWorkspace(): Workspace {
  const value = new URLSearchParams(window.location.search).get('view');
  return value === 'market' || value === 'regime' || value === 'sector' || value === 'candidates' || value === 'research' ? value : 'research';
}

function isUniverse(value: string | null): value is UniverseId {
  return value !== null && UNIVERSES.includes(value as UniverseId);
}

function requestedUniverse(): UniverseId {
  const value = new URLSearchParams(window.location.search).get('universe');
  return isUniverse(value) ? value : PRIMARY_UNIVERSE;
}

function writeQuery(changes: Record<string, string | null>, replace = false): void {
  const url = new URL(window.location.href);
  Object.entries(changes).forEach(([key, value]) => {
    if (value === null) url.searchParams.delete(key);
    else url.searchParams.set(key, value);
  });
  window.history[replace ? 'replaceState' : 'pushState'](window.history.state, '', url);
}

async function logout(locale: string): Promise<void> {
  await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
  window.location.assign(`/?lang=${locale}`);
}

export default function App(): JSX.Element {
  const { locale, t } = useI18n();
  const [workspace, setWorkspace] = useState<Workspace>(requestedWorkspace);
  const [universe, setUniverse] = useState(requestedUniverse);
  const [guestVisitorCount, setGuestVisitorCount] = useState<number | null>(null);
  const snapshotMode = import.meta.env.VITE_MARKET_DATA_MODE === 'snapshot';

  useEffect(() => {
    if (!snapshotMode) return;
    const controller = new AbortController();
    void recordGuestWorkspaceEntry(controller.signal)
      .then((result) => setGuestVisitorCount(result.count))
      .catch(() => setGuestVisitorCount(null));
    return () => controller.abort();
  }, [snapshotMode]);

  useEffect(() => {
    const rawUniverse = new URLSearchParams(window.location.search).get('universe');
    if (rawUniverse !== universe) writeQuery({ universe }, true);
  }, [universe]);

  useEffect(() => {
    const handler = () => {
      setWorkspace(requestedWorkspace());
      setUniverse(requestedUniverse());
    };
    window.addEventListener('popstate', handler);
    return () => window.removeEventListener('popstate', handler);
  }, []);

  const navigate = (next: Workspace) => {
    writeQuery({ view: next });
    setWorkspace(next);
  };
  const preloadWorkspace = (next: Workspace) => {
    void WORKSPACE_PRELOADERS[next]();
  };
  const selectUniverse = (next: string) => {
    if (!isUniverse(next)) return;
    writeQuery({ universe: next });
    setUniverse(next);
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  return (
    <div className="workspace-layout">
      <aside className="workspace-sidebar">
        <div className="workspace-brand">
          <img src="/favicon.png" alt="" width="48" height="48" />
          <div>
            <strong>WH Alpha</strong>
            <span>{t('app.productLabel')}</span>
          </div>
        </div>
        <nav className="workspace-navigation" aria-label={t('app.navAria')}>
          <div className="workspace-nav-group workspace-nav-group--research" role="group" aria-labelledby="research-navigation-label">
            <div className="workspace-nav-heading"><span id="research-navigation-label">{t('app.researchGroup')}</span><b>{t('app.coreBadge')}</b></div>
            <button type="button" className={`workspace-nav-primary ${workspace === 'research' ? 'active' : ''}`} aria-current={workspace === 'research' ? 'page' : undefined} onPointerEnter={() => preloadWorkspace('research')} onFocus={() => preloadWorkspace('research')} onClick={() => navigate('research')}>
              <span className="workspace-nav-mark workspace-nav-mark--core" aria-hidden="true">LAB</span>
              <strong>{t('app.quantResearch')}</strong>
              <small>{t('app.quantResearchDescription')}</small>
            </button>
            <button type="button" className={`workspace-nav-secondary ${workspace === 'candidates' ? 'active' : ''}`} aria-current={workspace === 'candidates' ? 'page' : undefined} onPointerEnter={() => preloadWorkspace('candidates')} onFocus={() => preloadWorkspace('candidates')} onClick={() => navigate('candidates')}>
              <span className="workspace-nav-mark" aria-hidden="true">MODEL</span>
              <strong>{t('app.stockCandidates')}</strong>
              <small>{t('app.stockCandidatesDescription')}</small>
            </button>
          </div>

          <div className="workspace-nav-divider" aria-hidden="true"><span>{t('app.freeToolsGroup')}</span><b>{t('app.freeBadge')}</b></div>

          <div className="workspace-nav-group workspace-nav-group--tools" role="group" aria-label={t('app.freeToolsGroup')}>
            <button type="button" className={workspace === 'regime' ? 'active' : ''} aria-current={workspace === 'regime' ? 'page' : undefined} onPointerEnter={() => preloadWorkspace('regime')} onFocus={() => preloadWorkspace('regime')} onClick={() => navigate('regime')}>
              <span className="workspace-tool-mark" aria-hidden="true"><i /></span>
              <strong>{t('app.regimeMap')}</strong>
              <small>{t('app.regimeMapDescription')}</small>
            </button>
            <button type="button" className={workspace === 'sector' ? 'active' : ''} aria-current={workspace === 'sector' ? 'page' : undefined} onPointerEnter={() => preloadWorkspace('sector')} onFocus={() => preloadWorkspace('sector')} onClick={() => navigate('sector')}>
              <span className="workspace-tool-mark" aria-hidden="true"><i /></span>
              <strong>{t('app.sectorRotation')}</strong>
              <small>{t('app.sectorRotationDescription')}</small>
            </button>
            <button type="button" className={workspace === 'market' ? 'active' : ''} aria-current={workspace === 'market' ? 'page' : undefined} onPointerEnter={() => preloadWorkspace('market')} onFocus={() => preloadWorkspace('market')} onClick={() => navigate('market')}>
              <span className="workspace-tool-mark" aria-hidden="true"><i /></span>
              <strong>{t('app.marketDashboard')}</strong>
              <small>{t('app.marketDashboardDescription')}</small>
            </button>
          </div>
        </nav>
        <p className="workspace-boundary">{t('app.researchBoundary')}</p>
      </aside>
      <div className="workspace-stage">
        <header className="workspace-utility" aria-label={t('app.utilityAria')}>
          <div className="workspace-context" aria-live="polite">
            <span>{t(workspace === 'research' || workspace === 'candidates' ? 'app.researchGroup' : 'app.freeToolsGroup')}</span>
            <strong>{t(WORKSPACE_LABELS[workspace])}</strong>
          </div>
          <label className="workspace-universe">
            <span>{t('common.universe')}</span>
            <select aria-label={t('app.universeAria')} value={universe} onChange={(event) => selectUniverse(event.target.value)}>
              {UNIVERSES.map((universeId) => <option key={universeId} value={universeId}>{universeName(t, universeId)}</option>)}
            </select>
          </label>
          <LanguageSelector />
          <div className="workspace-account">
            <span>{t('app.account')}</span>
            <strong>{t('app.privateSession')}</strong>
            {snapshotMode ? <button type="button" onClick={() => void logout(locale)}>{t('dashboard.logout')}</button> : null}
          </div>
        </header>
        <div className="workspace-view" data-workspace={workspace}>
          <Suspense fallback={<div className="workspace-route-loading" role="status">{t('common.loading')}</div>}>
            {workspace === 'regime' ? <MarketRegimeOpportunityMapPage withinWorkspaceShell /> : workspace === 'sector' ? <SectorRotationPage universeId={universe} /> : workspace === 'market' ? <MarketDashboardPage withinWorkspaceShell /> : workspace === 'candidates' ? <OpportunityCandidatesPage /> : <QuantResearchLabPage />}
          </Suspense>
        </div>
        {guestVisitorCount !== null ? <footer className="workspace-boundary" aria-live="polite"><span>{t('app.cumulativeGuestEntries')} · </span><strong>{new Intl.NumberFormat(locale === 'zh' ? 'zh-CN' : locale === 'es' ? 'es-ES' : 'en-US').format(guestVisitorCount)}</strong></footer> : null}
      </div>
    </div>
  );
}
