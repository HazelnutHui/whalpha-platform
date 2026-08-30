from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta

import pytest

from tip_api.services import daily_eod_cadence_evidence as custody
from tip_api.services import daily_eod_pipeline_cadence as cadence
from tip_api.services import daily_eod_pipeline_scheduler as scheduler
from tip_api.services import daily_eod_run_journal as journal
from tip_api.services.daily_eod_automation import (
    CONTRACT_VERSION as AUTOMATION_CONTRACT_VERSION,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_coordinator import (
    CONTRACT_VERSION as COORDINATOR_CONTRACT_VERSION,
    CoordinatorStatus,
    DailyEodCoordinatorResult,
    daily_eod_coordinator_result_fingerprint,
)
from tip_api.services.daily_eod_executor import (
    DailyEodExecutionResult,
    StageExecutionEvidence,
)


TARGET = date(2026, 8, 28)
PRIOR = date(2026, 8, 27)
STARTED = datetime(2026, 8, 29, 12, tzinfo=UTC)
COMPLETED = STARTED + timedelta(seconds=30)


def _automation_plan(
    action: NextAction,
    *,
    fingerprint: str = "a" * 64,
) -> DailyEodAutomationPlan:
    return DailyEodAutomationPlan(
        contract_version=AUTOMATION_CONTRACT_VERSION,
        target_session=TARGET.isoformat(),
        prior_session=PRIOR.isoformat(),
        status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        next_action=action,
        reason_codes=("test",),
        observations=(),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=fingerprint,
    )


def _offline_pipeline(checked_at: datetime = STARTED):
    automation = _automation_plan(NextAction.CALCULATE_PHASE1A)
    logical = asdict(automation)
    logical.pop("logical_content_fingerprint")
    automation = replace(
        automation,
        logical_content_fingerprint=scheduler._fingerprint(
            scheduler._jsonable(logical)
        ),
    )
    return scheduler.plan_daily_eod_pipeline_wake(
        checked_at=checked_at,
        completed_sessions=(PRIOR, TARGET),
        latest_pipeline_plan=automation,
        review_enabled_candidate=True,
    )


def _data_pipeline(checked_at: datetime = STARTED):
    return scheduler.plan_daily_eod_pipeline_wake(
        checked_at=checked_at,
        completed_sessions=(PRIOR,),
        review_enabled_candidate=True,
    )


def _cadence_plan(pipeline, *, prior_wakes=()):
    checked = datetime.fromisoformat(pipeline.checked_at)
    return cadence.plan_bounded_pipeline_cadence(
        checked_at=checked,
        cadence_started_at=STARTED - timedelta(minutes=30),
        pipeline_plan=pipeline,
        prior_wakes=prior_wakes,
        review_enabled_candidate=True,
    )


def _coordinator_result(
    status: CoordinatorStatus,
    *,
    next_action: str,
    transition_fingerprint: str | None,
    next_check_at: str | None = None,
) -> DailyEodCoordinatorResult:
    result = DailyEodCoordinatorResult(
        status=status,
        target_session=TARGET.isoformat(),
        next_action=next_action,
        reason_codes=("test",),
        automation_plan_fingerprint="a" * 64,
        readiness_plan_fingerprint="b" * 64,
        transition_fingerprint=transition_fingerprint,
        external_request_count=0,
        production_write_count=0,
        next_check_at=next_check_at,
        contract_version=COORDINATOR_CONTRACT_VERSION,
    )
    return replace(
        result,
        logical_content_fingerprint=daily_eod_coordinator_result_fingerprint(result),
    )


def _event(
    event_type: str,
    *,
    attempt_id: str = "c" * 64,
    observed_at: datetime = COMPLETED,
) -> journal.DailyEodRunEvent:
    base = {
        "contract_version": journal.JOURNAL_CONTRACT,
        "sequence": 1,
        "event_type": event_type,
        "target_session": TARGET.isoformat(),
        "observed_at": observed_at.isoformat(),
        "attempt_id": attempt_id,
        "previous_event_fingerprint": None,
        "details": {"reason_code": "test"},
    }
    return journal.DailyEodRunEvent(
        **base,
        event_fingerprint=journal._fingerprint(base),
    )


def _offline_result(*, succeeded: bool) -> DailyEodExecutionResult:
    pipeline = _offline_pipeline()
    action = NextAction.CALCULATE_PHASE1A
    pre = _automation_plan(
        action,
        fingerprint=str(pipeline.automation_plan_fingerprint),
    )
    attempt_id = "c" * 64
    return DailyEodExecutionResult(
        outcome="succeeded" if succeeded else "failed",
        action=action,
        attempt_id=attempt_id,
        event=_event(
            "action_succeeded" if succeeded else "action_failed",
            attempt_id=attempt_id,
        ),
        pre_plan=pre,
        post_plan=(
            _automation_plan(
                NextAction.CALCULATE_PHASE1B_INCREMENTAL,
                fingerprint="d" * 64,
            )
            if succeeded
            else None
        ),
        stage_evidence=(
            StageExecutionEvidence(
                action=action,
                output_path="/tmp/phase1a",
                summary_sha256="e" * 64,
                summary_bytes=10,
            )
            if succeeded
            else None
        ),
        reason_code=(
            "offline_action_completed_and_replanned"
            if succeeded
            else "offline_action_raised"
        ),
    )


@pytest.mark.parametrize(
    ("status", "next_action", "transition", "expected"),
    (
        (
            CoordinatorStatus.TRANSITION_EXECUTED,
            "fetch_eod",
            "f" * 64,
            cadence.CadenceWakeOutcome.ADVANCED,
        ),
        (
            CoordinatorStatus.WAITING,
            "wait",
            None,
            cadence.CadenceWakeOutcome.NO_CHANGE,
        ),
        (
            CoordinatorStatus.BLOCKED,
            "operator_diagnosis",
            "f" * 64,
            cadence.CadenceWakeOutcome.FAILED,
        ),
    ),
)
def test_coordinator_results_project_without_inferred_success(
    status, next_action, transition, expected
) -> None:
    pipeline = _data_pipeline()
    evidence = custody.cadence_evidence_from_coordinator_result(
        sequence=1,
        started_at=STARTED,
        completed_at=COMPLETED,
        cadence_plan=_cadence_plan(pipeline),
        pipeline_plan=pipeline,
        result=_coordinator_result(
            status,
            next_action=next_action,
            transition_fingerprint=transition,
        ),
    )

    assert evidence.outcome is expected


def test_waiting_result_carries_formal_retry_boundary_into_next_cadence() -> None:
    pipeline = _data_pipeline()
    plan = _cadence_plan(pipeline)
    next_check = STARTED + timedelta(minutes=30)
    evidence = custody.cadence_evidence_from_coordinator_result(
        sequence=1,
        started_at=STARTED,
        completed_at=COMPLETED,
        cadence_plan=plan,
        pipeline_plan=pipeline,
        result=_coordinator_result(
            CoordinatorStatus.WAITING,
            next_action="wait",
            transition_fingerprint=None,
            next_check_at=next_check.isoformat(),
        ),
    )
    checked = STARTED + timedelta(minutes=6)
    refreshed = _data_pipeline(checked)
    next_plan = cadence.plan_bounded_pipeline_cadence(
        checked_at=checked,
        cadence_started_at=STARTED - timedelta(minutes=30),
        pipeline_plan=refreshed,
        prior_wakes=(evidence,),
        review_enabled_candidate=True,
    )

    assert evidence.next_eligible_at == next_check.isoformat()
    assert next_plan.status is cadence.CadenceStatus.WAITING
    assert next_plan.next_wake_at == next_check.isoformat()


@pytest.mark.parametrize(
    ("succeeded", "expected"),
    (
        (True, cadence.CadenceWakeOutcome.ADVANCED),
        (False, cadence.CadenceWakeOutcome.FAILED),
    ),
)
def test_offline_results_project_success_and_failure_exactly(
    succeeded, expected
) -> None:
    pipeline = _offline_pipeline()
    evidence = custody.cadence_evidence_from_offline_result(
        sequence=1,
        started_at=STARTED,
        completed_at=COMPLETED,
        cadence_plan=_cadence_plan(pipeline),
        pipeline_plan=pipeline,
        result=_offline_result(succeeded=succeeded),
    )

    assert evidence.outcome is expected
    assert evidence.result_fingerprint == _offline_result(
        succeeded=succeeded
    ).event.event_fingerprint


def test_tampered_or_mismatched_results_fail_closed() -> None:
    result = _coordinator_result(
        CoordinatorStatus.TRANSITION_EXECUTED,
        next_action="fetch_eod",
        transition_fingerprint="f" * 64,
    )
    data_pipeline = _data_pipeline()
    with pytest.raises(custody.DailyEodCadenceEvidenceError):
        custody.cadence_evidence_from_coordinator_result(
            sequence=1,
            started_at=STARTED,
            completed_at=COMPLETED,
            cadence_plan=_cadence_plan(data_pipeline),
            pipeline_plan=data_pipeline,
            result=replace(result, target_session=PRIOR.isoformat()),
        )
    offline_pipeline = _offline_pipeline()
    with pytest.raises(custody.DailyEodCadenceEvidenceError, match="differs"):
        custody.cadence_evidence_from_offline_result(
            sequence=1,
            started_at=STARTED,
            completed_at=COMPLETED,
            cadence_plan=_cadence_plan(offline_pipeline),
            pipeline_plan=offline_pipeline,
            result=replace(
                _offline_result(succeeded=True),
                action=NextAction.CALCULATE_CANDIDATE_DAILY,
            ),
        )


def _root(tmp_path):
    root = tmp_path / "daily-runs"
    root.mkdir(parents=True, mode=0o700)
    root.chmod(0o700)
    return root


def _known_evidence(sequence: int = 1):
    pipeline = _offline_pipeline()
    cadence_plan = _cadence_plan(pipeline)
    return custody.cadence_evidence_from_offline_result(
        sequence=sequence,
        started_at=STARTED,
        completed_at=COMPLETED + timedelta(minutes=sequence - 1),
        cadence_plan=cadence_plan,
        pipeline_plan=pipeline,
        result=_offline_result(succeeded=False),
    ), cadence_plan


def test_known_evidence_appends_to_existing_owner_only_journal(tmp_path) -> None:
    root = _root(tmp_path)
    evidence, cadence_plan = _known_evidence()

    retained_event = custody.append_cadence_wake_evidence(
        run_root=root,
        target_session=TARGET,
        cadence_plan=cadence_plan,
        evidence=evidence,
    )

    with journal.locked_daily_eod_run_journal(
        run_root=root,
        target_session=TARGET,
    ) as locked:
        events = locked.read_events()
    assert custody.cadence_evidence_from_events(
        events,
        target_session=TARGET,
    ) == (evidence,)
    assert retained_event.event_type == journal.CADENCE_WAKE_RECORDED_EVENT
    assert (root / "session=2026-08-28" / "event-000001.json").stat().st_mode & 0o777 == 0o400


def test_two_advanced_wakes_retain_one_cadence_start_and_exact_budget(tmp_path) -> None:
    root = _root(tmp_path)
    first_pipeline = _data_pipeline()
    first_plan = _cadence_plan(first_pipeline)
    first = custody.cadence_evidence_from_coordinator_result(
        sequence=1,
        started_at=STARTED,
        completed_at=COMPLETED,
        cadence_plan=first_plan,
        pipeline_plan=first_pipeline,
        result=_coordinator_result(
            CoordinatorStatus.TRANSITION_EXECUTED,
            next_action="fetch_eod",
            transition_fingerprint="f" * 64,
        ),
    )
    custody.append_cadence_wake_evidence(
        run_root=root,
        target_session=TARGET,
        cadence_plan=first_plan,
        evidence=first,
    )

    second_started = STARTED + timedelta(minutes=6)
    second_pipeline = _data_pipeline(second_started)
    second_plan = _cadence_plan(second_pipeline, prior_wakes=(first,))
    second = custody.cadence_evidence_from_coordinator_result(
        sequence=2,
        started_at=second_started,
        completed_at=second_started + timedelta(seconds=30),
        cadence_plan=second_plan,
        pipeline_plan=second_pipeline,
        result=_coordinator_result(
            CoordinatorStatus.TRANSITION_EXECUTED,
            next_action="apply_eod",
            transition_fingerprint="e" * 64,
        ),
    )
    custody.append_cadence_wake_evidence(
        run_root=root,
        target_session=TARGET,
        cadence_plan=second_plan,
        evidence=second,
    )

    with journal.locked_daily_eod_run_journal(
        run_root=root,
        target_session=TARGET,
    ) as locked:
        retained = custody.cadence_evidence_from_events(
            locked.read_events(),
            target_session=TARGET,
        )
    assert retained == (first, second)
    assert second.cadence_started_at == first.cadence_started_at
    assert second_plan.transition_wakes_used == 1


def test_duplicate_result_and_unknown_outcome_are_not_persisted(tmp_path) -> None:
    root = _root(tmp_path)
    first, cadence_plan = _known_evidence()
    custody.append_cadence_wake_evidence(
        run_root=root,
        target_session=TARGET,
        cadence_plan=cadence_plan,
        evidence=first,
    )
    with pytest.raises(custody.DailyEodCadenceEvidenceError, match="duplicated"):
        custody.append_cadence_wake_evidence(
            run_root=root,
            target_session=TARGET,
            cadence_plan=cadence_plan,
            evidence=first,
        )

    empty_root = _root(tmp_path / "unknown")
    pipeline = _offline_pipeline()
    unknown_plan = _cadence_plan(pipeline)
    unknown = custody.unknown_cadence_wake_evidence(
        sequence=1,
        started_at=STARTED,
        cadence_plan=unknown_plan,
        pipeline_plan=pipeline,
    )
    with pytest.raises(custody.DailyEodCadenceEvidenceError, match="known"):
        custody.append_cadence_wake_evidence(
            run_root=empty_root,
            target_session=TARGET,
            cadence_plan=unknown_plan,
            evidence=unknown,
        )


def test_unresolved_action_blocks_cadence_evidence_append(tmp_path) -> None:
    root = _root(tmp_path)
    with journal.locked_daily_eod_run_journal(
        run_root=root,
        target_session=TARGET,
    ) as locked:
        attempt_id = journal.new_attempt_id(
            target_session=TARGET,
            plan_fingerprint="a" * 64,
            sequence=1,
        )
        locked.append(
            event_type="action_started",
            attempt_id=attempt_id,
            details={"action": "calculate_phase1a"},
            observed_at=STARTED,
        )

    with pytest.raises(custody.DailyEodCadenceEvidenceError, match="journal"):
        evidence, cadence_plan = _known_evidence()
        custody.append_cadence_wake_evidence(
            run_root=root,
            target_session=TARGET,
            cadence_plan=cadence_plan,
            evidence=evidence,
        )
