"""Durable reservation, outcome, and recovery custody for daily provider fetches."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Callable

from tip_api.providers.massive.same_day_catchup import (
    FetchPackageEvidenceV1,
    SameDayCatchupError,
    read_fetch_package_evidence,
)
from tip_api.services.daily_eod_automation import NextAction
from tip_api.services.daily_eod_readiness import (
    ACQUISITION_ACTIONS,
    AcquisitionAttempt,
    AttemptOutcome,
    DailyEodReadinessPlan,
    ReadinessNextAction,
    ReadinessStatus,
    plan_daily_eod_readiness,
)
from tip_api.services.daily_eod_run_journal import (
    ACQUISITION_START_EVENT,
    DailyEodRunEvent,
    DailyEodRunJournalError,
    locked_daily_eod_run_journal,
    new_attempt_id,
    unresolved_started_event,
)


CONTRACT_VERSION = "daily-eod-acquisition-custody/1.0"
MAXIMUM_PLAN_AGE = timedelta(minutes=5)
OUTCOME_EVENT = {
    AttemptOutcome.NOT_READY: "acquisition_not_ready",
    AttemptOutcome.RATE_LIMITED: "acquisition_rate_limited",
    AttemptOutcome.TRANSIENT_FAILURE: "acquisition_transient_failed",
    AttemptOutcome.FETCH_PACKAGE_READY: "acquisition_package_ready",
    AttemptOutcome.PERMANENT_FAILURE: "acquisition_permanent_failed",
    AttemptOutcome.QUALITY_FAILURE: "acquisition_quality_failed",
}
EVENT_OUTCOME = {
    **{event: outcome for outcome, event in OUTCOME_EVENT.items()},
    "acquisition_recovered_package_ready": AttemptOutcome.FETCH_PACKAGE_READY,
    "acquisition_recovered_not_completed": AttemptOutcome.TRANSIENT_FAILURE,
    "acquisition_recovery_blocked": AttemptOutcome.PERMANENT_FAILURE,
}


class DailyEodAcquisitionCustodyError(RuntimeError):
    """Raised when provider-attempt custody cannot prove a safe transition."""


@dataclass(frozen=True, slots=True)
class DailyEodAcquisitionConfig:
    target_session: date
    latest_canonical_session: date
    acquisition_action: NextAction
    package_path: Path
    run_root: Path


@dataclass(frozen=True, slots=True)
class AcquisitionCustodyResult:
    outcome: str
    attempt_id: str
    event: DailyEodRunEvent
    readiness_plan: DailyEodReadinessPlan | None = None
    package_evidence: FetchPackageEvidenceV1 | None = None
    reason_code: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": CONTRACT_VERSION,
            "outcome": self.outcome,
            "attempt_id": self.attempt_id,
            "event_fingerprint": self.event.event_fingerprint,
            "readiness_plan_fingerprint": (
                None
                if self.readiness_plan is None
                else self.readiness_plan.logical_content_fingerprint
            ),
            "package_manifest_sha256": (
                None
                if self.package_evidence is None
                else self.package_evidence.package_manifest_sha256
            ),
            "package_content_sha256": (
                None
                if self.package_evidence is None
                else self.package_evidence.package_content_sha256
            ),
            "reason_code": self.reason_code,
            "provider_request_executed_by_custody": False,
            "provider_request_outcome_recorded": self.outcome
            not in {"reserved", "recovered_not_completed", "recovery_blocked"},
            "credential_access_count": 0,
            "production_write_count": 0,
            "apply_authorized": False,
            "scheduler_enabled": False,
        }


Clock = Callable[[], datetime]


def reserve_acquisition_attempt(
    *,
    config: DailyEodAcquisitionConfig,
    checked_at: datetime,
    expected_readiness_fingerprint: str,
    authorization_file_sha256: str | None = None,
    authorization_content_sha256: str | None = None,
    clock: Clock = lambda: datetime.now(UTC),
) -> AcquisitionCustodyResult:
    """Reserve one separately authorized fetch without executing it."""

    _validate_config(config, require_new_package=True)
    observed_at = _aware_utc(clock())
    checked = _aware_utc(checked_at)
    if observed_at < checked or observed_at - checked > MAXIMUM_PLAN_AGE:
        raise DailyEodAcquisitionCustodyError("readiness plan is outside the reservation age window")
    if not _is_fingerprint(expected_readiness_fingerprint):
        raise DailyEodAcquisitionCustodyError("readiness fingerprint is malformed")
    _validate_authorization_binding(
        authorization_file_sha256,
        authorization_content_sha256,
    )
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        events = journal.read_events()
        if unresolved_started_event(events) is not None:
            raise DailyEodAcquisitionCustodyError("daily run has an unresolved attempt")
        attempts = acquisition_attempts_from_events(
            events,
            target_session=config.target_session,
            acquisition_action=config.acquisition_action,
        )
        readiness = plan_daily_eod_readiness(
            checked_at=checked,
            target_session=config.target_session,
            latest_canonical_session=config.latest_canonical_session,
            acquisition_action=config.acquisition_action,
            attempts=attempts,
        )
        if (
            readiness.logical_content_fingerprint != expected_readiness_fingerprint
            or readiness.next_action is not ReadinessNextAction.REVIEW_FETCH_AUTHORIZATION
            or readiness.status
            not in {
                ReadinessStatus.READY_FOR_FETCH_REVIEW,
                ReadinessStatus.MISSED_SESSION_RECOVERY,
            }
        ):
            raise DailyEodAcquisitionCustodyError("readiness plan is stale or not fetch-reviewable")
        attempt_id = new_attempt_id(
            target_session=config.target_session,
            plan_fingerprint=expected_readiness_fingerprint,
            sequence=len(events) + 1,
        )
        event = journal.append(
            event_type=ACQUISITION_START_EVENT,
            attempt_id=attempt_id,
            observed_at=observed_at,
            details={
                "custody_contract": CONTRACT_VERSION,
                "acquisition_action": config.acquisition_action.value,
                "readiness_plan_fingerprint": readiness.logical_content_fingerprint,
                "readiness_status": readiness.status.value,
                "execution_input_fingerprint": _execution_input_fingerprint(config),
                "package_path": str(config.package_path),
                "attempt_number": len(attempts) + 1,
                "authorization_file_sha256": authorization_file_sha256,
                "authorization_content_sha256": authorization_content_sha256,
            },
        )
        return AcquisitionCustodyResult(
            outcome="reserved",
            attempt_id=attempt_id,
            event=event,
            readiness_plan=readiness,
            reason_code="fetch_reserved_but_not_executed",
        )


def record_acquisition_outcome(
    *,
    config: DailyEodAcquisitionConfig,
    outcome: AttemptOutcome,
    retry_after_seconds: int | None = None,
    authorization_decision_fingerprint: str | None = None,
    clock: Clock = lambda: datetime.now(UTC),
) -> AcquisitionCustodyResult:
    """Record the result of an externally authorized fetch under exact custody."""

    _validate_config(config, require_new_package=False)
    _validate_outcome(outcome, retry_after_seconds)
    if authorization_decision_fingerprint is not None and not _is_fingerprint(
        authorization_decision_fingerprint
    ):
        raise DailyEodAcquisitionCustodyError(
            "authorization decision fingerprint is malformed"
        )
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        pending = _pending_acquisition(journal.read_events(), config)
        observed_at = _aware_utc(clock())
        package_evidence = _outcome_package_evidence(
            config,
            outcome,
            started_at=datetime.fromisoformat(pending.observed_at),
            observed_at=observed_at,
        )
        details: dict[str, object] = {
            "acquisition_action": config.acquisition_action.value,
            "outcome": outcome.value,
            "reason_code": f"fetch_{outcome.value}",
            "retry_after_seconds": retry_after_seconds,
            "provider_request_executed_by_custody": False,
            "authorization_decision_fingerprint": authorization_decision_fingerprint,
        }
        if package_evidence is not None:
            details.update(
                {
                    "request_count": package_evidence.request_count,
                    "fetched_at": package_evidence.fetched_at.isoformat(),
                    "package_manifest_sha256": package_evidence.package_manifest_sha256,
                    "package_content_sha256": package_evidence.package_content_sha256,
                }
            )
        event = journal.append(
            event_type=OUTCOME_EVENT[outcome],
            attempt_id=pending.attempt_id,
            observed_at=observed_at,
            details=details,
        )
        readiness = _readiness_from_events(
            journal.read_events(), config=config, checked_at=observed_at
        )
        return AcquisitionCustodyResult(
            outcome=outcome.value,
            attempt_id=pending.attempt_id,
            event=event,
            readiness_plan=readiness,
            package_evidence=package_evidence,
            reason_code=f"fetch_{outcome.value}",
        )


def recover_acquisition_attempt(
    *,
    config: DailyEodAcquisitionConfig,
    clock: Clock = lambda: datetime.now(UTC),
) -> AcquisitionCustodyResult:
    """Classify an interrupted fetch from package custody without network access."""

    _validate_config(config, require_new_package=False)
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        pending = _pending_acquisition(journal.read_events(), config)
        observed_at = _aware_utc(clock())
        started_at = datetime.fromisoformat(pending.observed_at)
        package_evidence: FetchPackageEvidenceV1 | None = None
        if config.package_path.exists() and not config.package_path.is_symlink():
            try:
                package_evidence = _read_package(config)
                _validate_package_evidence(
                    package_evidence,
                    config,
                    started_at=started_at,
                    observed_at=observed_at,
                )
            except (OSError, SameDayCatchupError, DailyEodAcquisitionCustodyError):
                event_type = "acquisition_recovery_blocked"
                outcome = "recovery_blocked"
                reason = "package_present_but_not_formally_valid"
            else:
                event_type = "acquisition_recovered_package_ready"
                outcome = "recovered_package_ready"
                reason = "completed_package_formally_reconciled"
        elif os.path.lexists(config.package_path) or os.path.lexists(_staging_path(config.package_path)):
            event_type = "acquisition_recovery_blocked"
            outcome = "recovery_blocked"
            reason = "package_or_staging_residue_requires_diagnosis"
        else:
            event_type = "acquisition_recovered_not_completed"
            outcome = "recovered_not_completed"
            reason = "no_completed_package_detected"
        details: dict[str, object] = {
            "acquisition_action": config.acquisition_action.value,
            "reason_code": reason,
            "provider_request_executed_by_custody": False,
        }
        if package_evidence is not None:
            details.update(
                {
                    "request_count": package_evidence.request_count,
                    "package_manifest_sha256": package_evidence.package_manifest_sha256,
                    "package_content_sha256": package_evidence.package_content_sha256,
                }
            )
        event = journal.append(
            event_type=event_type,
            attempt_id=pending.attempt_id,
            observed_at=observed_at,
            details=details,
        )
        readiness = _readiness_from_events(
            journal.read_events(), config=config, checked_at=observed_at
        )
        return AcquisitionCustodyResult(
            outcome=outcome,
            attempt_id=pending.attempt_id,
            event=event,
            readiness_plan=readiness,
            package_evidence=package_evidence,
            reason_code=reason,
        )


def acquisition_attempts_from_events(
    events: tuple[DailyEodRunEvent, ...],
    *,
    target_session: date,
    acquisition_action: NextAction,
) -> tuple[AcquisitionAttempt, ...]:
    """Project completed exact-action acquisition pairs into readiness evidence."""

    attempts: list[AcquisitionAttempt] = []
    pending: DailyEodRunEvent | None = None
    for event in events:
        if event.event_type == ACQUISITION_START_EVENT:
            pending = event
            continue
        if event.event_type not in EVENT_OUTCOME:
            continue
        if pending is None or pending.attempt_id != event.attempt_id:
            raise DailyEodRunJournalError("acquisition terminal has no matching start")
        try:
            action = NextAction(str(pending.details["acquisition_action"]))
            attempt_number = int(pending.details["attempt_number"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DailyEodRunJournalError("acquisition start details are malformed") from exc
        if action is acquisition_action:
            if pending.target_session != target_session.isoformat():
                raise DailyEodRunJournalError("acquisition session mismatch")
            retry_after = event.details.get("retry_after_seconds")
            attempts.append(
                AcquisitionAttempt(
                    sequence=len(attempts) + 1,
                    observed_at=datetime.fromisoformat(pending.observed_at),
                    outcome=EVENT_OUTCOME[event.event_type],
                    retry_after_seconds=(
                        retry_after if isinstance(retry_after, int) else None
                    ),
                )
            )
            if attempt_number != len(attempts):
                raise DailyEodRunJournalError("acquisition attempt number mismatch")
        pending = None
    return tuple(attempts)


def _readiness_from_events(
    events: tuple[DailyEodRunEvent, ...],
    *,
    config: DailyEodAcquisitionConfig,
    checked_at: datetime,
) -> DailyEodReadinessPlan:
    return plan_daily_eod_readiness(
        checked_at=checked_at,
        target_session=config.target_session,
        latest_canonical_session=config.latest_canonical_session,
        acquisition_action=config.acquisition_action,
        attempts=acquisition_attempts_from_events(
            events,
            target_session=config.target_session,
            acquisition_action=config.acquisition_action,
        ),
    )


def _pending_acquisition(
    events: tuple[DailyEodRunEvent, ...], config: DailyEodAcquisitionConfig
) -> DailyEodRunEvent:
    pending = unresolved_started_event(events)
    if pending is None or pending.event_type != ACQUISITION_START_EVENT:
        raise DailyEodAcquisitionCustodyError("no unresolved acquisition attempt exists")
    if pending.details.get("execution_input_fingerprint") != _execution_input_fingerprint(config):
        raise DailyEodAcquisitionCustodyError("acquisition inputs differ from reservation")
    return pending


def _outcome_package_evidence(
    config: DailyEodAcquisitionConfig,
    outcome: AttemptOutcome,
    *,
    started_at: datetime,
    observed_at: datetime,
) -> FetchPackageEvidenceV1 | None:
    if outcome is AttemptOutcome.FETCH_PACKAGE_READY:
        evidence = _read_package(config)
        _validate_package_evidence(
            evidence,
            config,
            started_at=started_at,
            observed_at=observed_at,
        )
        return evidence
    if os.path.lexists(config.package_path) or os.path.lexists(_staging_path(config.package_path)):
        raise DailyEodAcquisitionCustodyError(
            "non-package-ready outcome cannot leave package custody"
        )
    return None


def _read_package(config: DailyEodAcquisitionConfig) -> FetchPackageEvidenceV1:
    operation = (
        "identity"
        if config.acquisition_action is NextAction.PREPARE_IDENTITY_CATCHUP
        else "eod"
    )
    try:
        return read_fetch_package_evidence(
            package_path=config.package_path,
            operation=operation,
            expected_session=config.target_session,
        )
    except (OSError, SameDayCatchupError) as exc:
        raise DailyEodAcquisitionCustodyError("fetch package failed formal reread") from exc


def _validate_package_evidence(
    evidence: FetchPackageEvidenceV1,
    config: DailyEodAcquisitionConfig,
    *,
    started_at: datetime,
    observed_at: datetime,
) -> None:
    expected_operation = (
        "identity"
        if config.acquisition_action is NextAction.PREPARE_IDENTITY_CATCHUP
        else "eod"
    )
    expected_type = "identity_reference" if expected_operation == "identity" else "grouped_daily"
    fetched_at = _aware_utc(evidence.fetched_at)
    if (
        evidence.operation != expected_operation
        or evidence.session_date != config.target_session
        or evidence.package_path != str(config.package_path)
        or evidence.package_type != expected_type
        or not _is_fingerprint(evidence.package_manifest_sha256)
        or not _is_fingerprint(evidence.package_content_sha256)
        or fetched_at < started_at
        or fetched_at > observed_at
        or (
            expected_operation == "eod"
            and evidence.request_count != 1
        )
        or (
            expected_operation == "identity"
            and not 1 <= evidence.request_count <= 20
        )
    ):
        raise DailyEodAcquisitionCustodyError(
            "fetch package evidence does not match the reserved attempt"
        )


def _validate_config(
    config: DailyEodAcquisitionConfig, *, require_new_package: bool
) -> None:
    if config.acquisition_action not in ACQUISITION_ACTIONS:
        raise DailyEodAcquisitionCustodyError("custody accepts only acquisition actions")
    if not config.run_root.is_absolute():
        raise DailyEodAcquisitionCustodyError("run root must be absolute")
    if _is_within(config.run_root, Path("/data")):
        raise DailyEodAcquisitionCustodyError("run root must remain outside /data")
    if (
        not config.package_path.is_absolute()
        or config.package_path.parent != Path("/tmp")
        or config.package_path.name.startswith(".")
    ):
        raise DailyEodAcquisitionCustodyError("fetch package must be a direct non-hidden child of /tmp")
    if require_new_package and (
        os.path.lexists(config.package_path)
        or os.path.lexists(_staging_path(config.package_path))
    ):
        raise DailyEodAcquisitionCustodyError("fetch package target or staging already exists")


def _validate_outcome(outcome: AttemptOutcome, retry_after_seconds: int | None) -> None:
    if not isinstance(outcome, AttemptOutcome):
        raise DailyEodAcquisitionCustodyError("acquisition outcome is invalid")
    if retry_after_seconds is not None and (
        outcome is not AttemptOutcome.RATE_LIMITED
        or type(retry_after_seconds) is not int
        or retry_after_seconds < 0
        or retry_after_seconds > 4 * 60 * 60
    ):
        raise DailyEodAcquisitionCustodyError("retry-after outcome evidence is invalid")


def _validate_authorization_binding(
    file_sha256: str | None,
    content_sha256: str | None,
) -> None:
    if (file_sha256 is None) != (content_sha256 is None) or (
        file_sha256 is not None
        and (not _is_fingerprint(file_sha256) or not _is_fingerprint(content_sha256))
    ):
        raise DailyEodAcquisitionCustodyError(
            "authorization artifact binding is malformed"
        )


def _execution_input_fingerprint(config: DailyEodAcquisitionConfig) -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "target_session": config.target_session.isoformat(),
            "latest_canonical_session": config.latest_canonical_session.isoformat(),
            "acquisition_action": config.acquisition_action.value,
            "package_path": str(config.package_path),
            "run_root": str(config.run_root),
        }
    )


def _staging_path(path: Path) -> Path:
    return path.with_name("." + path.name + ".staging")


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.absolute().relative_to(root.absolute())
        return True
    except ValueError:
        return False


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodAcquisitionCustodyError("custody timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _fingerprint(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
