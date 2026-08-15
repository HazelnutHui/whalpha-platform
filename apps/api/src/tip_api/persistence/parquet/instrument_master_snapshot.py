"""PyArrow-backed Instrument Master point-in-time snapshot repository."""

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

from tip_api.contracts.market_data.v1 import InstrumentMasterV1, ProviderInstrumentIdentityV1, ProviderTickerResolverV1
from tip_api.persistence.instrument_master import (
    InstrumentMasterSnapshotConflictError,
    InstrumentMasterSnapshotCorruptionError,
    InstrumentMasterSnapshotPersistenceError,
    InstrumentMasterSnapshotWriteResult,
)

SCHEMA_VERSION = "1.0"
SCHEMA_VERSION_PARTITION = "1"
PARQUET_FILE_NAME = "part-00000.parquet"
MANIFEST_FILE_NAME = "manifest.json"
COMPLETION_STATUS = "completed"

INSTRUMENT_MASTER_ARROW_SCHEMA = pa.schema(
    [
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("issuer_id", pa.string(), nullable=True),
        pa.field("instrument_type", pa.string(), nullable=False),
        pa.field("status", pa.string(), nullable=False),
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("ticker", pa.string(), nullable=False),
        pa.field("name", pa.string(), nullable=False),
        pa.field("primary_exchange", pa.string(), nullable=False),
        pa.field("listing_country", pa.string(), nullable=False),
        pa.field("currency", pa.string(), nullable=False),
        pa.field("figi", pa.string(), nullable=True),
        pa.field("cik", pa.string(), nullable=True),
        pa.field("valid_from", pa.date32(), nullable=False),
        pa.field("valid_to", pa.date32(), nullable=True),
        pa.field("first_trade_date", pa.date32(), nullable=True),
        pa.field("last_trade_date", pa.date32(), nullable=True),
        pa.field("as_of_date", pa.date32(), nullable=False),
        pa.field("source", pa.string(), nullable=False),
        pa.field("source_instrument_id", pa.string(), nullable=False),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
        pa.field("quality_notes", pa.string(), nullable=True),
    ]
)

PROVIDER_IDENTITY_ARROW_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("provider", pa.string(), nullable=False),
        pa.field("as_of_date", pa.date32(), nullable=False),
        pa.field("provider_ticker", pa.string(), nullable=False),
        pa.field("provider_instrument_id", pa.string(), nullable=True),
        pa.field("composite_figi", pa.string(), nullable=True),
        pa.field("share_class_figi", pa.string(), nullable=True),
        pa.field("cik", pa.string(), nullable=True),
        pa.field("canonical_instrument_id", pa.string(), nullable=True),
        pa.field("resolution_status", pa.string(), nullable=False),
        pa.field("resolution_method", pa.string(), nullable=False),
        pa.field("valid_from", pa.date32(), nullable=False),
        pa.field("valid_to", pa.date32(), nullable=True),
        pa.field("source_updated_at", pa.timestamp("us", tz="UTC"), nullable=True),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
        pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
    ]
)

PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("provider", pa.string(), nullable=False),
        pa.field("as_of_date", pa.date32(), nullable=False),
        pa.field("provider_ticker", pa.string(), nullable=False),
        pa.field("canonical_instrument_id", pa.string(), nullable=False),
        pa.field("resolution_method", pa.string(), nullable=False),
        pa.field("source_identity_key", pa.string(), nullable=False),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
    ]
)


def sort_instruments(records: tuple[InstrumentMasterV1, ...]) -> tuple[InstrumentMasterV1, ...]:
    return tuple(sorted(records, key=lambda record: (str(record.instrument_id), record.ticker, record.source_instrument_id)))


def sort_identities(records: tuple[ProviderInstrumentIdentityV1, ...]) -> tuple[ProviderInstrumentIdentityV1, ...]:
    return tuple(sorted(records, key=lambda record: (record.provider_ticker, record.provider_instrument_id or "", record.composite_figi or "", record.share_class_figi or "")))


def sort_resolvers(records: tuple[ProviderTickerResolverV1, ...]) -> tuple[ProviderTickerResolverV1, ...]:
    return tuple(sorted(records, key=lambda record: (record.provider_ticker, str(record.canonical_instrument_id))))

def resolver_content_fingerprint(records: tuple[ProviderTickerResolverV1, ...]) -> str:
    return records_fingerprint([_resolver_fingerprint_row(record) for record in sort_resolvers(records)])

def records_fingerprint(rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def instrument_content_fingerprint(records: tuple[InstrumentMasterV1, ...]) -> str:
    return records_fingerprint([_instrument_fingerprint_row(record) for record in sort_instruments(records)])


def identity_content_fingerprint(records: tuple[ProviderInstrumentIdentityV1, ...]) -> str:
    return records_fingerprint([_identity_fingerprint_row(record) for record in sort_identities(records)])


@dataclass(frozen=True)
class ParquetInstrumentMasterSnapshotRepository:
    """Persist Instrument Master and provider identity datasets with a snapshot marker."""

    root: Path
    created_at: datetime | None = None

    def publish_snapshot(
        self,
        *,
        instruments: tuple[InstrumentMasterV1, ...],
        identities: tuple[ProviderInstrumentIdentityV1, ...],
        resolvers: tuple[ProviderTickerResolverV1, ...],
        as_of_date: date,
        provider_id: str,
        quality_summary: dict[str, object],
    ) -> InstrumentMasterSnapshotWriteResult:
        provider_id = _normalize_provider_id(provider_id)
        _validate_snapshot_records(instruments=instruments, identities=identities, resolvers=resolvers, as_of_date=as_of_date, provider_id=provider_id)
        instruments = sort_instruments(instruments)
        identities = sort_identities(identities)
        resolvers = sort_resolvers(resolvers)
        instrument_sha = instrument_content_fingerprint(instruments)
        identity_sha = identity_content_fingerprint(identities)
        resolver_sha = resolver_content_fingerprint(resolvers)
        snapshot_sha = records_fingerprint([{"instrument_content_sha256": instrument_sha, "identity_content_sha256": identity_sha, "resolver_content_sha256": resolver_sha}])
        root = _prepare_root(self.root)
        instrument_partition = _instrument_partition_path(root, as_of_date)
        identity_partition = _identity_partition_path(root, provider_id, as_of_date)
        resolver_partition = _resolver_partition_path(root, provider_id, as_of_date)
        snapshot_dir = _snapshot_manifest_dir(root, as_of_date)
        snapshot_manifest = snapshot_dir / MANIFEST_FILE_NAME

        if snapshot_manifest.exists():
            return self._handle_existing_snapshot(
                instruments=instruments,
                identities=identities,
                resolvers=resolvers,
                as_of_date=as_of_date,
                provider_id=provider_id,
                instrument_partition=instrument_partition,
                identity_partition=identity_partition,
                resolver_partition=resolver_partition,
                snapshot_manifest=snapshot_manifest,
                instrument_sha=instrument_sha,
                identity_sha=identity_sha,
                resolver_sha=resolver_sha,
                snapshot_sha=snapshot_sha,
            )
        if instrument_partition.exists() or identity_partition.exists() or resolver_partition.exists() or snapshot_dir.exists():
            raise InstrumentMasterSnapshotCorruptionError("existing snapshot artifacts are incomplete")

        created_at = self.created_at or datetime.now(UTC)
        try:
            self._write_partition(
                partition_path=instrument_partition,
                table=instrument_records_to_table(instruments),
                expected_schema=INSTRUMENT_MASTER_ARROW_SCHEMA,
                expected_fingerprint=instrument_sha,
                expected_count=len(instruments),
                manifest=_dataset_manifest(
                    dataset_name="instrument-master",
                    schema_version=SCHEMA_VERSION,
                    as_of_date=as_of_date,
                    provider_id=provider_id,
                    record_count=len(instruments),
                    content_sha256=instrument_sha,
                    created_at=created_at,
                    quality_summary=quality_summary,
                ),
                table_to_rows=_instrument_table_to_rows,
            )
            self._write_partition(
                partition_path=identity_partition,
                table=identity_records_to_table(identities),
                expected_schema=PROVIDER_IDENTITY_ARROW_SCHEMA,
                expected_fingerprint=identity_sha,
                expected_count=len(identities),
                manifest=_dataset_manifest(
                    dataset_name="provider-instrument-identity",
                    schema_version=SCHEMA_VERSION,
                    as_of_date=as_of_date,
                    provider_id=provider_id,
                    record_count=len(identities),
                    content_sha256=identity_sha,
                    created_at=created_at,
                    quality_summary=quality_summary,
                ),
                table_to_rows=_identity_table_to_rows,
            )

            self._write_partition(
                partition_path=resolver_partition,
                table=resolver_records_to_table(resolvers),
                expected_schema=PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA,
                expected_fingerprint=resolver_sha,
                expected_count=len(resolvers),
                manifest=_dataset_manifest(
                    dataset_name="provider-ticker-resolver",
                    schema_version=SCHEMA_VERSION,
                    as_of_date=as_of_date,
                    provider_id=provider_id,
                    record_count=len(resolvers),
                    content_sha256=resolver_sha,
                    created_at=created_at,
                    quality_summary=quality_summary,
                ),
                table_to_rows=_resolver_table_to_rows,
            )
            snapshot_dir.mkdir(parents=True, exist_ok=False)
            write_json_atomic(snapshot_manifest, _snapshot_manifest(
                as_of_date=as_of_date,
                provider_id=provider_id,
                instrument_partition_path=instrument_partition,
                identity_partition_path=identity_partition,
                resolver_partition_path=resolver_partition,
                instrument_count=len(instruments),
                identity_count=len(identities),
                resolver_count=len(resolvers),
                instrument_sha=instrument_sha,
                identity_sha=identity_sha,
                resolver_sha=resolver_sha,
                snapshot_sha=snapshot_sha,
                created_at=created_at,
                quality_summary=quality_summary,
            ))
            _fsync_directory(snapshot_dir)
            _fsync_directory(snapshot_dir.parent)
        except Exception:
            for path in (instrument_partition, identity_partition, resolver_partition, snapshot_dir):
                if path.exists() and not path.is_symlink():
                    shutil.rmtree(path)
            raise

        return InstrumentMasterSnapshotWriteResult(
            schema_version=SCHEMA_VERSION,
            as_of_date=as_of_date,
            provider_id=provider_id,
            instrument_count=len(instruments),
            identity_count=len(identities),
            resolver_count=len(resolvers),
            written_instrument_count=len(instruments),
            written_identity_count=len(identities),
            written_resolver_count=len(resolvers),
            instrument_partition_path=instrument_partition,
            identity_partition_path=identity_partition,
            resolver_partition_path=resolver_partition,
            snapshot_manifest_path=snapshot_manifest,
            instrument_content_sha256=instrument_sha,
            identity_content_sha256=identity_sha,
            resolver_content_sha256=resolver_sha,
            snapshot_content_sha256=snapshot_sha,
            status="published",
        )

    def _write_partition(self, *, partition_path: Path, table: pa.Table, expected_schema: pa.Schema, expected_fingerprint: str, expected_count: int, manifest: dict[str, object], table_to_rows: Any) -> None:
        partition_path.parent.mkdir(parents=True, exist_ok=True)
        staging_path = partition_path.parent / f".{partition_path.name}.staging.{os.getpid()}"
        if staging_path.exists() or staging_path.is_symlink():
            raise InstrumentMasterSnapshotConflictError("staging path already exists")
        try:
            staging_path.mkdir(parents=False)
            parquet_path = staging_path / PARQUET_FILE_NAME
            pq.write_table(table, parquet_path)
            _fsync_file(parquet_path)
            _validate_parquet(parquet_path, expected_schema=expected_schema, expected_fingerprint=expected_fingerprint, expected_count=expected_count, table_to_rows=table_to_rows)
            write_json_atomic(staging_path / MANIFEST_FILE_NAME, manifest)
            _fsync_directory(staging_path)
            staging_path.replace(partition_path)
            _fsync_directory(partition_path.parent)
        except Exception:
            if staging_path.exists() and not staging_path.is_symlink():
                shutil.rmtree(staging_path)
            raise

    def _handle_existing_snapshot(self, *, instruments: tuple[InstrumentMasterV1, ...], identities: tuple[ProviderInstrumentIdentityV1, ...], resolvers: tuple[ProviderTickerResolverV1, ...], as_of_date: date, provider_id: str, instrument_partition: Path, identity_partition: Path, resolver_partition: Path, snapshot_manifest: Path, instrument_sha: str, identity_sha: str, resolver_sha: str, snapshot_sha: str) -> InstrumentMasterSnapshotWriteResult:
        manifest = _read_json(snapshot_manifest)
        expected = {
            "completion_status": COMPLETION_STATUS,
            "as_of_date": as_of_date.isoformat(),
            "provider_id": provider_id,
            "instrument_content_sha256": instrument_sha,
            "identity_content_sha256": identity_sha,
            "resolver_content_sha256": resolver_sha,
            "snapshot_content_sha256": snapshot_sha,
            "instrument_count": len(instruments),
            "identity_count": len(identities),
            "resolver_count": len(resolvers),
        }
        if any(manifest.get(key) != value for key, value in expected.items()):
            raise InstrumentMasterSnapshotConflictError("existing snapshot manifest differs")
        _validate_existing_partition(instrument_partition, expected_schema=INSTRUMENT_MASTER_ARROW_SCHEMA, expected_fingerprint=instrument_sha, expected_count=len(instruments), table_to_rows=_instrument_table_to_rows)
        _validate_existing_partition(identity_partition, expected_schema=PROVIDER_IDENTITY_ARROW_SCHEMA, expected_fingerprint=identity_sha, expected_count=len(identities), table_to_rows=_identity_table_to_rows)
        _validate_existing_partition(resolver_partition, expected_schema=PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA, expected_fingerprint=resolver_sha, expected_count=len(resolvers), table_to_rows=_resolver_table_to_rows)
        return InstrumentMasterSnapshotWriteResult(
            schema_version=SCHEMA_VERSION,
            as_of_date=as_of_date,
            provider_id=provider_id,
            instrument_count=len(instruments),
            identity_count=len(identities),
            resolver_count=len(resolvers),
            written_instrument_count=0,
            written_identity_count=0,
            written_resolver_count=0,
            instrument_partition_path=instrument_partition,
            identity_partition_path=identity_partition,
            resolver_partition_path=resolver_partition,
            snapshot_manifest_path=snapshot_manifest,
            instrument_content_sha256=instrument_sha,
            identity_content_sha256=identity_sha,
            resolver_content_sha256=resolver_sha,
            snapshot_content_sha256=snapshot_sha,
            status="already_present",
        )


def instrument_records_to_table(records: tuple[InstrumentMasterV1, ...]) -> pa.Table:
    return pa.Table.from_pylist([_instrument_arrow_row(record) for record in sort_instruments(records)], schema=INSTRUMENT_MASTER_ARROW_SCHEMA)


def identity_records_to_table(records: tuple[ProviderInstrumentIdentityV1, ...]) -> pa.Table:
    return pa.Table.from_pylist([_identity_arrow_row(record) for record in sort_identities(records)], schema=PROVIDER_IDENTITY_ARROW_SCHEMA)


def resolver_records_to_table(records: tuple[ProviderTickerResolverV1, ...]) -> pa.Table:
    return pa.Table.from_pylist([_resolver_arrow_row(record) for record in sort_resolvers(records)], schema=PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA)

def _instrument_arrow_row(record: InstrumentMasterV1) -> dict[str, Any]:
    return {
        "instrument_id": str(record.instrument_id),
        "issuer_id": str(record.issuer_id) if record.issuer_id else None,
        "instrument_type": record.instrument_type.value,
        "status": record.status.value,
        "schema_version": record.schema_version,
        "ticker": record.ticker,
        "name": record.name,
        "primary_exchange": record.primary_exchange,
        "listing_country": record.listing_country,
        "currency": record.currency,
        "figi": record.figi,
        "cik": record.cik,
        "valid_from": record.valid_from,
        "valid_to": record.valid_to,
        "first_trade_date": record.first_trade_date,
        "last_trade_date": record.last_trade_date,
        "as_of_date": record.as_of_date,
        "source": record.source,
        "source_instrument_id": record.source_instrument_id,
        "ingested_at": record.ingested_at.astimezone(UTC),
        "quality_status": record.quality_status.value,
        "quality_notes": record.quality_notes,
    }


def _identity_arrow_row(record: ProviderInstrumentIdentityV1) -> dict[str, Any]:
    return {
        "schema_version": record.schema_version,
        "provider": record.provider,
        "as_of_date": record.as_of_date,
        "provider_ticker": record.provider_ticker,
        "provider_instrument_id": record.provider_instrument_id,
        "composite_figi": record.composite_figi,
        "share_class_figi": record.share_class_figi,
        "cik": record.cik,
        "canonical_instrument_id": str(record.canonical_instrument_id) if record.canonical_instrument_id else None,
        "resolution_status": record.resolution_status.value,
        "resolution_method": record.resolution_method.value,
        "valid_from": record.valid_from,
        "valid_to": record.valid_to,
        "source_updated_at": record.source_updated_at.astimezone(UTC) if record.source_updated_at else None,
        "ingested_at": record.ingested_at.astimezone(UTC),
        "quality_status": record.quality_status.value,
        "quality_flags": list(record.quality_flags),
    }


def _resolver_arrow_row(record: ProviderTickerResolverV1) -> dict[str, Any]:
    return {"schema_version": record.schema_version, "provider": record.provider, "as_of_date": record.as_of_date, "provider_ticker": record.provider_ticker, "canonical_instrument_id": str(record.canonical_instrument_id), "resolution_method": record.resolution_method, "source_identity_key": record.source_identity_key, "ingested_at": record.ingested_at.astimezone(UTC)}

def _instrument_fingerprint_row(record: InstrumentMasterV1) -> dict[str, Any]:
    row = _instrument_arrow_row(record)
    return _normalize_row(row)


def _identity_fingerprint_row(record: ProviderInstrumentIdentityV1) -> dict[str, Any]:
    row = _identity_arrow_row(record)
    return _normalize_row(row)


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            normalized[key] = value.astimezone(UTC).isoformat()
        elif isinstance(value, date):
            normalized[key] = value.isoformat()
        else:
            normalized[key] = value
    return normalized


def _instrument_table_to_rows(table: pa.Table) -> list[dict[str, Any]]:
    rows = [_normalize_row(dict(row)) for row in table.to_pylist()]
    return sorted(rows, key=lambda row: (row["instrument_id"], row["ticker"], row["source_instrument_id"]))


def _identity_table_to_rows(table: pa.Table) -> list[dict[str, Any]]:
    rows = [_normalize_row(dict(row)) for row in table.to_pylist()]
    return sorted(rows, key=lambda row: (row["provider_ticker"], row["provider_instrument_id"] or "", row["composite_figi"] or "", row["share_class_figi"] or ""))


def _resolver_fingerprint_row(record: ProviderTickerResolverV1) -> dict[str, Any]:
    return _normalize_row(_resolver_arrow_row(record))

def _resolver_table_to_rows(table: pa.Table) -> list[dict[str, Any]]:
    rows = [_normalize_row(dict(row)) for row in table.to_pylist()]
    return sorted(rows, key=lambda row: (row["provider_ticker"], row["canonical_instrument_id"]))

def _validate_snapshot_records(*, instruments: tuple[InstrumentMasterV1, ...], identities: tuple[ProviderInstrumentIdentityV1, ...], resolvers: tuple[ProviderTickerResolverV1, ...], as_of_date: date, provider_id: str) -> None:
    if not instruments:
        raise InstrumentMasterSnapshotPersistenceError("cannot publish an empty Instrument Master snapshot")
    if not identities:
        raise InstrumentMasterSnapshotPersistenceError("cannot publish an empty provider identity snapshot")
    instrument_ids = set()
    for record in instruments:
        if record.as_of_date != as_of_date:
            raise InstrumentMasterSnapshotPersistenceError("instrument as_of_date mismatch")
        if record.source != provider_id:
            raise InstrumentMasterSnapshotPersistenceError("instrument provider source mismatch")
        if record.instrument_id in instrument_ids:
            raise InstrumentMasterSnapshotPersistenceError("duplicate canonical instrument_id")
        instrument_ids.add(record.instrument_id)
    for record in resolvers:
        if record.as_of_date != as_of_date:
            raise InstrumentMasterSnapshotPersistenceError("resolver as_of_date mismatch")
        if record.provider != provider_id:
            raise InstrumentMasterSnapshotPersistenceError("resolver provider mismatch")
        if record.canonical_instrument_id not in instrument_ids:
            raise InstrumentMasterSnapshotPersistenceError("resolver references unknown canonical instrument_id")
    for record in identities:
        if record.as_of_date != as_of_date:
            raise InstrumentMasterSnapshotPersistenceError("identity as_of_date mismatch")
        if record.provider != provider_id:
            raise InstrumentMasterSnapshotPersistenceError("identity provider mismatch")
        if record.canonical_instrument_id is not None and record.canonical_instrument_id not in instrument_ids:
            raise InstrumentMasterSnapshotPersistenceError("identity references unknown canonical instrument_id")


def _validate_existing_partition(path: Path, *, expected_schema: pa.Schema, expected_fingerprint: str, expected_count: int, table_to_rows: Any) -> None:
    if path.is_symlink():
        raise InstrumentMasterSnapshotCorruptionError("partition path is a symlink")
    if not (path / MANIFEST_FILE_NAME).exists() or not (path / PARQUET_FILE_NAME).exists():
        raise InstrumentMasterSnapshotCorruptionError("existing partition is incomplete")
    _validate_parquet(path / PARQUET_FILE_NAME, expected_schema=expected_schema, expected_fingerprint=expected_fingerprint, expected_count=expected_count, table_to_rows=table_to_rows)


def _validate_parquet(path: Path, *, expected_schema: pa.Schema, expected_fingerprint: str, expected_count: int, table_to_rows: Any) -> None:
    try:
        table = pq.ParquetFile(path).read()
    except Exception as exc:
        raise InstrumentMasterSnapshotCorruptionError("parquet file cannot be read") from exc
    if not table.schema.equals(expected_schema, check_metadata=False):
        raise InstrumentMasterSnapshotCorruptionError("parquet schema does not match expected snapshot schema")
    if table.num_rows != expected_count:
        raise InstrumentMasterSnapshotCorruptionError("parquet row count mismatch")
    if records_fingerprint(table_to_rows(table)) != expected_fingerprint:
        raise InstrumentMasterSnapshotCorruptionError("parquet content fingerprint mismatch")


def _dataset_manifest(*, dataset_name: str, schema_version: str, as_of_date: date, provider_id: str, record_count: int, content_sha256: str, created_at: datetime, quality_summary: dict[str, object]) -> dict[str, object]:
    return {
        "manifest_version": "1.0",
        "dataset_name": dataset_name,
        "schema_version": schema_version,
        "as_of_date": as_of_date.isoformat(),
        "provider_id": provider_id,
        "record_count": record_count,
        "content_sha256": content_sha256,
        "parquet_file": PARQUET_FILE_NAME,
        "created_at": created_at.astimezone(UTC).isoformat(),
        "quality_summary": quality_summary,
        "completion_status": COMPLETION_STATUS,
    }


def _snapshot_manifest(*, as_of_date: date, provider_id: str, instrument_partition_path: Path, identity_partition_path: Path, resolver_partition_path: Path, instrument_count: int, identity_count: int, resolver_count: int, instrument_sha: str, identity_sha: str, resolver_sha: str, snapshot_sha: str, created_at: datetime, quality_summary: dict[str, object]) -> dict[str, object]:
    return {
        "manifest_version": "1.0",
        "dataset_name": "instrument-master-logical-snapshot",
        "schema_version": SCHEMA_VERSION,
        "as_of_date": as_of_date.isoformat(),
        "provider_id": provider_id,
        "instrument_partition_path": str(instrument_partition_path),
        "identity_partition_path": str(identity_partition_path),
        "resolver_partition_path": str(resolver_partition_path),
        "instrument_count": instrument_count,
        "identity_count": identity_count,
        "resolver_count": resolver_count,
        "instrument_content_sha256": instrument_sha,
        "identity_content_sha256": identity_sha,
        "resolver_content_sha256": resolver_sha,
        "snapshot_content_sha256": snapshot_sha,
        "created_at": created_at.astimezone(UTC).isoformat(),
        "quality_summary": quality_summary,
        "completion_status": COMPLETION_STATUS,
    }


def _prepare_root(root: Path) -> Path:
    if root.exists() and root.is_symlink():
        raise InstrumentMasterSnapshotPersistenceError("root path must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    resolved = root.resolve()
    if resolved.is_symlink():
        raise InstrumentMasterSnapshotPersistenceError("resolved root path must not be a symlink")
    return resolved


def _instrument_partition_path(root: Path, as_of_date: date) -> Path:
    return _contained_path(root, root / "market-data" / "instrument-master" / f"schema_version={SCHEMA_VERSION_PARTITION}" / f"as_of_date={as_of_date.isoformat()}")


def _identity_partition_path(root: Path, provider_id: str, as_of_date: date) -> Path:
    return _contained_path(root, root / "market-data" / "provider-instrument-identity" / f"schema_version={SCHEMA_VERSION_PARTITION}" / f"provider={provider_id}" / f"as_of_date={as_of_date.isoformat()}")


def _resolver_partition_path(root: Path, provider_id: str, as_of_date: date) -> Path:
    return _contained_path(root, root / "market-data" / "provider-ticker-resolver" / f"schema_version={SCHEMA_VERSION_PARTITION}" / f"provider={provider_id}" / f"as_of_date={as_of_date.isoformat()}")

def _snapshot_manifest_dir(root: Path, as_of_date: date) -> Path:
    return _contained_path(root, root / "market-data" / "snapshots" / "instrument-master" / f"as_of_date={as_of_date.isoformat()}")


def _contained_path(root: Path, path: Path) -> Path:
    parent = path.parent.resolve(strict=False)
    if root not in (parent, *parent.parents):
        raise InstrumentMasterSnapshotPersistenceError("path escapes root")
    if path.exists() and path.is_symlink():
        raise InstrumentMasterSnapshotPersistenceError("target path must not be a symlink")
    return path


def _normalize_provider_id(provider_id: str) -> str:
    if not isinstance(provider_id, str):
        raise InstrumentMasterSnapshotPersistenceError("provider_id must be a string")
    normalized = provider_id.strip()
    if not normalized:
        raise InstrumentMasterSnapshotPersistenceError("provider_id must not be empty")
    return normalized


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _fsync_file(tmp_path)
    tmp_path.replace(path)


def _read_json(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise InstrumentMasterSnapshotCorruptionError("manifest cannot be read") from exc
    if not isinstance(data, dict):
        raise InstrumentMasterSnapshotCorruptionError("manifest must be an object")
    return data


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

