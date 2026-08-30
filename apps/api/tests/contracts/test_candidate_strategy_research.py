from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1 import (
    MAXIMUM_PREREGISTERED_PARAMETER_COMBINATIONS,
    STRONG_STOCK_PULLBACK_EXPERIMENT_ID,
    STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT,
    CandidateStrategyResearchExperimentV1,
    StrategyChannel,
    StrategyResearchStage,
    strong_stock_pullback_research_experiment_v1,
)


def _payload() -> dict[str, object]:
    return strong_stock_pullback_research_experiment_v1().model_dump(mode="json")


def test_first_pullback_experiment_is_preregistered_and_data_blocked() -> None:
    experiment = strong_stock_pullback_research_experiment_v1()

    assert experiment.channel is StrategyChannel.STRONG_STOCK_PULLBACK
    assert experiment.experiment_id == STRONG_STOCK_PULLBACK_EXPERIMENT_ID
    assert experiment.logical_fingerprint == STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    assert experiment.stage is StrategyResearchStage.PREREGISTERED_DATA_BLOCKED
    assert experiment.primary_horizon_sessions == 3
    assert experiment.target_holding_sessions == (1, 3, 5)
    assert experiment.primary_contrast.endswith("eligible_leader_non_signal_control")
    assert experiment.parameter_combination_count == 24
    assert experiment.parameter_combination_count == MAXIMUM_PREREGISTERED_PARAMETER_COMBINATIONS
    assert experiment.random_split_prohibited is True
    assert experiment.untouched_holdout_required is True
    assert experiment.research_only is True
    assert experiment.not_trading_recommendation is True
    assert experiment.model_may_decay_or_fail is True
    assert experiment.underlying_stock_result_not_option_return is True
    assert "canonical_252_session_history_absent" in experiment.activation_blocker_codes
    adjusted_panel = next(
        item
        for item in experiment.feature_requirements
        if item.feature_id == "adjusted_ohlcv_panel"
    )
    assert adjusted_panel.minimum_lookback_sessions == 20
    assert experiment.minimum_research_history_sessions == 252


def test_first_pullback_experiment_is_deterministic() -> None:
    first = strong_stock_pullback_research_experiment_v1()
    second = strong_stock_pullback_research_experiment_v1()

    assert first.experiment_id == second.experiment_id
    assert first.logical_fingerprint == second.logical_fingerprint


def test_experiment_rejects_unfingerprinted_gate_drift() -> None:
    payload = _payload()
    gates = deepcopy(payload["decision_gates"])
    gates[0]["threshold"] = "0.20"
    payload["decision_gates"] = gates

    with pytest.raises(ValidationError, match="logical fingerprint mismatch"):
        CandidateStrategyResearchExperimentV1.model_validate(payload)


def test_parameter_grid_cannot_expand_beyond_preregistered_bound() -> None:
    payload = _payload()
    dimensions = deepcopy(payload["parameter_grid"])
    dimensions[0]["candidate_values"].append(
        "rs20_percentile_gte_0.95_and_trend_quality_gte_80"
    )
    payload["parameter_grid"] = dimensions
    payload["parameter_combination_count"] = 36

    with pytest.raises(ValidationError, match="exceeds its preregistered bound"):
        CandidateStrategyResearchExperimentV1.model_validate(payload)


def test_active_research_stage_cannot_hide_unresolved_data_blockers() -> None:
    payload = _payload()
    payload["stage"] = "development"

    with pytest.raises(ValidationError, match="cannot retain unresolved activation blockers"):
        CandidateStrategyResearchExperimentV1.model_validate(payload)


def test_feature_ids_are_unique_and_stably_ordered() -> None:
    payload = _payload()
    requirements = deepcopy(payload["feature_requirements"])
    requirements[1]["feature_id"] = requirements[0]["feature_id"]
    payload["feature_requirements"] = requirements

    with pytest.raises(ValidationError, match="feature IDs must be unique and sorted"):
        CandidateStrategyResearchExperimentV1.model_validate(payload)


def test_contract_forbids_undeclared_fields_and_mutation() -> None:
    payload = _payload()
    payload["backtested_win_rate"] = "0.75"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CandidateStrategyResearchExperimentV1.model_validate(payload)

    experiment = strong_stock_pullback_research_experiment_v1()
    with pytest.raises(ValidationError, match="Instance is frozen"):
        experiment.stage = StrategyResearchStage.DEVELOPMENT
