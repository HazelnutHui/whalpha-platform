"""Frozen Phase 5 stock-candidate scoring, state, and risk-mode parameters."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


CANDIDATE_CONTRACT_VERSION = "opportunity-candidate/1.1"
CANDIDATE_CALCULATION_VERSION = "market-regime-opportunity-candidate-v1.1.1"
CANDIDATE_PARAMETER_SET_ID = "mrom-candidate-v1-fixed-baseline-3"
CANDIDATE_STATE_CONTRACT_VERSION = "opportunity-candidate-state/1.0"
CANDIDATE_STATE_CALCULATION_VERSION = "market-regime-opportunity-candidate-state-v1.0.0"
CANDIDATE_STATE_PARAMETER_SET_ID = "mrom-candidate-state-v1-fixed-baseline-1"
MINIMUM_CONFIGURED_WEIGHT_AVAILABLE = 80
BASE_WATCH_SCORE = "50"
BASE_WATCH_CONFIDENCE = "0.40"
BASE_PRICE_FLOOR = "2"
BASE_LIQUIDITY_FLOOR = "5000000"
PREPARE_SCORE = "65"
PREPARE_RELATIVE_STRENGTH_SCORE = "55"
PREPARE_TREND_SCORE = "55"
ENTER_SCORE = "75"
BREAKOUT_ENTER_SCORE = "70"
BREAKOUT_VOLUME_RATIO = "1.20"
ENTER_TO_PREPARE_SCORE = "68"
ENTER_TO_PREPARE_TREND_SCORE = "50"
PREPARE_TO_WATCH_SCORE = "58"
PREPARE_TO_WATCH_MARKET_ALIGNMENT_SCORE = "40"
INVALIDATION_SCORE = "45"
REENTRY_WATCH_SCORE = "55"
MISSING_STATE_HOLD_SESSIONS = 1
CORRELATION_MINIMUM_OBSERVATIONS = 18
CORRELATION_MINIMUM = "0.35"
ETF_ALIGNMENT_CAP = "70"
CROSS_SECTION_WINSOR_LOW = "0.05"
CROSS_SECTION_WINSOR_HIGH = "0.95"
CROSS_SECTION_ROBUST_Z_SCALE = "0.67448975"
CROSS_SECTION_SCORE_SCALE = "15"
CROSS_SECTION_SCORE_CENTER = "50"
QUANTILE_METHOD = "inclusive_linear_type7_decimal"
TIE_PERCENTILE_METHOD = "average_rank_inclusive_0_100_stable_id_order"
CANDIDATE_PANEL_SESSION_COUNT = 26
CANDIDATE_REQUIRED_HISTORY_SESSION_COUNT = 21
ANNUALIZATION_SESSION_COUNT = 252
CALCULATION_DECIMAL_PRECISION = 50
SCORE_DECIMAL_SCALE = 4
RAW_DECIMAL_SCALE = 10
RETURN_WINDOWS = (1, 5, 20)
SMA_SHORT_WINDOW = 10
SMA_LONG_WINDOW = 20
MAXIMUM_DRAWDOWN_CLOSE_COUNT = 6
PRIOR_VOLUME_WINDOW = 20
PRIOR_VOLUME_MINIMUM_OBSERVATIONS = 15
VOLUME_PERSISTENCE_SESSION_COUNT = 5
VOLUME_PERSISTENCE_MINIMUM_OBSERVATIONS = 4
REALIZED_VOLATILITY_RETURN_COUNT = 10
OPEN_GAP_SESSION_COUNT = 5
OPEN_GAP_MINIMUM_OBSERVATIONS = 5
DOWNSIDE_TAIL_SESSION_COUNT = 5
DOWNSIDE_TAIL_MINIMUM_OBSERVATIONS = 4
DOWNSIDE_TAIL_RETURN_THRESHOLD = "-0.04"
DOLLAR_VOLUME_WINDOW = 20
DOLLAR_VOLUME_MINIMUM_OBSERVATIONS = 15
DRIVER_CORRELATION_WINDOW = 20
DRIVER_CORRELATION_NORMALIZER_HIGH = "0.80"
SMA_RATIO_NORMALIZER_LOW = "-0.03"
SMA_RATIO_NORMALIZER_HIGH = "0.03"
MAXIMUM_DRAWDOWN_NORMALIZER_LOW = "0.02"
MAXIMUM_DRAWDOWN_NORMALIZER_HIGH = "0.12"
REALIZED_VOLATILITY_NORMALIZER_LOW = "0.25"
REALIZED_VOLATILITY_NORMALIZER_HIGH = "1.00"
OPEN_GAP_NORMALIZER_LOW = "0.03"
OPEN_GAP_NORMALIZER_HIGH = "0.20"
DOWNSIDE_TAIL_NORMALIZER_LOW = "0"
DOWNSIDE_TAIL_NORMALIZER_HIGH = "0.40"
LIQUIDITY_NORMALIZER_LOW = "5000000"
LIQUIDITY_NORMALIZER_HIGH = "100000000"
PRICE_NORMALIZER_LOW = "2"
PRICE_NORMALIZER_HIGH = "20"
EXTREME_CLOSE_RETURN_REVIEW_THRESHOLD = "0.50"
EXTREME_OPEN_GAP_REVIEW_THRESHOLD = "0.30"
CANDIDATE_NON_BLOCKING_QUALITY_FLAGS = (
    "adjustment_factors_unverified",
    "missing_vwap",
    "missing_trade_count",
    "zero_volume",
)
CONFIDENCE_SOURCE_WEIGHT = "0.40"
CONFIDENCE_HISTORY_WEIGHT = "0.25"
CONFIDENCE_RELATIONSHIP_WEIGHT = "0.20"
CONFIDENCE_STATE_WEIGHT = "0.15"
RELATIONSHIP_SUPPORT_LEVELS = (
    ("insufficient", "0"),
    ("low", "0.40"),
    ("medium", "0.70"),
    ("high", "1.00"),
)
STATE_CONFIRMATION_SUPPORT_SESSION_CAP = 3
PRIOR_STATE_BOOTSTRAP_MARKER = "explicit_bootstrap_no_prior_candidate_state_history"
CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT = hashlib.sha256(
    PRIOR_STATE_BOOTSTRAP_MARKER.encode("utf-8")
).hexdigest()


@dataclass(frozen=True, slots=True)
class CandidateComponentParameter:
    component_id: str
    configured_weight: int
    submetric_weights: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class CandidateRiskModeParameter:
    risk_mode: str
    minimum_median_dollar_volume: str
    maximum_annualized_volatility: str
    maximum_absolute_open_gap: str
    minimum_price: str
    minimum_confidence: str
    adrc_permitted: bool
    candidate_display_cap: int
    concentration_cap: str


@dataclass(frozen=True, slots=True)
class CandidateStateTransitionParameter:
    rule_id: str
    source_stage: str
    target_stage: str
    confirmation_sessions: int


COMPONENT_PARAMETERS = (
    CandidateComponentParameter("market_alignment", 12, (("regime_score", 100),)),
    CandidateComponentParameter(
        "etf_sector_alignment",
        13,
        (("driver_relative_strength_5", 40), ("stock_relative_to_driver_5", 35), ("driver_correlation_20", 25)),
    ),
    CandidateComponentParameter(
        "stock_relative_strength",
        25,
        (("stock_relative_to_spy_5", 45), ("stock_relative_to_spy_20", 35), ("stock_return_percentile_20", 20)),
    ),
    CandidateComponentParameter(
        "trend_quality",
        18,
        (("close_above_sma10", 35), ("sma10_to_sma20", 35), ("maximum_drawdown_5", 30)),
    ),
    CandidateComponentParameter(
        "volume_participation",
        12,
        (("current_volume_ratio", 50), ("up_session_participation", 25), ("volume_persistence_5", 25)),
    ),
    CandidateComponentParameter(
        "volatility_risk",
        10,
        (("realized_volatility_10", 50), ("maximum_open_gap_5", 30), ("downside_tail_share_5", 20)),
    ),
    CandidateComponentParameter(
        "liquidity_suitability",
        10,
        (("median_dollar_volume_20", 70), ("latest_price", 30)),
    ),
)

RISK_MODE_PARAMETERS = (
    CandidateRiskModeParameter("conservative", "50000000", "0.45", "0.08", "10", "0.75", False, 25, "0.20"),
    CandidateRiskModeParameter("balanced", "20000000", "0.65", "0.12", "5", "0.60", True, 50, "0.25"),
    CandidateRiskModeParameter("aggressive", "5000000", "1.00", "0.20", "2", "0.45", True, 100, "0.35"),
)

STATE_TRANSITION_PARAMETERS = (
    CandidateStateTransitionParameter("not_listed_to_watch", "not_listed", "watch", 1),
    CandidateStateTransitionParameter("watch_to_prepare", "watch", "prepare", 2),
    CandidateStateTransitionParameter("prepare_to_enter", "prepare", "enter", 2),
    CandidateStateTransitionParameter("prepare_to_enter_breakout", "prepare", "enter", 1),
    CandidateStateTransitionParameter("enter_to_prepare", "enter", "prepare", 2),
    CandidateStateTransitionParameter("prepare_to_watch", "prepare", "watch", 2),
    CandidateStateTransitionParameter("active_to_invalidated", "active", "invalidated", 1),
    CandidateStateTransitionParameter("invalidated_to_watch", "invalidated", "watch", 3),
)


def parameter_payload() -> dict[str, object]:
    return {
        "contract_version": CANDIDATE_CONTRACT_VERSION,
        "calculation_version": CANDIDATE_CALCULATION_VERSION,
        "parameter_set_id": CANDIDATE_PARAMETER_SET_ID,
        "minimum_configured_weight_available": MINIMUM_CONFIGURED_WEIGHT_AVAILABLE,
        "base_candidate_floor": {
            "watch_score": BASE_WATCH_SCORE,
            "confidence": BASE_WATCH_CONFIDENCE,
            "price": BASE_PRICE_FLOOR,
            "median_dollar_volume": BASE_LIQUIDITY_FLOOR,
        },
        "cross_section": {
            "winsor_low": CROSS_SECTION_WINSOR_LOW,
            "winsor_high": CROSS_SECTION_WINSOR_HIGH,
            "robust_z_scale": CROSS_SECTION_ROBUST_Z_SCALE,
            "score_scale": CROSS_SECTION_SCORE_SCALE,
            "score_center": CROSS_SECTION_SCORE_CENTER,
            "quantile_method": QUANTILE_METHOD,
            "tie_percentile_method": TIE_PERCENTILE_METHOD,
        },
        "driver": {
            "minimum_return_observations": CORRELATION_MINIMUM_OBSERVATIONS,
            "minimum_correlation": CORRELATION_MINIMUM,
            "correlation_window": DRIVER_CORRELATION_WINDOW,
            "require_positive_five_session_return": True,
            "correlation_normalizer_high": DRIVER_CORRELATION_NORMALIZER_HIGH,
            "component_cap": ETF_ALIGNMENT_CAP,
            "selection": "highest_positive_correlation_then_ticker_ascending",
            "relationship_kind": "price_derived_exposure_proxy",
        },
        "components": [asdict(item) for item in COMPONENT_PARAMETERS],
        "metric_formulas": {
            "panel_session_count": CANDIDATE_PANEL_SESSION_COUNT,
            "required_history_session_count": CANDIDATE_REQUIRED_HISTORY_SESSION_COUNT,
            "annualization_session_count": ANNUALIZATION_SESSION_COUNT,
            "return_windows": list(RETURN_WINDOWS),
            "sma_windows": [SMA_SHORT_WINDOW, SMA_LONG_WINDOW],
            "maximum_drawdown_close_count": MAXIMUM_DRAWDOWN_CLOSE_COUNT,
            "prior_volume_window": PRIOR_VOLUME_WINDOW,
            "prior_volume_minimum_observations": PRIOR_VOLUME_MINIMUM_OBSERVATIONS,
            "volume_persistence_session_count": VOLUME_PERSISTENCE_SESSION_COUNT,
            "volume_persistence_minimum_observations": VOLUME_PERSISTENCE_MINIMUM_OBSERVATIONS,
            "realized_volatility_return_count": REALIZED_VOLATILITY_RETURN_COUNT,
            "open_gap_session_count": OPEN_GAP_SESSION_COUNT,
            "open_gap_minimum_observations": OPEN_GAP_MINIMUM_OBSERVATIONS,
            "downside_tail_session_count": DOWNSIDE_TAIL_SESSION_COUNT,
            "downside_tail_minimum_observations": DOWNSIDE_TAIL_MINIMUM_OBSERVATIONS,
            "downside_tail_return_threshold": DOWNSIDE_TAIL_RETURN_THRESHOLD,
            "dollar_volume_window": DOLLAR_VOLUME_WINDOW,
            "dollar_volume_minimum_observations": DOLLAR_VOLUME_MINIMUM_OBSERVATIONS,
            "up_session_participation_scores": {
                "both_positive_return_and_above_median_volume": "100",
                "exactly_one_condition": "50",
                "neither_condition": "0",
            },
        },
        "normalizers": {
            "sma10_to_sma20": [SMA_RATIO_NORMALIZER_LOW, SMA_RATIO_NORMALIZER_HIGH],
            "maximum_drawdown_5": [MAXIMUM_DRAWDOWN_NORMALIZER_LOW, MAXIMUM_DRAWDOWN_NORMALIZER_HIGH],
            "realized_volatility_10": [REALIZED_VOLATILITY_NORMALIZER_LOW, REALIZED_VOLATILITY_NORMALIZER_HIGH],
            "maximum_open_gap_5": [OPEN_GAP_NORMALIZER_LOW, OPEN_GAP_NORMALIZER_HIGH],
            "downside_tail_share_5": [DOWNSIDE_TAIL_NORMALIZER_LOW, DOWNSIDE_TAIL_NORMALIZER_HIGH],
            "median_dollar_volume_20": [LIQUIDITY_NORMALIZER_LOW, LIQUIDITY_NORMALIZER_HIGH],
            "latest_price": [PRICE_NORMALIZER_LOW, PRICE_NORMALIZER_HIGH],
        },
        "confidence": {
            "weights": {
                "source_completeness": CONFIDENCE_SOURCE_WEIGHT,
                "history_completeness": CONFIDENCE_HISTORY_WEIGHT,
                "relationship_support": CONFIDENCE_RELATIONSHIP_WEIGHT,
                "state_confirmation_support": CONFIDENCE_STATE_WEIGHT,
            },
            "relationship_support_levels": dict(RELATIONSHIP_SUPPORT_LEVELS),
            "state_confirmation_session_cap": STATE_CONFIRMATION_SUPPORT_SESSION_CAP,
            "prior_state_source": "typed_prior_candidate_state_history_through_t_minus_1",
            "bootstrap_marker": PRIOR_STATE_BOOTSTRAP_MARKER,
            "bootstrap_fingerprint": CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT,
        },
        "quality_review": {
            "extreme_close_return_threshold": EXTREME_CLOSE_RETURN_REVIEW_THRESHOLD,
            "extreme_open_gap_threshold": EXTREME_OPEN_GAP_REVIEW_THRESHOLD,
            "non_unit_adjustment_factor_requires_review": True,
            "non_valid_quality_status_requires_review": True,
            "non_blocking_quality_flags": list(CANDIDATE_NON_BLOCKING_QUALITY_FLAGS),
            "unknown_quality_flag_requires_review": True,
            "review_scope": "exact_candidate_panel",
        },
        "numeric_publication": {
            "calculation_decimal_precision": CALCULATION_DECIMAL_PRECISION,
            "rounding": "round_half_even",
            "score_decimal_scale": SCORE_DECIMAL_SCALE,
            "raw_decimal_scale": RAW_DECIMAL_SCALE,
        },
        "risk_modes": [asdict(item) for item in RISK_MODE_PARAMETERS],
        "risk_rank_order": [
            "base_score_desc",
            "confidence_desc",
            "median_dollar_volume_desc",
            "ticker_asc",
        ],
        "concentration_count_rule": "floor_display_cap_times_mode_cap_minimum_one",
        "regime_adjustment": "0.0000",
    }


CANDIDATE_PARAMETER_FINGERPRINT = hashlib.sha256(
    json.dumps(parameter_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
).hexdigest()


def candidate_state_parameter_payload() -> dict[str, object]:
    return {
        "contract_version": CANDIDATE_STATE_CONTRACT_VERSION,
        "calculation_version": CANDIDATE_STATE_CALCULATION_VERSION,
        "parameter_set_id": CANDIDATE_STATE_PARAMETER_SET_ID,
        "decision_context": "candidate",
        "stage_values": ["watch", "prepare", "enter", "invalidated"],
        "confirmation_count_source": "prior_candidate_state_history",
        "missing_state_hold_sessions": MISSING_STATE_HOLD_SESSIONS,
        "state_liquidity_gates": {
            "minimum_price": BASE_PRICE_FLOOR,
            "minimum_median_dollar_volume": BASE_LIQUIDITY_FLOOR,
        },
        "thresholds": {
            "watch_score": BASE_WATCH_SCORE,
            "watch_confidence": BASE_WATCH_CONFIDENCE,
            "prepare_score": PREPARE_SCORE,
            "prepare_relative_strength_score": PREPARE_RELATIVE_STRENGTH_SCORE,
            "prepare_trend_score": PREPARE_TREND_SCORE,
            "enter_score": ENTER_SCORE,
            "breakout_enter_score": BREAKOUT_ENTER_SCORE,
            "breakout_volume_ratio": BREAKOUT_VOLUME_RATIO,
            "enter_to_prepare_score": ENTER_TO_PREPARE_SCORE,
            "enter_to_prepare_trend_score": ENTER_TO_PREPARE_TREND_SCORE,
            "prepare_to_watch_score": PREPARE_TO_WATCH_SCORE,
            "prepare_to_watch_market_alignment_score": PREPARE_TO_WATCH_MARKET_ALIGNMENT_SCORE,
            "invalidation_score": INVALIDATION_SCORE,
            "reentry_watch_score": REENTRY_WATCH_SCORE,
        },
        "transitions": [asdict(item) for item in STATE_TRANSITION_PARAMETERS],
        "promotion_quarantine_policy": "quarantine_prevents_prepare_or_enter_and_invalidates_active_candidate",
        "breakout_fact": "close_gt_prior_five_session_close_high_and_volume_ratio_gte_1_20",
        "candidate_exit_semantics": "invalidated_not_sale_action",
    }


CANDIDATE_STATE_PARAMETER_FINGERPRINT = hashlib.sha256(
    json.dumps(
        candidate_state_parameter_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
).hexdigest()


if sum(item.configured_weight for item in COMPONENT_PARAMETERS) != 100:
    raise RuntimeError("candidate component weights must total 100")
if any(sum(weight for _, weight in item.submetric_weights) != 100 for item in COMPONENT_PARAMETERS):
    raise RuntimeError("candidate submetric weights must total 100 inside each component")
if tuple(item.risk_mode for item in RISK_MODE_PARAMETERS) != ("conservative", "balanced", "aggressive"):
    raise RuntimeError("risk modes must use fixed contract order")
if tuple(item.rule_id for item in STATE_TRANSITION_PARAMETERS) != (
    "not_listed_to_watch",
    "watch_to_prepare",
    "prepare_to_enter",
    "prepare_to_enter_breakout",
    "enter_to_prepare",
    "prepare_to_watch",
    "active_to_invalidated",
    "invalidated_to_watch",
):
    raise RuntimeError("candidate state transitions must use fixed contract order")
