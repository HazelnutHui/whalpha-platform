"""Coordinate at most one exact daily EOD state transition."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Callable

from tip_api.persistence.parquet.market_intelligence_active import (
    read_market_intelligence_approval_plan,
)
from tip_api.persistence.parquet.dashboard_snapshot_active import (
    read_dashboard_snapshot_approval_plan,
)
from tip_api.services.daily_eod_acquisition_custody import (
    DailyEodAcquisitionConfig,
    acquisition_attempts_from_events,
    acquisition_operator_reviews_from_events,
)
from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_executor import (
    OFFLINE_ACTIONS,
    DailyEodExecutionConfig,
    DailyEodExecutionResult,
    execute_daily_eod_action,
)
from tip_api.services.daily_eod_readiness import (
    DailyEodReadinessPlan,
    ReadinessNextAction,
    ReadinessStatus,
    plan_daily_eod_readiness,
)
from tip_api.services.daily_eod_run_journal import (
    ACQUISITION_START_EVENT,
    CANONICAL_APPLY_START_EVENT,
    DASHBOARD_SNAPSHOT_APPLY_START_EVENT,
    MARKET_INTELLIGENCE_APPLY_START_EVENT,
    OCI_DEPLOYMENT_START_EVENT,
    START_EVENT,
    DailyEodRunEvent,
    locked_daily_eod_run_journal,
    unresolved_started_event,
)


CONTRACT_VERSION = "daily-eod-one-transition-coordinator/1.14"


class DailyEodCoordinatorError(RuntimeError):
    """Raised when one exact daily transition cannot be coordinated safely."""


class CoordinatorStatus(StrEnum):
    WAITING = "waiting"
    MANUAL_AUTHORIZATION_REQUIRED = "manual_authorization_required"
    RECOVERY_REQUIRED = "recovery_required"
    READY_FOR_OFFLINE_EXECUTION = "ready_for_offline_execution"
    TRANSITION_EXECUTED = "transition_executed"
    PUBLICATION_REVIEW_READY = "publication_review_ready"
    DEPLOYMENT_REVIEW_READY = "deployment_review_ready"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class DailyEodCoordinatorConfig:
    target_session: date
    latest_canonical_session: date
    paths: DailyEodAutomationPaths
    run_root: Path
    package_path: Path
    approval_plan_path: Path
    panel_cache_root: Path | None = None
    candidate_work_dir: Path | None = None
    publication_created_at: datetime | None = None
    publication_expected_current_state_fingerprint: str | None = None
    snapshot_generated_at: datetime | None = None
    bundle_built_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AuthorizedTransitionContext:
    acquisition: DailyEodAcquisitionConfig
    approval_plan_path: Path
    automation_plan: DailyEodAutomationPlan
    readiness_plan: DailyEodReadinessPlan
    operation: str


@dataclass(frozen=True, slots=True)
class AuthorizedTransitionEvidence:
    operation: str
    target_session: str
    precondition_fingerprint: str
    outcome: str
    event_fingerprint: str
    external_request_count: int
    production_write_count: int
    reason_code: str


@dataclass(frozen=True, slots=True)
class RecoveryTransitionContext:
    coordinator: DailyEodCoordinatorConfig
    pending_event: DailyEodRunEvent
    automation_plan: DailyEodAutomationPlan
    recovery_action: str


@dataclass(frozen=True, slots=True)
class RecoveryTransitionEvidence:
    recovery_action: str
    target_session: str
    pending_event_fingerprint: str
    outcome: str
    event_fingerprint: str
    external_request_count: int
    production_write_count: int
    action_replayed: bool
    reason_code: str


@dataclass(frozen=True, slots=True)
class PublicationTransitionContext:
    coordinator: DailyEodCoordinatorConfig
    automation_plan: DailyEodAutomationPlan
    checked_at: datetime
    operation: str
    publication_id: str
    approval_plan_content_fingerprint: str


@dataclass(frozen=True, slots=True)
class PublicationTransitionEvidence:
    operation: str
    target_session: str
    precondition_fingerprint: str
    outcome: str
    event_fingerprint: str
    external_request_count: int
    production_write_count: int
    publication_id: str
    reason_code: str


@dataclass(frozen=True, slots=True)
class DeploymentTransitionContext:
    coordinator: DailyEodCoordinatorConfig
    automation_plan: DailyEodAutomationPlan
    checked_at: datetime
    operation: str
    bundle_path: Path
    release_id: str
    bundle_logical_fingerprint: str


@dataclass(frozen=True, slots=True)
class DeploymentTransitionEvidence:
    operation: str
    target_session: str
    precondition_fingerprint: str
    outcome: str
    event_fingerprint: str
    external_request_count: int
    production_write_count: int
    release_id: str
    reason_code: str


@dataclass(frozen=True, slots=True)
class DailyEodCoordinatorResult:
    status: CoordinatorStatus
    target_session: str
    next_action: str
    reason_codes: tuple[str, ...]
    automation_plan_fingerprint: str
    readiness_plan_fingerprint: str | None
    transition_fingerprint: str | None
    external_request_count: int
    production_write_count: int
    next_check_at: str | None = None
    alert_required: bool = False
    publication_authorized: bool = False
    deployment_authorized: bool = False
    scheduler_enabled: bool = False
    contract_version: str = CONTRACT_VERSION
    logical_content_fingerprint: str = ""

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


Planner = Callable[..., DailyEodAutomationPlan]
JournalReader = Callable[[Path, date], tuple[DailyEodRunEvent, ...]]
AuthorizedCapability = Callable[
    [AuthorizedTransitionContext], AuthorizedTransitionEvidence
]
RecoveryCapability = Callable[
    [RecoveryTransitionContext], RecoveryTransitionEvidence
]
PublicationCapability = Callable[
    [PublicationTransitionContext], PublicationTransitionEvidence
]
DeploymentCapability = Callable[
    [DeploymentTransitionContext], DeploymentTransitionEvidence
]
OfflineExecutor = Callable[..., DailyEodExecutionResult]
PublicationPlanReader = Callable[[Path], object]


def coordinate_daily_eod_transition(
    *,
    config: DailyEodCoordinatorConfig,
    checked_at: datetime,
    execute_offline: bool = False,
    recover_unresolved: bool = False,
    apply_market_intelligence: bool = False,
    apply_dashboard_snapshot: bool = False,
    deploy_oci_dashboard: bool = False,
    fetch_capability: AuthorizedCapability | None = None,
    apply_capability: AuthorizedCapability | None = None,
    recovery_capability: RecoveryCapability | None = None,
    publication_capability: PublicationCapability | None = None,
    snapshot_publication_capability: PublicationCapability | None = None,
    deployment_capability: DeploymentCapability | None = None,
    planner: Planner = plan_daily_eod_automation,
    journal_reader: JournalReader | None = None,
    offline_executor: OfflineExecutor = execute_daily_eod_action,
    publication_plan_reader: PublicationPlanReader = read_market_intelligence_approval_plan,
    snapshot_plan_reader: PublicationPlanReader = read_dashboard_snapshot_approval_plan,
) -> DailyEodCoordinatorResult:
    """Return or execute at most one exact transition; never loop or retry."""

    checked = _aware_utc(checked_at)
    _validate_config(config)
    if sum((apply_market_intelligence, apply_dashboard_snapshot, deploy_oci_dashboard)) > 1:
        raise DailyEodCoordinatorError(
            "publication Apply and OCI deployment modes are mutually exclusive"
        )
    plan = planner(target_session=config.target_session, paths=config.paths)
    _validate_plan(plan, config)
    events = (journal_reader or _read_journal_events)(
        config.run_root, config.target_session
    )
    pending = unresolved_started_event(events)
    if pending is not None:
        recovery_action, recovery_reason = _pending_recovery(pending)
        if not recover_unresolved:
            return _result(
                status=CoordinatorStatus.RECOVERY_REQUIRED,
                next_action=recovery_action,
                reasons=(recovery_reason,),
                plan=plan,
                alert=True,
            )
        if recovery_capability is None:
            raise DailyEodCoordinatorError(
                "recovery execution requires an explicit recovery capability"
            )
        recovery = recovery_capability(
            RecoveryTransitionContext(
                coordinator=config,
                pending_event=pending,
                automation_plan=plan,
                recovery_action=recovery_action,
            )
        )
        return _recovery_result(plan, pending, recovery, recovery_action)

    if plan.status is PlanStatus.BLOCKED or plan.next_action is NextAction.OPERATOR_DIAGNOSIS:
        return _result(
            status=CoordinatorStatus.BLOCKED,
            next_action=NextAction.OPERATOR_DIAGNOSIS.value,
            reasons=plan.reason_codes,
            plan=plan,
            alert=True,
        )
    if plan.status is PlanStatus.ANALYTICS_READY:
        if plan.next_action not in {
            NextAction.REVIEW_PUBLICATION,
            NextAction.REVIEW_SNAPSHOT_PUBLICATION,
            NextAction.REVIEW_BUNDLE_DEPLOYMENT,
        }:
            raise DailyEodCoordinatorError("analytics-ready plan has an invalid action")
        if plan.next_action is NextAction.REVIEW_BUNDLE_DEPLOYMENT:
            if apply_market_intelligence or apply_dashboard_snapshot:
                raise DailyEodCoordinatorError(
                    "publication Apply cannot run after bundle construction"
                )
            if not deploy_oci_dashboard:
                return _result(
                    status=CoordinatorStatus.DEPLOYMENT_REVIEW_READY,
                    next_action=NextAction.REVIEW_BUNDLE_DEPLOYMENT.value,
                    reasons=plan.reason_codes,
                    plan=plan,
                )
            observation = _serving_bundle_observation(plan)
            release_id = Path(observation.path).name
            if deployment_capability is None:
                raise DailyEodCoordinatorError(
                    "OCI deployment requires an explicit one-shot capability"
                )
            evidence = deployment_capability(
                DeploymentTransitionContext(
                    coordinator=config,
                    automation_plan=plan,
                    checked_at=checked,
                    operation="deploy_oci_dashboard",
                    bundle_path=Path(observation.path),
                    release_id=release_id,
                    bundle_logical_fingerprint=observation.logical_fingerprint,
                )
            )
            return _deployment_result(plan, evidence, release_id)
        if plan.next_action is NextAction.REVIEW_SNAPSHOT_PUBLICATION:
            if apply_market_intelligence:
                raise DailyEodCoordinatorError(
                    "MI Apply cannot run after the planner advanced to Snapshot review"
                )
            if not apply_dashboard_snapshot:
                return _result(
                    status=CoordinatorStatus.PUBLICATION_REVIEW_READY,
                    next_action=NextAction.REVIEW_SNAPSHOT_PUBLICATION.value,
                    reasons=plan.reason_codes,
                    plan=plan,
                )
            if snapshot_publication_capability is None:
                raise DailyEodCoordinatorError(
                    "Snapshot Apply requires an explicit one-shot publication capability"
                )
            approval = snapshot_plan_reader(config.paths.snapshot_approval_plan)
            if (
                getattr(approval, "analysis_session", None)
                != config.target_session
                or getattr(approval, "plan_content_fingerprint", None)
                != _snapshot_plan_fingerprint(plan)
                or not isinstance(getattr(approval, "release_id", None), str)
                or not isinstance(getattr(approval, "files", None), tuple)
            ):
                raise DailyEodCoordinatorError(
                    "reviewed Snapshot approval plan differs from automation evidence"
                )
            evidence = snapshot_publication_capability(
                PublicationTransitionContext(
                    coordinator=config,
                    automation_plan=plan,
                    checked_at=checked,
                    operation="apply_dashboard_snapshot",
                    publication_id=approval.release_id,
                    approval_plan_content_fingerprint=(
                        approval.plan_content_fingerprint
                    ),
                )
            )
            return _snapshot_publication_result(
                plan,
                evidence,
                approval.release_id,
                expected_write_count=len(approval.files) + 1,
            )
        if apply_dashboard_snapshot:
            raise DailyEodCoordinatorError(
                "Snapshot Apply cannot run before Snapshot publication review"
            )
        if not apply_market_intelligence:
            return _result(
                status=CoordinatorStatus.PUBLICATION_REVIEW_READY,
                next_action=NextAction.REVIEW_PUBLICATION.value,
                reasons=plan.reason_codes,
                plan=plan,
            )
        if publication_capability is None:
            raise DailyEodCoordinatorError(
                "MI Apply requires an explicit one-shot publication capability"
            )
        approval = publication_plan_reader(
            config.paths.market_intelligence_approval_plan
        )
        if (
            getattr(approval, "analysis_session", None) != config.target_session
            or getattr(approval, "plan_content_fingerprint", None)
            != _publication_plan_fingerprint(plan)
            or not isinstance(getattr(approval, "publication_id", None), str)
        ):
            raise DailyEodCoordinatorError(
                "reviewed MI approval plan differs from automation evidence"
            )
        evidence = publication_capability(
            PublicationTransitionContext(
                coordinator=config,
                automation_plan=plan,
                checked_at=checked,
                operation="apply_market_intelligence",
                publication_id=approval.publication_id,
                approval_plan_content_fingerprint=(
                    approval.plan_content_fingerprint
                ),
            )
        )
        return _publication_result(plan, evidence, approval.publication_id)
    if apply_market_intelligence or apply_dashboard_snapshot or deploy_oci_dashboard:
        raise DailyEodCoordinatorError(
            "requested publication Apply is not at its review boundary"
        )
    if plan.next_action in OFFLINE_ACTIONS:
        if plan.status is not PlanStatus.READY_FOR_OFFLINE_CALCULATION:
            raise DailyEodCoordinatorError("offline action is not calculation-ready")
        if not execute_offline:
            return _result(
                status=CoordinatorStatus.READY_FOR_OFFLINE_EXECUTION,
                next_action=plan.next_action.value,
                reasons=("offline_execution_requires_explicit_invocation",),
                plan=plan,
            )
        if (
            plan.next_action is NextAction.BUILD_SERVING_BUNDLE
            and config.bundle_built_at is None
        ):
            raise DailyEodCoordinatorError(
                "serving bundle construction requires an explicit UTC timestamp"
            )
        if (
            plan.next_action is not NextAction.BUILD_SERVING_BUNDLE
            and config.bundle_built_at is not None
        ):
            raise DailyEodCoordinatorError(
                "serving bundle timestamp is only valid for bundle construction"
            )
        execution = offline_executor(
            config=_execution_config(config),
            expected_plan_fingerprint=plan.logical_content_fingerprint,
            expected_action=plan.next_action,
            planner=planner,
        )
        return _offline_result(plan, execution)
    if plan.next_action not in {
        NextAction.PREPARE_IDENTITY_CATCHUP,
        NextAction.PREPARE_EOD_CATCHUP,
    }:
        raise DailyEodCoordinatorError("automation plan has no supported transition")

    acquisition = DailyEodAcquisitionConfig(
        target_session=config.target_session,
        latest_canonical_session=config.latest_canonical_session,
        acquisition_action=plan.next_action,
        package_path=config.package_path,
        run_root=config.run_root,
    )
    attempts = acquisition_attempts_from_events(
        events,
        target_session=config.target_session,
        acquisition_action=plan.next_action,
    )
    readiness = plan_daily_eod_readiness(
        checked_at=checked,
        target_session=config.target_session,
        latest_canonical_session=config.latest_canonical_session,
        acquisition_action=plan.next_action,
        attempts=attempts,
        operator_reviews=acquisition_operator_reviews_from_events(
            events,
            target_session=config.target_session,
            acquisition_action=plan.next_action,
        ),
    )
    if readiness.next_action is ReadinessNextAction.WAIT:
        return _result(
            status=CoordinatorStatus.WAITING,
            next_action=ReadinessNextAction.WAIT.value,
            reasons=readiness.reason_codes,
            plan=plan,
            readiness=readiness,
        )
    if readiness.next_action is ReadinessNextAction.OPERATOR_DIAGNOSIS:
        return _result(
            status=CoordinatorStatus.BLOCKED,
            next_action=ReadinessNextAction.OPERATOR_DIAGNOSIS.value,
            reasons=readiness.reason_codes,
            plan=plan,
            readiness=readiness,
            alert=readiness.alert_required,
        )
    if readiness.next_action is ReadinessNextAction.REVIEW_FETCH_AUTHORIZATION:
        operation = _operation(plan.next_action, apply=False)
        if fetch_capability is None:
            return _result(
                status=CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED,
                next_action=ReadinessNextAction.REVIEW_FETCH_AUTHORIZATION.value,
                reasons=("authorized_fetch_capability_not_installed",),
                plan=plan,
                readiness=readiness,
                alert=readiness.alert_required,
            )
        evidence = fetch_capability(
            _transition_context(config, acquisition, plan, readiness, operation)
        )
        return _capability_result(plan, readiness, evidence, operation, apply=False)
    if readiness.next_action is ReadinessNextAction.REVIEW_APPLY_AUTHORIZATION:
        operation = _operation(plan.next_action, apply=True)
        if apply_capability is None:
            return _result(
                status=CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED,
                next_action=ReadinessNextAction.REVIEW_APPLY_AUTHORIZATION.value,
                reasons=("authorized_apply_capability_not_installed",),
                plan=plan,
                readiness=readiness,
                alert=readiness.alert_required,
            )
        evidence = apply_capability(
            _transition_context(config, acquisition, plan, readiness, operation)
        )
        return _capability_result(plan, readiness, evidence, operation, apply=True)
    if readiness.status is ReadinessStatus.ALREADY_COMPLETED:
        raise DailyEodCoordinatorError("automation and readiness completion disagree")
    raise DailyEodCoordinatorError("readiness plan has no supported transition")


def _read_journal_events(
    run_root: Path, target_session: date
) -> tuple[DailyEodRunEvent, ...]:
    with locked_daily_eod_run_journal(
        run_root=run_root,
        target_session=target_session,
    ) as journal:
        return journal.read_events()


def _transition_context(
    config: DailyEodCoordinatorConfig,
    acquisition: DailyEodAcquisitionConfig,
    plan: DailyEodAutomationPlan,
    readiness: DailyEodReadinessPlan,
    operation: str,
) -> AuthorizedTransitionContext:
    return AuthorizedTransitionContext(
        acquisition=acquisition,
        approval_plan_path=config.approval_plan_path,
        automation_plan=plan,
        readiness_plan=readiness,
        operation=operation,
    )


def _operation(action: NextAction, *, apply: bool) -> str:
    subject = "identity" if action is NextAction.PREPARE_IDENTITY_CATCHUP else "eod"
    return f"{'apply' if apply else 'fetch'}_{subject}"


def _capability_result(
    plan: DailyEodAutomationPlan,
    readiness: DailyEodReadinessPlan,
    evidence: AuthorizedTransitionEvidence,
    operation: str,
    *,
    apply: bool,
) -> DailyEodCoordinatorResult:
    maximum_requests = 0 if apply else 20 if operation == "fetch_identity" else 1
    expected_writes = 1 if apply else 0
    if (
        not isinstance(evidence, AuthorizedTransitionEvidence)
        or evidence.operation != operation
        or evidence.target_session != plan.target_session
        or evidence.precondition_fingerprint
        != readiness.logical_content_fingerprint
        or evidence.outcome not in {"succeeded", "waiting", "failed"}
        or not _is_fingerprint(evidence.event_fingerprint)
        or not 0 <= evidence.external_request_count <= maximum_requests
        or not 0 <= evidence.production_write_count <= expected_writes
        or (
            evidence.outcome == "succeeded"
            and (
                (not apply and evidence.external_request_count < 1)
                or (apply and evidence.external_request_count != 0)
                or evidence.production_write_count != expected_writes
            )
        )
        or not evidence.reason_code
    ):
        raise DailyEodCoordinatorError("authorized capability evidence is invalid")
    status = {
        "succeeded": CoordinatorStatus.TRANSITION_EXECUTED,
        "waiting": CoordinatorStatus.WAITING,
        "failed": CoordinatorStatus.BLOCKED,
    }[evidence.outcome]
    return _result(
        status=status,
        next_action=(
            operation
            if evidence.outcome == "succeeded"
            else (
                ReadinessNextAction.WAIT.value
                if evidence.outcome == "waiting"
                else NextAction.OPERATOR_DIAGNOSIS.value
            )
        ),
        reasons=(evidence.reason_code,),
        plan=plan,
        readiness=readiness,
        transition_fingerprint=_fingerprint(asdict(evidence)),
        requests=evidence.external_request_count,
        writes=evidence.production_write_count,
        alert=evidence.outcome == "failed",
    )


def _offline_result(
    plan: DailyEodAutomationPlan,
    execution: DailyEodExecutionResult,
) -> DailyEodCoordinatorResult:
    if (
        not isinstance(execution, DailyEodExecutionResult)
        or execution.action is not plan.next_action
        or execution.pre_plan.logical_content_fingerprint
        != plan.logical_content_fingerprint
        or not _is_fingerprint(execution.event.event_fingerprint)
        or execution.outcome not in {"succeeded", "failed"}
        or (
            execution.outcome == "succeeded"
            and (
                execution.event.event_type != "action_succeeded"
                or execution.post_plan is None
                or execution.stage_evidence is None
                or execution.post_plan.logical_content_fingerprint
                == plan.logical_content_fingerprint
            )
        )
        or (
            execution.outcome == "failed"
            and execution.event.event_type != "action_failed"
        )
    ):
        raise DailyEodCoordinatorError("offline executor evidence is invalid")
    return _result(
        status=(
            CoordinatorStatus.TRANSITION_EXECUTED
            if execution.outcome == "succeeded"
            else CoordinatorStatus.BLOCKED
        ),
        next_action=(
            plan.next_action.value
            if execution.outcome == "succeeded"
            else NextAction.OPERATOR_DIAGNOSIS.value
        ),
        reasons=(execution.reason_code,),
        plan=plan,
        transition_fingerprint=execution.event.event_fingerprint,
        alert=execution.outcome == "failed",
    )


def _publication_plan_fingerprint(plan: DailyEodAutomationPlan) -> str:
    matches = tuple(
        observation.logical_fingerprint
        for observation in plan.observations
        if observation.stage == "publication_plan"
    )
    if len(matches) != 1 or not _is_fingerprint(matches[0]):
        raise DailyEodCoordinatorError(
            "automation plan lacks exact MI approval-plan evidence"
        )
    return str(matches[0])


def _snapshot_plan_fingerprint(plan: DailyEodAutomationPlan) -> str:
    matches = tuple(
        observation.logical_fingerprint
        for observation in plan.observations
        if observation.stage == "snapshot_plan"
    )
    if len(matches) != 1 or not _is_fingerprint(matches[0]):
        raise DailyEodCoordinatorError(
            "automation plan lacks exact Snapshot approval-plan evidence"
        )
    return str(matches[0])


def _publication_result(
    plan: DailyEodAutomationPlan,
    evidence: PublicationTransitionEvidence,
    publication_id: str,
) -> DailyEodCoordinatorResult:
    if (
        not isinstance(evidence, PublicationTransitionEvidence)
        or evidence.operation != "apply_market_intelligence"
        or evidence.target_session != plan.target_session
        or evidence.precondition_fingerprint != plan.logical_content_fingerprint
        or evidence.outcome != "succeeded"
        or evidence.publication_id != publication_id
        or not _is_fingerprint(evidence.event_fingerprint)
        or evidence.external_request_count != 0
        or evidence.production_write_count != 3
        or not evidence.reason_code
    ):
        raise DailyEodCoordinatorError(
            "MI publication capability evidence is invalid"
        )
    return _result(
        status=CoordinatorStatus.TRANSITION_EXECUTED,
        next_action="apply_market_intelligence",
        reasons=(evidence.reason_code,),
        plan=plan,
        transition_fingerprint=_fingerprint(asdict(evidence)),
        writes=evidence.production_write_count,
    )


def _snapshot_publication_result(
    plan: DailyEodAutomationPlan,
    evidence: PublicationTransitionEvidence,
    release_id: str,
    *,
    expected_write_count: int,
) -> DailyEodCoordinatorResult:
    if (
        not isinstance(evidence, PublicationTransitionEvidence)
        or evidence.operation != "apply_dashboard_snapshot"
        or evidence.target_session != plan.target_session
        or evidence.precondition_fingerprint != plan.logical_content_fingerprint
        or evidence.outcome != "succeeded"
        or evidence.publication_id != release_id
        or not _is_fingerprint(evidence.event_fingerprint)
        or evidence.external_request_count != 0
        or evidence.production_write_count != expected_write_count
        or expected_write_count < 2
        or not evidence.reason_code
    ):
        raise DailyEodCoordinatorError(
            "Snapshot publication capability evidence is invalid"
        )
    return _result(
        status=CoordinatorStatus.TRANSITION_EXECUTED,
        next_action="apply_dashboard_snapshot",
        reasons=(evidence.reason_code,),
        plan=plan,
        transition_fingerprint=_fingerprint(asdict(evidence)),
        writes=evidence.production_write_count,
    )


def _serving_bundle_observation(plan: DailyEodAutomationPlan):  # type: ignore[no-untyped-def]
    matches = tuple(
        observation
        for observation in plan.observations
        if observation.stage == "serving_bundle"
    )
    if (
        len(matches) != 1
        or not Path(matches[0].path).is_absolute()
        or not _is_fingerprint(matches[0].logical_fingerprint)
    ):
        raise DailyEodCoordinatorError(
            "automation plan lacks exact Serving Bundle evidence"
        )
    return matches[0]


def _deployment_result(
    plan: DailyEodAutomationPlan,
    evidence: DeploymentTransitionEvidence,
    release_id: str,
) -> DailyEodCoordinatorResult:
    if (
        not isinstance(evidence, DeploymentTransitionEvidence)
        or evidence.operation != "deploy_oci_dashboard"
        or evidence.target_session != plan.target_session
        or evidence.precondition_fingerprint != plan.logical_content_fingerprint
        or evidence.outcome != "succeeded"
        or evidence.release_id != release_id
        or not _is_fingerprint(evidence.event_fingerprint)
        or evidence.external_request_count != 3
        or evidence.production_write_count != 1
        or not evidence.reason_code
    ):
        raise DailyEodCoordinatorError("OCI deployment capability evidence is invalid")
    return _result(
        status=CoordinatorStatus.TRANSITION_EXECUTED,
        next_action="deploy_oci_dashboard",
        reasons=(evidence.reason_code,),
        plan=plan,
        transition_fingerprint=_fingerprint(asdict(evidence)),
        requests=evidence.external_request_count,
        writes=evidence.production_write_count,
    )


def _pending_recovery(pending: DailyEodRunEvent) -> tuple[str, str]:
    if pending.event_type == ACQUISITION_START_EVENT:
        return "recover_acquisition_attempt", "unresolved_acquisition_attempt"
    if pending.event_type == START_EVENT:
        return "recover_offline_action", "unresolved_offline_attempt"
    if pending.event_type == CANONICAL_APPLY_START_EVENT:
        return "recover_canonical_apply", "unresolved_canonical_apply"
    if pending.event_type == MARKET_INTELLIGENCE_APPLY_START_EVENT:
        return (
            "recover_market_intelligence_apply",
            "unresolved_market_intelligence_apply",
        )
    if pending.event_type == DASHBOARD_SNAPSHOT_APPLY_START_EVENT:
        return (
            "recover_dashboard_snapshot_apply",
            "unresolved_dashboard_snapshot_apply",
        )
    if pending.event_type == OCI_DEPLOYMENT_START_EVENT:
        return (
            "recover_oci_deployment",
            "unresolved_oci_deployment",
        )
    raise DailyEodCoordinatorError("unrecognized unresolved journal event")


def _recovery_result(
    plan: DailyEodAutomationPlan,
    pending: DailyEodRunEvent,
    evidence: RecoveryTransitionEvidence,
    recovery_action: str,
) -> DailyEodCoordinatorResult:
    allowed_outcomes = {
        "recover_acquisition_attempt": {
            "recovered_package_ready",
            "recovered_not_completed",
            "recovery_blocked",
        },
        "recover_canonical_apply": {
            "recovered_succeeded",
            "recovered_not_completed",
            "recovery_blocked",
        },
        "recover_offline_action": {
            "recovered_succeeded",
            "recovered_not_completed",
            "recovery_blocked",
        },
        "recover_market_intelligence_apply": {
            "recovered_succeeded",
            "recovered_not_completed",
            "recovery_blocked",
        },
        "recover_dashboard_snapshot_apply": {
            "recovered_succeeded",
            "recovered_not_completed",
            "recovery_blocked",
        },
        "recover_oci_deployment": {
            "recovered_succeeded",
            "recovered_not_completed",
            "recovery_blocked",
        },
    }
    if (
        not isinstance(evidence, RecoveryTransitionEvidence)
        or evidence.recovery_action != recovery_action
        or evidence.target_session != plan.target_session
        or evidence.pending_event_fingerprint != pending.event_fingerprint
        or recovery_action not in allowed_outcomes
        or evidence.outcome not in allowed_outcomes[recovery_action]
        or not _is_fingerprint(evidence.event_fingerprint)
        or evidence.external_request_count
        != (1 if recovery_action == "recover_oci_deployment" else 0)
        or evidence.production_write_count != 0
        or evidence.action_replayed
        or not evidence.reason_code
    ):
        raise DailyEodCoordinatorError("recovery capability evidence is invalid")
    blocked = evidence.outcome == "recovery_blocked"
    return _result(
        status=(
            CoordinatorStatus.BLOCKED
            if blocked
            else CoordinatorStatus.TRANSITION_EXECUTED
        ),
        next_action=(
            NextAction.OPERATOR_DIAGNOSIS.value if blocked else recovery_action
        ),
        reasons=(evidence.reason_code,),
        plan=plan,
        transition_fingerprint=_fingerprint(asdict(evidence)),
        requests=evidence.external_request_count,
        alert=blocked,
    )


def _execution_config(config: DailyEodCoordinatorConfig) -> DailyEodExecutionConfig:
    return DailyEodExecutionConfig(
        target_session=config.target_session,
        paths=config.paths,
        run_root=config.run_root,
        panel_cache_root=config.panel_cache_root,
        candidate_work_dir=config.candidate_work_dir,
        publication_created_at=config.publication_created_at,
        publication_expected_current_state_fingerprint=(
            config.publication_expected_current_state_fingerprint
        ),
        snapshot_generated_at=config.snapshot_generated_at,
        bundle_built_at=config.bundle_built_at,
    )


def _result(
    *,
    status: CoordinatorStatus,
    next_action: str,
    reasons: tuple[str, ...],
    plan: DailyEodAutomationPlan,
    readiness: DailyEodReadinessPlan | None = None,
    transition_fingerprint: str | None = None,
    requests: int = 0,
    writes: int = 0,
    alert: bool = False,
) -> DailyEodCoordinatorResult:
    base = {
        "status": status,
        "target_session": plan.target_session,
        "next_action": next_action,
        "reason_codes": reasons,
        "automation_plan_fingerprint": plan.logical_content_fingerprint,
        "readiness_plan_fingerprint": (
            None if readiness is None else readiness.logical_content_fingerprint
        ),
        "transition_fingerprint": transition_fingerprint,
        "external_request_count": requests,
        "production_write_count": writes,
        "next_check_at": None if readiness is None else readiness.next_check_at,
        "alert_required": alert,
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_enabled": False,
        "contract_version": CONTRACT_VERSION,
    }
    result = DailyEodCoordinatorResult(
        **base,
        logical_content_fingerprint=_fingerprint(base),
    )
    verify_daily_eod_coordinator_result(result)
    return result


def daily_eod_coordinator_result_fingerprint(
    result: DailyEodCoordinatorResult,
) -> str:
    """Recompute the canonical logical identity of one coordinator result."""

    logical = asdict(result)
    logical.pop("logical_content_fingerprint")
    return _fingerprint(logical)


def verify_daily_eod_coordinator_result(
    result: DailyEodCoordinatorResult,
) -> None:
    """Reject a malformed or field-tampered coordinator result."""

    if (
        not isinstance(result, DailyEodCoordinatorResult)
        or result.contract_version != CONTRACT_VERSION
        or result.logical_content_fingerprint
        != daily_eod_coordinator_result_fingerprint(result)
    ):
        raise DailyEodCoordinatorError(
            "coordinator result content fingerprint mismatch"
        )


def _validate_config(config: DailyEodCoordinatorConfig) -> None:
    if (
        not config.run_root.is_absolute()
        or _is_within(config.run_root, Path("/data"))
        or _is_within(config.run_root, config.paths.data_root)
    ):
        raise DailyEodCoordinatorError("coordinator run root is invalid")
    for path in (config.package_path, config.approval_plan_path):
        if (
            not path.is_absolute()
            or path.parent != Path("/tmp")
            or path.name.startswith(".")
        ):
            raise DailyEodCoordinatorError("coordinator custody path is invalid")
    if config.package_path == config.approval_plan_path:
        raise DailyEodCoordinatorError("coordinator package and plan paths must differ")
    publication_values = (
        config.publication_created_at,
        config.publication_expected_current_state_fingerprint,
    )
    if any(value is not None for value in publication_values):
        if (
            config.publication_created_at is None
            or config.publication_created_at.tzinfo is None
            or config.publication_created_at.utcoffset() is None
            or config.publication_created_at.utcoffset().total_seconds() != 0
            or not _is_fingerprint(
                config.publication_expected_current_state_fingerprint
            )
        ):
            raise DailyEodCoordinatorError(
                "publication planning inputs must be complete UTC/fingerprint bindings"
            )
    if config.snapshot_generated_at is not None and (
        config.snapshot_generated_at.tzinfo is None
        or config.snapshot_generated_at.utcoffset() is None
        or config.snapshot_generated_at.utcoffset().total_seconds() != 0
    ):
        raise DailyEodCoordinatorError(
            "Snapshot planning timestamp must be explicit UTC"
        )
    if config.bundle_built_at is not None and (
        config.bundle_built_at.tzinfo is None
        or config.bundle_built_at.utcoffset() is None
        or config.bundle_built_at.utcoffset().total_seconds() != 0
    ):
        raise DailyEodCoordinatorError(
            "serving bundle timestamp must be explicit UTC"
        )


def _validate_plan(
    plan: DailyEodAutomationPlan,
    config: DailyEodCoordinatorConfig,
) -> None:
    if (
        not isinstance(plan, DailyEodAutomationPlan)
        or plan.target_session != config.target_session.isoformat()
        or not _is_fingerprint(plan.logical_content_fingerprint)
        or plan.publication_authorized
        or plan.deployment_authorized
        or plan.scheduler_enabled
        or plan.external_request_count != 0
        or plan.production_write_count != 0
    ):
        raise DailyEodCoordinatorError("automation plan differs from coordinator boundary")
    if (
        plan.next_action
        in {
            *OFFLINE_ACTIONS,
            NextAction.REVIEW_PUBLICATION,
            NextAction.REVIEW_SNAPSHOT_PUBLICATION,
            NextAction.REVIEW_BUNDLE_DEPLOYMENT,
        }
        and config.latest_canonical_session != config.target_session
    ):
        raise DailyEodCoordinatorError("canonical session is stale for downstream work")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodCoordinatorError("coordinator time must be timezone-aware")
    return value.astimezone(UTC)


def _fingerprint(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=lambda item: item.value if isinstance(item, StrEnum) else str(item),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.absolute().relative_to(root.absolute())
        return True
    except ValueError:
        return False
