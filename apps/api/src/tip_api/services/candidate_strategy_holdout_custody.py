"""Durable single-consumption custody for one locked research holdout."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Literal, Mapping

from tip_api.contracts.analytics.v1 import (
    ResearchStatisticsStage,
    StrongLeaderPullbackStatisticsReportV1,
)


CONTRACT_VERSION = "candidate-strategy-holdout-custody/1.0"
JOURNAL_VERSION = "candidate-strategy-holdout-custody-journal/1.0"
LOCK_FILE = ".research-holdout.lock"
EVENT_FILE = re.compile(r"event-(\d{6})\.json")
MAXIMUM_EVENT_BYTES = 64 * 1024


class CandidateStrategyHoldoutCustodyError(RuntimeError):
    """Raised when one-use holdout custody cannot fail closed."""


@dataclass(frozen=True, slots=True)
class HoldoutCustodyConfig:
    holdout_root: Path
    repository_root: Path
    data_root: Path


@dataclass(frozen=True, slots=True)
class HoldoutEvaluationContext:
    custody_id: str
    validation_report_fingerprint: str
    mechanics_batch_fingerprint: str
    parameter_lock_fingerprint: str
    parameter_combination_id: str


@dataclass(frozen=True, slots=True)
class HoldoutEvaluationEvidence:
    custody_id: str
    validation_report_fingerprint: str
    mechanics_batch_fingerprint: str
    parameter_lock_fingerprint: str
    parameter_combination_id: str
    result_report_fingerprint: str | None
    outcome: Literal["completed", "failed"]
    reason_code: str


@dataclass(frozen=True, slots=True)
class HoldoutCustodyEvent:
    sequence: int
    event_type: Literal["holdout_reserved", "holdout_completed", "holdout_failed"]
    observed_at: str
    custody_id: str
    previous_event_fingerprint: str | None
    details: Mapping[str, object]
    event_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return {"contract_version": JOURNAL_VERSION, **asdict(self)}


@dataclass(frozen=True, slots=True)
class HoldoutCustodyResult:
    outcome: str
    custody_id: str
    validation_report_fingerprint: str
    parameter_lock_fingerprint: str
    parameter_combination_id: str
    result_report_fingerprint: str | None
    holdout_evaluated_by_invocation: bool
    custody_event_write_count: int
    production_write_count: Literal[0] = 0
    external_request_count: Literal[0] = 0
    stage_transition_authorized: Literal[False] = False
    performance_claim_authorized: Literal[False] = False
    contract_version: str = CONTRACT_VERSION


Clock = Callable[[], datetime]
HoldoutCapability = Callable[[HoldoutEvaluationContext], HoldoutEvaluationEvidence]


def consume_locked_holdout_once(
    *,
    config: HoldoutCustodyConfig,
    validation_report: StrongLeaderPullbackStatisticsReportV1,
    capability: HoldoutCapability,
    clock: Clock = lambda: datetime.now(UTC),
) -> HoldoutCustodyResult:
    """Reserve before evaluation; any interruption permanently blocks replay."""

    context = _context(validation_report)
    root = _validate_config(config)
    if not callable(capability):
        raise CandidateStrategyHoldoutCustodyError("holdout capability is absent")
    descriptor = _open_lock(root / LOCK_FILE)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CandidateStrategyHoldoutCustodyError(
                "holdout custody lock is unavailable"
            ) from exc
        _validate_root_entries(root)
        directory = root / f"holdout={context.custody_id}"
        events = _read_events(directory, context)
        if events:
            return _existing_result(context, events)
        reserved = _append_event(
            directory=directory,
            context=context,
            existing=(),
            event_type="holdout_reserved",
            observed_at=_aware_utc(clock()),
            details={
                "validation_report_fingerprint": context.validation_report_fingerprint,
                "mechanics_batch_fingerprint": context.mechanics_batch_fingerprint,
                "parameter_lock_fingerprint": context.parameter_lock_fingerprint,
                "parameter_combination_id": context.parameter_combination_id,
                "evaluation_permitted_after_reservation": True,
            },
        )
        evidence = capability(context)
        _validate_evidence(context, evidence)
        terminal = _append_event(
            directory=directory,
            context=context,
            existing=(reserved,),
            event_type=(
                "holdout_completed" if evidence.outcome == "completed" else "holdout_failed"
            ),
            observed_at=_aware_utc(clock()),
            details={
                "result_report_fingerprint": evidence.result_report_fingerprint,
                "outcome": evidence.outcome,
                "reason_code": evidence.reason_code,
            },
        )
        return HoldoutCustodyResult(
            outcome=evidence.outcome,
            custody_id=context.custody_id,
            validation_report_fingerprint=context.validation_report_fingerprint,
            parameter_lock_fingerprint=context.parameter_lock_fingerprint,
            parameter_combination_id=context.parameter_combination_id,
            result_report_fingerprint=evidence.result_report_fingerprint,
            holdout_evaluated_by_invocation=True,
            custody_event_write_count=2,
        )
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _context(report: StrongLeaderPullbackStatisticsReportV1) -> HoldoutEvaluationContext:
    if (
        report.stage is not ResearchStatisticsStage.VALIDATION
        or report.parameter_lock is None
        or report.selected_parameter_combination_id is None
        or not report.all_required_gates_passed
        or report.holdout_consumed
    ):
        raise CandidateStrategyHoldoutCustodyError(
            "holdout custody requires one passed, unconsumed validation report"
        )
    payload = {
        "contract_version": CONTRACT_VERSION,
        "experiment_fingerprint": report.experiment_fingerprint,
        "mechanics_batch_fingerprint": report.mechanics_batch_fingerprint,
        "validation_report_fingerprint": report.logical_fingerprint,
        "parameter_lock_fingerprint": report.parameter_lock.logical_fingerprint,
        "parameter_combination_id": report.selected_parameter_combination_id,
    }
    return HoldoutEvaluationContext(
        custody_id=_fingerprint(payload),
        validation_report_fingerprint=report.logical_fingerprint,
        mechanics_batch_fingerprint=report.mechanics_batch_fingerprint,
        parameter_lock_fingerprint=report.parameter_lock.logical_fingerprint,
        parameter_combination_id=report.selected_parameter_combination_id,
    )


def _existing_result(
    context: HoldoutEvaluationContext,
    events: tuple[HoldoutCustodyEvent, ...],
) -> HoldoutCustodyResult:
    if len(events) == 1:
        raise CandidateStrategyHoldoutCustodyError(
            "holdout outcome is unknown after reservation; replay is prohibited"
        )
    terminal = events[-1]
    if terminal.event_type == "holdout_failed":
        raise CandidateStrategyHoldoutCustodyError(
            "prior holdout evaluation failed; replay is prohibited"
        )
    return HoldoutCustodyResult(
        outcome="already_consumed",
        custody_id=context.custody_id,
        validation_report_fingerprint=context.validation_report_fingerprint,
        parameter_lock_fingerprint=context.parameter_lock_fingerprint,
        parameter_combination_id=context.parameter_combination_id,
        result_report_fingerprint=str(terminal.details["result_report_fingerprint"]),
        holdout_evaluated_by_invocation=False,
        custody_event_write_count=0,
    )


def _validate_evidence(
    context: HoldoutEvaluationContext,
    evidence: HoldoutEvaluationEvidence,
) -> None:
    if not isinstance(evidence, HoldoutEvaluationEvidence):
        raise CandidateStrategyHoldoutCustodyError("holdout evidence is invalid")
    expected = asdict(context)
    actual = {key: getattr(evidence, key) for key in expected}
    if actual != expected:
        raise CandidateStrategyHoldoutCustodyError("holdout evidence binding differs")
    if evidence.outcome not in {"completed", "failed"}:
        raise CandidateStrategyHoldoutCustodyError("holdout outcome is invalid")
    if evidence.outcome == "completed":
        if evidence.result_report_fingerprint is None or not re.fullmatch(
            r"[0-9a-f]{64}", evidence.result_report_fingerprint
        ):
            raise CandidateStrategyHoldoutCustodyError("holdout result fingerprint is invalid")
    elif evidence.result_report_fingerprint is not None:
        raise CandidateStrategyHoldoutCustodyError("failed holdout cannot claim a result")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_]{2,127}", evidence.reason_code):
        raise CandidateStrategyHoldoutCustodyError("holdout reason is invalid")


def _validate_config(config: HoldoutCustodyConfig) -> Path:
    root = config.holdout_root
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise CandidateStrategyHoldoutCustodyError("holdout custody root is unsafe")
    resolved = root.resolve()
    for forbidden in (config.repository_root.resolve(), config.data_root.resolve()):
        if (
            resolved == forbidden
            or resolved.is_relative_to(forbidden)
            or forbidden.is_relative_to(resolved)
        ):
            raise CandidateStrategyHoldoutCustodyError(
                "holdout custody overlaps protected storage"
            )
    metadata = root.stat()
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise CandidateStrategyHoldoutCustodyError("holdout custody root is unsafe")
    _reject_symlinks(root)
    _validate_root_entries(root)
    return root


def _validate_root_entries(root: Path) -> None:
    for item in root.iterdir():
        if item.name == LOCK_FILE:
            if item.is_symlink() or not item.is_file():
                raise CandidateStrategyHoldoutCustodyError("holdout lock custody differs")
            continue
        if (
            not re.fullmatch(r"holdout=[0-9a-f]{64}", item.name)
            or item.is_symlink()
            or not item.is_dir()
        ):
            raise CandidateStrategyHoldoutCustodyError("unexpected holdout custody entry")


def _open_lock(path: Path) -> int:
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        os.close(descriptor)
        raise CandidateStrategyHoldoutCustodyError("holdout lock custody differs")
    return descriptor


def _append_event(
    *,
    directory: Path,
    context: HoldoutEvaluationContext,
    existing: tuple[HoldoutCustodyEvent, ...],
    event_type: str,
    observed_at: datetime,
    details: Mapping[str, object],
) -> HoldoutCustodyEvent:
    directory.mkdir(mode=0o700, exist_ok=bool(existing))
    if not existing:
        _fsync_directory(directory.parent)
    sequence = len(existing) + 1
    payload = {
        "sequence": sequence,
        "event_type": event_type,
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "custody_id": context.custody_id,
        "previous_event_fingerprint": existing[-1].event_fingerprint if existing else None,
        "details": dict(details),
    }
    event = HoldoutCustodyEvent(**payload, event_fingerprint=_fingerprint(payload))
    target = directory / f"event-{sequence:06d}.json"
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        content = _json_bytes(event.as_dict())
        offset = 0
        while offset < len(content):
            offset += os.write(descriptor, content[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(directory)
    return event


def _read_events(
    directory: Path,
    context: HoldoutEvaluationContext,
) -> tuple[HoldoutCustodyEvent, ...]:
    if not directory.exists():
        return ()
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or stat.S_IMODE(directory.stat().st_mode) != 0o700
    ):
        raise CandidateStrategyHoldoutCustodyError("holdout directory custody differs")
    paths = sorted(directory.iterdir())
    if any(
        not EVENT_FILE.fullmatch(path.name)
        or path.is_symlink()
        or not path.is_file()
        for path in paths
    ):
        raise CandidateStrategyHoldoutCustodyError("holdout event inventory differs")
    events: list[HoldoutCustodyEvent] = []
    for sequence, path in enumerate(paths, start=1):
        if (
            path.name != f"event-{sequence:06d}.json"
            or path.stat().st_size > MAXIMUM_EVENT_BYTES
            or stat.S_IMODE(path.stat().st_mode) != 0o600
        ):
            raise CandidateStrategyHoldoutCustodyError("holdout event custody differs")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CandidateStrategyHoldoutCustodyError(
                "holdout event cannot be read"
            ) from exc
        if not isinstance(raw, dict):
            raise CandidateStrategyHoldoutCustodyError("holdout event is malformed")
        if raw.pop("contract_version", None) != JOURNAL_VERSION:
            raise CandidateStrategyHoldoutCustodyError("holdout event contract differs")
        fingerprint = raw.pop("event_fingerprint", None)
        if fingerprint != _fingerprint(raw):
            raise CandidateStrategyHoldoutCustodyError("holdout event fingerprint differs")
        try:
            event = HoldoutCustodyEvent(**raw, event_fingerprint=fingerprint)
        except TypeError as exc:
            raise CandidateStrategyHoldoutCustodyError(
                "holdout event fields differ"
            ) from exc
        if (
            event.sequence != sequence
            or event.custody_id != context.custody_id
            or event.previous_event_fingerprint
            != (events[-1].event_fingerprint if events else None)
        ):
            raise CandidateStrategyHoldoutCustodyError("holdout event chain differs")
        events.append(event)
    if (
        not events
        or events[0].event_type != "holdout_reserved"
        or len(events) > 2
        or (
            len(events) == 2
            and events[1].event_type not in {"holdout_completed", "holdout_failed"}
        )
    ):
        raise CandidateStrategyHoldoutCustodyError("holdout event sequence differs")
    expected_reservation = {
        "validation_report_fingerprint": context.validation_report_fingerprint,
        "mechanics_batch_fingerprint": context.mechanics_batch_fingerprint,
        "parameter_lock_fingerprint": context.parameter_lock_fingerprint,
        "parameter_combination_id": context.parameter_combination_id,
        "evaluation_permitted_after_reservation": True,
    }
    if events[0].details != expected_reservation:
        raise CandidateStrategyHoldoutCustodyError("holdout reservation binding differs")
    if len(events) == 2:
        terminal = events[1]
        if terminal.details.get("outcome") != (
            "completed" if terminal.event_type == "holdout_completed" else "failed"
        ):
            raise CandidateStrategyHoldoutCustodyError("holdout terminal outcome differs")
        result = terminal.details.get("result_report_fingerprint")
        if terminal.event_type == "holdout_completed":
            if not isinstance(result, str) or not re.fullmatch(
                r"[0-9a-f]{64}", result
            ):
                raise CandidateStrategyHoldoutCustodyError("holdout terminal result differs")
        elif result is not None:
            raise CandidateStrategyHoldoutCustodyError("failed holdout terminal claims a result")
        reason = terminal.details.get("reason_code")
        if not isinstance(reason, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9_]{2,127}", reason
        ):
            raise CandidateStrategyHoldoutCustodyError("holdout terminal reason differs")
    return tuple(events)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CandidateStrategyHoldoutCustodyError(
            "holdout custody clock must be timezone-aware"
        )
    return value.astimezone(UTC)


def _reject_symlinks(path: Path) -> None:
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise CandidateStrategyHoldoutCustodyError("holdout custody symlink is rejected")


def _fingerprint(value: Mapping[str, object]) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _json_bytes(value: Mapping[str, object]) -> bytes:
    content = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"{content}\n".encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
