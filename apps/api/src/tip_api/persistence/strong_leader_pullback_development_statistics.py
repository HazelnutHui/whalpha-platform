"""Immutable owner-only custody for Strong-Leader Pullback development statistics."""

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
    StrongLeaderPullbackDevelopmentStatisticsReportV1,
)


REPORT_FILE = "report.json"
OUTPUT_PREFIX = "report="
MAXIMUM_REPORT_BYTES = 16 * 1024 * 1024


class StrongLeaderPullbackDevelopmentStatisticsPersistenceError(RuntimeError):
    """Raised when private development-statistics custody cannot be proven."""


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackDevelopmentStatisticsRead:
    root: Path
    report: StrongLeaderPullbackDevelopmentStatisticsReportV1
    report_sha256: str
    status: str


def write_strong_leader_pullback_development_statistics(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackDevelopmentStatisticsReportV1,
) -> StrongLeaderPullbackDevelopmentStatisticsRead:
    """Atomically retain one immutable, owner-only development report."""

    target, custody = _validated_target(output_root, output_custody_root)
    payload = _report_bytes(report)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_development_statistics(
            output_root=target,
            output_custody_root=custody,
        )
        if existing.report != report:
            raise StrongLeaderPullbackDevelopmentStatisticsPersistenceError(
                "existing development statistics differ"
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
            exc, StrongLeaderPullbackDevelopmentStatisticsPersistenceError
        ):
            raise
        raise StrongLeaderPullbackDevelopmentStatisticsPersistenceError(
            "development statistics write failed"
        ) from exc

    retained = read_strong_leader_pullback_development_statistics(
        output_root=target,
        output_custody_root=custody,
    )
    if retained.report != report or retained.report_sha256 != hashlib.sha256(
        payload
    ).hexdigest():
        raise StrongLeaderPullbackDevelopmentStatisticsPersistenceError(
            "development statistics reread differs"
        )
    return StrongLeaderPullbackDevelopmentStatisticsRead(
        root=retained.root,
        report=retained.report,
        report_sha256=retained.report_sha256,
        status="published",
    )


def read_strong_leader_pullback_development_statistics(
    *,
    output_root: Path,
    output_custody_root: Path,
) -> StrongLeaderPullbackDevelopmentStatisticsRead:
    """Reread and verify one immutable development report."""

    target, _ = _validated_target(output_root, output_custody_root)
    if (
        target.is_symlink()
        or not target.is_dir()
        or target.resolve(strict=True) != target
        or target.stat().st_uid != os.getuid()
        or stat.S_IMODE(target.stat().st_mode) != 0o700
        or {item.name for item in target.iterdir()} != {REPORT_FILE}
    ):
        raise StrongLeaderPullbackDevelopmentStatisticsPersistenceError(
            "development statistics directory differs"
        )
    raw = _read_regular(target / REPORT_FILE)
    try:
        report = StrongLeaderPullbackDevelopmentStatisticsReportV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackDevelopmentStatisticsPersistenceError(
            "development statistics report is invalid"
        ) from exc
    if raw != _report_bytes(report):
        raise StrongLeaderPullbackDevelopmentStatisticsPersistenceError(
            "development statistics report bytes differ"
        )
    return StrongLeaderPullbackDevelopmentStatisticsRead(
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
        or not target.name.startswith(OUTPUT_PREFIX)
        or target.name == OUTPUT_PREFIX
    ):
        raise StrongLeaderPullbackDevelopmentStatisticsPersistenceError(
            "development statistics custody differs"
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
        raise StrongLeaderPullbackDevelopmentStatisticsPersistenceError(
            "development statistics file custody differs"
        )
    return path.read_bytes()


def _report_bytes(report: StrongLeaderPullbackDevelopmentStatisticsReportV1) -> bytes:
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
