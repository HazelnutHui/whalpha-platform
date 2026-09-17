"""Immutable persistent custody for the five-year A-share source population."""

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

from tip_api.contracts.china_ashare.v1.population import (
    ChinaAshareBaoStockBasicRecordV1,
    ChinaAshareFiveYearPopulationPackageManifestV1,
    ChinaAshareFiveYearPopulationReportV1,
    ChinaAshareOfficialPopulationSourceKind,
    ChinaAsharePopulationOccurrenceV1,
    ChinaAsharePopulationRawArtifactV1,
    baostock_basic_set_fingerprint,
    build_five_year_population_package_manifest,
    population_occurrence_set_fingerprint,
)
from tip_api.persistence.china_ashare_identity_lifecycle_package import (
    ChinaAshareIdentityLifecyclePackageResultV1,
)


BASIC_FILE = "normalized/baostock-security-basic.json"
OCCURRENCES_FILE = "normalized/population-occurrences.json"
REPORT_FILE = "five-year-population-report.json"
MANIFEST_FILE = "five-year-population-manifest.json"
MAXIMUM_FILE_BYTES = 64 * 1024 * 1024


class ChinaAsharePopulationPackageError(RuntimeError):
    pass


class ChinaAsharePopulationPackageConflictError(ChinaAsharePopulationPackageError):
    pass


class ChinaAsharePopulationPackageCorruptionError(ChinaAsharePopulationPackageError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAsharePopulationPackageResultV1:
    manifest: ChinaAshareFiveYearPopulationPackageManifestV1
    baostock_basic_records: tuple[ChinaAshareBaoStockBasicRecordV1, ...]
    occurrences: tuple[ChinaAsharePopulationOccurrenceV1, ...]
    report: ChinaAshareFiveYearPopulationReportV1
    package_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_population_package(
    *,
    custody_root: Path,
    identity_lifecycle_package: ChinaAshareIdentityLifecyclePackageResultV1,
    baostock_basic_records: tuple[ChinaAshareBaoStockBasicRecordV1, ...],
    occurrences: tuple[ChinaAsharePopulationOccurrenceV1, ...],
    report: ChinaAshareFiveYearPopulationReportV1,
    created_at: datetime,
) -> ChinaAsharePopulationPackageResultV1:
    root = _root(custody_root)
    if report.official_identity_package_fingerprint != (
        identity_lifecycle_package.manifest.logical_fingerprint
    ):
        raise ChinaAsharePopulationPackageConflictError(
            "population report differs from official identity package"
        )
    basic_fp = baostock_basic_set_fingerprint(baostock_basic_records)
    occurrence_fp = population_occurrence_set_fingerprint(occurrences)
    if basic_fp != report.baostock_basic_set_fingerprint:
        raise ChinaAsharePopulationPackageConflictError(
            "population BaoStock basic set differs from report"
        )
    if occurrence_fp != report.occurrence_set_fingerprint:
        raise ChinaAsharePopulationPackageConflictError(
            "population occurrence set differs from report"
        )
    basic_bytes = _canonical_json_bytes(
        {
            "schema_version": "1.0",
            "rows": [item.model_dump(mode="json") for item in baostock_basic_records],
        }
    )
    occurrence_bytes = _canonical_json_bytes(
        {
            "schema_version": "1.0",
            "rows": [item.model_dump(mode="json") for item in occurrences],
        }
    )
    report_bytes = _canonical_json_bytes(report.model_dump(mode="json"))
    source_by_kind = {
        item.artifact_kind: item
        for item in identity_lifecycle_package.manifest.raw_artifacts
    }
    raw_artifacts = tuple(
        ChinaAsharePopulationRawArtifactV1(
            artifact_kind=ChinaAshareOfficialPopulationSourceKind(kind),
            relative_path=(
                f"raw/official/{kind}."
                f"{'json' if 'json' in item.content_type.lower() else 'xlsx'}"
            ),
            byte_size=item.byte_size,
            physical_sha256=item.physical_sha256,
        )
        for kind, item in sorted(source_by_kind.items())
    )
    manifest = build_five_year_population_package_manifest(
        created_at=created_at,
        official_identity_package_fingerprint=(
            identity_lifecycle_package.manifest.logical_fingerprint
        ),
        baostock_basic_document_sha256=_sha(basic_bytes),
        baostock_basic_set_fingerprint=basic_fp,
        occurrence_document_sha256=_sha(occurrence_bytes),
        occurrence_set_fingerprint=occurrence_fp,
        report_document_sha256=_sha(report_bytes),
        report_fingerprint=report.logical_fingerprint,
        official_raw_artifacts=raw_artifacts,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    target = root / f"population-package={manifest.logical_fingerprint}"
    if target.exists():
        existing = read_china_ashare_population_package(package_path=target)
        if existing.manifest != manifest:
            raise ChinaAsharePopulationPackageConflictError(
                "existing population package differs"
            )
        return existing
    staging = Path(tempfile.mkdtemp(prefix=".population-", dir=root))
    try:
        (staging / "normalized").mkdir(mode=0o700)
        (staging / "raw/official").mkdir(mode=0o700, parents=True)
        _write(staging / BASIC_FILE, basic_bytes)
        _write(staging / OCCURRENCES_FILE, occurrence_bytes)
        _write(staging / REPORT_FILE, report_bytes)
        for artifact in raw_artifacts:
            source = source_by_kind[artifact.artifact_kind.value]
            source_path = identity_lifecycle_package.package_path / PurePosixPath(
                source.relative_path
            )
            payload = _read(source_path)
            if len(payload) != artifact.byte_size or _sha(payload) != artifact.physical_sha256:
                raise ChinaAsharePopulationPackageConflictError(
                    "official population source bytes differ"
                )
            _write(staging / PurePosixPath(artifact.relative_path), payload)
        _write(staging / MANIFEST_FILE, manifest_bytes)
        _owner_only(staging)
        _fsync_tree(staging)
        staging.rename(target)
        _fsync_directory(root)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_china_ashare_population_package(package_path=target),
        status="published",
    )


def read_china_ashare_population_package(
    *, package_path: Path
) -> ChinaAsharePopulationPackageResultV1:
    package = package_path.expanduser().resolve()
    if not package.is_dir() or package.is_symlink():
        raise ChinaAsharePopulationPackageCorruptionError(
            "population package path is invalid"
        )
    manifest_payload = _read(package / MANIFEST_FILE)
    try:
        manifest = ChinaAshareFiveYearPopulationPackageManifestV1.model_validate_json(
            manifest_payload
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAsharePopulationPackageCorruptionError(
            "population manifest is invalid"
        ) from exc
    if package.name != f"population-package={manifest.logical_fingerprint}":
        raise ChinaAsharePopulationPackageCorruptionError(
            "population package path identity differs"
        )
    basic_payload = _read(package / BASIC_FILE)
    occurrence_payload = _read(package / OCCURRENCES_FILE)
    report_payload = _read(package / REPORT_FILE)
    for payload, expected, label in (
        (basic_payload, manifest.baostock_basic_document_sha256, "basic"),
        (occurrence_payload, manifest.occurrence_document_sha256, "occurrence"),
        (report_payload, manifest.report_document_sha256, "report"),
    ):
        if _sha(payload) != expected:
            raise ChinaAsharePopulationPackageCorruptionError(
                f"population {label} bytes changed"
            )
    try:
        basic = tuple(
            ChinaAshareBaoStockBasicRecordV1.model_validate(item)
            for item in _rows(basic_payload)
        )
        occurrences = tuple(
            ChinaAsharePopulationOccurrenceV1.model_validate(item)
            for item in _rows(occurrence_payload)
        )
        report = ChinaAshareFiveYearPopulationReportV1.model_validate_json(
            report_payload
        )
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ChinaAsharePopulationPackageCorruptionError(
            "population normalized document is invalid"
        ) from exc
    if baostock_basic_set_fingerprint(basic) != manifest.baostock_basic_set_fingerprint:
        raise ChinaAsharePopulationPackageCorruptionError(
            "population basic set fingerprint differs"
        )
    if population_occurrence_set_fingerprint(occurrences) != (
        manifest.occurrence_set_fingerprint
    ):
        raise ChinaAsharePopulationPackageCorruptionError(
            "population occurrence set fingerprint differs"
        )
    if report.logical_fingerprint != manifest.report_fingerprint:
        raise ChinaAsharePopulationPackageCorruptionError(
            "population report fingerprint differs"
        )
    if report.occurrence_set_fingerprint != manifest.occurrence_set_fingerprint:
        raise ChinaAsharePopulationPackageCorruptionError(
            "population report occurrence set differs"
        )
    raw_paths = []
    for artifact in manifest.official_raw_artifacts:
        payload = _read(package / PurePosixPath(artifact.relative_path))
        if len(payload) != artifact.byte_size or _sha(payload) != artifact.physical_sha256:
            raise ChinaAsharePopulationPackageCorruptionError(
                "population official raw bytes changed"
            )
        raw_paths.append(artifact.relative_path)
    expected_files = {
        BASIC_FILE,
        OCCURRENCES_FILE,
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
        raise ChinaAsharePopulationPackageCorruptionError(
            "population package file set differs"
        )
    files = tuple(item for item in package.rglob("*") if item.is_file())
    return ChinaAsharePopulationPackageResultV1(
        manifest=manifest,
        baostock_basic_records=basic,
        occurrences=occurrences,
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
        raise ValueError("population document shape differs")
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
        raise ChinaAsharePopulationPackageConflictError(
            "population custody root is unsafe"
        )
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink():
        raise ChinaAsharePopulationPackageConflictError(
            "population custody root cannot be a symlink"
        )
    return root


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ChinaAsharePopulationPackageCorruptionError(
            "population package file is absent or unsafe"
        )
    size = path.stat().st_size
    if size <= 0 or size > MAXIMUM_FILE_BYTES:
        raise ChinaAsharePopulationPackageCorruptionError(
            "population package file size is invalid"
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
