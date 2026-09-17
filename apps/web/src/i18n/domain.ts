import type { MessageKey } from './catalog';
import type { Translate } from './I18nProvider';

const UNIVERSE_KEYS: Record<string, MessageKey> = {
  provider_classified_common_shares_v1: 'universe.primary',
  provider_classified_common_shares_plus_adrs_v1: 'universe.secondary',
  china_a_share_research_foundation_v1: 'universe.ashare',
};
const UNIVERSE_DESCRIPTION_KEYS: Record<string, MessageKey> = {
  provider_classified_common_shares_v1: 'universe.primaryDescription',
  provider_classified_common_shares_plus_adrs_v1: 'universe.secondaryDescription',
  china_a_share_research_foundation_v1: 'universe.ashareDescription',
};
const STATE_KEYS: Record<string, MessageKey> = {
  risk_on: 'state.risk_on', balanced: 'state.balanced', defensive: 'state.defensive', stress: 'state.stress', unavailable: 'state.unavailable',
};
const STATE_SUMMARY_KEYS: Record<string, MessageKey> = {
  risk_on: 'state.summary.risk_on', balanced: 'state.summary.balanced', defensive: 'state.summary.defensive', stress: 'state.summary.stress',
};
const EVIDENCE_KEYS: Record<string, MessageKey> = {
  support: 'evidence.support', neutral: 'evidence.neutral', drag: 'evidence.drag',
};
const DIMENSION_KEYS: Record<string, MessageKey> = {
  trend: 'dimension.trend', breadth: 'dimension.breadth', volatility: 'dimension.volatility',
  liquidity_participation: 'dimension.liquidity_participation', leadership_dispersion: 'dimension.leadership_dispersion',
};
const DIMENSION_SHORT_KEYS: Record<string, MessageKey> = {
  trend: 'dimension.short.trend', breadth: 'dimension.short.breadth', volatility: 'dimension.short.volatility',
  liquidity_participation: 'dimension.short.liquidity_participation', leadership_dispersion: 'dimension.short.leadership_dispersion',
};
const DIMENSION_AUDIT_KEYS: Record<string, MessageKey> = {
  trend: 'dimension.audit.trend', breadth: 'dimension.audit.breadth', volatility: 'dimension.audit.volatility',
  liquidity_participation: 'dimension.audit.liquidity_participation', leadership_dispersion: 'dimension.audit.leadership_dispersion',
};
const RELATIONSHIP_KEYS: Record<string, MessageKey> = {
  synchronous_strengthening: 'relationship.synchronous_strengthening', synchronous_weakening: 'relationship.synchronous_weakening',
  divergence: 'relationship.divergence', rotation_candidate: 'relationship.rotation_candidate',
  relationship_break_candidate: 'relationship.relationship_break_candidate', neutral: 'relationship.neutral', unavailable: 'relationship.unavailable',
};
const CONFIDENCE_KEYS: Record<string, MessageKey> = { low: 'confidence.low', medium: 'confidence.medium', high: 'confidence.high' };
const FAMILY_KEYS: Record<string, MessageKey> = {
  growth_vs_broad: 'family.growth_vs_broad', style_rotation: 'family.style_rotation', size_participation: 'family.size_participation',
  cyclical_defensive: 'family.cyclical_defensive', sector_relative: 'family.sector_relative', defensive_relative: 'family.defensive_relative',
  industry_within_growth: 'family.industry_within_growth', industry_within_sector: 'family.industry_within_sector',
  credit_risk: 'family.credit_risk', credit_vs_duration: 'family.credit_vs_duration',
};
const REASON_KEYS: Record<string, MessageKey> = {
  candidate_band_balanced: 'reason.candidate_band_balanced', confirmed_state_held: 'reason.confirmed_state_held',
  state_input_available: 'reason.state_input_available', short_history_low_confidence: 'reason.short_history_low_confidence',
  short_history_limits_reliability: 'reason.short_history_limits_reliability',
  both_five_session_returns_negative: 'reason.both_five_session_returns_negative',
  both_five_session_returns_positive: 'reason.both_five_session_returns_positive',
  positive_correlation_threshold_met: 'reason.positive_correlation_threshold_met',
  five_session_spread_threshold_met: 'reason.five_session_spread_threshold_met', opposite_return_signs: 'reason.opposite_return_signs',
  relative_strength_direction_differs_across_windows: 'reason.relative_strength_direction_differs_across_windows',
  correlation_threshold_not_stable_across_18_20_22_windows: 'reason.correlation_threshold_not_stable_across_18_20_22_windows',
  no_higher_priority_relationship_rule_met: 'reason.no_higher_priority_relationship_rule_met', confidence_low: 'reason.confidence_low',
  dimension_available: 'reason.dimension_available',
};
const METRIC_KEYS: Record<string, MessageKey> = {
  broad_return_5: 'metric.broad_return_5', broad_return_20: 'metric.broad_return_20',
  benchmark_direction_agreement_5: 'metric.benchmark_direction_agreement_5', above_sma20_share: 'metric.above_sma20_share',
  advancer_share_1: 'metric.advancer_share_1', positive_return_share_5: 'metric.positive_return_share_5',
  high_low_balance_20: 'metric.high_low_balance_20', broad_above_sma20_share: 'metric.broad_above_sma20_share',
  spy_realized_volatility_10: 'metric.spy_realized_volatility_10',
  median_stock_realized_volatility_10: 'metric.median_stock_realized_volatility_10',
  downside_tail_frequency_5: 'metric.downside_tail_frequency_5', aggregate_participation_ratio: 'metric.aggregate_participation_ratio',
  up_participation_share: 'metric.up_participation_share', above_own_volume_median_share: 'metric.above_own_volume_median_share',
  broad_direction_agreement: 'metric.broad_direction_agreement', cross_sectional_dispersion_1: 'metric.cross_sectional_dispersion_1',
  return_dispersion_5: 'metric.return_dispersion_5', winner_concentration_5: 'metric.winner_concentration_5',
};
const UNIT_KEYS: Record<string, MessageKey> = { ratio: 'unit.ratio', annualized_ratio: 'unit.annualized_ratio' };
const FUNNEL_KEYS: Record<string, MessageKey> = {
  provider_evidence_base: 'funnel.provider_evidence_base', target_security_form: 'funnel.target_security_form',
  supported_exchange: 'funnel.supported_exchange', comparable_bars: 'funnel.comparable_bars', previous_close: 'funnel.previous_close',
  history_completeness: 'funnel.history_completeness', trailing_liquidity: 'funnel.trailing_liquidity',
  outlier_quarantine: 'funnel.outlier_quarantine', reviewed_overlay: 'funnel.reviewed_overlay', final_membership: 'funnel.final_membership',
};
const SECTOR_KEYS: Record<string, MessageKey> = {
  'Communication Services': 'sector.communication_services', 'Consumer Discretionary': 'sector.consumer_discretionary',
  'Consumer Staples': 'sector.consumer_staples', Energy: 'sector.energy', Financials: 'sector.financials',
  'Health Care': 'sector.health_care', Industrials: 'sector.industrials', Materials: 'sector.materials',
  'Real Estate': 'sector.real_estate', Technology: 'sector.technology', Utilities: 'sector.utilities',
};
const FLAG_KEYS: Record<string, MessageKey> = {
  unverified_price_discontinuity: 'flag.unverified_price_discontinuity', identity_conflict: 'flag.identity_conflict',
  missing_required_benchmark: 'flag.missing_required_benchmark', adjustment_factors_unverified: 'flag.adjustment_factors_unverified',
};
const BENCHMARK_KEYS: Record<string, MessageKey> = {
  spy: 'dashboard.benchmark.spy', qqq: 'dashboard.benchmark.qqq', iwm: 'dashboard.benchmark.iwm', dia: 'dashboard.benchmark.dia',
  equal_weight_universe: 'dashboard.benchmark.equalWeight',
};
const WARNING_KEYS: Record<string, MessageKey> = {
  'Only 26 completed XNYS sessions are available; reliability measures describe data completeness and rule agreement, not predictive probability.': 'warning.shortHistory',
  'The 16 ETF pairs are preregistered; the preview does not search the market for favorable relationships.': 'warning.preregistered',
  'Statistical relationships are contemporaneous observations, not evidence of causation.': 'warning.nonCausal',
  'Price and volume relationships are participation proxies, not fund flow.': 'warning.notFundFlow',
  'This research context is not a trade recommendation or a backtest result.': 'warning.notRecommendation',
};

type PairField = 'rationale' | 'expected' | 'forbidden';
const PAIR_IDS = new Set([
  'growth_broad', 'growth_value', 'small_large', 'mid_large', 'consumer_risk', 'technology_defensive',
  'industrial_defensive', 'financial_defensive', 'energy_broad', 'health_broad', 'semis_growth',
  'biotech_health', 'regional_financials', 'software_growth', 'credit_quality', 'credit_duration',
]);

function translated(t: Translate, mapping: Record<string, MessageKey>, value: string, fallback: string): string {
  const key = mapping[value];
  return key ? t(key) : fallback;
}

export const universeName = (t: Translate, universeId: string, fallback = ''): string => translated(t, UNIVERSE_KEYS, universeId, fallback || t('universe.unknown'));
export const universeDescription = (t: Translate, universeId: string, fallback = ''): string => translated(t, UNIVERSE_DESCRIPTION_KEYS, universeId, fallback);
export const stateName = (t: Translate, value: string | null): string => translated(t, STATE_KEYS, value ?? 'unavailable', t('state.unavailable'));
export const stateSummary = (t: Translate, value: string): string => translated(t, STATE_SUMMARY_KEYS, value, t('state.unavailable'));
export const evidenceName = (t: Translate, value: string): string => translated(t, EVIDENCE_KEYS, value, value);
export const dimensionName = (t: Translate, value: string): string => translated(t, DIMENSION_KEYS, value, value);
export const dimensionShortName = (t: Translate, value: string): string => translated(t, DIMENSION_SHORT_KEYS, value, value);
export const dimensionAuditText = (t: Translate, value: string): string => translated(t, DIMENSION_AUDIT_KEYS, value, t('reason.unknown'));
export const relationshipName = (t: Translate, value: string | null): string => translated(t, RELATIONSHIP_KEYS, value ?? 'unavailable', t('relationship.unavailable'));
export const confidenceName = (t: Translate, value: string): string => translated(t, CONFIDENCE_KEYS, value, value);
export const familyName = (t: Translate, value: string): string => translated(t, FAMILY_KEYS, value, value);
export const reasonText = (t: Translate, value: string): string => translated(t, REASON_KEYS, value, t('reason.unknown'));
export const metricName = (t: Translate, value: string): string => translated(t, METRIC_KEYS, value, value);
export const unitName = (t: Translate, value: string): string => translated(t, UNIT_KEYS, value, value);
export const funnelName = (t: Translate, value: string, fallback: string): string => translated(t, FUNNEL_KEYS, value, fallback);
export const sectorName = (t: Translate, value: string): string => translated(t, SECTOR_KEYS, value, value);
export const flagName = (t: Translate, value: string): string => translated(t, FLAG_KEYS, value, value);
export const benchmarkName = (t: Translate, value: string, fallback: string): string => translated(t, BENCHMARK_KEYS, value, fallback);
export function validationStatusName(t: Translate, value: string): string {
  return value === 'file_schema_consistency_checks_passed' ? t('dashboard.validationPassed') : value;
}
export function dashboardFunnelName(t: Translate, stageId: string, fallback: string, index: number): string {
  if (stageId.startsWith('synthetic_stage_')) return t('funnel.synthetic', { index });
  return funnelName(t, stageId, fallback);
}
export const warningText = (t: Translate, value: string): string => translated(t, WARNING_KEYS, value, value);
export function pairText(t: Translate, pairId: string, field: PairField, fallback: string): string {
  if (!PAIR_IDS.has(pairId)) return fallback;
  return t(`pair.${pairId}.${field}` as MessageKey);
}

export function localizeClientError(t: Translate, message: string): string {
  const match = /status (\d{3})/.exec(message);
  if (match) return t('common.apiErrorStatus', { status: match[1] });
  if (/timed out|cancelled/i.test(message)) return t('common.apiErrorTimeout');
  if (/invalid|unsupported|incomplete|duplicate|ordering|validation/i.test(message)) return t('common.apiErrorInvalid');
  return t('common.apiError');
}
