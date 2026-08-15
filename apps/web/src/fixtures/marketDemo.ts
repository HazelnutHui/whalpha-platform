import type { DashboardData, EodReturnResponse, LiquidityMapNodeResponse } from '../api/types';

const base = {
  instrument_type: 'common_stock',
  current_session_date: '2026-08-13',
  previous_session_date: '2026-08-12',
  previous_close: '100',
  current_volume: '1250000.5',
  current_vwap: '101.25',
  quality_status: 'ok',
  quality_flags: ['synthetic_demo_fixture'],
};

function mover(rank: number, ticker: string, ret: string, close: string): EodReturnResponse {
  return {
    ...base,
    instrument_id: `00000000-0000-5000-8000-0000000000${String(rank).padStart(2, '0')}`,
    ticker,
    name: `${ticker} Synthetic Holdings`,
    current_close: close,
    close_to_close_return: ret,
    current_dollar_volume_proxy: String(Number(close) * 1_250_000.5),
  };
}

const gainers = Array.from({ length: 10 }, (_, index) => mover(index + 1, `TEST${String.fromCharCode(65 + index)}`, String(0.082 - index * 0.006), String(42 + index)));
const losers = Array.from({ length: 10 }, (_, index) => mover(index + 21, `TEST${String.fromCharCode(75 + index)}`, String(-0.074 + index * 0.005), String(88 - index)));

const nodes: LiquidityMapNodeResponse[] = [...gainers, ...losers].map((item, index) => ({
  instrument_id: item.instrument_id,
  ticker: item.ticker,
  name: item.name,
  instrument_type: item.instrument_type,
  size_value: item.current_dollar_volume_proxy,
  color_value: item.close_to_close_return,
  current_close: item.current_close,
  current_volume: item.current_volume,
  rank: index + 1,
  quality_flags: item.quality_flags,
}));

export const demoDashboardData: DashboardData = {
  summary: {
    current_session_date: '2026-08-13',
    previous_session_date: '2026-08-12',
    comparable_instrument_count: 240,
    current_only_count: 7,
    previous_only_count: 5,
    advancer_count: 136,
    decliner_count: 91,
    unchanged_count: 13,
    advance_decline_ratio: '1.4945054945',
    advance_decline_net: 45,
    advancer_volume: '185000000.75',
    decliner_volume: '132000000.25',
    up_down_volume_ratio: '1.4015151515',
    equal_weight_return: '0.0064',
    median_return: '0.0021',
    positive_return_share: '0.5666666667',
    negative_return_share: '0.3791666667',
    common_stock_comparable_count: 188,
    etf_comparable_count: 52,
    quality_warning_count: 4,
    data_status: 'synthetic_demo',
  },
  movers: {
    current_session_date: '2026-08-13',
    previous_session_date: '2026-08-12',
    threshold: '5000000',
    top_gainers: gainers,
    top_losers: losers,
  },
  liquidityMap: {
    map_type: 'liquidity',
    size_metric: 'close_times_volume_proxy',
    color_metric: 'close_to_close_return',
    is_market_cap_weighted: false,
    is_sector_grouped: false,
    threshold: '5000000',
    current_session_date: '2026-08-13',
    previous_session_date: '2026-08-12',
    nodes,
  },
};
