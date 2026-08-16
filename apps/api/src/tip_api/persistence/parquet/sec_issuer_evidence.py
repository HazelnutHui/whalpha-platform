"""Atomic Parquet repository for future canonical SEC issuer evidence."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.security_classification.v1 import SecIssuerEvidenceManifestV1, SecIssuerStructureEvidenceV1
from tip_api.persistence.parquet.instrument_master_snapshot import records_fingerprint
from tip_api.persistence.sec_issuer_evidence import (
    SecIssuerEvidenceConflictError,
    SecIssuerEvidenceCorruptionError,
    SecIssuerEvidencePersistenceError,
    SecIssuerEvidenceWriteResult,
)

SEC_ISSUER_EVIDENCE_DATASET = "sec-issuer-structure-evidence"
SEC_ISSUER_EVIDENCE_RELATIVE_ROOT = Path("market-data") / SEC_ISSUER_EVIDENCE_DATASET
PARQUET_FILE = "part-00000.parquet"
MANIFEST_FILE = "manifest.json"

SEC_ISSUER_EVIDENCE_SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), nullable=False),
    pa.field("evidence_kind", pa.string(), nullable=False),
    pa.field("evidence_version", pa.string(), nullable=False),
    pa.field("as_of_date", pa.date32(), nullable=False),
    pa.field("instrument_id", pa.string(), nullable=False),
    pa.field("cik", pa.string(), nullable=False),
    pa.field("asserted_security_form", pa.string(), nullable=True),
    pa.field("asserted_issuer_structure", pa.string(), nullable=True),
    pa.field("asserted_listing_scope", pa.string(), nullable=True),
    pa.field("evidence_grade", pa.string(), nullable=False),
    pa.field("universe_disposition", pa.string(), nullable=False),
    pa.field("source_observation_ids", pa.list_(pa.string()), nullable=False),
    pa.field("decision_reasons", pa.list_(pa.string()), nullable=False),
    pa.field("quality_status", pa.string(), nullable=False),
    pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
    pa.field("source_observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
])


@dataclass(frozen=True, slots=True)
class ParquetSecIssuerEvidenceRepository:
    root: Path
    created_at: datetime

    def publish(
        self,
        records: tuple[SecIssuerStructureEvidenceV1, ...],
        *,
        source_datasets: tuple[str, ...],
    ) -> SecIssuerEvidenceWriteResult:
        root = self._validated_root()
        if not records:
            raise SecIssuerEvidencePersistenceError("SEC evidence cannot be empty")
        dates = {item.as_of_date for item in records}
        if len(dates) != 1:
            raise SecIssuerEvidencePersistenceError("SEC evidence must contain one as_of_date")
        ordered = tuple(sorted(records, key=lambda item: (str(item.instrument_id), item.as_of_date, item.evidence_kind, item.evidence_version)))
        if len({item.business_key for item in ordered}) != len(ordered):
            raise SecIssuerEvidenceConflictError("SEC evidence business key conflict")
        rows = [_row(item) for item in ordered]
        content_sha = records_fingerprint(_normalized_rows(rows))
        as_of_date = next(iter(dates))
        partition = root / SEC_ISSUER_EVIDENCE_RELATIVE_ROOT / "schema_version=1" / f"as_of_date={as_of_date.isoformat()}"
        if partition.exists() or partition.is_symlink():
            return self._validate_existing(partition, content_sha, len(rows))
        partition.parent.mkdir(parents=True, exist_ok=True)
        staging = partition.parent / f".{partition.name}.staging.{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise SecIssuerEvidenceConflictError("SEC evidence staging path already exists")
        try:
            staging.mkdir()
            table = pa.Table.from_pylist(rows, schema=SEC_ISSUER_EVIDENCE_SCHEMA)
            parquet = staging / PARQUET_FILE
            pq.write_table(table, parquet, compression="zstd")
            reread = pq.ParquetFile(parquet).read()
            _validate_table(reread, len(rows), content_sha)
            parquet_sha = _file_sha256(parquet)
            manifest = SecIssuerEvidenceManifestV1(
                as_of_date=as_of_date,
                record_count=len(rows),
                content_sha256=content_sha,
                parquet_sha256=parquet_sha,
                source_datasets=source_datasets,
                created_at=self.created_at,
            )
            _write_json(staging / MANIFEST_FILE, manifest.model_dump(mode="json"))
            if SecIssuerEvidenceManifestV1.model_validate_json((staging / MANIFEST_FILE).read_text()) != manifest:
                raise SecIssuerEvidenceCorruptionError("SEC evidence manifest reread mismatch")
            staging.replace(partition)
            return SecIssuerEvidenceWriteResult(partition, len(rows), content_sha, parquet_sha, "published")
        except Exception:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise

    def _validated_root(self) -> Path:
        if not self.root.is_absolute() or self.root.is_symlink() or not self.root.is_dir():
            raise SecIssuerEvidencePersistenceError("SEC evidence root is unavailable")
        return self.root.resolve()

    def _validate_existing(self, partition: Path, content_sha: str, count: int) -> SecIssuerEvidenceWriteResult:
        if partition.is_symlink() or not partition.is_dir():
            raise SecIssuerEvidenceCorruptionError("existing SEC evidence partition is invalid")
        manifest_path, parquet = partition / MANIFEST_FILE, partition / PARQUET_FILE
        if any(path.is_symlink() for path in (manifest_path, parquet)) or not manifest_path.is_file() or not parquet.is_file():
            raise SecIssuerEvidenceCorruptionError("existing SEC evidence partition is incomplete")
        manifest = SecIssuerEvidenceManifestV1.model_validate_json(manifest_path.read_text())
        if manifest.record_count != count or manifest.content_sha256 != content_sha:
            raise SecIssuerEvidenceConflictError("existing SEC evidence partition conflicts")
        table = pq.ParquetFile(parquet).read()
        _validate_table(table, count, content_sha)
        if _file_sha256(parquet) != manifest.parquet_sha256:
            raise SecIssuerEvidenceCorruptionError("existing SEC evidence Parquet hash mismatch")
        return SecIssuerEvidenceWriteResult(partition, count, content_sha, manifest.parquet_sha256, "already_present")


def read_completed_sec_issuer_evidence(partition: Path) -> tuple[SecIssuerStructureEvidenceV1, ...]:
    if partition.is_symlink() or not partition.is_dir():
        raise SecIssuerEvidenceCorruptionError("SEC evidence partition is invalid")
    manifest = SecIssuerEvidenceManifestV1.model_validate_json((partition / MANIFEST_FILE).read_text())
    table = pq.ParquetFile(partition / PARQUET_FILE).read()
    _validate_table(table, manifest.record_count, manifest.content_sha256)
    if _file_sha256(partition / PARQUET_FILE) != manifest.parquet_sha256:
        raise SecIssuerEvidenceCorruptionError("SEC evidence Parquet hash mismatch")
    return tuple(SecIssuerStructureEvidenceV1.model_validate(row) for row in table.to_pylist())


def _row(record: SecIssuerStructureEvidenceV1) -> dict[str, Any]:
    value = record.model_dump(mode="python")
    value["instrument_id"] = str(record.instrument_id)
    for field in ("asserted_security_form", "asserted_issuer_structure", "asserted_listing_scope"):
        item = value[field]
        value[field] = item.value if item is not None else None
    value["evidence_grade"] = record.evidence_grade.value
    value["universe_disposition"] = record.universe_disposition.value
    value["quality_status"] = record.quality_status.value
    value["source_observation_ids"] = list(record.source_observation_ids)
    value["decision_reasons"] = list(record.decision_reasons)
    value["quality_flags"] = list(record.quality_flags)
    return value


def _normalized_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                item[key] = value.astimezone(UTC).isoformat()
            elif isinstance(value, date):
                item[key] = value.isoformat()
            else:
                item[key] = value
        normalized.append(item)
    return sorted(normalized, key=lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")))


def _validate_table(table: pa.Table, count: int, content_sha: str) -> None:
    if not table.schema.equals(SEC_ISSUER_EVIDENCE_SCHEMA, check_metadata=False):
        raise SecIssuerEvidenceCorruptionError("SEC evidence schema mismatch")
    if table.num_rows != count:
        raise SecIssuerEvidenceCorruptionError("SEC evidence row count mismatch")
    if records_fingerprint(_normalized_rows(table.to_pylist())) != content_sha:
        raise SecIssuerEvidenceCorruptionError("SEC evidence fingerprint mismatch")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
