"""Owner-only immutable custody for A-share corporate-action reconciliation."""

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

from tip_api.contracts.china_ashare.v1.corporate_actions import (
    ChinaAshareCorporateActionObservationV1,
    ChinaAshareCorporateActionPackageManifestV1,
    ChinaAshareCorporateActionRawArtifactV1,
    ChinaAshareCorporateActionReconciliationReportV1,
    build_corporate_action_package_manifest,
)
from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareAdjustmentFactorObservationV1,
)
from tip_api.providers.china_ashare.cninfo_corporate_action_adapter import (
    CapturedCninfoCorporateActionsV1,
)
from tip_api.services.china_ashare_corporate_action_reconciliation import (
    ChinaAshareDistributionCrosscheckV1,
)


ACTIONS_FILE = "normalized/corporate-actions.json"
ADJUSTMENTS_FILE = "normalized/full-adjustment-history.json"
CROSSCHECKS_FILE = "normalized/distribution-crosschecks.json"
REPORT_FILE = "corporate-action-reconciliation-report.json"
MANIFEST_FILE = "corporate-action-evidence-manifest.json"
MAXIMUM_FILE_BYTES = 64 * 1024 * 1024


class ChinaAshareCorporateActionPackageError(RuntimeError):
    """Base failure for corporate-action evidence custody."""


class ChinaAshareCorporateActionPackageConflictError(
    ChinaAshareCorporateActionPackageError
):
    """Raised when immutable package scope or content conflicts."""


class ChinaAshareCorporateActionPackageCorruptionError(
    ChinaAshareCorporateActionPackageError
):
    """Raised when exact reread detects changed or malformed custody."""


@dataclass(frozen=True, slots=True)
class ChinaAshareCorporateActionPackageResultV1:
    manifest: ChinaAshareCorporateActionPackageManifestV1
    actions: tuple[ChinaAshareCorporateActionObservationV1, ...]
    adjustments: tuple[ChinaAshareAdjustmentFactorObservationV1, ...]
    crosschecks: tuple[ChinaAshareDistributionCrosscheckV1, ...]
    report: ChinaAshareCorporateActionReconciliationReportV1
    package_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_corporate_action_package(
    *,
    custody_root: Path,
    daily_package_fingerprint: str,
    captured_sources: tuple[CapturedCninfoCorporateActionsV1, ...],
    actions: tuple[ChinaAshareCorporateActionObservationV1, ...],
    adjustments: tuple[ChinaAshareAdjustmentFactorObservationV1, ...],
    crosschecks: tuple[ChinaAshareDistributionCrosscheckV1, ...],
    report: ChinaAshareCorporateActionReconciliationReportV1,
    created_at: datetime,
) -> ChinaAshareCorporateActionPackageResultV1:
    root = _validate_root(custody_root)
    ordered_sources = tuple(
        sorted(
            captured_sources,
            key=lambda item: (item.source_security_id, item.source_kind.value),
        )
    )
    ordered_actions = tuple(
        sorted(actions, key=lambda item: (str(item.instrument_id), item.ex_date))
    )
    ordered_adjustments = tuple(
        sorted(
            adjustments,
            key=lambda item: (str(item.instrument_id), item.session_date),
        )
    )
    ordered_crosschecks = tuple(
        sorted(crosschecks, key=lambda item: (item.source_security_id, item.ex_date))
    )
    _validate_inputs(
        daily_package_fingerprint=daily_package_fingerprint,
        captured_sources=ordered_sources,
        actions=ordered_actions,
        adjustments=ordered_adjustments,
        crosschecks=ordered_crosschecks,
        report=report,
    )
    actions_bytes = _canonical_json_bytes(
        {"schema_version": "1.0", "rows": [item.model_dump(mode="json") for item in ordered_actions]}
    )
    adjustments_bytes = _canonical_json_bytes(
        {"schema_version": "1.0", "rows": [item.model_dump(mode="json") for item in ordered_adjustments]}
    )
    crosschecks_bytes = _canonical_json_bytes(
        {
            "schema_version": "1.0",
            "rows": [_crosscheck_json(item) for item in ordered_crosschecks],
        }
    )
    report_bytes = _canonical_json_bytes(report.model_dump(mode="json"))
    artifacts = tuple(
        ChinaAshareCorporateActionRawArtifactV1(
            source_kind=item.source_kind.value,
            source_security_id=item.source_security_id,
            retrieved_at=item.retrieved_at,
            final_url=item.final_url,
            content_type=item.content_type,
            relative_path=(
                f"raw/{item.source_security_id.replace('.', '-')}-"
                f"{item.source_kind.value}.json"
            ),
            byte_size=len(item.raw_bytes),
            physical_sha256=_sha256(item.raw_bytes),
        )
        for item in ordered_sources
    )
    manifest = build_corporate_action_package_manifest(
        daily_package_fingerprint=daily_package_fingerprint,
        created_at=created_at,
        actions_document_sha256=_sha256(actions_bytes),
        adjustments_document_sha256=_sha256(adjustments_bytes),
        crosschecks_document_sha256=_sha256(crosschecks_bytes),
        report_document_sha256=_sha256(report_bytes),
        report_fingerprint=report.logical_fingerprint,
        raw_artifacts=artifacts,
        raw_upstream_payload_retained=True,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    scope = root / f"corporate-action-daily={daily_package_fingerprint}"
    target = scope / f"corporate-action-package={manifest.logical_fingerprint}"
    if target.exists():
        existing = read_china_ashare_corporate_action_package(package_path=target)
        if existing.manifest != manifest:
            raise ChinaAshareCorporateActionPackageConflictError(
                "existing corporate-action package differs"
            )
        return existing
    scope.mkdir(mode=0o700, parents=True, exist_ok=True)
    if scope.is_symlink():
        raise ChinaAshareCorporateActionPackageConflictError(
            "corporate-action scope cannot be a symlink"
        )
    staging = Path(tempfile.mkdtemp(prefix=".corporate-action-", dir=scope))
    try:
        (staging / "normalized").mkdir(mode=0o700)
        (staging / "raw").mkdir(mode=0o700)
        _write_file(staging / ACTIONS_FILE, actions_bytes)
        _write_file(staging / ADJUSTMENTS_FILE, adjustments_bytes)
        _write_file(staging / CROSSCHECKS_FILE, crosschecks_bytes)
        _write_file(staging / REPORT_FILE, report_bytes)
        for artifact, captured in zip(artifacts, ordered_sources, strict=True):
            _write_file(staging / PurePosixPath(artifact.relative_path), captured.raw_bytes)
        _write_file(staging / MANIFEST_FILE, manifest_bytes)
        _owner_only(staging)
        _fsync_tree(staging)
        staging.rename(target)
        _fsync_directory(scope)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    result = read_china_ashare_corporate_action_package(package_path=target)
    if result.manifest != manifest or result.report != report:
        raise ChinaAshareCorporateActionPackageCorruptionError(
            "corporate-action package changed after publication"
        )
    return replace(result, status="published")


def read_china_ashare_corporate_action_package(
    *, package_path: Path
) -> ChinaAshareCorporateActionPackageResultV1:
    package = _validate_package(package_path)
    manifest_payload = _read_file(package / MANIFEST_FILE)
    try:
        manifest = ChinaAshareCorporateActionPackageManifestV1.model_validate_json(
            manifest_payload
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareCorporateActionPackageCorruptionError(
            "corporate-action manifest is invalid"
        ) from exc
    if package.parent.name != (
        f"corporate-action-daily={manifest.daily_package_fingerprint}"
    ):
        raise ChinaAshareCorporateActionPackageCorruptionError(
            "corporate-action scope path differs"
        )
    if package.name != f"corporate-action-package={manifest.logical_fingerprint}":
        raise ChinaAshareCorporateActionPackageCorruptionError(
            "corporate-action package identity differs"
        )
    actions_payload = _read_file(package / ACTIONS_FILE)
    adjustments_payload = _read_file(package / ADJUSTMENTS_FILE)
    crosschecks_payload = _read_file(package / CROSSCHECKS_FILE)
    report_payload = _read_file(package / REPORT_FILE)
    checks = (
        (actions_payload, manifest.actions_document_sha256, "actions"),
        (adjustments_payload, manifest.adjustments_document_sha256, "adjustments"),
        (crosschecks_payload, manifest.crosschecks_document_sha256, "crosschecks"),
        (report_payload, manifest.report_document_sha256, "report"),
    )
    for payload, expected, name in checks:
        if _sha256(payload) != expected:
            raise ChinaAshareCorporateActionPackageCorruptionError(
                f"corporate-action {name} bytes changed"
            )
    try:
        actions = tuple(
            ChinaAshareCorporateActionObservationV1.model_validate(item)
            for item in _rows(actions_payload)
        )
        adjustments = tuple(
            ChinaAshareAdjustmentFactorObservationV1.model_validate(item)
            for item in _rows(adjustments_payload)
        )
        crosschecks = tuple(_crosscheck_from_json(item) for item in _rows(crosschecks_payload))
        report = ChinaAshareCorporateActionReconciliationReportV1.model_validate_json(
            report_payload
        )
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ChinaAshareCorporateActionPackageCorruptionError(
            "corporate-action normalized document is invalid"
        ) from exc
    if report.logical_fingerprint != manifest.report_fingerprint:
        raise ChinaAshareCorporateActionPackageCorruptionError(
            "corporate-action report fingerprint differs"
        )
    raw_paths: list[str] = []
    for artifact in manifest.raw_artifacts:
        payload = _read_file(package / PurePosixPath(artifact.relative_path))
        if len(payload) != artifact.byte_size or _sha256(payload) != artifact.physical_sha256:
            raise ChinaAshareCorporateActionPackageCorruptionError(
                "corporate-action raw artifact bytes changed"
            )
        raw_paths.append(artifact.relative_path)
    expected_files = {
        ACTIONS_FILE,
        ADJUSTMENTS_FILE,
        CROSSCHECKS_FILE,
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
        raise ChinaAshareCorporateActionPackageCorruptionError(
            "corporate-action package file set differs"
        )
    files = tuple(item for item in package.rglob("*") if item.is_file())
    return ChinaAshareCorporateActionPackageResultV1(
        manifest=manifest,
        actions=actions,
        adjustments=adjustments,
        crosschecks=crosschecks,
        report=report,
        package_path=package,
        manifest_path=package / MANIFEST_FILE,
        manifest_physical_sha256=_sha256(manifest_payload),
        file_count=len(files),
        total_bytes=sum(item.stat().st_size for item in files),
        status="exact_reread_complete",
    )


def _validate_inputs(
    *,
    daily_package_fingerprint: str,
    captured_sources: tuple[CapturedCninfoCorporateActionsV1, ...],
    actions: tuple[ChinaAshareCorporateActionObservationV1, ...],
    adjustments: tuple[ChinaAshareAdjustmentFactorObservationV1, ...],
    crosschecks: tuple[ChinaAshareDistributionCrosscheckV1, ...],
    report: ChinaAshareCorporateActionReconciliationReportV1,
) -> None:
    if report.daily_package_fingerprint != daily_package_fingerprint:
        raise ChinaAshareCorporateActionPackageConflictError(
            "corporate-action report differs from daily package"
        )
    source_keys = tuple(
        (item.source_security_id, item.source_kind.value) for item in captured_sources
    )
    if source_keys != tuple(sorted(set(source_keys))):
        raise ChinaAshareCorporateActionPackageConflictError(
            "captured corporate-action sources must be unique and ordered"
        )
    captured_actions = tuple(
        sorted(
            (item for captured in captured_sources for item in captured.observations),
            key=lambda item: (str(item.instrument_id), item.ex_date),
        )
    )
    if actions != captured_actions:
        raise ChinaAshareCorporateActionPackageConflictError(
            "normalized actions differ from captured sources"
        )
    if not captured_sources or any(not item.raw_bytes for item in captured_sources):
        raise ChinaAshareCorporateActionPackageConflictError(
            "raw corporate-action payloads must be retained"
        )
    if len(actions) != report.corporate_action_count:
        raise ChinaAshareCorporateActionPackageConflictError(
            "corporate-action report count differs"
        )
    if not adjustments or not crosschecks:
        raise ChinaAshareCorporateActionPackageConflictError(
            "adjustment and independent cross-check evidence are required"
        )


def _crosscheck_json(value: ChinaAshareDistributionCrosscheckV1) -> dict[str, str]:
    return {
        "source_security_id": value.source_security_id,
        "ex_date": value.ex_date.isoformat(),
        "record_date": value.record_date.isoformat(),
        "cash_dividend_per_share_cny": str(value.cash_dividend_per_share_cny),
        "bonus_share_ratio": str(value.bonus_share_ratio),
        "capitalization_ratio": str(value.capitalization_ratio),
        "source": value.source,
    }


def _crosscheck_from_json(value: Any) -> ChinaAshareDistributionCrosscheckV1:
    if not isinstance(value, dict):
        raise ValueError("corporate-action cross-check row is malformed")
    return ChinaAshareDistributionCrosscheckV1(
        source_security_id=str(value["source_security_id"]),
        ex_date=datetime.strptime(str(value["ex_date"]), "%Y-%m-%d").date(),
        record_date=datetime.strptime(str(value["record_date"]), "%Y-%m-%d").date(),
        cash_dividend_per_share_cny=_decimal(value["cash_dividend_per_share_cny"]),
        bonus_share_ratio=_decimal(value["bonus_share_ratio"]),
        capitalization_ratio=_decimal(value["capitalization_ratio"]),
        source=str(value["source"]),
    )


def _decimal(value: Any):
    from decimal import Decimal

    return Decimal(str(value))


def _rows(payload: bytes) -> list[Any]:
    document = json.loads(payload)
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != "1.0"
        or not isinstance(document.get("rows"), list)
    ):
        raise ValueError("normalized document shape differs")
    return document["rows"]


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validate_root(value: Path) -> Path:
    root = value.expanduser().resolve()
    if root == Path("/") or root.is_symlink():
        raise ChinaAshareCorporateActionPackageConflictError(
            "corporate-action custody root is unsafe"
        )
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def _validate_package(value: Path) -> Path:
    package = value.expanduser().resolve()
    if not package.is_dir() or package.is_symlink():
        raise ChinaAshareCorporateActionPackageCorruptionError(
            "corporate-action package path is invalid"
        )
    return package


def _read_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ChinaAshareCorporateActionPackageCorruptionError(
            "corporate-action package file is absent or unsafe"
        )
    size = path.stat().st_size
    if size <= 0 or size > MAXIMUM_FILE_BYTES:
        raise ChinaAshareCorporateActionPackageCorruptionError(
            "corporate-action package file size is invalid"
        )
    return path.read_bytes()


def _write_file(path: Path, payload: bytes) -> None:
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
