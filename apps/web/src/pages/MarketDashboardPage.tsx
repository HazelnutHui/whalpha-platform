import { useCallback, useEffect, useMemo, useState } from 'react';

import { getMarketDashboardData, getSnapshotDashboardData } from '../api/market';
import type { DashboardData, DashboardUniverseViewResponse, LiquidityMapNodeResponse, SectorBenchmarkEtfResponse } from '../api/types';
import { demoDashboardData } from '../fixtures/marketDemo';
import { formatCompact, formatCurrencyCompact, formatNumber, formatPercent, formatPrice, formatRatio, parseDecimal } from '../utils/format';
import { LiquidityTreemap } from '../components/dashboard/LiquidityTreemap';

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

async function logout(): Promise<void> {
  await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
  window.location.assign('/');
}

function activeUniverse(data: DashboardData, selected: string): DashboardUniverseViewResponse {
  return data.overview.universes.find((item) => item.definition.universe_id === selected) ?? data.overview.universes[0];
}

function Header({ data, universe, mode }: { data: DashboardData; universe: DashboardUniverseViewResponse; mode: DashboardMode }): JSX.Element {
  return (
    <header className="dashboard-header">
      <div>
        <p className="brand">WH Alpha</p>
        <h1>Market Overview</h1>
        <p className="subtitle">EOD · {data.overview.data_as_of_label} · {universe.definition.display_name}</p>
      </div>
      <div className="session-strip" aria-label="Session metadata">
        <span>{universe.definition.display_name}</span>
        <span>EOD</span>
        {mode === 'demo' ? <span className="badge badge-demo">DEMO DATA</span> : null}
        {mode === 'snapshot' ? <button className="logout-button" type="button" onClick={() => void logout()}>Logout</button> : null}
      </div>
    </header>
  );
}

function UniverseSelector({ data, selected, onChange }: { data: DashboardData; selected: string; onChange: (value: string) => void }): JSX.Element {
  return (
    <section className="panel universe-panel" aria-labelledby="universe-title">
      <div className="section-header compact">
        <div>
          <p className="eyebrow">Universe</p>
          <h2 id="universe-title">Analysis universe</h2>
        </div>
        <select aria-label="Dashboard universe" value={selected} onChange={(event) => onChange(event.target.value)}>
          {data.overview.universes.map((item) => (
            <option key={item.definition.universe_id} value={item.definition.universe_id}>{item.definition.display_name}</option>
          ))}
        </select>
      </div>
      <p className="section-copy">{activeUniverse(data, selected).definition.description}</p>
    </section>
  );
}

function MetricCard({ label, value, tone, note }: { label: string; value: string; tone?: 'positive' | 'negative' | 'neutral'; note?: string }): JSX.Element {
  return (
    <article className={`metric-card ${tone ? `metric-${tone}` : ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {note ? <small>{note}</small> : null}
    </article>
  );
}

function MarketPulse({ universe }: { universe: DashboardUniverseViewResponse }): JSX.Element {
  const summary = universe.summary;
  const equalWeight = summary.equal_weight_return ? parseDecimal(summary.equal_weight_return, 'equal-weight return') : 0;
  const median = summary.median_return ? parseDecimal(summary.median_return, 'median return') : 0;
  return (
    <section className="panel" aria-labelledby="pulse-title">
      <div className="section-header">
        <div>
          <p className="eyebrow">Market Pulse · {universe.definition.display_name}</p>
          <h2 id="pulse-title">Close-to-close structure</h2>
        </div>
        <p className="section-note">Comparable instruments: {formatNumber(summary.comparable_instrument_count)}</p>
      </div>
      <div className="metric-grid metric-grid-compact">
        <MetricCard label="Equal-Weight Return" value={formatPercent(summary.equal_weight_return, { signed: true })} tone={equalWeight > 0 ? 'positive' : equalWeight < 0 ? 'negative' : 'neutral'} note="Simple average, not an index return" />
        <MetricCard label="Median Return" value={formatPercent(summary.median_return, { signed: true })} tone={median > 0 ? 'positive' : median < 0 ? 'negative' : 'neutral'} />
        <MetricCard label="Advancers / Decliners" value={`${formatNumber(summary.advancer_count)} / ${formatNumber(summary.decliner_count)}`} />
        <MetricCard label="Up/Down Volume Ratio" value={formatRatio(summary.up_down_volume_ratio)} />
      </div>
    </section>
  );
}

function Segment({ label, count, total, className }: { label: string; count: number; total: number; className: string }): JSX.Element {
  const percent = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className={`breadth-segment ${className}`} style={{ width: `${percent}%` }}>
      <span>{label}</span>
      <strong>{formatNumber(count)}</strong>
      <em>{percent.toFixed(1)}%</em>
    </div>
  );
}

function BreadthChart({ universe }: { universe: DashboardUniverseViewResponse }): JSX.Element {
  const summary = universe.summary;
  const total = summary.advancer_count + summary.decliner_count + summary.unchanged_count;
  return (
    <section className="panel" aria-labelledby="breadth-title">
      <div className="section-header">
        <div>
          <p className="eyebrow">Market Breadth · {universe.definition.display_name}</p>
          <h2 id="breadth-title">Advancers, unchanged, decliners</h2>
        </div>
        <p className="section-note">{summary.current_session_date} vs {summary.previous_session_date}</p>
      </div>
      <div className="breadth-bar" aria-label="Breadth distribution">
        <Segment label="Advancers" count={summary.advancer_count} total={total} className="segment-up" />
        <Segment label="Unchanged" count={summary.unchanged_count} total={total} className="segment-flat" />
        <Segment label="Decliners" count={summary.decliner_count} total={total} className="segment-down" />
      </div>
      <p className="chart-summary">Positive share: {formatPercent(summary.positive_return_share)} · A/D net: {formatNumber(summary.advance_decline_net)}</p>
    </section>
  );
}

function VolumeBreadth({ universe }: { universe: DashboardUniverseViewResponse }): JSX.Element {
  const summary = universe.summary;
  const up = parseDecimal(summary.advancer_volume, 'advancer volume');
  const down = parseDecimal(summary.decliner_volume, 'decliner volume');
  const total = up + down;
  const upPct = total > 0 ? (up / total) * 100 : 0;
  const downPct = total > 0 ? (down / total) * 100 : 0;
  return (
    <section className="panel" aria-labelledby="volume-title">
      <div className="section-header">
        <div>
          <p className="eyebrow">Up/Down Volume · {universe.definition.display_name}</p>
          <h2 id="volume-title">Share volume participation</h2>
        </div>
        <p className="section-note">Share volume participation, not money flow.</p>
      </div>
      <div className="volume-compare">
        <div className="volume-row"><span>Advancer volume</span><strong>{formatCompact(summary.advancer_volume)}</strong></div>
        <div className="volume-row"><span>Decliner volume</span><strong>{formatCompact(summary.decliner_volume)}</strong></div>
        <div className="volume-ratio"><span>Up/Down Volume Ratio</span><strong>{formatRatio(summary.up_down_volume_ratio)}</strong></div>
      </div>
      <div className="volume-bar" aria-label="Up down volume distribution">
        <div className="volume-up" style={{ width: `${upPct}%` }}>{upPct.toFixed(1)}%</div>
        <div className="volume-down" style={{ width: `${downPct}%` }}>{downPct.toFixed(1)}%</div>
      </div>
    </section>
  );
}

function SectorBenchmarks({ items }: { items: SectorBenchmarkEtfResponse[] }): JSX.Element {
  return (
    <section className="panel" aria-labelledby="sector-etf-title">
      <div className="section-header">
        <div>
          <p className="eyebrow">Sector Benchmark ETFs</p>
          <h2 id="sector-etf-title">S&P 500 Select Sector SPDR 1D performance</h2>
        </div>
        <p className="section-note">ETF benchmark performance, not sector breadth or fund flow.</p>
      </div>
      <div className="sector-rank">
        {items.map((item) => (
          <div key={item.ticker} className="sector-row" title={`${item.ticker} ${item.sector}`}>
            <span className="ticker">{item.ticker}</span>
            <span>{item.sector}</span>
            <strong className={item.close_to_close_return && parseDecimal(item.close_to_close_return, item.ticker) >= 0 ? 'positive-text' : 'negative-text'}>{item.available ? formatPercent(item.close_to_close_return, { signed: true }) : 'Unavailable'}</strong>
            <span>{item.available ? formatPrice(item.previous_close) : '—'}</span>
            <span>{item.available ? formatPrice(item.current_close) : '—'}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function MoversTable({ title, items, direction }: { title: string; items: DashboardUniverseViewResponse['movers']['top_gainers']; direction: 'up' | 'down' }): JSX.Element {
  return (
    <section className="panel mover-panel" aria-labelledby={`${direction}-movers-title`}>
      <div className="section-header compact">
        <div>
          <p className="eyebrow">Tradable U.S. Equities</p>
          <h2 id={`${direction}-movers-title`}>{title}</h2>
        </div>
      </div>
      <div className="mover-heading" aria-hidden="true"><span>Rank</span><span>Ticker</span><span>Company</span><span>Return</span><span>Close</span><span>Current Dollar Volume</span></div>
      <ol className="mover-list">
        {items.map((item, index) => (
          <li key={item.instrument_id} tabIndex={0}>
            <span className="rank">{index + 1}</span>
            <span className="ticker">{item.ticker}</span>
            <span className="company" title={item.name}>{item.name}</span>
            <strong className={direction === 'up' ? 'positive-text' : 'negative-text'}>{formatPercent(item.close_to_close_return, { signed: true })}</strong>
            <span>{formatPrice(item.current_close)}</span>
            <span>{formatCurrencyCompact(item.current_dollar_volume_proxy)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function MoversPanel({ universe }: { universe: DashboardUniverseViewResponse }): JSX.Element {
  return (
    <div className="movers-grid" aria-label="Top movers">
      <MoversTable title="Top Gainers" items={universe.movers.top_gainers} direction="up" />
      <MoversTable title="Top Losers" items={universe.movers.top_losers} direction="down" />
    </div>
  );
}

function DataDetails({ universe, data }: { universe: DashboardUniverseViewResponse; data: DashboardData }): JSX.Element {
  const qualityEntries = Object.entries(universe.quality_flag_counts);
  return (
    <details className="panel quality-panel">
      <summary>Data Details</summary>
      <dl className="quality-grid">
        <div><dt>Current session</dt><dd>{data.overview.current_session_date}</dd></div>
        <div><dt>Previous session</dt><dd>{data.overview.previous_session_date}</dd></div>
        <div><dt>Universe count</dt><dd>{formatNumber(universe.summary.comparable_instrument_count)}</dd></div>
        <div><dt>Outlier review</dt><dd>{formatNumber(universe.outlier_review_count)}</dd></div>
        <div><dt>ETF excluded count</dt><dd>{formatNumber(universe.audit.etf_count)}</dd></div>
        <div><dt>Price gate count</dt><dd>{formatNumber(universe.audit.price_gate_count)}</dd></div>
        <div><dt>Liquidity gate final</dt><dd>{formatNumber(universe.audit.final_count)}</dd></div>
        <div><dt>Data status</dt><dd>{data.overview.data_status}</dd></div>
      </dl>
      <div className="quality-flags">
        {qualityEntries.length ? qualityEntries.map(([flag, count]) => <span key={flag}>{flag.replace(/_/g, ' ')} — {formatNumber(count)} records</span>) : <span>No quality flags in selected universe.</span>}
      </div>
      <p className="quality-copy">EOD market structure; not real-time. Complete means the snapshot files are internally complete, not that the data is the latest possible market day. Trading Activity Map uses close × volume proxy and close-to-close return; it is not a market-cap heatmap, sector map, or fund-flow display.</p>
    </details>
  );
}

function LoadingState(): JSX.Element {
  return <main className="app-shell" aria-live="polite"><div className="panel state-panel">Loading market overview…</div></main>;
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }): JSX.Element {
  return (
    <main className="app-shell">
      <div className="panel state-panel error-state" role="alert">
        <h1>Market Overview</h1>
        <p>{message}</p>
        <button type="button" onClick={onRetry}>Retry</button>
      </div>
    </main>
  );
}

export function MarketDashboardPage(): JSX.Element {
  const [state, setState] = useState<DashboardState>({ kind: 'loading' });
  const [selectedUniverseId, setSelectedUniverseId] = useState<string | null>(null);
  const [mapLimit, setMapLimit] = useState(75);
  const [searchTicker, setSearchTicker] = useState('');
  const [selectedNode, setSelectedNode] = useState<LiquidityMapNodeResponse | null>(null);
  const mode = useMemo(marketDataMode, []);

  const load = useCallback(() => {
    if (mode === 'demo') {
      setState({ kind: 'ready', data: demoDashboardData, mode });
      setSelectedUniverseId(demoDashboardData.overview.default_universe_id);
      return undefined;
    }
    const controller = new AbortController();
    setState({ kind: 'loading' });
    const request = mode === 'snapshot' ? getSnapshotDashboardData(controller.signal).then(({ data }) => data) : getMarketDashboardData(controller.signal);
    request
      .then((data) => {
        setState({ kind: 'ready', data, mode });
        setSelectedUniverseId(data.overview.default_universe_id);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ kind: 'error', message: error instanceof Error ? error.message : 'Market overview request failed' });
      });
    return () => controller.abort();
  }, [mode]);

  useEffect(() => load(), [load]);

  if (state.kind === 'loading') return <LoadingState />;
  if (state.kind === 'error') return <ErrorState message={state.message} onRetry={() => load()} />;

  const selected = selectedUniverseId ?? state.data.overview.default_universe_id;
  const universe = activeUniverse(state.data, selected);
  const displayedMap = { ...universe.trading_activity_map, nodes: universe.trading_activity_map.nodes.slice(0, mapLimit) };
  const searched = searchTicker.trim().toUpperCase();
  const searchHit = searched ? displayedMap.nodes.find((node) => node.ticker === searched) ?? null : null;

  return (
    <main className="app-shell dashboard-shell">
      <Header data={state.data} universe={universe} mode={state.mode} />
      <UniverseSelector data={state.data} selected={universe.definition.universe_id} onChange={setSelectedUniverseId} />
      <MarketPulse universe={universe} />
      <div className="two-column-grid">
        <BreadthChart universe={universe} />
        <VolumeBreadth universe={universe} />
      </div>
      <SectorBenchmarks items={state.data.overview.sector_benchmarks} />
      <section className="panel liquidity-panel" aria-labelledby="activity-title">
        <div className="section-header">
          <div>
            <p className="eyebrow">Trading Activity Map</p>
            <h2 id="activity-title">Where trading activity is concentrated</h2>
          </div>
          <div className="map-controls">
            <label>Top N <select value={mapLimit} onChange={(event) => setMapLimit(Number(event.target.value))}><option value={50}>50</option><option value={75}>75</option><option value={100}>100</option></select></label>
            <label>Search <input value={searchTicker} onChange={(event) => setSearchTicker(event.target.value)} placeholder="Ticker" /></label>
          </div>
        </div>
        <LiquidityTreemap liquidityMap={displayedMap} highlightedTicker={searchHit?.ticker ?? null} onSelectNode={setSelectedNode} />
        {searched && !searchHit ? <p className="chart-summary">Ticker {searched} is not in the current Top {mapLimit} map.</p> : null}
        {selectedNode ? <aside className="detail-panel"><h3>{selectedNode.ticker}</h3><p>{selectedNode.name}</p><dl><div><dt>Return</dt><dd>{formatPercent(selectedNode.color_value, { signed: true })}</dd></div><div><dt>Close</dt><dd>{formatPrice(selectedNode.current_close)}</dd></div><div><dt>Share Volume</dt><dd>{formatCompact(selectedNode.current_volume)}</dd></div><div><dt>Trading Activity Proxy</dt><dd>{formatCurrencyCompact(selectedNode.size_value)}</dd></div><div><dt>Instrument Type</dt><dd>{selectedNode.instrument_type}</dd></div></dl></aside> : null}
      </section>
      <MoversPanel universe={universe} />
      <DataDetails universe={universe} data={state.data} />
    </main>
  );
}
