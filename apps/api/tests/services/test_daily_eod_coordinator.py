from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_coordinator import (
    AuthorizedTransitionEvidence,
    CoordinatorStatus,
    DailyEodCoordinatorConfig,
    DailyEodCoordinatorError,
    coordinate_daily_eod_transition,
)
from tip_api.services.daily_eod_executor import (
    DailyEodExecutionResult,
    StageExecutionEvidence,
)
from tip_api.services.daily_eod_run_journal import DailyEodRunEvent


TARGET = date(2026, 8, 27)
LATEST = date(2026, 8, 26)
AFTER_STABILIZATION = datetime(2026, 8, 27, 21, 0, tzinfo=UTC)
FINGERPRINT = "a" * 64


def paths() -> DailyEodAutomationPaths:
    return DailyEodAutomationPaths(
        data_root=Path("/data/trading-intelligence-platform"),
        phase1a_audit=Path("/tmp/phase1a"),
        prior_phase1b_audit=Path("/tmp/prior-phase1b"),
        phase1b_audit=Path("/tmp/phase1b"),
        prior_candidate_audit=Path("/tmp/prior-candidate"),
        candidate_audit=Path("/tmp/candidate"),
        entry_geometry_audit=Path("/tmp/entry"),
    )


def config(*, latest: date = LATEST) -> DailyEodCoordinatorConfig:
    return DailyEodCoordinatorConfig(
        target_session=TARGET,
        latest_canonical_session=latest,
        paths=paths(),
        run_root=Path("/tmp/daily-run-root"),
        package_path=Path("/tmp/daily-package"),
        approval_plan_path=Path("/tmp/daily-plan.json"),
    )


def plan(
    action: NextAction,
    *,
    status: PlanStatus | None = None,
    fingerprint: str = FINGERPRINT,
) -> DailyEodAutomationPlan:
    selected_status = status
    if selected_status is None:
        selected_status = (
            PlanStatus.READY_FOR_OFFLINE_CALCULATION
            if action in {
                NextAction.CALCULATE_PHASE1A,
                NextAction.CALCULATE_PHASE1B_INCREMENTAL,
                NextAction.CALCULATE_CANDIDATE_DAILY,
                NextAction.CALCULATE_ENTRY_GEOMETRY,
            }
            else PlanStatus.WAITING_FOR_AUTHORIZED_INPUT
        )
    return DailyEodAutomationPlan(
        contract_version="daily-eod-automation-plan/1.0",
        target_session=TARGET.isoformat(),
        prior_session=LATEST.isoformat(),
        status=selected_status,
        next_action=action,
        reason_codes=("fixture_reason",),
        observations=(),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=fingerprint,
    )


def planner(value: DailyEodAutomationPlan):
    def selected(**_kwargs):
        return value

    return selected


def journal(events: tuple[DailyEodRunEvent, ...] = ()):
    def selected(_run_root: Path, _target: date):
        return events

    return selected


def event(
    sequence: int,
    event_type: str,
    *,
    attempt_id: str = "b" * 64,
    details: dict[str, object] | None = None,
    observed_at: str = "2026-08-27T20:31:00+00:00",
) -> DailyEodRunEvent:
    return DailyEodRunEvent(
        sequence=sequence,
        event_type=event_type,
        target_session=TARGET.isoformat(),
        observed_at=observed_at,
        attempt_id=attempt_id,
        previous_event_fingerprint=None if sequence == 1 else "c" * 64,
        details=details or {},
        event_fingerprint=("d" if sequence == 1 else "e") * 64,
    )


def completed_fetch_events(
    action: NextAction,
) -> tuple[DailyEodRunEvent, DailyEodRunEvent]:
    started = event(
        1,
        "acquisition_started",
        details={
            "acquisition_action": action.value,
            "attempt_number": 1,
        },
    )
    completed = event(
        2,
        "acquisition_package_ready",
        details={"outcome": "fetch_package_ready"},
        observed_at="2026-08-27T20:32:00+00:00",
    )
    return started, completed


def test_waits_without_calling_a_capability_before_stabilization() -> None:
    calls: list[object] = []
    result = coordinate_daily_eod_transition(
        config=config(),
        checked_at=datetime(2026, 8, 27, 20, 10, tzinfo=UTC),
        planner=planner(plan(NextAction.PREPARE_IDENTITY_CATCHUP)),
        journal_reader=journal(),
        fetch_capability=lambda context: calls.append(context),  # type: ignore[arg-type,return-value]
    )

    assert result.status is CoordinatorStatus.WAITING
    assert result.next_action == "wait"
    assert calls == []
    assert result.external_request_count == 0
    assert result.production_write_count == 0


def test_ready_fetch_requires_manual_authorization_by_default() -> None:
    result = coordinate_daily_eod_transition(
        config=config(),
        checked_at=AFTER_STABILIZATION,
        planner=planner(plan(NextAction.PREPARE_IDENTITY_CATCHUP)),
        journal_reader=journal(),
    )

    assert result.status is CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED
    assert result.next_action == "review_fetch_authorization"
    assert result.reason_codes == ("authorized_fetch_capability_not_installed",)
    assert result.as_dict()["status"] == "manual_authorization_required"


def test_fetch_capability_is_called_exactly_once_with_exact_context() -> None:
    calls = []

    def fetch(context):
        calls.append(context)
        return AuthorizedTransitionEvidence(
            operation="fetch_identity",
            target_session=TARGET.isoformat(),
            precondition_fingerprint=context.readiness_plan.logical_content_fingerprint,
            outcome="succeeded",
            event_fingerprint="f" * 64,
            external_request_count=1,
            production_write_count=0,
            reason_code="fetch_package_ready",
        )

    result = coordinate_daily_eod_transition(
        config=config(),
        checked_at=AFTER_STABILIZATION,
        planner=planner(plan(NextAction.PREPARE_IDENTITY_CATCHUP)),
        journal_reader=journal(),
        fetch_capability=fetch,
    )

    assert len(calls) == 1
    assert calls[0].operation == "fetch_identity"
    assert calls[0].acquisition.package_path == Path("/tmp/daily-package")
    assert result.status is CoordinatorStatus.TRANSITION_EXECUTED
    assert result.external_request_count == 1
    assert result.production_write_count == 0


def test_identity_fetch_capability_can_report_bounded_pagination() -> None:
    def fetch(context):
        return AuthorizedTransitionEvidence(
            operation=context.operation,
            target_session=TARGET.isoformat(),
            precondition_fingerprint=context.readiness_plan.logical_content_fingerprint,
            outcome="succeeded",
            event_fingerprint="f" * 64,
            external_request_count=2,
            production_write_count=0,
            reason_code="two_page_identity_fetch",
        )

    result = coordinate_daily_eod_transition(
        config=config(),
        checked_at=AFTER_STABILIZATION,
        planner=planner(plan(NextAction.PREPARE_IDENTITY_CATCHUP)),
        journal_reader=journal(),
        fetch_capability=fetch,
    )

    assert result.external_request_count == 2


def test_identity_fetch_capability_cannot_claim_more_than_twenty_requests() -> None:
    def fetch(context):
        return AuthorizedTransitionEvidence(
            operation=context.operation,
            target_session=TARGET.isoformat(),
            precondition_fingerprint=context.readiness_plan.logical_content_fingerprint,
            outcome="succeeded",
            event_fingerprint="f" * 64,
            external_request_count=21,
            production_write_count=0,
            reason_code="too_many_requests",
        )

    with pytest.raises(DailyEodCoordinatorError, match="evidence is invalid"):
        coordinate_daily_eod_transition(
            config=config(),
            checked_at=AFTER_STABILIZATION,
            planner=planner(plan(NextAction.PREPARE_IDENTITY_CATCHUP)),
            journal_reader=journal(),
            fetch_capability=fetch,
        )


def test_successful_fetch_cannot_claim_zero_requests() -> None:
    def fetch(context):
        return AuthorizedTransitionEvidence(
            operation=context.operation,
            target_session=TARGET.isoformat(),
            precondition_fingerprint=context.readiness_plan.logical_content_fingerprint,
            outcome="succeeded",
            event_fingerprint="f" * 64,
            external_request_count=0,
            production_write_count=0,
            reason_code="false_success",
        )

    with pytest.raises(DailyEodCoordinatorError, match="evidence is invalid"):
        coordinate_daily_eod_transition(
            config=config(),
            checked_at=AFTER_STABILIZATION,
            planner=planner(plan(NextAction.PREPARE_EOD_CATCHUP)),
            journal_reader=journal(),
            fetch_capability=fetch,
        )

    with pytest.raises(DailyEodCoordinatorError, match="evidence is invalid"):
        coordinate_daily_eod_transition(
            config=config(),
            checked_at=AFTER_STABILIZATION,
            planner=planner(plan(NextAction.PREPARE_EOD_CATCHUP)),
            journal_reader=journal(),
            fetch_capability=fetch,
        )


def test_completed_fetch_requires_manual_apply_by_default() -> None:
    result = coordinate_daily_eod_transition(
        config=config(),
        checked_at=AFTER_STABILIZATION,
        planner=planner(plan(NextAction.PREPARE_EOD_CATCHUP)),
        journal_reader=journal(
            completed_fetch_events(NextAction.PREPARE_EOD_CATCHUP)
        ),
    )

    assert result.status is CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED
    assert result.next_action == "review_apply_authorization"
    assert result.external_request_count == 0
    assert result.production_write_count == 0


def test_apply_capability_is_called_once_and_bounded_to_one_write() -> None:
    calls = []

    def apply(context):
        calls.append(context)
        return AuthorizedTransitionEvidence(
            operation="apply_eod",
            target_session=TARGET.isoformat(),
            precondition_fingerprint=context.readiness_plan.logical_content_fingerprint,
            outcome="succeeded",
            event_fingerprint="f" * 64,
            external_request_count=0,
            production_write_count=1,
            reason_code="canonical_eod_applied",
        )

    result = coordinate_daily_eod_transition(
        config=config(),
        checked_at=AFTER_STABILIZATION,
        planner=planner(plan(NextAction.PREPARE_EOD_CATCHUP)),
        journal_reader=journal(
            completed_fetch_events(NextAction.PREPARE_EOD_CATCHUP)
        ),
        apply_capability=apply,
    )

    assert len(calls) == 1
    assert calls[0].approval_plan_path == Path("/tmp/daily-plan.json")
    assert result.status is CoordinatorStatus.TRANSITION_EXECUTED
    assert result.external_request_count == 0
    assert result.production_write_count == 1


@pytest.mark.parametrize(
    ("event_type", "next_action"),
    (
        ("acquisition_started", "recover_acquisition_attempt"),
        ("canonical_apply_started", "recover_canonical_apply"),
        ("action_started", "recover_offline_action"),
    ),
)
def test_unresolved_attempt_requires_recovery_before_any_action(
    event_type: str, next_action: str
) -> None:
    result = coordinate_daily_eod_transition(
        config=config(),
        checked_at=AFTER_STABILIZATION,
        planner=planner(plan(NextAction.PREPARE_IDENTITY_CATCHUP)),
        journal_reader=journal((event(1, event_type),)),
    )

    assert result.status is CoordinatorStatus.RECOVERY_REQUIRED
    assert result.next_action == next_action


def test_offline_action_is_ready_but_not_executed_by_default() -> None:
    result = coordinate_daily_eod_transition(
        config=config(latest=TARGET),
        checked_at=AFTER_STABILIZATION,
        planner=planner(plan(NextAction.CALCULATE_PHASE1A)),
        journal_reader=journal(),
    )

    assert result.status is CoordinatorStatus.READY_FOR_OFFLINE_EXECUTION
    assert result.next_action == "calculate_phase1a"


def test_downstream_action_requires_target_to_be_canonical() -> None:
    with pytest.raises(DailyEodCoordinatorError, match="canonical session is stale"):
        coordinate_daily_eod_transition(
            config=config(),
            checked_at=AFTER_STABILIZATION,
            planner=planner(plan(NextAction.CALCULATE_PHASE1A)),
            journal_reader=journal(),
        )


def test_opt_in_offline_execution_calls_existing_executor_once() -> None:
    calls = []
    pre_plan = plan(NextAction.CALCULATE_PHASE1A)
    terminal = event(2, "action_succeeded")

    def execute(**kwargs):
        calls.append(kwargs)
        return DailyEodExecutionResult(
            outcome="succeeded",
            action=NextAction.CALCULATE_PHASE1A,
            attempt_id="b" * 64,
            event=terminal,
            pre_plan=pre_plan,
            post_plan=plan(
                NextAction.CALCULATE_PHASE1B_INCREMENTAL,
                fingerprint="9" * 64,
            ),
            stage_evidence=StageExecutionEvidence(
                action=NextAction.CALCULATE_PHASE1A,
                output_path="/tmp/phase1a",
                summary_sha256="8" * 64,
                summary_bytes=10,
            ),
            reason_code="offline_action_completed_and_replanned",
        )

    result = coordinate_daily_eod_transition(
        config=config(latest=TARGET),
        checked_at=AFTER_STABILIZATION,
        execute_offline=True,
        planner=planner(pre_plan),
        journal_reader=journal(),
        offline_executor=execute,
    )

    assert len(calls) == 1
    assert calls[0]["expected_action"] is NextAction.CALCULATE_PHASE1A
    assert result.status is CoordinatorStatus.TRANSITION_EXECUTED
    assert result.external_request_count == 0
    assert result.production_write_count == 0


def test_blocked_and_publication_ready_states_never_execute() -> None:
    blocked = coordinate_daily_eod_transition(
        config=config(),
        checked_at=AFTER_STABILIZATION,
        planner=planner(
            plan(
                NextAction.OPERATOR_DIAGNOSIS,
                status=PlanStatus.BLOCKED,
            )
        ),
        journal_reader=journal(),
    )
    ready = coordinate_daily_eod_transition(
        config=config(latest=TARGET),
        checked_at=AFTER_STABILIZATION,
        planner=planner(
            plan(
                NextAction.REVIEW_PUBLICATION,
                status=PlanStatus.ANALYTICS_READY,
            )
        ),
        journal_reader=journal(),
    )

    assert blocked.status is CoordinatorStatus.BLOCKED
    assert ready.status is CoordinatorStatus.PUBLICATION_REVIEW_READY
    assert ready.publication_authorized is False
    assert ready.deployment_authorized is False
    assert ready.scheduler_enabled is False


def test_coordinator_rejects_unsafe_custody_paths() -> None:
    unsafe = replace(config(), package_path=Path("/var/tmp/package"))
    with pytest.raises(DailyEodCoordinatorError, match="custody path"):
        coordinate_daily_eod_transition(
            config=unsafe,
            checked_at=AFTER_STABILIZATION,
            planner=planner(plan(NextAction.PREPARE_EOD_CATCHUP)),
            journal_reader=journal(),
        )

    unsafe_root = replace(config(), run_root=Path("/data/run-journal"))
    with pytest.raises(DailyEodCoordinatorError, match="run root"):
        coordinate_daily_eod_transition(
            config=unsafe_root,
            checked_at=AFTER_STABILIZATION,
            planner=planner(plan(NextAction.PREPARE_EOD_CATCHUP)),
            journal_reader=journal(),
        )
