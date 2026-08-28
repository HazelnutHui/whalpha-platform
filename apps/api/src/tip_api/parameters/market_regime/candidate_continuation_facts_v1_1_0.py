"""Frozen parameters for descriptive Candidate continuation and breakout facts."""

from __future__ import annotations

import hashlib
import json


CONTINUATION_FACTS_CONTRACT_VERSION = "candidate-continuation-facts/1.1"
CONTINUATION_FACTS_CALCULATION_VERSION = "candidate-continuation-facts-v1.1.0"
CONTINUATION_FACTS_PARAMETER_SET_ID = "candidate-continuation-facts-v1-descriptive-2"
CONTINUATION_FACTS_PANEL_SESSION_COUNT = 26
CONTINUATION_FACTS_REQUIRED_SESSION_COUNT = 21
CONTINUATION_FACTS_RETURN_WINDOW = 10
CONTINUATION_FACTS_SMA_WINDOW = 10
CONTINUATION_FACTS_SMA_SLOPE_LAG = 5
CONTINUATION_FACTS_ATR_SHORT_WINDOW = 5
CONTINUATION_FACTS_ATR_LONG_WINDOW = 14
CONTINUATION_FACTS_STRUCTURE_WINDOW = 5
CONTINUATION_FACTS_RECENT_VOLUME_WINDOW = 5
CONTINUATION_FACTS_PRIOR_VOLUME_WINDOW = 15
CONTINUATION_FACTS_RAW_DECIMAL_SCALE = 10


def continuation_facts_parameter_payload() -> dict[str, object]:
    return {
        "contract_version": CONTINUATION_FACTS_CONTRACT_VERSION,
        "calculation_version": CONTINUATION_FACTS_CALCULATION_VERSION,
        "parameter_set_id": CONTINUATION_FACTS_PARAMETER_SET_ID,
        "purpose": "descriptive_continuation_facts_not_strategy_score_or_signal",
        "history": {
            "panel_session_count": CONTINUATION_FACTS_PANEL_SESSION_COUNT,
            "required_session_count": CONTINUATION_FACTS_REQUIRED_SESSION_COUNT,
            "return_window": CONTINUATION_FACTS_RETURN_WINDOW,
            "sma_window": CONTINUATION_FACTS_SMA_WINDOW,
            "sma_slope_lag": CONTINUATION_FACTS_SMA_SLOPE_LAG,
            "atr_windows": [
                CONTINUATION_FACTS_ATR_SHORT_WINDOW,
                CONTINUATION_FACTS_ATR_LONG_WINDOW,
            ],
            "structure_window": CONTINUATION_FACTS_STRUCTURE_WINDOW,
            "volume_windows": [
                CONTINUATION_FACTS_RECENT_VOLUME_WINDOW,
                CONTINUATION_FACTS_PRIOR_VOLUME_WINDOW,
            ],
        },
        "facts": {
            "net_return_10": "close_t_over_close_t_minus_10_minus_1",
            "information_discreteness_10": (
                "sign_net_return_times_negative_share_minus_positive_share_"
                "over_nonzero_returns"
            ),
            "return_path_efficiency_10": (
                "absolute_sum_log_returns_over_sum_absolute_log_returns"
            ),
            "largest_absolute_return_share_10": (
                "largest_absolute_log_return_over_sum_absolute_log_returns"
            ),
            "positive_return_share_10": "positive_simple_returns_over_ten",
            "above_sma10_share_10": "recent_closes_above_contemporaneous_sma10_over_ten",
            "sma10_slope_5_atr": "sma10_t_minus_sma10_t_minus_5_over_atr14",
            "atr_5_to_14": "atr5_over_atr14",
            "close_drawdown_from_high_20_atr": (
                "highest_twenty_session_close_minus_current_close_over_atr14"
            ),
            "recent_close_low_vs_prior_5_atr": (
                "recent_five_close_low_minus_prior_five_close_low_over_atr14"
            ),
            "recent_close_high_vs_prior_5_atr": (
                "recent_five_close_high_minus_prior_five_close_high_over_atr14"
            ),
            "recent_volume_median_ratio_5_to_prior_15": (
                "recent_five_median_volume_over_prior_fifteen_median_volume"
            ),
            "prior_10_close_range_atr": "prior_ten_close_range_over_prior_atr14",
            "prior_atr_5_to_14": "prior_atr5_over_prior_atr14",
            "close_vs_prior_20_close_high_atr": (
                "current_close_minus_prior_twenty_close_high_over_prior_atr14"
            ),
            "current_close_move_atr": (
                "current_close_minus_prior_close_over_prior_atr14"
            ),
            "current_intraday_move_atr": (
                "current_close_minus_current_open_over_prior_atr14"
            ),
            "current_absolute_return_share_10": (
                "current_absolute_log_return_over_last_ten_absolute_log_return_path"
            ),
        },
        "numeric_publication": {
            "raw_decimal_scale": CONTINUATION_FACTS_RAW_DECIMAL_SCALE,
            "rounding": "round_half_even",
        },
        "boundaries": [
            "short_window_adaptation_not_published_factor_replication",
            "descriptive_facts_not_strategy_score_or_status",
            "no_outcome_fitted_thresholds",
            "price_volume_not_fund_flow",
            "underlying_stock_result_not_option_return",
        ],
    }


CONTINUATION_FACTS_PARAMETER_FINGERPRINT = hashlib.sha256(
    json.dumps(
        continuation_facts_parameter_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
).hexdigest()
