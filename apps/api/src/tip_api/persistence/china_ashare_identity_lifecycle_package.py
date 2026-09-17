"""Immutable owner-only custody for A-share identity and lifecycle evidence."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.identity_lifecycle import (
    ChinaAshareIdentityLifecyclePackageManifestV1,
    ChinaAshareIdentityLifecycleRawArtifactV1,
    ChinaAshareIdentityLifecycleReportV1,
    ChinaAshareListedLifecycleDecisionV1,
    ChinaAshareResearchInstrumentIdentityV1,
    build_identity_lifecycle_package_manifest,
)
from tip_api.providers.china_ashare.official_identity_evidence_adapter import (
    CapturedOfficialIdentityArtifactV1,
)


IDENTITIES_FILE = "normalized/research-instrument-identities.json"
LIFECYCLE_FILE = "normalized/listed-lifecycle-decisions.json"
REPORT_FILE = "identity-lifecycle-report.json"
MANIFEST_FILE = "identity-lifecycle-manifest.json"
MAXIMUM_FILE_BYTES = 32 * 1024 * 1024


class ChinaAshareIdentityLifecyclePackageError(RuntimeError):
    pass


class ChinaAshareIdentityLifecyclePackageConflictError(
    ChinaAshareIdentityLifecyclePackageError
):
    pass


class ChinaAshareIdentityLifecyclePackageCorruptionError(
    ChinaAshareIdentityLifecyclePackageError
):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareIdentityLifecyclePackageResultV1:
    manifest: ChinaAshareIdentityLifecyclePackageManifestV1
    identities: tuple[ChinaAshareResearchInstrumentIdentityV1, ...]
    lifecycle_decisions: tuple[ChinaAshareListedLifecycleDecisionV1, ...]
    report: ChinaAshareIdentityLifecycleReportV1
    package_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_identity_lifecycle_package(
    *,
    custody_root: Path,
    captured_sources: tuple[CapturedOfficialIdentityArtifactV1, ...],
    report: ChinaAshareIdentityLifecycleReportV1,
    created_at: datetime,
) -> ChinaAshareIdentityLifecyclePackageResultV1:
    root = _root(custody_root)
    ordered_sources = tuple(sorted(captured_sources, key=lambda item: item.artifact_kind.value))
    if len(ordered_sources) != 5 or len({item.artifact_kind for item in ordered_sources}) != 5:
        raise ChinaAshareIdentityLifecyclePackageConflictError(
            "identity lifecycle package requires five unique official sources"
        )
    identities_bytes = _canonical_json_bytes(
        {
            "schema_version": "1.0",
            "rows": [item.model_dump(mode="json") for item in report.identities],
        }
    )
    lifecycle_bytes = _canonical_json_bytes(
        {
            "schema_version": "1.0",
            "rows": [
                item.model_dump(mode="json") for item in report.lifecycle_decisions
            ],
        }
    )
    report_bytes = _canonical_json_bytes(report.model_dump(mode="json"))
    artifacts = tuple(
        ChinaAshareIdentityLifecycleRawArtifactV1(
            artifact_kind=item.artifact_kind.value,
            exchange=item.exchange,
            retrieved_at=item.retrieved_at,
            final_url=item.final_url,
            content_type=item.content_type,
            relative_path=(
                f"raw/{item.artifact_kind.value}."
                f"{'json' if 'json' in item.content_type.lower() else 'xlsx'}"
            ),
            byte_size=len(item.raw_bytes),
            physical_sha256=_sha(item.raw_bytes),
        )
        for item in ordered_sources
    )
    manifest = build_identity_lifecycle_package_manifest(
        reference_package_fingerprint=report.reference_package_fingerprint,
        daily_package_fingerprint=report.daily_package_fingerprint,
        created_at=created_at,
        identities_document_sha256=_sha(identities_bytes),
        lifecycle_document_sha256=_sha(lifecycle_bytes),
        report_document_sha256=_sha(report_bytes),
        report_fingerprint=report.logical_fingerprint,
        raw_artifacts=artifacts,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    scope = root / f"identity-lifecycle-daily={report.daily_package_fingerprint}"
    target = scope / f"identity-lifecycle-package={manifest.logical_fingerprint}"
    if target.exists():
        existing = read_china_ashare_identity_lifecycle_package(package_path=target)
        if existing.manifest != manifest:
            raise ChinaAshareIdentityLifecyclePackageConflictError(
                "existing identity lifecycle package differs"
            )
        return existing
    scope.mkdir(mode=0o700, parents=True, exist_ok=True)
    if scope.is_symlink():
        raise ChinaAshareIdentityLifecyclePackageConflictError(
            "identity lifecycle scope cannot be a symlink"
        )
    staging = Path(tempfile.mkdtemp(prefix=".identity-lifecycle-", dir=scope))
    try:
        (staging / "normalized").mkdir(mode=0o700)
        (staging / "raw").mkdir(mode=0o700)
        _write(staging / IDENTITIES_FILE, identities_bytes)
        _write(staging / LIFECYCLE_FILE, lifecycle_bytes)
        _write(staging / REPORT_FILE, report_bytes)
        for artifact, captured in zip(artifacts, ordered_sources, strict=True):
            _write(staging / PurePosixPath(artifact.relative_path), captured.raw_bytes)
        _write(staging / MANIFEST_FILE, manifest_bytes)
        _owner_only(staging)
        _fsync_tree(staging)
        staging.rename(target)
        _fsync_directory(scope)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    result = read_china_ashare_identity_lifecycle_package(package_path=target)
    return replace(result, status="published")


def read_china_ashare_identity_lifecycle_package(
    *, package_path: Path
) -> ChinaAshareIdentityLifecyclePackageResultV1:
    package = package_path.expanduser().resolve()
    if not package.is_dir() or package.is_symlink():
        raise ChinaAshareIdentityLifecyclePackageCorruptionError(
            "identity lifecycle package path is invalid"
        )
    manifest_payload = _read(package / MANIFEST_FILE)
    try:
        manifest = ChinaAshareIdentityLifecyclePackageManifestV1.model_validate_json(
            manifest_payload
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareIdentityLifecyclePackageCorruptionError(
            "identity lifecycle manifest is invalid"
        ) from exc
    if package.parent.name != f"identity-lifecycle-daily={manifest.daily_package_fingerprint}":
        raise ChinaAshareIdentityLifecyclePackageCorruptionError(
            "identity lifecycle scope path differs"
        )
    if package.name != f"identity-lifecycle-package={manifest.logical_fingerprint}":
        raise ChinaAshareIdentityLifecyclePackageCorruptionError(
            "identity lifecycle package path identity differs"
        )
    identities_payload = _read(package / IDENTITIES_FILE)
    lifecycle_payload = _read(package / LIFECYCLE_FILE)
    report_payload = _read(package / REPORT_FILE)
    for payload, expected, label in (
        (identities_payload, manifest.identities_document_sha256, "identities"),
        (lifecycle_payload, manifest.lifecycle_document_sha256, "lifecycle"),
        (report_payload, manifest.report_document_sha256, "report"),
    ):
        if _sha(payload) != expected:
            raise ChinaAshareIdentityLifecyclePackageCorruptionError(
                f"identity lifecycle {label} bytes changed"
            )
    try:
        identities = tuple(
            ChinaAshareResearchInstrumentIdentityV1.model_validate(item)
            for item in _rows(identities_payload)
        )
        lifecycle = tuple(
            ChinaAshareListedLifecycleDecisionV1.model_validate(item)
            for item in _rows(lifecycle_payload)
        )
        report = ChinaAshareIdentityLifecycleReportV1.model_validate_json(report_payload)
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ChinaAshareIdentityLifecyclePackageCorruptionError(
            "identity lifecycle normalized document is invalid"
        ) from exc
    if identities != report.identities or lifecycle != report.lifecycle_decisions:
        raise ChinaAshareIdentityLifecyclePackageCorruptionError(
            "identity lifecycle normalized rows differ from report"
        )
    if report.logical_fingerprint != manifest.report_fingerprint:
        raise ChinaAshareIdentityLifecyclePackageCorruptionError(
            "identity lifecycle report fingerprint differs"
        )
    raw_paths = []
    for artifact in manifest.raw_artifacts:
        payload = _read(package / PurePosixPath(artifact.relative_path))
        if len(payload) != artifact.byte_size or _sha(payload) != artifact.physical_sha256:
            raise ChinaAshareIdentityLifecyclePackageCorruptionError(
                "identity lifecycle raw artifact bytes changed"
            )
        raw_paths.append(artifact.relative_path)
    expected_files = {
        IDENTITIES_FILE,
        LIFECYCLE_FILE,
        REPORT_FILE,
        MANIFEST_FILE,
        *raw_paths,
    }
    actual_files = {
        item.relative_to(package).as_posix()
        for item in package.rglob("*")
        if item.is_file()
    }
    if actual_files != expected_files:
        raise ChinaAshareIdentityLifecyclePackageCorruptionError(
            "identity lifecycle package file set differs"
        )
    files = tuple(item for item in package.rglob("*") if item.is_file())
    return ChinaAshareIdentityLifecyclePackageResultV1(
        manifest=manifest,
        identities=identities,
        lifecycle_decisions=lifecycle,
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
        raise ValueError("identity lifecycle document shape differs")
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
        raise ChinaAshareIdentityLifecyclePackageConflictError(
            "identity lifecycle custody root is unsafe"
        )
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ChinaAshareIdentityLifecyclePackageCorruptionError(
            "identity lifecycle package file is absent or unsafe"
        )
    size = path.stat().st_size
    if size <= 0 or size > MAXIMUM_FILE_BYTES:
        raise ChinaAshareIdentityLifecyclePackageCorruptionError(
            "identity lifecycle package file size is invalid"
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
