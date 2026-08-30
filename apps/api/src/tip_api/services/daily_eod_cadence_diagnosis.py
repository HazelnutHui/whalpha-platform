"""Read-only diagnosis for one unresolved bounded-cadence reservation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from enum import StrEnum

from tip_api.services.daily_eod_cadence_evidence import (
    DailyEodCadenceEvidenceError,
    cadence_wake_state_from_events,
)
from tip_api.services.daily_eod_run_journal import (
    ACQUISITION_START_EVENT,
    ACQUISITION_TERMINAL_EVENTS,
    ACTION_TERMINAL_EVENTS,
    CANONICAL_APPLY_START_EVENT,
    CANONICAL_APPLY_TERMINAL_EVENTS,
    START_EVENT,
    DailyEodRunEvent,
    DailyEodRunJournalError,
    verify_daily_eod_run_event,
)


CONTRACT_VERSION = "daily-eod-cadence-diagnosis/1.0"
SUPPORTED_STARTS = {
    ACQUISITION_START_EVENT: (
        ACQUISITION_TERMINAL_EVENTS,
        "recover_acquisition_attempt",
    ),
    CANONICAL_APPLY_START_EVENT: (
        CANONICAL_APPLY_TERMINAL_EVENTS,
        "recover_canonical_apply",
    ),
    START_EVENT: (ACTION_TERMINAL_EVENTS, "recover_offline_action"),
}
ADVANCED_TERMINALS = {
    "acquisition_package_ready",
    "acquisition_recovered_package_ready",
    "canonical_apply_succeeded",
    "canonical_apply_recovered_succeeded",
    "action_succeeded",
    "action_recovered_succeeded",
}
NO_CHANGE_TERMINALS = {
    "acquisition_not_ready",
    "acquisition_rate_limited",
    "acquisition_transient_failed",
    "acquisition_recovered_not_completed",
}


class DailyEodCadenceDiagnosisError(RuntimeError):
    """Raised when cadence diagnosis inputs cannot be trusted exactly."""


class CadenceDiagnosisStatus(StrEnum):
    NO_PENDING_WAKE = "no_pending_wake"
    OUTCOME_UNKNOWN = "outcome_unknown"
    ACTION_RECOVERY_REQUIRED = "action_recovery_required"
    KNOWN_RESULT_REVIEW_READY = "known_result_review_ready"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class DailyEodCadenceDiagnosis:
    contract_version: str
    checked_at: str
    target_session: str
    status: CadenceDiagnosisStatus
    next_action: str
    reason_codes: tuple[str, ...]
    reservation_event_fingerprint: str | None
    cadence_sequence: int | None
    pipeline_action: str | None
    nested_start_event_type: str | None
    nested_start_event_fingerprint: str | None
    nested_terminal_event_type: str | None
    nested_terminal_event_fingerprint: str | None
    terminal_outcome_candidate: str | None
    events_after_reservation: int
    action_replayed: bool
    automatic_resolution_enabled: bool
    automatic_retry_enabled: bool
    automatic_recovery_enabled: bool
    external_request_count: int
    filesystem_write_count: int
    production_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


def diagnose_unresolved_cadence_wake(
    *,
    events: tuple[DailyEodRunEvent, ...],
    target_session: date,
    checked_at: datetime,
) -> DailyEodCadenceDiagnosis:
    """Classify journal evidence without writing, resolving, or replaying."""

    checked = _aware_utc(checked_at)
    _verify_event_chain(events, target_session=target_session)
    try:
        state = cadence_wake_state_from_events(
            events,
            target_session=target_session,
        )
    except DailyEodCadenceEvidenceError as exc:
        raise DailyEodCadenceDiagnosisError(
            "cadence custody state is invalid"
        ) from exc
    reservation = state.pending_event
    pending = state.pending_evidence
    if reservation is None:
        return _result(
            checked=checked,
            target_session=target_session,
            status=CadenceDiagnosisStatus.NO_PENDING_WAKE,
            next_action="none",
            reasons=("no_unresolved_cadence_reservation",),
        )
    if pending is None or checked < datetime.fromisoformat(reservation.observed_at):
        raise DailyEodCadenceDiagnosisError(
            "pending cadence reservation identity is inconsistent"
        )
    following = events[reservation.sequence :]
    common = {
        "checked": checked,
        "target_session": target_session,
        "reservation": reservation,
        "cadence_sequence": pending.sequence,
        "pipeline_action": pending.pipeline_action,
        "events_after_reservation": len(following),
    }
    if not following:
        return _result(
            **common,
            status=CadenceDiagnosisStatus.OUTCOME_UNKNOWN,
            next_action="operator_confirm_invocation_boundary",
            reasons=(
                "wake_reserved_without_nested_action_evidence",
                "automatic_replay_prohibited",
            ),
        )
    started = following[0]
    start_policy = SUPPORTED_STARTS.get(started.event_type)
    if start_policy is None:
        return _blocked(
            common,
            reasons=("unsupported_event_after_cadence_reservation",),
        )
    allowed_terminals, recovery_action = start_policy
    if len(following) == 1:
        return _result(
            **common,
            status=CadenceDiagnosisStatus.ACTION_RECOVERY_REQUIRED,
            next_action=recovery_action,
            reasons=(
                "nested_action_attempt_is_unresolved",
                "use_existing_no_replay_recovery_boundary",
            ),
            started=started,
        )
    if len(following) != 2:
        return _blocked(
            common,
            reasons=("unexpected_events_after_cadence_reservation",),
            started=started,
        )
    terminal = following[1]
    if (
        terminal.event_type not in allowed_terminals
        or terminal.attempt_id != started.attempt_id
    ):
        return _blocked(
            common,
            reasons=("nested_action_terminal_identity_conflict",),
            started=started,
            terminal=terminal,
        )
    outcome = (
        "advanced_candidate"
        if terminal.event_type in ADVANCED_TERMINALS
        else (
            "no_change_candidate"
            if terminal.event_type in NO_CHANGE_TERMINALS
            else "failed_candidate"
        )
    )
    return _result(
        **common,
        status=CadenceDiagnosisStatus.KNOWN_RESULT_REVIEW_READY,
        next_action="review_no_replay_cadence_resolution",
        reasons=(
            "nested_action_has_formal_terminal_evidence",
            "cadence_resolution_requires_separate_operator_review",
        ),
        started=started,
        terminal=terminal,
        terminal_outcome_candidate=outcome,
    )


def verify_daily_eod_cadence_diagnosis(
    report: DailyEodCadenceDiagnosis,
) -> None:
    if not isinstance(report, DailyEodCadenceDiagnosis):
        raise DailyEodCadenceDiagnosisError("cadence diagnosis contract is invalid")
    logical = asdict(report)
    logical.pop("logical_content_fingerprint")
    if (
        report.contract_version != CONTRACT_VERSION
        or not isinstance(report.status, CadenceDiagnosisStatus)
        or report.logical_content_fingerprint != _fingerprint(_jsonable(logical))
        or report.action_replayed
        or report.automatic_resolution_enabled
        or report.automatic_retry_enabled
        or report.automatic_recovery_enabled
        or report.external_request_count != 0
        or report.filesystem_write_count != 0
        or report.production_write_count != 0
    ):
        raise DailyEodCadenceDiagnosisError(
            "cadence diagnosis content or authority conflicts"
        )
    _verify_report_semantics(report)


def _verify_report_semantics(report: DailyEodCadenceDiagnosis) -> None:
    try:
        checked = datetime.fromisoformat(report.checked_at)
        date.fromisoformat(report.target_session)
    except ValueError as exc:
        raise DailyEodCadenceDiagnosisError(
            "cadence diagnosis identity is malformed"
        ) from exc
    _aware_utc(checked)
    has_reservation = _is_fingerprint(report.reservation_event_fingerprint)
    has_start = (
        report.nested_start_event_type in SUPPORTED_STARTS
        and _is_fingerprint(report.nested_start_event_fingerprint)
    )
    has_terminal = (
        isinstance(report.nested_terminal_event_type, str)
        and _is_fingerprint(report.nested_terminal_event_fingerprint)
    )
    has_wake = (
        has_reservation
        and type(report.cadence_sequence) is int
        and report.cadence_sequence > 0
        and isinstance(report.pipeline_action, str)
        and bool(report.pipeline_action)
    )
    start_policy = SUPPORTED_STARTS.get(str(report.nested_start_event_type))
    valid = {
        CadenceDiagnosisStatus.NO_PENDING_WAKE: (
            report.next_action == "none"
            and not has_reservation
            and report.cadence_sequence is None
            and report.pipeline_action is None
            and not has_start
            and not has_terminal
            and report.terminal_outcome_candidate is None
            and report.events_after_reservation == 0
        ),
        CadenceDiagnosisStatus.OUTCOME_UNKNOWN: (
            report.next_action == "operator_confirm_invocation_boundary"
            and has_wake
            and not has_start
            and not has_terminal
            and report.terminal_outcome_candidate is None
            and report.events_after_reservation == 0
        ),
        CadenceDiagnosisStatus.ACTION_RECOVERY_REQUIRED: (
            has_wake
            and has_start
            and not has_terminal
            and report.terminal_outcome_candidate is None
            and report.events_after_reservation == 1
            and start_policy is not None
            and report.next_action == start_policy[1]
        ),
        CadenceDiagnosisStatus.KNOWN_RESULT_REVIEW_READY: (
            report.next_action == "review_no_replay_cadence_resolution"
            and has_wake
            and has_start
            and has_terminal
            and start_policy is not None
            and report.nested_terminal_event_type
            in start_policy[0]
            and report.terminal_outcome_candidate
            in {
                "advanced_candidate",
                "no_change_candidate",
                "failed_candidate",
            }
            and report.events_after_reservation == 2
        ),
        CadenceDiagnosisStatus.BLOCKED: (
            report.next_action == "operator_diagnosis"
            and has_wake
            and report.events_after_reservation >= 1
        ),
    }[report.status]
    if not valid or not report.reason_codes:
        raise DailyEodCadenceDiagnosisError(
            "cadence diagnosis state fields conflict"
        )


def _blocked(
    common: dict[str, object],
    *,
    reasons: tuple[str, ...],
    started: DailyEodRunEvent | None = None,
    terminal: DailyEodRunEvent | None = None,
) -> DailyEodCadenceDiagnosis:
    return _result(
        **common,
        status=CadenceDiagnosisStatus.BLOCKED,
        next_action="operator_diagnosis",
        reasons=reasons,
        started=started,
        terminal=terminal,
    )


def _result(
    *,
    checked: datetime,
    target_session: date,
    status: CadenceDiagnosisStatus,
    next_action: str,
    reasons: tuple[str, ...],
    reservation: DailyEodRunEvent | None = None,
    cadence_sequence: int | None = None,
    pipeline_action: str | None = None,
    events_after_reservation: int = 0,
    started: DailyEodRunEvent | None = None,
    terminal: DailyEodRunEvent | None = None,
    terminal_outcome_candidate: str | None = None,
) -> DailyEodCadenceDiagnosis:
    logical = {
        "contract_version": CONTRACT_VERSION,
        "checked_at": checked.isoformat(),
        "target_session": target_session.isoformat(),
        "status": status.value,
        "next_action": next_action,
        "reason_codes": list(reasons),
        "reservation_event_fingerprint": (
            None if reservation is None else reservation.event_fingerprint
        ),
        "cadence_sequence": cadence_sequence,
        "pipeline_action": pipeline_action,
        "nested_start_event_type": None if started is None else started.event_type,
        "nested_start_event_fingerprint": (
            None if started is None else started.event_fingerprint
        ),
        "nested_terminal_event_type": (
            None if terminal is None else terminal.event_type
        ),
        "nested_terminal_event_fingerprint": (
            None if terminal is None else terminal.event_fingerprint
        ),
        "terminal_outcome_candidate": terminal_outcome_candidate,
        "events_after_reservation": events_after_reservation,
        "action_replayed": False,
        "automatic_resolution_enabled": False,
        "automatic_retry_enabled": False,
        "automatic_recovery_enabled": False,
        "external_request_count": 0,
        "filesystem_write_count": 0,
        "production_write_count": 0,
    }
    report = DailyEodCadenceDiagnosis(
        contract_version=CONTRACT_VERSION,
        checked_at=checked.isoformat(),
        target_session=target_session.isoformat(),
        status=status,
        next_action=next_action,
        reason_codes=reasons,
        reservation_event_fingerprint=logical["reservation_event_fingerprint"],
        cadence_sequence=cadence_sequence,
        pipeline_action=pipeline_action,
        nested_start_event_type=logical["nested_start_event_type"],
        nested_start_event_fingerprint=logical["nested_start_event_fingerprint"],
        nested_terminal_event_type=logical["nested_terminal_event_type"],
        nested_terminal_event_fingerprint=logical[
            "nested_terminal_event_fingerprint"
        ],
        terminal_outcome_candidate=terminal_outcome_candidate,
        events_after_reservation=events_after_reservation,
        action_replayed=False,
        automatic_resolution_enabled=False,
        automatic_retry_enabled=False,
        automatic_recovery_enabled=False,
        external_request_count=0,
        filesystem_write_count=0,
        production_write_count=0,
        logical_content_fingerprint=_fingerprint(logical),
    )
    verify_daily_eod_cadence_diagnosis(report)
    return report


def _verify_event_chain(
    events: tuple[DailyEodRunEvent, ...],
    *,
    target_session: date,
) -> None:
    previous: DailyEodRunEvent | None = None
    for sequence, event in enumerate(events, start=1):
        try:
            verify_daily_eod_run_event(event)
        except DailyEodRunJournalError as exc:
            raise DailyEodCadenceDiagnosisError(
                "daily run event is invalid"
            ) from exc
        if (
            event.sequence != sequence
            or event.target_session != target_session.isoformat()
            or (
                previous is not None
                and event.previous_event_fingerprint
                != previous.event_fingerprint
            )
        ):
            raise DailyEodCadenceDiagnosisError(
                "daily run event chain is inconsistent"
            )
        previous = event


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodCadenceDiagnosisError(
            "cadence diagnosis time must be timezone-aware"
        )
    return value.astimezone(UTC)


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
