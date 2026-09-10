"""Deterministic Parquet persistence for historical research foundation rows."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, TypeAlias, TypeVar
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ValidationError

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    AdjustmentLedgerEntryV1,
    CorporateActionSourceObservationV1,
    HistoricalDatasetFamily,
    InstrumentLifecycleObservationV1,
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipDispositionSummaryV1,
    UniverseMembershipPartitionManifestV1,
)
from tip_api.persistence.historical_research import (
    HistoricalResearchConflictError,
    HistoricalResearchCorruptionError,
    HistoricalResearchPartitionWriteResult,
    HistoricalResearchPersistenceError,
)
from tip_api.persistence.parquet.manifest import decimal_to_string

SCHEMA_VERSION = "1.0"
CORPORATE_ACTION_OBSERVATION_SCHEMA_VERSION = "1.1"
SCHEMA_VERSION_PARTITION = "1"
MANIFEST_VERSION = "1.0"
UNIVERSE_MEMBERSHIP_MANIFEST_VERSION = "1.1"
PARQUET_FILE_NAME = "part-00000.parquet"
MANIFEST_FILE_NAME = "manifest.json"
COMPLETION_STATUS = "completed"
DECIMAL_PRECISION = 38
DECIMAL_SCALE = 18

HistoricalRecord: TypeAlias = (
    CorporateActionSourceObservationV1
    | InstrumentLifecycleObservationV1
    | UniverseMembershipDecisionV1
    | AdjustmentLedgerEntryV1
)
RecordT = TypeVar("RecordT", bound=HistoricalRecord)


def read_universe_membership_partition_content(
    partition_path: Path,
) -> tuple[UniverseMembershipDecisionV1, ...]:
    """Formally validate Membership bytes when namespace is governed elsewhere."""

    spec = _SPECS[HistoricalDatasetFamily.UNIVERSE_MEMBERSHIP]
    records, _ = _read_partition(partition_path, spec)
    if any(not isinstance(record, UniverseMembershipDecisionV1) for record in records):
        raise HistoricalResearchCorruptionError(
            "partition returned an unexpected Membership record type"
        )
    return records  # type: ignore[return-value]

CORPORATE_ACTION_OBSERVATION_ARROW_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("provider", pa.string(), nullable=False),
        pa.field("source_action_id", pa.string(), nullable=False),
        pa.field("source_revision", pa.int32(), nullable=False),
        pa.field("supersedes_source_action_id", pa.string(), nullable=True),
        pa.field("record_status", pa.string(), nullable=False),
        pa.field("action_type", pa.string(), nullable=False),
        pa.field("provider_ticker", pa.string(), nullable=False),
        pa.field("instrument_resolution_status", pa.string(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=True),
        pa.field("announcement_date", pa.date32(), nullable=True),
        pa.field("ex_date", pa.date32(), nullable=True),
        pa.field("record_date", pa.date32(), nullable=True),
        pa.field("pay_date", pa.date32(), nullable=True),
        pa.field("effective_date", pa.date32(), nullable=False),
        pa.field("split_ratio_from", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=True),
        pa.field("split_ratio_to", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=True),
        pa.field("cash_amount", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=True),
        pa.field("currency", pa.string(), nullable=True),
        pa.field(
            "provider_historical_adjustment_factor",
            pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE),
            nullable=True,
        ),
        pa.field("provider_split_adjusted_cash_amount", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=True),
        pa.field("distribution_type", pa.string(), nullable=True),
        pa.field("frequency", pa.int32(), nullable=True),
        pa.field("new_ticker", pa.string(), nullable=True),
        pa.field("successor_instrument_id", pa.string(), nullable=True),
        pa.field("related_instrument_id", pa.string(), nullable=True),
        pa.field("termination_reason", pa.string(), nullable=True),
        pa.field("knowledge_time_status", pa.string(), nullable=False),
        pa.field("source_available_at", pa.timestamp("us", tz="UTC"), nullable=True),
        pa.field("first_observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
        pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
    ]
)

INSTRUMENT_LIFECYCLE_ARROW_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("as_of_date", pa.date32(), nullable=False),
        pa.field("valid_from", pa.date32(), nullable=False),
        pa.field("valid_to", pa.date32(), nullable=True),
        pa.field("lifecycle_status", pa.string(), nullable=False),
        pa.field("ticker", pa.string(), nullable=False),
        pa.field("primary_exchange", pa.string(), nullable=True),
        pa.field("first_tradable_date", pa.date32(), nullable=True),
        pa.field("last_tradable_date", pa.date32(), nullable=True),
        pa.field("predecessor_instrument_id", pa.string(), nullable=True),
        pa.field("successor_instrument_id", pa.string(), nullable=True),
        pa.field("lineage_evidence_status", pa.string(), nullable=False),
        pa.field("terminal_cash_amount", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=True),
        pa.field("terminal_currency", pa.string(), nullable=True),
        pa.field("source", pa.string(), nullable=False),
        pa.field("source_record_id", pa.string(), nullable=False),
        pa.field("source_revision", pa.int32(), nullable=False),
        pa.field("knowledge_time_status", pa.string(), nullable=False),
        pa.field("source_available_at", pa.timestamp("us", tz="UTC"), nullable=True),
        pa.field("first_observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
        pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
    ]
)

UNIVERSE_MEMBERSHIP_ARROW_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("universe_id", pa.string(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("session_date", pa.date32(), nullable=False),
        pa.field("methodology_version", pa.string(), nullable=False),
        pa.field("origin", pa.string(), nullable=False),
        pa.field("disposition", pa.string(), nullable=False),
        pa.field("is_member", pa.bool_(), nullable=True),
        pa.field("reason_codes", pa.list_(pa.string()), nullable=False),
        pa.field("evaluated_base_fingerprint", pa.string(), nullable=False),
        pa.field("source_fingerprints", pa.list_(pa.string()), nullable=False),
        pa.field("source_data_cutoff", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("evaluated_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
    ]
)

ADJUSTMENT_LEDGER_ARROW_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("source_session", pa.date32(), nullable=False),
        pa.field("basis_session", pa.date32(), nullable=False),
        pa.field("factor_direction", pa.string(), nullable=False),
        pa.field("split_price_multiplier_to_basis", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=True),
        pa.field("split_volume_multiplier_to_basis", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=True),
        pa.field("split_adjustment_status", pa.string(), nullable=False),
        pa.field("total_return_multiplier_to_basis", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=True),
        pa.field("total_return_adjustment_status", pa.string(), nullable=False),
        pa.field("source_action_set_fingerprint", pa.string(), nullable=False),
        pa.field("calculation_methodology_version", pa.string(), nullable=False),
        pa.field("source_data_cutoff", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("calculated_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("revision", pa.int32(), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
        pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
    ]
)


@dataclass(frozen=True)
class _FamilySpec:
    family: HistoricalDatasetFamily
    model: type[BaseModel]
    schema: pa.Schema
    schema_version: str
    directory_name: str
    partition_keys: tuple[str, ...]
    sort_key: Callable[[Any], tuple[Any, ...]]
    allow_empty: bool = False


_SPECS = {
    HistoricalDatasetFamily.CORPORATE_ACTION_SOURCE_OBSERVATION: _FamilySpec(
        family=HistoricalDatasetFamily.CORPORATE_ACTION_SOURCE_OBSERVATION,
        model=CorporateActionSourceObservationV1,
        schema=CORPORATE_ACTION_OBSERVATION_ARROW_SCHEMA,
        schema_version=CORPORATE_ACTION_OBSERVATION_SCHEMA_VERSION,
        directory_name="provider-corporate-action-observation",
        partition_keys=("provider_id", "event_year"),
        sort_key=lambda row: (row.provider, row.source_action_id, row.source_revision),
        allow_empty=True,
    ),
    HistoricalDatasetFamily.INSTRUMENT_LIFECYCLE: _FamilySpec(
        family=HistoricalDatasetFamily.INSTRUMENT_LIFECYCLE,
        model=InstrumentLifecycleObservationV1,
        schema=INSTRUMENT_LIFECYCLE_ARROW_SCHEMA,
        schema_version=SCHEMA_VERSION,
        directory_name="instrument-lifecycle",
        partition_keys=("as_of_date",),
        sort_key=lambda row: (
            str(row.instrument_id),
            row.as_of_date,
            row.source,
            row.source_record_id,
            row.source_revision,
        ),
    ),
    HistoricalDatasetFamily.UNIVERSE_MEMBERSHIP: _FamilySpec(
        family=HistoricalDatasetFamily.UNIVERSE_MEMBERSHIP,
        model=UniverseMembershipDecisionV1,
        schema=UNIVERSE_MEMBERSHIP_ARROW_SCHEMA,
        schema_version=SCHEMA_VERSION,
        directory_name="universe-membership",
        partition_keys=("methodology_version", "session_date"),
        sort_key=lambda row: (
            row.universe_id,
            str(row.instrument_id),
            row.session_date,
            row.methodology_version,
        ),
    ),
    HistoricalDatasetFamily.ADJUSTMENT_LEDGER: _FamilySpec(
        family=HistoricalDatasetFamily.ADJUSTMENT_LEDGER,
        model=AdjustmentLedgerEntryV1,
        schema=ADJUSTMENT_LEDGER_ARROW_SCHEMA,
        schema_version=SCHEMA_VERSION,
        directory_name="adjustment-ledger",
        partition_keys=("methodology_version", "basis_session"),
        sort_key=lambda row: (
            str(row.instrument_id),
            row.source_session,
            row.basis_session,
            row.calculation_methodology_version,
            row.revision,
        ),
    ),
}


@dataclass(frozen=True)
class ParquetHistoricalResearchRepository:
    """Publish and formally reread immutable historical research partitions."""

    root: Path
    created_at: datetime | None = None

    def publish_corporate_action_observations(
        self,
        records: tuple[CorporateActionSourceObservationV1, ...],
        *,
        provider_id: str,
        event_year: int,
    ) -> HistoricalResearchPartitionWriteResult:
        provider = _safe_segment(provider_id, "provider_id")
        if any(record.provider != provider for record in records):
            raise HistoricalResearchPersistenceError("corporate-action provider partition mismatch")
        if any(record.effective_date.year != event_year for record in records):
            raise HistoricalResearchPersistenceError("corporate-action event-year partition mismatch")
        return self._publish(
            family=HistoricalDatasetFamily.CORPORATE_ACTION_SOURCE_OBSERVATION,
            records=records,
            partition_values={"provider_id": provider, "event_year": str(event_year)},
        )

    def publish_instrument_lifecycle(
        self,
        records: tuple[InstrumentLifecycleObservationV1, ...],
        *,
        as_of_date: date,
    ) -> HistoricalResearchPartitionWriteResult:
        if any(record.as_of_date != as_of_date for record in records):
            raise HistoricalResearchPersistenceError("lifecycle as-of partition mismatch")
        return self._publish(
            family=HistoricalDatasetFamily.INSTRUMENT_LIFECYCLE,
            records=records,
            partition_values={"as_of_date": as_of_date.isoformat()},
        )

    def publish_universe_membership(
        self,
        records: tuple[UniverseMembershipDecisionV1, ...],
        *,
        methodology_version: str,
        session_date: date,
    ) -> HistoricalResearchPartitionWriteResult:
        methodology = _safe_segment(methodology_version, "methodology_version")
        if any(
            record.methodology_version != methodology or record.session_date != session_date
            for record in records
        ):
            raise HistoricalResearchPersistenceError("membership partition mismatch")
        return self._publish(
            family=HistoricalDatasetFamily.UNIVERSE_MEMBERSHIP,
            records=records,
            partition_values={
                "methodology_version": methodology,
                "session_date": session_date.isoformat(),
            },
        )

    def publish_adjustment_ledger(
        self,
        records: tuple[AdjustmentLedgerEntryV1, ...],
        *,
        methodology_version: str,
        basis_session: date,
    ) -> HistoricalResearchPartitionWriteResult:
        methodology = _safe_segment(methodology_version, "methodology_version")
        if any(
            record.calculation_methodology_version != methodology
            or record.basis_session != basis_session
            for record in records
        ):
            raise HistoricalResearchPersistenceError("adjustment partition mismatch")
        return self._publish(
            family=HistoricalDatasetFamily.ADJUSTMENT_LEDGER,
            records=records,
            partition_values={
                "methodology_version": methodology,
                "basis_session": basis_session.isoformat(),
            },
        )

    def read_corporate_action_observations(
        self, partition_path: Path
    ) -> tuple[CorporateActionSourceObservationV1, ...]:
        return self._read_typed(
            HistoricalDatasetFamily.CORPORATE_ACTION_SOURCE_OBSERVATION,
            partition_path,
            CorporateActionSourceObservationV1,
        )

    def read_instrument_lifecycle(
        self, partition_path: Path
    ) -> tuple[InstrumentLifecycleObservationV1, ...]:
        return self._read_typed(
            HistoricalDatasetFamily.INSTRUMENT_LIFECYCLE,
            partition_path,
            InstrumentLifecycleObservationV1,
        )

    def read_universe_membership(
        self, partition_path: Path
    ) -> tuple[UniverseMembershipDecisionV1, ...]:
        return self._read_typed(
            HistoricalDatasetFamily.UNIVERSE_MEMBERSHIP,
            partition_path,
            UniverseMembershipDecisionV1,
        )

    def read_adjustment_ledger(
        self, partition_path: Path
    ) -> tuple[AdjustmentLedgerEntryV1, ...]:
        return self._read_typed(
            HistoricalDatasetFamily.ADJUSTMENT_LEDGER,
            partition_path,
            AdjustmentLedgerEntryV1,
        )

    def _publish(
        self,
        *,
        family: HistoricalDatasetFamily,
        records: tuple[HistoricalRecord, ...],
        partition_values: Mapping[str, str],
    ) -> HistoricalResearchPartitionWriteResult:
        spec = _SPECS[family]
        if not records and not spec.allow_empty:
            raise HistoricalResearchPersistenceError("historical partition must not be empty")
        if any(not isinstance(record, spec.model) for record in records):
            raise HistoricalResearchPersistenceError("record type does not match dataset family")
        ordered = _ordered_records(records, spec)
        _reject_duplicate_business_keys(ordered, spec)
        logical_fingerprint = _records_fingerprint(ordered, spec)
        membership_manifest = (
            _membership_manifest_fields(ordered)
            if family is HistoricalDatasetFamily.UNIVERSE_MEMBERSHIP
            else {}
        )
        root = _prepare_root(self.root)
        partition_path = _partition_path(root, spec, partition_values)

        if partition_path.exists() or partition_path.is_symlink():
            _reject_existing_symlinks(root, partition_path)
            if partition_path.is_symlink():
                raise HistoricalResearchCorruptionError("partition path is a symlink")
            existing, manifest = _read_partition(partition_path, spec)
            if manifest["partition"] != dict(partition_values):
                raise HistoricalResearchCorruptionError("partition manifest boundary differs")
            existing_fingerprint = _records_fingerprint(existing, spec)
            if existing_fingerprint != logical_fingerprint:
                raise HistoricalResearchConflictError("immutable partition content differs")
            return _write_result(
                family=family,
                partition_path=partition_path,
                manifest=manifest,
                written_record_count=0,
                status="already_present",
            )

        _reject_existing_symlinks(root, partition_path.parent)
        partition_path.parent.mkdir(parents=True, exist_ok=True)
        staging_path = partition_path.parent / f".{partition_path.name}.staging.{os.getpid()}"
        if staging_path.exists() or staging_path.is_symlink():
            raise HistoricalResearchConflictError("staging path already exists")
        try:
            staging_path.mkdir()
            parquet_path = staging_path / PARQUET_FILE_NAME
            table = _records_to_table(ordered, spec)
            pq.write_table(table, parquet_path, compression="zstd", use_dictionary=False)
            _fsync_file(parquet_path)
            physical_sha256 = _file_sha256(parquet_path)
            created_at = normalize_utc_datetime(self.created_at or datetime.now(UTC))
            manifest = {
                "manifest_version": (
                    UNIVERSE_MEMBERSHIP_MANIFEST_VERSION
                    if family is HistoricalDatasetFamily.UNIVERSE_MEMBERSHIP
                    else MANIFEST_VERSION
                ),
                "family": family.value,
                "schema_version": spec.schema_version,
                "partition": dict(partition_values),
                "record_count": len(ordered),
                "logical_fingerprint": logical_fingerprint,
                "physical_sha256": physical_sha256,
                "parquet_file": PARQUET_FILE_NAME,
                "created_at": created_at.isoformat(),
                "completion_status": COMPLETION_STATUS,
                **membership_manifest,
            }
            _write_json_atomic(staging_path / MANIFEST_FILE_NAME, manifest)
            _read_partition(staging_path, spec)
            _fsync_directory(staging_path)
            staging_path.replace(partition_path)
            _fsync_directory(partition_path.parent)
        except HistoricalResearchPersistenceError:
            if staging_path.exists() and not staging_path.is_symlink():
                shutil.rmtree(staging_path)
            raise
        except Exception as exc:
            if staging_path.exists() and not staging_path.is_symlink():
                shutil.rmtree(staging_path)
            raise HistoricalResearchPersistenceError("historical partition write failed") from exc

        return _write_result(
            family=family,
            partition_path=partition_path,
            manifest=manifest,
            written_record_count=len(ordered),
            status="published",
        )

    def _read_typed(
        self,
        family: HistoricalDatasetFamily,
        partition_path: Path,
        expected_type: type[RecordT],
    ) -> tuple[RecordT, ...]:
        root = _prepare_root(self.root)
        _require_partition_within_root(root, partition_path)
        spec = _SPECS[family]
        records, manifest = _read_partition(partition_path, spec)
        try:
            expected_path = _partition_path(root, spec, manifest["partition"])
        except (HistoricalResearchPersistenceError, KeyError, TypeError) as exc:
            raise HistoricalResearchCorruptionError("partition manifest path is invalid") from exc
        if expected_path != partition_path.absolute():
            raise HistoricalResearchCorruptionError("partition path does not match its manifest")
        if any(not isinstance(record, expected_type) for record in records):
            raise HistoricalResearchCorruptionError("partition returned an unexpected record type")
        return records  # type: ignore[return-value]


def _records_to_table(records: tuple[HistoricalRecord, ...], spec: _FamilySpec) -> pa.Table:
    rows = [_arrow_row(record) for record in records]
    try:
        return pa.Table.from_pylist(rows, schema=spec.schema)
    except (pa.ArrowException, OverflowError, ValueError) as exc:
        raise HistoricalResearchPersistenceError("record cannot be represented by the Arrow schema") from exc


def _arrow_row(record: HistoricalRecord) -> dict[str, Any]:
    row = record.model_dump(mode="python")
    return {key: _arrow_value(value) for key, value in row.items()}


def _arrow_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, tuple):
        return [_arrow_value(item) for item in value]
    return value


def _read_partition(
    partition_path: Path,
    spec: _FamilySpec,
) -> tuple[tuple[HistoricalRecord, ...], dict[str, Any]]:
    if not partition_path.exists() or not partition_path.is_dir() or partition_path.is_symlink():
        raise HistoricalResearchCorruptionError("partition directory is missing or unsafe")
    parquet_path = partition_path / PARQUET_FILE_NAME
    manifest_path = partition_path / MANIFEST_FILE_NAME
    if any(path.is_symlink() or not path.is_file() for path in (parquet_path, manifest_path)):
        raise HistoricalResearchCorruptionError("partition files are missing or unsafe")
    manifest = _read_json(manifest_path)
    required_manifest = {
        "manifest_version": (
            UNIVERSE_MEMBERSHIP_MANIFEST_VERSION
            if spec.family is HistoricalDatasetFamily.UNIVERSE_MEMBERSHIP
            else MANIFEST_VERSION
        ),
        "family": spec.family.value,
        "schema_version": spec.schema_version,
        "parquet_file": PARQUET_FILE_NAME,
        "completion_status": COMPLETION_STATUS,
    }
    if any(manifest.get(key) != value for key, value in required_manifest.items()):
        raise HistoricalResearchCorruptionError("partition manifest contract differs")
    _validate_manifest_shape(manifest)
    if spec.family is HistoricalDatasetFamily.UNIVERSE_MEMBERSHIP:
        try:
            UniverseMembershipPartitionManifestV1.model_validate(manifest)
        except (ValidationError, ValueError, TypeError) as exc:
            raise HistoricalResearchCorruptionError("membership coverage manifest is invalid") from exc
    physical_sha256 = _file_sha256(parquet_path)
    if manifest.get("physical_sha256") != physical_sha256:
        raise HistoricalResearchCorruptionError("Parquet physical hash differs")
    try:
        table = pq.ParquetFile(parquet_path).read()
    except (pa.ArrowException, OSError) as exc:
        raise HistoricalResearchCorruptionError("Parquet file cannot be read") from exc
    if not table.schema.equals(spec.schema, check_metadata=False):
        raise HistoricalResearchCorruptionError("Parquet schema differs")
    if table.num_rows != manifest.get("record_count"):
        raise HistoricalResearchCorruptionError("Parquet row count differs")
    try:
        records = tuple(spec.model.model_validate(row) for row in table.to_pylist())
    except (ValidationError, ValueError, TypeError) as exc:
        raise HistoricalResearchCorruptionError("Parquet row validation failed") from exc
    ordered = _ordered_records(records, spec)
    if records != ordered:
        raise HistoricalResearchCorruptionError("Parquet rows are not deterministically ordered")
    if _records_fingerprint(records, spec) != manifest.get("logical_fingerprint"):
        raise HistoricalResearchCorruptionError("logical fingerprint differs")
    _reject_duplicate_business_keys(records, spec, corruption=True)
    if spec.family is HistoricalDatasetFamily.UNIVERSE_MEMBERSHIP:
        expected_membership = _membership_manifest_fields(records)
        if any(manifest.get(key) != value for key, value in expected_membership.items()):
            raise HistoricalResearchCorruptionError("membership coverage manifest differs from rows")
    return records, manifest


def _membership_manifest_fields(records: tuple[HistoricalRecord, ...]) -> dict[str, Any]:
    membership_records = tuple(
        record for record in records if isinstance(record, UniverseMembershipDecisionV1)
    )
    if len(membership_records) != len(records) or not membership_records:
        raise HistoricalResearchPersistenceError("membership partition must contain membership decisions")
    methodology_versions = {record.methodology_version for record in membership_records}
    session_dates = {record.session_date for record in membership_records}
    origins = {record.origin for record in membership_records}
    base_fingerprints = {record.evaluated_base_fingerprint for record in membership_records}
    source_fingerprint_sets = {record.source_fingerprints for record in membership_records}
    source_cutoffs = {record.source_data_cutoff for record in membership_records}
    evaluated_times = {record.evaluated_at for record in membership_records}
    if any(len(values) != 1 for values in (
        methodology_versions,
        session_dates,
        origins,
        base_fingerprints,
        source_fingerprint_sets,
        source_cutoffs,
        evaluated_times,
    )):
        raise HistoricalResearchPersistenceError("membership partition provenance must be uniform")
    universe_ids = tuple(sorted({record.universe_id for record in membership_records}))
    base_by_universe = {
        universe_id: frozenset(
            record.instrument_id for record in membership_records if record.universe_id == universe_id
        )
        for universe_id in universe_ids
    }
    first_base = base_by_universe[universe_ids[0]]
    if any(ids != first_base for ids in base_by_universe.values()):
        raise HistoricalResearchPersistenceError("each Universe must cover the same evaluated base")
    actual_base_fingerprint = _stable_id_set_fingerprint(first_base)
    declared_base_fingerprint = next(iter(base_fingerprints))
    if actual_base_fingerprint != declared_base_fingerprint:
        raise HistoricalResearchPersistenceError("evaluated-base fingerprint differs from row coverage")
    source_fingerprints = next(iter(source_fingerprint_sets))
    if source_fingerprints != tuple(sorted(set(source_fingerprints))):
        raise HistoricalResearchPersistenceError("membership source fingerprints must be unique and sorted")
    summaries = []
    for universe_id in universe_ids:
        rows = tuple(record for record in membership_records if record.universe_id == universe_id)
        summaries.append(
            UniverseMembershipDispositionSummaryV1(
                universe_id=universe_id,
                included_count=sum(record.disposition is UniverseMembershipDisposition.INCLUDED for record in rows),
                excluded_count=sum(record.disposition is UniverseMembershipDisposition.EXCLUDED for record in rows),
                quarantined_count=sum(record.disposition is UniverseMembershipDisposition.QUARANTINED for record in rows),
            ).model_dump(mode="json")
        )
    return {
        "methodology_version": next(iter(methodology_versions)),
        "session_date": next(iter(session_dates)).isoformat(),
        "origin": next(iter(origins)).value,
        "universe_ids": list(universe_ids),
        "evaluated_base_count": len(first_base),
        "evaluated_base_fingerprint": actual_base_fingerprint,
        "disposition_summaries": summaries,
        "source_fingerprints": list(source_fingerprints),
        "source_data_cutoff": next(iter(source_cutoffs)).isoformat(),
        "evaluated_at": next(iter(evaluated_times)).isoformat(),
    }


def _stable_id_set_fingerprint(instrument_ids: frozenset[UUID]) -> str:
    payload = json.dumps(
        [str(item) for item in sorted(instrument_ids, key=str)],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ordered_records(
    records: tuple[HistoricalRecord, ...],
    spec: _FamilySpec,
) -> tuple[HistoricalRecord, ...]:
    return tuple(sorted(records, key=spec.sort_key))


def _reject_duplicate_business_keys(
    records: tuple[HistoricalRecord, ...],
    spec: _FamilySpec,
    *,
    corruption: bool = False,
) -> None:
    keys = tuple(spec.sort_key(record) for record in records)
    if len(keys) != len(set(keys)):
        error = HistoricalResearchCorruptionError if corruption else HistoricalResearchConflictError
        raise error("historical partition contains duplicate business keys")


def _records_fingerprint(records: tuple[HistoricalRecord, ...], spec: _FamilySpec) -> str:
    payload = json.dumps(
        [_canonical_value(record.model_dump(mode="python")) for record in records],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonical_value(value.model_dump(mode="python"))
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return decimal_to_string(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _partition_path(
    root: Path,
    spec: _FamilySpec,
    partition_values: Mapping[str, str],
) -> Path:
    if set(partition_values) != set(spec.partition_keys):
        raise HistoricalResearchPersistenceError("partition keys do not match the family contract")
    path = root / "market-data" / spec.directory_name / f"schema_version={SCHEMA_VERSION_PARTITION}"
    for key in spec.partition_keys:
        value = partition_values[key]
        path = path / f"{_safe_segment(key, 'partition key')}={_safe_segment(value, key)}"
    return path


def _prepare_root(root: Path) -> Path:
    if root.exists() and (not root.is_dir() or root.is_symlink()):
        raise HistoricalResearchPersistenceError("repository root must be a non-symlink directory")
    root.mkdir(parents=True, exist_ok=True)
    return root.absolute()


def _require_partition_within_root(root: Path, partition_path: Path) -> None:
    absolute_root = root.absolute()
    absolute_partition = partition_path.absolute()
    if absolute_partition == absolute_root or absolute_root not in absolute_partition.parents:
        raise HistoricalResearchPersistenceError("partition path is outside repository root")
    _reject_existing_symlinks(root, partition_path)


def _reject_existing_symlinks(root: Path, path: Path) -> None:
    current = path
    while current != root:
        if current.exists() and current.is_symlink():
            raise HistoricalResearchPersistenceError("partition parent contains a symlink")
        if root not in current.parents:
            raise HistoricalResearchPersistenceError("partition path escaped repository root")
        current = current.parent


def _safe_segment(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise HistoricalResearchPersistenceError(f"{field_name} must be text")
    normalized = value.strip()
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    if not normalized or normalized in {".", ".."} or any(char not in allowed for char in normalized):
        raise HistoricalResearchPersistenceError(f"{field_name} is not a safe path segment")
    return normalized


def _validate_manifest_shape(manifest: Mapping[str, Any]) -> None:
    partition = manifest.get("partition")
    if not isinstance(partition, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in partition.items()
    ):
        raise HistoricalResearchCorruptionError("partition manifest lacks valid partition values")
    record_count = manifest.get("record_count")
    if type(record_count) is not int or record_count < 0:
        raise HistoricalResearchCorruptionError("partition manifest has an invalid record count")
    for field_name in ("logical_fingerprint", "physical_sha256"):
        value = manifest.get(field_name)
        if not isinstance(value, str) or len(value) != 64 or any(
            character not in "0123456789abcdef" for character in value
        ):
            raise HistoricalResearchCorruptionError(
                f"partition manifest has an invalid {field_name}"
            )
    created_at = manifest.get("created_at")
    if not isinstance(created_at, str):
        raise HistoricalResearchCorruptionError("partition manifest lacks created_at")
    try:
        normalize_utc_datetime(datetime.fromisoformat(created_at))
    except (TypeError, ValueError) as exc:
        raise HistoricalResearchCorruptionError(
            "partition manifest created_at must be UTC"
        ) from exc


def _write_result(
    *,
    family: HistoricalDatasetFamily,
    partition_path: Path,
    manifest: Mapping[str, Any],
    written_record_count: int,
    status: str,
) -> HistoricalResearchPartitionWriteResult:
    return HistoricalResearchPartitionWriteResult(
        family=family,
        partition_path=partition_path,
        parquet_path=partition_path / PARQUET_FILE_NAME,
        manifest_path=partition_path / MANIFEST_FILE_NAME,
        record_count=int(manifest["record_count"]),
        written_record_count=written_record_count,
        logical_fingerprint=str(manifest["logical_fingerprint"]),
        physical_sha256=str(manifest["physical_sha256"]),
        status=status,
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HistoricalResearchCorruptionError("manifest cannot be read") from exc
    if not isinstance(value, dict):
        raise HistoricalResearchCorruptionError("manifest must be an object")
    return value


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    _fsync_file(temporary)
    temporary.replace(path)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
