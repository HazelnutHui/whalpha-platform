"""Append-only, hash-chained Dell custody for daily EOD action attempts."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterator, Mapping


JOURNAL_CONTRACT = "daily-eod-run-journal/1.7"
READABLE_JOURNAL_CONTRACTS = frozenset(
    {
        "daily-eod-run-journal/1.2",
        "daily-eod-run-journal/1.3",
        "daily-eod-run-journal/1.4",
        "daily-eod-run-journal/1.5",
        "daily-eod-run-journal/1.6",
        JOURNAL_CONTRACT,
    }
)
LOCK_FILE = ".daily-eod.lock"
EVENT_NAME = re.compile(r"event-(\d{6})\.json")
START_EVENT = "action_started"
ACTION_TERMINAL_EVENTS = frozenset(
    {
        "action_succeeded",
        "action_failed",
        "action_recovered_succeeded",
        "action_recovered_not_completed",
        "action_recovery_blocked",
    }
)
ACQUISITION_START_EVENT = "acquisition_started"
ACQUISITION_TERMINAL_EVENTS = frozenset(
    {
        "acquisition_not_ready",
        "acquisition_rate_limited",
        "acquisition_transient_failed",
        "acquisition_package_ready",
        "acquisition_permanent_failed",
        "acquisition_quality_failed",
        "acquisition_recovered_package_ready",
        "acquisition_recovered_not_completed",
        "acquisition_recovery_blocked",
    }
)
CANONICAL_APPLY_START_EVENT = "canonical_apply_started"
CANONICAL_APPLY_TERMINAL_EVENTS = frozenset(
    {
        "canonical_apply_succeeded",
        "canonical_apply_recovered_succeeded",
        "canonical_apply_recovered_not_completed",
        "canonical_apply_recovery_blocked",
    }
)
MARKET_INTELLIGENCE_APPLY_START_EVENT = "market_intelligence_apply_started"
MARKET_INTELLIGENCE_APPLY_TERMINAL_EVENTS = frozenset(
    {
        "market_intelligence_apply_succeeded",
        "market_intelligence_apply_recovered_succeeded",
        "market_intelligence_apply_recovered_not_completed",
        "market_intelligence_apply_recovery_blocked",
    }
)
MARKET_INTELLIGENCE_APPLY_CONTRACTS = frozenset(
    {"daily-eod-run-journal/1.4", "daily-eod-run-journal/1.5", JOURNAL_CONTRACT}
)
DASHBOARD_SNAPSHOT_APPLY_START_EVENT = "dashboard_snapshot_apply_started"
DASHBOARD_SNAPSHOT_APPLY_TERMINAL_EVENTS = frozenset(
    {
        "dashboard_snapshot_apply_succeeded",
        "dashboard_snapshot_apply_recovered_succeeded",
        "dashboard_snapshot_apply_recovered_not_completed",
        "dashboard_snapshot_apply_recovery_blocked",
    }
)
DASHBOARD_SNAPSHOT_APPLY_CONTRACTS = frozenset(
    {"daily-eod-run-journal/1.5", JOURNAL_CONTRACT}
)
OCI_DEPLOYMENT_START_EVENT = "oci_deployment_started"
OCI_DEPLOYMENT_TERMINAL_EVENTS = frozenset(
    {
        "oci_deployment_succeeded",
        "oci_deployment_recovered_succeeded",
        "oci_deployment_recovered_not_completed",
        "oci_deployment_recovery_blocked",
    }
)
OCI_DEPLOYMENT_CONTRACTS = frozenset(
    {"daily-eod-run-journal/1.6", JOURNAL_CONTRACT}
)
START_EVENTS = frozenset(
    {
        START_EVENT,
        ACQUISITION_START_EVENT,
        CANONICAL_APPLY_START_EVENT,
        MARKET_INTELLIGENCE_APPLY_START_EVENT,
        DASHBOARD_SNAPSHOT_APPLY_START_EVENT,
        OCI_DEPLOYMENT_START_EVENT,
    }
)
ACQUISITION_REVIEW_EVENT = "acquisition_operator_reviewed"
CADENCE_WAKE_RECORDED_EVENT = "cadence_wake_recorded"
ACQUISITION_REVIEW_CONTRACTS = frozenset(
    {
        "daily-eod-run-journal/1.3",
        "daily-eod-run-journal/1.4",
        "daily-eod-run-journal/1.5",
        JOURNAL_CONTRACT,
    }
)
TERMINAL_EVENTS = (
    ACTION_TERMINAL_EVENTS
    | ACQUISITION_TERMINAL_EVENTS
    | CANONICAL_APPLY_TERMINAL_EVENTS
    | MARKET_INTELLIGENCE_APPLY_TERMINAL_EVENTS
    | DASHBOARD_SNAPSHOT_APPLY_TERMINAL_EVENTS
    | OCI_DEPLOYMENT_TERMINAL_EVENTS
)
STANDALONE_EVENTS = frozenset(
    {ACQUISITION_REVIEW_EVENT, CADENCE_WAKE_RECORDED_EVENT}
)
EVENT_TYPES = START_EVENTS | TERMINAL_EVENTS | STANDALONE_EVENTS


class DailyEodRunJournalError(RuntimeError):
    """Raised when durable daily-run custody is unsafe or inconsistent."""


@dataclass(frozen=True, slots=True)
class DailyEodRunEvent:
    sequence: int
    event_type: str
    target_session: str
    observed_at: str
    attempt_id: str
    previous_event_fingerprint: str | None
    details: Mapping[str, Any]
    event_fingerprint: str
    contract_version: str = JOURNAL_CONTRACT

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "target_session": self.target_session,
            "observed_at": self.observed_at,
            "attempt_id": self.attempt_id,
            "previous_event_fingerprint": self.previous_event_fingerprint,
            "details": _jsonable(self.details),
            "event_fingerprint": self.event_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class LockedDailyEodRunJournal:
    root: Path
    session_dir: Path
    target_session: date
    previous_session_event_fingerprint: str | None

    def read_events(self) -> tuple[DailyEodRunEvent, ...]:
        return _read_events(
            self.session_dir,
            self.target_session,
            initial_previous_event_fingerprint=self.previous_session_event_fingerprint,
        )

    def append(
        self,
        *,
        event_type: str,
        attempt_id: str,
        details: Mapping[str, Any],
        observed_at: datetime | None = None,
    ) -> DailyEodRunEvent:
        events = self.read_events()
        _validate_next_event(events, event_type=event_type, attempt_id=attempt_id)
        event_time = _normalize_observed_at(observed_at or datetime.now(UTC))
        if events and event_time < datetime.fromisoformat(events[-1].observed_at):
            raise DailyEodRunJournalError("daily run event timestamp moved backwards")
        sequence = len(events) + 1
        base = {
            "contract_version": JOURNAL_CONTRACT,
            "sequence": sequence,
            "event_type": event_type,
            "target_session": self.target_session.isoformat(),
            "observed_at": event_time.isoformat(),
            "attempt_id": attempt_id,
            "previous_event_fingerprint": (
                self.previous_session_event_fingerprint
                if not events
                else events[-1].event_fingerprint
            ),
            "details": _jsonable(details),
        }
        event = DailyEodRunEvent(
            sequence=sequence,
            event_type=event_type,
            target_session=self.target_session.isoformat(),
            observed_at=str(base["observed_at"]),
            attempt_id=attempt_id,
            previous_event_fingerprint=base["previous_event_fingerprint"],
            details=base["details"],
            event_fingerprint=_fingerprint(base),
            contract_version=JOURNAL_CONTRACT,
        )
        path = self.session_dir / f"event-{sequence:06d}.json"
        _write_new(path, _canonical_bytes(event.as_dict()))
        _fsync_directory(self.session_dir)
        reread = self.read_events()
        if len(reread) != sequence or reread[-1] != event:
            raise DailyEodRunJournalError("daily run event did not formally reread")
        return event


@contextmanager
def locked_daily_eod_run_journal(
    *, run_root: Path, target_session: date
) -> Iterator[LockedDailyEodRunJournal]:
    """Acquire the one Dell-local daily-run lock and expose exact-session custody."""

    root = _safe_run_root(run_root)
    descriptor = _open_lock(root / LOCK_FILE)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DailyEodRunJournalError("daily EOD run lock is unavailable") from exc
        previous_session_event_fingerprint = _validate_run_root_entries(
            root, active_session=target_session
        )
        session_dir = root / f"session={target_session.isoformat()}"
        if not session_dir.exists():
            session_dir.mkdir(mode=0o700)
            session_dir.chmod(0o700)
            _fsync_directory(root)
        _safe_session_dir(root, session_dir, target_session)
        journal = LockedDailyEodRunJournal(
            root,
            session_dir,
            target_session,
            previous_session_event_fingerprint,
        )
        journal.read_events()
        yield journal
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def unresolved_started_event(
    events: tuple[DailyEodRunEvent, ...],
) -> DailyEodRunEvent | None:
    if events and events[-1].event_type in START_EVENTS:
        return events[-1]
    return None


def verify_daily_eod_run_event(event: DailyEodRunEvent) -> None:
    """Recompute one event's standalone schema and content identity."""

    if not isinstance(event, DailyEodRunEvent):
        raise DailyEodRunJournalError("daily run event contract is invalid")
    if _event_from_payload(event.as_dict()) != event:
        raise DailyEodRunJournalError("daily run event content differs")


def new_attempt_id(*, target_session: date, plan_fingerprint: str, sequence: int) -> str:
    if not _is_fingerprint(plan_fingerprint) or sequence < 1:
        raise DailyEodRunJournalError("daily attempt identity input is invalid")
    return _fingerprint(
        {
            "contract_version": JOURNAL_CONTRACT,
            "target_session": target_session.isoformat(),
            "plan_fingerprint": plan_fingerprint,
            "start_event_sequence": sequence,
        }
    )


def _read_events(
    session_dir: Path,
    target_session: date,
    *,
    initial_previous_event_fingerprint: str | None = None,
) -> tuple[DailyEodRunEvent, ...]:
    names = tuple(sorted(item.name for item in session_dir.iterdir()))
    expected = tuple(f"event-{index:06d}.json" for index in range(1, len(names) + 1))
    if names != expected:
        raise DailyEodRunJournalError("daily run journal event sequence is incomplete or has extras")
    events: list[DailyEodRunEvent] = []
    for index, name in enumerate(names, start=1):
        if EVENT_NAME.fullmatch(name) is None:
            raise DailyEodRunJournalError("daily run journal file name is invalid")
        path = session_dir / name
        metadata = path.lstat()
        if (
            path.is_symlink()
            or not path.is_file()
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o400
        ):
            raise DailyEodRunJournalError("daily run journal event custody mismatch")
        payload = _read_canonical_json(path)
        event = _event_from_payload(payload)
        if event.sequence != index or event.target_session != target_session.isoformat():
            raise DailyEodRunJournalError("daily run journal event identity mismatch")
        expected_previous = (
            initial_previous_event_fingerprint
            if not events
            else events[-1].event_fingerprint
        )
        if event.previous_event_fingerprint != expected_previous:
            raise DailyEodRunJournalError("daily run journal hash chain mismatch")
        events.append(event)
    _validate_event_state_machine(tuple(events))
    return tuple(events)


def _event_from_payload(payload: Mapping[str, Any]) -> DailyEodRunEvent:
    expected_keys = {
        "contract_version",
        "sequence",
        "event_type",
        "target_session",
        "observed_at",
        "attempt_id",
        "previous_event_fingerprint",
        "details",
        "event_fingerprint",
    }
    contract_version = payload.get("contract_version")
    if (
        set(payload) != expected_keys
        or contract_version not in READABLE_JOURNAL_CONTRACTS
    ):
        raise DailyEodRunJournalError("daily run journal event contract mismatch")
    logical = {key: value for key, value in payload.items() if key != "event_fingerprint"}
    fingerprint = payload.get("event_fingerprint")
    if not _is_fingerprint(fingerprint) or _fingerprint(logical) != fingerprint:
        raise DailyEodRunJournalError("daily run journal event fingerprint mismatch")
    try:
        observed_at = datetime.fromisoformat(str(payload["observed_at"]))
        target_session = date.fromisoformat(str(payload["target_session"]))
    except ValueError as exc:
        raise DailyEodRunJournalError("daily run journal event date is malformed") from exc
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise DailyEodRunJournalError("daily run journal timestamp must be timezone-aware")
    if observed_at.utcoffset().total_seconds() != 0:
        raise DailyEodRunJournalError("daily run journal timestamp must be UTC")
    event_type = payload.get("event_type")
    attempt_id = payload.get("attempt_id")
    previous = payload.get("previous_event_fingerprint")
    details = payload.get("details")
    sequence = payload.get("sequence")
    if (
        event_type not in EVENT_TYPES
        or not _is_fingerprint(attempt_id)
        or (previous is not None and not _is_fingerprint(previous))
        or not isinstance(details, dict)
        or type(sequence) is not int
        or sequence < 1
    ):
        raise DailyEodRunJournalError("daily run journal event fields are malformed")
    if (
        event_type
        in {MARKET_INTELLIGENCE_APPLY_START_EVENT}
        | MARKET_INTELLIGENCE_APPLY_TERMINAL_EVENTS
        and contract_version not in MARKET_INTELLIGENCE_APPLY_CONTRACTS
    ):
        raise DailyEodRunJournalError(
            "MI Apply event predates its journal contract"
        )
    if (
        event_type
        in {DASHBOARD_SNAPSHOT_APPLY_START_EVENT}
        | DASHBOARD_SNAPSHOT_APPLY_TERMINAL_EVENTS
        and contract_version not in DASHBOARD_SNAPSHOT_APPLY_CONTRACTS
    ):
        raise DailyEodRunJournalError(
            "Snapshot Apply event predates its journal contract"
        )
    if (
        event_type in {OCI_DEPLOYMENT_START_EVENT} | OCI_DEPLOYMENT_TERMINAL_EVENTS
        and contract_version not in OCI_DEPLOYMENT_CONTRACTS
    ):
        raise DailyEodRunJournalError("OCI deployment event predates its journal contract")
    if (
        event_type == CADENCE_WAKE_RECORDED_EVENT
        and contract_version != JOURNAL_CONTRACT
    ):
        raise DailyEodRunJournalError("cadence evidence predates its journal contract")
    return DailyEodRunEvent(
        sequence=sequence,
        event_type=str(event_type),
        target_session=target_session.isoformat(),
        observed_at=observed_at.astimezone(UTC).isoformat(),
        attempt_id=str(attempt_id),
        previous_event_fingerprint=previous,
        details=details,
        event_fingerprint=str(fingerprint),
        contract_version=str(contract_version),
    )


def _validate_event_state_machine(events: tuple[DailyEodRunEvent, ...]) -> None:
    pending: DailyEodRunEvent | None = None
    for event in events:
        if event.event_type in START_EVENTS:
            if pending is not None:
                raise DailyEodRunJournalError("daily run journal has overlapping attempts")
            pending = event
        elif event.event_type in STANDALONE_EVENTS:
            if (
                pending is not None
                or (
                    event.event_type == ACQUISITION_REVIEW_EVENT
                    and event.contract_version not in ACQUISITION_REVIEW_CONTRACTS
                )
            ):
                raise DailyEodRunJournalError(
                    "daily run standalone evidence is not safely placed"
                )
        else:
            if (
                pending is None
                or event.attempt_id != pending.attempt_id
                or not _terminal_matches_start(pending.event_type, event.event_type)
            ):
                raise DailyEodRunJournalError("daily run terminal event has no matching start")
            pending = None


def _validate_next_event(
    events: tuple[DailyEodRunEvent, ...], *, event_type: str, attempt_id: str
) -> None:
    if event_type not in EVENT_TYPES or not _is_fingerprint(attempt_id):
        raise DailyEodRunJournalError("daily run next event is invalid")
    pending = unresolved_started_event(events)
    if event_type in STANDALONE_EVENTS:
        if pending is not None:
            raise DailyEodRunJournalError(
                "daily run standalone evidence cannot overlap an attempt"
            )
        return
    if event_type in START_EVENTS:
        if pending is not None:
            raise DailyEodRunJournalError("daily run has an unresolved started action")
    elif (
        pending is None
        or pending.attempt_id != attempt_id
        or not _terminal_matches_start(pending.event_type, event_type)
    ):
        raise DailyEodRunJournalError("daily run terminal event does not match the pending action")


def _terminal_matches_start(start_type: str, terminal_type: str) -> bool:
    if start_type == START_EVENT:
        return terminal_type in ACTION_TERMINAL_EVENTS
    if start_type == ACQUISITION_START_EVENT:
        return terminal_type in ACQUISITION_TERMINAL_EVENTS
    if start_type == CANONICAL_APPLY_START_EVENT:
        return terminal_type in CANONICAL_APPLY_TERMINAL_EVENTS
    if start_type == MARKET_INTELLIGENCE_APPLY_START_EVENT:
        return terminal_type in MARKET_INTELLIGENCE_APPLY_TERMINAL_EVENTS
    if start_type == DASHBOARD_SNAPSHOT_APPLY_START_EVENT:
        return terminal_type in DASHBOARD_SNAPSHOT_APPLY_TERMINAL_EVENTS
    if start_type == OCI_DEPLOYMENT_START_EVENT:
        return terminal_type in OCI_DEPLOYMENT_TERMINAL_EVENTS
    return False


def _safe_run_root(run_root: Path) -> Path:
    if not run_root.is_absolute() or run_root.name in {"", ".", ".."}:
        raise DailyEodRunJournalError("daily run root must be absolute")
    _reject_symlink_chain(run_root)
    if not run_root.exists():
        raise DailyEodRunJournalError("daily run root must be provisioned explicitly")
    root = run_root.resolve(strict=True)
    metadata = root.stat()
    if (
        not root.is_dir()
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise DailyEodRunJournalError("daily run root custody mismatch")
    return root


def _validate_run_root_entries(
    root: Path, *, active_session: date
) -> str | None:
    session_paths: list[tuple[date, Path]] = []
    for path in root.iterdir():
        if path.name == LOCK_FILE:
            continue
        if not path.name.startswith("session="):
            raise DailyEodRunJournalError("daily run root contains an unknown entry")
        try:
            session = date.fromisoformat(path.name.removeprefix("session="))
        except ValueError as exc:
            raise DailyEodRunJournalError("daily run session directory name is invalid") from exc
        session_paths.append((session, path))
    previous_event_fingerprint: str | None = None
    active_chain_start: str | None = None
    for session, path in sorted(session_paths):
        if session > active_session:
            raise DailyEodRunJournalError("daily run cannot append before a later session")
        _safe_session_dir(root, path, session)
        if session == active_session:
            active_chain_start = previous_event_fingerprint
        events = _read_events(
            path,
            session,
            initial_previous_event_fingerprint=previous_event_fingerprint,
        )
        if events:
            previous_event_fingerprint = events[-1].event_fingerprint
        if session != active_session and unresolved_started_event(events) is not None:
            raise DailyEodRunJournalError("an earlier daily session has an unresolved action")
    return (
        active_chain_start
        if any(session == active_session for session, _ in session_paths)
        else previous_event_fingerprint
    )


def _safe_session_dir(root: Path, path: Path, target_session: date) -> Path:
    if path.name != f"session={target_session.isoformat()}" or path.is_symlink():
        raise DailyEodRunJournalError("daily run session directory is invalid")
    resolved = path.resolve(strict=True)
    metadata = resolved.stat()
    if (
        not resolved.is_dir()
        or resolved.parent != root
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise DailyEodRunJournalError("daily run session directory custody mismatch")
    return resolved


def _open_lock(path: Path) -> int:
    if path.is_symlink():
        raise DailyEodRunJournalError("daily run lock symlink is rejected")
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise DailyEodRunJournalError("daily run lock cannot be opened") from exc
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        os.close(descriptor)
        raise DailyEodRunJournalError("daily run lock custody mismatch")
    return descriptor


def _reject_symlink_chain(path: Path) -> None:
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        if os.path.lexists(current) and current.is_symlink():
            raise DailyEodRunJournalError("daily run path contains a symlink")


def _write_new(path: Path, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o400)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise DailyEodRunJournalError("daily run journal event already exists") from exc
    path.chmod(0o400)


def _read_canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DailyEodRunJournalError("daily run journal event is malformed") from exc
    if not isinstance(payload, dict) or _canonical_bytes(payload) != raw:
        raise DailyEodRunJournalError("daily run journal event is not canonical")
    return payload


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _normalize_observed_at(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodRunJournalError("daily run event timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise DailyEodRunJournalError("daily run journal details are not JSON-safe")
