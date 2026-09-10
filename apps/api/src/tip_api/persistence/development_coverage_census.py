"""Owner-only persistence for a development coverage census."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from uuid import uuid4

from tip_api.contracts.analytics.v1.candidate_strategy_development_coverage import (
    StrongLeaderPullbackDevelopmentCoverageCensusV1,
)


REPORT_FILE = "report.json"
OUTPUT_PREFIX = "whalpha-strong-leader-pullback-development-census-"
MAXIMUM_REPORT_BYTES = 128 * 1024 * 1024


class DevelopmentCoverageCensusPersistenceError(RuntimeError):
    """Raised when owner-only census custody cannot be trusted."""


def write_development_coverage_census(
    *,
    output_root: Path,
    report: StrongLeaderPullbackDevelopmentCoverageCensusV1,
) -> Path:
    """Atomically write one new owner-only report below /tmp."""

    target = _validate_new_output_root(output_root)
    staging = target.parent / f"{target.name}-staging-{uuid4().hex}"
    try:
        staging.mkdir(mode=0o700)
        _write_exclusive(staging / REPORT_FILE, development_coverage_census_bytes(report))
        reread = read_development_coverage_census(output_root=staging)
        if reread != report:
            raise DevelopmentCoverageCensusPersistenceError(
                "development census formal reread differs"
            )
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(target.parent)
    except Exception as exc:
        _cleanup_staging(staging)
        if isinstance(exc, DevelopmentCoverageCensusPersistenceError):
            raise
        raise DevelopmentCoverageCensusPersistenceError(
            "development census write failed"
        ) from exc
    final = read_development_coverage_census(output_root=target)
    if final != report:
        raise DevelopmentCoverageCensusPersistenceError(
            "development census final reread differs"
        )
    return target / REPORT_FILE


def read_development_coverage_census(
    *, output_root: Path
) -> StrongLeaderPullbackDevelopmentCoverageCensusV1:
    """Formally reread one owner-only census report."""

    root = output_root.absolute()
    temporary_root = Path("/tmp").resolve(strict=True)
    if (
        root.parent != temporary_root
        or not root.name.startswith(OUTPUT_PREFIX)
        or root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or {item.name for item in root.iterdir()} != {REPORT_FILE}
    ):
        raise DevelopmentCoverageCensusPersistenceError(
            "development census directory custody differs"
        )
    path = root / REPORT_FILE
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.getuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or not 0 < path.stat().st_size <= MAXIMUM_REPORT_BYTES
    ):
        raise DevelopmentCoverageCensusPersistenceError(
            "development census file custody differs"
        )
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackDevelopmentCoverageCensusV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise DevelopmentCoverageCensusPersistenceError(
            "development census report is invalid"
        ) from exc
    if raw != development_coverage_census_bytes(report):
        raise DevelopmentCoverageCensusPersistenceError(
            "development census report bytes are not canonical"
        )
    return report


def development_coverage_census_bytes(
    report: StrongLeaderPullbackDevelopmentCoverageCensusV1,
) -> bytes:
    return (
        json.dumps(
            report.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _validate_new_output_root(output_root: Path) -> Path:
    target = output_root.absolute()
    temporary_root = Path("/tmp").resolve(strict=True)
    if (
        target.parent != temporary_root
        or not target.name.startswith(OUTPUT_PREFIX)
        or target.exists()
        or target.is_symlink()
    ):
        raise DevelopmentCoverageCensusPersistenceError(
            "output root must be one new direct /tmp census directory"
        )
    return target


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


def _cleanup_staging(staging: Path) -> None:
    if staging.is_symlink() or not staging.exists():
        return
    report_path = staging / REPORT_FILE
    if report_path.exists() and not report_path.is_symlink():
        report_path.unlink()
    try:
        staging.rmdir()
    except OSError:
        pass


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
