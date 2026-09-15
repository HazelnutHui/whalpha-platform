"""Immutable owner-only custody for Factor Catalog V1 screening results."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from uuid import uuid4

from tip_api.contracts.analytics.v1.quant_research_factor_screening_result import (
    QuantResearchFactorScreeningReportV1,
)


REPORT_FILE = "factor-screening-report.json"
OUTPUT_PREFIX = "report="
MAXIMUM_REPORT_BYTES = 16 * 1024 * 1024


class QuantResearchFactorScreeningPersistenceError(RuntimeError):
    """Raised when private factor-screening custody cannot be trusted."""


def write_quant_research_factor_screening_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: QuantResearchFactorScreeningReportV1,
) -> tuple[Path, str, str]:
    target, custody = _validated_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing, sha256 = read_quant_research_factor_screening_report(
            output_root=target,
            output_custody_root=custody,
        )
        if existing != report:
            raise QuantResearchFactorScreeningPersistenceError(
                "existing factor-screening report differs"
            )
        return target / REPORT_FILE, sha256, "already_present"

    staging = custody / f".{target.name}.staging.{uuid4().hex}"
    try:
        staging.mkdir(mode=0o700)
        payload = factor_screening_report_bytes(report)
        _write_exclusive(staging / REPORT_FILE, payload)
        staged, _ = _read_report_root(staging)
        if staged != report:
            raise QuantResearchFactorScreeningPersistenceError(
                "factor-screening staging reread differs"
            )
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(custody)
    except Exception as exc:
        _cleanup_staging(staging)
        if isinstance(exc, QuantResearchFactorScreeningPersistenceError):
            raise
        raise QuantResearchFactorScreeningPersistenceError(
            "factor-screening report write failed"
        ) from exc
    reread, sha256 = _read_report_root(target)
    if reread != report:
        raise QuantResearchFactorScreeningPersistenceError(
            "factor-screening final reread differs"
        )
    return target / REPORT_FILE, sha256, "published"


def read_quant_research_factor_screening_report(
    *, output_root: Path, output_custody_root: Path
) -> tuple[QuantResearchFactorScreeningReportV1, str]:
    target, _ = _validated_target(output_root, output_custody_root)
    return _read_report_root(target)


def factor_screening_report_bytes(report: QuantResearchFactorScreeningReportV1) -> bytes:
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


def _validated_target(
    output_root: Path, output_custody_root: Path
) -> tuple[Path, Path]:
    custody = output_custody_root.absolute()
    target = output_root.absolute()
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
        raise QuantResearchFactorScreeningPersistenceError(
            "factor-screening custody differs"
        )
    return target, custody


def _read_report_root(root: Path) -> tuple[QuantResearchFactorScreeningReportV1, str]:
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or {item.name for item in root.iterdir()} != {REPORT_FILE}
    ):
        raise QuantResearchFactorScreeningPersistenceError(
            "factor-screening report directory differs"
        )
    path = root / REPORT_FILE
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.getuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or not 0 < path.stat().st_size <= MAXIMUM_REPORT_BYTES
    ):
        raise QuantResearchFactorScreeningPersistenceError(
            "factor-screening report file differs"
        )
    payload = path.read_bytes()
    try:
        report = QuantResearchFactorScreeningReportV1.model_validate_json(payload)
    except Exception as exc:
        raise QuantResearchFactorScreeningPersistenceError(
            "factor-screening report is invalid"
        ) from exc
    if payload != factor_screening_report_bytes(report):
        raise QuantResearchFactorScreeningPersistenceError(
            "factor-screening report bytes are not canonical"
        )
    return report, hashlib.sha256(payload).hexdigest()


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
    report = staging / REPORT_FILE
    if report.exists() and not report.is_symlink():
        report.unlink()
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
