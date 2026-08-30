from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services.daily_eod_automation import (
    ArtifactObservation,
    ArtifactStatus,
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
    DeploymentTransitionEvidence,
    RecoveryTransitionEvidence,
    PublicationTransitionEvidence,
    coordinate_daily_eod_transition,
)
from tip_api.services.daily_eod_executor import (
    DailyEodExecutionResult,
    StageExecutionEvidence,
)
from tip_api.services.daily_eod_readiness import (
    AcquisitionOperatorReview,
    OperatorReviewDisposition,
    OperatorReviewEvidenceCode,
    OperatorReviewPurpose,
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
        phase2_audit=Path("/tmp/phase2"),
        preview_bundle=Path("/tmp/preview"),
        strategy_channel_audit=Path("/tmp/strategy"),
        market_intelligence_output_root=Path("/tmp/mi-output"),
        market_intelligence_approval_plan=Path("/tmp/mi-plan.json"),
        snapshot_output_root=Path("/tmp/snapshot-output"),
        snapshot_approval_plan=Path("/tmp/snapshot-plan.json"),
        serving_bundle_root=Path("/tmp/tip-serving-bundle"),
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
                NextAction.CALCULATE_ETF_RELATIONSHIPS,
                NextAction.BUILD_MARKET_PREVIEW,
                NextAction.CALCULATE_STRATEGY_CHANNELS,
                NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN,
                NextAction.PREPARE_DASHBOARD_SNAPSHOT_PLAN,
                NextAction.BUILD_SERVING_BUNDLE,
            }
            else PlanStatus.WAITING_FOR_AUTHORIZED_INPUT
        )
    return DailyEodAutomationPlan(
        contract_version="daily-eod-automation-plan/1.2",
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


def initial_eod_review_event() -> DailyEodRunEvent:
    reviewed_at = datetime(2026, 8, 27, 20, 31, tzinfo=UTC)
    review = AcquisitionOperatorReview(
        purpose=OperatorReviewPurpose.INITIAL_EOD_AVAILABILITY,
        acquisition_action=NextAction.PREPARE_EOD_CATCHUP,
        attempt_sequence=0,
        reviewed_at=reviewed_at,
        not_before=reviewed_at,
        disposition=OperatorReviewDisposition.AUTHORIZE_ONE_FETCH_AFTER,
        evidence_code=(
            OperatorReviewEvidenceCode.PROVIDER_PLAN_AND_RELEASE_REVIEWED
        ),
    )
    return event(
        1,
        "acquisition_operator_reviewed",
        details={
            "acquisition_action": NextAction.PREPARE_EOD_CATCHUP.value,
            "purpose": review.purpose.value,
            "attempt_sequence": 0,
            "not_before": reviewed_at.isoformat(),
            "disposition": review.disposition.value,
            "evidence_code": review.evidence_code.value,
            "source_event_fingerprint": None,
            "review_fingerprint": review.logical_fingerprint,
        },
        observed_at=reviewed_at.isoformat(),
    )


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
    assert result.next_check_at == "2026-08-27T20:30:00+00:00"
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
    assert result.alert_required is False


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
            journal_reader=journal((initial_eod_review_event(),)),
            fetch_capability=fetch,
        )

    with pytest.raises(DailyEodCoordinatorError, match="evidence is invalid"):
        coordinate_daily_eod_transition(
            config=config(),
            checked_at=AFTER_STABILIZATION,
            planner=planner(plan(NextAction.PREPARE_IDENTITY_CATCHUP)),
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
    ("outcome", "expected_status", "expected_action", "alert_required"),
    (
        ("waiting", CoordinatorStatus.WAITING, "wait", False),
        ("failed", CoordinatorStatus.BLOCKED, "operator_diagnosis", True),
    ),
)
def test_capability_non_success_is_not_reported_as_transition_executed(
    outcome, expected_status, expected_action, alert_required
) -> None:
    def fetch(context):
        return AuthorizedTransitionEvidence(
            operation=context.operation,
            target_session=TARGET.isoformat(),
            precondition_fingerprint=context.readiness_plan.logical_content_fingerprint,
            outcome=outcome,
            event_fingerprint="f" * 64,
            external_request_count=1,
            production_write_count=0,
            reason_code=f"fetch_{outcome}",
        )

    result = coordinate_daily_eod_transition(
        config=config(),
        checked_at=AFTER_STABILIZATION,
        planner=planner(plan(NextAction.PREPARE_IDENTITY_CATCHUP)),
        journal_reader=journal(),
        fetch_capability=fetch,
    )

    assert result.status is expected_status
    assert result.next_action == expected_action
    assert result.alert_required is alert_required
    assert result.transition_fingerprint is not None
    assert result.external_request_count == 1
    assert result.production_write_count == 0


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
    assert result.alert_required is True


@pytest.mark.parametrize(
    ("event_type", "recovery_action", "outcome"),
    (
        (
            "acquisition_started",
            "recover_acquisition_attempt",
            "recovered_package_ready",
        ),
        (
            "canonical_apply_started",
            "recover_canonical_apply",
            "recovered_succeeded",
        ),
        ("action_started", "recover_offline_action", "recovered_not_completed"),
    ),
)
def test_explicit_recovery_routes_exactly_one_pending_event(
    event_type: str,
    recovery_action: str,
    outcome: str,
) -> None:
    pending = event(1, event_type)
    calls = []

    def recover(context):
        calls.append(context)
        return RecoveryTransitionEvidence(
            recovery_action=recovery_action,
            target_session=TARGET.isoformat(),
            pending_event_fingerprint=pending.event_fingerprint,
            outcome=outcome,
            event_fingerprint="f" * 64,
            external_request_count=0,
            production_write_count=0,
            action_replayed=False,
            reason_code="formally_reconciled",
        )

    result = coordinate_daily_eod_transition(
        config=config(),
        checked_at=AFTER_STABILIZATION,
        recover_unresolved=True,
        planner=planner(plan(NextAction.PREPARE_IDENTITY_CATCHUP)),
        journal_reader=journal((pending,)),
        recovery_capability=recover,
    )

    assert len(calls) == 1
    assert calls[0].pending_event == pending
    assert calls[0].recovery_action == recovery_action
    assert result.status is CoordinatorStatus.TRANSITION_EXECUTED
    assert result.external_request_count == 0
    assert result.production_write_count == 0


def test_explicit_blocked_recovery_requires_operator_diagnosis() -> None:
    pending = event(1, "action_started")

    def recover(_context):
        return RecoveryTransitionEvidence(
            recovery_action="recover_offline_action",
            target_session=TARGET.isoformat(),
            pending_event_fingerprint=pending.event_fingerprint,
            outcome="recovery_blocked",
            event_fingerprint="f" * 64,
            external_request_count=0,
            production_write_count=0,
            action_replayed=False,
            reason_code="state_is_ambiguous",
        )

    result = coordinate_daily_eod_transition(
        config=config(),
        checked_at=AFTER_STABILIZATION,
        recover_unresolved=True,
        planner=planner(plan(NextAction.PREPARE_IDENTITY_CATCHUP)),
        journal_reader=journal((pending,)),
        recovery_capability=recover,
    )

    assert result.status is CoordinatorStatus.BLOCKED
    assert result.next_action == "operator_diagnosis"
    assert result.alert_required is True


def test_explicit_recovery_requires_a_capability_and_rejects_replay_claims() -> None:
    pending = event(1, "action_started")
    kwargs = {
        "config": config(),
        "checked_at": AFTER_STABILIZATION,
        "recover_unresolved": True,
        "planner": planner(plan(NextAction.PREPARE_IDENTITY_CATCHUP)),
        "journal_reader": journal((pending,)),
    }
    with pytest.raises(DailyEodCoordinatorError, match="explicit recovery capability"):
        coordinate_daily_eod_transition(**kwargs)

    def invalid(_context):
        return RecoveryTransitionEvidence(
            recovery_action="recover_offline_action",
            target_session=TARGET.isoformat(),
            pending_event_fingerprint=pending.event_fingerprint,
            outcome="recovered_not_completed",
            event_fingerprint="f" * 64,
            external_request_count=0,
            production_write_count=0,
            action_replayed=True,
            reason_code="invalid_replay",
        )

    with pytest.raises(DailyEodCoordinatorError, match="evidence is invalid"):
        coordinate_daily_eod_transition(**kwargs, recovery_capability=invalid)

    def wrong_family_outcome(_context):
        return replace(
            invalid(_context),
            action_replayed=False,
            outcome="recovered_package_ready",
        )

    with pytest.raises(DailyEodCoordinatorError, match="evidence is invalid"):
        coordinate_daily_eod_transition(
            **kwargs,
            recovery_capability=wrong_family_outcome,
        )


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


def test_publication_plan_execution_carries_exact_review_bindings() -> None:
    calls = []
    pre_plan = plan(NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN)
    bound_config = replace(
        config(latest=TARGET),
        publication_created_at=AFTER_STABILIZATION,
        publication_expected_current_state_fingerprint="7" * 64,
    )

    def execute(**kwargs):
        calls.append(kwargs)
        return DailyEodExecutionResult(
            outcome="succeeded",
            action=NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN,
            attempt_id="b" * 64,
            event=event(2, "action_succeeded"),
            pre_plan=pre_plan,
            post_plan=plan(
                NextAction.REVIEW_PUBLICATION,
                status=PlanStatus.ANALYTICS_READY,
                fingerprint="9" * 64,
            ),
            stage_evidence=StageExecutionEvidence(
                action=NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN,
                output_path="/tmp/mi-plan.json",
                summary_sha256="8" * 64,
                summary_bytes=10,
            ),
            reason_code="offline_action_completed_and_replanned",
        )

    result = coordinate_daily_eod_transition(
        config=bound_config,
        checked_at=AFTER_STABILIZATION,
        execute_offline=True,
        planner=planner(pre_plan),
        journal_reader=journal(),
        offline_executor=execute,
    )
    execution_config = calls[0]["config"]
    assert execution_config.publication_created_at == AFTER_STABILIZATION
    assert execution_config.publication_expected_current_state_fingerprint == "7" * 64
    assert result.status is CoordinatorStatus.TRANSITION_EXECUTED


def test_failed_offline_execution_is_blocked_not_transition_executed() -> None:
    pre_plan = plan(NextAction.CALCULATE_PHASE1A)

    def execute(**kwargs):
        return DailyEodExecutionResult(
            outcome="failed",
            action=NextAction.CALCULATE_PHASE1A,
            attempt_id="b" * 64,
            event=event(2, "action_failed"),
            pre_plan=pre_plan,
            post_plan=None,
            stage_evidence=None,
            reason_code="offline_action_raised",
        )

    result = coordinate_daily_eod_transition(
        config=config(latest=TARGET),
        checked_at=AFTER_STABILIZATION,
        execute_offline=True,
        planner=planner(pre_plan),
        journal_reader=journal(),
        offline_executor=execute,
    )

    assert result.status is CoordinatorStatus.BLOCKED
    assert result.next_action == "operator_diagnosis"
    assert result.alert_required is True
    assert result.transition_fingerprint == event(2, "action_failed").event_fingerprint


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
    assert blocked.alert_required is True
    assert ready.status is CoordinatorStatus.PUBLICATION_REVIEW_READY
    assert ready.publication_authorized is False
    assert ready.deployment_authorized is False
    assert ready.scheduler_enabled is False


def test_market_intelligence_apply_requires_explicit_flag_and_exact_capability() -> None:
    approval_fingerprint = "7" * 64
    ready_plan = replace(
        plan(
            NextAction.REVIEW_PUBLICATION,
            status=PlanStatus.ANALYTICS_READY,
        ),
        observations=(
            ArtifactObservation(
                stage="publication_plan",
                status=ArtifactStatus.COMPLETED,
                path="/tmp/mi-plan.json",
                as_of_session=TARGET.isoformat(),
                logical_fingerprint=approval_fingerprint,
            ),
        ),
    )
    calls = []

    def capability(context):
        calls.append(context)
        return PublicationTransitionEvidence(
            operation="apply_market_intelligence",
            target_session=TARGET.isoformat(),
            precondition_fingerprint=ready_plan.logical_content_fingerprint,
            outcome="succeeded",
            event_fingerprint="8" * 64,
            external_request_count=0,
            production_write_count=3,
            publication_id="publication-1",
            reason_code="market_intelligence_active_state_formally_proven",
        )

    result = coordinate_daily_eod_transition(
        config=config(latest=TARGET),
        checked_at=AFTER_STABILIZATION,
        apply_market_intelligence=True,
        publication_capability=capability,
        planner=planner(ready_plan),
        journal_reader=journal(),
        publication_plan_reader=lambda _path: SimpleNamespace(
            analysis_session=TARGET,
            plan_content_fingerprint=approval_fingerprint,
            publication_id="publication-1",
        ),
    )

    assert len(calls) == 1
    assert result.status is CoordinatorStatus.TRANSITION_EXECUTED
    assert result.next_action == "apply_market_intelligence"
    assert result.production_write_count == 3
    assert result.publication_authorized is False
    assert result.deployment_authorized is False
    assert result.scheduler_enabled is False


def test_market_intelligence_apply_flag_without_capability_fails_closed() -> None:
    with pytest.raises(DailyEodCoordinatorError, match="one-shot"):
        coordinate_daily_eod_transition(
            config=config(latest=TARGET),
            checked_at=AFTER_STABILIZATION,
            apply_market_intelligence=True,
            planner=planner(
                plan(
                    NextAction.REVIEW_PUBLICATION,
                    status=PlanStatus.ANALYTICS_READY,
                )
            ),
            journal_reader=journal(),
        )


def test_snapshot_review_is_a_separate_nonexecuting_stop() -> None:
    result = coordinate_daily_eod_transition(
        config=config(latest=TARGET),
        checked_at=AFTER_STABILIZATION,
        planner=planner(
            plan(
                NextAction.REVIEW_SNAPSHOT_PUBLICATION,
                status=PlanStatus.ANALYTICS_READY,
            )
        ),
        journal_reader=journal(),
    )

    assert result.status is CoordinatorStatus.PUBLICATION_REVIEW_READY
    assert result.next_action == "review_snapshot_publication"
    assert result.production_write_count == 0
    assert result.publication_authorized is False


def test_completed_bundle_is_a_nonexecuting_deployment_review_stop() -> None:
    result = coordinate_daily_eod_transition(
        config=config(latest=TARGET),
        checked_at=AFTER_STABILIZATION,
        planner=planner(
            plan(
                NextAction.REVIEW_BUNDLE_DEPLOYMENT,
                status=PlanStatus.ANALYTICS_READY,
            )
        ),
        journal_reader=journal(),
    )

    assert result.status is CoordinatorStatus.DEPLOYMENT_REVIEW_READY
    assert result.next_action == "review_bundle_deployment"
    assert result.production_write_count == 0
    assert result.publication_authorized is False
    assert result.deployment_authorized is False


def test_explicit_oci_deployment_requires_exact_bundle_evidence_and_capability() -> None:
    bundle_path = "/tmp/tip-serving-bundle/2026-08-29T120000Z-aaaaaaaaaaaa"
    ready = replace(
        plan(
            NextAction.REVIEW_BUNDLE_DEPLOYMENT,
            status=PlanStatus.ANALYTICS_READY,
        ),
        observations=(
            ArtifactObservation(
                stage="serving_bundle",
                status=ArtifactStatus.COMPLETED,
                path=bundle_path,
                as_of_session=TARGET.isoformat(),
                logical_fingerprint="7" * 64,
            ),
        ),
    )
    calls = []

    def capability(context):
        calls.append(context)
        return DeploymentTransitionEvidence(
            operation="deploy_oci_dashboard",
            target_session=TARGET.isoformat(),
            precondition_fingerprint=ready.logical_content_fingerprint,
            outcome="succeeded",
            event_fingerprint="8" * 64,
            external_request_count=3,
            production_write_count=1,
            release_id=Path(bundle_path).name,
            reason_code="exact_remote_postcondition_proven",
        )

    result = coordinate_daily_eod_transition(
        config=config(latest=TARGET),
        checked_at=AFTER_STABILIZATION,
        deploy_oci_dashboard=True,
        deployment_capability=capability,
        planner=planner(ready),
        journal_reader=journal(),
    )

    assert result.status is CoordinatorStatus.TRANSITION_EXECUTED
    assert result.next_action == "deploy_oci_dashboard"
    assert result.external_request_count == 3
    assert result.production_write_count == 1
    assert calls[0].bundle_logical_fingerprint == "7" * 64


def test_dashboard_snapshot_apply_requires_exact_one_shot_capability() -> None:
    approval_fingerprint = "7" * 64
    ready_plan = replace(
        plan(
            NextAction.REVIEW_SNAPSHOT_PUBLICATION,
            status=PlanStatus.ANALYTICS_READY,
        ),
        observations=(
            ArtifactObservation(
                stage="snapshot_plan",
                status=ArtifactStatus.COMPLETED,
                path="/tmp/snapshot-plan.json",
                as_of_session=TARGET.isoformat(),
                logical_fingerprint=approval_fingerprint,
            ),
        ),
    )
    calls = []

    def capability(context):
        calls.append(context)
        return PublicationTransitionEvidence(
            operation="apply_dashboard_snapshot",
            target_session=TARGET.isoformat(),
            precondition_fingerprint=ready_plan.logical_content_fingerprint,
            outcome="succeeded",
            event_fingerprint="8" * 64,
            external_request_count=0,
            production_write_count=3,
            publication_id="snapshot-1",
            reason_code="dashboard_snapshot_active_state_formally_proven",
        )

    result = coordinate_daily_eod_transition(
        config=config(latest=TARGET),
        checked_at=AFTER_STABILIZATION,
        apply_dashboard_snapshot=True,
        snapshot_publication_capability=capability,
        planner=planner(ready_plan),
        journal_reader=journal(),
        snapshot_plan_reader=lambda _path: SimpleNamespace(
            analysis_session=TARGET,
            plan_content_fingerprint=approval_fingerprint,
            release_id="snapshot-1",
            files=(SimpleNamespace(), SimpleNamespace()),
        ),
    )

    assert len(calls) == 1
    assert result.status is CoordinatorStatus.TRANSITION_EXECUTED
    assert result.next_action == "apply_dashboard_snapshot"
    assert result.production_write_count == 3
    assert result.publication_authorized is False
    assert result.deployment_authorized is False
    assert result.scheduler_enabled is False


def test_dashboard_snapshot_apply_without_capability_fails_closed() -> None:
    with pytest.raises(DailyEodCoordinatorError, match="one-shot"):
        coordinate_daily_eod_transition(
            config=config(latest=TARGET),
            checked_at=AFTER_STABILIZATION,
            apply_dashboard_snapshot=True,
            planner=planner(
                plan(
                    NextAction.REVIEW_SNAPSHOT_PUBLICATION,
                    status=PlanStatus.ANALYTICS_READY,
                )
            ),
            journal_reader=journal(),
        )


def test_elapsed_daily_deadline_propagates_alert_requirement() -> None:
    result = coordinate_daily_eod_transition(
        config=config(),
        checked_at=datetime(2026, 8, 28, 3, 0, tzinfo=UTC),
        planner=planner(plan(NextAction.PREPARE_EOD_CATCHUP)),
        journal_reader=journal(),
    )

    assert result.status is CoordinatorStatus.BLOCKED
    assert result.next_action == "operator_diagnosis"
    assert result.reason_codes[0] == (
        "basic_eod_release_window_requires_operator_review"
    )
    assert result.alert_required is True
    assert result.readiness_plan_fingerprint is not None


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
