"""Frozen Phase 5A stock-candidate scoring and risk-mode parameters."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


CANDIDATE_CONTRACT_VERSION = "opportunity-candidate/1.0"
CANDIDATE_CALCULATION_VERSION = "market-regime-opportunity-candidate-v1.0.0"
CANDIDATE_PARAMETER_SET_ID = "mrom-candidate-v1-fixed-baseline-1"
MINIMUM_CONFIGURED_WEIGHT_AVAILABLE = 80
BASE_WATCH_SCORE = "50"
BASE_WATCH_CONFIDENCE = "0.40"
BASE_PRICE_FLOOR = "2"
BASE_LIQUIDITY_FLOOR = "5000000"
CORRELATION_MINIMUM_OBSERVATIONS = 18
CORRELATION_MINIMUM = "0.35"
ETF_ALIGNMENT_CAP = "70"
CROSS_SECTION_WINSOR_LOW = "0.05"
CROSS_SECTION_WINSOR_HIGH = "0.95"
CROSS_SECTION_ROBUST_Z_SCALE = "0.67448975"
CROSS_SECTION_SCORE_SCALE = "15"
QUANTILE_METHOD = "inclusive_linear_type7_decimal"
TIE_PERCENTILE_METHOD = "average_rank_inclusive_0_100_stable_id_order"


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
            "quantile_method": QUANTILE_METHOD,
            "tie_percentile_method": TIE_PERCENTILE_METHOD,
        },
        "driver": {
            "minimum_return_observations": CORRELATION_MINIMUM_OBSERVATIONS,
            "minimum_correlation": CORRELATION_MINIMUM,
            "component_cap": ETF_ALIGNMENT_CAP,
            "selection": "highest_positive_correlation_then_ticker_ascending",
            "relationship_kind": "price_derived_exposure_proxy",
        },
        "components": [asdict(item) for item in COMPONENT_PARAMETERS],
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


if sum(item.configured_weight for item in COMPONENT_PARAMETERS) != 100:
    raise RuntimeError("candidate component weights must total 100")
if any(sum(weight for _, weight in item.submetric_weights) != 100 for item in COMPONENT_PARAMETERS):
    raise RuntimeError("candidate submetric weights must total 100 inside each component")
if tuple(item.risk_mode for item in RISK_MODE_PARAMETERS) != ("conservative", "balanced", "aggressive"):
    raise RuntimeError("risk modes must use fixed contract order")
