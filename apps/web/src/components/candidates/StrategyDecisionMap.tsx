import type { CandidateExtensionRisk } from '../../api/opportunityCandidates';
import { useI18n } from '../../i18n/I18nProvider';

export type StrategyDecisionMapReadiness =
  | 'technical_review_ready'
  | 'wait_for_setup'
  | 'risk_gates_reject'
  | 'unavailable';

export interface StrategyDecisionMapPoint {
  instrumentId: string;
  ticker: string;
  rank: number;
  score: number;
  extensionRisk: CandidateExtensionRisk;
  readiness: StrategyDecisionMapReadiness;
  repeated: boolean;
}

const EXTENSION_ORDER = ['low', 'moderate', 'high', 'extreme'] as const;
const X_POSITIONS: Record<Exclude<CandidateExtensionRisk, 'unavailable'>, number> = {
  low: 125,
  moderate: 305,
  high: 485,
  extreme: 665,
};

function pointX(point: StrategyDecisionMapPoint, points: StrategyDecisionMapPoint[]): number {
  if (point.extensionRisk === 'unavailable') return 0;
  const peers = points.filter((item) => item.extensionRisk === point.extensionRisk);
  const index = peers.findIndex((item) => item.instrumentId === point.instrumentId);
  return X_POSITIONS[point.extensionRisk] + (index - (peers.length - 1) / 2) * 28;
}

function pointY(score: number): number {
  return 272 - Math.max(0, Math.min(100, score)) * 2.35;
}

export function StrategyDecisionMap({
  channelName,
  points,
  onSelect,
}: {
  channelName: string;
  points: StrategyDecisionMapPoint[];
  onSelect: (instrumentId: string) => void;
}): JSX.Element {
  const { t } = useI18n();
  const plotted = points.filter((item) => item.extensionRisk !== 'unavailable');
  const unavailable = points.length - plotted.length;
  const ready = points.filter((item) => item.readiness === 'technical_review_ready').length;
  const waiting = points.filter((item) => item.readiness === 'wait_for_setup').length;
  const rejected = points.filter((item) => item.readiness === 'risk_gates_reject').length;
  const extended = points.filter((item) => item.extensionRisk === 'high' || item.extensionRisk === 'extreme').length;
  const gridScores = [100, 75, 50, 25, 0];

  return <section className="panel strategy-decision-map" aria-labelledby="strategy-decision-map-title">
    <header>
      <div><p className="eyebrow">{t('candidate.strategy.mapEyebrow')}</p><h2 id="strategy-decision-map-title">{t('candidate.strategy.mapTitle')}</h2></div>
      <p>{t('candidate.strategy.mapBody').replace('{channel}', channelName)}</p>
    </header>
    <div className="strategy-decision-map-summary">
      <span>{t('candidate.strategy.mapSummaryReady')} <strong>{ready}</strong></span>
      <span>{t('candidate.strategy.mapSummaryWait')} <strong>{waiting}</strong></span>
      <span>{t('candidate.strategy.mapSummaryRejected')} <strong>{rejected}</strong></span>
      <span>{t('candidate.strategy.mapSummaryExtended')} <strong>{extended}</strong></span>
      {unavailable ? <span>{t('candidate.strategy.mapSummaryUnavailable')} <strong>{unavailable}</strong></span> : null}
    </div>
    <div className="strategy-decision-map-frame">
      <span className="strategy-decision-map-y-label">{t('candidate.strategy.mapYAxis')}</span>
      <svg viewBox="0 0 780 330" role="img" aria-label={t('candidate.strategy.mapAria').replace('{channel}', channelName)}>
        {gridScores.map((score) => <g className="strategy-map-grid" key={score}>
          <line x1="70" x2="750" y1={pointY(score)} y2={pointY(score)} />
          <text x="58" y={pointY(score) + 4} textAnchor="end">{score}</text>
        </g>)}
        {EXTENSION_ORDER.map((risk) => <g className="strategy-map-axis" key={risk}>
          <line x1={X_POSITIONS[risk]} x2={X_POSITIONS[risk]} y1="37" y2="272" />
          <text x={X_POSITIONS[risk]} y="305" textAnchor="middle">{t(`candidate.entry.extension.${risk}` as never)}</text>
        </g>)}
        {plotted.map((point) => {
          const x = pointX(point, plotted);
          const y = pointY(point.score);
          const aria = t('candidate.strategy.mapPointAria')
            .replace('{ticker}', point.ticker)
            .replace('{rank}', String(point.rank))
            .replace('{score}', point.score.toFixed(1))
            .replace('{extension}', t(`candidate.entry.extension.${point.extensionRisk}` as never));
          return <g
            className={`strategy-map-point strategy-map-point-${point.readiness} ${point.repeated ? 'strategy-map-point-repeated' : ''}`}
            key={point.instrumentId}
            role="button"
            tabIndex={0}
            aria-label={aria}
            onClick={() => onSelect(point.instrumentId)}
            onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(point.instrumentId); } }}
          >
            {point.repeated ? <circle cx={x} cy={y} r="11" className="strategy-map-repeat-ring" /> : null}
            <circle cx={x} cy={y} r="7" />
            <text x={x} y={y - 13} textAnchor="middle">{point.ticker}</text>
            <text x={x} y={y + 22} textAnchor="middle" className="strategy-map-rank">#{point.rank}</text>
          </g>;
        })}
      </svg>
      <span className="strategy-decision-map-x-label">{t('candidate.strategy.mapXAxis')}</span>
    </div>
    <div className="strategy-decision-map-legend" aria-label={t('candidate.strategy.mapLegend')}>
      <span className="strategy-map-legend-ready">{t('candidate.strategy.readiness.technical_review_ready')}</span>
      <span className="strategy-map-legend-wait">{t('candidate.strategy.readiness.wait_for_setup')}</span>
      <span className="strategy-map-legend-reject">{t('candidate.strategy.readiness.risk_gates_reject')}</span>
      <span className="strategy-map-legend-unavailable">{t('candidate.strategy.readiness.unavailable')}</span>
      <span className="strategy-map-legend-repeat">{t('candidate.strategy.mapRepeat')}</span>
    </div>
    <p className="strategy-decision-map-boundary">{t('candidate.strategy.mapBoundary')}</p>
  </section>;
}
