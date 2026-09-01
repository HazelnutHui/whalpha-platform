import type { CandidateComponent, CandidateItem, CandidateMetric } from '../../api/opportunityCandidates';
import { useI18n, type Translate } from '../../i18n/I18nProvider';

function componentName(t: Translate, id: string): string {
  const names: Record<string, ReturnType<Translate>> = {
    market_alignment: t('candidate.component.market'),
    etf_sector_alignment: t('candidate.component.etf'),
    stock_relative_strength: t('candidate.component.relative'),
    trend_quality: t('candidate.component.trend'),
    volume_participation: t('candidate.component.volume'),
    volatility_risk: t('candidate.component.volatility'),
    liquidity_suitability: t('candidate.component.liquidity'),
  };
  return names[id] ?? id;
}

function metricName(t: Translate, id: string): string {
  const key = `candidate.metric.${id}` as never;
  return t(key);
}

function numeric(value: string | null, digits = 1): string {
  if (value === null) return '—';
  return Number(value).toLocaleString('en-US', { maximumFractionDigits: digits });
}

function metricValue(metric: CandidateMetric): string {
  if (metric.raw_value === null) return '—';
  const value = Number(metric.raw_value);
  if (metric.raw_unit === 'usd_proxy' || metric.raw_unit === 'usd') {
    if (Math.abs(value) >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
    if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
    return `$${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
  }
  if (metric.metric_id === 'current_volume_ratio') return `${numeric(metric.raw_value, 2)}×`;
  if (metric.metric_id === 'regime_score' || metric.raw_unit === 'score') return numeric(metric.raw_value);
  if (metric.metric_id === 'driver_correlation_20') return numeric(metric.raw_value, 2);
  return `${(value * 100).toFixed(1)}%`;
}

function contribution(component: CandidateComponent): number {
  return component.contribution === null ? 0 : Number(component.contribution);
}

function shortfall(component: CandidateComponent): number {
  return component.contribution === null ? 0 : Math.max(0, Number(component.effective_weight) - Number(component.contribution));
}

export function CandidateContributionLedger({ item }: { item: CandidateItem }): JSX.Element {
  const { t } = useI18n();
  const available = item.components.filter((component) => component.availability === 'available');
  const unavailable = item.components.filter((component) => component.availability === 'unavailable');
  const strongest = [...available].sort((a, b) => contribution(b) - contribution(a))[0];
  const limiting = [...available].sort((a, b) => shortfall(b) - shortfall(a))[0];
  const publishedTotal = item.base_score === null ? null : Number(item.base_score);
  const displayedTotal = available.reduce((total, component) => total + contribution(component), 0);

  return <section className="candidate-contribution-ledger" aria-labelledby="candidate-contribution-title">
    <div className="candidate-contribution-heading">
      <div><p className="eyebrow">{t('candidate.contribution.eyebrow')}</p><h3 id="candidate-contribution-title">{t('candidate.contributionTitle')}</h3></div>
      <small>{t('candidate.contribution.boundary')}</small>
    </div>
    <div className="candidate-contribution-summary">
      <div><span>{t('candidate.contribution.publishedTotal')}</span><strong>{numeric(item.base_score)}</strong><small>{t('candidate.contribution.reconciled').replace('{sum}', numeric(String(displayedTotal)))}</small></div>
      <div><span>{t('candidate.contribution.strongest')}</span><strong>{strongest ? componentName(t, strongest.component_id) : '—'}</strong><small>{strongest ? `+${numeric(strongest.contribution)} ${t('candidate.contribution.points')}` : t('common.unavailable')}</small></div>
      <div><span>{t('candidate.contribution.limiting')}</span><strong>{limiting ? componentName(t, limiting.component_id) : '—'}</strong><small>{limiting ? t('candidate.contribution.shortfall').replace('{points}', numeric(String(shortfall(limiting)))) : t('common.unavailable')}</small></div>
      <div><span>{t('candidate.contribution.coverage')}</span><strong>{numeric(item.configured_weight_available)}%</strong><small>{unavailable.length ? t('candidate.contribution.unavailableCount').replace('{count}', String(unavailable.length)) : t('candidate.contribution.complete')}</small></div>
    </div>
    {publishedTotal !== null ? <div className="candidate-score-bridge" role="img" aria-label={t('candidate.contribution.bridgeAria').replace('{score}', numeric(item.base_score))}>
      {available.map((component, index) => <i key={component.component_id} className={`candidate-score-segment candidate-score-segment-${index + 1}`} style={{ width: `${contribution(component)}%` }} title={`${componentName(t, component.component_id)} +${numeric(component.contribution)}`} />)}
      <i className="candidate-score-unfilled" style={{ width: `${Math.max(0, 100 - publishedTotal)}%` }} />
    </div> : null}
    <div className="candidate-contribution-table">
      <div className="candidate-contribution-table-head"><span>{t('candidate.contribution.component')}</span><span>{t('candidate.contribution.inputScore')}</span><span>{t('candidate.contribution.maxPoints')}</span><span>{t('candidate.contribution.earnedPoints')}</span></div>
      {item.components.map((component) => {
        const maxPoints = Number(component.effective_weight);
        const earned = contribution(component);
        const fill = maxPoints > 0 ? Math.max(0, Math.min(100, earned / maxPoints * 100)) : 0;
        return <div className={component.availability === 'available' ? '' : 'candidate-contribution-unavailable'} key={component.component_id}>
          <strong>{componentName(t, component.component_id)}</strong>
          <span>{numeric(component.score)}{component.cap_applied ? <small className="candidate-contribution-cap">{t('candidate.contribution.capApplied').replace('{cap}', numeric(component.cap_applied))}</small> : null}</span>
          <span>{numeric(component.effective_weight)}</span>
          <span className="candidate-contribution-earned"><i style={{ width: `${fill}%` }} />{component.contribution === null ? '—' : `+${numeric(component.contribution)}`}</span>
        </div>;
      })}
    </div>
    <p className="candidate-contribution-note">{t('candidate.contribution.note')}</p>
    <details className="candidate-metric-ledger"><summary>{t('candidate.contribution.rawMetrics')}</summary>
      {item.components.map((component) => <div key={component.component_id}><h4>{componentName(t, component.component_id)}</h4>
        {component.metrics.map((metric) => <div key={metric.metric_id}><span>{metricName(t, metric.metric_id)}</span><strong>{metricValue(metric)}</strong><small>{metric.availability === 'available' ? `${t('candidate.contribution.normalized')} ${numeric(metric.normalized_value)}` : t('common.unavailable')}</small></div>)}
      </div>)}
    </details>
  </section>;
}
