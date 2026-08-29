"""Synthetic multi-wake rehearsal for the default-off scheduler boundary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime

from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorResult,
    daily_eod_coordinator_result_fingerprint,
)
from tip_api.services.daily_eod_scheduled_wake import run_one_scheduled_wake
from tip_api.services.daily_eod_scheduler import plan_daily_eod_scheduler_wake


CONTRACT_VERSION = "daily-eod-scheduler-rehearsal/1.0"


@dataclass(frozen=True, slots=True)
class SchedulerRehearsalScenario:
    name: str
    wake_status: str
    coordinator_status: str | None
    coordinator_invocation_count: int
    alert_required: bool
    alert_delivery_attempted: bool
    recovery_attempted: bool
    automatic_retry_enabled: bool
    automatic_recovery_enabled: bool


@dataclass(frozen=True, slots=True)
class DailyEodSchedulerRehearsalReport:
    contract_version: str
    scenarios: tuple[SchedulerRehearsalScenario, ...]
    scenario_count: int
    total_coordinator_invocation_count: int
    maximum_coordinator_invocations_per_wake: int
    synthetic_coordinator_results: bool
    scheduler_installed: bool
    credential_access_count: int
    external_request_count: int
    filesystem_write_count: int
    production_write_count: int
    publication_authorized: bool
    deployment_authorized: bool
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def review_daily_eod_scheduler_rehearsal() -> DailyEodSchedulerRehearsalReport:
    """Run five independent in-memory wakes with synthetic coordinator results."""

    current_plan = plan_daily_eod_scheduler_wake(
        checked_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
    )
    current = run_one_scheduled_wake(
        plan=current_plan,
        expected_plan_fingerprint=current_plan.logical_content_fingerprint,
    )
    ready_plan = plan_daily_eod_scheduler_wake(
        checked_at=datetime(2026, 8, 28, 21, tzinfo=UTC),
        completed_sessions=(date(2026, 8, 27),),
        review_enabled_candidate=True,
    )
    cases = (
        (
            "oldest_missing",
            CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED,
            "review_fetch_authorization",
            False,
        ),
        ("retry_wait", CoordinatorStatus.WAITING, "wait_for_retry", False),
        (
            "unresolved_interruption",
            CoordinatorStatus.RECOVERY_REQUIRED,
            "recover_acquisition",
            False,
        ),
        ("alert_required", CoordinatorStatus.BLOCKED, "operator_diagnosis", True),
    )
    scenarios = [
        SchedulerRehearsalScenario(
            name="current",
            wake_status=current.status.value,
            coordinator_status=current.coordinator_status,
            coordinator_invocation_count=current.coordinator_invocation_count,
            alert_required=current.alert_required,
            alert_delivery_attempted=current.alert_delivery_attempted,
            recovery_attempted=current.recovery_attempted,
            automatic_retry_enabled=current.automatic_retry_enabled,
            automatic_recovery_enabled=current.automatic_recovery_enabled,
        )
    ]
    for name, status, next_action, alert in cases:
        result = run_one_scheduled_wake(
            plan=ready_plan,
            expected_plan_fingerprint=ready_plan.logical_content_fingerprint,
            invoke_one_transition=True,
            coordinator=(
                lambda status=status, next_action=next_action, alert=alert: (
                    _coordinator_result(
                        status=status,
                        next_action=next_action,
                        alert=alert,
                    )
                )
            ),
        )
        scenarios.append(
            SchedulerRehearsalScenario(
                name=name,
                wake_status=result.status.value,
                coordinator_status=result.coordinator_status,
                coordinator_invocation_count=result.coordinator_invocation_count,
                alert_required=result.alert_required,
                alert_delivery_attempted=result.alert_delivery_attempted,
                recovery_attempted=result.recovery_attempted,
                automatic_retry_enabled=result.automatic_retry_enabled,
                automatic_recovery_enabled=result.automatic_recovery_enabled,
            )
        )
    logical = {
        "contract_version": CONTRACT_VERSION,
        "scenarios": [asdict(item) for item in scenarios],
        "scenario_count": len(scenarios),
        "total_coordinator_invocation_count": sum(
            item.coordinator_invocation_count for item in scenarios
        ),
        "maximum_coordinator_invocations_per_wake": max(
            item.coordinator_invocation_count for item in scenarios
        ),
        "synthetic_coordinator_results": True,
        "scheduler_installed": False,
        "credential_access_count": 0,
        "external_request_count": 0,
        "filesystem_write_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
        "deployment_authorized": False,
    }
    return DailyEodSchedulerRehearsalReport(
        contract_version=CONTRACT_VERSION,
        scenarios=tuple(scenarios),
        scenario_count=len(scenarios),
        total_coordinator_invocation_count=int(
            logical["total_coordinator_invocation_count"]
        ),
        maximum_coordinator_invocations_per_wake=int(
            logical["maximum_coordinator_invocations_per_wake"]
        ),
        synthetic_coordinator_results=True,
        scheduler_installed=False,
        credential_access_count=0,
        external_request_count=0,
        filesystem_write_count=0,
        production_write_count=0,
        publication_authorized=False,
        deployment_authorized=False,
        logical_content_fingerprint=_fingerprint(logical),
    )


def _coordinator_result(
    *,
    status: CoordinatorStatus,
    next_action: str,
    alert: bool,
) -> DailyEodCoordinatorResult:
    result = DailyEodCoordinatorResult(
        status=status,
        target_session="2026-08-28",
        next_action=next_action,
        reason_codes=(f"synthetic_{next_action}",),
        automation_plan_fingerprint="a" * 64,
        readiness_plan_fingerprint="b" * 64,
        transition_fingerprint=None,
        external_request_count=0,
        production_write_count=0,
        alert_required=alert,
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        logical_content_fingerprint="",
    )
    return replace(
        result,
        logical_content_fingerprint=daily_eod_coordinator_result_fingerprint(result),
    )


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
