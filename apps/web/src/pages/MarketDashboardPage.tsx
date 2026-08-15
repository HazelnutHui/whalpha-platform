import { useCallback, useEffect, useMemo, useState } from 'react';

import { getMarketDashboardData, getSnapshotDashboardData } from '../api/market';
import type { DashboardData, EodReturnResponse, MarketSummaryResponse, MoversResponse } from '../api/types';
import { demoDashboardData } from '../fixtures/marketDemo';
import { formatCompact, formatCurrencyCompact, formatNumber, formatPercent, formatPrice, formatRatio, parseDecimal } from '../utils/format';
import { LiquidityTreemap } from '../components/dashboard/LiquidityTreemap';

type DashboardMode = 'api' | 'demo' | 'snapshot';

type DashboardState =
  | { kind: 'loading' }
  | { kind: 'ready'; data: DashboardData; loadedAt: Date; mode: DashboardMode; releaseId?: string }
  | { kind: 'error'; message: string };

function marketDataMode(): DashboardMode {
  if (import.meta.env.VITE_MARKET_DATA_MODE === 'demo') {
    return 'demo';
  }
  if (import.meta.env.VITE_MARKET_DATA_MODE === 'snapshot') {
    return 'snapshot';
  }
  return 'api';
}

function displayType(value: string): string {
  return value === 'common_stock' ? 'Common Stock' : value.toUpperCase();
}

async function logout(): Promise<void> {
  await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
  window.location.assign('/');
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

function DashboardHeader({ summary, loadedAt, mode, releaseId }: { summary: MarketSummaryResponse; loadedAt: Date; mode: DashboardMode; releaseId?: string }): JSX.Element {
  return (
    <header className="dashboard-header">
      <div>
        <p className="brand">WH Alpha</p>
        <h1>Market Dashboard</h1>
        <p className="subtitle">Trading Intelligence · EOD market structure</p>
      </div>
      <div className="session-strip" aria-label="Session metadata">
        <span>Current {summary.current_session_date}</span>
        <span>Previous {summary.previous_session_date}</span>
        <span className="badge">EOD</span>
        <span className="badge badge-private">Private Data</span>
        {mode === 'demo' ? <span className="badge badge-demo">DEMO DATA</span> : null}
        {mode === 'snapshot' ? <span className="badge badge-snapshot">PRIVATE EOD SNAPSHOT</span> : null}
        <span>Status {summary.data_status}</span>
        {releaseId ? <span>Release {releaseId}</span> : null}
        <span>Loaded {loadedAt.toLocaleTimeString()}</span>
        {mode === 'snapshot' ? <button className="logout-button" type="button" onClick={() => void logout()}>Logout</button> : null}
      </div>
    </header>
  );
}

function MarketPulse({ summary }: { summary: MarketSummaryResponse }): JSX.Element {
  const equalWeight = summary.equal_weight_return ? parseDecimal(summary.equal_weight_return, 'equal-weight return') : 0;
  const median = summary.median_return ? parseDecimal(summary.median_return, 'median return') : 0;
  return (
    <section className="panel" aria-labelledby="pulse-title">
      <div className="section-header">
        <div>
          <p className="eyebrow">Market Pulse</p>
          <h2 id="pulse-title">Close-to-close structure</h2>
        </div>
        <p className="section-note">Equal-weight return is a simple average of comparable securities, not an index return.</p>
      </div>
      <div className="metric-grid">
        <MetricCard label="Equal-Weight Return" value={formatPercent(summary.equal_weight_return, { signed: true })} tone={equalWeight > 0 ? 'positive' : equalWeight < 0 ? 'negative' : 'neutral'} />
        <MetricCard label="Median Return" value={formatPercent(summary.median_return, { signed: true })} tone={median > 0 ? 'positive' : median < 0 ? 'negative' : 'neutral'} />
        <MetricCard label="Advancers / Decliners" value={`${formatNumber(summary.advancer_count)} / ${formatNumber(summary.decliner_count)}`} />
        <MetricCard label="Positive Return Share" value={formatPercent(summary.positive_return_share)} />
        <MetricCard label="Advance–Decline Net" value={formatNumber(summary.advance_decline_net)} tone={summary.advance_decline_net > 0 ? 'positive' : summary.advance_decline_net < 0 ? 'negative' : 'neutral'} />
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

function BreadthChart({ summary }: { summary: MarketSummaryResponse }): JSX.Element {
  const total = summary.advancer_count + summary.decliner_count + summary.unchanged_count;
  return (
    <section className="panel" aria-labelledby="breadth-title">
      <div className="section-header">
        <div>
          <p className="eyebrow">Market Breadth</p>
          <h2 id="breadth-title">Advancers, unchanged, decliners</h2>
        </div>
        <p className="section-note">Comparable instruments: {formatNumber(summary.comparable_instrument_count)}</p>
      </div>
      <div className="breadth-bar" aria-label="Breadth distribution">
        <Segment label="Advancers" count={summary.advancer_count} total={total} className="segment-up" />
        <Segment label="Unchanged" count={summary.unchanged_count} total={total} className="segment-flat" />
        <Segment label="Decliners" count={summary.decliner_count} total={total} className="segment-down" />
      </div>
    </section>
  );
}

function VolumeBreadth({ summary }: { summary: MarketSummaryResponse }): JSX.Element {
  const up = parseDecimal(summary.advancer_volume, 'advancer volume');
  const down = parseDecimal(summary.decliner_volume, 'decliner volume');
  const total = up + down;
  const upPct = total > 0 ? (up / total) * 100 : 0;
  const downPct = total > 0 ? (down / total) * 100 : 0;
  return (
    <section className="panel" aria-labelledby="volume-title">
      <div className="section-header">
        <div>
          <p className="eyebrow">Up/Down Volume</p>
          <h2 id="volume-title">Share volume confirmation</h2>
        </div>
        <p className="section-note">Aggregate share volume may include fractional volume. This is not money flow.</p>
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

function MoversTable({ title, items, direction }: { title: string; items: EodReturnResponse[]; direction: 'up' | 'down' }): JSX.Element {
  return (
    <section className="panel mover-panel" aria-labelledby={`${direction}-movers-title`}>
      <div className="section-header compact">
        <div>
          <p className="eyebrow">Liquidity-screened</p>
          <h2 id={`${direction}-movers-title`}>{title}</h2>
        </div>
      </div>
      <ol className="mover-list">
        {items.map((item, index) => (
          <li key={item.instrument_id} tabIndex={0}>
            <span className="rank">{index + 1}</span>
            <span className="ticker">{item.ticker}</span>
            <span className="company">{item.name}</span>
            <strong className={direction === 'up' ? 'positive-text' : 'negative-text'}>{formatPercent(item.close_to_close_return, { signed: true })}</strong>
            <span>{formatPrice(item.current_close)}</span>
            <span>{formatCurrencyCompact(item.current_dollar_volume_proxy)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function MoversPanel({ movers }: { movers: MoversResponse }): JSX.Element {
  return (
    <div className="movers-grid" aria-label="Top movers">
      <MoversTable title="Top Gainers" items={movers.top_gainers} direction="up" />
      <MoversTable title="Top Losers" items={movers.top_losers} direction="down" />
    </div>
  );
}

function DataQualityPanel({ summary, data }: { summary: MarketSummaryResponse; data: DashboardData }): JSX.Element {
  return (
    <section className="panel quality-panel" aria-labelledby="quality-title">
      <div>
        <p className="eyebrow">Data Quality</p>
        <h2 id="quality-title">Session metadata</h2>
      </div>
      <dl className="quality-grid">
        <div><dt>Current session</dt><dd>{summary.current_session_date}</dd></div>
        <div><dt>Previous session</dt><dd>{summary.previous_session_date}</dd></div>
        <div><dt>Comparable instruments</dt><dd>{formatNumber(summary.comparable_instrument_count)}</dd></div>
        <div><dt>Current-only</dt><dd>{formatNumber(summary.current_only_count)}</dd></div>
        <div><dt>Previous-only</dt><dd>{formatNumber(summary.previous_only_count)}</dd></div>
        <div><dt>Quality warnings</dt><dd>{formatNumber(summary.quality_warning_count)}</dd></div>
        <div><dt>Liquidity nodes</dt><dd>{formatNumber(data.liquidityMap.nodes.length)}</dd></div>
        <div><dt>Mover threshold</dt><dd>{formatCurrencyCompact(data.movers.threshold)}</dd></div>
      </dl>
      <p className="quality-copy">EOD market structure; not real-time. Liquidity Map V1 uses close × volume proxy and close-to-close return. Traditional market-cap sector heatmap is not implemented because market capitalization, sector taxonomy, and point-in-time classification are not yet available.</p>
    </section>
  );
}

function LoadingState(): JSX.Element {
  return <main className="app-shell" aria-live="polite"><div className="panel state-panel">Loading market dashboard…</div></main>;
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }): JSX.Element {
  return (
    <main className="app-shell">
      <div className="panel state-panel error-state" role="alert">
        <h1>Market Dashboard</h1>
        <p>{message}</p>
        <button type="button" onClick={onRetry}>Retry</button>
      </div>
    </main>
  );
}

function EmptyState(): JSX.Element {
  return <div className="panel state-panel">No completed market dashboard data is available.</div>;
}

export function MarketDashboardPage(): JSX.Element {
  const [state, setState] = useState<DashboardState>({ kind: 'loading' });
  const mode = useMemo(marketDataMode, []);

  const load = useCallback(() => {
    if (mode === 'demo') {
      setState({ kind: 'ready', data: demoDashboardData, loadedAt: new Date(), mode });
      return undefined;
    }
    const controller = new AbortController();
    setState({ kind: 'loading' });
    const request = mode === 'snapshot'
      ? getSnapshotDashboardData(controller.signal).then(({ data, manifest }) => ({ data, releaseId: manifest.release_id }))
      : getMarketDashboardData(controller.signal).then((data) => ({ data, releaseId: undefined }));
    request
      .then(({ data, releaseId }) => setState({ kind: 'ready', data, loadedAt: new Date(), mode, releaseId }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const message = error instanceof Error ? error.message : 'Market dashboard request failed';
        setState({ kind: 'error', message });
      });
    return () => controller.abort();
  }, [mode]);

  useEffect(() => load(), [load]);

  if (state.kind === 'loading') {
    return <LoadingState />;
  }
  if (state.kind === 'error') {
    return <ErrorState message={state.message} onRetry={() => load()} />;
  }
  if (state.data.summary.comparable_instrument_count === 0) {
    return <main className="app-shell"><EmptyState /></main>;
  }

  const { summary, movers, liquidityMap } = state.data;
  return (
    <main className="app-shell dashboard-shell">
      <DashboardHeader summary={summary} loadedAt={state.loadedAt} mode={state.mode} releaseId={state.releaseId} />
      <MarketPulse summary={summary} />
      <div className="two-column-grid">
        <BreadthChart summary={summary} />
        <VolumeBreadth summary={summary} />
      </div>
      <LiquidityTreemap liquidityMap={liquidityMap} />
      <MoversPanel movers={movers} />
      <DataQualityPanel summary={summary} data={state.data} />
    </main>
  );
}
