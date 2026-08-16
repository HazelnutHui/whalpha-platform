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
    ProviderInstrumentSecurityEvidenceV1,
    ProviderSecurityTypeCatalogV1,
)
from tip_api.persistence.parquet.instrument_master_snapshot import records_fingerprint
from tip_api.persistence.security_evidence import (
    SecurityEvidenceConflictError,
    SecurityEvidenceCorruptionError,
    SecurityEvidencePersistenceError,
    SecurityEvidenceWriteResult,
)

SCHEMA_VERSION = "1.0"
SCHEMA_PARTITION = "1"
PARQUET_FILE = "part-00000.parquet"
MANIFEST_FILE = "manifest.json"
COMPLETION_STATUS = "completed"
CATALOG_DATASET = "provider-security-type-catalog"
EVIDENCE_DATASET = "provider-instrument-security-evidence"

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
        pa.field("as_of_date", pa.date32(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("provider", pa.string(), nullable=False),
        pa.field("provider_ticker", pa.string(), nullable=False),
        pa.field("provider_type_code", pa.string(), nullable=False),
        pa.field("provider_type_description", pa.string(), nullable=False),
        pa.field("primary_exchange", pa.string(), nullable=False),
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
    return row


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
