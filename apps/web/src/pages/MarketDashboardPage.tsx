import { useCallback, useEffect, useMemo, useState } from 'react';

import { getMarketDashboardData, getSnapshotDashboardData } from '../api/market';
import type { DashboardData, DashboardUniverseViewResponse, EodReturnResponse, LiquidityMapNodeResponse, MarketBenchmarkResponse, SectorBenchmarkEtfResponse } from '../api/types';
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

const MATERIAL_FLAGS = new Set(['unverified_price_discontinuity', 'identity_conflict', 'missing_required_benchmark']);

function friendlyStatus(value: string): string {
  return value.replace(/_/g, ' ');
}

function materialFlags(flags: string[]): string[] {
  return flags.filter((flag) => MATERIAL_FLAGS.has(flag));
}

function Header({ mode }: { mode: DashboardMode }): JSX.Element {
  return (
    <header className="dashboard-header">
      <div>
        <p className="brand">WH Alpha</p>
        <h1>Market Overview</h1>
        <p className="subtitle">End-of-day market structure and trading activity.</p>
      </div>
      <div className="session-strip" aria-label="Session metadata">
        {mode === 'demo' ? <span className="badge badge-demo">DEMO DATA</span> : null}
        {mode === 'snapshot' ? <button className="logout-button" type="button" onClick={() => void logout()}>Logout</button> : null}
      </div>
    </header>
  );
}

function MetaControlBar({ data, universe, selected, onChange }: { data: DashboardData; universe: DashboardUniverseViewResponse; selected: string; onChange: (value: string) => void }): JSX.Element {
  const multiple = data.overview.universes.length > 1;
  return (
    <section className="meta-control-bar" aria-label="Market overview controls">
      <div>
        <span className="meta-label">Universe</span>
        {multiple ? (
          <select aria-label="Dashboard universe" value={selected} onChange={(event) => onChange(event.target.value)}>
            {data.overview.universes.map((item) => (
              <option key={item.definition.universe_id} value={item.definition.universe_id}>{item.definition.display_name}</option>
            ))}
          </select>
        ) : (
          <strong>{universe.definition.display_name}</strong>
        )}
      </div>
      <div><span className="meta-label">Period</span><strong>1D close-to-close</strong></div>
      <div><span className="meta-label">Data as of</span><strong>{data.overview.current_session_date} EOD</strong></div>
      <div><span className="meta-label">Freshness</span><strong>{friendlyStatus(data.overview.freshness_status)}</strong></div>
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

function BenchmarkStrip({ items }: { items: MarketBenchmarkResponse[] }): JSX.Element {
  return (
    <section className="benchmark-strip" aria-label="Market benchmarks">
      {items.map((item) => {
        const value = item.close_to_close_return ? parseDecimal(item.close_to_close_return, `${item.label} return`) : 0;
        return (
          <article key={item.benchmark_id} className={`benchmark-chip ${item.available ? '' : 'benchmark-unavailable'}`} title={item.available && item.current_close ? `${item.label} close ${formatPrice(item.current_close)}` : `${item.label} unavailable`}>
            <span>{item.ticker ?? 'EQW'}</span>
            <small>{item.label}</small>
            <strong className={item.available ? (value > 0 ? 'positive-text' : value < 0 ? 'negative-text' : '') : ''}>{item.available ? formatPercent(item.close_to_close_return, { signed: true }) : 'Unavailable'}</strong>
          </article>
        );
      })}
    </section>
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
      <div className="sector-rank sector-performance">
        {items.map((item) => (
          <div key={item.ticker} className="sector-row" title={`${item.ticker} ${item.sector}`}>
            <span className="ticker">{item.ticker}</span>
            <span>{item.sector}</span>
            <strong className={item.close_to_close_return && parseDecimal(item.close_to_close_return, item.ticker) >= 0 ? 'positive-text' : 'negative-text'}>{item.available ? formatPercent(item.close_to_close_return, { signed: true }) : 'Unavailable'}</strong>
            <span title="Arithmetic return difference versus SPY; not alpha or risk-adjusted return.">vs SPY {item.available && item.relative_to_spy_return ? formatPercent(item.relative_to_spy_return, { signed: true }) : '—'}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function DetailPanel({ item, onClose }: { item: LiquidityMapNodeResponse | EodReturnResponse; onClose: () => void }): JSX.Element {
  const flags = materialFlags(item.quality_flags);
  const isNode = 'size_value' in item;
  return (
    <aside className="detail-panel" aria-labelledby="detail-title">
      <div className="detail-header">
        <h3 id="detail-title">{item.ticker}</h3>
        <button type="button" onClick={onClose} aria-label="Close detail">Close</button>
      </div>
      <p>{item.name}</p>
      <dl>
        <div><dt>Return</dt><dd>{formatPercent(isNode ? item.color_value : item.close_to_close_return, { signed: true })}</dd></div>
        <div><dt>Price</dt><dd>{formatPrice(isNode ? item.current_close : item.current_close)}</dd></div>
        <div><dt>Share Volume</dt><dd>{formatCompact(isNode ? item.current_volume : item.current_volume)}</dd></div>
        <div><dt>Trading Activity Proxy</dt><dd>{formatCurrencyCompact(isNode ? item.size_value : item.current_dollar_volume_proxy)}</dd></div>
        {'rank' in item ? <div><dt>Activity Rank</dt><dd>{formatNumber(item.rank)}</dd></div> : null}
        <div><dt>Instrument Type</dt><dd>{item.instrument_type}</dd></div>
        <div><dt>Material Review</dt><dd>{flags.length ? flags.map((flag) => flag.replace(/_/g, ' ')).join(', ') : 'None'}</dd></div>
      </dl>
    </aside>
  );
}

function MoversTable({ title, items, direction, onSelect }: { title: string; items: DashboardUniverseViewResponse['movers']['top_gainers']; direction: 'up' | 'down'; onSelect: (item: EodReturnResponse) => void }): JSX.Element {
  return (
    <section className="panel mover-panel" aria-labelledby={`${direction}-movers-title`}>
      <div className="section-header compact">
        <div>
          <p className="eyebrow">Tradable U.S. Equities</p>
          <h2 id={`${direction}-movers-title`}>{title}</h2>
        </div>
      </div>
      <p className="section-note">{direction === 'up' ? 'Top 1D gainer in selected universe' : 'Top 1D loser in selected universe'} · Dollar Volume is close × volume proxy.</p>
      <div className="mover-heading" aria-hidden="true"><span>Rank</span><span>Ticker</span><span>Company</span><span>Return</span><span>Price</span><span>Dollar Volume</span></div>
      <ol className="mover-list">
        {items.map((item, index) => (
          <li key={item.instrument_id} tabIndex={0} onClick={() => onSelect(item)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') onSelect(item); }}>
            <span className="rank">{index + 1}</span>
            <span className="ticker">{item.ticker}</span>
            <span className="company" title={item.name}>{item.name}</span>
            <strong className={direction === 'up' ? 'positive-text' : 'negative-text'}>{formatPercent(item.close_to_close_return, { signed: true })}</strong>
            <span>{formatPrice(item.current_close)}</span>
            <span>{formatCurrencyCompact(item.current_dollar_volume_proxy)}</span>
            {materialFlags(item.quality_flags).length ? <span className="risk-badge">Review</span> : null}
          </li>
        ))}
      </ol>
    </section>
  );
}

function MoversPanel({ universe, onSelect }: { universe: DashboardUniverseViewResponse; onSelect: (item: EodReturnResponse) => void }): JSX.Element {
  return (
    <div className="movers-grid" aria-label="Top movers">
      <MoversTable title="Top Gainers" items={universe.movers.top_gainers} direction="up" onSelect={onSelect} />
      <MoversTable title="Top Losers" items={universe.movers.top_losers} direction="down" onSelect={onSelect} />
    </div>
  );
}

function DataDetails({ universe, data }: { universe: DashboardUniverseViewResponse; data: DashboardData }): JSX.Element {
  const adjustmentCount = universe.quality_flag_counts.adjustment_factors_unverified ?? 0;
  const materialEntries = Object.entries(universe.quality_flag_counts).filter(([flag]) => MATERIAL_FLAGS.has(flag));
  return (
    <details className="panel quality-panel">
      <summary>Data Details</summary>
      <h3>Snapshot Status</h3>
      <dl className="quality-grid">
        <div><dt>Current session</dt><dd>{data.overview.current_session_date}</dd></div>
        <div><dt>Previous session</dt><dd>{data.overview.previous_session_date}</dd></div>
        <div><dt>Snapshot generated at</dt><dd>{data.overview.snapshot_generated_at ?? 'Unavailable'}</dd></div>
        <div><dt>Validation status</dt><dd>{friendlyStatus(data.overview.snapshot_validation_status)}</dd></div>
        <div><dt>Freshness status</dt><dd>{friendlyStatus(data.overview.freshness_status)}</dd></div>
      </dl>
      <h3>Universe Funnel</h3>
      <dl className="quality-grid">
        <div><dt>Raw comparable</dt><dd>{formatNumber(universe.audit.raw_comparable_count)}</dd></div>
        <div><dt>Common equities classified</dt><dd>{formatNumber(universe.audit.common_stock_count)}</dd></div>
        <div><dt>ETF/ETP excluded</dt><dd>{formatNumber(universe.audit.etf_count)}</dd></div>
        <div><dt>Supported exchange records</dt><dd>{formatNumber(universe.audit.major_exchange_count)}</dd></div>
        <div><dt>Price gate passed</dt><dd>{formatNumber(universe.audit.price_gate_count)}</dd></div>
        <div><dt>Liquidity gate final</dt><dd>{formatNumber(universe.audit.final_count)}</dd></div>
        <div><dt>Outlier review</dt><dd>{formatNumber(universe.outlier_review_count)}</dd></div>
      </dl>
      <h3>Methodology Notes</h3>
      <div className="quality-flags">
        <span>close × volume trading activity proxy</span>
        <span>Equal-weight return is not an index return</span>
        <span>ETF benchmarks are not sector breadth</span>
        <span>ETF benchmark volume is not fund flow</span>
      </div>
      <h3>Data Limitations</h3>
      <div className="quality-flags">
        {adjustmentCount ? <span>Adjustment factors unverified — {formatNumber(adjustmentCount)} records</span> : null}
        <span>Missing point-in-time sector taxonomy</span>
        <span>Missing market capitalization</span>
        <span>Insufficient history for trailing liquidity</span>
      </div>
      <h3>Material Warnings</h3>
      <div className="quality-flags">
        {materialEntries.length ? materialEntries.map(([flag, count]) => <span key={flag}>{flag.replace(/_/g, ' ')} — {formatNumber(count)} records</span>) : <span>No material warnings in selected universe.</span>}
      </div>
      <p className="quality-copy">EOD market structure; not real-time. Snapshot validation means the completed files passed consistency checks, not that the session is independently verified as the latest market day.</p>
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
  const [mapLimit, setMapLimit] = useState(50);
  const [searchTicker, setSearchTicker] = useState('');
  const [selectedItem, setSelectedItem] = useState<LiquidityMapNodeResponse | EodReturnResponse | null>(null);
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
      <Header mode={state.mode} />
      <MetaControlBar data={state.data} universe={universe} selected={universe.definition.universe_id} onChange={setSelectedUniverseId} />
      <BenchmarkStrip items={state.data.overview.market_benchmarks} />
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
        <LiquidityTreemap liquidityMap={displayedMap} highlightedTicker={searchHit?.ticker ?? null} onSelectNode={setSelectedItem} />
        {searched && !searchHit ? <p className="chart-summary">Ticker {searched} is not in the current Top {mapLimit} map.</p> : null}
        {selectedItem ? <DetailPanel item={selectedItem} onClose={() => setSelectedItem(null)} /> : null}
      </section>
      <MoversPanel universe={universe} onSelect={setSelectedItem} />
      <DataDetails universe={universe} data={state.data} />
    </main>
  );
}
