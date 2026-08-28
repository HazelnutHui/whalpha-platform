"""Frozen, unvalidated baseline for offline Candidate strategy-channel previews."""

from __future__ import annotations

import hashlib
import json


STRATEGY_CHANNEL_CONTRACT_VERSION = "candidate-strategy-channel-shadow/1.0"
STRATEGY_CHANNEL_CALCULATION_VERSION = "candidate-strategy-channel-shadow-v1.1.0"
STRATEGY_CHANNEL_PARAMETER_SET_ID = (
    "candidate-strategy-channel-preview-v1-fixed-baseline-1"
)
STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION = (
    "candidate-strategy-channel-consumer/1.0"
)
STRATEGY_CHANNEL_DISPLAY_CAP = 8
STRATEGY_CHANNEL_ORDER = (
    "momentum_breakout",
    "strong_stock_pullback",
    "trend_continuation",
    "technical_reversal",
    "fundamental_value_reversal",
    "defensive_rotation",
)

REQUIRED_PRIMARY_EVIDENCE = {
    "momentum_breakout": ("price_volume",),
    "strong_stock_pullback": ("price_volume",),
    "trend_continuation": ("price_volume",),
    "technical_reversal": ("price_volume",),
    "fundamental_value_reversal": (
        "fundamentals",
        "valuation",
        "price_volume",
    ),
    "defensive_rotation": (
        "market_regime",
        "price_derived_relationship_proxy",
        "price_volume",
    ),
}

# Scores are research triage only and remain incomparable across channels.
CHANNEL_SCORE_WEIGHTS = {
    "momentum_breakout": {
        "stock_relative_strength": "0.3500",
        "trend_quality": "0.2500",
        "volume_participation": "0.1500",
        "entry_geometry": "0.2500",
    },
    "strong_stock_pullback": {
        "stock_relative_strength": "0.3000",
        "trend_quality": "0.2500",
        "volatility_risk": "0.1500",
        "liquidity_suitability": "0.1000",
        "entry_geometry": "0.2000",
    },
    "trend_continuation": {
        "stock_relative_strength": "0.3500",
        "trend_quality": "0.3500",
        "volume_participation": "0.1500",
        "volatility_risk": "0.1000",
        "entry_geometry": "0.0500",
    },
}

CHANNEL_GEOMETRY_SCORES = {
    "momentum_breakout": {
        "breakout_confirmed": "100.0000",
        "breakout_watch": "70.0000",
        "pullback": "25.0000",
        "strong_but_extended": "15.0000",
        "no_viable_setup": "20.0000",
    },
    "strong_stock_pullback": {
        "breakout_confirmed": "25.0000",
        "breakout_watch": "35.0000",
        "pullback": "100.0000",
        "strong_but_extended": "55.0000",
        "no_viable_setup": "20.0000",
    },
    "trend_continuation": {
        "breakout_confirmed": "85.0000",
        "breakout_watch": "70.0000",
        "pullback": "85.0000",
        "strong_but_extended": "35.0000",
        "no_viable_setup": "50.0000",
    },
}

TREND_CONTINUATION_ADVANCE_COMPONENT_FLOOR = "65.0000"
TREND_CONTINUATION_WATCH_COMPONENT_FLOOR = "55.0000"
TREND_CONTINUATION_WATCH_BASE_FLOOR = "65.0000"


def strategy_channel_parameter_payload() -> dict[str, object]:
    return {
        "contract_version": STRATEGY_CHANNEL_CONTRACT_VERSION,
        "calculation_version": STRATEGY_CHANNEL_CALCULATION_VERSION,
        "parameter_set_id": STRATEGY_CHANNEL_PARAMETER_SET_ID,
        "channel_order": list(STRATEGY_CHANNEL_ORDER),
        "required_primary_evidence": REQUIRED_PRIMARY_EVIDENCE,
        "technical_channel_score_weights": CHANNEL_SCORE_WEIGHTS,
        "technical_channel_geometry_scores": CHANNEL_GEOMETRY_SCORES,
        "trend_continuation_status_floors": {
            "advance_component": TREND_CONTINUATION_ADVANCE_COMPONENT_FLOOR,
            "watch_component": TREND_CONTINUATION_WATCH_COMPONENT_FLOOR,
            "watch_base": TREND_CONTINUATION_WATCH_BASE_FLOOR,
        },
        "status_rules": {
            "momentum_breakout": {
                "advance": ["breakout_confirmed"],
                "watch": ["breakout_watch", "strong_but_extended"],
            },
            "strong_stock_pullback": {
                "advance": ["pullback"],
                "watch": ["strong_but_extended"],
            },
            "trend_continuation": (
                "advance_requires_prepare_or_enter_stage_component_floors_"
                "and_non_high_extension; watch_requires_base_and_component_floors"
            ),
            "technical_reversal": "unavailable_pending_stabilization_and_reclaim_facts",
            "fundamental_value_reversal": "unavailable_pending_fundamentals_and_valuation",
            "defensive_rotation": "unavailable_pending_point_in_time_defensive_taxonomy",
        },
        "ranking": (
            "within_channel_advance_then_watch_score_desc_ticker_asc_stable_id_asc"
        ),
        "consumer": {
            "contract_version": STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION,
            "display_cap_per_channel": STRATEGY_CHANNEL_DISPLAY_CAP,
            "selection": "top_contiguous_within_channel_ranks_only",
        },
        "boundaries": {
            "cross_channel_score_prohibited": True,
            "market_and_sector_fit_separate_and_unvalidated": True,
            "no_outcome_fitted_parameters": True,
            "shadow_only_not_publication_input": True,
            "research_priority_not_recommendation": True,
            "underlying_stock_result_not_option_return": True,
            "price_volume_not_fund_flow": True,
        },
    }


STRATEGY_CHANNEL_PARAMETER_FINGERPRINT = hashlib.sha256(
    json.dumps(
        strategy_channel_parameter_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
).hexdigest()
