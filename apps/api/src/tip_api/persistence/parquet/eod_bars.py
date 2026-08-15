"""PyArrow-backed EOD Price Bar V1 Parquet repository."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1 import EodPriceBarV1
from tip_api.persistence.eod_bars import (
    EodPriceBarConflictError,
    EodPriceBarCorruptionError,
    EodPriceBarPersistenceError,
    EodPriceBarWriteResult,
)
from tip_api.persistence.parquet.manifest import (
    COMPLETION_STATUS,
    MANIFEST_FILE_NAME,
    PARQUET_FILE_NAME,
    build_manifest,
    content_fingerprint,
    decimal_to_string,
    logical_revision_key,
    record_business_key,
    sort_eod_bars,
    table_rows_fingerprint,
    write_manifest_atomic,
)

SCHEMA_VERSION = "1.0"
SCHEMA_VERSION_PARTITION = "1"
DECIMAL_PRECISION = 38
DECIMAL_SCALE = 10

EOD_PRICE_BAR_ARROW_SCHEMA = pa.schema(
    [
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("session_date", pa.date32(), nullable=False),
        pa.field("open", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=False),
        pa.field("high", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=False),
        pa.field("low", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=False),
        pa.field("close", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=False),
        pa.field("volume", pa.int64(), nullable=False),
        pa.field("vwap", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=True),
        pa.field("trade_count", pa.int64(), nullable=True),
        pa.field("notional", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=False),
        pa.field("currency", pa.string(), nullable=False),
        pa.field("split_adjustment_factor", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=False),
        pa.field("dividend_adjustment_factor", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=False),
        pa.field("total_return_adjustment_factor", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=False),
        pa.field("adjusted_close", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=False),
        pa.field("source", pa.string(), nullable=False),
        pa.field("source_record_id", pa.string(), nullable=True),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("revision", pa.int32(), nullable=False),
        pa.field("is_latest_revision", pa.bool_(), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
        pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
        pa.field("schema_version", pa.string(), nullable=False),
    ]
)


@dataclass(frozen=True)
class ParquetEodPriceBarRepository:
    """Persist one-session EOD Price Bar V1 partitions using explicit PyArrow schemas."""

    root: Path
    created_at: datetime | None = None

    def publish_session(
        self,
        records: tuple[EodPriceBarV1, ...],
        *,
        session_date: date,
        provider_id: str,
        quality_summary: dict[str, Any] | None = None,
        identity_snapshot: dict[str, Any] | None = None,
    ) -> EodPriceBarWriteResult:
        normalized_provider_id = _normalize_provider_id(provider_id)
        _validate_records_for_publish(records, session_date=session_date)
        ordered_records = sort_eod_bars(records)
        fingerprint = content_fingerprint(ordered_records)
        root = _prepare_root(self.root)
        partition_path = _partition_path(root, session_date=session_date)

        if partition_path.exists():
            return self._handle_existing_partition(
                partition_path=partition_path,
                records=ordered_records,
                session_date=session_date,
                provider_id=normalized_provider_id,
                content_sha256=fingerprint,
            )

        staging_path = partition_path.parent / f".{partition_path.name}.staging.{os.getpid()}"
        if staging_path.exists() or staging_path.is_symlink():
            raise EodPriceBarConflictError("staging path already exists")

        try:
            staging_path.mkdir(parents=False)
            parquet_path = staging_path / PARQUET_FILE_NAME
            table = records_to_table(ordered_records)
            pq.write_table(table, parquet_path)
            _fsync_file(parquet_path)
            _validate_parquet_file(
                parquet_path,
                expected_records=ordered_records,
                expected_session_date=session_date,
                expected_fingerprint=fingerprint,
            )
            manifest = build_manifest(
                schema_version=SCHEMA_VERSION,
                session_date=session_date,
                provider_id=normalized_provider_id,
                record_count=len(ordered_records),
                content_sha256=fingerprint,
                parquet_file=PARQUET_FILE_NAME,
                created_at=self.created_at or datetime.now(UTC),
                records=ordered_records,
                quality_summary=quality_summary,
                identity_snapshot=identity_snapshot,
            )
            write_manifest_atomic(staging_path / MANIFEST_FILE_NAME, manifest)
            _fsync_directory(staging_path)
            staging_path.replace(partition_path)
            _fsync_directory(partition_path.parent)
        except Exception:
            if staging_path.exists() and not staging_path.is_symlink():
                shutil.rmtree(staging_path)
            raise

        return EodPriceBarWriteResult(
            schema_version=SCHEMA_VERSION,
            session_date=session_date,
            provider_id=normalized_provider_id,
            record_count=len(ordered_records),
            written_record_count=len(ordered_records),
            partition_path=partition_path,
            content_sha256=fingerprint,
            status="published",
        )

    def _handle_existing_partition(
        self,
        *,
        partition_path: Path,
        records: tuple[EodPriceBarV1, ...],
        session_date: date,
        provider_id: str,
        content_sha256: str,
    ) -> EodPriceBarWriteResult:
        if partition_path.is_symlink():
            raise EodPriceBarCorruptionError("partition path is a symlink")
        manifest_path = partition_path / MANIFEST_FILE_NAME
        parquet_path = partition_path / PARQUET_FILE_NAME
        if not manifest_path.exists() or not parquet_path.exists():
            raise EodPriceBarCorruptionError("existing partition is incomplete")
        if manifest_path.is_symlink() or parquet_path.is_symlink():
            raise EodPriceBarCorruptionError("existing partition contains symlinks")
        manifest = _read_manifest(manifest_path)
        try:
            _validate_parquet_file(
                parquet_path,
                expected_records=records,
                expected_session_date=session_date,
                expected_fingerprint=content_sha256,
            )
        except EodPriceBarCorruptionError as exc:
            if manifest.get("content_sha256") != content_sha256:
                raise EodPriceBarConflictError("existing partition content fingerprint differs") from exc
            raise
        expected = {
            "schema_version": SCHEMA_VERSION,
            "session_date": session_date.isoformat(),
            "provider_id": provider_id,
            "record_count": len(records),
            "content_sha256": content_sha256,
            "parquet_file": PARQUET_FILE_NAME,
            "completion_status": COMPLETION_STATUS,
        }
        mismatches = [key for key, value in expected.items() if manifest.get(key) != value]
        if mismatches:
            if manifest.get("content_sha256") != content_sha256:
                raise EodPriceBarConflictError("existing partition content fingerprint differs")
            raise EodPriceBarCorruptionError("existing partition manifest is inconsistent")
        return EodPriceBarWriteResult(
            schema_version=SCHEMA_VERSION,
            session_date=session_date,
            provider_id=provider_id,
            record_count=len(records),
            written_record_count=0,
            partition_path=partition_path,
            content_sha256=content_sha256,
            status="already_present",
        )


def records_to_table(records: tuple[EodPriceBarV1, ...]) -> pa.Table:
    """Convert canonical records into an Arrow table with the explicit V1 schema."""

    ordered_records = sort_eod_bars(records)
    rows = [_record_to_arrow_row(record) for record in ordered_records]
    return pa.Table.from_pylist(rows, schema=EOD_PRICE_BAR_ARROW_SCHEMA)


def _record_to_arrow_row(record: EodPriceBarV1) -> dict[str, Any]:
    return {
        "instrument_id": str(record.instrument_id),
        "session_date": record.session_date,
        "open": _decimal_for_arrow(record.open, field_name="open"),
        "high": _decimal_for_arrow(record.high, field_name="high"),
        "low": _decimal_for_arrow(record.low, field_name="low"),
        "close": _decimal_for_arrow(record.close, field_name="close"),
        "volume": record.volume,
        "vwap": _decimal_for_arrow(record.vwap, field_name="vwap") if record.vwap is not None else None,
        "trade_count": record.trade_count,
        "notional": _decimal_for_arrow(record.notional, field_name="notional"),
        "currency": record.currency,
        "split_adjustment_factor": _decimal_for_arrow(
            record.split_adjustment_factor, field_name="split_adjustment_factor"
        ),
        "dividend_adjustment_factor": _decimal_for_arrow(
            record.dividend_adjustment_factor, field_name="dividend_adjustment_factor"
        ),
        "total_return_adjustment_factor": _decimal_for_arrow(
            record.total_return_adjustment_factor, field_name="total_return_adjustment_factor"
        ),
        "adjusted_close": _decimal_for_arrow(record.adjusted_close, field_name="adjusted_close"),
        "source": record.source,
        "source_record_id": record.source_record_id,
        "ingested_at": record.ingested_at.astimezone(UTC),
        "revision": record.revision,
        "is_latest_revision": record.is_latest_revision,
        "quality_status": record.quality_status.value,
        "quality_flags": list(record.quality_flags),
        "schema_version": record.schema_version,
    }


def _decimal_for_arrow(value: Decimal, *, field_name: str) -> Decimal:
    sign, digits, exponent = value.as_tuple()
    del sign
    scale = max(-exponent, 0)
    precision = len(digits) + max(exponent, 0)
    if scale > DECIMAL_SCALE:
        raise EodPriceBarPersistenceError(f"{field_name} exceeds decimal scale {DECIMAL_SCALE}")
    if precision > DECIMAL_PRECISION:
        raise EodPriceBarPersistenceError(f"{field_name} exceeds decimal precision {DECIMAL_PRECISION}")
    return value


def _validate_records_for_publish(records: tuple[EodPriceBarV1, ...], *, session_date: date) -> None:
    if len(records) == 0:
        raise EodPriceBarPersistenceError("cannot publish an empty EOD session")
    business_keys: set[tuple[str, str, str, int]] = set()
    latest_counts: dict[tuple[str, str, str], int] = {}
    for record in records:
        if record.schema_version != SCHEMA_VERSION:
            raise EodPriceBarPersistenceError("unsupported EOD Price Bar schema_version")
        if record.session_date != session_date:
            raise EodPriceBarPersistenceError("record session_date does not match partition session_date")
        key = record_business_key(record)
        if key in business_keys:
            raise EodPriceBarPersistenceError("duplicate EOD Price Bar business key")
        business_keys.add(key)
        if record.is_latest_revision:
            latest_key = logical_revision_key(record)
            latest_counts[latest_key] = latest_counts.get(latest_key, 0) + 1
            if latest_counts[latest_key] > 1:
                raise EodPriceBarPersistenceError("multiple latest revisions for one logical EOD bar")


def _prepare_root(root: Path) -> Path:
    if root.exists() and root.is_symlink():
        raise EodPriceBarPersistenceError("root path must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    resolved = root.resolve()
    if resolved.is_symlink():
        raise EodPriceBarPersistenceError("resolved root path must not be a symlink")
    return resolved


def _partition_path(root: Path, *, session_date: date) -> Path:
    partition = (
        root
        / "market-data"
        / "eod-price-bars"
        / f"schema_version={SCHEMA_VERSION_PARTITION}"
        / f"session_date={session_date.isoformat()}"
    )
    resolved_parent = partition.parent.resolve(strict=False)
    if root not in (resolved_parent, *resolved_parent.parents):
        raise EodPriceBarPersistenceError("partition path escapes root")
    partition.parent.mkdir(parents=True, exist_ok=True)
    if partition.exists() and partition.is_symlink():
        raise EodPriceBarPersistenceError("partition path must not be a symlink")
    return partition


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise EodPriceBarCorruptionError("manifest cannot be read") from exc
    if not isinstance(data, dict):
        raise EodPriceBarCorruptionError("manifest must be a JSON object")
    return data


def _validate_parquet_file(
    path: Path,
    *,
    expected_records: tuple[EodPriceBarV1, ...],
    expected_session_date: date,
    expected_fingerprint: str,
) -> None:
    try:
        table = pq.ParquetFile(path).read()
    except Exception as exc:
        raise EodPriceBarCorruptionError("parquet file cannot be read") from exc
    if not table.schema.equals(EOD_PRICE_BAR_ARROW_SCHEMA, check_metadata=False):
        raise EodPriceBarCorruptionError("parquet schema does not match EOD Price Bar V1")
    if table.num_rows != len(expected_records):
        raise EodPriceBarCorruptionError("parquet row count does not match expected records")
    rows = _table_to_fingerprint_rows(table)
    session_dates = {row["session_date"] for row in rows}
    if session_dates != {expected_session_date.isoformat()}:
        raise EodPriceBarCorruptionError("parquet session_date does not match partition")
    if table_rows_fingerprint(rows) != expected_fingerprint:
        raise EodPriceBarCorruptionError("parquet content fingerprint does not match expected records")


def _table_to_fingerprint_rows(table: pa.Table) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in table.to_pylist():
        ingested_at = raw["ingested_at"]
        if not isinstance(ingested_at, datetime):
            raise EodPriceBarCorruptionError("ingested_at did not round trip as datetime")
        session_date = raw["session_date"]
        if not isinstance(session_date, date):
            raise EodPriceBarCorruptionError("session_date did not round trip as date")
        rows.append(
            {
                "instrument_id": raw["instrument_id"],
                "session_date": session_date.isoformat(),
                "open": decimal_to_string(raw["open"]),
                "high": decimal_to_string(raw["high"]),
                "low": decimal_to_string(raw["low"]),
                "close": decimal_to_string(raw["close"]),
                "volume": raw["volume"],
                "vwap": decimal_to_string(raw["vwap"]),
                "trade_count": raw["trade_count"],
                "notional": decimal_to_string(raw["notional"]),
                "currency": raw["currency"],
                "split_adjustment_factor": decimal_to_string(raw["split_adjustment_factor"]),
                "dividend_adjustment_factor": decimal_to_string(raw["dividend_adjustment_factor"]),
                "total_return_adjustment_factor": decimal_to_string(raw["total_return_adjustment_factor"]),
                "adjusted_close": decimal_to_string(raw["adjusted_close"]),
                "source": raw["source"],
                "source_record_id": raw["source_record_id"],
                "ingested_at": ingested_at.astimezone(UTC).isoformat(),
                "revision": raw["revision"],
                "is_latest_revision": raw["is_latest_revision"],
                "quality_status": raw["quality_status"],
                "quality_flags": raw["quality_flags"],
                "schema_version": raw["schema_version"],
            }
        )
    return sorted(rows, key=lambda row: (row["instrument_id"], row["session_date"], row["source"], row["revision"]))


def _normalize_provider_id(provider_id: str) -> str:
    if not isinstance(provider_id, str):
        raise EodPriceBarPersistenceError("provider_id must be a string")
    normalized = provider_id.strip()
    if not normalized:
        raise EodPriceBarPersistenceError("provider_id must not be empty")
    return normalized


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
