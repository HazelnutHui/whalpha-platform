"""Atomic Parquet persistence for provider security-type evidence."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.security_classification.v1 import (
    FailedSecurityEvidenceDiagnosticV1,
    ProviderInstrumentSecurityEvidenceV1,
    ProviderSecurityObservationV1,
    ProviderSecurityEvidenceSnapshotManifestV1,
    ProviderSecurityTypeCatalogV1,
)
from tip_api.persistence.parquet.instrument_master_snapshot import records_fingerprint
from tip_api.persistence.security_evidence import (
    CompletedSecurityEvidenceSnapshot,
    SecurityEvidenceConflictError,
    SecurityEvidenceCorruptionError,
    SecurityEvidencePersistenceError,
    SecurityEvidenceSnapshotWriteResult,
    SecurityEvidenceWriteResult,
    FailedDiagnosticWriteResult,
)

SCHEMA_VERSION = "1.0"
SCHEMA_PARTITION = "1"
PARQUET_FILE = "part-00000.parquet"
MANIFEST_FILE = "manifest.json"
COMPLETION_STATUS = "completed"
CATALOG_DATASET = "provider-security-type-catalog"
EVIDENCE_DATASET = "provider-instrument-security-evidence"
OBSERVATION_DATASET = "provider-security-observation"
DIAGNOSTIC_DIRECTORY = "operation-diagnostics/provider-security-type-evidence"
SNAPSHOT_DATASET = "provider-security-evidence"
SNAPSHOT_DIRECTORY = "market-data/snapshots/provider-security-evidence"

CATALOG_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("provider", pa.string(), nullable=False),
        pa.field("provider_type_code", pa.string(), nullable=False),
        pa.field("provider_type_description", pa.string(), nullable=False),
        pa.field("provider_asset_class", pa.string(), nullable=False),
        pa.field("provider_locale", pa.string(), nullable=False),
        pa.field("observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("source_endpoint", pa.string(), nullable=False),
        pa.field("evidence_fingerprint", pa.string(), nullable=False),
    ]
)

INSTRUMENT_EVIDENCE_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("evidence_kind", pa.string(), nullable=False),
        pa.field("evidence_version", pa.string(), nullable=False),
        pa.field("as_of_date", pa.date32(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("provider", pa.string(), nullable=False),
        pa.field("provider_ticker", pa.string(), nullable=False),
        pa.field("provider_type_code", pa.string(), nullable=False),
        pa.field("provider_type_description", pa.string(), nullable=False),
        pa.field("primary_exchange", pa.string(), nullable=False),
        pa.field("provider_instrument_id", pa.string(), nullable=True),
        pa.field("cik", pa.string(), nullable=True),
        pa.field("composite_figi", pa.string(), nullable=True),
        pa.field("share_class_figi", pa.string(), nullable=True),
        pa.field("security_form_evidence", pa.string(), nullable=False),
        pa.field("evidence_source", pa.string(), nullable=False),
        pa.field("evidence_grade", pa.string(), nullable=False),
        pa.field("classification_status", pa.string(), nullable=False),
        pa.field("universe_disposition", pa.string(), nullable=False),
        pa.field("decision_flags", pa.list_(pa.string()), nullable=False),
        pa.field("review_flags", pa.list_(pa.string()), nullable=False),
        pa.field("provider_observation_ids", pa.list_(pa.string()), nullable=False),
        pa.field("observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
    ]
)

OBSERVATION_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("provider_observation_id", pa.string(), nullable=False),
        pa.field("as_of_date", pa.date32(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=True),
        pa.field("provider", pa.string(), nullable=False),
        pa.field("provider_ticker", pa.string(), nullable=True),
        pa.field("provider_type_code", pa.string(), nullable=True),
        pa.field("provider_type_description", pa.string(), nullable=True),
        pa.field("primary_exchange", pa.string(), nullable=True),
        pa.field("provider_instrument_id", pa.string(), nullable=True),
        pa.field("cik", pa.string(), nullable=True),
        pa.field("composite_figi", pa.string(), nullable=True),
        pa.field("share_class_figi", pa.string(), nullable=True),
        pa.field("security_form_evidence", pa.string(), nullable=False),
        pa.field("evidence_source", pa.string(), nullable=False),
        pa.field("evidence_grade", pa.string(), nullable=False),
        pa.field("observation_status", pa.string(), nullable=False),
        pa.field("resolution_method", pa.string(), nullable=False),
        pa.field("reason_codes", pa.list_(pa.string()), nullable=False),
        pa.field("review_flags", pa.list_(pa.string()), nullable=False),
        pa.field("occurrence_count", pa.int64(), nullable=False),
        pa.field("observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
    ]
)


@dataclass(frozen=True, slots=True)
class ParquetSecurityEvidenceRepository:
    root: Path
    created_at: datetime | None = None

    def publish_catalog(
        self,
        records: tuple[ProviderSecurityTypeCatalogV1, ...],
        *,
        observed_date: date,
        provider_id: str,
    ) -> SecurityEvidenceWriteResult:
        if not records:
            raise SecurityEvidencePersistenceError("catalog cannot be empty")
        ordered = tuple(sorted(records, key=lambda item: item.provider_type_code))
        if len({item.provider_type_code for item in ordered}) != len(ordered):
            raise SecurityEvidencePersistenceError("catalog provider type code is not unique")
        if any(item.provider != provider_id or item.observed_at.date() != observed_date for item in ordered):
            raise SecurityEvidencePersistenceError("catalog partition fields do not match")
        rows = [_catalog_row(item) for item in ordered]
        partition = self._root() / "market-data" / CATALOG_DATASET / f"schema_version={SCHEMA_PARTITION}" / f"provider={provider_id}" / f"observed_date={observed_date.isoformat()}"
        return self._publish(
            dataset=CATALOG_DATASET,
            partition=partition,
            schema=CATALOG_SCHEMA,
            rows=rows,
            manifest_extra={"provider_id": provider_id, "observed_date": observed_date.isoformat(), "source_endpoint": "/v3/reference/tickers/types"},
        )

    def publish_instrument_evidence(
        self,
        records: tuple[ProviderInstrumentSecurityEvidenceV1, ...],
        *,
        as_of_date: date,
        provider_id: str,
        catalog_content_sha256: str,
        quality_summary: dict[str, object],
    ) -> SecurityEvidenceWriteResult:
        if not records:
            raise SecurityEvidencePersistenceError("instrument evidence cannot be empty")
        ordered = tuple(sorted(records, key=lambda item: (str(item.instrument_id), item.provider_ticker)))
        if len({item.instrument_id for item in ordered}) != len(ordered):
            raise SecurityEvidencePersistenceError("instrument evidence business key is not unique")
        if any(item.provider != provider_id or item.as_of_date != as_of_date for item in ordered):
            raise SecurityEvidencePersistenceError("instrument evidence partition fields do not match")
        rows = [_evidence_row(item) for item in ordered]
        partition = self._root() / "market-data" / EVIDENCE_DATASET / f"schema_version={SCHEMA_PARTITION}" / f"provider={provider_id}" / f"as_of_date={as_of_date.isoformat()}"
        return self._publish(
            dataset=EVIDENCE_DATASET,
            partition=partition,
            schema=INSTRUMENT_EVIDENCE_SCHEMA,
            rows=rows,
            manifest_extra={
                "provider_id": provider_id,
                "as_of_date": as_of_date.isoformat(),
                "source_endpoint": "/v3/reference/tickers",
                "catalog_content_sha256": catalog_content_sha256,
                "quality_summary": quality_summary,
            },
        )

    def publish_observations(
        self,
        records: tuple[ProviderSecurityObservationV1, ...],
        *,
        as_of_date: date,
        provider_id: str,
        catalog_content_sha256: str,
        quality_summary: dict[str, object],
    ) -> SecurityEvidenceWriteResult:
        if not records:
            raise SecurityEvidencePersistenceError("provider observations cannot be empty")
        ordered = tuple(sorted(records, key=lambda item: item.provider_observation_id))
        if len({item.provider_observation_id for item in ordered}) != len(ordered):
            raise SecurityEvidencePersistenceError("provider observation business key is not unique")
        if any(item.provider != provider_id or item.as_of_date != as_of_date for item in ordered):
            raise SecurityEvidencePersistenceError("provider observation partition fields do not match")
        rows = [_observation_row(item) for item in ordered]
        partition = self._root() / "market-data" / OBSERVATION_DATASET / f"schema_version={SCHEMA_PARTITION}" / f"provider={provider_id}" / f"as_of_date={as_of_date.isoformat()}"
        return self._publish(
            dataset=OBSERVATION_DATASET,
            partition=partition,
            schema=OBSERVATION_SCHEMA,
            rows=rows,
            manifest_extra={
                "provider_id": provider_id,
                "as_of_date": as_of_date.isoformat(),
                "source_endpoint": "/v3/reference/tickers",
                "catalog_content_sha256": catalog_content_sha256,
                "quality_summary": quality_summary,
            },
        )

    def publish_logical_snapshot(
        self,
        *,
        as_of_date: date,
        observed_date: date,
        provider_id: str,
        created_at: datetime,
        request_count: int,
        catalog: SecurityEvidenceWriteResult,
        observations: SecurityEvidenceWriteResult,
        evidence: SecurityEvidenceWriteResult,
    ) -> SecurityEvidenceSnapshotWriteResult:
        root = self._root()
        _verify_write_result(root, catalog, CATALOG_DATASET, CATALOG_SCHEMA)
        _verify_write_result(root, observations, OBSERVATION_DATASET, OBSERVATION_SCHEMA)
        _verify_write_result(root, evidence, EVIDENCE_DATASET, INSTRUMENT_EVIDENCE_SCHEMA)
        components = {
            "provider": provider_id,
            "as_of_date": as_of_date.isoformat(),
            "observed_date": observed_date.isoformat(),
            "source_endpoints": ["/v3/reference/tickers", "/v3/reference/tickers/types"],
            "request_count": request_count,
            "retry_count": 0,
            "catalog_path": catalog.partition_path.relative_to(root).as_posix(),
            "observations_path": observations.partition_path.relative_to(root).as_posix(),
            "evidence_path": evidence.partition_path.relative_to(root).as_posix(),
            "catalog_record_count": catalog.record_count,
            "observation_record_count": observations.record_count,
            "evidence_record_count": evidence.record_count,
            "catalog_content_sha256": catalog.content_sha256,
            "observations_content_sha256": observations.content_sha256,
            "evidence_content_sha256": evidence.content_sha256,
            "catalog_parquet_sha256": catalog.parquet_sha256,
            "observations_parquet_sha256": observations.parquet_sha256,
            "evidence_parquet_sha256": evidence.parquet_sha256,
        }
        logical_hash = _logical_components_hash(components)
        manifest = ProviderSecurityEvidenceSnapshotManifestV1(
            **components,
            created_at=created_at,
            logical_content_sha256=logical_hash,
        )
        partition = root / SNAPSHOT_DIRECTORY / f"as_of_date={as_of_date.isoformat()}"
        if partition.exists() or partition.is_symlink():
            return _validate_existing_logical_snapshot(partition, manifest)
        partition.parent.mkdir(parents=True, exist_ok=True)
        staging = partition.parent / f".{partition.name}.staging.{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise SecurityEvidenceConflictError("logical snapshot staging path already exists")
        try:
            staging.mkdir()
            _write_json(staging / MANIFEST_FILE, manifest.model_dump(mode="json"))
            reread = ProviderSecurityEvidenceSnapshotManifestV1.model_validate_json(
                (staging / MANIFEST_FILE).read_text(encoding="utf-8")
            )
            if reread != manifest:
                raise SecurityEvidenceCorruptionError("logical snapshot manifest reread mismatch")
            _fsync_directory(staging)
            staging.replace(partition)
            _fsync_directory(partition.parent)
            return SecurityEvidenceSnapshotWriteResult(
                partition / MANIFEST_FILE, logical_hash, "published"
            )
        except Exception:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise

    def _root(self) -> Path:
        if not self.root.is_absolute() or self.root.is_symlink() or not self.root.is_dir():
            raise SecurityEvidencePersistenceError("data root is unavailable")
        return self.root.resolve()

    def _publish(
        self,
        *,
        dataset: str,
        partition: Path,
        schema: pa.Schema,
        rows: list[dict[str, Any]],
        manifest_extra: dict[str, object],
    ) -> SecurityEvidenceWriteResult:
        normalized = _normalized_rows(rows)
        content_sha = records_fingerprint(normalized)
        if partition.exists() or partition.is_symlink():
            return _validate_existing(partition, dataset, schema, content_sha, len(rows), manifest_extra)
        partition.parent.mkdir(parents=True, exist_ok=True)
        staging = partition.parent / f".{partition.name}.staging.{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise SecurityEvidenceConflictError("staging path already exists")
        try:
            staging.mkdir()
            parquet_path = staging / PARQUET_FILE
            table = pa.Table.from_pylist(rows, schema=schema)
            pq.write_table(table, parquet_path)
            _fsync_file(parquet_path)
            reread = pq.ParquetFile(parquet_path).read()
            _validate_table(reread, schema, len(rows), content_sha)
            parquet_sha = _file_sha256(parquet_path)
            manifest = {
                "manifest_version": "1.0",
                "dataset_name": dataset,
                "schema_version": SCHEMA_VERSION,
                "record_count": len(rows),
                "content_sha256": content_sha,
                "parquet_sha256": parquet_sha,
                "parquet_file": PARQUET_FILE,
                "created_at": (self.created_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
                "completion_status": COMPLETION_STATUS,
                **manifest_extra,
            }
            _write_json(staging / MANIFEST_FILE, manifest)
            _fsync_directory(staging)
            staging.replace(partition)
            _fsync_directory(partition.parent)
            return SecurityEvidenceWriteResult(dataset, partition, len(rows), content_sha, parquet_sha, "published")
        except Exception:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise


def _validate_existing(
    partition: Path,
    dataset: str,
    schema: pa.Schema,
    content_sha: str,
    count: int,
    extra: dict[str, object],
) -> SecurityEvidenceWriteResult:
    if partition.is_symlink() or not partition.is_dir():
        raise SecurityEvidenceCorruptionError("existing partition is unavailable")
    manifest_path, parquet_path = partition / MANIFEST_FILE, partition / PARQUET_FILE
    if manifest_path.is_symlink() or parquet_path.is_symlink() or not manifest_path.is_file() or not parquet_path.is_file():
        raise SecurityEvidenceCorruptionError("existing partition is incomplete")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SecurityEvidenceCorruptionError("existing manifest is invalid") from exc
    expected = {"dataset_name": dataset, "schema_version": SCHEMA_VERSION, "record_count": count, "content_sha256": content_sha, "completion_status": COMPLETION_STATUS, **extra}
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise SecurityEvidenceConflictError("existing partition conflicts with requested evidence")
    table = pq.ParquetFile(parquet_path).read()
    _validate_table(table, schema, count, content_sha)
    parquet_sha = _file_sha256(parquet_path)
    if manifest.get("parquet_sha256") != parquet_sha:
        raise SecurityEvidenceCorruptionError("existing parquet hash mismatch")
    return SecurityEvidenceWriteResult(dataset, partition, count, content_sha, parquet_sha, "already_present")


def _verify_write_result(
    root: Path,
    result: SecurityEvidenceWriteResult,
    dataset: str,
    schema: pa.Schema,
) -> None:
    try:
        result.partition_path.relative_to(root)
    except ValueError as exc:
        raise SecurityEvidencePersistenceError("evidence partition escapes data root") from exc
    manifest_path = result.partition_path / MANIFEST_FILE
    parquet_path = result.partition_path / PARQUET_FILE
    if any(path.is_symlink() for path in (result.partition_path, manifest_path, parquet_path)):
        raise SecurityEvidenceCorruptionError("evidence partition contains a symlink")
    if not manifest_path.is_file() or not parquet_path.is_file():
        raise SecurityEvidenceCorruptionError("evidence partition is incomplete")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "dataset_name": dataset,
        "record_count": result.record_count,
        "content_sha256": result.content_sha256,
        "parquet_sha256": result.parquet_sha256,
        "completion_status": COMPLETION_STATUS,
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise SecurityEvidenceCorruptionError("evidence partition manifest does not match write result")
    table = pq.ParquetFile(parquet_path).read()
    _validate_table(table, schema, result.record_count, result.content_sha256)
    if _file_sha256(parquet_path) != result.parquet_sha256:
        raise SecurityEvidenceCorruptionError("evidence partition parquet hash mismatch")


def _validate_existing_logical_snapshot(
    partition: Path,
    expected: ProviderSecurityEvidenceSnapshotManifestV1,
) -> SecurityEvidenceSnapshotWriteResult:
    manifest_path = partition / MANIFEST_FILE
    if partition.is_symlink() or manifest_path.is_symlink() or not manifest_path.is_file():
        raise SecurityEvidenceCorruptionError("existing logical snapshot is incomplete")
    actual = ProviderSecurityEvidenceSnapshotManifestV1.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    if actual != expected:
        raise SecurityEvidenceConflictError("existing logical snapshot conflicts with requested evidence")
    return SecurityEvidenceSnapshotWriteResult(
        manifest_path, actual.logical_content_sha256, "already_present"
    )


def read_completed_security_evidence_snapshot(
    root: Path,
    *,
    as_of_date: date,
) -> CompletedSecurityEvidenceSnapshot:
    repository_root = ParquetSecurityEvidenceRepository(root)._root()
    manifest_path = (
        repository_root
        / SNAPSHOT_DIRECTORY
        / f"as_of_date={as_of_date.isoformat()}"
        / MANIFEST_FILE
    )
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise SecurityEvidenceCorruptionError("completed logical snapshot manifest is unavailable")
    manifest = ProviderSecurityEvidenceSnapshotManifestV1.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    if manifest.as_of_date != as_of_date:
        raise SecurityEvidenceCorruptionError("logical snapshot as_of_date mismatch")
    components = {
        field: getattr(manifest, field)
        for field in (
            "provider",
            "as_of_date",
            "observed_date",
            "source_endpoints",
            "request_count",
            "retry_count",
            "catalog_path",
            "observations_path",
            "evidence_path",
            "catalog_record_count",
            "observation_record_count",
            "evidence_record_count",
            "catalog_content_sha256",
            "observations_content_sha256",
            "evidence_content_sha256",
            "catalog_parquet_sha256",
            "observations_parquet_sha256",
            "evidence_parquet_sha256",
        )
    }
    serialized_components = {
        key: value.isoformat() if isinstance(value, date) else list(value) if isinstance(value, tuple) else value
        for key, value in components.items()
    }
    if _logical_components_hash(serialized_components) != manifest.logical_content_sha256:
        raise SecurityEvidenceCorruptionError("logical snapshot fingerprint mismatch")

    catalog = _read_partition_records(
        repository_root,
        manifest.catalog_path,
        CATALOG_DATASET,
        CATALOG_SCHEMA,
        manifest.catalog_record_count,
        manifest.catalog_content_sha256,
        manifest.catalog_parquet_sha256,
        ProviderSecurityTypeCatalogV1,
    )
    observations = _read_partition_records(
        repository_root,
        manifest.observations_path,
        OBSERVATION_DATASET,
        OBSERVATION_SCHEMA,
        manifest.observation_record_count,
        manifest.observations_content_sha256,
        manifest.observations_parquet_sha256,
        ProviderSecurityObservationV1,
    )
    evidence = _read_partition_records(
        repository_root,
        manifest.evidence_path,
        EVIDENCE_DATASET,
        INSTRUMENT_EVIDENCE_SCHEMA,
        manifest.evidence_record_count,
        manifest.evidence_content_sha256,
        manifest.evidence_parquet_sha256,
        ProviderInstrumentSecurityEvidenceV1,
    )
    if tuple(item.provider_type_code for item in catalog) != tuple(sorted(item.provider_type_code for item in catalog)):
        raise SecurityEvidenceCorruptionError("catalog ordering is not deterministic")
    if tuple(item.provider_observation_id for item in observations) != tuple(sorted(item.provider_observation_id for item in observations)):
        raise SecurityEvidenceCorruptionError("observation ordering is not deterministic")
    evidence_keys = tuple((str(item.instrument_id), item.provider_ticker) for item in evidence)
    if evidence_keys != tuple(sorted(evidence_keys)):
        raise SecurityEvidenceCorruptionError("canonical evidence ordering is not deterministic")
    return CompletedSecurityEvidenceSnapshot(manifest, catalog, observations, evidence)


def _read_partition_records(
    root: Path,
    relative_path: str,
    dataset: str,
    schema: pa.Schema,
    count: int,
    content_sha256: str,
    parquet_sha256: str,
    model: type[Any],
) -> tuple[Any, ...]:
    path = root / relative_path
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SecurityEvidenceCorruptionError("logical snapshot path escapes data root") from exc
    manifest_path, parquet_path = path / MANIFEST_FILE, path / PARQUET_FILE
    if any(item.is_symlink() for item in (path, manifest_path, parquet_path)):
        raise SecurityEvidenceCorruptionError("logical snapshot references a symlink")
    if not manifest_path.is_file() or not parquet_path.is_file():
        raise SecurityEvidenceCorruptionError("logical snapshot references an incomplete partition")
    partition_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "dataset_name": dataset,
        "record_count": count,
        "content_sha256": content_sha256,
        "parquet_sha256": parquet_sha256,
        "completion_status": COMPLETION_STATUS,
    }
    if any(partition_manifest.get(key) != value for key, value in expected.items()):
        raise SecurityEvidenceCorruptionError("logical snapshot partition manifest mismatch")
    table = pq.ParquetFile(parquet_path).read()
    _validate_table(table, schema, count, content_sha256)
    if _file_sha256(parquet_path) != parquet_sha256:
        raise SecurityEvidenceCorruptionError("logical snapshot parquet hash mismatch")
    return tuple(model.model_validate(row) for row in table.to_pylist())


def _logical_components_hash(components: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(components, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _catalog_row(record: ProviderSecurityTypeCatalogV1) -> dict[str, Any]:
    return record.model_dump(mode="python")


def _evidence_row(record: ProviderInstrumentSecurityEvidenceV1) -> dict[str, Any]:
    row = record.model_dump(mode="python")
    row["instrument_id"] = str(record.instrument_id)
    row["security_form_evidence"] = record.security_form_evidence.value
    row["evidence_grade"] = record.evidence_grade.value
    row["classification_status"] = record.classification_status.value
    row["universe_disposition"] = record.universe_disposition.value
    row["decision_flags"] = list(record.decision_flags)
    row["review_flags"] = list(record.review_flags)
    row["provider_observation_ids"] = list(record.provider_observation_ids)
    return row


def _observation_row(record: ProviderSecurityObservationV1) -> dict[str, Any]:
    row = record.model_dump(mode="python")
    row["instrument_id"] = str(record.instrument_id) if record.instrument_id is not None else None
    row["security_form_evidence"] = record.security_form_evidence.value
    row["evidence_grade"] = record.evidence_grade.value
    row["observation_status"] = record.observation_status.value
    row["reason_codes"] = list(record.reason_codes)
    row["review_flags"] = list(record.review_flags)
    return row


def write_failed_diagnostic(
    root: Path,
    diagnostic: FailedSecurityEvidenceDiagnosticV1,
) -> FailedDiagnosticWriteResult:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise SecurityEvidencePersistenceError("diagnostic root is unavailable")
    root = root.resolve()
    base = root
    for component in (*Path(DIAGNOSTIC_DIRECTORY).parts, f"as_of_date={diagnostic.as_of_date.isoformat()}"):
        base = base / component
        if base.is_symlink() or (base.exists() and not base.is_dir()):
            raise SecurityEvidencePersistenceError("diagnostic directory is unavailable")
        base.mkdir(exist_ok=True)
    directory = base / f"run_id={diagnostic.run_id}"
    if directory.exists() or directory.is_symlink():
        raise SecurityEvidenceConflictError("failed diagnostic already exists")
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = directory.parent / f".{directory.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise SecurityEvidenceConflictError("failed diagnostic staging path already exists")
    try:
        staging.mkdir()
        target = staging / "failed.json"
        _write_json(target, diagnostic.model_dump(mode="json"))
        reread = FailedSecurityEvidenceDiagnosticV1.model_validate_json(target.read_text(encoding="utf-8"))
        if reread != diagnostic:
            raise SecurityEvidenceCorruptionError("failed diagnostic reread mismatch")
        _fsync_directory(staging)
        staging.replace(directory)
        _fsync_directory(directory.parent)
        return FailedDiagnosticWriteResult(directory / "failed.json", diagnostic.run_id, "written")
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise


def _normalized_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        value = {}
        for key, item in row.items():
            if isinstance(item, datetime):
                value[key] = item.astimezone(UTC).isoformat()
            elif isinstance(item, date):
                value[key] = item.isoformat()
            else:
                value[key] = item
        normalized.append(value)
    return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))


def _validate_table(table: pa.Table, schema: pa.Schema, count: int, content_sha: str) -> None:
    if not table.schema.equals(schema, check_metadata=False):
        raise SecurityEvidenceCorruptionError("Parquet schema mismatch")
    if table.num_rows != count:
        raise SecurityEvidenceCorruptionError("Parquet row count mismatch")
    if records_fingerprint(_normalized_rows(table.to_pylist())) != content_sha:
        raise SecurityEvidenceCorruptionError("Parquet fingerprint mismatch")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: dict[str, object]) -> None:
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    _fsync_file(temp)
    temp.replace(path)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
