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
    ProviderSecurityTypeCatalogV1,
)
from tip_api.persistence.parquet.instrument_master_snapshot import records_fingerprint
from tip_api.persistence.security_evidence import (
    SecurityEvidenceConflictError,
    SecurityEvidenceCorruptionError,
    SecurityEvidencePersistenceError,
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
