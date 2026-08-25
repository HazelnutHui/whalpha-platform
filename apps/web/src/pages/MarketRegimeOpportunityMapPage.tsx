import { useCallback, useEffect, useMemo, useState } from 'react';

import { getMarketRegimePreview, type MarketRegimePreviewResponse, type RegimeDimension, type Relationship, type RelationshipWindow } from '../api/marketRegime';

type PageState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; data: MarketRegimePreviewResponse };
type WindowSize = 5 | 10 | 20;
type EvidenceTone = 'support' | 'neutral' | 'drag';

const STATE_PRIORITY: Record<string, number> = {
  relationship_break_candidate: 0, rotation_candidate: 1, divergence: 2,
  synchronous_weakening: 3, synchronous_strengthening: 4, neutral: 5, unavailable: 6,
};
const DIMENSION_LABELS: Record<string, string> = {
  trend: 'Trend', breadth: 'Breadth', volatility: 'Volatility environment',
  liquidity_participation: 'Liquidity / Participation', leadership_dispersion: 'Leadership / Dispersion',
};
const DIMENSION_SHORT_LABELS: Record<string, string> = {
  trend: 'Trend', breadth: 'Breadth', volatility: 'Volatility',
  liquidity_participation: 'Participation', leadership_dispersion: 'Leadership / Dispersion',
};
const REASON_LABELS: Record<string, string> = {
  candidate_band_balanced: 'The Composite remains inside the fixed Balanced range.',
  confirmed_state_held: 'The confirmed state held under the fixed hysteresis rules.',
  state_input_available: 'All critical state inputs are available.',
  short_history_low_confidence: 'Only 26 sessions are available, so reliability remains low.',
  short_history_limits_reliability: 'Short history limits how much weight to place on this relationship.',
  both_five_session_returns_negative: 'Both ETFs declined over the 5-session window.',
  both_five_session_returns_positive: 'Both ETFs advanced over the 5-session window.',
  positive_correlation_threshold_met: 'The fixed positive-correlation rule was met.',
  five_session_spread_threshold_met: 'The 5-session relative-performance spread crossed its fixed threshold.',
  opposite_return_signs: 'The two ETFs moved in opposite directions over 5 sessions.',
  relative_strength_direction_differs_across_windows: 'Relative leadership is not consistent across 5, 10, and 20 sessions.',
  correlation_threshold_not_stable_across_18_20_22_windows: 'Correlation is sensitive to small changes in the lookback window.',
  no_higher_priority_relationship_rule_met: 'No higher-priority fixed relationship rule was triggered.',
  confidence_low: 'Reliability is low because the available history is short.',
  dimension_available: 'The dimension passed its input and availability checks.',
};
const STATE_SUMMARIES: Record<string, string> = {
  risk_on: 'Broadly constructive', balanced: 'Mixed but constructive', defensive: 'Defensive conditions', stress: 'Market stress',
};

function human(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (item: string) => item.toUpperCase());
}
function number(value: string | null, digits = 2): string {
  return value === null ? 'Unavailable' : Number(value).toFixed(digits);
}
function score(value: string | null): string { return number(value, 1); }
function contribution(value: string | null): string { return value === null ? 'Unavailable' : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(2)} pts`; }
function weight(value: string): string { return `${Number(value).toFixed(Number(value) % 1 === 0 ? 0 : 1)}%`; }
function percent(value: string | null): string {
  return value === null ? 'Unavailable' : `${Number(value) >= 0 ? '+' : ''}${(Number(value) * 100).toFixed(2)}%`;
}
function percentagePoints(value: string | null): string {
  return value === null ? 'Unavailable' : `${Math.abs(Number(value) * 100).toFixed(2)} percentage points`;
}
function signed(value: string | null, digits = 2): string {
  return value === null ? 'Unavailable' : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(digits)}`;
}
function reasonText(value: string): string { return REASON_LABELS[value] ?? human(value); }
function sentenceList(values: string[]): string {
  if (values.length === 0) return 'No dimensions';
  if (values.length === 1) return values[0];
  return `${values.slice(0, -1).join(', ')} and ${values[values.length - 1]}`;
}
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
function StateMark({ state }: { state: string | null }): JSX.Element {
  return <span className={`regime-state state-${state ?? 'unavailable'}`}><i aria-hidden="true" />{state ? human(state) : 'Unavailable'}</span>;
}
function metricFor(item: Relationship, windowSize: WindowSize): RelationshipWindow {
  return item.current.windows.find((metric) => metric.window_sessions === windowSize) as RelationshipWindow;
}
function directionSentence(metric: RelationshipWindow, windowSize: WindowSize): string {
  if (metric.left_return === null || metric.right_return === null) return `The ${windowSize}-session comparison is unavailable.`;
  const left = Number(metric.left_return); const right = Number(metric.right_return);
  if (left < 0 && right < 0) return `Both ETFs declined over ${windowSize} sessions.`;
  if (left > 0 && right > 0) return `Both ETFs advanced over ${windowSize} sessions.`;
  if (left > 0 && right < 0) return `The left ETF advanced while the right ETF declined over ${windowSize} sessions.`;
  if (left < 0 && right > 0) return `The left ETF declined while the right ETF advanced over ${windowSize} sessions.`;
  return `The two ETFs were mixed around flat over ${windowSize} sessions.`;
}
function relativeSentence(item: Relationship, metric: RelationshipWindow): string {
  if (metric.relative_return === null) return 'Relative performance is unavailable.';
  const leftLeads = Number(metric.relative_return) >= 0;
  const leader = leftLeads ? item.definition.left_ticker : item.definition.right_ticker;
  const laggard = leftLeads ? item.definition.right_ticker : item.definition.left_ticker;
  const bothNegative = metric.left_return !== null && metric.right_return !== null && Number(metric.left_return) < 0 && Number(metric.right_return) < 0;
  return `${leader} ${bothNegative ? 'held up' : 'performed'} ${percentagePoints(metric.relative_return)} better than ${laggard}.`;
}
function crossWindowSentence(item: Relationship): string {
  const available = item.current.windows.filter((metric) => metric.relative_return !== null);
  if (available.length !== 3) return 'Cross-window relative strength is incomplete.';
  const signs = available.map((metric) => Math.sign(Number(metric.relative_return)));
  if (signs.every((value) => value >= 0)) return `${item.definition.left_ticker} leads ${item.definition.right_ticker} across 5, 10, and 20 sessions.`;
  if (signs.every((value) => value <= 0)) return `${item.definition.right_ticker} leads ${item.definition.left_ticker} across 5, 10, and 20 sessions.`;
  return 'Relative leadership changes across 5, 10, and 20 sessions.';
}
function dimensionTone(data: MarketRegimePreviewResponse, dimensionId: string): EvidenceTone {
  if (data.regime.current_state.conflicting_dimension_ids.includes(dimensionId)) return 'drag';
  if (data.regime.current_state.supporting_dimension_ids.includes(dimensionId)) return 'support';
  return 'neutral';
}
function dimensionCopy(dimension: RegimeDimension, tone: EvidenceTone): string {
  if (dimension.dimension_id === 'volatility') return 'Realized volatility conditions are supportive; this is not a claim that volatility itself is high.';
  if (dimension.dimension_id === 'liquidity_participation') return tone === 'drag' ? 'Participation is the main drag; price × volume is a participation proxy, not fund flow.' : 'Participation is mixed and remains a price-and-volume proxy, not fund flow.';
  if (dimension.dimension_id === 'leadership_dispersion') return 'Leadership breadth supports the reading; it does not imply current leaders will keep rising.';
  if (dimension.dimension_id === 'breadth') return tone === 'support' ? 'More members support the market direction.' : tone === 'drag' ? 'Member-level breadth is holding back the reading.' : 'Member-level breadth is mixed rather than decisive.';
  return tone === 'support' ? 'Medium-term trend remains supportive.' : tone === 'drag' ? 'Trend is holding back the current reading.' : 'Trend evidence is mixed.';
}

function Hero({ data }: { data: MarketRegimePreviewResponse }): JSX.Element {
  const state = data.regime.current_state; const confirmed = state.confirmed_state ?? 'unavailable';
  const candidateDiffers = state.instantaneous_candidate_state !== null && state.instantaneous_candidate_state !== state.confirmed_state;
  const support = state.supporting_dimension_ids.map((item) => DIMENSION_SHORT_LABELS[item]);
  const conflict = state.conflicting_dimension_ids.map((item) => DIMENSION_SHORT_LABELS[item]);
  const riskOnDistance = state.threshold_distances.find((item) => item.threshold_id === 'balanced_to_risk_on');
  const defensiveDistance = state.threshold_distances.find((item) => item.threshold_id === 'balanced_to_defensive');
  const transitionCopy = confirmed === 'balanced' && riskOnDistance && defensiveDistance
    ? `Risk-on confirmation is ${Math.abs(Number(riskOnDistance.signed_distance)).toFixed(1)} points away; Defensive conditions are not pending.`
    : state.pending_target_state ? `${human(state.pending_target_state)} is pending with ${state.confirmation_sessions_remaining} confirmation session${state.confirmation_sessions_remaining === 1 ? '' : 's'} remaining.`
      : 'No regime transition is currently pending.';
  return <section className="regime-hero panel">
    <div className="hero-heading"><p className="eyebrow">Market regime · Frozen local preview</p><h1>Market Regime &amp; Opportunity Map</h1></div>
    <div className="hero-state-block"><span className="hero-label">Confirmed state</span><div className={`hero-state state-text-${confirmed}`}><i aria-hidden="true" />{human(confirmed)}</div><strong>{STATE_SUMMARIES[confirmed] ?? 'State unavailable'}</strong></div>
    <div className="hero-composite" data-exact-value={data.regime.composite.regime_score ?? undefined}><span>Composite</span><strong>{score(data.regime.composite.regime_score)} <small>/ 100</small></strong><p>{candidateDiffers ? <>Candidate: <b>{human(state.instantaneous_candidate_state as string)}</b></> : 'Candidate matches the confirmed state.'}</p></div>
    <div className="hero-evidence"><div className="evidence-callout evidence-support"><span>What supports it</span><strong>{sentenceList(support)}</strong><small>{support.length ? 'Trend and risk conditions remain constructive.' : 'No supporting dimension is available.'}</small></div><div className="evidence-callout evidence-drag"><span>What holds it back</span><strong>{sentenceList(conflict)}</strong><small>{conflict.length ? 'Participation is not confirming the stronger dimensions.' : 'No material drag is present.'}</small></div></div>
    <div className="hero-transition"><span>{transitionCopy}</span><small>Fixed thresholds and hysteresis; no dynamic adjustment.</small></div>
    <div className="regime-hero-meta"><span>As of <b>{data.as_of_session}</b></span><span>Universe <b>{data.regime.definition.display_name}</b></span><span className="short-history-chip">26-session preview</span><span>Research context, not a trade recommendation.</span></div>
  </section>;
}

function Dimensions({ data }: { data: MarketRegimePreviewResponse }): JSX.Element {
  const exactTotal = data.regime.composite.dimensions.map((item) => Number(item.score_contribution ?? 0)).reduce((a, b) => a + b, 0).toFixed(4);
  return <section className="panel dimensions-panel" aria-labelledby="dimensions-title"><div className="section-header compact"><div><p className="eyebrow">Regime drivers</p><h2 id="dimensions-title">What supports the market—and what holds it back</h2></div><p className="section-note">The Composite is the transparent weighted sum of these five dimensions.</p></div>
    <div className="dimension-grid">{data.regime.composite.dimensions.map((dimension) => {
      const tone = dimensionTone(data, dimension.dimension_id); const width = Math.max(0, Math.min(100, Number(dimension.score ?? 0)));
      return <details className={`dimension-card tone-${tone}`} key={dimension.dimension_id}><summary>
        <span className="dimension-name">{DIMENSION_LABELS[dimension.dimension_id]}</span><span className={`evidence-tag evidence-${tone}`}>{human(tone)}</span>
        <strong>{score(dimension.score)}</strong><div className="dimension-bar" aria-label={`${DIMENSION_LABELS[dimension.dimension_id]} score ${score(dimension.score)} out of 100`}><i style={{ width: `${width}%` }} /></div>
        <p>{dimensionCopy(dimension, tone)}</p><small>Weight {weight(dimension.effective_weight)} <b>·</b> Contribution {contribution(dimension.score_contribution)}</small><span className="audit-link">View calculation</span>
      </summary><div className="dimension-audit"><p>{dimension.rendered_explanation}</p><div className="metric-ledger"><div className="metric-ledger-head"><span>Metric</span><span>Raw</span><span>Normalized</span><span>Configured / effective weight</span><span>Contribution</span></div>{dimension.raw_metrics.map((metric) => <div key={metric.metric_id}><span>{human(metric.metric_id)}</span><span>{number(metric.raw_value, 4)} <small>{metric.raw_unit}</small></span><span>{number(metric.normalized_value, 4)}</span><span>{number(metric.configured_weight, 4)} / {number(metric.effective_weight, 4)}</span><span>{number(metric.weighted_contribution, 4)}</span></div>)}</div><p className="reason-line"><b>Reason codes:</b> {dimension.reason_codes.join(' · ')} — {dimension.reason_codes.map(reasonText).join(' ')}</p></div></details>;
    })}</div>
    <details className="contribution-audit"><summary>Calculation audit</summary><div><span>Exact contribution reconciliation</span><strong>{exactTotal} = {number(data.regime.composite.regime_score, 4)}</strong><span>Configured/effective weights and high-precision Decimal values are shown inside each dimension. Regime adjustment remains fixed at 0.</span></div></details>
  </section>;
}

function RelationshipCard({ item, windowSize, onOpen }: { item: Relationship; windowSize: WindowSize; onOpen: () => void }): JSX.Element {
  const metric = metricFor(item, windowSize);
  return <button type="button" className="relationship-highlight" title={`Open ${item.definition.left_ticker} / ${item.definition.right_ticker} relationship detail`} onClick={onOpen}>
    <span className="highlight-family">{item.definition.economic_rationale}</span><div className="highlight-title"><strong>{item.definition.left_ticker} / {item.definition.right_ticker}</strong><StateMark state={item.current.relationship_state} /></div>
    <div className="highlight-returns"><span><small>{item.definition.left_ticker}</small><b>{percent(metric.left_return)}</b></span><span><small>{item.definition.right_ticker}</small><b>{percent(metric.right_return)}</b></span><span className="highlight-spread"><small>Relative spread</small><b>{percent(metric.relative_return)}</b></span></div>
    <p>{directionSentence(metric, windowSize)} {relativeSentence(item, metric)}</p>
  </button>;
}
function WindowMetric({ relationship, windowSize }: { relationship: Relationship; windowSize: WindowSize }): JSX.Element {
  const metric = metricFor(relationship, windowSize);
  return <><span className="return-cell"><small>{relationship.definition.left_ticker}</small><b className={metric.left_return && Number(metric.left_return) >= 0 ? 'positive-text' : 'negative-text'}>{percent(metric.left_return)}</b></span><span className="return-cell"><small>{relationship.definition.right_ticker}</small><b className={metric.right_return && Number(metric.right_return) >= 0 ? 'positive-text' : 'negative-text'}>{percent(metric.right_return)}</b></span><span className="spread-cell"><small>Spread</small><strong>{percent(metric.relative_return)}</strong></span><span className="correlation-cell"><small>Correlation</small><b>{number(metric.rolling_correlation, 2)}</b></span></>;
}
function PairDetail({ item, windowSize, onClose }: { item: Relationship; windowSize: WindowSize; onClose: () => void }): JSX.Element {
  const metric = metricFor(item, windowSize);
  return <aside className="relationship-drawer" role="dialog" aria-modal="false" aria-labelledby="pair-detail-title"><div className="detail-header"><div><p className="eyebrow">{human(item.definition.relationship_family)}</p><h2 id="pair-detail-title">{item.definition.left_ticker} / {item.definition.right_ticker}</h2><p>{item.definition.economic_rationale}</p></div><button className="drawer-close" type="button" onClick={onClose} aria-label={`Close ${item.definition.left_ticker} / ${item.definition.right_ticker} details`}><span aria-hidden="true">×</span> Close</button></div>
    <div className="drawer-observation"><span>Current read · {windowSize} sessions</span><strong>{directionSentence(metric, windowSize)}</strong><strong>{relativeSentence(item, metric)}</strong><p>{crossWindowSentence(item)} Short history limits reliability.</p></div>
    <div className="drawer-summary"><div><span>Relationship state</span><StateMark state={item.current.relationship_state} /></div><div><span>Relative result</span><strong>{percent(metric.relative_return)}</strong><small>{Number(metric.relative_return ?? 0) >= 0 ? item.definition.left_ticker : item.definition.right_ticker} leads</small></div><div><span>Reliability</span><strong>{human(item.current.confidence)}</strong><small>Completeness and rule agreement—not forecast probability.</small></div></div>
    <div className="pair-window-detail"><div className="pair-window-head"><span>Window</span><span>{item.definition.left_ticker}</span><span>{item.definition.right_ticker}</span><span>Spread</span><span>Correlation</span></div>{item.current.windows.map((row) => <div className={row.window_sessions === windowSize ? 'selected-window' : ''} key={row.window_sessions}><strong>{row.window_sessions} sessions</strong><span>{percent(row.left_return)}</span><span>{percent(row.right_return)}</span><span>{percent(row.relative_return)}</span><span>{number(row.rolling_correlation, 2)}</span></div>)}</div>
    <div className="evidence-columns"><section><h3>Supporting evidence</h3><ul>{item.explanation.supporting_evidence.map((line) => <li key={line}>{reasonText(line)}</li>)}</ul></section><section><h3>Counterevidence</h3>{item.explanation.counterevidence.length ? <ul>{item.explanation.counterevidence.map((line) => <li key={line}>{reasonText(line)}</li>)}</ul> : <p>No fixed-rule counterevidence for the current classification.</p>}</section></div>
    <details className="technical-diagnostics"><summary>Technical diagnostics and interpretation boundary</summary><dl className="drawer-stats"><div><dt>Correlation change</dt><dd>{signed(item.current.correlation_change_5, 2)}</dd></div><div><dt>Price-ratio level</dt><dd>{number(item.current.ratio_level, 3)}</dd></div><div><dt>Ratio robust-z / percentile</dt><dd>{item.current.ratio_robust_z === null && item.current.ratio_percentile === null ? 'Unavailable — needs at least 60 sessions' : `${number(item.current.ratio_robust_z, 2)} / ${number(item.current.ratio_percentile, 2)}`}</dd></div></dl><p><b>Reason codes:</b> {item.current.reason_codes.join(' · ')}</p><p>{item.definition.expected_interpretation}</p><p>{item.definition.forbidden_interpretation}</p></details>
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
  return <><section className="panel highlights-panel"><div className="section-header compact"><div><p className="eyebrow">Relationship highlights · {windowSize} sessions</p><h2>Where the market’s internal relationships disagree</h2></div><details className="highlight-method"><summary>How highlights are selected</summary><p>Non-neutral states appear first using the fixed state priority and preregistered pair order. Returns do not select or rank pairs.</p></details></div><div className="highlight-grid">{highlights.map((item) => <RelationshipCard key={item.definition.pair_id} item={item} windowSize={windowSize} onOpen={() => { setPairId(item.definition.pair_id); updateUrl({ pair: item.definition.pair_id }); }} />)}</div></section>
    <section className="panel relationship-map-panel"><div className="section-header relationship-header"><div><p className="eyebrow">Complete relationship map</p><h2>All 16 preregistered pairs</h2></div><div className="window-tabs" aria-label="Relationship window">{([5, 10, 20] as WindowSize[]).map((value) => <button type="button" className={windowSize === value ? 'active' : ''} key={value} onClick={() => { setWindowSize(value); updateUrl({ window: String(value) }); }}>{value} sessions</button>)}</div></div>
      <div className="relationship-filters"><label>Family<select value={family} onChange={(event) => { setFamily(event.target.value); updateUrl({ family: event.target.value }); }}><option value="all">All families</option>{families.map((value) => <option key={value} value={value}>{human(value)}</option>)}</select></label><label>State<select value={stateFilter} onChange={(event) => { setStateFilter(event.target.value); updateUrl({ state: event.target.value }); }}><option value="all">All states</option>{states.map((value) => <option key={value} value={value}>{human(value)}</option>)}</select></label><label className="toggle-filter"><input type="checkbox" checked={scope === 'nonneutral'} onChange={(event) => { const value = event.target.checked ? 'nonneutral' : 'all'; setScope(value); updateUrl({ scope: value }); }} /> Only non-neutral</label><button type="button" onClick={() => { setFamily('all'); setStateFilter('all'); setScope('all'); updateUrl({ family: null, state: null, scope: null }); }}>Clear filters</button></div>
      <div className="relationship-table"><div className="relationship-table-head"><span>Pair / economic relationship</span><span>Left return</span><span>Right return</span><span>Relative result</span><span>Co-movement</span><span>Relationship state</span></div>{visible.map((item) => <button type="button" className="relationship-row" title={`Open ${item.definition.left_ticker} / ${item.definition.right_ticker} detail`} key={item.definition.pair_id} onClick={() => { setPairId(item.definition.pair_id); updateUrl({ pair: item.definition.pair_id }); }}><span className="pair-identity"><strong>{item.definition.left_ticker} / {item.definition.right_ticker}</strong><small>{item.definition.economic_rationale}</small></span><WindowMetric relationship={item} windowSize={windowSize} /><span className="relationship-state-cell"><StateMark state={item.current.relationship_state} /><small>{human(item.current.confidence)} reliability</small>{item.explanation.counterevidence.length ? <em>Evidence caveat</em> : null}</span></button>)}</div><p className="table-foot">Showing {visible.length} of 16 preregistered pairs. ETF metrics remain identical across Universe selections.</p>
    </section>{selected ? <PairDetail item={selected} windowSize={windowSize} onClose={() => { setPairId(undefined); updateUrl({ pair: null }); }} /> : null}</>;
}

function Methodology({ data }: { data: MarketRegimePreviewResponse }): JSX.Element {
  return <details className="panel methodology"><summary>Methodology, safeguards, and source diagnostics</summary><div className="method-grid"><div><h3>Fixed, preregistered scope</h3><p>Five fixed-weight regime dimensions sit beside 16 preregistered ETF relationships over 5, 10, and 20 XNYS sessions.</p><p>Highlights use fixed state priority and registry order—not return-based selection.</p></div><div><h3>Interpretation boundaries</h3><p>Correlation is not causation. Price relationships are not fund flow. Confidence describes completeness and rule agreement, not forecast probability.</p><p>This is research context, not a backtest or trade recommendation.</p></div><div><h3>Short-history boundary</h3><p>Only {data.input_session_count} sessions ({data.input_first_session} to {data.input_last_session}) are available. Ratio robust-z and percentile require at least 60 sessions.</p></div><div><h3>Source identity</h3><code>Phase 1a {data.source_logical_fingerprints.phase1a}<br />Phase 1b {data.source_logical_fingerprints.phase1b}<br />Phase 2 {data.source_logical_fingerprints.phase2}</code></div></div>{data.warnings.map((warning) => <p className="quality-copy" key={warning}>• {warning}</p>)}</details>;
}

export function MarketRegimeOpportunityMapPage(): JSX.Element {
  const [state, setState] = useState<PageState>({ kind: 'loading' }); const initial = requested(); const [universeId, setUniverseId] = useState(initial.universe);
  const load = useCallback((universe?: string) => { const controller = new AbortController(); setState({ kind: 'loading' }); getMarketRegimePreview(universe, controller.signal).then((data) => { setState({ kind: 'ready', data }); if (universe !== data.selected_universe_id) updateUrl({ universe: data.selected_universe_id }, true); }).catch((error: unknown) => { if (!controller.signal.aborted) setState({ kind: 'error', message: error instanceof Error ? error.message : 'Market Regime preview unavailable' }); }); return () => controller.abort(); }, []);
  useEffect(() => load(universeId), [load, universeId]); useEffect(() => { const onPop = () => setUniverseId(requested().universe); window.addEventListener('popstate', onPop); return () => window.removeEventListener('popstate', onPop); }, []);
  if (state.kind === 'loading') return <main className="app-shell"><div className="panel state-panel">Loading Market Regime preview…</div></main>;
  if (state.kind === 'error') return <main className="app-shell"><div className="panel state-panel error-state" role="alert"><h1>Market Regime preview unavailable</h1><p>{state.message}</p><p>No partial or mixed-version analytics were shown.</p><button type="button" onClick={() => load(universeId)}>Retry</button></div></main>;
  const data = state.data;
  return <main className="app-shell regime-shell"><div className="regime-topbar"><div><span className="brand">WH Alpha · Private research</span><span>Local read-only preview</span></div><label>Universe<select aria-label="Universe" value={data.selected_universe_id} onChange={(event) => { setUniverseId(event.target.value); updateUrl({ universe: event.target.value }); }}>{data.available_universes.map((item) => <option key={item.universe_id} value={item.universe_id}>{item.display_name} · {item.member_count.toLocaleString()}</option>)}</select></label></div><Hero data={data} /><Dimensions data={data} /><Relationships data={data} /><Methodology data={data} /></main>;
}
