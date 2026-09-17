"""Immutable owner-only custody for A-share daily Universe decisions."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.daily_universe import (
    ChinaAshareDailyUniversePackageManifestV1,
    ChinaAshareDailyUniverseReportV1,
    build_daily_universe_package_manifest,
    daily_universe_decision_set_fingerprint,
)
from tip_api.contracts.china_ashare.v1.foundation import ChinaAshareUniverseDecisionV1


DECISIONS_FILE = "daily-universe-decisions.json"
REPORT_FILE = "daily-universe-report.json"
MANIFEST_FILE = "daily-universe-manifest.json"
MAXIMUM_FILE_BYTES = 32 * 1024 * 1024


class ChinaAshareDailyUniversePackageError(RuntimeError):
    pass


class ChinaAshareDailyUniversePackageConflictError(
    ChinaAshareDailyUniversePackageError
):
    pass


class ChinaAshareDailyUniversePackageCorruptionError(
    ChinaAshareDailyUniversePackageError
):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareDailyUniversePackageResultV1:
    manifest: ChinaAshareDailyUniversePackageManifestV1
    decisions: tuple[ChinaAshareUniverseDecisionV1, ...]
    report: ChinaAshareDailyUniverseReportV1
    package_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_daily_universe_package(
    *,
    custody_root: Path,
    decisions: tuple[ChinaAshareUniverseDecisionV1, ...],
    report: ChinaAshareDailyUniverseReportV1,
    created_at: datetime,
) -> ChinaAshareDailyUniversePackageResultV1:
    root = _root(custody_root)
    keys = tuple((str(item.instrument_id), item.session_date) for item in decisions)
    if keys != tuple(sorted(set(keys))):
        raise ChinaAshareDailyUniversePackageConflictError(
            "daily Universe decisions must be unique and ordered"
        )
    decision_set_fingerprint = daily_universe_decision_set_fingerprint(decisions)
    if decision_set_fingerprint != report.decision_set_fingerprint:
        raise ChinaAshareDailyUniversePackageConflictError(
            "daily Universe decision set differs from report"
        )
    decisions_bytes = _canonical_json_bytes(
        {
            "schema_version": "1.0",
            "rows": [item.model_dump(mode="json") for item in decisions],
        }
    )
    report_bytes = _canonical_json_bytes(report.model_dump(mode="json"))
    manifest = build_daily_universe_package_manifest(
        daily_package_fingerprint=report.daily_package_fingerprint,
        identity_lifecycle_package_fingerprint=(
            report.identity_lifecycle_package_fingerprint
        ),
        created_at=created_at,
        decision_document_sha256=_sha(decisions_bytes),
        decision_set_fingerprint=decision_set_fingerprint,
        report_document_sha256=_sha(report_bytes),
        report_fingerprint=report.logical_fingerprint,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    scope = root / (
        "daily-universe-identity="
        f"{report.identity_lifecycle_package_fingerprint}"
    )
    target = scope / f"daily-universe-package={manifest.logical_fingerprint}"
    if target.exists():
        existing = read_china_ashare_daily_universe_package(package_path=target)
        if existing.manifest != manifest:
            raise ChinaAshareDailyUniversePackageConflictError(
                "existing daily Universe package differs"
            )
        return existing
    scope.mkdir(mode=0o700, parents=True, exist_ok=True)
    if scope.is_symlink():
        raise ChinaAshareDailyUniversePackageConflictError(
            "daily Universe scope cannot be a symlink"
        )
    staging = Path(tempfile.mkdtemp(prefix=".daily-universe-", dir=scope))
    try:
        _write(staging / DECISIONS_FILE, decisions_bytes)
        _write(staging / REPORT_FILE, report_bytes)
        _write(staging / MANIFEST_FILE, manifest_bytes)
        _owner_only(staging)
        _fsync_tree(staging)
        staging.rename(target)
        _fsync_directory(scope)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_china_ashare_daily_universe_package(package_path=target),
        status="published",
    )


def read_china_ashare_daily_universe_package(
    *, package_path: Path
) -> ChinaAshareDailyUniversePackageResultV1:
    package = package_path.expanduser().resolve()
    if not package.is_dir() or package.is_symlink():
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe package path is invalid"
        )
    manifest_payload = _read(package / MANIFEST_FILE)
    try:
        manifest = ChinaAshareDailyUniversePackageManifestV1.model_validate_json(
            manifest_payload
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe manifest is invalid"
        ) from exc
    if package.parent.name != (
        "daily-universe-identity="
        f"{manifest.identity_lifecycle_package_fingerprint}"
    ):
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe scope path differs"
        )
    if package.name != f"daily-universe-package={manifest.logical_fingerprint}":
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe package path identity differs"
        )
    decisions_payload = _read(package / DECISIONS_FILE)
    report_payload = _read(package / REPORT_FILE)
    if _sha(decisions_payload) != manifest.decision_document_sha256:
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe decision bytes changed"
        )
    if _sha(report_payload) != manifest.report_document_sha256:
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe report bytes changed"
        )
    try:
        decisions = tuple(
            ChinaAshareUniverseDecisionV1.model_validate(item)
            for item in _rows(decisions_payload)
        )
        report = ChinaAshareDailyUniverseReportV1.model_validate_json(report_payload)
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe normalized document is invalid"
        ) from exc
    keys = tuple((str(item.instrument_id), item.session_date) for item in decisions)
    if keys != tuple(sorted(set(keys))):
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe decisions are not unique and ordered"
        )
    if daily_universe_decision_set_fingerprint(decisions) != (
        manifest.decision_set_fingerprint
    ):
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe decision fingerprint differs"
        )
    if report.decision_set_fingerprint != manifest.decision_set_fingerprint:
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe report decision fingerprint differs"
        )
    if report.logical_fingerprint != manifest.report_fingerprint:
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe report fingerprint differs"
        )
    expected_files = {DECISIONS_FILE, REPORT_FILE, MANIFEST_FILE}
    actual_files = {
        item.relative_to(package).as_posix()
        for item in package.rglob("*")
        if item.is_file()
    }
    if actual_files != expected_files:
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe package file set differs"
        )
    files = tuple(item for item in package.rglob("*") if item.is_file())
    return ChinaAshareDailyUniversePackageResultV1(
        manifest=manifest,
        decisions=decisions,
        report=report,
        package_path=package,
        manifest_path=package / MANIFEST_FILE,
        manifest_physical_sha256=_sha(manifest_payload),
        file_count=len(files),
        total_bytes=sum(item.stat().st_size for item in files),
        status="exact_reread_complete",
    )


def _rows(payload: bytes) -> list[Any]:
    document = json.loads(payload)
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != "1.0"
        or not isinstance(document.get("rows"), list)
    ):
        raise ValueError("daily Universe document shape differs")
    return document["rows"]


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _root(value: Path) -> Path:
    root = value.expanduser().resolve()
    if root == Path("/"):
        raise ChinaAshareDailyUniversePackageConflictError(
            "daily Universe custody root is unsafe"
        )
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe package file is absent or unsafe"
        )
    size = path.stat().st_size
    if size <= 0 or size > MAXIMUM_FILE_BYTES:
        raise ChinaAshareDailyUniversePackageCorruptionError(
            "daily Universe package file size is invalid"
        )
    return path.read_bytes()


def _write(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
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


def _owner_only(root: Path) -> None:
    for item in root.rglob("*"):
        os.chmod(item, 0o700 if item.is_dir() else 0o600)
    os.chmod(root, 0o700)


def _fsync_tree(root: Path) -> None:
    for directory, _, _ in os.walk(root, topdown=False):
        _fsync_directory(Path(directory))


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
