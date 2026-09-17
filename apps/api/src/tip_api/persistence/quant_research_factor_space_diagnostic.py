"""Owner-only immutable custody for U.S. factor-space diagnostics."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from uuid import uuid4

from tip_api.contracts.analytics.v1.quant_research_factor_space_diagnostic import (
    QuantResearchFactorSpaceDiagnosticV1,
)


REPORT_FILE = "factor-space-diagnostic-v1.json"
OUTPUT_PREFIX = "report="
MAXIMUM_REPORT_BYTES = 32 * 1024 * 1024


class FactorSpaceDiagnosticPersistenceError(RuntimeError):
    """Raised when private diagnostic custody cannot be trusted."""


def factor_space_diagnostic_bytes(report: QuantResearchFactorSpaceDiagnosticV1) -> bytes:
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


def write_factor_space_diagnostic(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: QuantResearchFactorSpaceDiagnosticV1,
) -> Path:
    target, custody = _validated_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_factor_space_diagnostic(
            output_root=target,
            output_custody_root=custody,
        )
        if existing != report:
            raise FactorSpaceDiagnosticPersistenceError(
                "existing factor-space diagnostic differs"
            )
        return target / REPORT_FILE
    staging = custody / f".{target.name}.staging.{uuid4().hex}"
    try:
        staging.mkdir(mode=0o700)
        _write_exclusive(staging / REPORT_FILE, factor_space_diagnostic_bytes(report))
        if _read_root(staging) != report:
            raise FactorSpaceDiagnosticPersistenceError("staging reread differs")
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(custody)
    except Exception as exc:
        _cleanup(staging)
        if isinstance(exc, FactorSpaceDiagnosticPersistenceError):
            raise
        raise FactorSpaceDiagnosticPersistenceError("diagnostic write failed") from exc
    if _read_root(target) != report:
        raise FactorSpaceDiagnosticPersistenceError("final reread differs")
    return target / REPORT_FILE


def read_factor_space_diagnostic(
    *, output_root: Path, output_custody_root: Path
) -> QuantResearchFactorSpaceDiagnosticV1:
    target, _ = _validated_target(output_root, output_custody_root)
    return _read_root(target)


def _validated_target(output_root: Path, output_custody_root: Path) -> tuple[Path, Path]:
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
        raise FactorSpaceDiagnosticPersistenceError("diagnostic custody differs")
    return target, custody


def _read_root(root: Path) -> QuantResearchFactorSpaceDiagnosticV1:
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or {item.name for item in root.iterdir()} != {REPORT_FILE}
    ):
        raise FactorSpaceDiagnosticPersistenceError("diagnostic directory differs")
    path = root / REPORT_FILE
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.getuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or not 0 < path.stat().st_size <= MAXIMUM_REPORT_BYTES
    ):
        raise FactorSpaceDiagnosticPersistenceError("diagnostic report custody differs")
    raw = path.read_bytes()
    try:
        report = QuantResearchFactorSpaceDiagnosticV1.model_validate_json(raw)
    except Exception as exc:
        raise FactorSpaceDiagnosticPersistenceError("diagnostic report is invalid") from exc
    if raw != factor_space_diagnostic_bytes(report):
        raise FactorSpaceDiagnosticPersistenceError("diagnostic bytes are not canonical")
    return report


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _cleanup(staging: Path) -> None:
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
