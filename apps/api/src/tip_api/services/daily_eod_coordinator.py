"""Coordinate at most one exact daily EOD state transition."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Callable

from tip_api.services.daily_eod_acquisition_custody import (
    DailyEodAcquisitionConfig,
    acquisition_attempts_from_events,
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
    START_EVENT,
    DailyEodRunEvent,
    locked_daily_eod_run_journal,
    unresolved_started_event,
)


CONTRACT_VERSION = "daily-eod-one-transition-coordinator/1.0"


class DailyEodCoordinatorError(RuntimeError):
    """Raised when one exact daily transition cannot be coordinated safely."""


class CoordinatorStatus(StrEnum):
    WAITING = "waiting"
    MANUAL_AUTHORIZATION_REQUIRED = "manual_authorization_required"
    RECOVERY_REQUIRED = "recovery_required"
    READY_FOR_OFFLINE_EXECUTION = "ready_for_offline_execution"
    TRANSITION_EXECUTED = "transition_executed"
    PUBLICATION_REVIEW_READY = "publication_review_ready"
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
class DailyEodCoordinatorResult:
    status: CoordinatorStatus
    next_action: str
    reason_codes: tuple[str, ...]
    automation_plan_fingerprint: str
    readiness_plan_fingerprint: str | None
    transition_fingerprint: str | None
    external_request_count: int
    production_write_count: int
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
OfflineExecutor = Callable[..., DailyEodExecutionResult]


def coordinate_daily_eod_transition(
    *,
    config: DailyEodCoordinatorConfig,
    checked_at: datetime,
    execute_offline: bool = False,
    fetch_capability: AuthorizedCapability | None = None,
    apply_capability: AuthorizedCapability | None = None,
    planner: Planner = plan_daily_eod_automation,
    journal_reader: JournalReader | None = None,
    offline_executor: OfflineExecutor = execute_daily_eod_action,
) -> DailyEodCoordinatorResult:
    """Return or execute at most one exact transition; never loop or retry."""

    checked = _aware_utc(checked_at)
    _validate_config(config)
    plan = planner(target_session=config.target_session, paths=config.paths)
    _validate_plan(plan, config)
    events = (journal_reader or _read_journal_events)(
        config.run_root, config.target_session
    )
    pending = unresolved_started_event(events)
    if pending is not None:
        if pending.event_type == ACQUISITION_START_EVENT:
            return _result(
                status=CoordinatorStatus.RECOVERY_REQUIRED,
                next_action="recover_acquisition_attempt",
                reasons=("unresolved_acquisition_attempt",),
                plan=plan,
            )
        if pending.event_type == START_EVENT:
            return _result(
                status=CoordinatorStatus.RECOVERY_REQUIRED,
                next_action="recover_offline_action",
                reasons=("unresolved_offline_attempt",),
                plan=plan,
            )
        raise DailyEodCoordinatorError("unrecognized unresolved journal event")

    if plan.status is PlanStatus.BLOCKED or plan.next_action is NextAction.OPERATOR_DIAGNOSIS:
        return _result(
            status=CoordinatorStatus.BLOCKED,
            next_action=NextAction.OPERATOR_DIAGNOSIS.value,
            reasons=plan.reason_codes,
            plan=plan,
        )
    if plan.status is PlanStatus.ANALYTICS_READY:
        if plan.next_action is not NextAction.REVIEW_PUBLICATION:
            raise DailyEodCoordinatorError("analytics-ready plan has an invalid action")
        return _result(
            status=CoordinatorStatus.PUBLICATION_REVIEW_READY,
            next_action=NextAction.REVIEW_PUBLICATION.value,
            reasons=plan.reason_codes,
            plan=plan,
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
    expected_requests = 0 if apply else 1
    expected_writes = 1 if apply else 0
    if (
        not isinstance(evidence, AuthorizedTransitionEvidence)
        or evidence.operation != operation
        or evidence.target_session != plan.target_session
        or evidence.precondition_fingerprint
        != readiness.logical_content_fingerprint
        or evidence.outcome not in {"succeeded", "waiting", "failed"}
        or not _is_fingerprint(evidence.event_fingerprint)
        or not 0 <= evidence.external_request_count <= expected_requests
        or not 0 <= evidence.production_write_count <= expected_writes
        or (
            evidence.outcome == "succeeded"
            and (
                evidence.external_request_count != expected_requests
                or evidence.production_write_count != expected_writes
            )
        )
        or not evidence.reason_code
    ):
        raise DailyEodCoordinatorError("authorized capability evidence is invalid")
    return _result(
        status=CoordinatorStatus.TRANSITION_EXECUTED,
        next_action=operation,
        reasons=(evidence.reason_code,),
        plan=plan,
        readiness=readiness,
        transition_fingerprint=_fingerprint(asdict(evidence)),
        requests=evidence.external_request_count,
        writes=evidence.production_write_count,
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
    ):
        raise DailyEodCoordinatorError("offline executor evidence is invalid")
    return _result(
        status=CoordinatorStatus.TRANSITION_EXECUTED,
        next_action=plan.next_action.value,
        reasons=(execution.reason_code,),
        plan=plan,
        transition_fingerprint=execution.event.event_fingerprint,
    )


def _execution_config(config: DailyEodCoordinatorConfig) -> DailyEodExecutionConfig:
    return DailyEodExecutionConfig(
        target_session=config.target_session,
        paths=config.paths,
        run_root=config.run_root,
        panel_cache_root=config.panel_cache_root,
        candidate_work_dir=config.candidate_work_dir,
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
) -> DailyEodCoordinatorResult:
    base = {
        "status": status,
        "next_action": next_action,
        "reason_codes": reasons,
        "automation_plan_fingerprint": plan.logical_content_fingerprint,
        "readiness_plan_fingerprint": (
            None if readiness is None else readiness.logical_content_fingerprint
        ),
        "transition_fingerprint": transition_fingerprint,
        "external_request_count": requests,
        "production_write_count": writes,
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_enabled": False,
        "contract_version": CONTRACT_VERSION,
    }
    return DailyEodCoordinatorResult(
        **base,
        logical_content_fingerprint=_fingerprint(base),
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
        plan.next_action in {*OFFLINE_ACTIONS, NextAction.REVIEW_PUBLICATION}
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
