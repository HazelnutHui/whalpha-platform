import { useCallback, useEffect, useMemo, useState } from 'react';

import { getMarketRegimePreview, type MarketRegimePreviewResponse, type Relationship, type RelationshipWindow } from '../api/marketRegime';

type PageState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; data: MarketRegimePreviewResponse };
type WindowSize = 5 | 10 | 20;

const STATE_PRIORITY: Record<string, number> = {
  relationship_break_candidate: 0, rotation_candidate: 1, divergence: 2,
  synchronous_weakening: 3, synchronous_strengthening: 4, neutral: 5, unavailable: 6,
};
const DIMENSION_LABELS: Record<string, string> = {
  trend: 'Trend', breadth: 'Breadth', volatility: 'Volatility',
  liquidity_participation: 'Liquidity / Participation', leadership_dispersion: 'Leadership / Dispersion',
};
const REASON_LABELS: Record<string, string> = {
  candidate_band_balanced: 'Composite is in the fixed Balanced candidate band.',
  confirmed_state_held: 'The confirmed state held under the hysteresis contract.',
  state_input_available: 'All critical state inputs are available.',
  short_history_low_confidence: 'History is complete for this window but too short for predictive confidence.',
};
function human(value: string): string { return value.replace(/_/g, ' ').replace(/\b\w/g, (item: string) => item.toUpperCase()); }
function number(value: string | null, digits = 2): string { return value === null ? 'Unavailable' : Number(value).toFixed(digits); }
function percent(value: string | null): string { return value === null ? 'Unavailable' : `${Number(value) >= 0 ? '+' : ''}${(Number(value) * 100).toFixed(2)}%`; }
function signed(value: string | null, digits = 3): string { return value === null ? 'Unavailable' : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(digits)}`; }
function requested(): { universe?: string; window: WindowSize; family: string; state: string; scope: string; pair?: string } {
  const query = new URLSearchParams(window.location.search); const windowValue = Number(query.get('window'));
  return { universe: query.get('universe') ?? undefined, window: [5, 10, 20].includes(windowValue) ? windowValue as WindowSize : 5,
    family: query.get('family') ?? 'all', state: query.get('state') ?? 'all', scope: query.get('scope') ?? 'all', pair: query.get('pair') ?? undefined };
}
function updateUrl(changes: Record<string, string | null>, replace = false): void {
  const url = new URL(window.location.href); url.searchParams.set('view', 'regime');
  Object.entries(changes).forEach(([key, value]) => value === null || value === 'all' ? url.searchParams.delete(key) : url.searchParams.set(key, value));
  window.history[replace ? 'replaceState' : 'pushState']({}, '', url);
}
function StateMark({ state }: { state: string | null }): JSX.Element { return <span className={`regime-state state-${state ?? 'unavailable'}`}><i aria-hidden="true" />{state ? human(state) : 'Unavailable'}</span>; }
function WindowMetric({ relationship, windowSize }: { relationship: Relationship; windowSize: WindowSize }): JSX.Element {
  const metric = relationship.current.windows.find((item) => item.window_sessions === windowSize) as RelationshipWindow;
  return <><span className={metric.left_return && Number(metric.left_return) >= 0 ? 'positive-text' : 'negative-text'}>{percent(metric.left_return)}</span><span className={metric.right_return && Number(metric.right_return) >= 0 ? 'positive-text' : 'negative-text'}>{percent(metric.right_return)}</span><strong>{percent(metric.relative_return)}</strong><span>{number(metric.rolling_correlation, 3)}</span></>;
}

function Hero({ data }: { data: MarketRegimePreviewResponse }): JSX.Element {
  const state = data.regime.current_state; const support = state.supporting_dimension_ids.map((item) => DIMENSION_LABELS[item]).join(', ');
  const conflict = state.conflicting_dimension_ids.map((item) => DIMENSION_LABELS[item]).join(', ');
  return <section className="regime-hero panel">
    <div><p className="eyebrow">Market Regime · Frozen local preview</p><h1>Market Regime &amp; Opportunity Map</h1><p className="subtitle">{support} support the current reading; {conflict || 'no dimensions'} currently drag it. The Composite has not reached the fixed Risk-on confirmation threshold.</p></div>
    <div className="regime-hero-score"><span>Confirmed</span><StateMark state={state.confirmed_state} /><strong>{number(data.regime.composite.regime_score, 4)}</strong><small>Composite / 100</small></div>
    <div className="regime-hero-meta"><span>Candidate <b>{human(state.instantaneous_candidate_state ?? 'unavailable')}</b></span><span>As of <b>{data.as_of_session}</b></span><span>Universe <b>{data.regime.definition.display_name}</b></span><span>Data <b>Short-history preview</b></span></div>
    <p className="research-banner">Research context, not a trade recommendation. Statistical relationships are not causation.</p>
  </section>;
}

function Dimensions({ data }: { data: MarketRegimePreviewResponse }): JSX.Element {
  return <section className="panel" aria-labelledby="dimensions-title"><div className="section-header"><div><p className="eyebrow">Transparent Composite</p><h2 id="dimensions-title">Five dimensions, one auditable score</h2></div><p className="section-note">Every contribution is score × effective weight. Regime adjustment is fixed at 0.</p></div>
    <div className="dimension-grid">{data.regime.composite.dimensions.map((dimension) => <details className={`dimension-card support-${dimension.support_status}`} key={dimension.dimension_id}>
      <summary><span><i />{DIMENSION_LABELS[dimension.dimension_id]}</span><strong>{number(dimension.score, 4)}</strong><small>{number(dimension.effective_weight, 4)} weight · {number(dimension.score_contribution, 4)} contribution</small></summary>
      <p>{dimension.rendered_explanation}</p><div className="metric-ledger"><div className="metric-ledger-head"><span>Metric</span><span>Raw</span><span>Normalized</span><span>Weight</span><span>Contribution</span></div>{dimension.raw_metrics.map((metric) => <div key={metric.metric_id}><span>{human(metric.metric_id)}</span><span>{number(metric.raw_value, 4)} <small>{metric.raw_unit}</small></span><span>{number(metric.normalized_value, 4)}</span><span>{number(metric.effective_weight, 4)}</span><span>{number(metric.weighted_contribution, 4)}</span></div>)}</div>
      <p className="reason-line">{dimension.reason_codes.map((code) => REASON_LABELS[code] ?? human(code)).join(' ')}</p></details>)}</div>
    <div className="contribution-total"><span>Contribution reconciliation</span><strong>{data.regime.composite.dimensions.map((item) => Number(item.score_contribution ?? 0)).reduce((a, b) => a + b, 0).toFixed(4)} = {number(data.regime.composite.regime_score, 4)}</strong></div>
  </section>;
}

function RelationshipCard({ item, windowSize, onOpen }: { item: Relationship; windowSize: WindowSize; onOpen: () => void }): JSX.Element {
  const metric = item.current.windows.find((row) => row.window_sessions === windowSize) as RelationshipWindow;
  const stronger = metric.relative_return === null ? 'Relative strength unavailable' : `${Number(metric.relative_return) >= 0 ? item.definition.left_ticker : item.definition.right_ticker} was ${Math.abs(Number(metric.relative_return) * 100).toFixed(2)}% relatively stronger over ${windowSize} sessions.`;
  return <button type="button" className="relationship-highlight" title={`Open ${item.definition.left_ticker} / ${item.definition.right_ticker} relationship detail`} onClick={onOpen}><span>{item.definition.left_ticker} / {item.definition.right_ticker}</span><StateMark state={item.current.relationship_state} /><strong>{percent(metric.relative_return)} spread</strong><small>{stronger}</small></button>;
}
function PairDetail({ item, onClose }: { item: Relationship; onClose: () => void }): JSX.Element {
  return <aside className="relationship-drawer" aria-labelledby="pair-detail-title"><div className="detail-header"><div><p className="eyebrow">{human(item.definition.relationship_family)}</p><h2 id="pair-detail-title">{item.definition.left_ticker} / {item.definition.right_ticker}</h2></div><button type="button" onClick={onClose}>Close</button></div>
    <p>{item.definition.economic_rationale}</p><div className="pair-window-detail"><div className="pair-window-head"><span>Window</span><span>{item.definition.left_ticker}</span><span>{item.definition.right_ticker}</span><span>Spread</span><span>Correlation</span></div>{item.current.windows.map((metric) => <div key={metric.window_sessions}><strong>{metric.window_sessions} sessions</strong><span>{percent(metric.left_return)}</span><span>{percent(metric.right_return)}</span><span>{percent(metric.relative_return)}</span><span>{number(metric.rolling_correlation, 3)}</span></div>)}</div>
    <dl className="drawer-stats"><div><dt>Current state</dt><dd>{human(item.current.relationship_state)}</dd></div><div><dt>Reliability</dt><dd>{human(item.current.confidence)} — completeness and rule agreement, not forecast probability</dd></div><div><dt>Correlation change</dt><dd>{signed(item.current.correlation_change_5)}</dd></div><div><dt>Ratio level</dt><dd>{item.current.ratio_level ?? 'Unavailable'}</dd></div><div><dt>Ratio robust-z / percentile</dt><dd>{item.current.ratio_robust_z === null && item.current.ratio_percentile === null ? 'Unavailable — needs at least 60 sessions' : `${item.current.ratio_robust_z ?? 'Unavailable'} / ${item.current.ratio_percentile ?? 'Unavailable'}`}</dd></div></dl>
    <h3>Supporting evidence</h3><ul>{item.explanation.supporting_evidence.map((line) => <li key={line}>{human(line)}</li>)}</ul><h3>Counterevidence</h3>{item.explanation.counterevidence.length ? <ul>{item.explanation.counterevidence.map((line) => <li key={line}>{human(line)}</li>)}</ul> : <p>No fixed-rule counterevidence for the current classification.</p>}
    <details><summary>Reason codes and interpretation boundary</summary><code>{item.current.reason_codes.join(' · ')}</code><p>{item.definition.expected_interpretation}</p><p>{item.definition.forbidden_interpretation}</p></details>
    <div className="drawer-disclaimers"><span>Statistical relationship, not causation.</span><span>Price relationship, not fund flow.</span><span>Research candidate, not trade recommendation.</span></div>
  </aside>;
}

function Relationships({ data }: { data: MarketRegimePreviewResponse }): JSX.Element {
  const initial = requested(); const [windowSize, setWindowSize] = useState<WindowSize>(initial.window); const [family, setFamily] = useState(initial.family); const [stateFilter, setStateFilter] = useState(initial.state); const [scope, setScope] = useState(initial.scope); const [pairId, setPairId] = useState<string | undefined>(initial.pair);
  useEffect(() => { const onPop = () => { const next = requested(); setWindowSize(next.window); setFamily(next.family); setStateFilter(next.state); setScope(next.scope); setPairId(next.pair); }; window.addEventListener('popstate', onPop); return () => window.removeEventListener('popstate', onPop); }, []);
  const families = useMemo(() => [...new Set(data.relationships.map((item) => item.definition.relationship_family))], [data]);
  const states = useMemo(() => [...new Set(data.relationships.map((item) => item.current.relationship_state))], [data]);
  const visible = data.relationships.filter((item) => (family === 'all' || item.definition.relationship_family === family) && (stateFilter === 'all' || item.current.relationship_state === stateFilter) && (scope === 'all' || item.current.relationship_state !== 'neutral'));
  const highlights = [...data.relationships].filter((item) => !['neutral', 'unavailable'].includes(item.current.relationship_state)).sort((a, b) => (STATE_PRIORITY[a.current.relationship_state] - STATE_PRIORITY[b.current.relationship_state]) || a.definition.registry_order - b.definition.registry_order).slice(0, 4);
  const selected = pairId ? data.relationships.find((item) => item.definition.pair_id === pairId) : undefined;
  return <><section className="panel"><div className="section-header"><div><p className="eyebrow">Relationship highlights</p><h2>What changed across preregistered economic pairs</h2></div><p className="section-note">Fixed state priority, then registry order. No return-based pair selection.</p></div><div className="highlight-grid">{highlights.map((item) => <RelationshipCard key={item.definition.pair_id} item={item} windowSize={windowSize} onOpen={() => { setPairId(item.definition.pair_id); updateUrl({ pair: item.definition.pair_id }); }} />)}</div></section>
    <section className="panel"><div className="section-header relationship-header"><div><p className="eyebrow">Complete relationship map</p><h2>All 16 registered pairs</h2></div><div className="window-tabs" aria-label="Relationship window">{([5, 10, 20] as WindowSize[]).map((value) => <button type="button" className={windowSize === value ? 'active' : ''} key={value} onClick={() => { setWindowSize(value); updateUrl({ window: String(value) }); }}>{value} sessions</button>)}</div></div>
      <div className="relationship-filters"><label>Family<select value={family} onChange={(event) => { setFamily(event.target.value); updateUrl({ family: event.target.value }); }}><option value="all">All families</option>{families.map((value) => <option key={value} value={value}>{human(value)}</option>)}</select></label><label>State<select value={stateFilter} onChange={(event) => { setStateFilter(event.target.value); updateUrl({ state: event.target.value }); }}><option value="all">All states</option>{states.map((value) => <option key={value} value={value}>{human(value)}</option>)}</select></label><label className="toggle-filter"><input type="checkbox" checked={scope === 'nonneutral'} onChange={(event) => { const value = event.target.checked ? 'nonneutral' : 'all'; setScope(value); updateUrl({ scope: value }); }} /> Only non-neutral</label><button type="button" onClick={() => { setFamily('all'); setStateFilter('all'); setScope('all'); updateUrl({ family: null, state: null, scope: null }); }}>Clear filters</button></div>
      <div className="relationship-table"><div className="relationship-table-head"><span>Pair / rationale</span><span>{data.relationships[0].definition.left_ticker ? 'Left' : ''}</span><span>Right</span><span>Relative spread</span><span>Correlation</span><span>State / reliability</span></div>{visible.map((item) => <button type="button" className="relationship-row" title={`Open ${item.definition.left_ticker} / ${item.definition.right_ticker} detail`} key={item.definition.pair_id} onClick={() => { setPairId(item.definition.pair_id); updateUrl({ pair: item.definition.pair_id }); }}><span><strong>{item.definition.left_ticker} / {item.definition.right_ticker}</strong><small>{human(item.definition.relationship_family)}</small></span><WindowMetric relationship={item} windowSize={windowSize} /><span><StateMark state={item.current.relationship_state} /><small>{human(item.current.confidence)} reliability{item.explanation.counterevidence.length ? ' · counterevidence' : ''}</small></span></button>)}</div><p className="table-foot">Showing {visible.length} of 16 preregistered pairs. ETF metrics remain identical across Universe selections.</p>
    </section>{selected ? <PairDetail item={selected} onClose={() => { setPairId(undefined); updateUrl({ pair: null }); }} /> : null}</>;
}

function Methodology({ data }: { data: MarketRegimePreviewResponse }): JSX.Element { return <details className="panel methodology"><summary>Methodology, data quality, and diagnostics</summary><div className="method-grid"><div><h3>What this is</h3><p>Five fixed-weight regime dimensions shown beside 16 preregistered ETF relationships over 5, 10, and 20 XNYS sessions.</p><p>Confidence describes data completeness and cross-window rule agreement only.</p></div><div><h3>What this is not</h3><p>Not a market-wide relationship search, causal model, backtest, fund-flow feed, options model, fundamental model, or recommendation.</p><p>Only {data.input_session_count} sessions ({data.input_first_session} to {data.input_last_session}) are available.</p></div><div><h3>Source identity</h3><code>Phase 1a {data.source_logical_fingerprints.phase1a}<br />Phase 1b {data.source_logical_fingerprints.phase1b}<br />Phase 2 {data.source_logical_fingerprints.phase2}</code></div></div>{data.warnings.map((warning) => <p className="quality-copy" key={warning}>• {warning}</p>)}</details>; }

export function MarketRegimeOpportunityMapPage(): JSX.Element {
  const [state, setState] = useState<PageState>({ kind: 'loading' }); const initial = requested(); const [universeId, setUniverseId] = useState(initial.universe);
  const load = useCallback((universe?: string) => { const controller = new AbortController(); setState({ kind: 'loading' }); getMarketRegimePreview(universe, controller.signal).then((data) => { setState({ kind: 'ready', data }); if (universe !== data.selected_universe_id) updateUrl({ universe: data.selected_universe_id }, true); }).catch((error: unknown) => { if (!controller.signal.aborted) setState({ kind: 'error', message: error instanceof Error ? error.message : 'Market Regime preview unavailable' }); }); return () => controller.abort(); }, []);
  useEffect(() => load(universeId), [load, universeId]); useEffect(() => { const onPop = () => setUniverseId(requested().universe); window.addEventListener('popstate', onPop); return () => window.removeEventListener('popstate', onPop); }, []);
  if (state.kind === 'loading') return <main className="app-shell"><div className="panel state-panel">Loading Market Regime preview…</div></main>;
  if (state.kind === 'error') return <main className="app-shell"><div className="panel state-panel error-state" role="alert"><h1>Market Regime preview unavailable</h1><p>{state.message}</p><p>No partial or mixed-version analytics were shown.</p><button type="button" onClick={() => load(universeId)}>Retry</button></div></main>;
  const data = state.data;
  return <main className="app-shell regime-shell"><div className="regime-topbar"><div><span className="brand">WH Alpha · Private research</span><span>Local read-only preview</span></div><label>Universe<select aria-label="Universe" value={data.selected_universe_id} onChange={(event) => { setUniverseId(event.target.value); updateUrl({ universe: event.target.value }); }}>{data.available_universes.map((item) => <option key={item.universe_id} value={item.universe_id}>{item.display_name} · {item.member_count.toLocaleString()}</option>)}</select></label></div><Hero data={data} /><Dimensions data={data} /><Relationships data={data} /><Methodology data={data} /></main>;
}
