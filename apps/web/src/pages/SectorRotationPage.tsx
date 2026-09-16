import { useEffect, useMemo, useState, type CSSProperties } from 'react';

import { getMarketRegimePreview, type MarketRegimePreviewResponse } from '../api/marketRegime';
import { getOpportunityCandidates, type CandidateExtensionRisk, type CandidateStage, type OpportunityCandidateResponse } from '../api/opportunityCandidates';
import {
  getSectorRotation,
  type SectorRotationPosture,
  type SectorRotationRecord,
  type SectorRotationResponse,
} from '../api/sectorRotation';
import { buildMarketDecisionChain } from '../features/marketDecisionChain';
import { useI18n, type Translate } from '../i18n/I18nProvider';
import { localizeClientError, sectorName, stateName, universeName } from '../i18n/domain';

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; data: SectorRotationResponse };
type WindowSize = 5 | 10 | 20;

const WINDOWS: WindowSize[] = [5, 10, 20];

type ChainState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; regime: MarketRegimePreviewResponse; candidates: OpportunityCandidateResponse };

function percent(t: Translate, value: string | null): string {
  if (value === null) return t('common.unavailable');
  const number = Number(value) * 100;
  return `${number >= 0 ? '+' : ''}${number.toFixed(2)}%`;
}

function postureName(t: Translate, posture: SectorRotationPosture): string {
  return t(`sector.posture.${posture}` as never);
}

function postureSummary(t: Translate, item: SectorRotationRecord): string {
  const relative20 = item.windows[2].relative_return;
  return t(`sector.summary.${item.posture}` as never, {
    sector: item.sector,
    relative: percent(t, relative20),
    acceleration: percent(t, item.five_day_relative_acceleration),
  });
}

function stageName(t: Translate, stage: CandidateStage | null): string {
  if (stage === 'watch') return t('candidate.stage.watch');
  if (stage === 'prepare') return t('candidate.stage.prepare');
  if (stage === 'enter') return t('candidate.stage.enter');
  if (stage === 'invalidated') return t('candidate.stage.invalidated');
  return t('candidate.stage.unavailable');
}

function extensionName(t: Translate, risk: CandidateExtensionRisk | undefined): string {
  return risk ? t(`candidate.entry.extension.${risk}` as never) : t('common.unavailable');
}

function navigateToCandidates(): void {
  const url = new URL(window.location.href);
  url.searchParams.set('view', 'candidates');
  url.searchParams.set('candidateView', 'entry');
  url.searchParams.set('candidateRisk', 'balanced');
  window.history.pushState(window.history.state, '', url);
  window.dispatchEvent(new PopStateEvent('popstate'));
}

function MarketToCandidateChain({ rotation, universeId, windowSize }: {
  rotation: SectorRotationResponse;
  universeId: string;
  windowSize: WindowSize;
}): JSX.Element {
  const { t } = useI18n();
  const [state, setState] = useState<ChainState>({ kind: 'loading' });

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: 'loading' });
    void Promise.all([
      getMarketRegimePreview(universeId, controller.signal),
      getOpportunityCandidates(universeId, controller.signal),
    ]).then(([regime, candidates]) => {
      buildMarketDecisionChain(regime, rotation, candidates, 20);
      setState({ kind: 'ready', regime, candidates });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ kind: 'error', message: localizeClientError(t, error instanceof Error ? error.message : String(error)) });
    });
    return () => controller.abort();
  }, [rotation, t, universeId]);

  const data = state.kind === 'ready'
    ? buildMarketDecisionChain(state.regime, rotation, state.candidates, windowSize)
    : null;

  return (
    <section className="sector-chain-card">
      <div className="sector-section-heading">
        <div><span>{t('sector.chainEyebrow')}</span><h2>{t('sector.chainTitle')}</h2></div>
        <p>{t('sector.chainNote')}</p>
      </div>
      {state.kind === 'loading' ? <p className="sector-chain-message">{t('sector.chainLoading')}</p> : null}
      {state.kind === 'error' ? <div className="sector-chain-message sector-chain-error"><strong>{t('sector.chainUnavailable')}</strong><p>{state.message}</p></div> : null}
      {data ? <>
        <div className="sector-chain-flow">
          <article className="sector-chain-market">
            <span>{t('sector.chainMarket')}</span>
            <strong>{stateName(t, data.confirmed_market_state)}</strong>
            <p>{t('sector.chainRegimeScore')} <b>{data.regime_score ?? t('common.unavailable')}</b></p>
            <small>{universeName(t, data.universe_id)}</small>
          </article>
          <span className="sector-chain-arrow" aria-hidden="true">→</span>
          <article className="sector-chain-direction">
            <span>{t('sector.chainDirection')}</span>
            <strong>{t('sector.chainTopProxies', { count: data.sector_proxies.length, window: windowSize })}</strong>
            <div className="sector-chain-proxies">{data.sector_proxies.map((item) => {
              const window = item.windows[WINDOWS.indexOf(windowSize)];
              return <div key={item.ticker}><b>{item.ticker}</b><span>{sectorName(t, item.sector)}</span><em>{percent(t, window.relative_return)}</em><small>{postureName(t, item.posture)}</small></div>;
            })}</div>
          </article>
          <span className="sector-chain-arrow sector-chain-arrow-qualified" aria-hidden="true">→</span>
          <article className="sector-chain-candidates">
            <span>{t('sector.chainCandidates')}</span>
            <strong>{t('sector.chainCandidateCount', { shown: data.candidates.length, total: data.balanced_display_count })}</strong>
            <div className="sector-chain-candidate-list">{data.candidates.map(({ item, balanced_rank }) => <div key={item.instrument_id}>
              <b><i>{balanced_rank}</i>{item.ticker}</b>
              <span>{stageName(t, item.state.final_stage)}</span>
              <em>{t('sector.chainBaseScore')} {item.base_score ?? '—'}</em>
              <small>{t('sector.chainExtension')} · {extensionName(t, item.entry_summary?.extension_risk)}</small>
            </div>)}</div>
            <button type="button" onClick={navigateToCandidates}>{t('sector.chainOpenCandidates')}</button>
          </article>
        </div>
        <p className="sector-chain-boundary"><strong>{t('sector.chainSeparate')}</strong> {t('sector.chainBoundary')}</p>
      </> : null}
    </section>
  );
}

function QuadrantMap({ records }: { records: SectorRotationRecord[] }): JSX.Element {
  const { t } = useI18n();
  const available = records.filter((item) => item.windows[2].relative_return !== null && item.five_day_relative_acceleration !== null);
  const scale = Math.max(0.001, ...available.flatMap((item) => [
    Math.abs(Number(item.windows[2].relative_return)),
    Math.abs(Number(item.five_day_relative_acceleration)),
  ]));
  return (
    <section className="sector-map-card">
      <div className="sector-section-heading">
        <div><span>{t('sector.mapEyebrow')}</span><h2>{t('sector.mapTitle')}</h2></div>
        <p>{t('sector.mapNote')}</p>
      </div>
      <div className="sector-quadrant" role="img" aria-label={t('sector.mapAria')}>
        <span className="sector-axis sector-axis-x" />
        <span className="sector-axis sector-axis-y" />
        <span className="sector-quadrant-label top-left">{t('sector.posture.lagging_improving')}</span>
        <span className="sector-quadrant-label top-right">{t('sector.posture.leading_improving')}</span>
        <span className="sector-quadrant-label bottom-left">{t('sector.posture.lagging_weakening')}</span>
        <span className="sector-quadrant-label bottom-right">{t('sector.posture.leading_weakening')}</span>
        {available.map((item) => {
          const x = 50 + (Number(item.windows[2].relative_return) / scale) * 42;
          const y = 50 - (Number(item.five_day_relative_acceleration) / scale) * 42;
          return <span key={item.ticker} className={`sector-dot posture-${item.posture}`} style={{ '--x': `${x}%`, '--y': `${y}%` } as CSSProperties} title={`${item.ticker} · ${item.sector}`}><b>{item.ticker}</b></span>;
        })}
      </div>
      <div className="sector-axis-caption"><span>{t('sector.axisRelative')}</span><span>{t('sector.axisAcceleration')}</span></div>
    </section>
  );
}

function SectorRotationContent({ data, universeId }: { data: SectorRotationResponse; universeId: string }): JSX.Element {
  const { t } = useI18n();
  const [windowSize, setWindowSize] = useState<WindowSize>(20);
  const windowIndex = WINDOWS.indexOf(windowSize);
  const ranked = useMemo(() => [...data.records].sort((left, right) => {
    const a = left.windows[windowIndex].relative_rank ?? 999;
    const b = right.windows[windowIndex].relative_rank ?? 999;
    return a - b || left.registry_order - right.registry_order;
  }), [data.records, windowIndex]);
  const leaders = ranked.filter((item) => (item.windows[windowIndex].relative_return !== null && Number(item.windows[windowIndex].relative_return) > 0)).length;
  const improving = data.records.filter((item) => item.five_day_relative_acceleration !== null && Number(item.five_day_relative_acceleration) > 0).length;
  const strongest = ranked[0];

  return (
    <main className="sector-page">
      <section className="sector-hero">
        <div><span className="eyebrow">{t('sector.eyebrow')}</span><h1>{t('sector.title')}</h1><p>{t('sector.subtitle')}</p></div>
        <div className="sector-asof"><span>{t('sector.asOf')}</span><strong>{data.as_of_session}</strong><small>{t('sector.marketWide')}</small></div>
      </section>
      <section className="sector-brief-grid">
        <article><span>{t('sector.strongest')}</span><strong>{strongest?.ticker ?? '—'}</strong><p>{strongest ? postureSummary(t, strongest) : t('common.unavailable')}</p></article>
        <article><span>{t('sector.relativeLeaders')}</span><strong>{leaders} / 11</strong><p>{t('sector.relativeLeadersNote', { window: windowSize })}</p></article>
        <article><span>{t('sector.improving')}</span><strong>{improving} / 11</strong><p>{t('sector.improvingNote')}</p></article>
        <article className="sector-boundary-card"><span>{t('sector.interpretation')}</span><strong>{t('sector.proxyOnly')}</strong><p>{t('sector.proxyBoundary')}</p></article>
      </section>
      <MarketToCandidateChain rotation={data} universeId={universeId} windowSize={windowSize} />
      <QuadrantMap records={data.records} />
      <section className="sector-ranking-card">
        <div className="sector-section-heading">
          <div><span>{t('sector.rankingEyebrow')}</span><h2>{t('sector.rankingTitle')}</h2></div>
          <div className="window-tabs" role="group" aria-label={t('sector.windowAria')}>{WINDOWS.map((item) => <button type="button" key={item} className={windowSize === item ? 'active' : ''} onClick={() => setWindowSize(item)}>{item}{t('sector.sessionsShort')}</button>)}</div>
        </div>
        <div className="sector-table-wrap"><table className="sector-table"><thead><tr><th>{t('sector.rank')}</th><th>{t('sector.sector')}</th><th>{t('sector.etf')}</th><th>{t('sector.relativeReturn')}</th><th>{t('sector.acceleration')}</th><th>{t('sector.posture')}</th><th>{t('sector.duration')}</th></tr></thead><tbody>{ranked.map((item) => { const window = item.windows[windowIndex]; return <tr key={item.ticker}><td>{window.relative_rank ?? '—'}</td><td><strong>{item.sector}</strong><small>{postureSummary(t, item)}</small></td><td>{item.ticker}</td><td className={window.relative_return !== null && Number(window.relative_return) >= 0 ? 'positive' : 'negative'}>{percent(t, window.relative_return)}</td><td>{percent(t, item.five_day_relative_acceleration)}</td><td><span className={`sector-posture posture-${item.posture}`}>{postureName(t, item.posture)}</span></td><td>{t(item.run_reaches_history_start ? 'sector.durationAtLeast' : 'sector.durationExact', { count: item.five_day_leadership_run_sessions })}</td></tr>; })}</tbody></table></div>
      </section>
      <section className="sector-limits-grid">
        <article><span>{t('sector.themeEyebrow')}</span><h2>{t('sector.themeUnavailable')}</h2><p>{t('sector.themeReason')}</p></article>
        <article><span>{t('sector.useEyebrow')}</span><h2>{t('sector.howToUse')}</h2><p>{t('sector.howToUseBody')}</p></article>
      </section>
      <details className="sector-method"><summary>{t('sector.methodTitle')}</summary><p>{t('sector.methodBody', { count: data.input_session_count })}</p></details>
    </main>
  );
}

export function SectorRotationPage({ universeId }: { universeId: string }): JSX.Element {
  const { t } = useI18n();
  const [state, setState] = useState<LoadState>({ kind: 'loading' });
  useEffect(() => {
    const controller = new AbortController();
    void getSectorRotation(controller.signal).then((data) => setState({ kind: 'ready', data })).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ kind: 'error', message: localizeClientError(t, error instanceof Error ? error.message : String(error)) });
    });
    return () => controller.abort();
  }, [t]);
  if (state.kind === 'loading') return <main className="sector-page sector-message"><p>{t('sector.loading')}</p></main>;
  if (state.kind === 'error') return <main className="sector-page sector-message"><h1>{t('sector.unavailable')}</h1><p>{state.message}</p><small>{t('sector.failClosed')}</small></main>;
  return <SectorRotationContent data={state.data} universeId={universeId} />;
}
