from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta

import pytest

from tip_api.services import daily_eod_pipeline_cadence as cadence
from tip_api.services import daily_eod_pipeline_scheduler as scheduler
from tip_api.services.daily_eod_automation import (
    CONTRACT_VERSION as AUTOMATION_CONTRACT_VERSION,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)


BASE = datetime(2026, 8, 28, 21, tzinfo=UTC)
STARTED = datetime(2026, 8, 28, 20, 30, tzinfo=UTC)
OFFLINE_BASE = datetime(2026, 8, 29, 12, tzinfo=UTC)


def _automation_plan(status: PlanStatus, action: NextAction) -> DailyEodAutomationPlan:
    plan = DailyEodAutomationPlan(
        contract_version=AUTOMATION_CONTRACT_VERSION,
        target_session="2026-08-28",
        prior_session="2026-08-27",
        status=status,
        next_action=action,
        reason_codes=("test",),
        observations=(),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint="",
    )
    logical = asdict(plan)
    logical.pop("logical_content_fingerprint")
    return replace(
        plan,
        logical_content_fingerprint=scheduler._fingerprint(
            scheduler._jsonable(logical)
        ),
    )


def _data_plan(
    checked_at: datetime = BASE,
    *,
    enabled: bool = False,
):
    return scheduler.plan_daily_eod_pipeline_wake(
        checked_at=checked_at,
        completed_sessions=(date(2026, 8, 27),),
        review_enabled_candidate=enabled,
    )


def _manual_plan(*, enabled: bool = True):
    checked = OFFLINE_BASE
    return scheduler.plan_daily_eod_pipeline_wake(
        checked_at=checked,
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
        latest_pipeline_plan=_automation_plan(
            PlanStatus.ANALYTICS_READY,
            NextAction.REVIEW_PUBLICATION,
        ),
        review_enabled_candidate=enabled,
    )


def _offline_plan(checked_at: datetime = OFFLINE_BASE, *, enabled: bool = True):
    return scheduler.plan_daily_eod_pipeline_wake(
        checked_at=checked_at,
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
        latest_pipeline_plan=_automation_plan(
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_PHASE1A,
        ),
        review_enabled_candidate=enabled,
    )


def _evidence(
    *,
    sequence: int,
    started_at: datetime,
    outcome: cadence.CadenceWakeOutcome = cadence.CadenceWakeOutcome.ADVANCED,
    plan=None,
    cadence_started_at: datetime = STARTED,
):
    selected = plan or _data_plan(started_at, enabled=True)
    known = outcome is not cadence.CadenceWakeOutcome.UNKNOWN
    return cadence.record_cadence_wake_evidence(
        sequence=sequence,
        target_session=selected.target_session,
        cadence_started_at=cadence_started_at,
        started_at=started_at,
        completed_at=started_at + timedelta(seconds=30) if known else None,
        cadence_plan_fingerprint="f" * 64,
        pipeline_plan_fingerprint=selected.logical_content_fingerprint,
        pipeline_action=selected.next_action.value,
        outcome=outcome,
        next_eligible_at=None,
        result_fingerprint=(f"{sequence % 10}" * 64 if known else None),
    )


def _refingerprint_pipeline(plan, **changes):
    changed = replace(plan, **changes, logical_content_fingerprint="")
    logical = asdict(changed)
    logical.pop("logical_content_fingerprint")
    return replace(
        changed,
        logical_content_fingerprint=scheduler._fingerprint(
            scheduler._jsonable(logical)
        ),
    )


def _refingerprint_cadence(plan, **changes):
    changed = replace(plan, **changes, logical_content_fingerprint="")
    logical = asdict(changed)
    logical.pop("logical_content_fingerprint")
    return replace(
        changed,
        logical_content_fingerprint=cadence._fingerprint(
            cadence._jsonable(logical)
        ),
    )


def test_default_candidate_only_reports_review_and_writes_nothing(tmp_path) -> None:
    before = tuple(tmp_path.rglob("*"))
    plan = cadence.plan_bounded_pipeline_cadence(
        checked_at=BASE,
        cadence_started_at=STARTED,
        pipeline_plan=_data_plan(),
    )

    assert plan.status is cadence.CadenceStatus.REVIEW_READY
    assert plan.next_action is cadence.CadenceAction.REVIEW_ONE_TRANSITION
    assert plan.transition_wakes_used == 0
    assert plan.transition_wakes_remaining == 16
    assert plan.transition_invocation_count == 0
    assert plan.external_request_count == 0
    assert plan.filesystem_write_count == 0
    assert tuple(tmp_path.rglob("*")) == before
    cadence.verify_bounded_pipeline_cadence_plan(plan)


def test_both_candidates_must_be_enabled_to_propose_one_invocation() -> None:
    enabled = cadence.plan_bounded_pipeline_cadence(
        checked_at=BASE,
        cadence_started_at=STARTED,
        pipeline_plan=_data_plan(enabled=True),
        review_enabled_candidate=True,
    )
    pipeline_disabled = cadence.plan_bounded_pipeline_cadence(
        checked_at=BASE,
        cadence_started_at=STARTED,
        pipeline_plan=_data_plan(enabled=False),
        review_enabled_candidate=True,
    )

    assert enabled.status is cadence.CadenceStatus.WAKE_READY
    assert enabled.next_action is cadence.CadenceAction.INVOKE_ONE_TRANSITION
    assert enabled.transition_invocation_limit == 1
    assert pipeline_disabled.status is cadence.CadenceStatus.REVIEW_READY


def test_distinct_wakes_enforce_minimum_interval() -> None:
    first = _evidence(sequence=1, started_at=BASE)
    checked = BASE + timedelta(minutes=2)
    plan = cadence.plan_bounded_pipeline_cadence(
        checked_at=checked,
        cadence_started_at=STARTED,
        pipeline_plan=_data_plan(checked, enabled=True),
        prior_wakes=(first,),
        review_enabled_candidate=True,
    )

    assert plan.status is cadence.CadenceStatus.WAITING
    assert plan.next_action is cadence.CadenceAction.WAIT_FOR_MINIMUM_INTERVAL
    assert plan.next_wake_at == "2026-08-28T21:05:30+00:00"


def test_formally_advanced_wake_allows_next_distinct_action_after_interval() -> None:
    first = _evidence(sequence=1, started_at=BASE)
    checked = BASE + timedelta(minutes=6)
    plan = cadence.plan_bounded_pipeline_cadence(
        checked_at=checked,
        cadence_started_at=STARTED,
        pipeline_plan=_data_plan(checked, enabled=True),
        prior_wakes=(first,),
        review_enabled_candidate=True,
    )

    assert plan.status is cadence.CadenceStatus.WAKE_READY
    assert plan.transition_wakes_used == 1
    assert plan.transition_wakes_remaining == 15


@pytest.mark.parametrize(
    ("outcome", "expected_action"),
    (
        (
            cadence.CadenceWakeOutcome.FAILED,
            cadence.CadenceAction.STOP_AFTER_KNOWN_FAILURE,
        ),
        (
            cadence.CadenceWakeOutcome.UNKNOWN,
            cadence.CadenceAction.STOP_AFTER_UNKNOWN_OUTCOME,
        ),
    ),
)
def test_offline_fault_or_unknown_outcome_stops_without_replay(
    outcome, expected_action
) -> None:
    prior_plan = _offline_plan()
    first = _evidence(
        sequence=1,
        started_at=OFFLINE_BASE,
        outcome=outcome,
        plan=prior_plan,
        cadence_started_at=OFFLINE_BASE - timedelta(minutes=30),
    )
    checked = OFFLINE_BASE + timedelta(minutes=6)
    plan = cadence.plan_bounded_pipeline_cadence(
        checked_at=checked,
        cadence_started_at=OFFLINE_BASE - timedelta(minutes=30),
        pipeline_plan=_offline_plan(checked, enabled=True),
        prior_wakes=(first,),
        review_enabled_candidate=True,
    )

    assert plan.status is cadence.CadenceStatus.STOPPED
    assert plan.next_action is expected_action
    assert plan.automatic_retry_enabled is False
    assert plan.automatic_recovery_enabled is False
    assert plan.transition_invocation_count == 0


def test_manual_review_always_stops_even_when_candidates_are_enabled() -> None:
    pipeline = _manual_plan(enabled=True)
    checked = datetime.fromisoformat(pipeline.checked_at)
    plan = cadence.plan_bounded_pipeline_cadence(
        checked_at=checked,
        cadence_started_at=checked - timedelta(minutes=30),
        pipeline_plan=pipeline,
        review_enabled_candidate=True,
    )

    assert plan.status is cadence.CadenceStatus.STOPPED
    assert plan.next_action is cadence.CadenceAction.STOP_FOR_MANUAL_REVIEW
    assert plan.publication_authorized is False
    assert plan.deployment_authorized is False


def test_sixteen_transition_wakes_exhaust_fixed_candidate_budget() -> None:
    wakes = tuple(
        _evidence(
            sequence=index,
            started_at=STARTED + timedelta(minutes=6 * index),
        )
        for index in range(1, 17)
    )
    checked = STARTED + timedelta(minutes=100)
    plan = cadence.plan_bounded_pipeline_cadence(
        checked_at=checked,
        cadence_started_at=STARTED,
        pipeline_plan=_data_plan(checked, enabled=True),
        prior_wakes=wakes,
        review_enabled_candidate=True,
    )

    assert plan.status is cadence.CadenceStatus.STOPPED
    assert plan.next_action is cadence.CadenceAction.STOP_AT_BUDGET
    assert plan.transition_wakes_remaining == 0


def test_four_hour_window_is_a_hard_stop() -> None:
    checked = STARTED + timedelta(hours=4)
    plan = cadence.plan_bounded_pipeline_cadence(
        checked_at=checked,
        cadence_started_at=STARTED,
        pipeline_plan=_data_plan(checked, enabled=True),
        review_enabled_candidate=True,
    )

    assert plan.status is cadence.CadenceStatus.STOPPED
    assert plan.next_action is cadence.CadenceAction.STOP_AT_BUDGET


def test_waiting_pipeline_uses_its_later_readiness_boundary() -> None:
    checked = datetime(2026, 8, 28, 20, 10, tzinfo=UTC)
    plan = cadence.plan_bounded_pipeline_cadence(
        checked_at=checked,
        cadence_started_at=checked,
        pipeline_plan=_data_plan(checked),
    )

    assert plan.status is cadence.CadenceStatus.WAITING
    assert plan.next_action is cadence.CadenceAction.WAIT_FOR_PIPELINE_CHECK
    assert plan.next_wake_at == "2026-08-28T20:30:00+00:00"


def test_invalid_evidence_chain_and_widened_policy_fail_closed() -> None:
    first = _evidence(sequence=1, started_at=BASE)
    too_soon = _evidence(sequence=2, started_at=BASE + timedelta(minutes=1))
    checked = BASE + timedelta(minutes=10)

    with pytest.raises(cadence.DailyEodPipelineCadenceError, match="chain"):
        cadence.plan_bounded_pipeline_cadence(
            checked_at=checked,
            cadence_started_at=STARTED,
            pipeline_plan=_data_plan(checked),
            prior_wakes=(first, too_soon),
        )
    with pytest.raises(cadence.DailyEodPipelineCadenceError, match="limits"):
        cadence.plan_bounded_pipeline_cadence(
            checked_at=checked,
            cadence_started_at=STARTED,
            pipeline_plan=_data_plan(checked),
            policy=cadence.BoundedCadencePolicy(maximum_transition_wakes=17),
        )


def test_refingerprinted_pipeline_authority_or_state_conflict_is_rejected() -> None:
    selected = _data_plan(enabled=True)
    authority = _refingerprint_pipeline(selected, publication_authorized=True)
    conflict = _refingerprint_pipeline(
        selected,
        status=scheduler.PipelineWakeStatus.BLOCKED,
    )

    for invalid in (authority, conflict):
        with pytest.raises(
            cadence.DailyEodPipelineCadenceError,
            match="pipeline wake plan is invalid",
        ):
            cadence.plan_bounded_pipeline_cadence(
                checked_at=BASE,
                cadence_started_at=STARTED,
                pipeline_plan=invalid,
                review_enabled_candidate=True,
            )


def test_refingerprinted_cadence_semantic_conflict_is_rejected() -> None:
    valid = cadence.plan_bounded_pipeline_cadence(
        checked_at=BASE,
        cadence_started_at=STARTED,
        pipeline_plan=_data_plan(enabled=True),
        review_enabled_candidate=True,
    )
    invalid = _refingerprint_cadence(
        valid,
        status=cadence.CadenceStatus.REVIEW_READY,
        next_action=cadence.CadenceAction.REVIEW_ONE_TRANSITION,
    )

    with pytest.raises(cadence.DailyEodPipelineCadenceError, match="enablement"):
        cadence.verify_bounded_pipeline_cadence_plan(invalid)
