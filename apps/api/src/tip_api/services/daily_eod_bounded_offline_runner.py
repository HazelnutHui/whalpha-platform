"""Finite continuous execution of already-governed daily offline actions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import Callable

from tip_api.services.daily_eod_automation import (
    CONTRACT_VERSION as AUTOMATION_CONTRACT_VERSION,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_executor import (
    OFFLINE_ACTIONS,
    DailyEodExecutionConfig,
    DailyEodExecutionResult,
    StageExecutionEvidence,
    execute_daily_eod_action,
)
from tip_api.services.daily_eod_run_journal import (
    DailyEodRunJournalError,
    verify_daily_eod_run_event,
)


CONTRACT_VERSION = "daily-eod-bounded-offline-run/1.0"
DEFAULT_MAXIMUM_ACTIONS = len(OFFLINE_ACTIONS)
MAXIMUM_ACTIONS = len(OFFLINE_ACTIONS)
DEFAULT_MAXIMUM_ELAPSED_SECONDS = 2 * 60 * 60
MAXIMUM_ELAPSED_SECONDS = 4 * 60 * 60


class DailyEodBoundedOfflineRunnerError(RuntimeError):
    """Raised when a bounded offline run cannot remain exact and fail closed."""


class BoundedOfflineRunStatus(StrEnum):
    REVIEW_READY = "review_ready"
    BOUNDARY_REACHED = "boundary_reached"
    BLOCKED = "blocked"
    ACTION_FAILED = "action_failed"
    BUDGET_EXHAUSTED = "budget_exhausted"


@dataclass(frozen=True, slots=True)
class BoundedOfflineActionEvidence:
    sequence: int
    action: str
    started_at: str
    completed_at: str
    outcome: str
    pre_plan_fingerprint: str
    post_plan_fingerprint: str | None
    event_fingerprint: str
    reason_code: str


@dataclass(frozen=True, slots=True)
class DailyEodBoundedOfflineRunResult:
    contract_version: str
    status: BoundedOfflineRunStatus
    target_session: str
    started_at: str
    completed_at: str
    maximum_actions: int
    maximum_elapsed_seconds: int
    action_attempt_count: int
    action_success_count: int
    action_evidence: tuple[BoundedOfflineActionEvidence, ...]
    final_plan_status: str
    final_next_action: str
    final_plan_fingerprint: str
    reason_codes: tuple[str, ...]
    execution_enabled: bool
    automatic_retry_enabled: bool
    automatic_recovery_enabled: bool
    external_request_count: int
    production_write_count: int
    publication_authorized: bool
    deployment_authorized: bool
    scheduler_installation_performed: bool
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))  # type: ignore[return-value]


Planner = Callable[..., DailyEodAutomationPlan]
Executor = Callable[..., DailyEodExecutionResult]
Clock = Callable[[], datetime]


def run_bounded_daily_eod_offline(
    *,
    config: DailyEodExecutionConfig,
    started_at: datetime,
    execute: bool = False,
    maximum_actions: int = DEFAULT_MAXIMUM_ACTIONS,
    maximum_elapsed_seconds: int = DEFAULT_MAXIMUM_ELAPSED_SECONDS,
    planner: Planner = plan_daily_eod_automation,
    executor: Executor = execute_daily_eod_action,
    clock: Clock = lambda: datetime.now(UTC),
) -> DailyEodBoundedOfflineRunResult:
    """Run successful offline actions consecutively, stopping at every boundary."""

    started = _aware_utc(started_at)
    _validate_inputs(
        config=config,
        maximum_actions=maximum_actions,
        maximum_elapsed_seconds=maximum_elapsed_seconds,
    )
    deadline = started + timedelta(seconds=maximum_elapsed_seconds)
    evidence: list[BoundedOfflineActionEvidence] = []
    seen_plans: set[str] = set()

    for _ in range(maximum_actions + 1):
        plan = planner(target_session=config.target_session, paths=config.paths)
        _verify_plan(plan, target_session=config.target_session)
        if (
            evidence
            and plan.logical_content_fingerprint
            != evidence[-1].post_plan_fingerprint
        ):
            raise DailyEodBoundedOfflineRunnerError(
                "fresh offline plan does not reproduce the completed post-plan; "
                "automatic continuation is prohibited"
            )
        checked = _monotonic_clock(clock, not_before=started)
        terminal = _terminal_status(
            plan=plan,
            execute=execute,
            action_count=len(evidence),
            checked_at=checked,
            deadline=deadline,
            maximum_actions=maximum_actions,
            publication_state_fingerprint=(
                config.publication_expected_current_state_fingerprint
            ),
        )
        if terminal is not None:
            status, reasons = terminal
            return _result(
                status=status,
                config=config,
                started_at=started,
                completed_at=checked,
                maximum_actions=maximum_actions,
                maximum_elapsed_seconds=maximum_elapsed_seconds,
                evidence=tuple(evidence),
                final_plan=plan,
                reasons=reasons,
                execute=execute,
            )
        if plan.logical_content_fingerprint in seen_plans:
            raise DailyEodBoundedOfflineRunnerError(
                "a successful bounded run cannot reuse an earlier plan"
            )
        seen_plans.add(plan.logical_content_fingerprint)

        action_config = _config_for_action(
            config,
            action=plan.next_action,
            action_started_at=checked,
        )
        try:
            action_result = executor(
                config=action_config,
                expected_plan_fingerprint=plan.logical_content_fingerprint,
                expected_action=plan.next_action,
                planner=planner,
            )
        except Exception as exc:
            raise DailyEodBoundedOfflineRunnerError(
                "offline action outcome is not available to the bounded runner; "
                "automatic continuation is prohibited"
            ) from exc
        completed = _monotonic_clock(clock, not_before=checked)
        action_evidence = _action_evidence(
            sequence=len(evidence) + 1,
            started_at=checked,
            completed_at=completed,
            planned=plan,
            result=action_result,
        )
        evidence.append(action_evidence)
        if action_result.outcome != "succeeded":
            final_plan = action_result.post_plan or plan
            return _result(
                status=BoundedOfflineRunStatus.ACTION_FAILED,
                config=config,
                started_at=started,
                completed_at=completed,
                maximum_actions=maximum_actions,
                maximum_elapsed_seconds=maximum_elapsed_seconds,
                evidence=tuple(evidence),
                final_plan=final_plan,
                reasons=(
                    "offline_action_failed",
                    "automatic_retry_prohibited",
                    action_result.reason_code,
                ),
                execute=execute,
            )

    raise DailyEodBoundedOfflineRunnerError(
        "bounded offline runner exceeded its finite action limit"
    )


def verify_daily_eod_bounded_offline_run_result(
    result: DailyEodBoundedOfflineRunResult,
) -> None:
    if not isinstance(result, DailyEodBoundedOfflineRunResult):
        raise DailyEodBoundedOfflineRunnerError(
            "bounded offline result contract is invalid"
        )
    logical = asdict(result)
    logical.pop("logical_content_fingerprint")
    try:
        date.fromisoformat(result.target_session)
        PlanStatus(result.final_plan_status)
        NextAction(result.final_next_action)
        _parse_utc(result.started_at)
        completed = _parse_utc(result.completed_at)
    except ValueError as exc:
        raise DailyEodBoundedOfflineRunnerError(
            "bounded offline result identity is malformed"
        ) from exc
    if (
        result.contract_version != CONTRACT_VERSION
        or result.logical_content_fingerprint != _fingerprint(_jsonable(logical))
        or not isinstance(result.status, BoundedOfflineRunStatus)
        or not 1 <= result.maximum_actions <= MAXIMUM_ACTIONS
        or not 1
        <= result.maximum_elapsed_seconds
        <= MAXIMUM_ELAPSED_SECONDS
        or result.action_attempt_count != len(result.action_evidence)
        or result.action_attempt_count > result.maximum_actions
        or result.action_success_count
        != sum(item.outcome == "succeeded" for item in result.action_evidence)
        or result.action_success_count > result.action_attempt_count
        or completed < _parse_utc(result.started_at)
        or not _is_fingerprint(result.final_plan_fingerprint)
        or not result.reason_codes
        or result.automatic_retry_enabled
        or result.automatic_recovery_enabled
        or result.external_request_count != 0
        or result.production_write_count != 0
        or result.publication_authorized
        or result.deployment_authorized
        or result.scheduler_installation_performed
        or (
            not result.execution_enabled
            and result.action_attempt_count != 0
        )
    ):
        raise DailyEodBoundedOfflineRunnerError(
            "bounded offline result content or authority differs"
        )
    run_started = _parse_utc(result.started_at)
    previous_completed = run_started
    previous_post_plan: str | None = None
    seen_pre_plans: set[str] = set()
    for sequence, item in enumerate(result.action_evidence, start=1):
        try:
            action = NextAction(item.action)
            item_started = _parse_utc(item.started_at)
            item_completed = _parse_utc(item.completed_at)
        except ValueError as exc:
            raise DailyEodBoundedOfflineRunnerError(
                "bounded offline action evidence is malformed"
            ) from exc
        if (
            item.sequence != sequence
            or action not in OFFLINE_ACTIONS
            or item.outcome not in {"succeeded", "failed"}
            or item_completed < item_started
            or item_started < previous_completed
            or item_completed > completed
            or item_started
            >= run_started + timedelta(seconds=result.maximum_elapsed_seconds)
            or not _is_fingerprint(item.pre_plan_fingerprint)
            or item.pre_plan_fingerprint in seen_pre_plans
            or (
                previous_post_plan is not None
                and item.pre_plan_fingerprint != previous_post_plan
            )
            or (
                item.post_plan_fingerprint is not None
                and not _is_fingerprint(item.post_plan_fingerprint)
            )
            or (
                item.outcome == "succeeded"
                and item.post_plan_fingerprint is None
            )
            or not _is_fingerprint(item.event_fingerprint)
            or not item.reason_code
        ):
            raise DailyEodBoundedOfflineRunnerError(
                "bounded offline action evidence fields conflict"
            )
        seen_pre_plans.add(item.pre_plan_fingerprint)
        previous_post_plan = item.post_plan_fingerprint
        previous_completed = item_completed
    _verify_result_semantics(result, completed=completed)


def _verify_result_semantics(
    result: DailyEodBoundedOfflineRunResult,
    *,
    completed: datetime,
) -> None:
    final_status = PlanStatus(result.final_plan_status)
    final_action = NextAction(result.final_next_action)
    evidence = result.action_evidence
    if evidence:
        final_evidence = evidence[-1]
        expected_final = (
            final_evidence.post_plan_fingerprint
            or final_evidence.pre_plan_fingerprint
        )
        if result.final_plan_fingerprint != expected_final:
            raise DailyEodBoundedOfflineRunnerError(
                "bounded offline final plan is not chained to action evidence"
            )
    status_valid = {
        BoundedOfflineRunStatus.REVIEW_READY: (
            not result.execution_enabled
            and not evidence
            and final_status is PlanStatus.READY_FOR_OFFLINE_CALCULATION
            and final_action in OFFLINE_ACTIONS
        ),
        BoundedOfflineRunStatus.BOUNDARY_REACHED: (
            final_status in {
                PlanStatus.WAITING_FOR_AUTHORIZED_INPUT,
                PlanStatus.ANALYTICS_READY,
            }
            or (
                final_action is NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN
                and result.reason_codes
                == ("publication_current_state_fingerprint_required",)
            )
        ),
        BoundedOfflineRunStatus.BLOCKED: final_status is PlanStatus.BLOCKED,
        BoundedOfflineRunStatus.ACTION_FAILED: (
            bool(evidence) and evidence[-1].outcome == "failed"
        ),
        BoundedOfflineRunStatus.BUDGET_EXHAUSTED: (
            result.action_attempt_count >= result.maximum_actions
            or completed
            >= _parse_utc(result.started_at)
            + timedelta(seconds=result.maximum_elapsed_seconds)
        ),
    }[result.status]
    if not status_valid:
        raise DailyEodBoundedOfflineRunnerError(
            "bounded offline result status conflicts with final state"
        )


def _terminal_status(
    *,
    plan: DailyEodAutomationPlan,
    execute: bool,
    action_count: int,
    checked_at: datetime,
    deadline: datetime,
    maximum_actions: int,
    publication_state_fingerprint: str | None,
) -> tuple[BoundedOfflineRunStatus, tuple[str, ...]] | None:
    if plan.status is PlanStatus.BLOCKED:
        return BoundedOfflineRunStatus.BLOCKED, plan.reason_codes
    if plan.status is not PlanStatus.READY_FOR_OFFLINE_CALCULATION:
        return (
            BoundedOfflineRunStatus.BOUNDARY_REACHED,
            ("non_offline_boundary_reached", *plan.reason_codes),
        )
    if plan.next_action not in OFFLINE_ACTIONS:
        raise DailyEodBoundedOfflineRunnerError(
            "offline-ready plan selected a non-offline action"
        )
    if not execute:
        return (
            BoundedOfflineRunStatus.REVIEW_READY,
            ("explicit_offline_execution_not_enabled",),
        )
    if (
        plan.next_action is NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN
        and publication_state_fingerprint is None
    ):
        return (
            BoundedOfflineRunStatus.BOUNDARY_REACHED,
            ("publication_current_state_fingerprint_required",),
        )
    if action_count >= maximum_actions or checked_at >= deadline:
        return (
            BoundedOfflineRunStatus.BUDGET_EXHAUSTED,
            ("bounded_offline_budget_exhausted",),
        )
    return None


def _action_evidence(
    *,
    sequence: int,
    started_at: datetime,
    completed_at: datetime,
    planned: DailyEodAutomationPlan,
    result: DailyEodExecutionResult,
) -> BoundedOfflineActionEvidence:
    try:
        verify_daily_eod_run_event(result.event)
    except (AttributeError, DailyEodRunJournalError) as exc:
        raise DailyEodBoundedOfflineRunnerError(
            "offline executor event is not formal journal evidence"
        ) from exc
    if (
        not isinstance(result, DailyEodExecutionResult)
        or result.action is not planned.next_action
        or result.pre_plan.logical_content_fingerprint
        != planned.logical_content_fingerprint
        or result.pre_plan.target_session != planned.target_session
        or result.event.target_session != planned.target_session
        or result.event.attempt_id != result.attempt_id
        or not _is_fingerprint(result.event.event_fingerprint)
        or result.outcome not in {"succeeded", "failed"}
        or (
            result.outcome == "succeeded"
            and result.event.event_type != "action_succeeded"
        )
        or (
            result.outcome == "failed"
            and result.event.event_type != "action_failed"
        )
        or (
            result.outcome == "succeeded"
            and (
                result.post_plan is None
                or not isinstance(result.stage_evidence, StageExecutionEvidence)
                or result.stage_evidence.action is not planned.next_action
                or result.post_plan.target_session != planned.target_session
                or result.post_plan.logical_content_fingerprint
                == planned.logical_content_fingerprint
                or result.post_plan.next_action is planned.next_action
            )
        )
    ):
        raise DailyEodBoundedOfflineRunnerError(
            "offline executor result differs from the bounded plan"
        )
    if result.post_plan is not None:
        _verify_plan(
            result.post_plan,
            target_session=date.fromisoformat(planned.target_session),
        )
    return BoundedOfflineActionEvidence(
        sequence=sequence,
        action=planned.next_action.value,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        outcome=result.outcome,
        pre_plan_fingerprint=planned.logical_content_fingerprint,
        post_plan_fingerprint=(
            None
            if result.post_plan is None
            else result.post_plan.logical_content_fingerprint
        ),
        event_fingerprint=result.event.event_fingerprint,
        reason_code=result.reason_code,
    )


def _config_for_action(
    config: DailyEodExecutionConfig,
    *,
    action: NextAction,
    action_started_at: datetime,
) -> DailyEodExecutionConfig:
    return replace(
        config,
        publication_created_at=(
            action_started_at
            if action is NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN
            else None
        ),
        publication_expected_current_state_fingerprint=(
            config.publication_expected_current_state_fingerprint
            if action is NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN
            else None
        ),
        snapshot_generated_at=(
            action_started_at
            if action is NextAction.PREPARE_DASHBOARD_SNAPSHOT_PLAN
            else None
        ),
        bundle_built_at=(
            action_started_at
            if action is NextAction.BUILD_SERVING_BUNDLE
            else None
        ),
    )


def _validate_inputs(
    *,
    config: DailyEodExecutionConfig,
    maximum_actions: int,
    maximum_elapsed_seconds: int,
) -> None:
    if (
        not isinstance(config, DailyEodExecutionConfig)
        or type(maximum_actions) is not int
        or not 1 <= maximum_actions <= MAXIMUM_ACTIONS
        or type(maximum_elapsed_seconds) is not int
        or not 1
        <= maximum_elapsed_seconds
        <= MAXIMUM_ELAPSED_SECONDS
        or config.publication_created_at is not None
        or config.snapshot_generated_at is not None
        or config.bundle_built_at is not None
        or (
            config.publication_expected_current_state_fingerprint is not None
            and not _is_fingerprint(
                config.publication_expected_current_state_fingerprint
            )
        )
    ):
        raise DailyEodBoundedOfflineRunnerError(
            "bounded offline inputs or budget are invalid"
        )


def _verify_plan(plan: DailyEodAutomationPlan, *, target_session: date) -> None:
    if not isinstance(plan, DailyEodAutomationPlan):
        raise DailyEodBoundedOfflineRunnerError(
            "bounded offline planner result is invalid"
        )
    logical = asdict(plan)
    logical.pop("logical_content_fingerprint")
    try:
        date.fromisoformat(plan.target_session)
        date.fromisoformat(plan.prior_session)
    except ValueError as exc:
        raise DailyEodBoundedOfflineRunnerError(
            "bounded offline plan session is malformed"
        ) from exc
    if (
        plan.contract_version != AUTOMATION_CONTRACT_VERSION
        or plan.target_session != target_session.isoformat()
        or plan.logical_content_fingerprint != _fingerprint(_jsonable(logical))
        or not isinstance(plan.status, PlanStatus)
        or not isinstance(plan.next_action, NextAction)
        or plan.publication_authorized
        or plan.deployment_authorized
        or plan.scheduler_enabled
        or plan.external_request_count != 0
        or plan.production_write_count != 0
    ):
        raise DailyEodBoundedOfflineRunnerError(
            "bounded offline plan content or authority differs"
        )


def _result(
    *,
    status: BoundedOfflineRunStatus,
    config: DailyEodExecutionConfig,
    started_at: datetime,
    completed_at: datetime,
    maximum_actions: int,
    maximum_elapsed_seconds: int,
    evidence: tuple[BoundedOfflineActionEvidence, ...],
    final_plan: DailyEodAutomationPlan,
    reasons: tuple[str, ...],
    execute: bool,
) -> DailyEodBoundedOfflineRunResult:
    logical = {
        "contract_version": CONTRACT_VERSION,
        "status": status.value,
        "target_session": config.target_session.isoformat(),
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "maximum_actions": maximum_actions,
        "maximum_elapsed_seconds": maximum_elapsed_seconds,
        "action_attempt_count": len(evidence),
        "action_success_count": sum(
            item.outcome == "succeeded" for item in evidence
        ),
        "action_evidence": [_jsonable(asdict(item)) for item in evidence],
        "final_plan_status": final_plan.status.value,
        "final_next_action": final_plan.next_action.value,
        "final_plan_fingerprint": final_plan.logical_content_fingerprint,
        "reason_codes": list(reasons),
        "execution_enabled": execute,
        "automatic_retry_enabled": False,
        "automatic_recovery_enabled": False,
        "external_request_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_installation_performed": False,
    }
    result = DailyEodBoundedOfflineRunResult(
        contract_version=CONTRACT_VERSION,
        status=status,
        target_session=config.target_session.isoformat(),
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        maximum_actions=maximum_actions,
        maximum_elapsed_seconds=maximum_elapsed_seconds,
        action_attempt_count=len(evidence),
        action_success_count=sum(item.outcome == "succeeded" for item in evidence),
        action_evidence=evidence,
        final_plan_status=final_plan.status.value,
        final_next_action=final_plan.next_action.value,
        final_plan_fingerprint=final_plan.logical_content_fingerprint,
        reason_codes=reasons,
        execution_enabled=execute,
        automatic_retry_enabled=False,
        automatic_recovery_enabled=False,
        external_request_count=0,
        production_write_count=0,
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_installation_performed=False,
        logical_content_fingerprint=_fingerprint(logical),
    )
    verify_daily_eod_bounded_offline_run_result(result)
    return result


def _monotonic_clock(clock: Clock, *, not_before: datetime) -> datetime:
    observed = _aware_utc(clock())
    if observed < not_before:
        raise DailyEodBoundedOfflineRunnerError(
            "bounded offline clock moved backwards"
        )
    return observed


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodBoundedOfflineRunnerError(
            "bounded offline time must be timezone aware"
        )
    return value.astimezone(UTC)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp is not timezone aware")
    return parsed.astimezone(UTC)


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _jsonable(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
