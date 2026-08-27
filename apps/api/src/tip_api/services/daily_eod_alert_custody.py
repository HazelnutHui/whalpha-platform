"""Immutable, no-duplicate custody for one explicit daily alert delivery."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Callable, Mapping

from tip_api.services.daily_eod_alerting import (
    DailyEodAlertIntent,
    validate_daily_eod_alert_intent,
)


CONTRACT_VERSION = "daily-eod-alert-delivery-custody/1.0"
JOURNAL_CONTRACT = "daily-eod-alert-delivery-journal/1.0"
LOCK_FILE = ".daily-eod-alert.lock"
ALERT_DIRECTORY = re.compile(r"alert=([0-9a-f]{64})")
EVENT_FILE = re.compile(r"event-(\d{6})\.json")
CHANNEL = re.compile(r"[a-z][a-z0-9_-]{1,31}")
START_EVENT = "delivery_started"
DELIVERED_EVENT = "delivery_delivered"
FAILED_EVENT = "delivery_failed"
EVENT_TYPES = frozenset({START_EVENT, DELIVERED_EVENT, FAILED_EVENT})
MAXIMUM_EVENT_BYTES = 64 * 1024


class DailyEodAlertCustodyError(RuntimeError):
    """Raised when alert delivery cannot preserve at-most-once custody."""


@dataclass(frozen=True, slots=True)
class DailyEodAlertCustodyConfig:
    alert_root: Path
    repository_root: Path
    data_root: Path
    run_root: Path
    channel: str


@dataclass(frozen=True, slots=True)
class AlertDeliveryContext:
    intent: DailyEodAlertIntent
    attempt_id: str
    channel: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class AlertDeliveryEvidence:
    channel: str
    deduplication_key: str
    outcome: str
    external_request_count: int
    delivery_reference_fingerprint: str | None
    reason_code: str


@dataclass(frozen=True, slots=True)
class AlertDeliveryEvent:
    sequence: int
    event_type: str
    deduplication_key: str
    target_session: str
    observed_at: str
    attempt_id: str
    previous_event_fingerprint: str | None
    details: Mapping[str, object]
    event_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": JOURNAL_CONTRACT,
            **asdict(self),
        }


@dataclass(frozen=True, slots=True)
class AlertDeliveryCustodyResult:
    outcome: str
    channel: str
    deduplication_key: str
    attempt_id: str
    start_event_fingerprint: str
    terminal_event_fingerprint: str
    delivery_attempted_by_invocation: bool
    notification_delivered: bool
    external_request_count: int
    custody_event_write_count: int
    production_write_count: int
    reason_code: str
    contract_version: str = CONTRACT_VERSION

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


Clock = Callable[[], datetime]
DeliveryCapability = Callable[[AlertDeliveryContext], AlertDeliveryEvidence]


def deliver_daily_eod_alert(
    *,
    config: DailyEodAlertCustodyConfig,
    intent: DailyEodAlertIntent,
    capability: DeliveryCapability,
    clock: Clock = lambda: datetime.now(UTC),
) -> AlertDeliveryCustodyResult:
    """Attempt one exact delivery; ambiguous interruption is never replayed."""

    validate_daily_eod_alert_intent(intent)
    root = _validate_config(config)
    if not callable(capability):
        raise DailyEodAlertCustodyError("alert delivery capability is absent")
    _validate_root_entries(root)
    descriptor = _open_lock(root / LOCK_FILE)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DailyEodAlertCustodyError(
                "alert delivery lock is unavailable"
            ) from exc
        _validate_root_entries(root)
        directory = _alert_directory(root, intent.deduplication_key)
        events = _read_events(directory, intent)
        if events:
            return _existing_result(config, intent, events)

        observed = _aware_utc(clock())
        attempt_id = _fingerprint(
            {
                "contract_version": CONTRACT_VERSION,
                "deduplication_key": intent.deduplication_key,
                "intent_fingerprint": intent.logical_content_fingerprint,
                "channel": config.channel,
            }
        )
        started = _append_event(
            directory=directory,
            intent=intent,
            existing=(),
            event_type=START_EVENT,
            attempt_id=attempt_id,
            observed_at=observed,
            details={
                "channel": config.channel,
                "intent_fingerprint": intent.logical_content_fingerprint,
                "source_fingerprint": intent.source_fingerprint,
                "delivery_attempted_after_event": True,
            },
        )
        evidence = capability(
            AlertDeliveryContext(
                intent=intent,
                attempt_id=attempt_id,
                channel=config.channel,
                idempotency_key=intent.deduplication_key,
            )
        )
        _validate_evidence(config, intent, evidence)
        terminal_type = (
            DELIVERED_EVENT if evidence.outcome == "delivered" else FAILED_EVENT
        )
        terminal = _append_event(
            directory=directory,
            intent=intent,
            existing=(started,),
            event_type=terminal_type,
            attempt_id=attempt_id,
            observed_at=_aware_utc(clock()),
            details={
                "channel": evidence.channel,
                "outcome": evidence.outcome,
                "external_request_count": evidence.external_request_count,
                "delivery_reference_fingerprint": (
                    evidence.delivery_reference_fingerprint
                ),
                "reason_code": evidence.reason_code,
            },
        )
        delivered = evidence.outcome == "delivered"
        return AlertDeliveryCustodyResult(
            outcome=evidence.outcome,
            channel=config.channel,
            deduplication_key=intent.deduplication_key,
            attempt_id=attempt_id,
            start_event_fingerprint=started.event_fingerprint,
            terminal_event_fingerprint=terminal.event_fingerprint,
            delivery_attempted_by_invocation=True,
            notification_delivered=delivered,
            external_request_count=evidence.external_request_count,
            custody_event_write_count=2,
            production_write_count=0,
            reason_code=evidence.reason_code,
        )
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _existing_result(
    config: DailyEodAlertCustodyConfig,
    intent: DailyEodAlertIntent,
    events: tuple[AlertDeliveryEvent, ...],
) -> AlertDeliveryCustodyResult:
    started = events[0]
    if started.details.get("channel") != config.channel:
        raise DailyEodAlertCustodyError("alert delivery channel changed")
    if len(events) == 1:
        raise DailyEodAlertCustodyError(
            "alert delivery outcome is unknown; automatic resend is prohibited"
        )
    terminal = events[1]
    evidence = _terminal_evidence(terminal)
    _validate_evidence(config, intent, evidence)
    if terminal.event_type == FAILED_EVENT:
        raise DailyEodAlertCustodyError(
            "prior alert delivery failed; operator review is required"
        )
    if terminal.event_type != DELIVERED_EVENT:
        raise DailyEodAlertCustodyError("alert delivery journal is inconsistent")
    return AlertDeliveryCustodyResult(
        outcome="already_delivered",
        channel=config.channel,
        deduplication_key=intent.deduplication_key,
        attempt_id=started.attempt_id,
        start_event_fingerprint=started.event_fingerprint,
        terminal_event_fingerprint=terminal.event_fingerprint,
        delivery_attempted_by_invocation=False,
        notification_delivered=True,
        external_request_count=0,
        custody_event_write_count=0,
        production_write_count=0,
        reason_code="matching_alert_was_already_delivered",
    )


def _terminal_evidence(event: AlertDeliveryEvent) -> AlertDeliveryEvidence:
    try:
        channel = event.details["channel"]
        outcome = event.details["outcome"]
        request_count = event.details["external_request_count"]
        reference = event.details["delivery_reference_fingerprint"]
        reason_code = event.details["reason_code"]
    except KeyError as exc:
        raise DailyEodAlertCustodyError(
            "alert delivery terminal evidence is incomplete"
        ) from exc
    if (
        not isinstance(channel, str)
        or not isinstance(outcome, str)
        or type(request_count) is not int
        or (reference is not None and not isinstance(reference, str))
        or not isinstance(reason_code, str)
        or (
            event.event_type == DELIVERED_EVENT
            and outcome != "delivered"
        )
        or (event.event_type == FAILED_EVENT and outcome != "failed")
    ):
        raise DailyEodAlertCustodyError(
            "alert delivery terminal evidence is malformed"
        )
    return AlertDeliveryEvidence(
        channel=channel,
        deduplication_key=event.deduplication_key,
        outcome=outcome,
        external_request_count=request_count,
        delivery_reference_fingerprint=reference,
        reason_code=reason_code,
    )


def _validate_evidence(
    config: DailyEodAlertCustodyConfig,
    intent: DailyEodAlertIntent,
    evidence: AlertDeliveryEvidence,
) -> None:
    delivered = (
        isinstance(evidence, AlertDeliveryEvidence)
        and evidence.outcome == "delivered"
    )
    if (
        not isinstance(evidence, AlertDeliveryEvidence)
        or evidence.channel != config.channel
        or evidence.deduplication_key != intent.deduplication_key
        or evidence.outcome not in {"delivered", "failed"}
        or not 0 <= evidence.external_request_count <= 1
        or (delivered and evidence.external_request_count != 1)
        or (
            delivered
            and not _is_fingerprint(evidence.delivery_reference_fingerprint)
        )
        or (
            not delivered
            and evidence.delivery_reference_fingerprint is not None
            and not _is_fingerprint(evidence.delivery_reference_fingerprint)
        )
        or not isinstance(evidence.reason_code, str)
        or not evidence.reason_code
    ):
        raise DailyEodAlertCustodyError("alert delivery evidence is invalid")


def _validate_config(config: DailyEodAlertCustodyConfig) -> Path:
    if not isinstance(config, DailyEodAlertCustodyConfig):
        raise DailyEodAlertCustodyError("alert custody config is invalid")
    roots = (
        config.repository_root,
        config.data_root,
        config.run_root,
    )
    if (
        not config.alert_root.is_absolute()
        or any(not root.is_absolute() for root in roots)
        or any(
            _is_within(config.alert_root, root)
            or _is_within(root, config.alert_root)
            for root in roots
        )
        or not CHANNEL.fullmatch(config.channel)
    ):
        raise DailyEodAlertCustodyError("alert custody boundary is invalid")
    try:
        metadata = config.alert_root.lstat()
    except OSError as exc:
        raise DailyEodAlertCustodyError(
            "pre-provisioned alert root is unavailable"
        ) from exc
    if (
        config.alert_root.resolve() != config.alert_root
        or stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise DailyEodAlertCustodyError("alert root custody is unsafe")
    return config.alert_root


def _open_lock(path: Path) -> int:
    flags = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
        metadata = os.fstat(descriptor)
    except OSError as exc:
        raise DailyEodAlertCustodyError("alert lock is unavailable") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        os.close(descriptor)
        raise DailyEodAlertCustodyError("alert lock custody is unsafe")
    return descriptor


def _validate_root_entries(root: Path) -> None:
    for item in root.iterdir():
        if item.name == LOCK_FILE:
            continue
        match = ALERT_DIRECTORY.fullmatch(item.name)
        try:
            metadata = item.lstat()
        except OSError as exc:
            raise DailyEodAlertCustodyError("alert root entry is unavailable") from exc
        if (
            match is None
            or stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or item.resolve().parent != root
        ):
            raise DailyEodAlertCustodyError("alert root contains an unsafe entry")


def _alert_directory(root: Path, deduplication_key: str) -> Path:
    if not _is_fingerprint(deduplication_key):
        raise DailyEodAlertCustodyError("alert deduplication key is malformed")
    directory = root / f"alert={deduplication_key}"
    if not directory.exists():
        try:
            directory.mkdir(mode=0o700)
            _fsync_directory(root)
        except OSError as exc:
            raise DailyEodAlertCustodyError(
                "alert journal directory could not be created"
            ) from exc
    metadata = directory.lstat()
    if (
        directory.resolve().parent != root
        or stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise DailyEodAlertCustodyError("alert journal directory is unsafe")
    return directory


def _read_events(
    directory: Path,
    intent: DailyEodAlertIntent,
) -> tuple[AlertDeliveryEvent, ...]:
    names = tuple(sorted(item.name for item in directory.iterdir()))
    expected = tuple(
        f"event-{index:06d}.json" for index in range(1, len(names) + 1)
    )
    if names != expected or len(names) > 2:
        raise DailyEodAlertCustodyError("alert journal sequence is invalid")
    events: list[AlertDeliveryEvent] = []
    for sequence, name in enumerate(names, start=1):
        if EVENT_FILE.fullmatch(name) is None:
            raise DailyEodAlertCustodyError("alert journal entry is unexpected")
        path = directory / name
        metadata = path.lstat()
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or not 0 < metadata.st_size <= MAXIMUM_EVENT_BYTES
        ):
            raise DailyEodAlertCustodyError("alert journal event custody is unsafe")
        try:
            raw = path.read_bytes()
            value = json.loads(raw)
            event = _event_from_value(value)
        except (
            KeyError,
            OSError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as exc:
            raise DailyEodAlertCustodyError("alert journal event is invalid") from exc
        if raw != _canonical_bytes(event.as_dict()):
            raise DailyEodAlertCustodyError("alert journal event is not canonical")
        previous = None if not events else events[-1].event_fingerprint
        if (
            event.sequence != sequence
            or event.deduplication_key != intent.deduplication_key
            or event.target_session != intent.target_session
            or event.previous_event_fingerprint != previous
            or event.event_type not in EVENT_TYPES
            or event.event_fingerprint != _event_fingerprint(event)
        ):
            raise DailyEodAlertCustodyError("alert journal hash chain is invalid")
        try:
            _aware_utc(datetime.fromisoformat(event.observed_at))
        except (TypeError, ValueError) as exc:
            raise DailyEodAlertCustodyError(
                "alert journal timestamp is invalid"
            ) from exc
        if sequence == 1 and event.event_type != START_EVENT:
            raise DailyEodAlertCustodyError("alert journal start event is invalid")
        if sequence == 2 and event.event_type not in {DELIVERED_EVENT, FAILED_EVENT}:
            raise DailyEodAlertCustodyError("alert journal terminal event is invalid")
        if events and event.attempt_id != events[0].attempt_id:
            raise DailyEodAlertCustodyError("alert journal attempt identity changed")
        events.append(event)
    if events:
        started = events[0]
        if (
            started.details.get("channel") is None
            or started.details.get("intent_fingerprint")
            != intent.logical_content_fingerprint
            or started.details.get("source_fingerprint") != intent.source_fingerprint
        ):
            raise DailyEodAlertCustodyError("alert journal differs from intent")
    return tuple(events)


def _append_event(
    *,
    directory: Path,
    intent: DailyEodAlertIntent,
    existing: tuple[AlertDeliveryEvent, ...],
    event_type: str,
    attempt_id: str,
    observed_at: datetime,
    details: Mapping[str, object],
) -> AlertDeliveryEvent:
    if event_type not in EVENT_TYPES or not _is_fingerprint(attempt_id):
        raise DailyEodAlertCustodyError("alert event identity is invalid")
    if existing and observed_at < datetime.fromisoformat(existing[-1].observed_at):
        raise DailyEodAlertCustodyError("alert event timestamp moved backwards")
    base = {
        "contract_version": JOURNAL_CONTRACT,
        "sequence": len(existing) + 1,
        "event_type": event_type,
        "deduplication_key": intent.deduplication_key,
        "target_session": intent.target_session,
        "observed_at": observed_at.isoformat(),
        "attempt_id": attempt_id,
        "previous_event_fingerprint": (
            None if not existing else existing[-1].event_fingerprint
        ),
        "details": dict(details),
    }
    event = AlertDeliveryEvent(
        sequence=base["sequence"],  # type: ignore[arg-type]
        event_type=event_type,
        deduplication_key=intent.deduplication_key,
        target_session=intent.target_session,
        observed_at=base["observed_at"],  # type: ignore[arg-type]
        attempt_id=attempt_id,
        previous_event_fingerprint=base["previous_event_fingerprint"],  # type: ignore[arg-type]
        details=base["details"],  # type: ignore[arg-type]
        event_fingerprint=_fingerprint(base),
    )
    path = directory / f"event-{event.sequence:06d}.json"
    _write_new(path, _canonical_bytes(event.as_dict()))
    _fsync_directory(directory)
    reread = _read_events(directory, intent)
    if len(reread) != event.sequence or reread[-1] != event:
        raise DailyEodAlertCustodyError("alert journal event failed formal reread")
    return event


def _event_from_value(value: object) -> AlertDeliveryEvent:
    if (
        not isinstance(value, dict)
        or value.get("contract_version") != JOURNAL_CONTRACT
    ):
        raise ValueError("event contract mismatch")
    details = value.get("details")
    if not isinstance(details, dict):
        raise ValueError("event details malformed")
    return AlertDeliveryEvent(
        sequence=value["sequence"],
        event_type=value["event_type"],
        deduplication_key=value["deduplication_key"],
        target_session=value["target_session"],
        observed_at=value["observed_at"],
        attempt_id=value["attempt_id"],
        previous_event_fingerprint=value["previous_event_fingerprint"],
        details=details,
        event_fingerprint=value["event_fingerprint"],
    )


def _event_fingerprint(event: AlertDeliveryEvent) -> str:
    value = event.as_dict()
    value.pop("event_fingerprint")
    return _fingerprint(value)


def _write_new(path: Path, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o400)
        try:
            remaining = memoryview(raw)
            while remaining:
                written = os.write(descriptor, remaining)
                if written < 1:
                    raise OSError("short alert journal write")
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise DailyEodAlertCustodyError("alert journal event write failed") from exc


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _aware_utc(value: datetime) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise DailyEodAlertCustodyError("alert custody time must be timezone-aware")
    return value.astimezone(UTC)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=lambda item: (
                item.value if isinstance(item, StrEnum) else str(item)
            ),
        )
        + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


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
