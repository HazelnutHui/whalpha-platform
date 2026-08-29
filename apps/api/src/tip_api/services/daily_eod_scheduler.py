"""Read-only planning for one default-off daily scheduler wake."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from tip_api.services.daily_eod_readiness import DailyEodReadinessPolicy
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar


CONTRACT_VERSION = "daily-eod-scheduler-wake-plan/1.0"


class DailyEodSchedulerError(RuntimeError):
    """Raised when one safe scheduler wake cannot be planned."""


class SchedulerWakeStatus(StrEnum):
    UP_TO_DATE = "up_to_date"
    WAITING = "waiting"
    READY_FOR_WAKE = "ready_for_wake"


class SchedulerWakeAction(StrEnum):
    WAIT = "wait"
    REVIEW_ONE_TRANSITION_WAKE = "review_one_transition_wake"
    INVOKE_ONE_TRANSITION = "invoke_one_transition"


@dataclass(frozen=True, slots=True)
class DailyEodSchedulerWakePlan:
    contract_version: str
    checked_at: str
    status: SchedulerWakeStatus
    next_action: SchedulerWakeAction
    latest_canonical_session: str
    expected_latest_completed_session: str
    target_session: str
    missing_session_count: int
    next_check_at: str
    reason_codes: tuple[str, ...]
    readiness_policy_fingerprint: str
    scheduler_candidate_enabled: bool
    scheduler_installed: bool
    coordinator_invocation_limit: int
    coordinator_invocation_count: int
    automatic_retry_enabled: bool
    automatic_recovery_enabled: bool
    publication_authorized: bool
    deployment_authorized: bool
    credential_access_count: int
    external_request_count: int
    filesystem_write_count: int
    production_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["status"] = self.status.value
        value["next_action"] = self.next_action.value
        return value


def plan_daily_eod_scheduler_wake(
    *,
    checked_at: datetime,
    completed_sessions: tuple[date, ...],
    review_enabled_candidate: bool = False,
    policy: DailyEodReadinessPolicy | None = None,
    calendar: MarketSessionCalendar | None = None,
) -> DailyEodSchedulerWakePlan:
    """Plan one future wake without invoking the coordinator or writing state."""

    checked = _aware_utc(checked_at)
    selected_policy = policy or DailyEodReadinessPolicy()
    session_calendar = calendar or ExchangeCalendar()
    sessions = _validate_completed_sessions(completed_sessions, session_calendar)
    latest = sessions[-1]
    expected = session_calendar.latest_completed_session(checked)
    if latest > expected:
        raise DailyEodSchedulerError(
            "latest canonical session cannot exceed calendar-completed state"
        )

    missing_count = session_calendar.session_lag(latest, expected)
    target = session_calendar.next_session(latest)
    if missing_count == 0:
        status = SchedulerWakeStatus.UP_TO_DATE
        action = SchedulerWakeAction.WAIT
        next_check = _review_at(
            target,
            selected_policy=selected_policy,
            session_calendar=session_calendar,
        )
        reasons = ("canonical_eod_current", "wait_for_next_session_stabilization")
    else:
        current_review_at = _review_at(
            target,
            selected_policy=selected_policy,
            session_calendar=session_calendar,
        )
        next_check = checked if target < expected else current_review_at
        if checked < next_check:
            status = SchedulerWakeStatus.WAITING
            action = SchedulerWakeAction.WAIT
            reasons = (
                "target_session_closed",
                "post_close_stabilization_window",
                "provider_completeness_not_asserted",
            )
        else:
            status = SchedulerWakeStatus.READY_FOR_WAKE
            action = (
                SchedulerWakeAction.INVOKE_ONE_TRANSITION
                if review_enabled_candidate
                else SchedulerWakeAction.REVIEW_ONE_TRANSITION_WAKE
            )
            reasons = (
                "oldest_missing_session_selected",
                "one_transition_wake_review_ready",
                "provider_completeness_not_asserted",
            )

    logical = {
        "contract_version": CONTRACT_VERSION,
        "checked_at": checked.isoformat(),
        "status": status.value,
        "next_action": action.value,
        "latest_canonical_session": latest.isoformat(),
        "expected_latest_completed_session": expected.isoformat(),
        "target_session": target.isoformat(),
        "missing_session_count": missing_count,
        "next_check_at": next_check.isoformat(),
        "reason_codes": list(reasons),
        "readiness_policy_fingerprint": selected_policy.logical_fingerprint,
        "scheduler_candidate_enabled": review_enabled_candidate,
        "scheduler_installed": False,
        "coordinator_invocation_limit": 1,
        "coordinator_invocation_count": 0,
        "automatic_retry_enabled": False,
        "automatic_recovery_enabled": False,
        "publication_authorized": False,
        "deployment_authorized": False,
        "credential_access_count": 0,
        "external_request_count": 0,
        "filesystem_write_count": 0,
        "production_write_count": 0,
    }
    return DailyEodSchedulerWakePlan(
        contract_version=CONTRACT_VERSION,
        checked_at=checked.isoformat(),
        status=status,
        next_action=action,
        latest_canonical_session=latest.isoformat(),
        expected_latest_completed_session=expected.isoformat(),
        target_session=target.isoformat(),
        missing_session_count=missing_count,
        next_check_at=next_check.isoformat(),
        reason_codes=reasons,
        readiness_policy_fingerprint=selected_policy.logical_fingerprint,
        scheduler_candidate_enabled=review_enabled_candidate,
        scheduler_installed=False,
        coordinator_invocation_limit=1,
        coordinator_invocation_count=0,
        automatic_retry_enabled=False,
        automatic_recovery_enabled=False,
        publication_authorized=False,
        deployment_authorized=False,
        credential_access_count=0,
        external_request_count=0,
        filesystem_write_count=0,
        production_write_count=0,
        logical_content_fingerprint=_fingerprint(logical),
    )


def _validate_completed_sessions(
    completed_sessions: tuple[date, ...],
    calendar: MarketSessionCalendar,
) -> tuple[date, ...]:
    if not completed_sessions:
        raise DailyEodSchedulerError("canonical EOD session sequence is empty")
    if tuple(sorted(set(completed_sessions))) != completed_sessions:
        raise DailyEodSchedulerError(
            "canonical EOD sessions must be unique and chronological"
        )
    for index, session in enumerate(completed_sessions):
        if not calendar.is_session(session):
            raise DailyEodSchedulerError("canonical EOD contains a non-XNYS session")
        if index and calendar.next_session(completed_sessions[index - 1]) != session:
            raise DailyEodSchedulerError("canonical EOD session sequence is not contiguous")
    return completed_sessions


def _review_at(
    session: date,
    *,
    selected_policy: DailyEodReadinessPolicy,
    session_calendar: MarketSessionCalendar,
) -> datetime:
    return session_calendar.session_close(session) + timedelta(
        seconds=selected_policy.stabilization_delay_seconds
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodSchedulerError("checked_at must be timezone-aware")
    return value.astimezone(UTC)


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
