"""Immutable completion-report custody for A-share raw-source expansion."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.source_expansion_completion import (
    ChinaAshareSourceExpansionCompletionReportV1,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    ChinaAshareSourceExpansionPlanResultV1,
)


REPORT_FILE = "source-expansion-completion-report.json"
MAXIMUM_REPORT_BYTES = 4 * 1024 * 1024


class ChinaAshareSourceExpansionCompletionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareSourceExpansionCompletionResultV1:
    report: ChinaAshareSourceExpansionCompletionReportV1
    package_path: Path
    report_path: Path
    report_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_source_expansion_completion(
    *,
    plan_result: ChinaAshareSourceExpansionPlanResultV1,
    report: ChinaAshareSourceExpansionCompletionReportV1,
) -> ChinaAshareSourceExpansionCompletionResultV1:
    if report.plan_fingerprint != plan_result.plan.logical_fingerprint:
        raise ChinaAshareSourceExpansionCompletionError(
            "source expansion completion plan differs"
        )
    parent = plan_result.plan_root / "completions"
    parent.mkdir(mode=0o700, exist_ok=True)
    if parent.is_symlink() or not parent.is_dir():
        raise ChinaAshareSourceExpansionCompletionError(
            "source expansion completion root is invalid"
        )
    target = parent / f"completion={report.logical_fingerprint}"
    if target.exists():
        return replace(
            read_china_ashare_source_expansion_completion(package_path=target),
            status="already_present",
        )
    staging = parent / f".{target.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise ChinaAshareSourceExpansionCompletionError(
            "source expansion completion staging path exists"
        )
    staging.mkdir(mode=0o700)
    try:
        _write(
            staging / REPORT_FILE,
            _canonical_json_bytes(report.model_dump(mode="json")),
        )
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_china_ashare_source_expansion_completion(package_path=target),
        status="published",
    )


def read_china_ashare_source_expansion_completion(
    *, package_path: Path
) -> ChinaAshareSourceExpansionCompletionResultV1:
    root = package_path.expanduser().resolve()
    if not root.is_dir() or root.is_symlink():
        raise ChinaAshareSourceExpansionCompletionError(
            "source expansion completion path is invalid"
        )
    payload = _read(root / REPORT_FILE)
    try:
        report = ChinaAshareSourceExpansionCompletionReportV1.model_validate_json(
            payload
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareSourceExpansionCompletionError(
            "source expansion completion report is invalid"
        ) from exc
    if root.name != f"completion={report.logical_fingerprint}":
        raise ChinaAshareSourceExpansionCompletionError(
            "source expansion completion identity differs"
        )
    files = tuple(item for item in root.rglob("*") if item.is_file())
    if (
        {item.relative_to(root).as_posix() for item in files} != {REPORT_FILE}
        or any(item.is_symlink() for item in root.rglob("*"))
        or (root.stat().st_mode & 0o777) != 0o700
        or any((item.stat().st_mode & 0o777) != 0o400 for item in files)
    ):
        raise ChinaAshareSourceExpansionCompletionError(
            "source expansion completion custody differs"
        )
    return ChinaAshareSourceExpansionCompletionResultV1(
        report=report,
        package_path=root,
        report_path=root / REPORT_FILE,
        report_physical_sha256=_sha(payload),
        file_count=len(files),
        total_bytes=sum(item.stat().st_size for item in files),
        status="exact_reread_complete",
    )


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ChinaAshareSourceExpansionCompletionError(
            "source expansion completion file is absent or unsafe"
        )
    size = path.stat().st_size
    if size <= 0 or size > MAXIMUM_REPORT_BYTES:
        raise ChinaAshareSourceExpansionCompletionError(
            "source expansion completion file size is invalid"
        )
    return path.read_bytes()


def _write(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
