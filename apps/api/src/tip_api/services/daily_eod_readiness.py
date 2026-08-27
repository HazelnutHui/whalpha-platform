"""Deterministic, network-free readiness policy for daily EOD acquisition review."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from tip_api.services.daily_eod_automation import NextAction
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar


CONTRACT_VERSION = "daily-eod-readiness-plan/1.0"
ACQUISITION_ACTIONS = frozenset(
    {NextAction.PREPARE_IDENTITY_CATCHUP, NextAction.PREPARE_EOD_CATCHUP}
)


class DailyEodReadinessError(RuntimeError):
    """Raised when inputs cannot define one safe acquisition-readiness decision."""


class AttemptOutcome(StrEnum):
    NOT_READY = "not_ready"
    RATE_LIMITED = "rate_limited"
    TRANSIENT_FAILURE = "transient_failure"
    FETCH_PACKAGE_READY = "fetch_package_ready"
    PERMANENT_FAILURE = "permanent_failure"
    QUALITY_FAILURE = "quality_failure"


class ReadinessStatus(StrEnum):
    ALREADY_COMPLETED = "already_completed"
    WAITING_FOR_CLOSE = "waiting_for_close"
    STABILIZING = "stabilizing"
    READY_FOR_FETCH_REVIEW = "ready_for_fetch_review"
    WAITING_TO_RETRY = "waiting_to_retry"
    READY_FOR_APPLY_REVIEW = "ready_for_apply_review"
    MISSED_SESSION_RECOVERY = "missed_session_recovery"
    BLOCKED = "blocked"


class ReadinessNextAction(StrEnum):
    NONE = "none"
    WAIT = "wait"
    REVIEW_FETCH_AUTHORIZATION = "review_fetch_authorization"
    REVIEW_APPLY_AUTHORIZATION = "review_apply_authorization"
    OPERATOR_DIAGNOSIS = "operator_diagnosis"


@dataclass(frozen=True, slots=True)
class DailyEodReadinessPolicy:
    stabilization_delay_seconds: int = 30 * 60
    retry_delay_seconds: tuple[int, ...] = (15 * 60, 30 * 60, 60 * 60, 120 * 60)
    deadline_after_close_seconds: int = 6 * 60 * 60
    maximum_attempt_count: int = 5
    maximum_retry_after_seconds: int = 4 * 60 * 60

    def __post_init__(self) -> None:
        if (
            self.stabilization_delay_seconds < 0
            or self.deadline_after_close_seconds <= self.stabilization_delay_seconds
            or self.maximum_attempt_count < 1
            or len(self.retry_delay_seconds) != self.maximum_attempt_count - 1
            or any(value <= 0 for value in self.retry_delay_seconds)
            or tuple(sorted(self.retry_delay_seconds)) != self.retry_delay_seconds
            or self.maximum_retry_after_seconds <= 0
        ):
            raise DailyEodReadinessError("daily readiness policy is malformed")

    @property
    def logical_fingerprint(self) -> str:
        return _fingerprint(asdict(self))


@dataclass(frozen=True, slots=True)
class AcquisitionAttempt:
    sequence: int
    observed_at: datetime
    outcome: AttemptOutcome
    retry_after_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class DailyEodReadinessPlan:
    contract_version: str
    checked_at: str
    target_session: str
    latest_canonical_session: str
    expected_latest_session: str
    acquisition_action: str
    session_close_at: str
    earliest_fetch_review_at: str
    deadline_at: str
    status: ReadinessStatus
    next_action: ReadinessNextAction
    reason_codes: tuple[str, ...]
    attempt_count: int
    next_check_at: str | None
    missing_session_count: int
    alert_required: bool
    policy_fingerprint: str
    provider_completeness_asserted: bool
    scheduler_enabled: bool
    external_request_count: int
    production_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def plan_daily_eod_readiness(
    *,
    checked_at: datetime,
    target_session: date,
    latest_canonical_session: date,
    acquisition_action: NextAction,
    attempts: tuple[AcquisitionAttempt, ...] = (),
    policy: DailyEodReadinessPolicy | None = None,
    calendar: MarketSessionCalendar | None = None,
) -> DailyEodReadinessPlan:
    """Return one review/wait/diagnosis decision without provider or filesystem I/O."""

    checked = _aware_utc(checked_at)
    selected_policy = policy or DailyEodReadinessPolicy()
    session_calendar = calendar or ExchangeCalendar()
    if acquisition_action not in ACQUISITION_ACTIONS:
        raise DailyEodReadinessError("readiness accepts only acquisition preparation actions")
    if not session_calendar.is_session(target_session):
        raise DailyEodReadinessError("readiness target must be an XNYS session")
    if not session_calendar.is_session(latest_canonical_session):
        raise DailyEodReadinessError("latest canonical date must be an XNYS session")
    expected = session_calendar.latest_completed_session(checked)
    if latest_canonical_session > expected:
        raise DailyEodReadinessError("latest canonical session cannot exceed calendar state")
    if latest_canonical_session == target_session:
        if attempts:
            raise DailyEodReadinessError("completed target must not carry pending attempt history")
        return _build_plan(
            checked=checked,
            target=target_session,
            latest=latest_canonical_session,
            expected=expected,
            acquisition_action=acquisition_action,
            close_at=session_calendar.session_close(target_session),
            policy=selected_policy,
            attempts=attempts,
            status=ReadinessStatus.ALREADY_COMPLETED,
            next_action=ReadinessNextAction.NONE,
            reasons=("target_already_canonical",),
            next_check_at=None,
            missing_count=0,
            alert=False,
        )
    if session_calendar.next_session(latest_canonical_session) != target_session:
        raise DailyEodReadinessError("target must be the oldest missing XNYS session")

    close_at = session_calendar.session_close(target_session)
    earliest = close_at + timedelta(seconds=selected_policy.stabilization_delay_seconds)
    deadline = close_at + timedelta(seconds=selected_policy.deadline_after_close_seconds)
    normalized_attempts = _validate_attempts(
        attempts,
        checked=checked,
        earliest=earliest,
        policy=selected_policy,
    )
    missing_count = session_calendar.session_lag(latest_canonical_session, expected)

    if checked < close_at:
        decision = (
            ReadinessStatus.WAITING_FOR_CLOSE,
            ReadinessNextAction.WAIT,
            ("target_session_not_closed",),
            close_at,
            False,
        )
    elif checked < earliest:
        decision = (
            ReadinessStatus.STABILIZING,
            ReadinessNextAction.WAIT,
            ("post_close_stabilization_window", "provider_completeness_not_asserted"),
            earliest,
            False,
        )
    elif not normalized_attempts:
        overdue = checked > deadline
        decision = (
            ReadinessStatus.MISSED_SESSION_RECOVERY if overdue else ReadinessStatus.READY_FOR_FETCH_REVIEW,
            ReadinessNextAction.REVIEW_FETCH_AUTHORIZATION,
            (
                ("daily_deadline_elapsed", "oldest_missing_session_first")
                if overdue
                else ("first_fetch_review_due", "provider_completeness_not_asserted")
            ),
            None,
            overdue,
        )
    else:
        decision = _decision_after_attempts(
            checked=checked,
            deadline=deadline,
            attempts=normalized_attempts,
            policy=selected_policy,
        )

    status, next_action, reasons, next_check_at, alert = decision
    return _build_plan(
        checked=checked,
        target=target_session,
        latest=latest_canonical_session,
        expected=expected,
        acquisition_action=acquisition_action,
        close_at=close_at,
        policy=selected_policy,
        attempts=normalized_attempts,
        status=status,
        next_action=next_action,
        reasons=reasons,
        next_check_at=next_check_at,
        missing_count=missing_count,
        alert=alert,
    )


def _decision_after_attempts(
    *,
    checked: datetime,
    deadline: datetime,
    attempts: tuple[AcquisitionAttempt, ...],
    policy: DailyEodReadinessPolicy,
) -> tuple[ReadinessStatus, ReadinessNextAction, tuple[str, ...], datetime | None, bool]:
    last = attempts[-1]
    if last.outcome is AttemptOutcome.FETCH_PACKAGE_READY:
        return (
            ReadinessStatus.READY_FOR_APPLY_REVIEW,
            ReadinessNextAction.REVIEW_APPLY_AUTHORIZATION,
            ("fetch_package_ready_requires_separate_apply_review",),
            None,
            False,
        )
    if last.outcome in {AttemptOutcome.PERMANENT_FAILURE, AttemptOutcome.QUALITY_FAILURE}:
        return (
            ReadinessStatus.BLOCKED,
            ReadinessNextAction.OPERATOR_DIAGNOSIS,
            (f"{last.outcome.value}_requires_diagnosis",),
            None,
            True,
        )
    if len(attempts) >= policy.maximum_attempt_count:
        return (
            ReadinessStatus.BLOCKED,
            ReadinessNextAction.OPERATOR_DIAGNOSIS,
            ("bounded_attempts_exhausted",),
            None,
            True,
        )
    delay = policy.retry_delay_seconds[len(attempts) - 1]
    if last.retry_after_seconds is not None:
        delay = max(delay, last.retry_after_seconds)
    retry_at = last.observed_at + timedelta(seconds=delay)
    if checked < retry_at:
        return (
            ReadinessStatus.WAITING_TO_RETRY,
            ReadinessNextAction.WAIT,
            (f"{last.outcome.value}_bounded_backoff",),
            retry_at,
            False,
        )
    if checked > deadline:
        return (
            ReadinessStatus.MISSED_SESSION_RECOVERY,
            ReadinessNextAction.REVIEW_FETCH_AUTHORIZATION,
            ("daily_deadline_elapsed", "oldest_missing_session_first"),
            None,
            True,
        )
    return (
        ReadinessStatus.READY_FOR_FETCH_REVIEW,
        ReadinessNextAction.REVIEW_FETCH_AUTHORIZATION,
        ("bounded_retry_due", "provider_completeness_not_asserted"),
        None,
        False,
    )


def _validate_attempts(
    attempts: tuple[AcquisitionAttempt, ...],
    *,
    checked: datetime,
    earliest: datetime,
    policy: DailyEodReadinessPolicy,
) -> tuple[AcquisitionAttempt, ...]:
    previous: datetime | None = None
    terminal_seen = False
    normalized: list[AcquisitionAttempt] = []
    for expected_sequence, attempt in enumerate(attempts, start=1):
        observed = _aware_utc(attempt.observed_at)
        if (
            type(attempt.sequence) is not int
            or attempt.sequence != expected_sequence
            or not isinstance(attempt.outcome, AttemptOutcome)
            or observed < earliest
            or observed > checked
            or (previous is not None and observed <= previous)
            or terminal_seen
        ):
            raise DailyEodReadinessError("acquisition attempt history is invalid")
        if normalized:
            prior = normalized[-1]
            required_delay = policy.retry_delay_seconds[len(normalized) - 1]
            if prior.retry_after_seconds is not None:
                required_delay = max(required_delay, prior.retry_after_seconds)
            if observed < prior.observed_at + timedelta(seconds=required_delay):
                raise DailyEodReadinessError("acquisition attempt violated bounded backoff")
        if attempt.retry_after_seconds is not None and (
            attempt.outcome is not AttemptOutcome.RATE_LIMITED
            or isinstance(attempt.retry_after_seconds, bool)
            or not isinstance(attempt.retry_after_seconds, int)
            or attempt.retry_after_seconds < 0
            or attempt.retry_after_seconds > policy.maximum_retry_after_seconds
        ):
            raise DailyEodReadinessError("retry-after evidence is invalid")
        terminal_seen = attempt.outcome in {
            AttemptOutcome.FETCH_PACKAGE_READY,
            AttemptOutcome.PERMANENT_FAILURE,
            AttemptOutcome.QUALITY_FAILURE,
        }
        normalized.append(
            AcquisitionAttempt(
                sequence=attempt.sequence,
                observed_at=observed,
                outcome=attempt.outcome,
                retry_after_seconds=attempt.retry_after_seconds,
            )
        )
        previous = observed
    return tuple(normalized)


def _build_plan(
    *,
    checked: datetime,
    target: date,
    latest: date,
    expected: date,
    acquisition_action: NextAction,
    close_at: datetime,
    policy: DailyEodReadinessPolicy,
    attempts: tuple[AcquisitionAttempt, ...],
    status: ReadinessStatus,
    next_action: ReadinessNextAction,
    reasons: tuple[str, ...],
    next_check_at: datetime | None,
    missing_count: int,
    alert: bool,
) -> DailyEodReadinessPlan:
    base = {
        "contract_version": CONTRACT_VERSION,
        "checked_at": checked.isoformat(),
        "target_session": target.isoformat(),
        "latest_canonical_session": latest.isoformat(),
        "expected_latest_session": expected.isoformat(),
        "acquisition_action": acquisition_action.value,
        "session_close_at": close_at.isoformat(),
        "earliest_fetch_review_at": (
            close_at + timedelta(seconds=policy.stabilization_delay_seconds)
        ).isoformat(),
        "deadline_at": (
            close_at + timedelta(seconds=policy.deadline_after_close_seconds)
        ).isoformat(),
        "status": status.value,
        "next_action": next_action.value,
        "reason_codes": list(reasons),
        "attempt_count": len(attempts),
        "next_check_at": None if next_check_at is None else next_check_at.isoformat(),
        "missing_session_count": missing_count,
        "alert_required": alert,
        "policy_fingerprint": policy.logical_fingerprint,
        "provider_completeness_asserted": False,
        "scheduler_enabled": False,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    typed = {
        **base,
        "status": status,
        "next_action": next_action,
        "reason_codes": tuple(reasons),
    }
    return DailyEodReadinessPlan(
        **typed,
        logical_content_fingerprint=_fingerprint(base),
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodReadinessError("readiness timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _fingerprint(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
