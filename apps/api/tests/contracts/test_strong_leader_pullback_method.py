from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1 import (
    STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT,
    STRONG_LEADER_PULLBACK_METHOD_ENGINEERING_LAUNCH_FINGERPRINT,
    STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT,
    StrongLeaderPullbackMethodV1,
    strong_leader_pullback_method_fingerprint,
    strong_leader_pullback_method_v1,
    strong_stock_pullback_research_experiment_v1,
)


def _method_payload() -> dict[str, object]:
    return strong_leader_pullback_method_v1().model_dump(mode="json")


def test_method_is_deterministic_and_preserves_registered_identity() -> None:
    first = strong_leader_pullback_method_v1()
    second = strong_leader_pullback_method_v1()
    experiment = strong_stock_pullback_research_experiment_v1()

    assert first == second
    assert first.source_experiment_id == experiment.experiment_id
    assert first.source_experiment_fingerprint == experiment.logical_fingerprint
    assert first.parameter_combination_count == 24
    assert first.evaluation.search_budget == 24
    assert first.method_engineering_launch_fingerprint == (
        STRONG_LEADER_PULLBACK_METHOD_ENGINEERING_LAUNCH_FINGERPRINT
    )
    assert first.logical_fingerprint == STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT
    assert first.logical_fingerprint == strong_leader_pullback_method_fingerprint(first)


def test_method_preserves_input_feature_identity_and_zero_outcome_authority() -> None:
    method = strong_leader_pullback_method_v1()

    assert STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT == (
        "407d9e1b77b4b60976583f1254fca8a46e94718d84c9d430b094e5a7a025e76d"
    )
    assert method.input_feature_fingerprint == (
        STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT
    )
    assert method.contains_forward_outcomes is False
    assert method.parameter_selection_authorized is False
    assert method.formal_development_authorized is False
    assert method.validation_authorized is False
    assert method.holdout_access_authorized is False
    assert method.performance_claims_authorized is False
    assert method.candidate_activation_authorized is False


def test_price_features_disclose_requirement_and_raw_source_lineage() -> None:
    method = strong_leader_pullback_method_v1()
    feature_by_id = {item.feature_id: item for item in method.features}

    assert feature_by_id["atr_pullback_depth"].requirement_source_family == (
        "candidate-entry-geometry-v1"
    )
    for feature_id in (
        "adjusted_ohlcv_panel",
        "atr_pullback_depth",
        "recovery_trigger",
        "relative_leadership_20s",
        "trend_quality",
        "volume_contraction",
    ):
        assert feature_by_id[feature_id].raw_source_families == (
            "historical-eod-price-bars-v1",
            "historical-research-adjustment-ledger-v1",
        )


def test_method_rejects_formula_drift_without_new_fingerprint() -> None:
    payload = _method_payload()
    features = deepcopy(payload["features"])
    features[1]["exact_formula"] = "close / ATR"
    payload["features"] = features

    with pytest.raises(ValidationError, match="method fingerprint mismatch"):
        StrongLeaderPullbackMethodV1.model_validate(payload)


def test_method_rejects_unregistered_parameter_even_with_recomputed_fingerprint() -> None:
    payload = _method_payload()
    parameters = deepcopy(payload["parameters"])
    parameters[0]["canonical_candidate_values"][0] = "unregistered_gate"
    payload["parameters"] = parameters
    payload["logical_fingerprint"] = strong_leader_pullback_method_fingerprint(payload)

    with pytest.raises(ValidationError, match="Input should be"):
        StrongLeaderPullbackMethodV1.model_validate(payload)
