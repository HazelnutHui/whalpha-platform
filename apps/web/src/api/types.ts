export type DecimalString = string;

export type InstrumentType = 'common_stock' | 'etf';

export interface EodReturnResponse {
  instrument_id: string;
  ticker: string;
  name: string;
  instrument_type: string;
  current_session_date: string;
  previous_session_date: string;
  previous_close: DecimalString;
  current_close: DecimalString;
  close_to_close_return: DecimalString;
  current_volume: DecimalString;
  current_vwap: DecimalString | null;
  current_dollar_volume_proxy: DecimalString;
  quality_status: string;
  quality_flags: string[];
}

export interface MarketSummaryResponse {
  current_session_date: string;
  previous_session_date: string;
  comparable_instrument_count: number;
  current_only_count: number;
  previous_only_count: number;
  advancer_count: number;
  decliner_count: number;
  unchanged_count: number;
  advance_decline_ratio: DecimalString | null;
  advance_decline_net: number;
  advancer_volume: DecimalString;
  decliner_volume: DecimalString;
  up_down_volume_ratio: DecimalString | null;
  equal_weight_return: DecimalString | null;
  median_return: DecimalString | null;
  positive_return_share: DecimalString | null;
  negative_return_share: DecimalString | null;
  common_stock_comparable_count: number;
  etf_comparable_count: number;
  quality_warning_count: number;
  data_status: string;
}

export interface MoversResponse {
  current_session_date: string;
  previous_session_date: string;
  threshold: DecimalString;
  top_gainers: EodReturnResponse[];
  top_losers: EodReturnResponse[];
}

export interface LiquidityMapNodeResponse {
  instrument_id: string;
  ticker: string;
  name: string;
  instrument_type: string;
  size_value: DecimalString;
  color_value: DecimalString;
  current_close: DecimalString;
  current_volume: DecimalString;
  rank: number;
  quality_flags: string[];
}

export interface LiquidityMapResponse {
  map_type: string;
  size_metric: string;
  color_metric: string;
  is_market_cap_weighted: boolean;
  is_sector_grouped: boolean;
  threshold: DecimalString;
  current_session_date: string;
  previous_session_date: string;
  nodes: LiquidityMapNodeResponse[];
}

export interface DashboardData {
  summary: MarketSummaryResponse;
  movers: MoversResponse;
  liquidityMap: LiquidityMapResponse;
}
