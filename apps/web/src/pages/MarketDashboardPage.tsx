import { useCallback, useEffect, useMemo, useState } from 'react';

import { getMarketDashboardData, getSnapshotDashboardData } from '../api/market';
import type { DashboardData, DashboardUniverseViewResponse, EodReturnResponse, LiquidityMapNodeResponse, MarketBenchmarkResponse, SectorBenchmarkEtfResponse } from '../api/types';
import { demoDashboardData } from '../fixtures/marketDemo';
import { formatCompact, formatCurrencyCompact, formatNumber, formatPercent, formatPrice, formatRatio, formatTimestamp, parseDecimal } from '../utils/format';
import { LiquidityTreemap } from '../components/dashboard/LiquidityTreemap';
import { useI18n, type Translate } from '../i18n/I18nProvider';
import {
  benchmarkName, dashboardFunnelName, flagName, localizeClientError, sectorName,
  universeDescription, universeName, validationStatusName,
} from '../i18n/domain';

type DashboardMode = 'api' | 'demo' | 'snapshot';
type DashboardState =
  | { kind: 'loading' }
  | { kind: 'ready'; data: DashboardData; mode: DashboardMode }
  | { kind: 'error'; message: string };

function marketDataMode(): DashboardMode {
  if (import.meta.env.VITE_MARKET_DATA_MODE === 'demo') return 'demo';
  if (import.meta.env.VITE_MARKET_DATA_MODE === 'snapshot') return 'snapshot';
  return 'api';
}

async function logout(locale: string): Promise<void> {
  await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
  window.location.assign(`/?lang=${locale}`);
}

function activeUniverse(data: DashboardData, selected: string): DashboardUniverseViewResponse {
  return data.overview.universes.find((item) => item.definition.universe_id === selected)
    ?? data.overview.universes.find((item) => item.definition.universe_id === data.overview.default_universe_id)
    ?? data.overview.universes[0];
}

function requestedUniverse(): string | null { return new URLSearchParams(window.location.search ?? '').get('universe'); }
function writeUniverseToUrl(universeId: string, replace = false): void {
  const params = new URLSearchParams(window.location.search ?? ''); params.set('universe', universeId);
  const path = window.location.pathname || '/dashboard/';
  window.history[replace ? 'replaceState' : 'pushState']({}, '', `${path}?${params.toString()}`);
}

const MATERIAL_FLAGS = new Set(['unverified_price_discontinuity', 'identity_conflict', 'missing_required_benchmark']);

function freshnessLabel(t: Translate, data: DashboardData): string {
  if (data.overview.freshness_status === 'fresh') return t('dashboard.fresh');
  if (data.overview.freshness_status === 'stale' && data.overview.session_lag !== null) {
    return t(data.overview.session_lag === 1 ? 'dashboard.stale' : 'dashboard.stalePlural', { count: data.overview.session_lag });
  }
  return t('dashboard.calendarUnavailable');
}

function materialFlags(flags: string[]): string[] {
  return flags.filter((flag) => MATERIAL_FLAGS.has(flag));
}

function Header({ mode }: { mode: DashboardMode }): JSX.Element {
  const { locale, t } = useI18n();
  return (
    <header className="dashboard-header">
      <div>
        <p className="brand">WH Alpha</p>
        <h1>{t('dashboard.title')}</h1>
        <p className="subtitle">{t('dashboard.subtitle')}</p>
      </div>
      <div className="session-strip" aria-label={t('dashboard.sessionMetadata')}>
        {mode === 'demo' ? <span className="badge badge-demo">{t('dashboard.demoData')}</span> : null}
        {mode === 'snapshot' ? <button className="logout-button" type="button" onClick={() => void logout(locale)}>{t('dashboard.logout')}</button> : null}
      </div>
    </header>
  );
}

function MetaControlBar({ data, universe, selected, onChange }: { data: DashboardData; universe: DashboardUniverseViewResponse; selected: string; onChange: (value: string) => void }): JSX.Element {
  const { t } = useI18n(); const multiple = data.overview.universes.length > 1;
  const localizedUniverse = universeName(t, universe.definition.universe_id, universe.definition.display_name);
  return (
    <section className="meta-control-bar" aria-label={t('dashboard.controlsAria')}>
      <div>
        <span className="meta-label">{t('common.universe')}</span>
        {multiple ? (
          <select aria-label={t('dashboard.universeAria')} value={selected} onChange={(event) => onChange(event.target.value)}>
            {data.overview.universes.map((item) => (
              <option key={item.definition.universe_id} value={item.definition.universe_id}>{universeName(t, item.definition.universe_id, item.definition.display_name)}</option>
            ))}
          </select>
        ) : <strong>{localizedUniverse}</strong>}
      </div>
      <div><span className="meta-label">{t('dashboard.period')}</span><strong>{t('dashboard.periodValue')}</strong></div>
      <div><span className="meta-label">{t('dashboard.dataAsOf')}</span><strong>{data.overview.current_session_date} EOD</strong></div>
      <div><span className="meta-label">{t('dashboard.freshness')}</span><strong>{freshnessLabel(t, data)}</strong></div>
      <div><span className="meta-label">{t('dashboard.governance')}</span><strong className="governance-provisional">{t('dashboard.provisional')}</strong></div>
      <p className="governance-copy">{universeDescription(t, universe.definition.universe_id, universe.definition.description)} {t('dashboard.scopeCaveat')}</p>
    </section>
  );
}

function MetricCard({ label, value, tone, note }: { label: string; value: string; tone?: 'positive' | 'negative' | 'neutral'; note?: string }): JSX.Element {
  return <article className={`metric-card ${tone ? `metric-${tone}` : ''}`}><span>{label}</span><strong>{value}</strong>{note ? <small>{note}</small> : null}</article>;
}

function BenchmarkStrip({ items, equalWeight }: { items: MarketBenchmarkResponse[]; equalWeight: MarketBenchmarkResponse }): JSX.Element {
  const { t } = useI18n(); const allItems = [...items, equalWeight];
  return (
    <section className="benchmark-strip" aria-label={t('dashboard.marketBenchmarks')}>
      {allItems.map((item) => {
        const label = benchmarkName(t, item.benchmark_id, item.label);
        const value = item.close_to_close_return ? parseDecimal(item.close_to_close_return, `${item.label} return`) : 0;
        const title = item.available && item.current_close
          ? t('dashboard.benchmarkClose', { label, price: formatPrice(item.current_close) })
          : t('dashboard.benchmarkUnavailable', { label });
        return <article key={item.benchmark_id} className={`benchmark-chip ${item.available ? '' : 'benchmark-unavailable'}`} title={title}>
          <span>{item.ticker ?? 'EQW'}</span><small>{label}</small>
          <strong className={item.available ? (value > 0 ? 'positive-text' : value < 0 ? 'negative-text' : '') : ''}>{item.available ? formatPercent(item.close_to_close_return, { signed: true }) : t('common.unavailable')}</strong>
        </article>;
      })}
    </section>
  );
}

function MarketPulse({ universe }: { universe: DashboardUniverseViewResponse }): JSX.Element {
  const { t } = useI18n(); const summary = universe.summary;
  const name = universeName(t, universe.definition.universe_id, universe.definition.display_name);
  const equalWeight = summary.equal_weight_return ? parseDecimal(summary.equal_weight_return, 'equal-weight return') : 0;
  const median = summary.median_return ? parseDecimal(summary.median_return, 'median return') : 0;
  return <section className="panel" aria-labelledby="pulse-title"><div className="section-header"><div><p className="eyebrow">{t('dashboard.marketPulse', { universe: name })}</p><h2 id="pulse-title">{t('dashboard.closeStructure')}</h2></div><p className="section-note">{t('dashboard.comparable', { count: formatNumber(summary.comparable_instrument_count) })}</p></div>
    <div className="metric-grid metric-grid-compact">
      <MetricCard label={t('dashboard.equalWeightReturn')} value={formatPercent(summary.equal_weight_return, { signed: true })} tone={equalWeight > 0 ? 'positive' : equalWeight < 0 ? 'negative' : 'neutral'} note={t('dashboard.equalWeightNote')} />
      <MetricCard label={t('dashboard.medianReturn')} value={formatPercent(summary.median_return, { signed: true })} tone={median > 0 ? 'positive' : median < 0 ? 'negative' : 'neutral'} />
      <MetricCard label={t('dashboard.advDecl')} value={`${formatNumber(summary.advancer_count)} / ${formatNumber(summary.decliner_count)}`} />
      <MetricCard label={t('dashboard.upDownRatio')} value={formatRatio(summary.up_down_volume_ratio)} />
    </div></section>;
}

function Segment({ label, count, total, className }: { label: string; count: number; total: number; className: string }): JSX.Element {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return <div className={`breadth-segment ${className}`} style={{ width: `${pct}%` }}><span>{label}</span><strong>{formatNumber(count)}</strong><em>{pct.toFixed(1)}%</em></div>;
}

function BreadthChart({ universe }: { universe: DashboardUniverseViewResponse }): JSX.Element {
  const { t } = useI18n(); const summary = universe.summary; const total = summary.advancer_count + summary.decliner_count + summary.unchanged_count;
  const name = universeName(t, universe.definition.universe_id, universe.definition.display_name);
  return <section className="panel" aria-labelledby="breadth-title"><div className="section-header"><div><p className="eyebrow">{t('dashboard.marketBreadth', { universe: name })}</p><h2 id="breadth-title">{t('dashboard.breadthTitle')}</h2></div><p className="section-note">{t('dashboard.vs', { current: summary.current_session_date, previous: summary.previous_session_date })}</p></div>
    <div className="breadth-bar" aria-label={t('dashboard.breadthAria')}><Segment label={t('dashboard.advancers')} count={summary.advancer_count} total={total} className="segment-up" /><Segment label={t('dashboard.unchanged')} count={summary.unchanged_count} total={total} className="segment-flat" /><Segment label={t('dashboard.decliners')} count={summary.decliner_count} total={total} className="segment-down" /></div>
    <p className="chart-summary">{t('dashboard.positiveShare', { value: formatPercent(summary.positive_return_share) })} · {t('dashboard.adNet', { value: formatNumber(summary.advance_decline_net) })}</p>
  </section>;
}

function VolumeBreadth({ universe }: { universe: DashboardUniverseViewResponse }): JSX.Element {
  const { t } = useI18n(); const summary = universe.summary;
  const up = parseDecimal(summary.advancer_volume, 'advancer volume'); const down = parseDecimal(summary.decliner_volume, 'decliner volume'); const total = up + down;
  const upPct = total > 0 ? (up / total) * 100 : 0; const downPct = total > 0 ? (down / total) * 100 : 0;
  return <section className="panel" aria-labelledby="volume-title"><div className="section-header"><div><p className="eyebrow">{t('dashboard.volumeEyebrow', { universe: universeName(t, universe.definition.universe_id, universe.definition.display_name) })}</p><h2 id="volume-title">{t('dashboard.volumeTitle')}</h2></div><p className="section-note">{t('dashboard.volumeCaveat')}</p></div>
    <div className="volume-compare"><div className="volume-row"><span>{t('dashboard.advancerVolume')}</span><strong>{formatCompact(summary.advancer_volume)}</strong></div><div className="volume-row"><span>{t('dashboard.declinerVolume')}</span><strong>{formatCompact(summary.decliner_volume)}</strong></div><div className="volume-ratio"><span>{t('dashboard.upDownRatio')}</span><strong>{formatRatio(summary.up_down_volume_ratio)}</strong></div></div>
    <div className="volume-bar" aria-label={t('dashboard.volumeDistribution')}><div className="volume-up" style={{ width: `${upPct}%` }}>{upPct.toFixed(1)}%</div><div className="volume-down" style={{ width: `${downPct}%` }}>{downPct.toFixed(1)}%</div></div>
  </section>;
}

function SectorBenchmarks({ items }: { items: SectorBenchmarkEtfResponse[] }): JSX.Element {
  const { t } = useI18n();
  return <section className="panel" aria-labelledby="sector-etf-title"><div className="section-header"><div><p className="eyebrow">{t('dashboard.sectorEtfs')}</p><h2 id="sector-etf-title">{t('dashboard.sectorTitle')}</h2></div><p className="section-note">{t('dashboard.sectorCaveat')}</p></div>
    <div className="sector-rank sector-performance">{items.map((item) => { const localizedSector = sectorName(t, item.sector); return <div key={item.ticker} className="sector-row" title={`${item.ticker} ${localizedSector}`}><span className="ticker">{item.ticker}</span><span>{localizedSector}</span><strong className={item.close_to_close_return && parseDecimal(item.close_to_close_return, item.ticker) >= 0 ? 'positive-text' : 'negative-text'}>{item.available ? formatPercent(item.close_to_close_return, { signed: true }) : t('common.unavailable')}</strong><span title={t('dashboard.vsSpyHelp')}>{t('dashboard.vsSpy', { value: item.available && item.relative_to_spy_return ? formatPercent(item.relative_to_spy_return, { signed: true }) : '—' })}</span></div>; })}</div>
  </section>;
}

function DetailPanel({ item, onClose }: { item: LiquidityMapNodeResponse | EodReturnResponse; onClose: () => void }): JSX.Element {
  const { t } = useI18n(); const flags = materialFlags(item.quality_flags); const isNode = 'size_value' in item;
  return <aside className="detail-panel" aria-labelledby="detail-title"><div className="detail-header"><h3 id="detail-title">{item.ticker}</h3><button type="button" onClick={onClose} aria-label={t('dashboard.closeDetail')}>{t('common.close')}</button></div><p>{item.name}</p><dl>
    <div><dt>{t('common.return')}</dt><dd>{formatPercent(isNode ? item.color_value : item.close_to_close_return, { signed: true })}</dd></div>
    <div><dt>{t('common.price')}</dt><dd>{formatPrice(item.current_close)}</dd></div>
    <div><dt>{t('dashboard.shareVolume')}</dt><dd>{formatCompact(item.current_volume)}</dd></div>
    <div><dt>{t('dashboard.activityProxy')}</dt><dd>{formatCurrencyCompact(isNode ? item.size_value : item.current_dollar_volume_proxy)}</dd></div>
    {'rank' in item ? <div><dt>{t('dashboard.activityRank')}</dt><dd>{formatNumber(item.rank)}</dd></div> : null}
    <div><dt>{t('dashboard.instrumentType')}</dt><dd>{item.instrument_type}</dd></div>
    <div><dt>{t('dashboard.materialReview')}</dt><dd>{flags.length ? flags.map((flag) => flagName(t, flag)).join(t('common.listSeparator')) : t('common.none')}</dd></div>
  </dl></aside>;
}

function MoversTable({ title, items, direction, onSelect }: { title: string; items: DashboardUniverseViewResponse['movers']['top_gainers']; direction: 'up' | 'down'; onSelect: (item: EodReturnResponse) => void }): JSX.Element {
  const { t } = useI18n();
  return <section className="panel mover-panel" aria-labelledby={`${direction}-movers-title`}><div className="section-header compact"><div><p className="eyebrow">{t('dashboard.selectedUniverse')}</p><h2 id={`${direction}-movers-title`}>{title}</h2></div></div>
    <p className="section-note">{t(direction === 'up' ? 'dashboard.topGainer' : 'dashboard.topLoser')} · {t('dashboard.dollarVolumeCaveat')}</p>
    <div className="mover-heading" aria-hidden="true"><span>{t('dashboard.rank')}</span><span>{t('dashboard.ticker')}</span><span>{t('dashboard.company')}</span><span>{t('common.return')}</span><span>{t('common.price')}</span><span>{t('dashboard.dollarVolume')}</span></div>
    <ol className="mover-list">{items.map((item, index) => <li key={item.instrument_id} tabIndex={0} onClick={() => onSelect(item)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') onSelect(item); }}><span className="rank">{index + 1}</span><span className="ticker">{item.ticker}</span><span className="company" title={item.name}>{item.name}</span><strong className={direction === 'up' ? 'positive-text' : 'negative-text'}>{formatPercent(item.close_to_close_return, { signed: true })}</strong><span>{formatPrice(item.current_close)}</span><span>{formatCurrencyCompact(item.current_dollar_volume_proxy)}</span>{materialFlags(item.quality_flags).length ? <span className="risk-badge">{t('common.review')}</span> : null}</li>)}</ol>
  </section>;
}

function MoversPanel({ universe, onSelect }: { universe: DashboardUniverseViewResponse; onSelect: (item: EodReturnResponse) => void }): JSX.Element {
  const { t } = useI18n();
  return <div className="movers-grid" aria-label={t('dashboard.topMoversAria')}><MoversTable title={t('dashboard.topGainers')} items={universe.movers.top_gainers} direction="up" onSelect={onSelect} /><MoversTable title={t('dashboard.topLosers')} items={universe.movers.top_losers} direction="down" onSelect={onSelect} /></div>;
}

function DataDetails({ universe, data }: { universe: DashboardUniverseViewResponse; data: DashboardData }): JSX.Element {
  const { t } = useI18n(); const adjustmentCount = universe.quality_flag_counts.adjustment_factors_unverified ?? 0;
  const materialEntries = Object.entries(universe.quality_flag_counts).filter(([flag]) => MATERIAL_FLAGS.has(flag));
  const localizedUniverse = universeName(t, universe.definition.universe_id, universe.definition.display_name);
  return <details className="panel quality-panel"><summary>{t('dashboard.dataDetails')}</summary><h3>{t('dashboard.snapshotStatus')}</h3><dl className="quality-grid">
    <div><dt>{t('dashboard.currentSession')}</dt><dd>{data.overview.current_session_date}</dd></div><div><dt>{t('dashboard.previousSession')}</dt><dd>{data.overview.previous_session_date}</dd></div>
    <div><dt>{t('dashboard.snapshotGenerated')}</dt><dd title={data.overview.snapshot_generated_at ?? undefined}>{formatTimestamp(data.overview.snapshot_generated_at)}</dd></div><div><dt>{t('dashboard.validationStatus')}</dt><dd>{validationStatusName(t, data.overview.snapshot_validation_status)}</dd></div>
    <div><dt>{t('dashboard.expectedLatest')}</dt><dd>{data.overview.expected_latest_completed_session ?? t('common.unavailable')}</dd></div><div><dt>{t('dashboard.actualLatest')}</dt><dd>{data.overview.actual_latest_completed_session ?? t('common.unavailable')}</dd></div>
    <div><dt>{t('dashboard.sessionLag')}</dt><dd>{data.overview.session_lag ?? t('common.unavailable')}</dd></div><div><dt>{t('dashboard.freshnessStatus')}</dt><dd>{freshnessLabel(t, data)}</dd></div>
    <div><dt>{t('dashboard.calendar')}</dt><dd>{data.overview.calendar_id}</dd></div><div><dt>{t('dashboard.freshnessChecked')}</dt><dd title={data.overview.freshness_checked_at}>{formatTimestamp(data.overview.freshness_checked_at)}</dd></div>
  </dl><h3>{t('dashboard.funnel')}</h3>
    {universe.funnel?.length === 10 ? <ol className="funnel-list" aria-label={t('dashboard.funnelAria', { universe: localizedUniverse })}>{universe.funnel.map((stage) => <li key={stage.stage_id}><span>{stage.stage_index}. {dashboardFunnelName(t, stage.stage_id, stage.display_label, stage.stage_index)}</span><span>{formatNumber(stage.input_count)} − {formatNumber(stage.excluded_count)} = <strong>{formatNumber(stage.remaining_count)}</strong></span></li>)}</ol> : <p className="quality-copy">{t('dashboard.funnelUnavailable')}</p>}
    <h3>{t('dashboard.methodology')}</h3><div className="quality-flags"><span>{t('dashboard.methodActivity')}</span><span>{t('dashboard.methodHistory', { start: data.overview.trailing_window_start, end: data.overview.trailing_window_end })}</span><span>{t('dashboard.methodPrice')}</span><span>{t('dashboard.methodLiquidity')}</span><span>{t('dashboard.methodEqualWeight')}</span><span>{t('dashboard.methodSector')}</span><span>{t('dashboard.methodFundFlow')}</span></div>
    <h3>{t('dashboard.dataLimitations')}</h3><div className="quality-flags">{adjustmentCount ? <span>{t('dashboard.adjustments', { count: formatNumber(adjustmentCount) })}</span> : null}<span>{t('dashboard.missingTaxonomy')}</span><span>{t('dashboard.missingMarketCap')}</span><span>{t('dashboard.domicileLimit')}</span><span>{t('dashboard.legacyRollback')}</span></div>
    <h3>{t('dashboard.materialWarnings')}</h3><div className="quality-flags"><span>{t('dashboard.coverageWarning')}</span>{materialEntries.map(([flag, count]) => <span key={flag}>{t('dashboard.flagRecords', { flag: flagName(t, flag), count: formatNumber(count) })}</span>)}</div><p className="quality-copy">{t('dashboard.eodCaveat')}</p>
  </details>;
}

function LoadingState(): JSX.Element { const { t } = useI18n(); return <main className="app-shell" aria-live="polite"><div className="panel state-panel">{t('dashboard.loading')}</div></main>; }
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }): JSX.Element {
  const { t } = useI18n(); return <main className="app-shell"><div className="panel state-panel error-state" role="alert"><h1>{t('dashboard.title')}</h1><p>{localizeClientError(t, message)}</p><button type="button" onClick={onRetry}>{t('common.retry')}</button></div></main>;
}

export function MarketDashboardPage(): JSX.Element {
  const { t } = useI18n();
  const [state, setState] = useState<DashboardState>({ kind: 'loading' }); const [selectedUniverseId, setSelectedUniverseId] = useState<string | null>(null);
  const [mapLimit, setMapLimit] = useState(50); const [searchTicker, setSearchTicker] = useState('');
  const [selectedItem, setSelectedItem] = useState<LiquidityMapNodeResponse | EodReturnResponse | null>(null); const mode = useMemo(marketDataMode, []);
  const load = useCallback(() => {
    if (mode === 'demo') { setState({ kind: 'ready', data: demoDashboardData, mode }); setSelectedUniverseId(demoDashboardData.overview.default_universe_id); return undefined; }
    const controller = new AbortController(); setState({ kind: 'loading' }); const requested = requestedUniverse();
    const request = mode === 'snapshot' ? getSnapshotDashboardData(controller.signal).then(({ data }) => data) : getMarketDashboardData(controller.signal, requested ?? undefined);
    request.then((data) => { setState({ kind: 'ready', data, mode }); const allowed = data.overview.universes.some((item) => item.definition.universe_id === requested); const selected = allowed && requested ? requested : data.overview.default_universe_id; setSelectedUniverseId(selected); writeUniverseToUrl(selected, true); })
      .catch((error: unknown) => { if (!controller.signal.aborted) setState({ kind: 'error', message: error instanceof Error ? error.message : '' }); });
    return () => controller.abort();
  }, [mode]);
  useEffect(() => load(), [load]);
  useEffect(() => { const handler = () => { if (state.kind === 'ready') { const requested = requestedUniverse(); const allowed = state.data.overview.universes.some((item) => item.definition.universe_id === requested); const selected = allowed && requested ? requested : state.data.overview.default_universe_id; setSelectedUniverseId(selected); if (!allowed) writeUniverseToUrl(selected, true); } }; window.addEventListener('popstate', handler); return () => window.removeEventListener('popstate', handler); }, [state]);
  if (state.kind === 'loading') return <LoadingState />; if (state.kind === 'error') return <ErrorState message={state.message} onRetry={() => load()} />;
  const selected = selectedUniverseId ?? state.data.overview.default_universe_id; const universe = activeUniverse(state.data, selected);
  const displayedMap = { ...universe.trading_activity_map, nodes: universe.trading_activity_map.nodes.slice(0, mapLimit) }; const searched = searchTicker.trim().toUpperCase();
  const searchHit = searched ? displayedMap.nodes.find((node) => node.ticker === searched) ?? null : null;
  return <main className="app-shell dashboard-shell"><Header mode={state.mode} /><MetaControlBar data={state.data} universe={universe} selected={universe.definition.universe_id} onChange={(value) => { setSelectedUniverseId(value); setSelectedItem(null); writeUniverseToUrl(value); }} />
    <BenchmarkStrip items={state.data.overview.market_benchmarks} equalWeight={universe.equal_weight_benchmark} /><MarketPulse universe={universe} /><div className="two-column-grid"><BreadthChart universe={universe} /><VolumeBreadth universe={universe} /></div><SectorBenchmarks items={state.data.overview.sector_benchmarks} />
    <section className="panel liquidity-panel" aria-labelledby="activity-title"><div className="section-header"><div><p className="eyebrow">{t('dashboard.activityMap')}</p><h2 id="activity-title">{t('dashboard.activityTitle')}</h2></div><div className="map-controls"><label>{t('dashboard.topN')} <select aria-label={t('dashboard.topN')} value={mapLimit} onChange={(event) => setMapLimit(Number(event.target.value))}><option value={50}>50</option><option value={75}>75</option><option value={100}>100</option></select></label><label>{t('dashboard.search')} <input aria-label={t('dashboard.search')} value={searchTicker} onChange={(event) => setSearchTicker(event.target.value)} placeholder={t('dashboard.searchPlaceholder')} /></label></div></div>
      <LiquidityTreemap liquidityMap={displayedMap} highlightedTicker={searchHit?.ticker ?? null} onSelectNode={setSelectedItem} />{searched && !searchHit ? <p className="chart-summary">{t('dashboard.searchMiss', { ticker: searched, count: mapLimit })}</p> : null}{selectedItem ? <DetailPanel item={selectedItem} onClose={() => setSelectedItem(null)} /> : null}
    </section><MoversPanel universe={universe} onSelect={setSelectedItem} /><DataDetails universe={universe} data={state.data} />
  </main>;
}
