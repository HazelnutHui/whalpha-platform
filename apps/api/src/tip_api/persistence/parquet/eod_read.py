"""Read canonical EOD Price Bar partitions from Parquet."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1 import InstrumentType, QualityStatus
from tip_api.persistence.eod_read import EodDatasetUnavailableError, EodSessionNotFoundError
from tip_api.persistence.parquet.eod_bars import EOD_PRICE_BAR_ARROW_SCHEMA, SCHEMA_VERSION, SCHEMA_VERSION_PARTITION
from tip_api.persistence.parquet.eod_bars import _table_to_fingerprint_rows as eod_table_to_rows
from tip_api.persistence.parquet.instrument_master_snapshot import (
    COMPLETION_STATUS,
    INSTRUMENT_MASTER_ARROW_SCHEMA,
    PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA,
    SCHEMA_VERSION_PARTITION as INSTRUMENT_SCHEMA_VERSION_PARTITION,
    _instrument_table_to_rows,
    _resolver_table_to_rows,
    records_fingerprint,
)
from tip_api.persistence.parquet.manifest import MANIFEST_FILE_NAME, PARQUET_FILE_NAME, table_rows_fingerprint
from tip_api.read_models.eod import EodMarketBarReadModel, EodSessionDescriptor


@dataclass(frozen=True, slots=True)
class CanonicalEodReadRepository:
    """Read completed canonical EOD sessions without exposing storage details."""

    root: Path

    def list_sessions(self) -> tuple[EodSessionDescriptor, ...]:
        root = self._validated_root()
        base = root / "market-data" / "eod-price-bars" / f"schema_version={SCHEMA_VERSION_PARTITION}"
        if not base.exists():
            return ()
        if base.is_symlink() or not base.is_dir():
            raise EodDatasetUnavailableError("EOD session directory is unavailable")
        sessions: list[EodSessionDescriptor] = []
        for partition in sorted(base.glob("session_date=*")):
            if partition.is_symlink() or not partition.is_dir():
                raise EodDatasetUnavailableError("EOD session partition is unavailable")
            try:
                session_date = date.fromisoformat(partition.name.removeprefix("session_date="))
            except ValueError as exc:
                raise EodDatasetUnavailableError("EOD session partition name is invalid") from exc
            if not (partition / MANIFEST_FILE_NAME).exists():
                continue
            sessions.append(self._descriptor_for_session(root, session_date=session_date))
        return tuple(sorted(sessions, key=lambda item: item.session_date))

    def read_bars(self, session_date: date) -> tuple[EodMarketBarReadModel, ...]:
        root = self._validated_root()
        manifest, table = self._read_valid_eod_partition(root, session_date=session_date)
        identity_as_of_date, provider_id = self._identity_reference(manifest)
        instruments = self._read_instruments(root, as_of_date=identity_as_of_date)
        resolver = self._read_resolver(root, provider_id=provider_id, as_of_date=identity_as_of_date)
        rows = table.to_pylist()
        seen_keys: set[tuple[str, str, str, int]] = set()
        bars: list[EodMarketBarReadModel] = []
        for row in rows:
            instrument_id = UUID(row["instrument_id"])
            key = (str(instrument_id), row["session_date"].isoformat(), row["source"], row["revision"])
            if key in seen_keys:
                raise EodDatasetUnavailableError("duplicate EOD business key")
            seen_keys.add(key)
            instrument = instruments.get(instrument_id)
            if instrument is None:
                raise EodDatasetUnavailableError("EOD bar references missing instrument")
            ticker = resolver.get(instrument_id)
            if ticker is None:
                raise EodDatasetUnavailableError("EOD bar instrument is missing from resolver")
            bars.append(
                EodMarketBarReadModel(
                    instrument_id=instrument_id,
                    ticker=ticker,
                    name=str(instrument["name"]),
                    instrument_type=InstrumentType(str(instrument["instrument_type"])),
                    session_date=row["session_date"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"],
                    vwap=row["vwap"],
                    trade_count=row["trade_count"],
                    currency=str(row["currency"]),
                    source=str(row["source"]),
                    quality_status=QualityStatus(str(row["quality_status"])),
                    quality_flags=tuple(row["quality_flags"] or ()),
                )
            )
        return tuple(sorted(bars, key=lambda item: (item.ticker, str(item.instrument_id))))

    def _descriptor_for_session(self, root: Path, *, session_date: date) -> EodSessionDescriptor:
        manifest, _ = self._read_valid_eod_partition(root, session_date=session_date)
        identity_as_of_date, _ = self._identity_reference(manifest)
        created_at = _parse_utc_datetime(manifest.get("created_at"), "manifest created_at")
        quality_summary = manifest.get("quality_summary")
        warnings = []
        if isinstance(quality_summary, dict):
            raw_warnings = quality_summary.get("quality_warnings")
            if isinstance(raw_warnings, list):
                warnings = raw_warnings
        return EodSessionDescriptor(
            schema_version=str(manifest.get("schema_version")),
            session_date=session_date,
            record_count=_required_int(manifest.get("record_count"), "record_count"),
            completion_status=str(manifest.get("completion_status")),
            identity_as_of_date=identity_as_of_date,
            available_at=created_at,
            quality_warning_count=len(warnings),
        )

    def _read_valid_eod_partition(self, root: Path, *, session_date: date) -> tuple[dict[str, Any], pa.Table]:
        partition = root / "market-data" / "eod-price-bars" / f"schema_version={SCHEMA_VERSION_PARTITION}" / f"session_date={session_date.isoformat()}"
        if partition.is_symlink():
            raise EodDatasetUnavailableError("EOD session partition is unavailable")
        if not partition.exists():
            raise EodSessionNotFoundError("EOD session is not available")
        manifest_path = partition / MANIFEST_FILE_NAME
        parquet_path = partition / PARQUET_FILE_NAME
        if manifest_path.is_symlink() or parquet_path.is_symlink():
            raise EodDatasetUnavailableError("EOD session files are unavailable")
        if not manifest_path.is_file() or not parquet_path.is_file():
            raise EodDatasetUnavailableError("EOD session partition is incomplete")
        manifest = _read_json(manifest_path)
        expected = {
            "dataset_name": "eod-price-bars",
            "schema_version": SCHEMA_VERSION,
            "session_date": session_date.isoformat(),
            "completion_status": COMPLETION_STATUS,
            "parquet_file": PARQUET_FILE_NAME,
        }
        for key, value in expected.items():
            if manifest.get(key) != value:
                raise EodDatasetUnavailableError("EOD session manifest is inconsistent")
        table = _read_table(parquet_path)
        if not table.schema.equals(EOD_PRICE_BAR_ARROW_SCHEMA, check_metadata=False):
            raise EodDatasetUnavailableError("EOD session schema is unavailable")
        if table.num_rows != _required_int(manifest.get("record_count"), "record_count"):
            raise EodDatasetUnavailableError("EOD session row count mismatch")
        rows = eod_table_to_rows(table)
        if {row["session_date"] for row in rows} != {session_date.isoformat()}:
            raise EodDatasetUnavailableError("EOD session_date mismatch")
        if table_rows_fingerprint(rows) != manifest.get("content_sha256"):
            raise EodDatasetUnavailableError("EOD session fingerprint mismatch")
        self._verify_identity_snapshot(root, manifest)
        return manifest, table

    def _verify_identity_snapshot(self, root: Path, manifest: dict[str, Any]) -> None:
        identity = manifest.get("identity_snapshot")
        if not isinstance(identity, dict):
            raise EodDatasetUnavailableError("EOD session identity reference is missing")
        identity_as_of_date, provider_id = self._identity_reference(manifest)
        snapshot_path = root / "market-data" / "snapshots" / "instrument-master" / f"as_of_date={identity_as_of_date.isoformat()}" / MANIFEST_FILE_NAME
        if snapshot_path.is_symlink() or not snapshot_path.is_file():
            raise EodDatasetUnavailableError("identity snapshot reference is unavailable")
        snapshot_manifest = _read_json(snapshot_path)
        if snapshot_manifest.get("completion_status") != COMPLETION_STATUS:
            raise EodDatasetUnavailableError("identity snapshot is not completed")
        if snapshot_manifest.get("provider_id") != provider_id or snapshot_manifest.get("as_of_date") != identity_as_of_date.isoformat():
            raise EodDatasetUnavailableError("identity snapshot reference mismatch")
        if snapshot_manifest.get("snapshot_content_sha256") != identity.get("snapshot_content_sha256"):
            raise EodDatasetUnavailableError("identity snapshot fingerprint mismatch")

    def _read_instruments(self, root: Path, *, as_of_date: date) -> dict[UUID, dict[str, Any]]:
        partition = root / "market-data" / "instrument-master" / f"schema_version={INSTRUMENT_SCHEMA_VERSION_PARTITION}" / f"as_of_date={as_of_date.isoformat()}"
        path = partition / PARQUET_FILE_NAME
        table = _read_schema_checked_table(path, INSTRUMENT_MASTER_ARROW_SCHEMA, "instrument snapshot")
        snapshot_manifest = _read_json(root / "market-data" / "snapshots" / "instrument-master" / f"as_of_date={as_of_date.isoformat()}" / MANIFEST_FILE_NAME)
        dataset_manifest = _read_json(partition / MANIFEST_FILE_NAME)
        expected_count = _required_int(snapshot_manifest.get("instrument_count"), "instrument_count")
        expected_fingerprint = snapshot_manifest.get("instrument_content_sha256")
        _verify_dataset_manifest(
            dataset_manifest,
            dataset_name="instrument-master",
            as_of_date=as_of_date,
            provider_id=str(snapshot_manifest.get("provider_id")),
            expected_count=expected_count,
            expected_fingerprint=expected_fingerprint,
        )
        if table.num_rows != expected_count or records_fingerprint(_instrument_table_to_rows(table)) != expected_fingerprint:
            raise EodDatasetUnavailableError("instrument snapshot validation failed")
        instruments: dict[UUID, dict[str, Any]] = {}
        for row in table.to_pylist():
            instrument_id = UUID(row["instrument_id"])
            if instrument_id in instruments:
                raise EodDatasetUnavailableError("duplicate instrument_id in snapshot")
            instruments[instrument_id] = row
        return instruments

    def _read_resolver(self, root: Path, *, provider_id: str, as_of_date: date) -> dict[UUID, str]:
        partition = root / "market-data" / "provider-ticker-resolver" / f"schema_version={INSTRUMENT_SCHEMA_VERSION_PARTITION}" / f"provider={provider_id}" / f"as_of_date={as_of_date.isoformat()}"
        path = partition / PARQUET_FILE_NAME
        table = _read_schema_checked_table(path, PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA, "ticker resolver")
        snapshot_manifest = _read_json(root / "market-data" / "snapshots" / "instrument-master" / f"as_of_date={as_of_date.isoformat()}" / MANIFEST_FILE_NAME)
        dataset_manifest = _read_json(partition / MANIFEST_FILE_NAME)
        expected_count = _required_int(snapshot_manifest.get("resolver_count"), "resolver_count")
        expected_fingerprint = snapshot_manifest.get("resolver_content_sha256")
        _verify_dataset_manifest(
            dataset_manifest,
            dataset_name="provider-ticker-resolver",
            as_of_date=as_of_date,
            provider_id=provider_id,
            expected_count=expected_count,
            expected_fingerprint=expected_fingerprint,
        )
        if table.num_rows != expected_count or records_fingerprint(_resolver_table_to_rows(table)) != expected_fingerprint:
            raise EodDatasetUnavailableError("ticker resolver validation failed")
        by_instrument: dict[UUID, str] = {}
        seen_tickers: set[str] = set()
        for row in table.to_pylist():
            if row["provider"] != provider_id or row["as_of_date"] != as_of_date:
                raise EodDatasetUnavailableError("ticker resolver row mismatch")
            ticker = str(row["provider_ticker"])
            if ticker in seen_tickers:
                raise EodDatasetUnavailableError("resolver ticker is not unique")
            seen_tickers.add(ticker)
            instrument_id = UUID(row["canonical_instrument_id"])
            by_instrument.setdefault(instrument_id, ticker)
        return by_instrument

    def _identity_reference(self, manifest: dict[str, Any]) -> tuple[date, str]:
        identity = manifest.get("identity_snapshot")
        if not isinstance(identity, dict):
            raise EodDatasetUnavailableError("EOD session identity reference is missing")
        as_of_raw = identity.get("as_of_date")
        provider_id = identity.get("provider_id")
        if not isinstance(as_of_raw, str) or not isinstance(provider_id, str) or not provider_id.strip():
            raise EodDatasetUnavailableError("EOD session identity reference is invalid")
        try:
            return date.fromisoformat(as_of_raw), provider_id.strip()
        except ValueError as exc:
            raise EodDatasetUnavailableError("EOD session identity date is invalid") from exc

    def _validated_root(self) -> Path:
        if not self.root.is_absolute():
            raise EodDatasetUnavailableError("market data root must be absolute")
        if self.root.is_symlink():
            raise EodDatasetUnavailableError("market data root is unavailable")
        if not self.root.exists() or not self.root.is_dir():
            raise EodDatasetUnavailableError("market data root is unavailable")
        resolved = self.root.resolve()
        if resolved.is_symlink():
            raise EodDatasetUnavailableError("market data root is unavailable")
        return resolved


def _verify_dataset_manifest(
    manifest: dict[str, Any],
    *,
    dataset_name: str,
    as_of_date: date,
    provider_id: str,
    expected_count: int,
    expected_fingerprint: object,
) -> None:
    expected = {
        "dataset_name": dataset_name,
        "schema_version": SCHEMA_VERSION,
        "as_of_date": as_of_date.isoformat(),
        "provider_id": provider_id,
        "record_count": expected_count,
        "content_sha256": expected_fingerprint,
        "parquet_file": PARQUET_FILE_NAME,
        "completion_status": COMPLETION_STATUS,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise EodDatasetUnavailableError(f"{dataset_name} manifest is inconsistent")


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EodDatasetUnavailableError("manifest is unavailable")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise EodDatasetUnavailableError("manifest cannot be read") from exc
    if not isinstance(data, dict):
        raise EodDatasetUnavailableError("manifest is invalid")
    return data


def _read_table(path: Path) -> pa.Table:
    if path.is_symlink() or not path.is_file():
        raise EodDatasetUnavailableError("parquet file is unavailable")
    try:
        return pq.ParquetFile(path).read()
    except Exception as exc:
        raise EodDatasetUnavailableError("parquet file cannot be read") from exc


def _read_schema_checked_table(path: Path, schema: pa.Schema, label: str) -> pa.Table:
    table = _read_table(path)
    if not table.schema.equals(schema, check_metadata=False):
        raise EodDatasetUnavailableError(f"{label} schema mismatch")
    return table


def _required_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise EodDatasetUnavailableError(f"{field_name} is invalid")
    return value


def _parse_utc_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise EodDatasetUnavailableError(f"{field_name} is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EodDatasetUnavailableError(f"{field_name} is invalid") from exc
    if parsed.tzinfo is None:
        raise EodDatasetUnavailableError(f"{field_name} is invalid")
    return parsed.astimezone(UTC)
