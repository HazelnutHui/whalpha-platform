"""Immutable physical evidence and coverage publication over historical data."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from pydantic import ValidationError

from tip_api.contracts.market_data.v1 import (
    HistoricalCoverageArtifactEvidenceV1,
    HistoricalCoverageManifestV1,
    HistoricalDatasetCoverageEvidenceV1,
    historical_coverage_manifest_fingerprint,
)
from tip_api.persistence.historical_research import (
    HistoricalResearchConflictError,
    HistoricalResearchCorruptionError,
    HistoricalResearchPersistenceError,
)


SCHEMA_VERSION_PARTITION = "1"
EVIDENCE_DIRECTORY = "historical-coverage-evidence"
COVERAGE_DIRECTORY = "historical-coverage"
EVIDENCE_FILE_NAME = "manifest.json"
COVERAGE_FILE_NAME = "coverage.json"
COMPLETION_FILE_NAME = "manifest.json"
COMPLETION_STATUS = "completed"
MAXIMUM_JSON_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class HistoricalDatasetEvidenceWriteResult:
    evidence: HistoricalDatasetCoverageEvidenceV1
    evidence_path: Path
    physical_sha256: str
    status: str


@dataclass(frozen=True, slots=True)
class HistoricalCoverageWriteResult:
    coverage: HistoricalCoverageManifestV1
    partition_path: Path
    coverage_path: Path
    completion_path: Path
    coverage_physical_sha256: str
    status: str


@dataclass(frozen=True, slots=True)
class ParquetHistoricalCoverageRepository:
    """Publish and formally reread historical coverage without copying facts."""

    root: Path

    def publish_dataset_evidence(
        self,
        evidence: HistoricalDatasetCoverageEvidenceV1,
    ) -> HistoricalDatasetEvidenceWriteResult:
        root = _prepare_publish_root(self.root)
        _validate_dataset_artifacts(root, evidence)
        evidence_path = _dataset_evidence_path(root, evidence)
        payload = _canonical_json_bytes(evidence.model_dump(mode="json"))
        physical_sha256 = _bytes_sha256(payload)

        if evidence_path.exists() or evidence_path.is_symlink():
            existing, existing_sha = _read_dataset_evidence_file(root, evidence_path)
            if existing.logical_fingerprint != evidence.logical_fingerprint:
                raise HistoricalResearchConflictError(
                    "immutable dataset coverage evidence differs"
                )
            return HistoricalDatasetEvidenceWriteResult(
                evidence=existing,
                evidence_path=evidence_path,
                physical_sha256=existing_sha,
                status="already_present",
            )

        _reject_symlink_ancestry(root, evidence_path.parent)
        _publish_single_file_directory(
            target=evidence_path.parent,
            file_name=EVIDENCE_FILE_NAME,
            payload=payload,
        )
        reread, reread_sha = _read_dataset_evidence_file(root, evidence_path)
        if reread.logical_fingerprint != evidence.logical_fingerprint:
            raise HistoricalResearchCorruptionError(
                "dataset coverage evidence changed after publication"
            )
        return HistoricalDatasetEvidenceWriteResult(
            evidence=reread,
            evidence_path=evidence_path,
            physical_sha256=reread_sha,
            status="published",
        )

    def read_dataset_evidence(
        self,
        evidence_path: Path,
    ) -> HistoricalDatasetEvidenceWriteResult:
        root = _require_read_root(self.root)
        candidate = evidence_path if evidence_path.is_absolute() else root / evidence_path
        evidence, physical_sha256 = _read_dataset_evidence_file(
            root,
            candidate,
        )
        return HistoricalDatasetEvidenceWriteResult(
            evidence=evidence,
            evidence_path=candidate.absolute(),
            physical_sha256=physical_sha256,
            status="reread",
        )

    def publish_coverage(
        self,
        coverage: HistoricalCoverageManifestV1,
    ) -> HistoricalCoverageWriteResult:
        root = _prepare_publish_root(self.root)
        _validate_coverage_fingerprint(coverage)
        _validate_coverage_dataset_references(root, coverage)
        partition_path = _coverage_partition_path(root, coverage.coverage_id)
        coverage_payload = _canonical_json_bytes(coverage.model_dump(mode="json"))
        coverage_sha = _bytes_sha256(coverage_payload)
        completion = {
            "manifest_version": "historical-coverage-publication/1.0",
            "coverage_id": coverage.coverage_id,
            "coverage_file": COVERAGE_FILE_NAME,
            "coverage_physical_sha256": coverage_sha,
            "logical_fingerprint": coverage.logical_fingerprint,
            "completion_status": COMPLETION_STATUS,
        }

        if partition_path.exists() or partition_path.is_symlink():
            existing = _read_coverage_partition(root, partition_path)
            if existing.coverage.logical_fingerprint != coverage.logical_fingerprint:
                raise HistoricalResearchConflictError(
                    "immutable historical coverage publication differs"
                )
            return replace(existing, status="already_present")

        parent = partition_path.parent
        _reject_symlink_ancestry(root, parent)
        parent.mkdir(parents=True, exist_ok=True)
        staging = parent / f".{partition_path.name}.staging.{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise HistoricalResearchConflictError("coverage staging path exists")
        try:
            staging.mkdir()
            _write_file(staging / COVERAGE_FILE_NAME, coverage_payload)
            _write_file(
                staging / COMPLETION_FILE_NAME,
                _canonical_json_bytes(completion),
            )
            _fsync_directory(staging)
            staging.replace(partition_path)
            _fsync_directory(parent)
            reread = _read_coverage_partition(root, partition_path)
        except HistoricalResearchPersistenceError:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise
        except Exception as exc:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise HistoricalResearchPersistenceError(
                "historical coverage publication failed"
            ) from exc
        return replace(reread, status="published")

    def read_coverage(self, coverage_id: str) -> HistoricalCoverageWriteResult:
        root = _require_read_root(self.root)
        partition_path = _coverage_partition_path(root, coverage_id)
        return _read_coverage_partition(root, partition_path)


def _read_coverage_partition(
    root: Path,
    partition_path: Path,
) -> HistoricalCoverageWriteResult:
    _require_exact_directory(root, partition_path)
    expected_names = {COVERAGE_FILE_NAME, COMPLETION_FILE_NAME}
    if {item.name for item in partition_path.iterdir()} != expected_names:
        raise HistoricalResearchCorruptionError(
            "historical coverage partition file set differs"
        )
    coverage_path = partition_path / COVERAGE_FILE_NAME
    completion_path = partition_path / COMPLETION_FILE_NAME
    _require_exact_file(root, coverage_path)
    _require_exact_file(root, completion_path)
    completion = _read_json(completion_path)
    required_completion = {
        "manifest_version": "historical-coverage-publication/1.0",
        "coverage_file": COVERAGE_FILE_NAME,
        "completion_status": COMPLETION_STATUS,
    }
    if set(completion) != {
        *required_completion,
        "coverage_id",
        "coverage_physical_sha256",
        "logical_fingerprint",
    } or any(completion.get(key) != value for key, value in required_completion.items()):
        raise HistoricalResearchCorruptionError(
            "historical coverage completion manifest differs"
        )
    coverage_bytes = _read_bounded_bytes(coverage_path)
    coverage_sha = _bytes_sha256(coverage_bytes)
    if completion.get("coverage_physical_sha256") != coverage_sha:
        raise HistoricalResearchCorruptionError("historical coverage file hash differs")
    try:
        coverage = HistoricalCoverageManifestV1.model_validate_json(coverage_bytes)
    except (ValidationError, ValueError, TypeError) as exc:
        raise HistoricalResearchCorruptionError(
            "historical coverage contract is invalid"
        ) from exc
    if (
        completion.get("coverage_id") != coverage.coverage_id
        or completion.get("logical_fingerprint") != coverage.logical_fingerprint
        or partition_path != _coverage_partition_path(root, coverage.coverage_id)
    ):
        raise HistoricalResearchCorruptionError(
            "historical coverage identity differs"
        )
    _validate_coverage_fingerprint(coverage)
    _validate_coverage_dataset_references(root, coverage)
    return HistoricalCoverageWriteResult(
        coverage=coverage,
        partition_path=partition_path,
        coverage_path=coverage_path,
        completion_path=completion_path,
        coverage_physical_sha256=coverage_sha,
        status="reread",
    )


def _validate_coverage_dataset_references(
    root: Path,
    coverage: HistoricalCoverageManifestV1,
) -> None:
    for reference in coverage.datasets:
        evidence_path = root / PurePosixPath(reference.dataset_path)
        evidence, physical_sha = _read_dataset_evidence_file(root, evidence_path)
        expected = {
            "family": reference.family,
            "record_count": reference.record_count,
            "first_session": reference.first_session,
            "last_session": reference.last_session,
            "logical_fingerprint": reference.logical_fingerprint,
            "completed": reference.completed,
            "quarantined_record_count": reference.quarantined_record_count,
            "physical_sha256": reference.physical_sha256,
        }
        actual = {
            "family": evidence.family,
            "record_count": evidence.record_count,
            "first_session": evidence.sessions[0],
            "last_session": evidence.sessions[-1],
            "logical_fingerprint": evidence.logical_fingerprint,
            "completed": evidence.completed,
            "quarantined_record_count": evidence.quarantined_record_count,
            "physical_sha256": physical_sha,
        }
        if actual != expected:
            raise HistoricalResearchCorruptionError(
                "historical coverage dataset reference differs from evidence"
            )


def _read_dataset_evidence_file(
    root: Path,
    evidence_path: Path,
) -> tuple[HistoricalDatasetCoverageEvidenceV1, str]:
    path = _require_exact_file(root, evidence_path)
    if {item.name for item in path.parent.iterdir()} != {EVIDENCE_FILE_NAME}:
        raise HistoricalResearchCorruptionError(
            "dataset coverage evidence file set differs"
        )
    try:
        evidence = HistoricalDatasetCoverageEvidenceV1.model_validate_json(
            _read_bounded_bytes(path)
        )
    except (ValidationError, ValueError, TypeError) as exc:
        raise HistoricalResearchCorruptionError(
            "dataset coverage evidence is invalid"
        ) from exc
    if path != _dataset_evidence_path(root, evidence):
        raise HistoricalResearchCorruptionError(
            "dataset coverage evidence path differs"
        )
    _validate_dataset_artifacts(root, evidence)
    return evidence, _file_sha256(path)


def _validate_dataset_artifacts(
    root: Path,
    evidence: HistoricalDatasetCoverageEvidenceV1,
) -> None:
    seen: set[str] = set()
    for artifact in evidence.artifacts:
        references = (artifact.completion_manifest, *artifact.payload_files)
        for reference in references:
            if reference.path in seen:
                raise HistoricalResearchCorruptionError(
                    "dataset evidence reuses one physical file"
                )
            seen.add(reference.path)
            path = _require_exact_file(root, root / PurePosixPath(reference.path))
            if _file_sha256(path) != reference.physical_sha256:
                raise HistoricalResearchCorruptionError(
                    "dataset evidence physical file hash differs"
                )
        _validate_source_completion_manifest(root, artifact)


def _validate_source_completion_manifest(
    root: Path,
    artifact: HistoricalCoverageArtifactEvidenceV1,
) -> None:
    manifest_path = root / PurePosixPath(artifact.completion_manifest.path)
    manifest = _read_json(manifest_path)
    if manifest.get("completion_status") != COMPLETION_STATUS:
        raise HistoricalResearchCorruptionError(
            "source completion manifest is not completed"
        )
    if manifest.get("record_count") != artifact.record_count:
        raise HistoricalResearchCorruptionError(
            "source completion record count differs"
        )
    logical_values = {
        value
        for key in ("logical_fingerprint", "content_sha256", "snapshot_content_sha256")
        if isinstance((value := manifest.get(key)), str)
    }
    if artifact.logical_fingerprint not in logical_values:
        raise HistoricalResearchCorruptionError(
            "source completion logical fingerprint differs"
        )
    named_payload = manifest.get("parquet_file")
    if isinstance(named_payload, str):
        expected_path = (
            PurePosixPath(artifact.completion_manifest.path).parent / named_payload
        ).as_posix()
        payload_by_path = {item.path: item for item in artifact.payload_files}
        if expected_path not in payload_by_path:
            raise HistoricalResearchCorruptionError(
                "source completion payload is not evidence-bound"
            )
        physical = manifest.get("physical_sha256")
        if (
            isinstance(physical, str)
            and physical != payload_by_path[expected_path].physical_sha256
        ):
            raise HistoricalResearchCorruptionError(
                "source completion payload hash differs"
            )


def _validate_coverage_fingerprint(coverage: HistoricalCoverageManifestV1) -> None:
    if historical_coverage_manifest_fingerprint(coverage) != coverage.logical_fingerprint:
        raise HistoricalResearchCorruptionError(
            "historical coverage logical fingerprint differs"
        )


def _dataset_evidence_path(
    root: Path,
    evidence: HistoricalDatasetCoverageEvidenceV1,
) -> Path:
    return (
        root
        / "market-data"
        / EVIDENCE_DIRECTORY
        / f"schema_version={SCHEMA_VERSION_PARTITION}"
        / f"family={evidence.family.value}"
        / f"evidence_id={evidence.logical_fingerprint}"
        / EVIDENCE_FILE_NAME
    ).absolute()


def _coverage_partition_path(root: Path, coverage_id: str) -> Path:
    if len(coverage_id) != 64 or any(
        character not in "0123456789abcdef" for character in coverage_id
    ):
        raise HistoricalResearchPersistenceError("coverage_id is malformed")
    return (
        root
        / "market-data"
        / COVERAGE_DIRECTORY
        / f"schema_version={SCHEMA_VERSION_PARTITION}"
        / f"coverage_id={coverage_id}"
    ).absolute()


def _publish_single_file_directory(
    *, target: Path, file_name: str, payload: bytes
) -> None:
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = parent / f".{target.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise HistoricalResearchConflictError("evidence staging path exists")
    try:
        staging.mkdir()
        _write_file(staging / file_name, payload)
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(parent)
    except Exception as exc:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise HistoricalResearchPersistenceError(
            "dataset coverage evidence publication failed"
        ) from exc


def _prepare_publish_root(root: Path) -> Path:
    if root.exists() and (not root.is_dir() or root.is_symlink()):
        raise HistoricalResearchPersistenceError(
            "repository root must be a non-symlink directory"
        )
    root.mkdir(parents=True, exist_ok=True)
    return root.absolute()


def _require_read_root(root: Path) -> Path:
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise HistoricalResearchCorruptionError(
            "repository root is missing or unsafe"
        )
    return root.absolute()


def _require_exact_directory(root: Path, path: Path) -> Path:
    absolute = path.absolute()
    _reject_symlink_ancestry(root, absolute)
    if not absolute.is_dir() or absolute.is_symlink():
        raise HistoricalResearchCorruptionError("publication directory is unsafe")
    return absolute


def _require_exact_file(root: Path, path: Path) -> Path:
    absolute = path.absolute()
    _reject_symlink_ancestry(root, absolute)
    if not absolute.is_file() or absolute.is_symlink():
        raise HistoricalResearchCorruptionError("evidence file is missing or unsafe")
    return absolute


def _reject_symlink_ancestry(root: Path, path: Path) -> None:
    absolute_root = root.absolute()
    absolute_path = path.absolute()
    if absolute_path == absolute_root or absolute_root not in absolute_path.parents:
        raise HistoricalResearchCorruptionError("evidence path escaped repository root")
    current = absolute_path
    while current != absolute_root:
        if current.exists() and current.is_symlink():
            raise HistoricalResearchCorruptionError("evidence path contains a symlink")
        current = current.parent


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_read_bounded_bytes(path))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HistoricalResearchCorruptionError("JSON evidence cannot be read") from exc
    if not isinstance(value, dict):
        raise HistoricalResearchCorruptionError("JSON evidence must be an object")
    return value


def _read_bounded_bytes(path: Path) -> bytes:
    size = path.stat().st_size
    if size <= 0 or size > MAXIMUM_JSON_BYTES:
        raise HistoricalResearchCorruptionError("evidence file size is invalid")
    return path.read_bytes()


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _write_file(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
