"""Fixed product-projection policy for Candidate entry-geometry lanes."""

from __future__ import annotations

import hashlib
import json


ENTRY_LANE_CONSUMER_CONTRACT_VERSION = "candidate-entry-lane-consumer/1.0"
ENTRY_LANE_CONSUMER_PARAMETER_SET_ID = "candidate-entry-lane-consumer-v1-fixed-baseline-1"
ENTRY_LANE_ORDER = (
    "review_now",
    "watch_trigger",
    "wait_reset",
    "other_research",
)
ENTRY_LANE_DISPLAY_CAPS = {
    "conservative": 8,
    "balanced": 8,
    "aggressive": 8,
}
SELECTION_LIMIT_REJECTION_CODES = frozenset(
    {
        "risk_mode_display_cap_exceeded",
        "risk_mode_concentration_cap_exceeded",
    }
)


def entry_lane_consumer_parameter_payload() -> dict[str, object]:
    return {
        "contract_version": ENTRY_LANE_CONSUMER_CONTRACT_VERSION,
        "parameter_set_id": ENTRY_LANE_CONSUMER_PARAMETER_SET_ID,
        "lane_order": list(ENTRY_LANE_ORDER),
        "display_caps_by_risk_mode": dict(ENTRY_LANE_DISPLAY_CAPS),
        "hard_risk_gate_rule": (
            "eligible_or_rejected_only_by_display_or_concentration_selection_limits"
        ),
        "lane_mapping": {
            "technical_review_ready": "review_now",
            "monitor_for_trigger": "watch_trigger",
            "wait_for_reset": "wait_reset",
            "deprioritized": "other_research",
            "not_assessable": "other_research",
        },
        "selection_order": (
            "base_score_desc_confidence_desc_median_dollar_volume_desc_"
            "ticker_asc_instrument_id_asc"
        ),
        "concentration_rule": (
            "reuse_risk_mode_concentration_cap_with_floor_lane_cap_times_cap_minimum_one"
        ),
        "semantics": {
            "leadership_rank_preserved": True,
            "entry_lane_not_recommendation": True,
            "reference_support_not_stop_price": True,
            "underlying_stock_result_not_option_return": True,
        },
    }


ENTRY_LANE_CONSUMER_PARAMETER_FINGERPRINT = hashlib.sha256(
    json.dumps(
        entry_lane_consumer_parameter_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
).hexdigest()
