"""Immutable owner-only custody for the replacement selection result."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from tip_api.contracts.analytics.v1 import (
    REPLACEMENT_SELECTION_OUTPUT_DIRECTORY,
    StrongLeaderPullbackReplacementSelectionReportV1,
)


REPORT_FILE = "report.json"
MAXIMUM_REPORT_BYTES = 2 * 1024 * 1024


class StrongLeaderPullbackReplacementSelectionPersistenceError(RuntimeError):
    """Raised when private replacement-selection custody cannot be proven."""


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackReplacementSelectionRead:
    root: Path
    report: StrongLeaderPullbackReplacementSelectionReportV1
    report_sha256: str
    status: str


def write_strong_leader_pullback_replacement_selection(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackReplacementSelectionReportV1,
) -> StrongLeaderPullbackReplacementSelectionRead:
    target, custody = _validated_target(output_root, output_custody_root)
    payload = _report_bytes(report)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_replacement_selection(
            output_root=target,
            output_custody_root=custody,
        )
        if existing.report != report:
            raise StrongLeaderPullbackReplacementSelectionPersistenceError(
                "existing replacement selection differs"
            )
        return existing

    staging = custody / f".{target.name}.staging.{uuid4().hex}"
    try:
        staging.mkdir(mode=0o700)
        _write_exclusive(staging / REPORT_FILE, payload)
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(custody)
    except Exception as exc:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(custody)
        if isinstance(
            exc, StrongLeaderPullbackReplacementSelectionPersistenceError
        ):
            raise
        raise StrongLeaderPullbackReplacementSelectionPersistenceError(
            "replacement selection write failed"
        ) from exc

    retained = read_strong_leader_pullback_replacement_selection(
        output_root=target,
        output_custody_root=custody,
    )
    if retained.report != report or retained.report_sha256 != hashlib.sha256(
        payload
    ).hexdigest():
        raise StrongLeaderPullbackReplacementSelectionPersistenceError(
            "replacement selection reread differs"
        )
    return StrongLeaderPullbackReplacementSelectionRead(
        root=retained.root,
        report=retained.report,
        report_sha256=retained.report_sha256,
        status="published",
    )


def read_strong_leader_pullback_replacement_selection(
    *,
    output_root: Path,
    output_custody_root: Path,
) -> StrongLeaderPullbackReplacementSelectionRead:
    target, _ = _validated_target(output_root, output_custody_root)
    if (
        target.is_symlink()
        or not target.is_dir()
        or target.resolve(strict=True) != target
        or target.stat().st_uid != os.getuid()
        or stat.S_IMODE(target.stat().st_mode) != 0o700
        or {item.name for item in target.iterdir()} != {REPORT_FILE}
    ):
        raise StrongLeaderPullbackReplacementSelectionPersistenceError(
            "replacement selection directory differs"
        )
    raw = _read_regular(target / REPORT_FILE)
    try:
        report = StrongLeaderPullbackReplacementSelectionReportV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackReplacementSelectionPersistenceError(
            "replacement selection report is invalid"
        ) from exc
    if raw != _report_bytes(report):
        raise StrongLeaderPullbackReplacementSelectionPersistenceError(
            "replacement selection report bytes differ"
        )
    return StrongLeaderPullbackReplacementSelectionRead(
        root=target,
        report=report,
        report_sha256=hashlib.sha256(raw).hexdigest(),
        status="already_present",
    )


def _validated_target(
    output_root: Path, output_custody_root: Path
) -> tuple[Path, Path]:
    target = output_root.absolute()
    custody = output_custody_root.absolute()
    if (
        custody.is_symlink()
        or not custody.is_dir()
        or custody.resolve(strict=True) != custody
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or target.parent != custody
        or target.name != REPLACEMENT_SELECTION_OUTPUT_DIRECTORY
    ):
        raise StrongLeaderPullbackReplacementSelectionPersistenceError(
            "replacement selection custody differs"
        )
    return target, custody


def _read_regular(path: Path) -> bytes:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.getuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or not 0 < path.stat().st_size <= MAXIMUM_REPORT_BYTES
    ):
        raise StrongLeaderPullbackReplacementSelectionPersistenceError(
            "replacement selection file custody differs"
        )
    return path.read_bytes()


def _report_bytes(report: StrongLeaderPullbackReplacementSelectionReportV1) -> bytes:
    return (
        json.dumps(
            report.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
