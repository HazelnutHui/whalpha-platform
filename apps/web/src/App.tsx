import { useEffect, useState } from 'react';

import { MarketDashboardPage } from './pages/MarketDashboardPage';
import { MarketRegimeOpportunityMapPage } from './pages/MarketRegimeOpportunityMapPage';
import { OpportunityCandidatesPage } from './pages/OpportunityCandidatesPage';
import { SectorRotationPage } from './pages/SectorRotationPage';
import { QuantResearchLabPage } from './pages/QuantResearchLabPage';
import { LanguageSelector } from './i18n/LanguageSelector';
import { useI18n } from './i18n/I18nProvider';
import { universeName } from './i18n/domain';

type Workspace = 'market' | 'regime' | 'sector' | 'candidates' | 'research';

const PRIMARY_UNIVERSE = 'provider_classified_common_shares_v1';
const SECONDARY_UNIVERSE = 'provider_classified_common_shares_plus_adrs_v1';
const UNIVERSES = [PRIMARY_UNIVERSE, SECONDARY_UNIVERSE] as const;
type UniverseId = (typeof UNIVERSES)[number];

function requestedWorkspace(): Workspace {
  const value = new URLSearchParams(window.location.search).get('view');
  return value === 'market' || value === 'sector' || value === 'candidates' || value === 'research' ? value : 'regime';
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
  const snapshotMode = import.meta.env.VITE_MARKET_DATA_MODE === 'snapshot';

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
          <button type="button" className={workspace === 'regime' ? 'active' : ''} aria-current={workspace === 'regime' ? 'page' : undefined} onClick={() => navigate('regime')}>
            <span className="workspace-index">01</span>
            <strong>{t('app.regimeMap')}</strong>
            <small>{t('app.regimeMapDescription')}</small>
          </button>
          <button type="button" className={workspace === 'sector' ? 'active' : ''} aria-current={workspace === 'sector' ? 'page' : undefined} onClick={() => navigate('sector')}>
            <span className="workspace-index">02</span>
            <strong>{t('app.sectorRotation')}</strong>
            <small>{t('app.sectorRotationDescription')}</small>
          </button>
          <button type="button" className={workspace === 'market' ? 'active' : ''} aria-current={workspace === 'market' ? 'page' : undefined} onClick={() => navigate('market')}>
            <span className="workspace-index">03</span>
            <strong>{t('app.marketDashboard')}</strong>
            <small>{t('app.marketDashboardDescription')}</small>
          </button>
          <button type="button" className={workspace === 'candidates' ? 'active' : ''} aria-current={workspace === 'candidates' ? 'page' : undefined} onClick={() => navigate('candidates')}>
            <span className="workspace-index">04</span>
            <strong>{t('app.stockCandidates')}</strong>
            <small>{t('app.stockCandidatesDescription')}</small>
          </button>
          <button type="button" className={workspace === 'research' ? 'active' : ''} aria-current={workspace === 'research' ? 'page' : undefined} onClick={() => navigate('research')}>
            <span className="workspace-index">05</span>
            <strong>{t('app.quantResearch')}</strong>
            <small>{t('app.quantResearchDescription')}</small>
          </button>
        </nav>
        <p className="workspace-boundary">{t('app.researchBoundary')}</p>
      </aside>
      <div className="workspace-stage">
        <header className="workspace-utility" aria-label={t('app.utilityAria')}>
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
        {workspace === 'regime' ? <MarketRegimeOpportunityMapPage withinWorkspaceShell /> : workspace === 'sector' ? <SectorRotationPage universeId={universe} /> : workspace === 'market' ? <MarketDashboardPage withinWorkspaceShell /> : workspace === 'candidates' ? <OpportunityCandidatesPage /> : <QuantResearchLabPage />}
      </div>
    </div>
  );
}
