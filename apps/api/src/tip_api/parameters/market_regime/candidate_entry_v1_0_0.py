"""Frozen parameters for the additive Candidate entry-geometry shadow layer."""

from __future__ import annotations

import hashlib
import json


ENTRY_GEOMETRY_CONTRACT_VERSION = "candidate-entry-geometry/1.0"
ENTRY_GEOMETRY_CALCULATION_VERSION = "candidate-entry-geometry-v1.0.0"
ENTRY_GEOMETRY_PARAMETER_SET_ID = "candidate-entry-geometry-v1-fixed-baseline-1"
ENTRY_GEOMETRY_PANEL_SESSION_COUNT = 26
ENTRY_GEOMETRY_ATR_WINDOW = 14
ENTRY_GEOMETRY_SMA_SHORT_WINDOW = 10
ENTRY_GEOMETRY_SMA_LONG_WINDOW = 20
ENTRY_GEOMETRY_PRIOR_BREAKOUT_WINDOW = 5
ENTRY_GEOMETRY_RETURN_WINDOWS = (3, 5)
ENTRY_GEOMETRY_TRAILING_UP_CAP = 5
ENTRY_GEOMETRY_RAW_DECIMAL_SCALE = 10
ENTRY_GEOMETRY_SCORE_FLOOR = "50"
ENTRY_GEOMETRY_STRONG_SCORE = "65"
ENTRY_GEOMETRY_BREAKOUT_SCORE = "70"
ENTRY_GEOMETRY_COMPONENT_FLOOR = "55"
ENTRY_GEOMETRY_TREND_KILL_FLOOR = "50"

# Extension thresholds are dimensionless. ATR distances compare price location
# with the instrument's own recent trading range; move units compare the
# five-session return with its own ten-return realized volatility.
MODERATE_SMA20_EXTENSION_ATR = "1.50"
HIGH_SMA20_EXTENSION_ATR = "2.50"
EXTREME_SMA20_EXTENSION_ATR = "3.50"
MODERATE_MOVE_5_VOLATILITY_UNITS = "1.00"
HIGH_MOVE_5_VOLATILITY_UNITS = "1.75"
EXTREME_MOVE_5_VOLATILITY_UNITS = "2.50"
MODERATE_SMA10_EXTENSION_ATR = "1.00"
HIGH_SMA10_EXTENSION_ATR = "1.50"
MODERATE_TRAILING_UP_SESSIONS = 3
HIGH_TRAILING_UP_SESSIONS = 4
MODERATE_POSITIVE_GAP_ATR = "1.00"
EXTREME_POSITIVE_GAP_ATR = "1.50"
VOLUME_CLIMAX_RATIO = "2.00"
VOLUME_CLIMAX_RANGE_ATR = "1.50"
VOLUME_CLIMAX_CLOSE_LOCATION = "0.75"

# Setup rules deliberately define technical-review candidates, not orders.
BREAKOUT_MAX_DISTANCE_ATR = "0.75"
BREAKOUT_MIN_VOLUME_RATIO = "1.20"
BREAKOUT_MAX_VOLUME_RATIO = "2.50"
BREAKOUT_MIN_CLOSE_LOCATION = "0.60"
BREAKOUT_WATCH_MAX_DISTANCE_ATR = "0.75"
BREAKOUT_WATCH_MAX_VOLUME_RATIO = "2.00"
PULLBACK_SMA10_DISTANCE_ATR = "0.75"
PULLBACK_FROM_HIGH_MIN_ATR = "0.25"
PULLBACK_FROM_HIGH_MAX_ATR = "2.00"
PULLBACK_MAX_VOLUME_RATIO = "1.20"
PULLBACK_MIN_CLOSE_LOCATION = "0.35"


def entry_geometry_parameter_payload() -> dict[str, object]:
    return {
        "contract_version": ENTRY_GEOMETRY_CONTRACT_VERSION,
        "calculation_version": ENTRY_GEOMETRY_CALCULATION_VERSION,
        "parameter_set_id": ENTRY_GEOMETRY_PARAMETER_SET_ID,
        "purpose": "entry_location_and_chase_risk_shadow_not_candidate_ranking",
        "history": {
            "panel_session_count": ENTRY_GEOMETRY_PANEL_SESSION_COUNT,
            "atr_window": ENTRY_GEOMETRY_ATR_WINDOW,
            "sma_windows": [ENTRY_GEOMETRY_SMA_SHORT_WINDOW, ENTRY_GEOMETRY_SMA_LONG_WINDOW],
            "prior_breakout_window": ENTRY_GEOMETRY_PRIOR_BREAKOUT_WINDOW,
            "return_windows": list(ENTRY_GEOMETRY_RETURN_WINDOWS),
            "trailing_up_cap": ENTRY_GEOMETRY_TRAILING_UP_CAP,
        },
        "research_floors": {
            "candidate_score": ENTRY_GEOMETRY_SCORE_FLOOR,
            "strong_candidate_score": ENTRY_GEOMETRY_STRONG_SCORE,
            "breakout_candidate_score": ENTRY_GEOMETRY_BREAKOUT_SCORE,
            "relative_strength_and_trend_component": ENTRY_GEOMETRY_COMPONENT_FLOOR,
            "trend_kill_floor": ENTRY_GEOMETRY_TREND_KILL_FLOOR,
        },
        "extension": {
            "moderate_sma20_atr": MODERATE_SMA20_EXTENSION_ATR,
            "high_sma20_atr": HIGH_SMA20_EXTENSION_ATR,
            "extreme_sma20_atr": EXTREME_SMA20_EXTENSION_ATR,
            "moderate_move_5_volatility_units": MODERATE_MOVE_5_VOLATILITY_UNITS,
            "high_move_5_volatility_units": HIGH_MOVE_5_VOLATILITY_UNITS,
            "extreme_move_5_volatility_units": EXTREME_MOVE_5_VOLATILITY_UNITS,
            "moderate_sma10_atr": MODERATE_SMA10_EXTENSION_ATR,
            "high_sma10_atr": HIGH_SMA10_EXTENSION_ATR,
            "moderate_trailing_up_sessions": MODERATE_TRAILING_UP_SESSIONS,
            "high_trailing_up_sessions": HIGH_TRAILING_UP_SESSIONS,
            "moderate_positive_gap_atr": MODERATE_POSITIVE_GAP_ATR,
            "extreme_positive_gap_atr": EXTREME_POSITIVE_GAP_ATR,
            "volume_climax_ratio": VOLUME_CLIMAX_RATIO,
            "volume_climax_range_atr": VOLUME_CLIMAX_RANGE_ATR,
            "volume_climax_close_location": VOLUME_CLIMAX_CLOSE_LOCATION,
        },
        "setups": {
            "breakout_max_distance_atr": BREAKOUT_MAX_DISTANCE_ATR,
            "breakout_min_volume_ratio": BREAKOUT_MIN_VOLUME_RATIO,
            "breakout_max_volume_ratio": BREAKOUT_MAX_VOLUME_RATIO,
            "breakout_min_close_location": BREAKOUT_MIN_CLOSE_LOCATION,
            "breakout_watch_max_distance_atr": BREAKOUT_WATCH_MAX_DISTANCE_ATR,
            "breakout_watch_max_volume_ratio": BREAKOUT_WATCH_MAX_VOLUME_RATIO,
            "pullback_sma10_distance_atr": PULLBACK_SMA10_DISTANCE_ATR,
            "pullback_from_high_min_atr": PULLBACK_FROM_HIGH_MIN_ATR,
            "pullback_from_high_max_atr": PULLBACK_FROM_HIGH_MAX_ATR,
            "pullback_max_volume_ratio": PULLBACK_MAX_VOLUME_RATIO,
            "pullback_min_close_location": PULLBACK_MIN_CLOSE_LOCATION,
        },
        "numeric_publication": {
            "raw_decimal_scale": ENTRY_GEOMETRY_RAW_DECIMAL_SCALE,
            "rounding": "round_half_even",
        },
        "boundaries": [
            "research_priority_not_recommendation",
            "technical_review_posture_not_order_instruction",
            "reference_support_not_stop_price",
            "underlying_stock_result_not_option_return",
            "no_outcome_fitted_parameters",
        ],
    }


ENTRY_GEOMETRY_PARAMETER_FINGERPRINT = hashlib.sha256(
    json.dumps(
        entry_geometry_parameter_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
).hexdigest()
