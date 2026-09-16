import { useCallback, useEffect, useMemo, useState } from 'react';

import { getMarketRegimePreview, type MarketRegimePreviewResponse, type RegimeDimension, type Relationship, type RelationshipWindow } from '../api/marketRegime';
import { useI18n, type Translate } from '../i18n/I18nProvider';
import {
  confidenceName, dimensionAuditText, dimensionName, dimensionShortName, evidenceName, familyName,
  localizeClientError, metricName, pairText, reasonText, relationshipName, stateName, stateSummary,
  unitName, universeName, warningText,
} from '../i18n/domain';

type PageState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; data: MarketRegimePreviewResponse };
type WindowSize = 5 | 10 | 20;
type EvidenceTone = 'support' | 'neutral' | 'drag';

const STATE_PRIORITY: Record<string, number> = {
  relationship_break_candidate: 0, rotation_candidate: 1, divergence: 2,
  synchronous_weakening: 3, synchronous_strengthening: 4, neutral: 5, unavailable: 6,
};

const DECISION_LANES = [
  ['growth_broad', 'small_large', 'mid_large'],
  ['growth_value'],
  ['consumer_risk', 'technology_defensive', 'industrial_defensive', 'financial_defensive'],
  ['energy_broad', 'health_broad'],
  ['semis_growth', 'software_growth', 'biotech_health', 'regional_financials'],
  ['credit_quality', 'credit_duration'],
] as const;

function number(t: Translate, value: string | null, digits = 2): string {
  return value === null ? t('common.unavailable') : Number(value).toFixed(digits);
}
function score(t: Translate, value: string | null): string { return number(t, value, 1); }
function contribution(t: Translate, value: string | null): string {
  return value === null ? t('common.unavailable') : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(2)} ${t('common.pointsShort')}`;
}
function delta(t: Translate, current: string | null, prior: string | null, digits = 1): string {
  if (current === null || prior === null) return t('common.unavailable');
  const value = Number(current) - Number(prior);
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`;
}
function thresholdDistance(item: { signed_distance: string; boundary_operator: string } | undefined): string | null {
  if (!item) return null;
  const signed = Number(item.signed_distance);
  if (!Number.isFinite(signed)) return null;
  return Math.max(0, item.boundary_operator.includes('>') ? -signed : signed).toFixed(1);
}
function weight(value: string): string { return `${Number(value).toFixed(Number(value) % 1 === 0 ? 0 : 1)}%`; }
function percent(t: Translate, value: string | null): string {
  return value === null ? t('common.unavailable') : `${Number(value) >= 0 ? '+' : ''}${(Number(value) * 100).toFixed(2)}%`;
}
function percentagePoints(t: Translate, value: string | null): string {
  return value === null ? t('common.unavailable') : Math.abs(Number(value) * 100).toFixed(2);
}
function signedPercentagePoints(t: Translate, value: string | null): string {
  return value === null ? t('common.unavailable') : `${Number(value) >= 0 ? '+' : ''}${(Number(value) * 100).toFixed(2)}`;
}
function signed(t: Translate, value: string | null, digits = 2): string {
  return value === null ? t('common.unavailable') : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(digits)}`;
}
function sentenceList(t: Translate, values: string[]): string {
  if (values.length === 0) return t('common.noDimensions');
  if (values.length === 1) return values[0];
  return `${values.slice(0, -1).join(t('common.listSeparator'))}${t('common.listAnd')}${values[values.length - 1]}`;
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
  const { t } = useI18n();
  return <span className={`regime-state state-${state ?? 'unavailable'}`}><i aria-hidden="true" />{relationshipName(t, state)}</span>;
}
function ReviewDeploymentBanner({ data }: { data: MarketRegimePreviewResponse }): JSX.Element | null {
  const { t } = useI18n(); const review = data.review_deployment;
  if (data.data_status !== 'stale_review' || !review) return null;
  return <section className="review-deployment-banner" role="status"><strong>{t('review.banner', {
    session: review.approved_as_of_session, count: review.expected_lag_sessions,
  })}</strong></section>;
}

function DecisionBrief({ data }: { data: MarketRegimePreviewResponse }): JSX.Element {
  const { t } = useI18n();
  const state = data.regime.current_state;
  const history = data.regime.state_history.filter((item) => item.composite !== null);
  const currentScore = state.composite ?? data.regime.composite.regime_score;
  const priorScore = history.length >= 2 ? history[history.length - 2].composite : null;
  const fiveSessionScore = history.length >= 6 ? history[history.length - 6].composite : null;
  const oneDayChange = currentScore !== null && priorScore !== null ? Number(currentScore) - Number(priorScore) : null;
  const confirmed = state.confirmed_state ?? 'unavailable';
  const riskOn = state.threshold_distances.find((item) => item.threshold_id === 'balanced_to_risk_on');
  const defensive = state.threshold_distances.find((item) => item.threshold_id === 'balanced_to_defensive');
  const broadRiskOn = confirmed === 'risk_on' && state.conflicting_dimension_ids.length === 0;
  const headlineKey = confirmed === 'balanced'
    ? oneDayChange !== null && oneDayChange < 0 ? 'regime.briefBalancedDeteriorating'
      : oneDayChange !== null && oneDayChange > 0 ? 'regime.briefBalancedImproving' : 'regime.briefBalancedMixed'
    : confirmed === 'risk_on' ? 'regime.briefRiskOn'
      : confirmed === 'defensive' ? 'regime.briefDefensive'
        : confirmed === 'stress' ? 'regime.briefStress' : 'regime.briefUnavailable';
  return <section className="panel decision-brief" aria-labelledby="decision-brief-title">
    <div className="decision-brief-heading"><div><p className="eyebrow">{t('regime.briefEyebrow')}</p><h1 id="decision-brief-title">{t('regime.briefTitle')}</h1></div><span className={`decision-stance ${broadRiskOn ? 'supports-risk-on' : 'selective-risk'}`}>{t(broadRiskOn ? 'regime.broadRiskOnSupported' : 'regime.broadRiskOnUnsupported')}</span></div>
    <strong className="decision-headline">{t(headlineKey)}</strong>
    <p className="decision-summary">{t('regime.briefEvidence', {
      supports: sentenceList(t, state.supporting_dimension_ids.map((item) => dimensionShortName(t, item))),
      drags: sentenceList(t, state.conflicting_dimension_ids.map((item) => dimensionShortName(t, item))),
    })}</p>
    <div className="decision-change-grid">
      <article><span>{t('regime.oneSessionChange')}</span><strong>{delta(t, currentScore, priorScore)}</strong><small>{t('regime.scorePoints')}</small></article>
      <article><span>{t('regime.fiveSessionChange')}</span><strong>{delta(t, currentScore, fiveSessionScore)}</strong><small>{t('regime.scorePoints')}</small></article>
      <article><span>{t('regime.distanceRiskOn')}</span><strong>{thresholdDistance(riskOn) ?? t('common.unavailable')}</strong><small>{t('regime.scorePoints')}</small></article>
      <article><span>{t('regime.distanceDefensive')}</span><strong>{thresholdDistance(defensive) ?? t('common.unavailable')}</strong><small>{t('regime.scorePoints')}</small></article>
    </div>
    <p className="decision-boundary">{t('regime.briefBoundary')}</p>
  </section>;
}
function metricFor(item: Relationship, windowSize: WindowSize): RelationshipWindow {
  return item.current.windows.find((metric) => metric.window_sessions === windowSize) as RelationshipWindow;
}
function directionSentence(t: Translate, metric: RelationshipWindow, windowSize: WindowSize): string {
  if (metric.left_return === null || metric.right_return === null) return t('regime.comparisonUnavailable', { count: windowSize });
  const left = Number(metric.left_return); const right = Number(metric.right_return);
  if (left < 0 && right < 0) return t('regime.bothDeclined', { count: windowSize });
  if (left > 0 && right > 0) return t('regime.bothAdvanced', { count: windowSize });
  if (left > 0 && right < 0) return t('regime.leftUpRightDown', { count: windowSize });
  if (left < 0 && right > 0) return t('regime.leftDownRightUp', { count: windowSize });
  return t('regime.mixedFlat', { count: windowSize });
}
function relativeSentence(t: Translate, item: Relationship, metric: RelationshipWindow): string {
  if (metric.relative_return === null) return t('regime.relativeUnavailable');
  const leftLeads = Number(metric.relative_return) >= 0;
  const leader = leftLeads ? item.definition.left_ticker : item.definition.right_ticker;
  const laggard = leftLeads ? item.definition.right_ticker : item.definition.left_ticker;
  const bothNegative = metric.left_return !== null && metric.right_return !== null && Number(metric.left_return) < 0 && Number(metric.right_return) < 0;
  return t(bothNegative ? 'regime.relativeHeldUp' : 'regime.relativeBetter', {
    leader, laggard, points: percentagePoints(t, metric.relative_return),
  });
}
function crossWindowSentence(t: Translate, item: Relationship): string {
  const available = item.current.windows.filter((metric) => metric.relative_return !== null);
  if (available.length !== 3) return t('regime.crossWindowIncomplete');
  const signs = available.map((metric) => Math.sign(Number(metric.relative_return)));
  if (signs.every((value) => value >= 0)) return t('regime.crossWindowLeft', { left: item.definition.left_ticker, right: item.definition.right_ticker });
  if (signs.every((value) => value <= 0)) return t('regime.crossWindowRight', { left: item.definition.left_ticker, right: item.definition.right_ticker });
  return t('regime.crossWindowMixed');
}
function relationshipChanged(item: Relationship): boolean {
  return item.current.previous_relationship_state !== undefined
    && item.current.previous_relationship_state !== null
    && item.current.previous_relationship_state !== item.current.relationship_state;
}
function relationshipPersistence(t: Translate, item: Relationship): string {
  const summary = item.change_summary;
  const previous = item.current.previous_relationship_state;
  if (previous === undefined || previous === null) return t('regime.stateHistoryUnavailable');
  if (previous === item.current.relationship_state && summary) return t(
    summary.state_run_reaches_history_start ? 'regime.stateRunsAtLeast' : 'regime.stateRuns',
    { count: summary.current_state_run_session_count, session: summary.current_state_run_started_session },
  );
  if (previous === item.current.relationship_state) return t('regime.stateContinues');
  return t('regime.stateChangedFrom', { state: relationshipName(t, previous) });
}
function leadershipChangeName(t: Translate, value: string): string {
  if (value === 'strengthening') return t('regime.leadershipStrengthening');
  if (value === 'weakening') return t('regime.leadershipWeakening');
  if (value === 'reversed') return t('regime.leadershipReversed');
  if (value === 'new_leadership') return t('regime.leadershipNew');
  if (value === 'leadership_faded') return t('regime.leadershipFaded');
  if (value === 'unchanged') return t('regime.leadershipUnchanged');
  return t('common.unavailable');
}
function relationshipMomentum(t: Translate, item: Relationship, windowSize: WindowSize): string | null {
  const summary = item.change_summary;
  const change = summary?.windows.find((row) => row.window_sessions === windowSize);
  if (!summary || !change) return null;
  const relativeReturn = change.current_relative_return === null ? null : Number(change.current_relative_return);
  const leader = relativeReturn === null || relativeReturn === 0 ? t('regime.noClearLeader')
    : relativeReturn > 0 ? item.definition.left_ticker : item.definition.right_ticker;
  return t('regime.relationshipMomentum', {
    leader, movement: leadershipChangeName(t, change.leadership_change_1),
    one: signedPercentagePoints(t, change.change_1_session),
    five: signedPercentagePoints(t, change.change_5_sessions),
  });
}
function selectDecisionHighlights(items: Relationship[]): Relationship[] {
  const selected: Relationship[] = [];
  DECISION_LANES.forEach((pairIds) => {
    const candidates = pairIds.map((pairId) => items.find((item) => item.definition.pair_id === pairId)).filter((item): item is Relationship => item !== undefined);
    const representative = candidates.find((item) => !['neutral', 'unavailable'].includes(item.current.relationship_state)) ?? candidates[0];
    if (representative && !selected.includes(representative)) selected.push(representative);
  });
  const remaining = [...items].filter((item) => !selected.includes(item) && !['neutral', 'unavailable'].includes(item.current.relationship_state))
    .sort((a, b) => Number(relationshipChanged(b)) - Number(relationshipChanged(a))
      || (STATE_PRIORITY[a.current.relationship_state] - STATE_PRIORITY[b.current.relationship_state])
      || a.definition.registry_order - b.definition.registry_order);
  return [...selected, ...remaining].slice(0, 6);
}
function dimensionTone(data: MarketRegimePreviewResponse, dimensionId: string): EvidenceTone {
  if (data.regime.current_state.conflicting_dimension_ids.includes(dimensionId)) return 'drag';
  if (data.regime.current_state.supporting_dimension_ids.includes(dimensionId)) return 'support';
  return 'neutral';
}
function dimensionCopy(t: Translate, dimension: RegimeDimension, tone: EvidenceTone): string {
  if (dimension.dimension_id === 'volatility') return t('dimension.copy.volatility');
  if (dimension.dimension_id === 'liquidity_participation') return t(tone === 'drag' ? 'dimension.copy.participationDrag' : 'dimension.copy.participationMixed');
  if (dimension.dimension_id === 'leadership_dispersion') return t('dimension.copy.leadership');
  if (dimension.dimension_id === 'breadth') return t(tone === 'support' ? 'dimension.copy.breadthSupport' : tone === 'drag' ? 'dimension.copy.breadthDrag' : 'dimension.copy.breadthNeutral');
  return t(tone === 'support' ? 'dimension.copy.trendSupport' : tone === 'drag' ? 'dimension.copy.trendDrag' : 'dimension.copy.trendNeutral');
}

function Hero({ data }: { data: MarketRegimePreviewResponse }): JSX.Element {
  const { t } = useI18n();
  const state = data.regime.current_state; const confirmed = state.confirmed_state ?? 'unavailable';
  const candidateDiffers = state.instantaneous_candidate_state !== null && state.instantaneous_candidate_state !== state.confirmed_state;
  const support = state.supporting_dimension_ids.map((item) => dimensionShortName(t, item));
  const conflict = state.conflicting_dimension_ids.map((item) => dimensionShortName(t, item));
  const riskOnDistance = state.threshold_distances.find((item) => item.threshold_id === 'balanced_to_risk_on');
  const defensiveDistance = state.threshold_distances.find((item) => item.threshold_id === 'balanced_to_defensive');
  const transitionCopy = confirmed === 'balanced' && riskOnDistance && defensiveDistance
    ? t('regime.thresholdPosition', {
      riskOn: Math.abs(Number(riskOnDistance.signed_distance)).toFixed(1),
      defensive: Math.abs(Number(defensiveDistance.signed_distance)).toFixed(1),
    })
    : state.pending_target_state ? t(state.confirmation_sessions_remaining === 1 ? 'regime.pending' : 'regime.pendingPlural', { state: stateName(t, state.pending_target_state), count: state.confirmation_sessions_remaining })
      : t('regime.noTransition');
  return <section className="regime-hero panel">
    <div className="hero-heading"><p className="eyebrow">{t('regime.heroEyebrow')}</p><h2>{t('regime.title')}</h2></div>
    <div className="hero-state-block"><span className="hero-label">{t('regime.confirmedState')}</span><div className={`hero-state state-text-${confirmed}`}><i aria-hidden="true" />{stateName(t, confirmed)}</div><strong>{stateSummary(t, confirmed)}</strong></div>
    <div className="hero-composite" data-exact-value={data.regime.composite.regime_score ?? undefined}><span>{t('regime.composite')}</span><strong>{score(t, data.regime.composite.regime_score)} <small>/ 100</small></strong><p>{candidateDiffers ? t('regime.candidate', { state: stateName(t, state.instantaneous_candidate_state) }) : t('regime.candidateMatches')}</p></div>
    <div className="hero-evidence"><div className="evidence-callout evidence-support"><span>{t('regime.whatSupports')}</span><strong>{sentenceList(t, support)}</strong><small>{t(support.length ? 'regime.supportDetail' : 'regime.supportUnavailable')}</small></div><div className="evidence-callout evidence-drag"><span>{t('regime.whatDrags')}</span><strong>{sentenceList(t, conflict)}</strong><small>{t(conflict.length ? 'regime.dragDetail' : 'regime.dragUnavailable')}</small></div></div>
    <div className="hero-transition"><span>{transitionCopy}</span><small>{t('regime.fixedRules')}</small></div>
    <div className="regime-hero-meta"><span>{t('regime.asOf', { session: data.as_of_session })}</span><span>{t('regime.universeMeta', { universe: universeName(t, data.regime.definition.universe_id, data.regime.definition.display_name) })}</span><span className="short-history-chip">{t('regime.sessionPreview', { count: data.input_session_count })}</span><span>{t('regime.researchCaveat')}</span></div>
  </section>;
}

function Dimensions({ data }: { data: MarketRegimePreviewResponse }): JSX.Element {
  const { t } = useI18n();
  const exactTotal = data.regime.composite.dimensions.map((item) => Number(item.score_contribution ?? 0)).reduce((a, b) => a + b, 0).toFixed(4);
  return <section className="panel dimensions-panel" aria-labelledby="dimensions-title"><div className="section-header compact"><div><p className="eyebrow">{t('regime.drivers')}</p><h2 id="dimensions-title">{t('regime.driversTitle')}</h2></div><p className="section-note">{t('regime.driversNote')}</p></div>
    <div className="dimension-grid">{data.regime.composite.dimensions.map((dimension) => {
      const tone = dimensionTone(data, dimension.dimension_id); const width = Math.max(0, Math.min(100, Number(dimension.score ?? 0)));
      return <details className={`dimension-card tone-${tone}`} key={dimension.dimension_id}><summary>
        <span className="dimension-name">{dimensionName(t, dimension.dimension_id)}</span><span className={`evidence-tag evidence-${tone}`}>{evidenceName(t, tone)}</span>
        <strong>{score(t, dimension.score)}</strong><div className="dimension-bar" aria-label={t('regime.scoreAria', { dimension: dimensionName(t, dimension.dimension_id), score: score(t, dimension.score) })}><i style={{ width: `${width}%` }} /></div>
        <p>{dimensionCopy(t, dimension, tone)}</p><small>{t('regime.weightContribution', { weight: weight(dimension.effective_weight), contribution: contribution(t, dimension.score_contribution) })}</small><span className="audit-link">{t('regime.viewCalculation')}</span>
      </summary><div className="dimension-audit"><p>{dimensionAuditText(t, dimension.dimension_id)}</p><div className="metric-ledger"><div className="metric-ledger-head"><span>{t('common.metric')}</span><span>{t('common.raw')}</span><span>{t('common.normalized')}</span><span>{t('regime.configEffectiveWeight')}</span><span>{t('common.contribution')}</span></div>{dimension.raw_metrics.map((metric) => <div key={metric.metric_id}><span>{metricName(t, metric.metric_id)}</span><span>{number(t, metric.raw_value, 4)} <small>{unitName(t, metric.raw_unit)}</small></span><span>{number(t, metric.normalized_value, 4)}</span><span>{number(t, metric.configured_weight, 4)} / {number(t, metric.effective_weight, 4)}</span><span>{number(t, metric.weighted_contribution, 4)}</span></div>)}</div><p className="reason-line"><b>{t('sector.interpretation')}:</b> {dimension.reason_codes.map((code) => reasonText(t, code)).join(' ')}</p></div></details>;
    })}</div>
    <details className="contribution-audit"><summary>{t('regime.calculationAudit')}</summary><div><span>{t('regime.exactReconciliation')}</span><strong>{exactTotal} = {number(t, data.regime.composite.regime_score, 4)}</strong><span>{t('regime.auditNote')}</span></div></details>
  </section>;
}

function RelationshipCard({ item, windowSize, onOpen }: { item: Relationship; windowSize: WindowSize; onOpen: () => void }): JSX.Element {
  const { t } = useI18n(); const metric = metricFor(item, windowSize); const pair = `${item.definition.left_ticker} / ${item.definition.right_ticker}`; const momentum = relationshipMomentum(t, item, windowSize);
  return <button type="button" className="relationship-highlight" title={t('regime.openPair', { pair })} onClick={onOpen}>
    <span className="highlight-family">{pairText(t, item.definition.pair_id, 'rationale', item.definition.economic_rationale)}</span><div className="highlight-title"><strong>{pair}</strong><StateMark state={item.current.relationship_state} /></div>
    <span className={`relationship-change ${relationshipChanged(item) ? 'changed' : ''}`}>{relationshipPersistence(t, item)}</span>
    <div className="highlight-returns"><span><small>{item.definition.left_ticker}</small><b>{percent(t, metric.left_return)}</b></span><span><small>{item.definition.right_ticker}</small><b>{percent(t, metric.right_return)}</b></span><span className="highlight-spread"><small>{t('regime.relativeSpread')}</small><b>{percent(t, metric.relative_return)}</b></span></div>
    <p>{directionSentence(t, metric, windowSize)} {relativeSentence(t, item, metric)}</p>
    {momentum ? <small className="relationship-momentum">{momentum}</small> : null}
  </button>;
}
function WindowMetric({ relationship, windowSize }: { relationship: Relationship; windowSize: WindowSize }): JSX.Element {
  const { t } = useI18n(); const metric = metricFor(relationship, windowSize);
  return <><span className="return-cell"><small>{relationship.definition.left_ticker}</small><b className={metric.left_return && Number(metric.left_return) >= 0 ? 'positive-text' : 'negative-text'}>{percent(t, metric.left_return)}</b></span><span className="return-cell"><small>{relationship.definition.right_ticker}</small><b className={metric.right_return && Number(metric.right_return) >= 0 ? 'positive-text' : 'negative-text'}>{percent(t, metric.right_return)}</b></span><span className="spread-cell"><small>{t('common.spread')}</small><strong>{percent(t, metric.relative_return)}</strong></span><span className="correlation-cell"><small>{t('common.correlation')}</small><b>{number(t, metric.rolling_correlation, 2)}</b></span></>;
}
function RelationshipStateTimeline({ item, windowSize }: { item: Relationship; windowSize: WindowSize }): JSX.Element | null {
  const { t } = useI18n(); const timeline = item.state_timeline;
  if (!timeline) return null;
  return <section className="relationship-timeline" aria-labelledby="relationship-timeline-title">
    <div className="relationship-timeline-heading"><div><span id="relationship-timeline-title">{t('regime.stateTimeline')}</span><strong>{t('regime.stateTimelineCaption', { displayed: timeline.displayed_session_count, retained: timeline.retained_session_count })}</strong></div><small>{t('regime.timelineRelative', { count: windowSize })}</small></div>
    <div className="relationship-timeline-track" role="list">
      {timeline.points.map((point) => { const timelineWindow = point.windows.find((row) => row.window_sessions === windowSize); return <div className={`relationship-timeline-point state-${point.relationship_state} ${point.changed_from_prior_retained_session ? 'timeline-state-change' : ''}`} role="listitem" key={point.as_of_session} title={point.as_of_session}>
        <time dateTime={point.as_of_session}>{point.as_of_session.slice(5)}</time><i aria-hidden="true" /><small>{relationshipName(t, point.relationship_state)}</small><b>{percent(t, timelineWindow?.relative_return ?? null)}</b>{point.changed_from_prior_retained_session ? <em>{t('regime.timelineChanged')}</em> : null}
      </div>; })}
    </div>
    <p>{timeline.truncated_before ? t('regime.timelineOlderCompacted', { session: timeline.retained_first_session }) : t('regime.timelineFullHistory', { session: timeline.retained_first_session })} {t('regime.changeIsDescriptive')}</p>
  </section>;
}
function PairDetail({ item, windowSize, onClose }: { item: Relationship; windowSize: WindowSize; onClose: () => void }): JSX.Element {
  const { t } = useI18n(); const metric = metricFor(item, windowSize); const pair = `${item.definition.left_ticker} / ${item.definition.right_ticker}`; const momentum = relationshipMomentum(t, item, windowSize);
  return <aside className="relationship-drawer" role="dialog" aria-modal="false" aria-labelledby="pair-detail-title"><div className="detail-header"><div><p className="eyebrow">{familyName(t, item.definition.relationship_family)}</p><h2 id="pair-detail-title">{pair}</h2><p>{pairText(t, item.definition.pair_id, 'rationale', item.definition.economic_rationale)}</p></div><button className="drawer-close" type="button" onClick={onClose} aria-label={t('regime.closePair', { pair })}><span aria-hidden="true">×</span> {t('common.close')}</button></div>
    <div className="drawer-observation"><span>{t('regime.currentRead', { count: windowSize })}</span><strong>{directionSentence(t, metric, windowSize)}</strong><strong>{relativeSentence(t, item, metric)}</strong><p>{crossWindowSentence(t, item)} {t('regime.shortReliability')}</p></div>
    <div className="drawer-summary"><div><span>{t('regime.relationshipState')}</span><StateMark state={item.current.relationship_state} /></div><div><span>{t('regime.relativeResult')}</span><strong>{percent(t, metric.relative_return)}</strong><small>{t('regime.leads', { ticker: Number(metric.relative_return ?? 0) >= 0 ? item.definition.left_ticker : item.definition.right_ticker })}</small></div><div><span>{t('regime.reliability')}</span><strong>{confidenceName(t, item.current.confidence)}</strong><small>{t('regime.reliabilityMeaning')}</small></div></div>
    {momentum ? <div className="relationship-change-detail"><strong>{relationshipPersistence(t, item)}</strong><span>{momentum}</span><small>{t('regime.changeIsDescriptive')}</small></div> : null}
    <RelationshipStateTimeline item={item} windowSize={windowSize} />
    <div className="pair-window-detail"><div className="pair-window-head"><span>{t('common.window')}</span><span>{item.definition.left_ticker}</span><span>{item.definition.right_ticker}</span><span>{t('common.spread')}</span><span>{t('common.correlation')}</span></div>{item.current.windows.map((row) => <div className={row.window_sessions === windowSize ? 'selected-window' : ''} key={row.window_sessions}><strong>{t('regime.windowSessions', { count: row.window_sessions })}</strong><span>{percent(t, row.left_return)}</span><span>{percent(t, row.right_return)}</span><span>{percent(t, row.relative_return)}</span><span>{number(t, row.rolling_correlation, 2)}</span></div>)}</div>
    <div className="evidence-columns"><section><h3>{t('regime.supportingEvidence')}</h3><ul>{item.explanation.supporting_evidence.map((line) => <li key={line}>{reasonText(t, line)}</li>)}</ul></section><section><h3>{t('regime.counterevidence')}</h3>{item.explanation.counterevidence.length ? <ul>{item.explanation.counterevidence.map((line) => <li key={line}>{reasonText(t, line)}</li>)}</ul> : <p>{t('regime.noCounterevidence')}</p>}</section></div>
    <details className="technical-diagnostics"><summary>{t('regime.technical')}</summary><dl className="drawer-stats"><div><dt>{t('regime.correlationChange')}</dt><dd>{signed(t, item.current.correlation_change_5, 2)}</dd></div><div><dt>{t('regime.ratioLevel')}</dt><dd>{number(t, item.current.ratio_level, 3)}</dd></div><div><dt>{t('regime.ratioRobust')}</dt><dd>{item.current.ratio_robust_z === null && item.current.ratio_percentile === null ? t('regime.needs60') : `${number(t, item.current.ratio_robust_z, 2)} / ${number(t, item.current.ratio_percentile, 2)}`}</dd></div></dl><p><b>{t('sector.interpretation')}:</b> {item.current.reason_codes.map((code) => reasonText(t, code)).join(' ')}</p><p>{pairText(t, item.definition.pair_id, 'expected', item.definition.expected_interpretation)}</p><p>{pairText(t, item.definition.pair_id, 'forbidden', item.definition.forbidden_interpretation)}</p></details>
    <div className="drawer-disclaimers"><span>{t('regime.causationCaveat')}</span><span>{t('regime.fundFlowCaveat')}</span><span>{t('regime.candidateCaveat')}</span></div>
  </aside>;
}

function Relationships({ data }: { data: MarketRegimePreviewResponse }): JSX.Element {
  const { t } = useI18n();
  const initial = requested(); const [windowSize, setWindowSize] = useState<WindowSize>(initial.window); const [family, setFamily] = useState(initial.family); const [stateFilter, setStateFilter] = useState(initial.state); const [scope, setScope] = useState(initial.scope); const [pairId, setPairId] = useState<string | undefined>(initial.pair);
  useEffect(() => { const onPop = () => { const next = requested(); setWindowSize(next.window); setFamily(next.family); setStateFilter(next.state); setScope(next.scope); setPairId(next.pair); }; window.addEventListener('popstate', onPop); return () => window.removeEventListener('popstate', onPop); }, []);
  const families = useMemo(() => [...new Set(data.relationships.map((item) => item.definition.relationship_family))], [data]);
  const states = useMemo(() => [...new Set(data.relationships.map((item) => item.current.relationship_state))], [data]);
  const visible = data.relationships.filter((item) => (family === 'all' || item.definition.relationship_family === family) && (stateFilter === 'all' || item.current.relationship_state === stateFilter) && (scope === 'all' || item.current.relationship_state !== 'neutral'));
  const highlights = selectDecisionHighlights(data.relationships);
  const selected = pairId ? data.relationships.find((item) => item.definition.pair_id === pairId) : undefined;
  return <>
    <section className="panel highlights-panel">
      <div className="section-header compact"><div><p className="eyebrow">{t('regime.highlightEyebrow', { count: windowSize })}</p><h2>{t('regime.highlightTitle')}</h2></div><details className="highlight-method"><summary>{t('regime.highlightMethod')}</summary><p>{t('regime.highlightMethodBody')}</p></details></div>
      <p className="relationship-reliability-note">{t('regime.globalLowReliability', { count: data.input_session_count })}</p>
      <div className="highlight-grid">{highlights.map((item) => <RelationshipCard key={item.definition.pair_id} item={item} windowSize={windowSize} onOpen={() => { setPairId(item.definition.pair_id); updateUrl({ pair: item.definition.pair_id }); }} />)}</div>
    </section>
    <details className="panel relationship-map-panel">
      <summary className="relationship-map-summary"><span><span className="eyebrow">{t('regime.completeMap')}</span><strong>{t('regime.allPairs')}</strong></span><small>{t('regime.expandCompleteMap')}</small></summary>
      <div className="relationship-map-content">
        <div className="section-header relationship-header"><p className="section-note">{t('regime.completeMapNote')}</p><div className="window-tabs" aria-label={t('regime.relationshipWindowAria')}>{([5, 10, 20] as WindowSize[]).map((value) => <button type="button" className={windowSize === value ? 'active' : ''} key={value} onClick={() => { setWindowSize(value); updateUrl({ window: String(value) }); }}>{t('regime.windowSessions', { count: value })}</button>)}</div></div>
        <div className="relationship-filters"><label>{t('common.family')}<select value={family} onChange={(event) => { setFamily(event.target.value); updateUrl({ family: event.target.value }); }}><option value="all">{t('regime.allFamilies')}</option>{families.map((value) => <option key={value} value={value}>{familyName(t, value)}</option>)}</select></label><label>{t('common.state')}<select value={stateFilter} onChange={(event) => { setStateFilter(event.target.value); updateUrl({ state: event.target.value }); }}><option value="all">{t('regime.allStates')}</option>{states.map((value) => <option key={value} value={value}>{relationshipName(t, value)}</option>)}</select></label><label className="toggle-filter"><input aria-label={t('regime.onlyNonNeutral')} type="checkbox" checked={scope === 'nonneutral'} onChange={(event) => { const value = event.target.checked ? 'nonneutral' : 'all'; setScope(value); updateUrl({ scope: value }); }} /> {t('regime.onlyNonNeutral')}</label><button type="button" onClick={() => { setFamily('all'); setStateFilter('all'); setScope('all'); updateUrl({ family: null, state: null, scope: null }); }}>{t('regime.clearFilters')}</button></div>
        <div className="relationship-table"><div className="relationship-table-head"><span>{t('regime.tablePair')}</span><span>{t('regime.tableLeft')}</span><span>{t('regime.tableRight')}</span><span>{t('regime.tableRelative')}</span><span>{t('regime.tableMovement')}</span><span>{t('regime.tableState')}</span></div>{visible.map((item) => { const pair = `${item.definition.left_ticker} / ${item.definition.right_ticker}`; return <button type="button" className="relationship-row" title={t('regime.openPair', { pair })} key={item.definition.pair_id} onClick={() => { setPairId(item.definition.pair_id); updateUrl({ pair: item.definition.pair_id }); }}><span className="pair-identity"><strong>{pair}</strong><small>{pairText(t, item.definition.pair_id, 'rationale', item.definition.economic_rationale)}</small></span><WindowMetric relationship={item} windowSize={windowSize} /><span className="relationship-state-cell"><StateMark state={item.current.relationship_state} /><small>{relationshipPersistence(t, item)} · {t('regime.reliabilityInline', { value: confidenceName(t, item.current.confidence) })}</small></span></button>; })}</div><p className="table-foot">{t('regime.showingPairs', { count: visible.length })}</p>
      </div>
    </details>
    {selected ? <PairDetail item={selected} windowSize={windowSize} onClose={() => { setPairId(undefined); updateUrl({ pair: null }); }} /> : null}
  </>;
}

function Methodology({ data }: { data: MarketRegimePreviewResponse }): JSX.Element {
  const { t } = useI18n();
  return <details className="panel methodology"><summary>{t('regime.methodologyTitle')}</summary><div className="method-grid"><div><h3>{t('regime.fixedScope')}</h3><p>{t('regime.fixedScopeBody')}</p><p>{t('regime.fixedScopeHighlight')}</p></div><div><h3>{t('regime.interpretation')}</h3><p>{t('regime.interpretationBody')}</p><p>{t('regime.interpretationResearch')}</p></div><div><h3>{t('regime.shortHistory')}</h3><p>{t('regime.shortHistoryBody', { count: data.input_session_count, start: data.input_first_session, end: data.input_last_session })}</p></div></div>{data.warnings.map((warning) => <p className="quality-copy" key={warning}>• {warningText(t, warning)}</p>)}</details>;
}

export function MarketRegimeOpportunityMapPage({ withinWorkspaceShell = false }: { withinWorkspaceShell?: boolean } = {}): JSX.Element {
  const { t } = useI18n();
  const [state, setState] = useState<PageState>({ kind: 'loading' }); const initial = requested(); const [universeId, setUniverseId] = useState(initial.universe);
  const load = useCallback((universe?: string) => { const controller = new AbortController(); setState({ kind: 'loading' }); getMarketRegimePreview(universe, controller.signal).then((data) => { setState({ kind: 'ready', data }); if (universe !== data.selected_universe_id) updateUrl({ universe: data.selected_universe_id }, true); }).catch((error: unknown) => { if (!controller.signal.aborted) setState({ kind: 'error', message: error instanceof Error ? error.message : '' }); }); return () => controller.abort(); }, []);
  useEffect(() => load(universeId), [load, universeId]); useEffect(() => { const onPop = () => setUniverseId(requested().universe); window.addEventListener('popstate', onPop); return () => window.removeEventListener('popstate', onPop); }, []);
  if (state.kind === 'loading') return <main className="app-shell"><div className="panel state-panel">{t('regime.loading')}</div></main>;
  if (state.kind === 'error') return <main className="app-shell"><div className="panel state-panel error-state" role="alert"><h1>{t('regime.unavailableTitle')}</h1><p>{localizeClientError(t, state.message)}</p><p>{t('regime.unavailableBody')}</p><button type="button" onClick={() => load(universeId)}>{t('common.retry')}</button></div></main>;
  const data = state.data;
  return <main className="app-shell regime-shell"><div className="regime-topbar"><div><span className="brand">{t('regime.privateResearch')}</span><span>{t('regime.localPreview')}</span></div>{withinWorkspaceShell ? null : <label>{t('common.universe')}<select aria-label={t('regime.topbarUniverseAria')} value={data.selected_universe_id} onChange={(event) => { setUniverseId(event.target.value); updateUrl({ universe: event.target.value }); }}>{data.available_universes.map((item) => <option key={item.universe_id} value={item.universe_id}>{universeName(t, item.universe_id, item.display_name)} · {item.member_count.toLocaleString('en-US')}</option>)}</select></label>}</div><ReviewDeploymentBanner data={data} /><DecisionBrief data={data} /><Hero data={data} /><Dimensions data={data} /><Relationships data={data} /><Methodology data={data} /></main>;
}
