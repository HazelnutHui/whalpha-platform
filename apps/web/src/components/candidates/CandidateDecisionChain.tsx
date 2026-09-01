import type { CandidateItem } from '../../api/opportunityCandidates';
import { useI18n, type Translate } from '../../i18n/I18nProvider';

function numeric(value: string | null, digits = 1): string {
  return value === null ? '—' : Number(value).toLocaleString('en-US', { maximumFractionDigits: digits });
}

function postureName(t: Translate, posture: CandidateItem['entry_geometry']['review_posture']): string {
  return t(`candidate.entry.posture.${posture}` as never);
}

function setupName(t: Translate, setup: CandidateItem['entry_geometry']['technical_setup']): string {
  return t(`candidate.entry.setup.${setup}` as never);
}

function extensionName(t: Translate, extension: CandidateItem['entry_geometry']['extension_risk']): string {
  return t(`candidate.entry.extension.${extension}` as never);
}

function component(item: CandidateItem, id: string) {
  return item.components.find((row) => row.component_id === id);
}

export function CandidateDecisionChain({ item }: { item: CandidateItem }): JSX.Element {
  const { t } = useI18n();
  const market = component(item, 'market_alignment');
  const proxy = component(item, 'etf_sector_alignment');
  const relative = component(item, 'stock_relative_strength');
  const trend = component(item, 'trend_quality');
  const entry = item.entry_geometry;
  const primaryInvalidation = entry.technical_invalidation_codes.find((code) => code === 'close_below_reference_support_requires_reunderwrite')
    ?? entry.technical_invalidation_codes.find((code) => code === 'trend_component_below_50')
    ?? entry.technical_invalidation_codes[0];

  return <section className="candidate-decision-chain" aria-labelledby="candidate-decision-chain-title">
    <div className="candidate-decision-chain-heading"><div><p className="eyebrow">{t('candidate.chain.eyebrow')}</p><h3 id="candidate-decision-chain-title">{t('candidate.chain.title')}</h3></div><small>{t('candidate.chain.boundary')}</small></div>
    <ol>
      <li><span>1</span><div><small>{t('candidate.chain.market')}</small><strong>{numeric(market?.score ?? null)} / 100</strong><p>{t('candidate.chain.marketBody').replace('{points}', numeric(market?.contribution ?? null))}</p></div></li>
      <li className={item.primary_driver_ticker ? '' : 'candidate-chain-unavailable'}><span>2</span><div><small>{t('candidate.chain.proxy')}</small><strong>{item.primary_driver_ticker ?? t('common.unavailable')}</strong><p>{item.primary_driver_ticker ? t('candidate.chain.proxyBody').replace('{score}', numeric(proxy?.score ?? null)).replace('{correlation}', numeric(item.driver_correlation_20, 2)) : t('candidate.chain.proxyUnavailable')}</p></div></li>
      <li><span>3</span><div><small>{t('candidate.chain.stock')}</small><strong>{t('candidate.chain.rsShort')} {numeric(relative?.score ?? null)} · {t('candidate.chain.trendShort')} {numeric(trend?.score ?? null)}</strong><p>{t('candidate.chain.stockBody')}</p></div></li>
      <li className={`candidate-chain-entry candidate-chain-extension-${entry.extension_risk}`}><span>4</span><div><small>{t('candidate.chain.entry')}</small><strong>{postureName(t, entry.review_posture)}</strong><p>{setupName(t, entry.technical_setup)} · {t('candidate.entry.extensionLabel')} {extensionName(t, entry.extension_risk)}</p></div></li>
      <li className="candidate-chain-invalidation"><span>5</span><div><small>{t('candidate.chain.invalidation')}</small><strong>{t('candidate.chain.reunderwrite')}</strong><p>{primaryInvalidation ? t(`candidate.entry.code.${primaryInvalidation}` as never) : t('common.unavailable')}</p></div></li>
    </ol>
    <p className="candidate-decision-chain-note">{t('candidate.chain.note')}</p>
  </section>;
}
