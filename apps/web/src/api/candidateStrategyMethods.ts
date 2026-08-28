import type { StrategyAssessment, StrategyChannel, StrategyEvidence } from './candidateStrategies';

export const STRATEGY_METHOD_PARAMETER_FINGERPRINT = '13312df3e5b132223878582b8cd3af533a880e9f2f0d520f8520b46b97138ac9';

export type TechnicalStrategyChannel = 'momentum_breakout' | 'strong_stock_pullback' | 'trend_continuation';

export interface StrategyMethodComponent {
  component_id: string;
  weight_bps: number;
}

export interface StrategyMethod {
  channel: TechnicalStrategyChannel;
  components: StrategyMethodComponent[];
  geometry_scores: Record<string, string>;
  status_rule: 'momentum_breakout' | 'strong_stock_pullback' | 'trend_continuation';
  ranking_rule: 'advance_then_watch_score_desc_ticker_stable_id';
}

export interface StrategyScoreContribution {
  component_id: string;
  input_score: string;
  weight_bps: number;
  contribution: string;
}

const METHODS: Record<TechnicalStrategyChannel, StrategyMethod> = {
  momentum_breakout: {
    channel: 'momentum_breakout',
    components: [
      { component_id: 'stock_relative_strength', weight_bps: 3500 },
      { component_id: 'trend_quality', weight_bps: 2500 },
      { component_id: 'volume_participation', weight_bps: 1500 },
      { component_id: 'entry_geometry', weight_bps: 2500 },
    ],
    geometry_scores: {
      breakout_confirmed: '100.0000', breakout_watch: '70.0000', pullback: '25.0000',
      strong_but_extended: '15.0000', no_viable_setup: '20.0000',
    },
    status_rule: 'momentum_breakout',
    ranking_rule: 'advance_then_watch_score_desc_ticker_stable_id',
  },
  strong_stock_pullback: {
    channel: 'strong_stock_pullback',
    components: [
      { component_id: 'stock_relative_strength', weight_bps: 3000 },
      { component_id: 'trend_quality', weight_bps: 2500 },
      { component_id: 'volatility_risk', weight_bps: 1500 },
      { component_id: 'liquidity_suitability', weight_bps: 1000 },
      { component_id: 'entry_geometry', weight_bps: 2000 },
    ],
    geometry_scores: {
      breakout_confirmed: '25.0000', breakout_watch: '35.0000', pullback: '100.0000',
      strong_but_extended: '55.0000', no_viable_setup: '20.0000',
    },
    status_rule: 'strong_stock_pullback',
    ranking_rule: 'advance_then_watch_score_desc_ticker_stable_id',
  },
  trend_continuation: {
    channel: 'trend_continuation',
    components: [
      { component_id: 'stock_relative_strength', weight_bps: 3500 },
      { component_id: 'trend_quality', weight_bps: 3500 },
      { component_id: 'volume_participation', weight_bps: 1500 },
      { component_id: 'volatility_risk', weight_bps: 1000 },
      { component_id: 'entry_geometry', weight_bps: 500 },
    ],
    geometry_scores: {
      breakout_confirmed: '85.0000', breakout_watch: '70.0000', pullback: '85.0000',
      strong_but_extended: '35.0000', no_viable_setup: '50.0000',
    },
    status_rule: 'trend_continuation',
    ranking_rule: 'advance_then_watch_score_desc_ticker_stable_id',
  },
};

export function isTechnicalStrategyChannel(channel: StrategyChannel): channel is TechnicalStrategyChannel {
  return channel in METHODS;
}

export function strategyMethod(
  channel: StrategyChannel,
  parameterFingerprint: unknown,
): StrategyMethod | null {
  if (parameterFingerprint !== STRATEGY_METHOD_PARAMETER_FINGERPRINT) {
    throw new Error('Unsupported strategy methodology parameter fingerprint');
  }
  return isTechnicalStrategyChannel(channel) ? METHODS[channel] : null;
}

export function strategyScoreBreakdown(
  item: StrategyAssessment,
  parameterFingerprint: unknown,
): StrategyScoreContribution[] {
  const method = strategyMethod(item.channel, parameterFingerprint);
  if (!method || item.channel_score === null) return [];
  const byId = new Map(item.evidence.map((row) => [row.evidence_id, row]));
  const setup = requiredEvidence(byId, 'entry_technical_setup').observed_value;
  if (setup === null || !(setup in method.geometry_scores)) {
    throw new Error('Strategy entry geometry does not match the frozen methodology');
  }
  let unroundedTotal = 0n;
  const rows = method.components.map((component) => {
    const input = component.component_id === 'entry_geometry'
      ? method.geometry_scores[setup]
      : requiredEvidence(byId, `component_${component.component_id}`).observed_value;
    if (input === null) throw new Error('Strategy score component is unavailable');
    const inputScaled = decimal4(input);
    const unrounded = inputScaled * BigInt(component.weight_bps);
    unroundedTotal += unrounded;
    return {
      component_id: component.component_id,
      input_score: format4(inputScaled),
      weight_bps: component.weight_bps,
      contribution: format4(roundHalfEven(unrounded, 10_000n)),
    };
  });
  if (format4(roundHalfEven(unroundedTotal, 10_000n)) !== format4(decimal4(item.channel_score))) {
    throw new Error('Strategy score does not reconstruct from the frozen methodology');
  }
  return rows;
}

function requiredEvidence(
  byId: Map<string, StrategyEvidence>,
  evidenceId: string,
): StrategyEvidence {
  const result = byId.get(evidenceId);
  if (!result || result.availability !== 'available') {
    throw new Error(`Strategy methodology evidence is unavailable: ${evidenceId}`);
  }
  return result;
}

function decimal4(value: string): bigint {
  const match = /^(\d+)(?:\.(\d{1,4}))?$/.exec(value);
  if (!match) throw new Error('Strategy methodology decimal is malformed');
  return BigInt(match[1]) * 10_000n + BigInt((match[2] ?? '').padEnd(4, '0'));
}

function roundHalfEven(value: bigint, divisor: bigint): bigint {
  const quotient = value / divisor;
  const remainder = value % divisor;
  const doubled = remainder * 2n;
  if (doubled > divisor || (doubled === divisor && quotient % 2n === 1n)) return quotient + 1n;
  return quotient;
}

function format4(value: bigint): string {
  const whole = value / 10_000n;
  const fraction = (value % 10_000n).toString().padStart(4, '0');
  return `${whole}.${fraction}`;
}
