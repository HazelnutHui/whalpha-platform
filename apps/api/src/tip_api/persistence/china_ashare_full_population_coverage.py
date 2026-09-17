"""Owner-only custody for the A-share full-population coverage report."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path

from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    ChinaAshareFullPopulationCoverageReportV1,
)


REPORT_FILE = "full-population-coverage-report.json"


class ChinaAshareFullPopulationCoverageCustodyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareFullPopulationCoverageResultV1:
    report: ChinaAshareFullPopulationCoverageReportV1
    package_path: Path
    report_path: Path
    report_physical_sha256: str
    status: str


def publish_china_ashare_full_population_coverage(
    *, custody_root: Path, report: ChinaAshareFullPopulationCoverageReportV1
) -> ChinaAshareFullPopulationCoverageResultV1:
    root = custody_root.expanduser().resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise ChinaAshareFullPopulationCoverageCustodyError(
            "coverage custody root is invalid"
        )
    target = root / f"report={report.logical_fingerprint}"
    if target.exists():
        return replace(
            read_china_ashare_full_population_coverage(package_path=target),
            status="already_present",
        )
    staging = root / f".{target.name}.staging.{os.getpid()}"
    staging.mkdir(mode=0o700)
    try:
        payload = _canonical(report)
        _write(staging / REPORT_FILE, payload)
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(root)
    except BaseException:
        if staging.is_dir() and not staging.is_symlink():
            (staging / REPORT_FILE).unlink(missing_ok=True)
            staging.rmdir()
        raise
    return replace(
        read_china_ashare_full_population_coverage(package_path=target),
        status="published",
    )


def read_china_ashare_full_population_coverage(
    *, package_path: Path
) -> ChinaAshareFullPopulationCoverageResultV1:
    root = package_path.expanduser().resolve()
    if root.is_symlink() or not root.is_dir() or (root.stat().st_mode & 0o777) != 0o700:
        raise ChinaAshareFullPopulationCoverageCustodyError(
            "coverage package path is invalid"
        )
    path = root / REPORT_FILE
    if path.is_symlink() or not path.is_file() or (path.stat().st_mode & 0o777) != 0o400:
        raise ChinaAshareFullPopulationCoverageCustodyError(
            "coverage report custody differs"
        )
    payload = path.read_bytes()
    try:
        report = ChinaAshareFullPopulationCoverageReportV1.model_validate_json(payload)
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareFullPopulationCoverageCustodyError(
            "coverage report is invalid"
        ) from exc
    if root.name != f"report={report.logical_fingerprint}" or payload != _canonical(report):
        raise ChinaAshareFullPopulationCoverageCustodyError(
            "coverage report identity differs"
        )
    files = tuple(item for item in root.iterdir())
    if files != (path,):
        raise ChinaAshareFullPopulationCoverageCustodyError(
            "coverage package inventory differs"
        )
    return ChinaAshareFullPopulationCoverageResultV1(
        report=report,
        package_path=root,
        report_path=path,
        report_physical_sha256=hashlib.sha256(payload).hexdigest(),
        status="exact_reread_complete",
    )


def _canonical(report: ChinaAshareFullPopulationCoverageReportV1) -> bytes:
    return (
        json.dumps(
            report.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode()


def _write(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
