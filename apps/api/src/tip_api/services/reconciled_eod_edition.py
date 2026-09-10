"""Pure reconciliation rules for a corrected immutable EOD research edition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable
from uuid import UUID

import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1 import EodPriceBarV1
from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodDiffDisposition,
    ReconciledEodDiffSummaryV1,
    ReconciledEodSourceProvenance,
    reconciled_eod_fingerprint,
)
from tip_api.persistence.parquet.eod_bars import (
    EOD_PRICE_BAR_ARROW_SCHEMA,
    PARQUET_FILE_NAME,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.manifest import (
    content_fingerprint,
    record_business_key,
)
from tip_api.providers.massive.grouped_daily_ingestion import (
    GroupedDailyIngestionResult,
    bind_case_sensitive_provider_ticker_source,
    load_identity_snapshot,
    process_grouped_daily_payload,
)
from tip_api.providers.massive.instrument_master_snapshot import (
    build_case_sensitive_provider_ticker_resolution,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.same_day_catchup import read_grouped_daily_package
from tip_api.services.historical_identity_source_custody import (
    read_identity_source_custody_at_data_root,
)


class ReconciledEodEditionError(RuntimeError):
    """Fail-closed error at the corrected EOD edition boundary."""


@dataclass(frozen=True, slots=True)
class ReconciledEodSessionCandidate:
    session_date: date
    rebuilt_records: tuple[EodPriceBarV1, ...]
    diff: ReconciledEodDiffSummaryV1
    source_provenance: ReconciledEodSourceProvenance
    source_observed_at: datetime
    source_package_manifest_sha256: str
    source_package_content_sha256: str
    identity_snapshot_fingerprint: str
    identity_source_fingerprint: str
    base_eod_fingerprint: str
    rebuilt_eod_fingerprint: str
    quality_summary_fingerprint: str
    quality_warnings: tuple[str, ...]
    mapping_result: GroupedDailyIngestionResult


def build_reconciled_eod_session_candidate(
    *,
    data_root: Path,
    package_path: Path,
    working_root: Path,
    session_date: date,
    source_provenance: ReconciledEodSourceProvenance,
) -> ReconciledEodSessionCandidate:
    """Rebuild and compare one session in an isolated `/tmp` workspace."""

    if not working_root.is_absolute() or not str(working_root).startswith("/tmp/"):
        raise ReconciledEodEditionError("reconciled EOD working root must be in /tmp")
    if working_root.exists() and any(working_root.iterdir()):
        raise ReconciledEodEditionError("reconciled EOD working root must be empty")
    working_root.mkdir(parents=True, exist_ok=True)

    package = read_grouped_daily_package(
        package_path=package_path,
        expected_session=session_date,
    )
    try:
        identity = load_identity_snapshot(
            data_root,
            provider_id=MASSIVE_PROVIDER_ID,
            as_of_date=session_date,
        )
        identity_source = read_identity_source_custody_at_data_root(
            data_root=data_root,
            provider=MASSIVE_PROVIDER_ID,
            session_date=session_date,
        )
    except Exception as exc:
        raise ReconciledEodEditionError(
            "same-session Identity evidence is unavailable"
        ) from exc
    identity_snapshot_fingerprint = identity.manifest.get(
        "snapshot_content_sha256"
    )
    if (
        not isinstance(identity_snapshot_fingerprint, str)
        or identity_source.manifest.canonical_snapshot_fingerprint
        != identity_snapshot_fingerprint
    ):
        raise ReconciledEodEditionError(
            "same-session Identity source binding differs"
        )
    source_payloads = tuple(
        item.source_payload() for item in identity_source.records
    )
    resolution = build_case_sensitive_provider_ticker_resolution(
        payloads=source_payloads,
        as_of_date=identity.as_of_date,
        ingested_at=_identity_created_at(identity.manifest),
        canonical_instrument_ids=identity.instrument_ids,
        canonical_resolver=identity.resolver,
    )
    try:
        bound_identity = bind_case_sensitive_provider_ticker_source(
            identity,
            source_payloads=source_payloads,
            source_fingerprint=identity_source.manifest.logical_fingerprint,
        )
    except RuntimeError as exc:
        raise ReconciledEodEditionError(
            "case-sensitive Identity source projection failed"
        ) from exc

    mapping = process_grouped_daily_payload(
        package.payload,
        identity=bound_identity,
        session_date=session_date,
        endpoint=package.manifest.endpoint_class,
        data_root=working_root,
        ingested_at=package.manifest.fetched_at,
        publish=True,
    )
    if not mapping.quality_gate_passed or mapping.status != "published":
        raise ReconciledEodEditionError(
            "reconciled EOD source package did not pass mapping gates"
        )
    rebuilt_records = _read_rebuilt_records(
        mapping.partition_path,
        session_date=session_date,
        expected_fingerprint=mapping.content_sha256,
    )
    base_repository = CanonicalEodReadRepository(data_root)
    base_integrity = base_repository.inspect_session(session_date)
    base_records = base_repository.read_canonical_records(session_date)
    diff = compare_reconciled_eod_records(
        base_records=base_records,
        rebuilt_records=rebuilt_records,
        expected_added_instrument_ids=(
            resolution.case_colliding_resolved_instrument_ids
        ),
        source_provenance=source_provenance,
    )
    return ReconciledEodSessionCandidate(
        session_date=session_date,
        rebuilt_records=rebuilt_records,
        diff=diff,
        source_provenance=source_provenance,
        source_observed_at=package.manifest.fetched_at,
        source_package_manifest_sha256=package.package_manifest_sha256,
        source_package_content_sha256=package.manifest.package_content_sha256,
        identity_snapshot_fingerprint=identity_snapshot_fingerprint,
        identity_source_fingerprint=identity_source.manifest.logical_fingerprint,
        base_eod_fingerprint=base_integrity.content_fingerprint,
        rebuilt_eod_fingerprint=mapping.content_sha256 or "",
        quality_summary_fingerprint=reconciled_eod_fingerprint(
            mapping.safe_lines()
        ),
        quality_warnings=tuple(sorted(mapping.quality_warnings)),
        mapping_result=mapping,
    )


def compare_reconciled_eod_records(
    *,
    base_records: tuple[EodPriceBarV1, ...],
    rebuilt_records: tuple[EodPriceBarV1, ...],
    expected_added_instrument_ids: frozenset[UUID],
    source_provenance: ReconciledEodSourceProvenance,
) -> ReconciledEodDiffSummaryV1:
    """Classify one complete-session rebuild without hiding unexpected change."""

    base = _records_by_key(base_records, family="base")
    rebuilt = _records_by_key(rebuilt_records, family="rebuilt")
    _require_same_session(base_records, rebuilt_records)

    base_keys = set(base)
    rebuilt_keys = set(rebuilt)
    added_keys = rebuilt_keys - base_keys
    absent_keys = base_keys - rebuilt_keys
    unexpected_added_keys = {
        key
        for key in added_keys
        if rebuilt[key].instrument_id not in expected_added_instrument_ids
    }

    unchanged = 0
    provenance_only = 0
    economic_changes = 0
    for key in base_keys & rebuilt_keys:
        base_record = base[key]
        rebuilt_record = rebuilt[key]
        if _economic_signature(base_record) != _economic_signature(rebuilt_record):
            economic_changes += 1
        elif _provenance_signature(base_record) != _provenance_signature(
            rebuilt_record
        ):
            provenance_only += 1
        else:
            unchanged += 1

    unexpected_provenance = (
        provenance_only
        if source_provenance == ReconciledEodSourceProvenance.RETAINED_ORIGINAL
        else 0
    )
    reasons: list[str] = []
    if unexpected_added_keys:
        reasons.append("unexpected_added_records")
    if absent_keys:
        reasons.append("base_records_absent")
    if economic_changes:
        reasons.append("economic_values_changed")
    if unexpected_provenance:
        reasons.append("retained_source_provenance_changed")

    if reasons:
        disposition = ReconciledEodDiffDisposition.QUARANTINED
    elif source_provenance == ReconciledEodSourceProvenance.LATER_REACQUISITION:
        if not added_keys and not provenance_only:
            disposition = ReconciledEodDiffDisposition.IDENTICAL
        else:
            disposition = (
                ReconciledEodDiffDisposition.ACCEPTED_LATER_REACQUISITION
            )
    elif added_keys:
        disposition = (
            ReconciledEodDiffDisposition.ACCEPTED_CASE_SENSITIVE_ADDITIONS_ONLY
        )
    else:
        disposition = ReconciledEodDiffDisposition.IDENTICAL

    return ReconciledEodDiffSummaryV1(
        base_record_count=len(base),
        rebuilt_record_count=len(rebuilt),
        unchanged_record_count=unchanged,
        provenance_only_change_count=provenance_only,
        unexpected_provenance_change_count=unexpected_provenance,
        added_record_count=len(added_keys),
        unexpected_added_record_count=len(unexpected_added_keys),
        absent_record_count=len(absent_keys),
        economic_change_record_count=economic_changes,
        disposition=disposition,
        quarantine_reasons=tuple(reasons),
    )


def _records_by_key(
    records: tuple[EodPriceBarV1, ...],
    *,
    family: str,
) -> dict[tuple[str, str, str, int], EodPriceBarV1]:
    if not records:
        raise ReconciledEodEditionError(f"{family} EOD session is empty")
    result: dict[tuple[str, str, str, int], EodPriceBarV1] = {}
    for record in records:
        key = record_business_key(record)
        if key in result:
            raise ReconciledEodEditionError(
                f"{family} EOD session contains a duplicate business key"
            )
        result[key] = record
    return result


def _require_same_session(
    base_records: tuple[EodPriceBarV1, ...],
    rebuilt_records: tuple[EodPriceBarV1, ...],
) -> date:
    sessions = {record.session_date for record in (*base_records, *rebuilt_records)}
    if len(sessions) != 1:
        raise ReconciledEodEditionError(
            "base and rebuilt records must describe exactly one shared session"
        )
    return next(iter(sessions))


def _economic_signature(record: EodPriceBarV1) -> tuple[object, ...]:
    return (
        record.open,
        record.high,
        record.low,
        record.close,
        record.volume,
        record.vwap,
        record.trade_count,
        record.notional,
        record.currency,
        record.split_adjustment_factor,
        record.dividend_adjustment_factor,
        record.total_return_adjustment_factor,
        record.adjusted_close,
    )


def _provenance_signature(record: EodPriceBarV1) -> tuple[object, ...]:
    return (
        record.source_record_id,
        record.ingested_at,
        record.is_latest_revision,
        record.quality_status,
        record.quality_flags,
        record.schema_version,
    )


def expected_case_sensitive_additions(
    *,
    exact_provider_tickers: Iterable[str],
    exact_resolver: dict[str, UUID],
) -> frozenset[UUID]:
    """Return resolved IDs whose normalized symbol has a case-distinct sibling."""

    groups: dict[str, set[str]] = {}
    for raw_ticker in exact_provider_tickers:
        if not isinstance(raw_ticker, str) or not raw_ticker.strip():
            raise ReconciledEodEditionError("exact provider ticker is invalid")
        ticker = raw_ticker.strip()
        groups.setdefault(ticker.upper(), set()).add(ticker)
    result: set[UUID] = set()
    for tickers in groups.values():
        if len(tickers) < 2:
            continue
        for ticker in tickers:
            instrument_id = exact_resolver.get(ticker)
            if instrument_id is not None:
                result.add(instrument_id)
    return frozenset(result)


def _identity_created_at(manifest: dict[str, object]) -> datetime:
    value = manifest.get("created_at")
    if not isinstance(value, str):
        raise ReconciledEodEditionError("Identity creation time is unavailable")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ReconciledEodEditionError("Identity creation time is invalid") from exc
    if parsed.tzinfo is None:
        raise ReconciledEodEditionError("Identity creation time lacks timezone")
    return parsed


def _read_rebuilt_records(
    partition_path: Path | None,
    *,
    session_date: date,
    expected_fingerprint: str | None,
) -> tuple[EodPriceBarV1, ...]:
    if partition_path is None or partition_path.is_symlink():
        raise ReconciledEodEditionError("rebuilt EOD partition is unavailable")
    parquet_path = partition_path / PARQUET_FILE_NAME
    if parquet_path.is_symlink() or not parquet_path.is_file():
        raise ReconciledEodEditionError("rebuilt EOD Parquet is unavailable")
    try:
        table = pq.ParquetFile(parquet_path).read()
    except Exception as exc:
        raise ReconciledEodEditionError("rebuilt EOD Parquet is unreadable") from exc
    if not table.schema.equals(EOD_PRICE_BAR_ARROW_SCHEMA, check_metadata=False):
        raise ReconciledEodEditionError("rebuilt EOD Parquet schema differs")
    try:
        records = tuple(
            EodPriceBarV1.model_validate(row) for row in table.to_pylist()
        )
    except Exception as exc:
        raise ReconciledEodEditionError(
            "rebuilt EOD rows violate the canonical contract"
        ) from exc
    if {item.session_date for item in records} != {session_date}:
        raise ReconciledEodEditionError("rebuilt EOD session differs")
    ordered = tuple(
        sorted(
            records,
            key=lambda item: (
                str(item.instrument_id),
                item.session_date,
                item.source,
                item.revision,
            ),
        )
    )
    if (
        expected_fingerprint is None
        or content_fingerprint(ordered) != expected_fingerprint
    ):
        raise ReconciledEodEditionError("rebuilt EOD fingerprint differs")
    return ordered
