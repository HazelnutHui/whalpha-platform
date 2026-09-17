"""Owner-only immutable custody for official A-share calendar evidence."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.calendar_evidence import (
    ChinaAshareOfficialCalendarEvidenceManifestV1,
    ChinaAshareOfficialCalendarEvidencePlanV1,
    ChinaAshareOfficialCalendarEvidenceReportV1,
    ChinaAshareOfficialCalendarNoticeV1,
    ChinaAshareOfficialCalendarRawArtifactV1,
    build_official_calendar_evidence_manifest,
)
from tip_api.providers.china_ashare.official_calendar_adapter import (
    CapturedOfficialCalendarNoticeV1,
)


PLAN_FILE = "calendar-evidence-plan.json"
NOTICES_FILE = "normalized/official-calendar-notices.json"
REPORT_FILE = "calendar-evidence-report.json"
MANIFEST_FILE = "calendar-evidence-manifest.json"
MAXIMUM_JSON_BYTES = 8 * 1024 * 1024


class ChinaAshareCalendarEvidencePackageError(RuntimeError):
    """Base failure for official-calendar evidence custody."""


class ChinaAshareCalendarEvidencePackageConflictError(
    ChinaAshareCalendarEvidencePackageError
):
    """Raised when immutable package scope or content conflicts."""


class ChinaAshareCalendarEvidencePackageCorruptionError(
    ChinaAshareCalendarEvidencePackageError
):
    """Raised when exact reread detects changed or malformed custody."""


@dataclass(frozen=True, slots=True)
class ChinaAshareCalendarEvidencePackageResultV1:
    manifest: ChinaAshareOfficialCalendarEvidenceManifestV1
    plan: ChinaAshareOfficialCalendarEvidencePlanV1
    notices: tuple[ChinaAshareOfficialCalendarNoticeV1, ...]
    report: ChinaAshareOfficialCalendarEvidenceReportV1
    package_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_calendar_evidence_package(
    *,
    custody_root: Path,
    plan: ChinaAshareOfficialCalendarEvidencePlanV1,
    captured_notices: tuple[CapturedOfficialCalendarNoticeV1, ...],
    report: ChinaAshareOfficialCalendarEvidenceReportV1,
    created_at: datetime,
) -> ChinaAshareCalendarEvidencePackageResultV1:
    """Persist exact public notice bytes and typed reconciliation evidence."""

    root = _validate_custody_root(custody_root)
    ordered = tuple(
        sorted(
            captured_notices,
            key=lambda item: (
                item.observation.notice_year,
                item.observation.exchange.value,
            ),
        )
    )
    _validate_inputs(plan=plan, captured_notices=ordered, report=report)
    plan_bytes = _canonical_json_bytes(plan.model_dump(mode="json"))
    notices_bytes = _canonical_json_bytes(
        {
            "schema_version": "1.0",
            "rows": [item.observation.model_dump(mode="json") for item in ordered],
        }
    )
    report_bytes = _canonical_json_bytes(report.model_dump(mode="json"))
    artifacts = tuple(
        ChinaAshareOfficialCalendarRawArtifactV1(
            exchange=item.observation.exchange,
            notice_year=item.observation.notice_year,
            relative_path=(
                f"raw/{item.observation.exchange.value.lower()}-"
                f"{item.observation.notice_year}.html"
            ),
            byte_size=len(item.raw_bytes),
            physical_sha256=_sha256(item.raw_bytes),
        )
        for item in ordered
    )
    manifest = build_official_calendar_evidence_manifest(
        plan_fingerprint=plan.logical_fingerprint,
        created_at=created_at,
        plan_document_sha256=_sha256(plan_bytes),
        notices_document_sha256=_sha256(notices_bytes),
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
    plan_directory = root / f"calendar-plan={plan.logical_fingerprint}"
    target = plan_directory / f"calendar-package={manifest.logical_fingerprint}"
    if target.exists():
        existing = read_china_ashare_calendar_evidence_package(package_path=target)
        if existing.manifest != manifest:
            raise ChinaAshareCalendarEvidencePackageConflictError(
                "existing calendar evidence package differs"
            )
        return existing
    plan_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if plan_directory.is_symlink():
        raise ChinaAshareCalendarEvidencePackageConflictError(
            "calendar evidence plan directory cannot be a symlink"
        )
    temporary = Path(
        tempfile.mkdtemp(prefix=".calendar-package-", dir=plan_directory)
    )
    try:
        (temporary / "normalized").mkdir(mode=0o700)
        (temporary / "raw").mkdir(mode=0o700)
        _write_file(temporary / PLAN_FILE, plan_bytes)
        _write_file(temporary / NOTICES_FILE, notices_bytes)
        _write_file(temporary / REPORT_FILE, report_bytes)
        for artifact, captured in zip(artifacts, ordered, strict=True):
            _write_file(temporary / artifact.relative_path, captured.raw_bytes)
        _write_file(temporary / MANIFEST_FILE, manifest_bytes)
        _make_directories_owner_only(temporary)
        _fsync_tree(temporary)
        temporary.rename(target)
        _fsync_directory(plan_directory)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return read_china_ashare_calendar_evidence_package(package_path=target)


def read_china_ashare_calendar_evidence_package(
    *,
    package_path: Path,
) -> ChinaAshareCalendarEvidencePackageResultV1:
    package = _validate_package_path(package_path)
    manifest_payload = _read_regular_file(package / MANIFEST_FILE)
    try:
        manifest = ChinaAshareOfficialCalendarEvidenceManifestV1.model_validate_json(
            manifest_payload
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence manifest is invalid"
        ) from exc
    plan_payload = _read_regular_file(package / PLAN_FILE)
    notices_payload = _read_regular_file(package / NOTICES_FILE)
    report_payload = _read_regular_file(package / REPORT_FILE)
    if _sha256(plan_payload) != manifest.plan_document_sha256:
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence plan hash differs"
        )
    if _sha256(notices_payload) != manifest.notices_document_sha256:
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence notices hash differs"
        )
    if _sha256(report_payload) != manifest.report_document_sha256:
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence report hash differs"
        )
    try:
        plan = ChinaAshareOfficialCalendarEvidencePlanV1.model_validate_json(plan_payload)
        report = ChinaAshareOfficialCalendarEvidenceReportV1.model_validate_json(
            report_payload
        )
        notices_document = json.loads(notices_payload)
        if (
            not isinstance(notices_document, dict)
            or notices_document.get("schema_version") != "1.0"
            or not isinstance(notices_document.get("rows"), list)
        ):
            raise ValueError("calendar notices document shape differs")
        notices = tuple(
            ChinaAshareOfficialCalendarNoticeV1.model_validate(item)
            for item in notices_document["rows"]
        )
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence document is invalid"
        ) from exc
    if plan.logical_fingerprint != manifest.plan_fingerprint:
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence plan fingerprint differs"
        )
    if report.logical_fingerprint != manifest.report_fingerprint:
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence report fingerprint differs"
        )
    notice_keys = tuple((item.notice_year, item.exchange.value) for item in notices)
    if notice_keys != tuple(sorted(set(notice_keys))):
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence notices are not unique and ordered"
        )
    raw_paths: list[Path] = []
    for artifact, notice in zip(manifest.raw_artifacts, notices, strict=True):
        if (artifact.notice_year, artifact.exchange) != (
            notice.notice_year,
            notice.exchange,
        ):
            raise ChinaAshareCalendarEvidencePackageCorruptionError(
                "calendar raw artifact order differs from notices"
            )
        payload = _read_regular_file(package / artifact.relative_path)
        if len(payload) != artifact.byte_size or _sha256(payload) != artifact.physical_sha256:
            raise ChinaAshareCalendarEvidencePackageCorruptionError(
                "calendar raw artifact bytes differ"
            )
        if artifact.physical_sha256 != notice.raw_sha256:
            raise ChinaAshareCalendarEvidencePackageCorruptionError(
                "calendar raw artifact hash differs from notice observation"
            )
        raw_paths.append(Path(artifact.relative_path))
    expected_files = {
        Path(PLAN_FILE),
        Path(NOTICES_FILE),
        Path(REPORT_FILE),
        Path(MANIFEST_FILE),
        *raw_paths,
    }
    actual_files = {
        item.relative_to(package)
        for item in package.rglob("*")
        if item.is_file() and not item.is_symlink()
    }
    if actual_files != expected_files:
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence package file set differs"
        )
    for item in package.rglob("*"):
        if item.is_symlink():
            raise ChinaAshareCalendarEvidencePackageCorruptionError(
                "calendar evidence package contains a symlink"
            )
        if item.is_file() and item.stat().st_mode & 0o777 != 0o400:
            raise ChinaAshareCalendarEvidencePackageCorruptionError(
                "calendar evidence file mode differs"
            )
        if item.is_dir() and item.stat().st_mode & 0o777 != 0o700:
            raise ChinaAshareCalendarEvidencePackageCorruptionError(
                "calendar evidence directory mode differs"
            )
    if package.stat().st_mode & 0o777 != 0o700:
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence package mode differs"
        )
    file_count = len(expected_files)
    total_bytes = sum((package / item).stat().st_size for item in expected_files)
    return ChinaAshareCalendarEvidencePackageResultV1(
        manifest=manifest,
        plan=plan,
        notices=notices,
        report=report,
        package_path=package,
        manifest_path=package / MANIFEST_FILE,
        manifest_physical_sha256=_sha256(manifest_payload),
        file_count=file_count,
        total_bytes=total_bytes,
        status="exact_reread_complete",
    )


def _validate_inputs(
    *,
    plan: ChinaAshareOfficialCalendarEvidencePlanV1,
    captured_notices: tuple[CapturedOfficialCalendarNoticeV1, ...],
    report: ChinaAshareOfficialCalendarEvidenceReportV1,
) -> None:
    expected_keys = tuple(
        (item.notice_year, item.exchange.value) for item in plan.notice_specs
    )
    observed_keys = tuple(
        (item.observation.notice_year, item.observation.exchange.value)
        for item in captured_notices
    )
    if observed_keys != expected_keys:
        raise ChinaAshareCalendarEvidencePackageConflictError(
            "captured calendar notices differ from the plan"
        )
    for spec, captured in zip(plan.notice_specs, captured_notices, strict=True):
        if spec.source_url != captured.observation.source_url:
            raise ChinaAshareCalendarEvidencePackageConflictError(
                "captured calendar notice URL differs from the plan"
            )
        if _sha256(captured.raw_bytes) != captured.observation.raw_sha256:
            raise ChinaAshareCalendarEvidencePackageConflictError(
                "captured calendar raw bytes differ from their observation"
            )
    if report.plan_fingerprint != plan.logical_fingerprint:
        raise ChinaAshareCalendarEvidencePackageConflictError(
            "calendar evidence report differs from the plan"
        )
    if report.notice_count != len(captured_notices):
        raise ChinaAshareCalendarEvidencePackageConflictError(
            "calendar evidence report notice count differs"
        )


def _validate_custody_root(path: Path) -> Path:
    root = path.absolute()
    if root.name != "china-a-share-research-pilot" or Path("/tmp") not in root.parents:
        raise ChinaAshareCalendarEvidencePackageConflictError(
            "calendar evidence custody must use the dedicated pilot path below /tmp"
        )
    if root.exists() and (root.is_symlink() or not root.is_dir()):
        raise ChinaAshareCalendarEvidencePackageConflictError(
            "calendar evidence custody root is invalid"
        )
    if not root.parent.is_dir() or root.parent.is_symlink():
        raise ChinaAshareCalendarEvidencePackageConflictError(
            "calendar evidence custody parent is invalid"
        )
    return root


def _validate_package_path(path: Path) -> Path:
    package = path.absolute()
    if (
        Path("/tmp") not in package.parents
        or not package.name.startswith("calendar-package=")
        or not package.parent.name.startswith("calendar-plan=")
        or package.parent.parent.name != "china-a-share-research-pilot"
        or not package.is_dir()
        or package.is_symlink()
    ):
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence package path is invalid"
        )
    return package


def _read_regular_file(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence file is invalid"
        )
    size = path.stat().st_size
    if size < 1 or size > MAXIMUM_JSON_BYTES:
        raise ChinaAshareCalendarEvidencePackageCorruptionError(
            "calendar evidence file size is invalid"
        )
    return path.read_bytes()


def _canonical_json_bytes(value: Any) -> bytes:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")
    if len(payload) > MAXIMUM_JSON_BYTES:
        raise ChinaAshareCalendarEvidencePackageConflictError(
            "calendar evidence JSON exceeds its byte ceiling"
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
