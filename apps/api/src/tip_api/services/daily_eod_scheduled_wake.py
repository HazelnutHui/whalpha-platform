"""Default-off bridge from one scheduler plan to one coordinator invocation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Callable

from tip_api.services.daily_eod_coordinator import (
    DailyEodCoordinatorError,
    DailyEodCoordinatorResult,
    verify_daily_eod_coordinator_result,
)
from tip_api.services.daily_eod_scheduler import (
    DailyEodSchedulerError,
    DailyEodSchedulerWakePlan,
    SchedulerWakeAction,
    verify_daily_eod_scheduler_wake_plan,
)


CONTRACT_VERSION = "daily-eod-scheduled-wake/1.0"


class DailyEodScheduledWakeError(RuntimeError):
    """Raised when a scheduled wake cannot remain bounded and fail closed."""


class ScheduledWakeStatus(StrEnum):
    WAITING = "waiting"
    REVIEW_READY = "review_ready"
    COORDINATOR_INVOKED = "coordinator_invoked"


@dataclass(frozen=True, slots=True)
class DailyEodScheduledWakeResult:
    contract_version: str
    status: ScheduledWakeStatus
    target_session: str
    wake_plan_fingerprint: str
    coordinator_result_fingerprint: str | None
    coordinator_status: str | None
    coordinator_next_action: str | None
    coordinator_invocation_count: int
    external_request_count: int
    production_write_count: int
    alert_required: bool
    alert_delivery_attempted: bool
    recovery_attempted: bool
    automatic_retry_enabled: bool
    automatic_recovery_enabled: bool
    publication_authorized: bool
    deployment_authorized: bool
    scheduler_installed: bool
    transition_outcome_formally_known: bool
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


CoordinatorInvocation = Callable[[], DailyEodCoordinatorResult]


def run_one_scheduled_wake(
    *,
    plan: DailyEodSchedulerWakePlan,
    expected_plan_fingerprint: str,
    invoke_one_transition: bool = False,
    coordinator: CoordinatorInvocation | None = None,
) -> DailyEodScheduledWakeResult:
    """Optionally invoke one coordinator callable; never retry or recover."""

    _validate_plan(plan, expected_plan_fingerprint)
    if not invoke_one_transition:
        status = (
            ScheduledWakeStatus.WAITING
            if plan.next_action is SchedulerWakeAction.WAIT
            else ScheduledWakeStatus.REVIEW_READY
        )
        return _result(status=status, plan=plan)
    if (
        not plan.scheduler_candidate_enabled
        or plan.next_action is not SchedulerWakeAction.INVOKE_ONE_TRANSITION
    ):
        raise DailyEodScheduledWakeError(
            "one transition requires an exact enabled ready-wake candidate"
        )
    if coordinator is None:
        raise DailyEodScheduledWakeError("one transition coordinator is absent")
    try:
        coordinator_result = coordinator()
    except Exception as exc:
        raise DailyEodScheduledWakeError(
            "coordinator outcome is unknown; automatic replay is prohibited"
        ) from exc
    _validate_coordinator_result(plan, coordinator_result)
    return _result(
        status=ScheduledWakeStatus.COORDINATOR_INVOKED,
        plan=plan,
        coordinator_result=coordinator_result,
    )


def _validate_plan(
    plan: DailyEodSchedulerWakePlan,
    expected_plan_fingerprint: str,
) -> None:
    try:
        verify_daily_eod_scheduler_wake_plan(plan)
    except DailyEodSchedulerError as exc:
        raise DailyEodScheduledWakeError(
            "scheduler wake plan content is invalid"
        ) from exc
    if (
        len(expected_plan_fingerprint) != 64
        or any(
            character not in "0123456789abcdef"
            for character in expected_plan_fingerprint
        )
        or plan.logical_content_fingerprint != expected_plan_fingerprint
    ):
        raise DailyEodScheduledWakeError("scheduler wake plan fingerprint mismatch")
    if (
        plan.scheduler_installed
        or plan.coordinator_invocation_limit != 1
        or plan.coordinator_invocation_count != 0
        or plan.automatic_retry_enabled
        or plan.automatic_recovery_enabled
        or plan.publication_authorized
        or plan.deployment_authorized
        or plan.credential_access_count != 0
        or plan.external_request_count != 0
        or plan.filesystem_write_count != 0
        or plan.production_write_count != 0
    ):
        raise DailyEodScheduledWakeError("scheduler wake plan exceeds review authority")


def _validate_coordinator_result(
    plan: DailyEodSchedulerWakePlan,
    result: DailyEodCoordinatorResult,
) -> None:
    if not isinstance(result, DailyEodCoordinatorResult):
        raise DailyEodScheduledWakeError("coordinator result contract is invalid")
    try:
        verify_daily_eod_coordinator_result(result)
    except DailyEodCoordinatorError as exc:
        raise DailyEodScheduledWakeError(
            "coordinator result content is invalid"
        ) from exc
    if result.target_session != plan.target_session:
        raise DailyEodScheduledWakeError("coordinator target differs from wake plan")
    if (
        result.scheduler_enabled
        or result.publication_authorized
        or result.deployment_authorized
        or result.external_request_count < 0
        or result.production_write_count < 0
    ):
        raise DailyEodScheduledWakeError("coordinator result exceeds scheduled authority")


def _result(
    *,
    status: ScheduledWakeStatus,
    plan: DailyEodSchedulerWakePlan,
    coordinator_result: DailyEodCoordinatorResult | None = None,
) -> DailyEodScheduledWakeResult:
    coordinator_status = (
        None if coordinator_result is None else coordinator_result.status.value
    )
    coordinator_result_fingerprint = (
        None
        if coordinator_result is None
        else coordinator_result.logical_content_fingerprint
    )
    coordinator_next_action = (
        None if coordinator_result is None else coordinator_result.next_action
    )
    invocation_count = 0 if coordinator_result is None else 1
    request_count = (
        0 if coordinator_result is None else coordinator_result.external_request_count
    )
    write_count = (
        0 if coordinator_result is None else coordinator_result.production_write_count
    )
    alert_required = (
        False if coordinator_result is None else coordinator_result.alert_required
    )
    logical = {
        "contract_version": CONTRACT_VERSION,
        "status": status.value,
        "target_session": plan.target_session,
        "wake_plan_fingerprint": plan.logical_content_fingerprint,
        "coordinator_result_fingerprint": coordinator_result_fingerprint,
        "coordinator_status": coordinator_status,
        "coordinator_next_action": coordinator_next_action,
        "coordinator_invocation_count": invocation_count,
        "external_request_count": request_count,
        "production_write_count": write_count,
        "alert_required": alert_required,
        "alert_delivery_attempted": False,
        "recovery_attempted": False,
        "automatic_retry_enabled": False,
        "automatic_recovery_enabled": False,
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_installed": False,
        "transition_outcome_formally_known": coordinator_result is not None,
    }
    return DailyEodScheduledWakeResult(
        contract_version=CONTRACT_VERSION,
        status=status,
        target_session=plan.target_session,
        wake_plan_fingerprint=plan.logical_content_fingerprint,
        coordinator_result_fingerprint=coordinator_result_fingerprint,
        coordinator_status=coordinator_status,
        coordinator_next_action=coordinator_next_action,
        coordinator_invocation_count=invocation_count,
        external_request_count=request_count,
        production_write_count=write_count,
        alert_required=alert_required,
        alert_delivery_attempted=False,
        recovery_attempted=False,
        automatic_retry_enabled=False,
        automatic_recovery_enabled=False,
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_installed=False,
        transition_outcome_formally_known=coordinator_result is not None,
        logical_content_fingerprint=_fingerprint(logical),
    )


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
