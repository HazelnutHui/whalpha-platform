"""Immutable fixed-baseline parameters for Market Regime V1 Phase 1a."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


CONTRACT_VERSION = "market-regime-opportunity-map/1.0"
CALCULATION_VERSION = "market-regime-opportunity-map-v1.0.0"
PARAMETER_SET_ID = "mrom-v1-fixed-baseline-1"
HISTORY_MEMBERSHIP_MODE = "current_as_of_constituent_replay"
BROAD_BENCHMARK_TICKERS = ("SPY", "QQQ", "IWM", "DIA")
MINIMUM_DIMENSION_INTERNAL_WEIGHT = 70
MINIMUM_COMPOSITE_WEIGHT = 90
REQUIRED_COMPOSITE_DIMENSIONS = ("trend", "breadth", "volatility")


@dataclass(frozen=True, slots=True)
class MetricParameter:
    metric_id: str
    lookback_sessions: int
    raw_unit: str
    direction: str
    normalizer: str
    low: str | None
    high: str | None
    center: str | None
    configured_weight: int
    minimum_observations: int
    minimum_coverage: str | None


@dataclass(frozen=True, slots=True)
class DimensionParameter:
    dimension_id: str
    configured_weight: int
    explanation_template_id: str
    metrics: tuple[MetricParameter, ...]


DIMENSION_PARAMETERS = (
    DimensionParameter(
        "trend",
        30,
        "market_regime_trend_v1",
        (
            MetricParameter("broad_return_20", 20, "ratio", "higher_supportive", "linear", "-0.08", "0.08", None, 35, 4, None),
            MetricParameter("broad_return_5", 5, "ratio", "higher_supportive", "linear", "-0.03", "0.03", None, 25, 4, None),
            MetricParameter("broad_above_sma20_share", 20, "ratio", "higher_supportive", "linear", "0.25", "0.75", None, 20, 3, None),
            MetricParameter("broad_direction_agreement", 5, "ratio", "higher_supportive", "linear", "0.25", "0.75", None, 20, 3, None),
        ),
    ),
    DimensionParameter(
        "breadth",
        25,
        "market_regime_breadth_v1",
        (
            MetricParameter("advancer_share_1", 1, "ratio", "higher_supportive", "linear", "0.35", "0.65", None, 25, 500, "0.80"),
            MetricParameter("positive_return_share_5", 5, "ratio", "higher_supportive", "linear", "0.35", "0.65", None, 25, 0, "0.80"),
            MetricParameter("above_sma20_share", 20, "ratio", "higher_supportive", "linear", "0.30", "0.70", None, 30, 0, "0.75"),
            MetricParameter("high_low_balance_20", 20, "ratio", "higher_supportive", "linear", "-0.10", "0.10", None, 20, 0, "0.75"),
        ),
    ),
    DimensionParameter(
        "volatility",
        20,
        "market_regime_volatility_v1",
        (
            MetricParameter("spy_realized_volatility_10", 10, "annualized_ratio", "lower_supportive", "declining", "0.10", "0.35", None, 35, 10, None),
            MetricParameter("median_stock_realized_volatility_10", 10, "annualized_ratio", "lower_supportive", "declining", "0.25", "0.80", None, 25, 0, "0.70"),
            MetricParameter("downside_tail_frequency_5", 5, "ratio", "lower_supportive", "declining", "0", "0.08", None, 20, 0, "0.70"),
            MetricParameter("cross_sectional_dispersion_1", 1, "ratio", "lower_supportive", "declining", "0.01", "0.04", None, 20, 500, None),
        ),
    ),
    DimensionParameter(
        "liquidity_participation",
        15,
        "market_regime_liquidity_participation_v1",
        (
            MetricParameter("aggregate_participation_ratio", 20, "ratio", "higher_supportive", "linear", "0.75", "1.25", None, 40, 18, "0.80"),
            MetricParameter("up_participation_share", 1, "ratio", "higher_supportive", "linear", "0.35", "0.65", None, 30, 0, "0.80"),
            MetricParameter("above_own_volume_median_share", 20, "ratio", "higher_supportive", "linear", "0.35", "0.65", None, 30, 15, "0.70"),
        ),
    ),
    DimensionParameter(
        "leadership_dispersion",
        10,
        "market_regime_leadership_dispersion_v1",
        (
            MetricParameter("winner_concentration_5", 5, "ratio", "lower_supportive", "declining", "0.35", "0.70", None, 45, 200, "0.70"),
            MetricParameter("benchmark_direction_agreement_5", 5, "ratio", "higher_supportive", "linear", "0.25", "0.75", None, 30, 3, None),
            MetricParameter("return_dispersion_5", 5, "ratio", "two_sided", "triangular", "0.005", "0.08", "0.025", 25, 500, None),
        ),
    ),
)


def _parameter_payload() -> dict[str, object]:
    return {
        "contract_version": CONTRACT_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "parameter_set_id": PARAMETER_SET_ID,
        "history_membership_mode": HISTORY_MEMBERSHIP_MODE,
        "broad_benchmark_tickers": list(BROAD_BENCHMARK_TICKERS),
        "minimum_dimension_internal_weight": MINIMUM_DIMENSION_INTERNAL_WEIGHT,
        "minimum_composite_weight": MINIMUM_COMPOSITE_WEIGHT,
        "required_composite_dimensions": list(REQUIRED_COMPOSITE_DIMENSIONS),
        "winner_top_decile_cardinality_rule": "ceiling_then_return_desc_stable_id_asc",
        "dimensions": [
            {
                **{key: value for key, value in asdict(dimension).items() if key != "metrics"},
                "metrics": [asdict(metric) for metric in dimension.metrics],
            }
            for dimension in DIMENSION_PARAMETERS
        ],
    }


PARAMETER_SET_FINGERPRINT = hashlib.sha256(
    json.dumps(_parameter_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
).hexdigest()


def parameter_payload() -> dict[str, object]:
    """Return a fresh JSON-compatible copy of the immutable parameter payload."""

    return json.loads(json.dumps(_parameter_payload(), sort_keys=True, separators=(",", ":")))
