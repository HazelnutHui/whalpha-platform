"""Owner-only immutable custody for Factor Catalog V2 qualification reports."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from uuid import uuid4

from tip_api.contracts.analytics.v1.quant_research_factor_qualification_v2 import (
    QuantResearchFactorQualificationReportV2,
)


REPORT_FILE = "factor-qualification-v2.json"
OUTPUT_PREFIX = "report="
MAXIMUM_REPORT_BYTES = 16 * 1024 * 1024


class QuantResearchFactorQualificationV2PersistenceError(RuntimeError):
    """Raised when private Factor Catalog V2 report custody is not exact."""


def write_quant_research_factor_qualification_v2(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: QuantResearchFactorQualificationReportV2,
) -> Path:
    target, custody = _validated_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_quant_research_factor_qualification_v2(
            output_root=target,
            output_custody_root=custody,
        )
        if existing != report:
            raise QuantResearchFactorQualificationV2PersistenceError(
                "existing Factor Catalog V2 qualification report differs"
            )
        return target / REPORT_FILE

    staging = custody / f".{target.name}.staging.{uuid4().hex}"
    try:
        staging.mkdir(mode=0o700)
        _write_exclusive(staging / REPORT_FILE, qualification_v2_bytes(report))
        if _read_report_root(staging) != report:
            raise QuantResearchFactorQualificationV2PersistenceError(
                "Factor Catalog V2 staging reread differs"
            )
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(custody)
    except Exception as exc:
        _cleanup_staging(staging)
        if isinstance(exc, QuantResearchFactorQualificationV2PersistenceError):
            raise
        raise QuantResearchFactorQualificationV2PersistenceError(
            "Factor Catalog V2 report write failed"
        ) from exc
    if _read_report_root(target) != report:
        raise QuantResearchFactorQualificationV2PersistenceError(
            "Factor Catalog V2 final reread differs"
        )
    return target / REPORT_FILE


def read_quant_research_factor_qualification_v2(
    *, output_root: Path, output_custody_root: Path
) -> QuantResearchFactorQualificationReportV2:
    target, _ = _validated_target(output_root, output_custody_root)
    return _read_report_root(target)


def qualification_v2_bytes(report: QuantResearchFactorQualificationReportV2) -> bytes:
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
        raise QuantResearchFactorQualificationV2PersistenceError(
            "Factor Catalog V2 report custody differs"
        )
    return target, custody


def _read_report_root(root: Path) -> QuantResearchFactorQualificationReportV2:
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or {item.name for item in root.iterdir()} != {REPORT_FILE}
    ):
        raise QuantResearchFactorQualificationV2PersistenceError(
            "Factor Catalog V2 report directory differs"
        )
    path = root / REPORT_FILE
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.getuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or not 0 < path.stat().st_size <= MAXIMUM_REPORT_BYTES
    ):
        raise QuantResearchFactorQualificationV2PersistenceError(
            "Factor Catalog V2 report file custody differs"
        )
    raw = path.read_bytes()
    try:
        report = QuantResearchFactorQualificationReportV2.model_validate_json(raw)
    except Exception as exc:
        raise QuantResearchFactorQualificationV2PersistenceError(
            "Factor Catalog V2 report is invalid"
        ) from exc
    if raw != qualification_v2_bytes(report):
        raise QuantResearchFactorQualificationV2PersistenceError(
            "Factor Catalog V2 report bytes are not canonical"
        )
    return report


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
