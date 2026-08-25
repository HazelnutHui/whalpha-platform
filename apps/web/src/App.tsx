import { useEffect, useState } from 'react';

import { MarketDashboardPage } from './pages/MarketDashboardPage';
import { MarketRegimeOpportunityMapPage } from './pages/MarketRegimeOpportunityMapPage';

export default function App(): JSX.Element {
  const [view, setView] = useState(() => new URLSearchParams(window.location.search).get('view') === 'regime' ? 'regime' : 'market');
  useEffect(() => { const handler = () => setView(new URLSearchParams(window.location.search).get('view') === 'regime' ? 'regime' : 'market'); window.addEventListener('popstate', handler); return () => window.removeEventListener('popstate', handler); }, []);
  const navigate = (next: 'market' | 'regime') => { const url = new URL(window.location.href); if (next === 'regime') url.searchParams.set('view', 'regime'); else url.searchParams.delete('view'); window.history.pushState({}, '', url); setView(next); };
  return <><nav className="product-nav" aria-label="Dashboard views"><button type="button" className={view === 'market' ? 'active' : ''} onClick={() => navigate('market')}>Market Dashboard</button><button type="button" className={view === 'regime' ? 'active' : ''} onClick={() => navigate('regime')}>Regime &amp; Opportunity Map</button></nav>{view === 'regime' ? <MarketRegimeOpportunityMapPage /> : <MarketDashboardPage />}</>;
}
