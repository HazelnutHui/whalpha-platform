from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1 import (
    STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT,
    StrategyMembershipMode,
    StrongLeaderPullbackDiagnosticExcludedPathV1,
    StrongLeaderPullbackDiagnosticUnavailableFeatureV1,
    StrongLeaderPullbackMethodDiagnosticsV1,
    strong_leader_pullback_method_v1,
)
from tip_api.services.candidate_strategy_research_execution import (
    build_candidate_strategy_chronological_plan,
    build_strong_leader_pullback_observation,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.strong_leader_pullback_diagnostics import (
    StrongLeaderPullbackDiagnosticsError,
    build_strong_leader_pullback_method_diagnostics,
)


IDS = tuple(
    UUID(f"00000000-0000-4000-8000-{index:012d}") for index in range(1, 7)
)


@pytest.fixture(scope="module")
def sessions() -> tuple[date, ...]:
    calendar = ExchangeCalendar()
    values = [date(2024, 1, 2)]
    while len(values) < 252:
        values.append(calendar.next_session(values[-1]))
    return tuple(values)


def _observation(
    *,
    session: date,
    index: int,
    relative_strength: str,
    trend: str,
    depth: str,
    volume: str,
    prior_close: bool,
    prior_high: bool,
):
    return build_strong_leader_pullback_observation(
        as_of_session=session,
        universe_id="primary",
        instrument_id=IDS[index],
        ticker=f"T{index + 1}",
        membership_mode=StrategyMembershipMode.POINT_IN_TIME,
        membership_session=session,
        membership_included=True,
        relative_strength_20s_percentile=relative_strength,
        trend_quality_score=trend,
        pullback_depth_atr=depth,
        close_above_prior_close=prior_close,
        close_above_prior_high=prior_high,
        pullback_volume_ratio=volume,
        market_regime="Balanced" if index < 3 else "Defensive",
        source_max_session=session,
        source_fingerprint=f"{index + 1:064x}",
    )


def _inputs(sessions: tuple[date, ...]):
    plan = build_candidate_strategy_chronological_plan(ordered_sessions=sessions)
    observations = tuple(
        sorted(
            (
                _observation(
                    session=sessions[40],
                    index=0,
                    relative_strength="0.8000",
                    trend="70.0000",
                    depth="0.5000",
                    volume="0.8000",
                    prior_close=True,
                    prior_high=False,
                ),
                _observation(
                    session=sessions[40],
                    index=1,
                    relative_strength="0.8000",
                    trend="74.0000",
                    depth="1.0000",
                    volume="0.7000",
                    prior_close=True,
                    prior_high=True,
                ),
                _observation(
                    session=sessions[41],
                    index=2,
                    relative_strength="0.9000",
                    trend="75.0000",
                    depth="1.5000",
                    volume="1.0000",
                    prior_close=False,
                    prior_high=False,
                ),
                _observation(
                    session=sessions[41],
                    index=3,
                    relative_strength="0.9500",
                    trend="82.0000",
                    depth="3.0000",
                    volume="1.2000",
                    prior_close=False,
                    prior_high=False,
                ),
            ),
            key=lambda item: (item.as_of_session, str(item.instrument_id)),
        )
    )
    excluded = (
        StrongLeaderPullbackDiagnosticExcludedPathV1(
            as_of_session=sessions[42],
            instrument_id=IDS[4],
            unavailable_features=(
                StrongLeaderPullbackDiagnosticUnavailableFeatureV1(
                    feature_id="adjusted_ohlcv_panel",
                    reason_codes=("adjustment_neutrality_unproven",),
                ),
                StrongLeaderPullbackDiagnosticUnavailableFeatureV1(
                    feature_id="atr_pullback_depth",
                    reason_codes=("missing_complete_feature_window",),
                ),
            ),
            source_max_session=sessions[42],
            source_fingerprint="f" * 64,
        ),
    )
    return plan, observations, excluded


def test_diagnostics_are_deterministic_outcome_blind_and_method_bound(
    sessions: tuple[date, ...],
) -> None:
    plan, observations, excluded = _inputs(sessions)

    first = build_strong_leader_pullback_method_diagnostics(
        plan=plan,
        observations=observations,
        excluded_paths=excluded,
    )
    second = build_strong_leader_pullback_method_diagnostics(
        plan=plan,
        observations=observations,
        excluded_paths=excluded,
    )

    assert first == second
    assert first.method_fingerprint == STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT
    assert first.expected_path_count == 5
    assert first.complete_observation_count == 4
    assert first.excluded_path_count == 1
    assert len(first.parameter_combinations) == 24
    assert first.contains_forward_outcomes is False
    assert first.contains_performance_metrics is False
    assert first.parameter_selection_authorized is False
    assert first.trigger_counts_reusable_for_parameter_selection is False
    assert "outcomes" not in type(first).model_fields
    assert "returns" not in type(first).model_fields


def test_diagnostics_expose_coverage_ties_thresholds_and_concentration(
    sessions: tuple[date, ...],
) -> None:
    plan, observations, excluded = _inputs(sessions)
    report = build_strong_leader_pullback_method_diagnostics(
        plan=plan,
        observations=observations,
        excluded_paths=excluded,
    )

    coverage = {item.feature_id: item for item in report.feature_coverage}
    assert coverage["adjusted_ohlcv_panel"].source_unavailable_count == 1
    assert coverage["adjusted_ohlcv_panel"].availability_rate == "0.8000"
    assert tuple(
        item.reason_code
        for item in coverage["adjusted_ohlcv_panel"].unavailable_reason_counts
    ) == ("adjustment_neutrality_unproven",)
    assert tuple(
        item.reason_code
        for item in coverage["atr_pullback_depth"].unavailable_reason_counts
    ) == ("missing_complete_feature_window",)
    assert coverage["trend_quality"].source_available_count == 5
    assert coverage["trend_quality"].complete_distribution_observation_count == 4

    numeric = {item.feature_id: item for item in report.numeric_diagnostics}
    leadership = numeric["relative_leadership_20s"]
    assert leadership.distinct_value_count == 3
    assert leadership.duplicate_excess_count == 1
    assert leadership.duplicate_excess_rate == "0.2500"
    assert leadership.minimum == "0.8000000000"
    assert leadership.maximum == "0.9500000000"

    proximity = {item.feature_id: item for item in report.threshold_proximity}
    assert proximity["relative_leadership_20s"].thresholds == (
        "0.8000000000",
        "0.9000000000",
    )
    assert proximity["relative_leadership_20s"].near_threshold_count == 3
    assert report.observation_concentration[0].axis.value == "session"
    assert report.observation_concentration[0].maximum_group_share == "0.5000"


def test_every_combination_classifies_the_whole_declared_population(
    sessions: tuple[date, ...],
) -> None:
    plan, observations, excluded = _inputs(sessions)
    report = build_strong_leader_pullback_method_diagnostics(
        plan=plan,
        observations=observations,
        excluded_paths=excluded,
    )

    for item in report.parameter_combinations:
        assert (
            item.signal_count
            + item.eligible_leader_control_count
            + item.excluded_chronological_boundary_count
            + item.excluded_membership_count
            + item.excluded_not_leader_count
            + item.unavailable_input_count
        ) == report.expected_path_count
        assert item.unavailable_input_count == 1


def test_diagnostics_reject_overlap_unsorted_inputs_and_method_drift(
    sessions: tuple[date, ...],
) -> None:
    plan, observations, excluded = _inputs(sessions)
    overlap = excluded[0].model_copy(
        update={
            "as_of_session": observations[0].as_of_session,
            "instrument_id": observations[0].instrument_id,
            "source_max_session": observations[0].as_of_session,
        }
    )
    with pytest.raises(StrongLeaderPullbackDiagnosticsError, match="cannot be complete"):
        build_strong_leader_pullback_method_diagnostics(
            plan=plan,
            observations=observations,
            excluded_paths=(overlap,),
        )
    with pytest.raises(StrongLeaderPullbackDiagnosticsError, match="unique and sorted"):
        build_strong_leader_pullback_method_diagnostics(
            plan=plan,
            observations=tuple(reversed(observations)),
            excluded_paths=excluded,
        )
    changed_method = strong_leader_pullback_method_v1().model_copy(
        update={"decision_use": "changed"}
    )
    with pytest.raises(StrongLeaderPullbackDiagnosticsError, match="exact canonical"):
        build_strong_leader_pullback_method_diagnostics(
            plan=plan,
            observations=observations,
            excluded_paths=excluded,
            method=changed_method,
        )


def test_diagnostic_contract_rejects_tampered_aggregate(
    sessions: tuple[date, ...],
) -> None:
    plan, observations, excluded = _inputs(sessions)
    report = build_strong_leader_pullback_method_diagnostics(
        plan=plan,
        observations=observations,
        excluded_paths=excluded,
    )
    payload = report.model_dump(mode="json")
    payload["expected_path_count"] = 6

    with pytest.raises(ValidationError, match="diagnostics differ"):
        StrongLeaderPullbackMethodDiagnosticsV1.model_validate(payload)
