import { useEffect, useState } from 'react';

import { MarketDashboardPage } from './pages/MarketDashboardPage';
import { MarketRegimeOpportunityMapPage } from './pages/MarketRegimeOpportunityMapPage';
import { LanguageSelector } from './i18n/LanguageSelector';
import { useI18n } from './i18n/I18nProvider';

export default function App(): JSX.Element {
  const { t } = useI18n();
  const [view, setView] = useState(() => new URLSearchParams(window.location.search).get('view') === 'regime' ? 'regime' : 'market');
  useEffect(() => { const handler = () => setView(new URLSearchParams(window.location.search).get('view') === 'regime' ? 'regime' : 'market'); window.addEventListener('popstate', handler); return () => window.removeEventListener('popstate', handler); }, []);
  const navigate = (next: 'market' | 'regime') => { const url = new URL(window.location.href); if (next === 'regime') url.searchParams.set('view', 'regime'); else url.searchParams.delete('view'); window.history.pushState({}, '', url); setView(next); };
  return <><nav className="product-nav" aria-label={t('app.navAria')}><div className="product-view-tabs"><button type="button" className={view === 'market' ? 'active' : ''} onClick={() => navigate('market')}>{t('app.marketDashboard')}</button><button type="button" className={view === 'regime' ? 'active' : ''} onClick={() => navigate('regime')}>{t('app.regimeMap')}</button></div><LanguageSelector /></nav>{view === 'regime' ? <MarketRegimeOpportunityMapPage /> : <MarketDashboardPage />}</>;
}
