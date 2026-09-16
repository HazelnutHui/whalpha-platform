"""Atomic temporary custody for normalized China A-share pilot evidence."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareDailyBarV1,
    ChinaAshareDailyTradingStateV1,
    ChinaAshareInstrumentSourceObservationV1,
    ChinaAshareLifecycleEventType,
    ChinaAshareLifecycleSourceObservationV1,
    ChinaAsharePilotArtifactKind,
    ChinaAsharePilotArtifactV1,
    ChinaAsharePilotDailyPackageManifestV1,
    ChinaAsharePilotDailyQualityReportV1,
    ChinaAsharePilotIdentityDecisionV1,
    ChinaAsharePilotIdentityDisposition,
    ChinaAsharePilotPackageManifestV1,
    ChinaAsharePilotPlanV1,
    ChinaAsharePilotReferenceQualityReportV1,
    ChinaAshareSourceSecuritySnapshotStateV1,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
    build_china_ashare_pilot_daily_package_manifest,
    build_china_ashare_pilot_daily_quality_report,
    build_china_ashare_pilot_package_manifest,
    build_china_ashare_pilot_quality_report,
)
from tip_api.providers.china_ashare import (
    BAOSTOCK_ASHARE_PROVIDER_ID,
    ChinaAshareDailySourceBatchV1,
    ChinaAshareSourceDailyQuery,
)


MANIFEST_DIRECTORY = "manifests"
PLAN_FILE = "pilot-plan.json"
QUALITY_REPORT_FILE = "reference-quality-report.json"
PACKAGE_MANIFEST_FILE = "package-manifest.json"
DAILY_QUALITY_REPORT_FILE = "daily-quality-report.json"
DAILY_PACKAGE_MANIFEST_FILE = "daily-package-manifest.json"
MAXIMUM_JSON_BYTES = 64 * 1024 * 1024
_ARTIFACT_PATHS = {
    ChinaAsharePilotArtifactKind.ADJUSTMENT_FACTOR: (
        "normalized/adjustment-factors.json"
    ),
    ChinaAsharePilotArtifactKind.OFFICIAL_CURRENT_INSTRUMENT: (
        "normalized/official-current-instruments.json"
    ),
    ChinaAsharePilotArtifactKind.BAOSTOCK_INSTRUMENT: (
        "normalized/baostock-instruments.json"
    ),
    ChinaAsharePilotArtifactKind.BAOSTOCK_SOURCE_STATE: (
        "normalized/baostock-source-states.json"
    ),
    ChinaAsharePilotArtifactKind.DAILY_BAR: "normalized/daily-bars.json",
    ChinaAsharePilotArtifactKind.DAILY_TRADING_STATE: (
        "normalized/daily-trading-states.json"
    ),
    ChinaAsharePilotArtifactKind.IDENTITY_DECISION: (
        "normalized/pilot-identity-decisions.json"
    ),
    ChinaAsharePilotArtifactKind.OFFICIAL_LIFECYCLE: (
        "normalized/official-lifecycle.json"
    ),
}


class ChinaAsharePilotPackageError(RuntimeError):
    """Base failure for temporary China A-share pilot custody."""


class ChinaAsharePilotPackageConflictError(ChinaAsharePilotPackageError):
    """Raised when planned evidence or an immutable package conflicts."""


class ChinaAsharePilotPackageCorruptionError(ChinaAsharePilotPackageError):
    """Raised when an exact reread detects changed or malformed custody."""


@dataclass(frozen=True, slots=True)
class CapturedChinaAsharePilotReferenceV1:
    official_current_instruments: tuple[
        ChinaAshareInstrumentSourceObservationV1, ...
    ]
    baostock_instruments: tuple[ChinaAshareInstrumentSourceObservationV1, ...]
    baostock_source_states: tuple[ChinaAshareSourceSecuritySnapshotStateV1, ...]
    official_lifecycle: tuple[ChinaAshareLifecycleSourceObservationV1, ...]
    source_request_count: int


@dataclass(frozen=True, slots=True)
class ChinaAsharePilotPackageResultV1:
    manifest: ChinaAsharePilotPackageManifestV1
    plan: ChinaAsharePilotPlanV1
    quality_report: ChinaAsharePilotReferenceQualityReportV1
    captured: CapturedChinaAsharePilotReferenceV1
    package_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


@dataclass(frozen=True, slots=True)
class CapturedChinaAsharePilotDailyV1:
    identity_decisions: tuple[ChinaAsharePilotIdentityDecisionV1, ...]
    daily_batch: ChinaAshareDailySourceBatchV1
    adjustment_observations: tuple[ChinaAshareAdjustmentFactorObservationV1, ...]
    source_request_count: int


@dataclass(frozen=True, slots=True)
class ChinaAsharePilotDailyPackageResultV1:
    manifest: ChinaAsharePilotDailyPackageManifestV1
    plan: ChinaAsharePilotPlanV1
    quality_report: ChinaAsharePilotDailyQualityReportV1
    captured: CapturedChinaAsharePilotDailyV1
    package_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_pilot_reference_package(
    *,
    custody_root: Path,
    plan: ChinaAsharePilotPlanV1,
    captured: CapturedChinaAsharePilotReferenceV1,
    created_at: datetime,
) -> ChinaAsharePilotPackageResultV1:
    """Publish normalized evidence only; no provider call or canonical apply occurs."""

    root = _validate_custody_root(custody_root)
    payloads = _prepare_artifact_payloads(plan, captured)
    report = _build_quality_report(plan, captured, created_at)
    plan_bytes = _canonical_json_bytes(plan.model_dump(mode="json"))
    report_bytes = _canonical_json_bytes(report.model_dump(mode="json"))
    artifacts = tuple(
        ChinaAsharePilotArtifactV1(
            artifact_kind=kind,
            relative_path=_ARTIFACT_PATHS[kind],
            row_count=row_count,
            byte_size=len(payload),
            physical_sha256=_sha256(payload),
        )
        for kind, payload, row_count in payloads
    )
    manifest = build_china_ashare_pilot_package_manifest(
        plan_fingerprint=plan.logical_fingerprint,
        created_at=created_at,
        payload_layer="normalized_library_observations",
        raw_upstream_payload_retained=False,
        plan_document_sha256=_sha256(plan_bytes),
        quality_report_sha256=_sha256(report_bytes),
        quality_report_fingerprint=report.logical_fingerprint,
        artifacts=artifacts,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    plan_directory = root / f"plan={plan.logical_fingerprint}"
    target = plan_directory / f"package={manifest.logical_fingerprint}"

    root.mkdir(mode=0o700, parents=False, exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise ChinaAsharePilotPackageConflictError("pilot custody root is invalid")
    root.chmod(0o700)
    plan_directory.mkdir(mode=0o700, exist_ok=True)
    if plan_directory.is_symlink() or not plan_directory.is_dir():
        raise ChinaAsharePilotPackageConflictError("pilot plan directory is invalid")
    plan_directory.chmod(0o700)

    if target.exists() or target.is_symlink():
        existing = read_china_ashare_pilot_reference_package(package_path=target)
        if (
            existing.manifest != manifest
            or existing.plan != plan
            or existing.quality_report != report
        ):
            raise ChinaAsharePilotPackageConflictError(
                "immutable China A-share pilot package differs"
            )
        return replace(existing, status="already_present")

    staging = plan_directory / f".{target.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise ChinaAsharePilotPackageConflictError("pilot package staging path exists")
    staging.mkdir(mode=0o700)
    try:
        manifests = staging / MANIFEST_DIRECTORY
        manifests.mkdir(mode=0o700)
        _write_file(manifests / PLAN_FILE, plan_bytes)
        _write_file(manifests / QUALITY_REPORT_FILE, report_bytes)
        for artifact, (_, payload, _) in zip(artifacts, payloads, strict=True):
            destination = staging / PurePosixPath(artifact.relative_path)
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            _write_file(destination, payload)
        _write_file(manifests / PACKAGE_MANIFEST_FILE, manifest_bytes)
        _make_directories_owner_only(staging)
        _fsync_tree(staging)
        staging.replace(target)
        _fsync_directory(plan_directory)
        result = read_china_ashare_pilot_reference_package(package_path=target)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(plan_directory)
        raise
    if result.manifest != manifest or result.quality_report != report:
        raise ChinaAsharePilotPackageCorruptionError(
            "pilot package changed after publication"
        )
    return replace(result, status="published")


def read_china_ashare_pilot_reference_package(
    *,
    package_path: Path,
) -> ChinaAsharePilotPackageResultV1:
    package = _validate_package_path(package_path)
    manifest_path = package / MANIFEST_DIRECTORY / PACKAGE_MANIFEST_FILE
    manifest_bytes = _read_regular_file(manifest_path)
    try:
        manifest = ChinaAsharePilotPackageManifestV1.model_validate_json(
            manifest_bytes
        )
        plan_bytes = _read_regular_file(package / MANIFEST_DIRECTORY / PLAN_FILE)
        report_bytes = _read_regular_file(
            package / MANIFEST_DIRECTORY / QUALITY_REPORT_FILE
        )
        plan = ChinaAsharePilotPlanV1.model_validate_json(plan_bytes)
        report = ChinaAsharePilotReferenceQualityReportV1.model_validate_json(
            report_bytes
        )
    except (ValidationError, ValueError, TypeError) as exc:
        raise ChinaAsharePilotPackageCorruptionError(
            "China A-share pilot manifest documents are invalid"
        ) from exc
    if package.parent.name != f"plan={manifest.plan_fingerprint}":
        raise ChinaAsharePilotPackageCorruptionError("pilot plan path identity differs")
    if package.name != f"package={manifest.logical_fingerprint}":
        raise ChinaAsharePilotPackageCorruptionError("pilot package path identity differs")
    if plan.logical_fingerprint != manifest.plan_fingerprint:
        raise ChinaAsharePilotPackageCorruptionError("pilot plan binding differs")
    if _sha256(plan_bytes) != manifest.plan_document_sha256:
        raise ChinaAsharePilotPackageCorruptionError("pilot plan bytes changed")
    if _sha256(report_bytes) != manifest.quality_report_sha256:
        raise ChinaAsharePilotPackageCorruptionError("pilot report bytes changed")
    if report.logical_fingerprint != manifest.quality_report_fingerprint:
        raise ChinaAsharePilotPackageCorruptionError("pilot report binding differs")
    if report.plan_fingerprint != plan.logical_fingerprint:
        raise ChinaAsharePilotPackageCorruptionError("pilot report plan differs")

    expected_files = {
        f"{MANIFEST_DIRECTORY}/{PLAN_FILE}",
        f"{MANIFEST_DIRECTORY}/{QUALITY_REPORT_FILE}",
        f"{MANIFEST_DIRECTORY}/{PACKAGE_MANIFEST_FILE}",
    }
    decoded_artifacts: dict[ChinaAsharePilotArtifactKind, tuple[Any, ...]] = {}
    for artifact in manifest.artifacts:
        expected_files.add(artifact.relative_path)
        payload = _read_regular_file(
            package / PurePosixPath(artifact.relative_path)
        )
        if (
            len(payload) != artifact.byte_size
            or _sha256(payload) != artifact.physical_sha256
        ):
            raise ChinaAsharePilotPackageCorruptionError(
                "pilot artifact custody differs"
            )
        rows = _read_artifact_rows(payload, artifact.artifact_kind)
        decoded_artifacts[artifact.artifact_kind] = rows
        if len(rows) != artifact.row_count:
            raise ChinaAsharePilotPackageCorruptionError(
                "pilot artifact row count differs"
            )

    actual_files: set[str] = set()
    total_bytes = 0
    if stat.S_IMODE(package.stat().st_mode) != 0o700:
        raise ChinaAsharePilotPackageCorruptionError(
            "pilot package directory custody differs"
        )
    for path in package.rglob("*"):
        if path.is_symlink():
            raise ChinaAsharePilotPackageCorruptionError(
                "pilot package contains a symlink"
            )
        if path.is_dir() and stat.S_IMODE(path.stat().st_mode) != 0o700:
            raise ChinaAsharePilotPackageCorruptionError(
                "pilot package directory custody differs"
            )
        if path.is_file():
            actual_files.add(path.relative_to(package).as_posix())
            total_bytes += path.stat().st_size
            if stat.S_IMODE(path.stat().st_mode) != 0o400:
                raise ChinaAsharePilotPackageCorruptionError(
                    "pilot package file custody differs"
                )
    if actual_files != expected_files:
        raise ChinaAsharePilotPackageCorruptionError("pilot package file set differs")
    try:
        captured = CapturedChinaAsharePilotReferenceV1(
            official_current_instruments=decoded_artifacts[
                ChinaAsharePilotArtifactKind.OFFICIAL_CURRENT_INSTRUMENT
            ],
            baostock_instruments=decoded_artifacts[
                ChinaAsharePilotArtifactKind.BAOSTOCK_INSTRUMENT
            ],
            baostock_source_states=decoded_artifacts[
                ChinaAsharePilotArtifactKind.BAOSTOCK_SOURCE_STATE
            ],
            official_lifecycle=decoded_artifacts[
                ChinaAsharePilotArtifactKind.OFFICIAL_LIFECYCLE
            ],
            source_request_count=report.source_request_count,
        )
    except KeyError as exc:
        raise ChinaAsharePilotPackageCorruptionError(
            "pilot package is missing a required reference artifact"
        ) from exc
    return ChinaAsharePilotPackageResultV1(
        manifest=manifest,
        plan=plan,
        quality_report=report,
        captured=captured,
        package_path=package,
        manifest_path=manifest_path,
        manifest_physical_sha256=_sha256(manifest_bytes),
        file_count=len(actual_files),
        total_bytes=total_bytes,
        status="reread",
    )


def publish_china_ashare_pilot_daily_package(
    *,
    custody_root: Path,
    plan: ChinaAsharePilotPlanV1,
    reference_package_fingerprint: str,
    captured: CapturedChinaAsharePilotDailyV1,
    created_at: datetime,
) -> ChinaAsharePilotDailyPackageResultV1:
    """Publish normalized pilot daily evidence without canonical authority."""

    root = _validate_custody_root(custody_root)
    payloads = _prepare_daily_artifact_payloads(plan, captured)
    report = _build_daily_quality_report(
        plan,
        reference_package_fingerprint,
        captured,
        created_at,
    )
    plan_bytes = _canonical_json_bytes(plan.model_dump(mode="json"))
    report_bytes = _canonical_json_bytes(report.model_dump(mode="json"))
    artifacts = tuple(
        ChinaAsharePilotArtifactV1(
            artifact_kind=kind,
            relative_path=_ARTIFACT_PATHS[kind],
            row_count=row_count,
            byte_size=len(payload),
            physical_sha256=_sha256(payload),
        )
        for kind, payload, row_count in payloads
    )
    manifest = build_china_ashare_pilot_daily_package_manifest(
        plan_fingerprint=plan.logical_fingerprint,
        reference_package_fingerprint=reference_package_fingerprint,
        created_at=created_at,
        payload_layer="normalized_library_observations",
        raw_upstream_payload_retained=False,
        plan_document_sha256=_sha256(plan_bytes),
        quality_report_sha256=_sha256(report_bytes),
        quality_report_fingerprint=report.logical_fingerprint,
        artifacts=artifacts,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    plan_directory = root / f"plan={plan.logical_fingerprint}"
    target = plan_directory / f"daily-package={manifest.logical_fingerprint}"

    root.mkdir(mode=0o700, parents=False, exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise ChinaAsharePilotPackageConflictError("pilot custody root is invalid")
    root.chmod(0o700)
    plan_directory.mkdir(mode=0o700, exist_ok=True)
    if plan_directory.is_symlink() or not plan_directory.is_dir():
        raise ChinaAsharePilotPackageConflictError("pilot plan directory is invalid")
    plan_directory.chmod(0o700)

    if target.exists() or target.is_symlink():
        existing = read_china_ashare_pilot_daily_package(package_path=target)
        if (
            existing.manifest != manifest
            or existing.plan != plan
            or existing.quality_report != report
        ):
            raise ChinaAsharePilotPackageConflictError(
                "immutable China A-share daily pilot package differs"
            )
        return replace(existing, status="already_present")

    staging = plan_directory / f".{target.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise ChinaAsharePilotPackageConflictError("daily pilot staging path exists")
    staging.mkdir(mode=0o700)
    try:
        manifests = staging / MANIFEST_DIRECTORY
        manifests.mkdir(mode=0o700)
        _write_file(manifests / PLAN_FILE, plan_bytes)
        _write_file(manifests / DAILY_QUALITY_REPORT_FILE, report_bytes)
        for artifact, (_, payload, _) in zip(artifacts, payloads, strict=True):
            destination = staging / PurePosixPath(artifact.relative_path)
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            _write_file(destination, payload)
        _write_file(manifests / DAILY_PACKAGE_MANIFEST_FILE, manifest_bytes)
        _make_directories_owner_only(staging)
        _fsync_tree(staging)
        staging.replace(target)
        _fsync_directory(plan_directory)
        result = read_china_ashare_pilot_daily_package(package_path=target)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(plan_directory)
        raise
    if result.manifest != manifest or result.quality_report != report:
        raise ChinaAsharePilotPackageCorruptionError(
            "daily pilot package changed after publication"
        )
    return replace(result, status="published")


def read_china_ashare_pilot_daily_package(
    *,
    package_path: Path,
) -> ChinaAsharePilotDailyPackageResultV1:
    package = _validate_daily_package_path(package_path)
    manifest_path = package / MANIFEST_DIRECTORY / DAILY_PACKAGE_MANIFEST_FILE
    manifest_bytes = _read_regular_file(manifest_path)
    try:
        manifest = ChinaAsharePilotDailyPackageManifestV1.model_validate_json(
            manifest_bytes
        )
        plan_bytes = _read_regular_file(package / MANIFEST_DIRECTORY / PLAN_FILE)
        report_bytes = _read_regular_file(
            package / MANIFEST_DIRECTORY / DAILY_QUALITY_REPORT_FILE
        )
        plan = ChinaAsharePilotPlanV1.model_validate_json(plan_bytes)
        report = ChinaAsharePilotDailyQualityReportV1.model_validate_json(
            report_bytes
        )
    except (ValidationError, ValueError, TypeError) as exc:
        raise ChinaAsharePilotPackageCorruptionError(
            "China A-share daily pilot manifest documents are invalid"
        ) from exc
    if package.parent.name != f"plan={manifest.plan_fingerprint}":
        raise ChinaAsharePilotPackageCorruptionError("daily pilot plan path differs")
    if package.name != f"daily-package={manifest.logical_fingerprint}":
        raise ChinaAsharePilotPackageCorruptionError("daily pilot path identity differs")
    if plan.logical_fingerprint != manifest.plan_fingerprint:
        raise ChinaAsharePilotPackageCorruptionError("daily pilot plan binding differs")
    if report.plan_fingerprint != plan.logical_fingerprint:
        raise ChinaAsharePilotPackageCorruptionError("daily pilot report plan differs")
    if report.reference_package_fingerprint != manifest.reference_package_fingerprint:
        raise ChinaAsharePilotPackageCorruptionError(
            "daily pilot reference-package binding differs"
        )
    if _sha256(plan_bytes) != manifest.plan_document_sha256:
        raise ChinaAsharePilotPackageCorruptionError("daily pilot plan bytes changed")
    if _sha256(report_bytes) != manifest.quality_report_sha256:
        raise ChinaAsharePilotPackageCorruptionError("daily pilot report bytes changed")
    if report.logical_fingerprint != manifest.quality_report_fingerprint:
        raise ChinaAsharePilotPackageCorruptionError("daily pilot report binding differs")

    expected_files = {
        f"{MANIFEST_DIRECTORY}/{PLAN_FILE}",
        f"{MANIFEST_DIRECTORY}/{DAILY_QUALITY_REPORT_FILE}",
        f"{MANIFEST_DIRECTORY}/{DAILY_PACKAGE_MANIFEST_FILE}",
    }
    decoded: dict[ChinaAsharePilotArtifactKind, tuple[Any, ...]] = {}
    for artifact in manifest.artifacts:
        expected_files.add(artifact.relative_path)
        payload = _read_regular_file(package / PurePosixPath(artifact.relative_path))
        if (
            len(payload) != artifact.byte_size
            or _sha256(payload) != artifact.physical_sha256
        ):
            raise ChinaAsharePilotPackageCorruptionError(
                "daily pilot artifact custody differs"
            )
        rows = _read_daily_artifact_rows(payload, artifact.artifact_kind)
        if len(rows) != artifact.row_count:
            raise ChinaAsharePilotPackageCorruptionError(
                "daily pilot artifact row count differs"
            )
        decoded[artifact.artifact_kind] = rows

    actual_files: set[str] = set()
    total_bytes = 0
    if stat.S_IMODE(package.stat().st_mode) != 0o700:
        raise ChinaAsharePilotPackageCorruptionError(
            "daily pilot directory custody differs"
        )
    for path in package.rglob("*"):
        if path.is_symlink():
            raise ChinaAsharePilotPackageCorruptionError(
                "daily pilot package contains a symlink"
            )
        if path.is_dir() and stat.S_IMODE(path.stat().st_mode) != 0o700:
            raise ChinaAsharePilotPackageCorruptionError(
                "daily pilot directory custody differs"
            )
        if path.is_file():
            actual_files.add(path.relative_to(package).as_posix())
            total_bytes += path.stat().st_size
            if stat.S_IMODE(path.stat().st_mode) != 0o400:
                raise ChinaAsharePilotPackageCorruptionError(
                    "daily pilot file custody differs"
                )
    if actual_files != expected_files:
        raise ChinaAsharePilotPackageCorruptionError(
            "daily pilot package file set differs"
        )
    try:
        query = ChinaAshareSourceDailyQuery(
            source_security_ids=report.daily_requested_ids,
            start_date=plan.history_start_date,
            end_date=plan.history_end_date,
        )
        daily_batch = ChinaAshareDailySourceBatchV1(
            provider_id=BAOSTOCK_ASHARE_PROVIDER_ID,
            query=query,
            bars=decoded[ChinaAsharePilotArtifactKind.DAILY_BAR],
            trading_states=decoded[
                ChinaAsharePilotArtifactKind.DAILY_TRADING_STATE
            ],
            source_request_count=len(report.daily_requested_ids),
        )
        captured = CapturedChinaAsharePilotDailyV1(
            identity_decisions=decoded[
                ChinaAsharePilotArtifactKind.IDENTITY_DECISION
            ],
            daily_batch=daily_batch,
            adjustment_observations=decoded[
                ChinaAsharePilotArtifactKind.ADJUSTMENT_FACTOR
            ],
            source_request_count=report.source_request_count,
        )
    except (KeyError, ValidationError, ValueError, TypeError) as exc:
        raise ChinaAsharePilotPackageCorruptionError(
            "daily pilot artifact set cannot be reconstructed"
        ) from exc
    _prepare_daily_artifact_payloads(plan, captured)
    return ChinaAsharePilotDailyPackageResultV1(
        manifest=manifest,
        plan=plan,
        quality_report=report,
        captured=captured,
        package_path=package,
        manifest_path=manifest_path,
        manifest_physical_sha256=_sha256(manifest_bytes),
        file_count=len(actual_files),
        total_bytes=total_bytes,
        status="reread",
    )


def _prepare_artifact_payloads(
    plan: ChinaAsharePilotPlanV1,
    captured: CapturedChinaAsharePilotReferenceV1,
) -> tuple[tuple[ChinaAsharePilotArtifactKind, bytes, int], ...]:
    if captured.source_request_count < 1:
        raise ChinaAsharePilotPackageConflictError(
            "pilot source request count must be positive"
        )
    if captured.source_request_count > plan.maximum_source_requests:
        raise ChinaAsharePilotPackageConflictError(
            "pilot source request count exceeds its ceiling"
        )
    anchor_ids = {item.source_security_id for item in plan.anchors}
    lifecycle_keys = set(plan.lifecycle_subject_keys)
    groups: tuple[tuple[ChinaAsharePilotArtifactKind, tuple[Any, ...], set[str]], ...] = (
        (
            ChinaAsharePilotArtifactKind.BAOSTOCK_INSTRUMENT,
            captured.baostock_instruments,
            anchor_ids,
        ),
        (
            ChinaAsharePilotArtifactKind.BAOSTOCK_SOURCE_STATE,
            captured.baostock_source_states,
            anchor_ids,
        ),
        (
            ChinaAsharePilotArtifactKind.OFFICIAL_CURRENT_INSTRUMENT,
            captured.official_current_instruments,
            anchor_ids,
        ),
        (
            ChinaAsharePilotArtifactKind.OFFICIAL_LIFECYCLE,
            captured.official_lifecycle,
            lifecycle_keys,
        ),
    )
    output: list[tuple[ChinaAsharePilotArtifactKind, bytes, int]] = []
    for kind, rows, allowed_ids in groups:
        keys = tuple(_row_key(kind, row) for row in rows)
        if keys != tuple(sorted(set(keys))):
            raise ChinaAsharePilotPackageConflictError(
                "pilot artifact rows must be unique and sorted"
            )
        if any(_row_scope_key(kind, row) not in allowed_ids for row in rows):
            raise ChinaAsharePilotPackageConflictError(
                "pilot artifact contains an unplanned security"
            )
        payload = _canonical_json_bytes(
            {
                "artifact_kind": kind.value,
                "rows": [row.model_dump(mode="json") for row in rows],
                "schema_version": "1.0",
            }
        )
        output.append((kind, payload, len(rows)))
    instrument_ids = tuple(
        item.source_security_id for item in captured.baostock_instruments
    )
    state_ids = tuple(
        item.source_security_id for item in captured.baostock_source_states
    )
    if instrument_ids != state_ids:
        raise ChinaAsharePilotPackageConflictError(
            "BaoStock pilot instrument and state rows must align"
        )
    return tuple(output)


def _prepare_daily_artifact_payloads(
    plan: ChinaAsharePilotPlanV1,
    captured: CapturedChinaAsharePilotDailyV1,
) -> tuple[tuple[ChinaAsharePilotArtifactKind, bytes, int], ...]:
    decisions = captured.identity_decisions
    decision_ids = tuple(item.source_security_id for item in decisions)
    planned_ids = tuple(item.source_security_id for item in plan.anchors)
    if decision_ids != planned_ids:
        raise ChinaAsharePilotPackageConflictError(
            "daily pilot identity decisions differ from the exact plan"
        )
    bound = tuple(
        item
        for item in decisions
        if item.disposition
        is ChinaAsharePilotIdentityDisposition.BOUND_FOR_DAILY_CAPTURE
    )
    bound_ids = tuple(item.source_security_id for item in bound)
    batch = captured.daily_batch
    if batch.provider_id != BAOSTOCK_ASHARE_PROVIDER_ID:
        raise ChinaAsharePilotPackageConflictError(
            "daily pilot provider differs from the qualified source"
        )
    if batch.query.source_security_ids != bound_ids:
        raise ChinaAsharePilotPackageConflictError(
            "daily pilot query differs from bound identities"
        )
    if (
        batch.query.start_date != plan.history_start_date
        or batch.query.end_date != plan.history_end_date
    ):
        raise ChinaAsharePilotPackageConflictError(
            "daily pilot query interval differs from the plan"
        )
    expected_requests = len(bound_ids) * 2
    if captured.source_request_count != expected_requests:
        raise ChinaAsharePilotPackageConflictError(
            "daily pilot request count differs from the exact request shape"
        )
    instrument_ids = {
        item.pilot_instrument_id for item in bound if item.pilot_instrument_id is not None
    }
    state_instrument_ids = {item.instrument_id for item in batch.trading_states}
    if state_instrument_ids != instrument_ids:
        raise ChinaAsharePilotPackageConflictError(
            "daily pilot state coverage differs from bound identities"
        )
    if any(item.instrument_id not in instrument_ids for item in batch.bars):
        raise ChinaAsharePilotPackageConflictError(
            "daily pilot bar carries an unbound instrument"
        )
    if any(
        item.instrument_id not in instrument_ids
        for item in captured.adjustment_observations
    ):
        raise ChinaAsharePilotPackageConflictError(
            "daily pilot adjustment carries an unbound instrument"
        )

    groups: tuple[tuple[ChinaAsharePilotArtifactKind, tuple[Any, ...]], ...] = (
        (
            ChinaAsharePilotArtifactKind.ADJUSTMENT_FACTOR,
            captured.adjustment_observations,
        ),
        (ChinaAsharePilotArtifactKind.DAILY_BAR, batch.bars),
        (
            ChinaAsharePilotArtifactKind.DAILY_TRADING_STATE,
            batch.trading_states,
        ),
        (ChinaAsharePilotArtifactKind.IDENTITY_DECISION, decisions),
    )
    output: list[tuple[ChinaAsharePilotArtifactKind, bytes, int]] = []
    for kind, rows in groups:
        keys = tuple(_daily_row_key(kind, row) for row in rows)
        if keys != tuple(sorted(set(keys))):
            raise ChinaAsharePilotPackageConflictError(
                "daily pilot artifact rows must be unique and sorted"
            )
        payload = _canonical_json_bytes(
            {
                "artifact_kind": kind.value,
                "rows": [row.model_dump(mode="json") for row in rows],
                "schema_version": "1.0",
            }
        )
        output.append((kind, payload, len(rows)))
    return tuple(output)


def _build_daily_quality_report(
    plan: ChinaAsharePilotPlanV1,
    reference_package_fingerprint: str,
    captured: CapturedChinaAsharePilotDailyV1,
    evaluated_at: datetime,
) -> ChinaAsharePilotDailyQualityReportV1:
    bound_ids = tuple(
        item.source_security_id
        for item in captured.identity_decisions
        if item.disposition
        is ChinaAsharePilotIdentityDisposition.BOUND_FOR_DAILY_CAPTURE
    )
    quarantined_ids = tuple(
        item.source_security_id
        for item in captured.identity_decisions
        if item.disposition is ChinaAsharePilotIdentityDisposition.QUARANTINED
    )
    states = captured.daily_batch.trading_states
    suspended_count = sum(
        item.trading_status is ChinaAshareTradingStatus.SUSPENDED for item in states
    )
    risk_warning_count = sum(
        item.risk_warning_status
        not in {
            ChinaAshareRiskWarningStatus.NONE,
            ChinaAshareRiskWarningStatus.UNKNOWN,
        }
        for item in states
    )
    reasons = {
        "adjustment_semantics_not_reconciled",
        "calendar_not_reconciled",
        "canonical_identity_not_authorized",
        "price_limit_rules_not_reconciled",
        "raw_upstream_payload_not_retained",
        "source_available_time_unreported",
    }
    if quarantined_ids:
        reasons.add("planned_anchor_quarantined")
    return build_china_ashare_pilot_daily_quality_report(
        plan_fingerprint=plan.logical_fingerprint,
        reference_package_fingerprint=reference_package_fingerprint,
        evaluated_at=evaluated_at,
        planned_anchor_ids=tuple(item.source_security_id for item in plan.anchors),
        bound_for_daily_capture_ids=bound_ids,
        quarantined_ids=quarantined_ids,
        daily_requested_ids=captured.daily_batch.query.source_security_ids,
        daily_bar_count=len(captured.daily_batch.bars),
        daily_state_count=len(states),
        suspended_state_count=suspended_count,
        risk_warning_state_count=risk_warning_count,
        adjustment_observation_count=len(captured.adjustment_observations),
        source_request_count=captured.source_request_count,
        source_request_ceiling=len(bound_ids) * 2,
        source_capture_complete=bool(bound_ids) and bool(states),
        diverse_scenarios_observed=all(
            (
                suspended_count > 0,
                risk_warning_count > 0,
                bool(captured.adjustment_observations),
            )
        ),
        canonical_identity_authorized=False,
        calendar_reconciled=False,
        price_limit_rules_reconciled=False,
        adjustment_semantics_reconciled=False,
        research_backtest_authorized=False,
        canonical_apply_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
        reason_codes=tuple(sorted(reasons)),
    )


def _build_quality_report(
    plan: ChinaAsharePilotPlanV1,
    captured: CapturedChinaAsharePilotReferenceV1,
    evaluated_at: datetime,
) -> ChinaAsharePilotReferenceQualityReportV1:
    planned_ids = tuple(item.source_security_id for item in plan.anchors)
    official_ids = tuple(
        item.source_security_id for item in captured.official_current_instruments
    )
    baostock_ids = tuple(
        item.source_security_id for item in captured.baostock_instruments
    )
    lifecycle_observed_keys = tuple(
        sorted({item.source_subject_key for item in captured.official_lifecycle})
    )
    reasons = {
        "adjustment_semantics_not_reconciled",
        "daily_history_not_captured",
        "raw_upstream_payload_not_retained",
        "stable_identity_not_adjudicated",
    }
    if set(planned_ids) - set(official_ids):
        reasons.add("official_reference_evidence_incomplete")
    if set(planned_ids) - set(baostock_ids):
        reasons.add("baostock_board_coverage_incomplete")
    if set(plan.lifecycle_subject_keys) - set(lifecycle_observed_keys):
        reasons.add("lifecycle_reference_evidence_incomplete")
    if any(
        item.event_type
        is ChinaAshareLifecycleEventType.PAUSED_OR_TERMINATED_LISTING
        for item in captured.official_lifecycle
    ):
        reasons.add("lifecycle_source_semantics_require_adjudication")
    return build_china_ashare_pilot_quality_report(
        plan_fingerprint=plan.logical_fingerprint,
        evaluated_at=evaluated_at,
        planned_anchor_ids=planned_ids,
        official_current_observed_ids=official_ids,
        baostock_snapshot_observed_ids=baostock_ids,
        lifecycle_target_keys=plan.lifecycle_subject_keys,
        lifecycle_observed_keys=lifecycle_observed_keys,
        official_current_missing_ids=tuple(
            sorted(set(planned_ids) - set(official_ids))
        ),
        baostock_snapshot_missing_ids=tuple(
            sorted(set(planned_ids) - set(baostock_ids))
        ),
        lifecycle_missing_keys=tuple(
            sorted(set(plan.lifecycle_subject_keys) - set(lifecycle_observed_keys))
        ),
        source_request_count=captured.source_request_count,
        source_request_ceiling=plan.maximum_source_requests,
        reference_evidence_complete=not (
            set(planned_ids) - set(official_ids)
            or set(plan.lifecycle_subject_keys) - set(lifecycle_observed_keys)
        ),
        stable_identity_adjudicated=False,
        daily_history_captured=False,
        adjustment_semantics_reconciled=False,
        research_backtest_authorized=False,
        canonical_apply_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
        reason_codes=tuple(sorted(reasons)),
    )


def _read_artifact_rows(
    payload: bytes,
    kind: ChinaAsharePilotArtifactKind,
) -> tuple[Any, ...]:
    try:
        document = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ChinaAsharePilotPackageCorruptionError(
            "pilot artifact JSON is invalid"
        ) from exc
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != "1.0"
        or document.get("artifact_kind") != kind.value
        or not isinstance(document.get("rows"), list)
    ):
        raise ChinaAsharePilotPackageCorruptionError(
            "pilot artifact document is invalid"
        )
    row_model = {
        ChinaAsharePilotArtifactKind.OFFICIAL_CURRENT_INSTRUMENT: (
            ChinaAshareInstrumentSourceObservationV1
        ),
        ChinaAsharePilotArtifactKind.BAOSTOCK_INSTRUMENT: (
            ChinaAshareInstrumentSourceObservationV1
        ),
        ChinaAsharePilotArtifactKind.BAOSTOCK_SOURCE_STATE: (
            ChinaAshareSourceSecuritySnapshotStateV1
        ),
        ChinaAsharePilotArtifactKind.OFFICIAL_LIFECYCLE: (
            ChinaAshareLifecycleSourceObservationV1
        ),
    }[kind]
    try:
        rows = tuple(row_model.model_validate(item) for item in document["rows"])
    except (ValidationError, ValueError, TypeError) as exc:
        raise ChinaAsharePilotPackageCorruptionError(
            "pilot artifact row is invalid"
        ) from exc
    keys = tuple(_row_key(kind, row) for row in rows)
    if keys != tuple(sorted(set(keys))):
        raise ChinaAsharePilotPackageCorruptionError(
            "pilot artifact row order differs"
        )
    return rows


def _read_daily_artifact_rows(
    payload: bytes,
    kind: ChinaAsharePilotArtifactKind,
) -> tuple[Any, ...]:
    try:
        document = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ChinaAsharePilotPackageCorruptionError(
            "daily pilot artifact JSON is invalid"
        ) from exc
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != "1.0"
        or document.get("artifact_kind") != kind.value
        or not isinstance(document.get("rows"), list)
    ):
        raise ChinaAsharePilotPackageCorruptionError(
            "daily pilot artifact document is invalid"
        )
    row_model = {
        ChinaAsharePilotArtifactKind.ADJUSTMENT_FACTOR: (
            ChinaAshareAdjustmentFactorObservationV1
        ),
        ChinaAsharePilotArtifactKind.DAILY_BAR: ChinaAshareDailyBarV1,
        ChinaAsharePilotArtifactKind.DAILY_TRADING_STATE: (
            ChinaAshareDailyTradingStateV1
        ),
        ChinaAsharePilotArtifactKind.IDENTITY_DECISION: (
            ChinaAsharePilotIdentityDecisionV1
        ),
    }.get(kind)
    if row_model is None:
        raise ChinaAsharePilotPackageCorruptionError(
            "unexpected daily pilot artifact kind"
        )
    try:
        rows = tuple(row_model.model_validate(item) for item in document["rows"])
    except (ValidationError, ValueError, TypeError) as exc:
        raise ChinaAsharePilotPackageCorruptionError(
            "daily pilot artifact row is invalid"
        ) from exc
    keys = tuple(_daily_row_key(kind, row) for row in rows)
    if keys != tuple(sorted(set(keys))):
        raise ChinaAsharePilotPackageCorruptionError(
            "daily pilot artifact row order differs"
        )
    return rows


def _row_key(kind: ChinaAsharePilotArtifactKind, row: Any) -> tuple[str, ...]:
    if kind is ChinaAsharePilotArtifactKind.OFFICIAL_LIFECYCLE:
        return (
            row.source_subject_key,
            row.event_date.isoformat(),
            row.list_date.isoformat() if row.list_date is not None else "",
            f"{row.source_row_sequence:09d}",
        )
    return (row.source_security_id,)


def _row_scope_key(kind: ChinaAsharePilotArtifactKind, row: Any) -> str:
    if kind is ChinaAsharePilotArtifactKind.OFFICIAL_LIFECYCLE:
        return row.source_subject_key
    return row.source_security_id


def _daily_row_key(kind: ChinaAsharePilotArtifactKind, row: Any) -> tuple[str, ...]:
    if kind is ChinaAsharePilotArtifactKind.IDENTITY_DECISION:
        return (row.source_security_id,)
    return (str(row.instrument_id), row.session_date.isoformat())


def _validate_custody_root(path: Path) -> Path:
    root = path.absolute()
    if root.name != "china-a-share-research-pilot" or Path("/tmp") not in root.parents:
        raise ChinaAsharePilotPackageConflictError(
            "pilot custody must use a dedicated path below /tmp"
        )
    if root.exists() and (root.is_symlink() or not root.is_dir()):
        raise ChinaAsharePilotPackageConflictError("pilot custody root is invalid")
    if not root.parent.is_dir() or root.parent.is_symlink():
        raise ChinaAsharePilotPackageConflictError(
            "pilot custody parent must be an existing non-symlink directory"
        )
    return root


def _validate_package_path(path: Path) -> Path:
    package = path.absolute()
    if (
        Path("/tmp") not in package.parents
        or not package.name.startswith("package=")
        or not package.parent.name.startswith("plan=")
        or package.parent.parent.name != "china-a-share-research-pilot"
        or not package.is_dir()
        or package.is_symlink()
    ):
        raise ChinaAsharePilotPackageCorruptionError("pilot package path is invalid")
    return package


def _validate_daily_package_path(path: Path) -> Path:
    package = path.absolute()
    if (
        Path("/tmp") not in package.parents
        or not package.name.startswith("daily-package=")
        or not package.parent.name.startswith("plan=")
        or package.parent.parent.name != "china-a-share-research-pilot"
        or not package.is_dir()
        or package.is_symlink()
    ):
        raise ChinaAsharePilotPackageCorruptionError(
            "daily pilot package path is invalid"
        )
    return package


def _read_regular_file(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ChinaAsharePilotPackageCorruptionError("pilot package file is invalid")
    size = path.stat().st_size
    if size < 1 or size > MAXIMUM_JSON_BYTES:
        raise ChinaAsharePilotPackageCorruptionError(
            "pilot package file size is invalid"
        )
    return path.read_bytes()


def _canonical_json_bytes(value: object) -> bytes:
    try:
        payload = (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ChinaAsharePilotPackageConflictError(
            "pilot evidence is not canonical JSON"
        ) from exc
    if len(payload) > MAXIMUM_JSON_BYTES:
        raise ChinaAsharePilotPackageConflictError(
            "pilot evidence exceeds its size ceiling"
        )
    return payload


def _write_file(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o400)


def _make_directories_owner_only(root: Path) -> None:
    for path in sorted(
        (item for item in root.rglob("*") if item.is_dir()),
        reverse=True,
    ):
        path.chmod(0o700)
    root.chmod(0o700)


def _fsync_tree(root: Path) -> None:
    for path in sorted(
        (item for item in root.rglob("*") if item.is_dir()),
        reverse=True,
    ):
        _fsync_directory(path)
    _fsync_directory(root)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
