import { useCallback, useEffect, useMemo, useState } from 'react';

import { getOpportunityCandidates, type CandidateItem, type CandidateRiskMode, type CandidateStage, type OpportunityCandidateResponse } from '../api/opportunityCandidates';
import { useI18n, type Translate } from '../i18n/I18nProvider';
import { localizeClientError, universeName } from '../i18n/domain';

type LoadState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; data: OpportunityCandidateResponse };
type StageFilter = 'active' | CandidateStage | 'all';
const PRIMARY = 'provider_classified_common_shares_v1';
const MODES: CandidateRiskMode[] = ['conservative', 'balanced', 'aggressive'];

function requestedUniverse(): string { return new URLSearchParams(window.location.search).get('universe') ?? PRIMARY; }
function requestedMode(): CandidateRiskMode { const value = new URLSearchParams(window.location.search).get('candidateRisk'); return MODES.includes(value as CandidateRiskMode) ? value as CandidateRiskMode : 'balanced'; }
function writeQuery(key: string, value: string): void { const url = new URL(window.location.href); url.searchParams.set(key, value); window.history.pushState(window.history.state, '', url); }
function stageName(t: Translate, stage: CandidateStage | null): string {
  if (stage === 'watch') return t('candidate.stage.watch'); if (stage === 'prepare') return t('candidate.stage.prepare');
  if (stage === 'enter') return t('candidate.stage.enter'); if (stage === 'invalidated') return t('candidate.stage.invalidated');
  return t('candidate.stage.unavailable');
}
function componentName(t: Translate, id: string): string {
  const names: Record<string, ReturnType<Translate>> = {
    market_alignment: t('candidate.component.market'), etf_sector_alignment: t('candidate.component.etf'),
    stock_relative_strength: t('candidate.component.relative'), trend_quality: t('candidate.component.trend'),
    volume_participation: t('candidate.component.volume'), volatility_risk: t('candidate.component.volatility'),
    liquidity_suitability: t('candidate.component.liquidity'),
  }; return names[id] ?? id;
}
function percent(value: string | null): string { return value === null ? '—' : `${(Number(value) * 100).toFixed(1)}%`; }
function number(value: string | null, digits = 1): string { return value === null ? '—' : Number(value).toLocaleString('en-US', { maximumFractionDigits: digits }); }
function money(value: string | null): string {
  if (value === null) return '—'; const amount = Number(value);
  if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`; return `$${amount.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

function CandidateDetail({ item, mode, onClose }: { item: CandidateItem; mode: CandidateRiskMode; onClose: () => void }): JSX.Element {
  const { t } = useI18n(); const disposition = item.risk_dispositions.find((row) => row.risk_mode === mode);
  const supports = item.evidence.filter((row) => row.evidence_kind === 'supporting'); const counters = item.evidence.filter((row) => row.evidence_kind === 'counterevidence');
  useEffect(() => { const key = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); }; window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key); }, [onClose]);
  return <div className="candidate-drawer-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}><aside className="candidate-drawer" role="dialog" aria-modal="true" aria-labelledby="candidate-detail-title">
    <header><div><p className="eyebrow">{t('candidate.detailEyebrow')}</p><h2 id="candidate-detail-title">{item.ticker} · {stageName(t, item.state.final_stage)}</h2><p>{item.instrument_id} · {item.security_type}</p></div><button type="button" onClick={onClose} aria-label={t('common.close')}>×</button></header>
    <div className="candidate-detail-summary"><div><span>{t('candidate.baseScore')}</span><strong>{number(item.base_score)}</strong></div><div><span>{t('candidate.dataSupport')}</span><strong>{percent(item.confidence.confidence)}</strong></div><div><span>{t('candidate.formalRank')}</span><strong>{disposition?.risk_adjusted_rank ?? '—'}</strong></div><div><span>{t('candidate.latestPrice')}</span><strong>${number(item.latest_price, 2)}</strong></div></div>
    <p className="candidate-boundary">{t('candidate.researchBoundary')}</p>
    <section><h3>{t('candidate.contributionTitle')}</h3><div className="candidate-contributions">{item.components.map((component) => <div key={component.component_id}><span>{componentName(t, component.component_id)}</span><div><i style={{ width: `${Math.max(0, Math.min(100, Number(component.score ?? 0)))}%` }} /></div><strong>{component.contribution ?? '—'}</strong></div>)}</div></section>
    <section className="candidate-evidence-grid"><div><h3>{t('candidate.supporting')}</h3>{supports.map((row) => <p key={`${row.evidence_id}-${row.component_id}`}>+ {componentName(t, row.component_id)}{row.observed_value ? ` · ${row.observed_value}` : ''}</p>)}</div><div><h3>{t('candidate.counter')}</h3>{counters.map((row) => <p key={`${row.evidence_id}-${row.component_id}`}>− {componentName(t, row.component_id)}{row.observed_value ? ` · ${row.observed_value}` : ''}</p>)}</div></section>
    <section><h3>{t('candidate.invalidation')}</h3><ul>{item.invalidation_condition_codes.map((code) => <li key={code}>{t(`candidate.invalidation.${code}` as never)}</li>)}</ul></section>
    <section><h3>{t('candidate.rawFacts')}</h3><div className="candidate-facts"><span>{t('candidate.liquidity')} <strong>{money(item.median_dollar_volume_20)}</strong></span><span>{t('candidate.volatility')} <strong>{percent(item.annualized_volatility_10)}</strong></span><span>{t('candidate.maxGap')} <strong>{percent(item.maximum_absolute_open_gap_5)}</strong></span><span>{t('candidate.volumeRatio')} <strong>{number(item.current_volume_ratio, 2)}×</strong></span><span>{t('candidate.etfProxy')} <strong>{item.primary_driver_ticker ?? '—'}</strong></span><span>{t('common.correlation')} <strong>{number(item.driver_correlation_20, 2)}</strong></span></div></section>
    <section><h3>{t('candidate.manualChecks')}</h3><p>{t('candidate.manualChecksBody')}</p></section>
  </aside></div>;
}

export function OpportunityCandidatesPage(): JSX.Element {
  const { t } = useI18n(); const [universe, setUniverse] = useState(requestedUniverse); const [mode, setMode] = useState<CandidateRiskMode>(requestedMode);
  const [state, setState] = useState<LoadState>({ kind: 'loading' }); const [stage, setStage] = useState<StageFilter>('active'); const [search, setSearch] = useState(''); const [selected, setSelected] = useState<CandidateItem | null>(null);
  const load = useCallback((universeId: string) => { const controller = new AbortController(); setState({ kind: 'loading' }); setSelected(null); getOpportunityCandidates(universeId, controller.signal).then((data) => setState({ kind: 'ready', data })).catch((error: unknown) => { if (!controller.signal.aborted) setState({ kind: 'error', message: error instanceof Error ? error.message : '' }); }); return () => controller.abort(); }, []);
  useEffect(() => load(universe), [load, universe]); useEffect(() => { const pop = () => { setUniverse(requestedUniverse()); setMode(requestedMode()); }; window.addEventListener('popstate', pop); return () => window.removeEventListener('popstate', pop); }, []);
  const rows = useMemo(() => { if (state.kind !== 'ready') return []; const result = state.data.universe.risk_modes.find((row) => row.risk_mode === mode); const order = new Map((result?.displayed_instrument_ids ?? []).map((id, index) => [id, index + 1])); return state.data.universe.candidates.filter((item) => {
    if (stage === 'active') return order.has(item.instrument_id) && ['watch', 'prepare', 'enter'].includes(item.state.final_stage ?? '');
    if (stage === 'all') return true;
    return item.state.final_stage === stage;
  }).filter((item) => item.ticker.toLowerCase().includes(search.trim().toLowerCase())).sort((a, b) => (order.get(a.instrument_id) ?? Number.MAX_SAFE_INTEGER) - (order.get(b.instrument_id) ?? Number.MAX_SAFE_INTEGER) || Number(b.base_score ?? 0) - Number(a.base_score ?? 0)); }, [mode, search, stage, state]);
  if (state.kind === 'loading') return <main className="app-shell candidate-shell"><div className="panel state-panel">{t('candidate.loading')}</div></main>;
  if (state.kind === 'error') return <main className="app-shell candidate-shell"><div className="panel state-panel error-state" role="alert"><h1>{t('candidate.unavailable')}</h1><p>{localizeClientError(t, state.message)}</p><p>{t('candidate.failClosed')}</p><button type="button" onClick={() => load(universe)}>{t('common.retry')}</button></div></main>;
  const data = state.data; const risk = data.universe.risk_modes.find((row) => row.risk_mode === mode)!;
  return <main className="app-shell candidate-shell"><section className="candidate-hero"><p className="eyebrow">{t('candidate.eyebrow')}</p><h1>{t('candidate.title')}</h1><p>{t('candidate.subtitle')}</p><div className="candidate-hero-facts"><span>{t('common.asOf')} <strong>{data.as_of_session}</strong></span><span>{universeName(t, data.selected_universe_id)} <strong>{data.universe.universe_member_count.toLocaleString('en-US')}</strong></span><span>{t('candidate.eligible')} <strong>{risk.eligible_count}</strong></span><span>{t('candidate.displayed')} <strong>{rows.length}</strong></span></div></section>
    <section className="panel candidate-control-panel"><div className="candidate-risk-tabs" aria-label={t('candidate.riskMode')}>{MODES.map((value) => <button type="button" className={mode === value ? 'active' : ''} key={value} onClick={() => { setMode(value); writeQuery('candidateRisk', value); }}>{t(`candidate.risk.${value}` as never)}</button>)}</div><p>{t('candidate.riskExplanation')}</p><div className="candidate-filters"><label>{t('common.state')}<select value={stage} onChange={(event) => setStage(event.target.value as StageFilter)}><option value="active">{t('candidate.filter.active')}</option><option value="watch">{t('candidate.stage.watch')}</option><option value="prepare">{t('candidate.stage.prepare')}</option><option value="enter">{t('candidate.stage.enter')}</option><option value="invalidated">{t('candidate.stage.invalidated')}</option><option value="all">{t('candidate.filter.all')}</option></select></label><label>{t('candidate.search')}<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="AAPL" /></label></div></section>
    <section className="panel candidate-summary"><h2>{t('candidate.currentState')}</h2><div><span>{t('candidate.stage.watch')} <strong>{data.universe.stage_counts.watch ?? 0}</strong></span><span>{t('candidate.stage.prepare')} <strong>{data.universe.stage_counts.prepare ?? 0}</strong></span><span>{t('candidate.stage.enter')} <strong>{data.universe.stage_counts.enter ?? 0}</strong></span><span>{t('candidate.stage.invalidated')} <strong>{data.universe.stage_counts.invalidated ?? 0}</strong></span><span>{t('candidate.manualReview')} <strong>{data.universe.stage_counts.unavailable ?? 0}</strong></span></div><p>{t('candidate.shortHistory')}</p></section>
    <section className="panel candidate-board"><div className="candidate-table-head"><span>{t('candidate.rank')}</span><span>{t('candidate.symbol')}</span><span>{t('common.state')}</span><span>{t('candidate.baseScore')}</span><span>{t('candidate.dataSupport')}</span><span>{t('candidate.etfProxy')}</span><span>{t('candidate.liquidity')}</span><span>{t('candidate.quality')}</span></div>{rows.map((item) => { const disposition = item.risk_dispositions.find((row) => row.risk_mode === mode)!; return <button type="button" className="candidate-row" key={item.instrument_id} onClick={() => setSelected(item)}><strong>{disposition.risk_adjusted_rank ? `#${disposition.risk_adjusted_rank}` : '—'}</strong><span><strong>{item.ticker}</strong><small>{item.security_type}</small></span><span className={`candidate-stage candidate-stage-${item.state.final_stage ?? 'unavailable'}`}>{stageName(t, item.state.final_stage)}</span><strong>{number(item.base_score)}</strong><span>{percent(item.confidence.confidence)}</span><span>{item.primary_driver_ticker ?? '—'}<small>{t('candidate.priceProxyShort')}</small></span><span>{money(item.median_dollar_volume_20)}</span><span>{t(`candidate.quality.${item.data_quality_status}` as never)}</span></button>; })}{rows.length === 0 ? <div className="candidate-empty"><h3>{t('candidate.empty')}</h3><p>{t('candidate.emptyBody')}</p></div> : null}</section>
    <details className="panel methodology"><summary>{t('candidate.methodTitle')}</summary><p>{t('candidate.methodBody')}</p><code>{data.logical_fingerprint}</code></details>
    {selected ? <CandidateDetail item={selected} mode={mode} onClose={() => setSelected(null)} /> : null}
  </main>;
}
