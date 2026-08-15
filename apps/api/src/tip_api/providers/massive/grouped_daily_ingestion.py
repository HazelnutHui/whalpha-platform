"""Massive Grouped Daily canonical EOD ingestion using completed ticker resolver."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal, Mapping
from uuid import UUID
from zoneinfo import ZoneInfo

import pyarrow.parquet as pq
from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import EodPriceBarV1
from tip_api.persistence.parquet.eod_bars import ParquetEodPriceBarRepository
from tip_api.persistence.parquet.instrument_master_snapshot import (
    INSTRUMENT_MASTER_ARROW_SCHEMA,
    PROVIDER_IDENTITY_ARROW_SCHEMA,
    PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA,
    _identity_table_to_rows,
    _instrument_table_to_rows,
    _resolver_table_to_rows,
    records_fingerprint,
)
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.credential import MassiveCredentialFileError, load_massive_provider_config_from_file
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveTransportDataError,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
    MassiveUrllibTransport,
)

AUTHORIZED_SESSION_DATE = date(2026, 8, 13)
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
ENDPOINT_TEMPLATE = "/v2/aggs/grouped/locale/us/market/stocks/{session_date}"
MARKET_TZ = ZoneInfo("America/New_York")
CONFLICTING_DUPLICATE_RATIO_GATE = 0.001
NUMERIC_FAILURE_RATIO_GATE = 0.001
REQUIRED_MISSING_RATIO_GATE = 0.001
IDENTITY_COVERAGE_GATE = 0.80

IdentityCategory = Literal["resolved_eligible", "unresolved_eligible", "expected_exclusion", "ambiguous", "rejected", "missing"]


@dataclass(frozen=True)
class IdentitySnapshot:
    as_of_date: date
    provider_id: str
    resolver: dict[str, UUID]
    identity_status: dict[str, str]
    identity_flags: dict[str, tuple[str, ...]]
    instrument_ids: frozenset[UUID]
    manifest: dict[str, object]


@dataclass(frozen=True)
class NumericBar:
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    vwap: Decimal | None
    trade_count: int | None
    timestamp_session_date: date | None


@dataclass(frozen=True)
class DuplicateAnalysis:
    records: tuple[Mapping[str, object], ...]
    exact_duplicate_ticker_count: int
    exact_duplicate_record_count: int
    conflicting_duplicate_ticker_count: int
    conflicting_duplicate_record_count: int
    conflicting_tickers: frozenset[str]


@dataclass(frozen=True)
class GroupedDailyIngestionResult:
    provider: str
    endpoint: str
    session_date: date
    identity_as_of_date: date
    request_count: int
    adjusted: bool
    raw_result_count: int
    unique_raw_ticker_count: int
    exact_duplicate_ticker_count: int
    exact_duplicate_record_count: int
    conflicting_duplicate_ticker_count: int
    conflicting_duplicate_record_count: int
    conflicting_duplicate_ratio: float
    resolved_eligible_bar_count: int
    unresolved_eligible_bar_count: int
    expected_exclusion_bar_count: int
    ambiguous_bar_count: int
    rejected_identity_bar_count: int
    missing_identity_bar_count: int
    identity_classified_count: int
    identity_eligible_denominator: int
    identity_resolved_coverage_ratio: float
    numeric_classified_count: int
    numeric_valid_count: int
    numeric_conversion_failure_count: int
    numeric_conversion_failure_ratio: float
    required_field_missing_count: int
    required_field_missing_ratio: float
    optional_vwap_missing_count: int
    optional_trade_count_missing_count: int
    nonpositive_price_count: int
    ohlc_consistency_failure_count: int
    negative_volume_count: int
    zero_volume_count: int
    timestamp_session_mismatch_count: int
    identity_resolved_and_numeric_valid_count: int
    canonical_validation_failure_count: int
    canonical_bar_count: int
    count_reconciliation_passed: bool
    written_record_count: int
    content_sha256: str | None
    partition_path: Path | None
    quality_gate_passed: bool
    quality_gate_failures: tuple[str, ...]
    quality_warnings: tuple[str, ...]
    status: str

    @property
    def exact_duplicate_count(self) -> int:
        return self.exact_duplicate_record_count

    @property
    def conflicting_duplicate_count(self) -> int:
        return self.conflicting_duplicate_record_count

    def safe_lines(self) -> tuple[str, ...]:
        pairs = (
            ("provider", self.provider),
            ("endpoint", self.endpoint),
            ("session_date", self.session_date.isoformat()),
            ("identity_as_of_date", self.identity_as_of_date.isoformat()),
            ("request_count", self.request_count),
            ("adjusted", str(self.adjusted).lower()),
            ("raw_result_count", self.raw_result_count),
            ("unique_raw_ticker_count", self.unique_raw_ticker_count),
            ("exact_duplicate_ticker_count", self.exact_duplicate_ticker_count),
            ("exact_duplicate_record_count", self.exact_duplicate_record_count),
            ("conflicting_duplicate_ticker_count", self.conflicting_duplicate_ticker_count),
            ("conflicting_duplicate_record_count", self.conflicting_duplicate_record_count),
            ("conflicting_duplicate_ratio", f"{self.conflicting_duplicate_ratio:.6f}"),
            ("resolved_eligible_bar_count", self.resolved_eligible_bar_count),
            ("unresolved_eligible_bar_count", self.unresolved_eligible_bar_count),
            ("expected_exclusion_bar_count", self.expected_exclusion_bar_count),
            ("ambiguous_bar_count", self.ambiguous_bar_count),
            ("rejected_identity_bar_count", self.rejected_identity_bar_count),
            ("missing_identity_bar_count", self.missing_identity_bar_count),
            ("identity_classified_count", self.identity_classified_count),
            ("identity_eligible_denominator", self.identity_eligible_denominator),
            ("identity_resolved_coverage_ratio", f"{self.identity_resolved_coverage_ratio:.6f}"),
            ("numeric_classified_count", self.numeric_classified_count),
            ("numeric_valid_count", self.numeric_valid_count),
            ("numeric_conversion_failure_count", self.numeric_conversion_failure_count),
            ("numeric_conversion_failure_ratio", f"{self.numeric_conversion_failure_ratio:.6f}"),
            ("required_field_missing_count", self.required_field_missing_count),
            ("required_field_missing_ratio", f"{self.required_field_missing_ratio:.6f}"),
            ("optional_vwap_missing_count", self.optional_vwap_missing_count),
            ("optional_trade_count_missing_count", self.optional_trade_count_missing_count),
            ("nonpositive_price_count", self.nonpositive_price_count),
            ("ohlc_consistency_failure_count", self.ohlc_consistency_failure_count),
            ("negative_volume_count", self.negative_volume_count),
            ("zero_volume_count", self.zero_volume_count),
            ("timestamp_session_mismatch_count", self.timestamp_session_mismatch_count),
            ("identity_resolved_and_numeric_valid_count", self.identity_resolved_and_numeric_valid_count),
            ("canonical_validation_failure_count", self.canonical_validation_failure_count),
            ("canonical_bar_count", self.canonical_bar_count),
            ("count_reconciliation_passed", str(self.count_reconciliation_passed).lower()),
            ("written_record_count", self.written_record_count),
            ("content_sha256", self.content_sha256 or ""),
            ("quality_gate_passed", str(self.quality_gate_passed).lower()),
            ("quality_gate_failures", ",".join(self.quality_gate_failures)),
            ("quality_warnings", ",".join(self.quality_warnings)),
            ("publish_ready", str(self.quality_gate_passed).lower()),
            ("status", self.status),
        )
        return tuple(f"{key}={value}" for key, value in pairs)


def load_identity_snapshot(root: Path, *, provider_id: str, as_of_date: date) -> IdentitySnapshot:
    root = _safe_root(root)
    base = root / "market-data"
    snapshot_manifest_path = base / "snapshots" / "instrument-master" / f"as_of_date={as_of_date.isoformat()}" / "manifest.json"
    manifest = _read_manifest(snapshot_manifest_path)
    if manifest.get("completion_status") != "completed":
        raise RuntimeError("identity snapshot is not completed")
    if manifest.get("as_of_date") != as_of_date.isoformat():
        raise RuntimeError("identity snapshot as_of_date mismatch")
    if manifest.get("provider_id") != provider_id:
        raise RuntimeError("identity snapshot provider mismatch")
    instrument_path = base / "instrument-master" / "schema_version=1" / f"as_of_date={as_of_date.isoformat()}" / "part-00000.parquet"
    identity_path = base / "provider-instrument-identity" / "schema_version=1" / f"provider={provider_id}" / f"as_of_date={as_of_date.isoformat()}" / "part-00000.parquet"
    resolver_path = base / "provider-ticker-resolver" / "schema_version=1" / f"provider={provider_id}" / f"as_of_date={as_of_date.isoformat()}" / "part-00000.parquet"
    for path in (instrument_path, identity_path, resolver_path):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("identity snapshot parquet path is invalid")
    instrument_table = pq.ParquetFile(instrument_path).read()
    identity_table = pq.ParquetFile(identity_path).read()
    resolver_table = pq.ParquetFile(resolver_path).read()
    _verify_table(
        instrument_table,
        expected_schema=INSTRUMENT_MASTER_ARROW_SCHEMA,
        expected_count=manifest.get("instrument_count"),
        expected_fingerprint=manifest.get("instrument_content_sha256"),
        table_to_rows=_instrument_table_to_rows,
    )
    _verify_table(
        identity_table,
        expected_schema=PROVIDER_IDENTITY_ARROW_SCHEMA,
        expected_count=manifest.get("identity_count"),
        expected_fingerprint=manifest.get("identity_content_sha256"),
        table_to_rows=_identity_table_to_rows,
    )
    _verify_table(
        resolver_table,
        expected_schema=PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA,
        expected_count=manifest.get("resolver_count"),
        expected_fingerprint=manifest.get("resolver_content_sha256"),
        table_to_rows=_resolver_table_to_rows,
    )
    instruments = instrument_table.to_pylist()
    identities = identity_table.to_pylist()
    resolvers = resolver_table.to_pylist()
    instrument_ids = frozenset(UUID(row["instrument_id"]) for row in instruments)
    resolver: dict[str, UUID] = {}
    for row in resolvers:
        ticker = _ticker(row.get("provider_ticker"))
        instrument_id = UUID(row["canonical_instrument_id"])
        if ticker in resolver:
            raise RuntimeError("resolver ticker is not unique")
        if instrument_id not in instrument_ids:
            raise RuntimeError("resolver instrument_id is missing from Instrument Master")
        resolver[ticker] = instrument_id
    status: dict[str, str] = {}
    flags: dict[str, tuple[str, ...]] = {}
    for row in identities:
        ticker = _ticker(row.get("provider_ticker"))
        current = status.get(ticker)
        next_status = str(row.get("resolution_status"))
        qflags = tuple(row.get("quality_flags") or ())
        if current is None or current == "resolved":
            status[ticker] = next_status
            flags[ticker] = qflags
    if len(resolver) != manifest.get("resolver_count"):
        raise RuntimeError("resolver count mismatch")
    return IdentitySnapshot(
        as_of_date=as_of_date,
        provider_id=provider_id,
        resolver=resolver,
        identity_status=status,
        identity_flags=flags,
        instrument_ids=instrument_ids,
        manifest=manifest,
    )


def ingest_grouped_daily(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    session_date: date,
    identity_as_of_date: date,
    data_root: Path,
    ingested_at: datetime | None = None,
) -> GroupedDailyIngestionResult:
    identity = load_identity_snapshot(data_root, provider_id=MASSIVE_PROVIDER_ID, as_of_date=identity_as_of_date)
    endpoint = ENDPOINT_TEMPLATE.format(session_date=session_date.isoformat())
    response = transport.get_json(
        endpoint,
        params={"adjusted": False},
        api_key=config.api_key,
        timeout_seconds=config.request_timeout_seconds,
        base_url=config.base_url,
    )
    return process_grouped_daily_payload(
        response,
        identity=identity,
        session_date=session_date,
        endpoint=endpoint,
        data_root=data_root,
        ingested_at=ingested_at or datetime.now(UTC),
        publish=True,
    )


def process_grouped_daily_payload(
    payload: Mapping[str, object],
    *,
    identity: IdentitySnapshot,
    session_date: date,
    endpoint: str,
    data_root: Path,
    ingested_at: datetime,
    publish: bool,
) -> GroupedDailyIngestionResult:
    results = payload.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Grouped Daily results must be a list")
    raw_records = tuple(item for item in results if isinstance(item, Mapping))
    duplicate_analysis = _deduplicate_records(raw_records)
    counters = _Counters(
        raw_result_count=len(results),
        unique_raw_ticker_count=len(_ticker_groups(raw_records)),
        exact_duplicate_ticker_count=duplicate_analysis.exact_duplicate_ticker_count,
        exact_duplicate_record_count=duplicate_analysis.exact_duplicate_record_count,
        conflicting_duplicate_ticker_count=duplicate_analysis.conflicting_duplicate_ticker_count,
        conflicting_duplicate_record_count=duplicate_analysis.conflicting_duplicate_record_count,
    )
    bars: list[EodPriceBarV1] = []
    for item in raw_records:
        category, instrument_id = _classify_identity(item, identity=identity)
        counters.record_identity(category)
    for item in duplicate_analysis.records:
        _process_numeric_and_canonical(
            item,
            identity=identity,
            session_date=session_date,
            ingested_at=ingested_at,
            counters=counters,
            bars=bars,
            conflicted=duplicate_analysis.conflicting_tickers,
        )
    coverage = counters.identity_resolved_coverage_ratio
    warnings = _quality_warnings(counters)
    failures = _gate_failures(counters, request_count=1, adjusted=False, canonical_count=len(bars))
    write_result = None
    if publish and not failures:
        write_result = ParquetEodPriceBarRepository(data_root).publish_session(
            tuple(bars),
            session_date=session_date,
            provider_id=MASSIVE_PROVIDER_ID,
            quality_summary=counters.quality_summary(warnings),
            identity_snapshot={
                "as_of_date": identity.as_of_date.isoformat(),
                "provider_id": identity.provider_id,
                "snapshot_content_sha256": identity.manifest.get("snapshot_content_sha256"),
                "resolver_count": len(identity.resolver),
            },
        )
    return GroupedDailyIngestionResult(
        provider=MASSIVE_PROVIDER_ID,
        endpoint=endpoint,
        session_date=session_date,
        identity_as_of_date=identity.as_of_date,
        request_count=1,
        adjusted=False,
        raw_result_count=counters.raw_result_count,
        unique_raw_ticker_count=counters.unique_raw_ticker_count,
        exact_duplicate_ticker_count=counters.exact_duplicate_ticker_count,
        exact_duplicate_record_count=counters.exact_duplicate_record_count,
        conflicting_duplicate_ticker_count=counters.conflicting_duplicate_ticker_count,
        conflicting_duplicate_record_count=counters.conflicting_duplicate_record_count,
        conflicting_duplicate_ratio=counters.conflicting_duplicate_ratio,
        resolved_eligible_bar_count=counters.resolved_eligible_bar_count,
        unresolved_eligible_bar_count=counters.unresolved_eligible_bar_count,
        expected_exclusion_bar_count=counters.expected_exclusion_bar_count,
        ambiguous_bar_count=counters.ambiguous_bar_count,
        rejected_identity_bar_count=counters.rejected_identity_bar_count,
        missing_identity_bar_count=counters.missing_identity_bar_count,
        identity_classified_count=counters.identity_classified_count,
        identity_eligible_denominator=counters.identity_eligible_denominator,
        identity_resolved_coverage_ratio=coverage,
        numeric_classified_count=counters.numeric_classified_count,
        numeric_valid_count=counters.numeric_valid_count,
        numeric_conversion_failure_count=counters.numeric_conversion_failure_count,
        numeric_conversion_failure_ratio=counters.numeric_conversion_failure_ratio,
        required_field_missing_count=counters.required_field_missing_count,
        required_field_missing_ratio=counters.required_field_missing_ratio,
        optional_vwap_missing_count=counters.optional_vwap_missing_count,
        optional_trade_count_missing_count=counters.optional_trade_count_missing_count,
        nonpositive_price_count=counters.nonpositive_price_count,
        ohlc_consistency_failure_count=counters.ohlc_consistency_failure_count,
        negative_volume_count=counters.negative_volume_count,
        zero_volume_count=counters.zero_volume_count,
        timestamp_session_mismatch_count=counters.timestamp_session_mismatch_count,
        identity_resolved_and_numeric_valid_count=counters.identity_resolved_and_numeric_valid_count,
        canonical_validation_failure_count=counters.canonical_validation_failure_count,
        canonical_bar_count=len(bars),
        count_reconciliation_passed=counters.count_reconciliation_passed,
        written_record_count=write_result.written_record_count if write_result else 0,
        content_sha256=write_result.content_sha256 if write_result else None,
        partition_path=write_result.partition_path if write_result else None,
        quality_gate_passed=not failures,
        quality_gate_failures=failures,
        quality_warnings=warnings,
        status=write_result.status if write_result else "quality_gate_failed",
    )


@dataclass
class _Counters:
    raw_result_count: int = 0
    unique_raw_ticker_count: int = 0
    exact_duplicate_ticker_count: int = 0
    exact_duplicate_record_count: int = 0
    conflicting_duplicate_ticker_count: int = 0
    conflicting_duplicate_record_count: int = 0
    resolved_eligible_bar_count: int = 0
    unresolved_eligible_bar_count: int = 0
    expected_exclusion_bar_count: int = 0
    ambiguous_bar_count: int = 0
    rejected_identity_bar_count: int = 0
    missing_identity_bar_count: int = 0
    numeric_classified_count: int = 0
    numeric_valid_count: int = 0
    numeric_conversion_failure_count: int = 0
    required_field_missing_count: int = 0
    optional_vwap_missing_count: int = 0
    optional_trade_count_missing_count: int = 0
    nonpositive_price_count: int = 0
    ohlc_consistency_failure_count: int = 0
    negative_volume_count: int = 0
    zero_volume_count: int = 0
    timestamp_session_mismatch_count: int = 0
    identity_resolved_and_numeric_valid_count: int = 0
    canonical_validation_failure_count: int = 0

    @property
    def identity_classified_count(self) -> int:
        return (
            self.resolved_eligible_bar_count
            + self.unresolved_eligible_bar_count
            + self.expected_exclusion_bar_count
            + self.ambiguous_bar_count
            + self.rejected_identity_bar_count
            + self.missing_identity_bar_count
        )

    @property
    def identity_eligible_denominator(self) -> int:
        return (
            self.resolved_eligible_bar_count
            + self.unresolved_eligible_bar_count
            + self.ambiguous_bar_count
            + self.missing_identity_bar_count
        )

    @property
    def identity_resolved_coverage_ratio(self) -> float:
        denominator = self.identity_eligible_denominator
        return self.resolved_eligible_bar_count / denominator if denominator else 0.0

    @property
    def numeric_conversion_failure_ratio(self) -> float:
        return self.numeric_conversion_failure_count / self.numeric_classified_count if self.numeric_classified_count else 0.0

    @property
    def required_field_missing_ratio(self) -> float:
        return self.required_field_missing_count / self.numeric_classified_count if self.numeric_classified_count else 0.0

    @property
    def conflicting_duplicate_ratio(self) -> float:
        return self.conflicting_duplicate_record_count / self.raw_result_count if self.raw_result_count else 0.0

    @property
    def count_reconciliation_passed(self) -> bool:
        return self.identity_classified_count == self.raw_result_count and self.numeric_classified_count == (
            self.raw_result_count - self.exact_duplicate_record_count - self.conflicting_duplicate_record_count
        )

    def record_identity(self, category: IdentityCategory) -> None:
        if category == "resolved_eligible":
            self.resolved_eligible_bar_count += 1
        elif category == "unresolved_eligible":
            self.unresolved_eligible_bar_count += 1
        elif category == "expected_exclusion":
            self.expected_exclusion_bar_count += 1
        elif category == "ambiguous":
            self.ambiguous_bar_count += 1
        elif category == "rejected":
            self.rejected_identity_bar_count += 1
        else:
            self.missing_identity_bar_count += 1

    def quality_summary(self, warnings: tuple[str, ...]) -> dict[str, object]:
        return {
            **self.__dict__,
            "identity_classified_count": self.identity_classified_count,
            "identity_eligible_denominator": self.identity_eligible_denominator,
            "identity_resolved_coverage_ratio": self.identity_resolved_coverage_ratio,
            "numeric_conversion_failure_ratio": self.numeric_conversion_failure_ratio,
            "required_field_missing_ratio": self.required_field_missing_ratio,
            "conflicting_duplicate_ratio": self.conflicting_duplicate_ratio,
            "count_reconciliation_passed": self.count_reconciliation_passed,
            "quality_warnings": list(warnings),
        }


def _ticker_groups(records: tuple[Mapping[str, object], ...]) -> dict[str, list[Mapping[str, object]]]:
    groups: dict[str, list[Mapping[str, object]]] = {}
    for item in records:
        try:
            ticker = _ticker(item.get("T") or item.get("ticker"))
        except RuntimeError:
            ticker = "<missing>"
        groups.setdefault(ticker, []).append(item)
    return groups


def _deduplicate_records(records: tuple[Mapping[str, object], ...]) -> DuplicateAnalysis:
    groups = _ticker_groups(records)
    exact_duplicate_ticker_count = 0
    exact_duplicate_record_count = 0
    conflicting_duplicate_ticker_count = 0
    conflicting_duplicate_record_count = 0
    unique_records: list[Mapping[str, object]] = []
    conflicted: set[str] = set()
    for ticker, items in groups.items():
        signatures = {_bar_signature(item) for item in items}
        if len(items) > 1 and len(signatures) == 1:
            exact_duplicate_ticker_count += 1
            exact_duplicate_record_count += len(items) - 1
            unique_records.append(items[0])
        elif len(items) > 1:
            conflicting_duplicate_ticker_count += 1
            conflicting_duplicate_record_count += len(items)
            conflicted.add(ticker)
        else:
            unique_records.append(items[0])
    return DuplicateAnalysis(
        records=tuple(unique_records),
        exact_duplicate_ticker_count=exact_duplicate_ticker_count,
        exact_duplicate_record_count=exact_duplicate_record_count,
        conflicting_duplicate_ticker_count=conflicting_duplicate_ticker_count,
        conflicting_duplicate_record_count=conflicting_duplicate_record_count,
        conflicting_tickers=frozenset(conflicted),
    )


def _classify_identity(item: Mapping[str, object], *, identity: IdentitySnapshot) -> tuple[IdentityCategory, UUID | None]:
    try:
        ticker = _ticker(item.get("T") or item.get("ticker"))
    except RuntimeError:
        return "missing", None
    instrument_id = identity.resolver.get(ticker)
    if instrument_id is not None:
        return "resolved_eligible", instrument_id
    status = identity.identity_status.get(ticker)
    if status == "unresolved":
        return "unresolved_eligible", None
    if status == "excluded":
        return "expected_exclusion", None
    if status == "ambiguous":
        return "ambiguous", None
    if status == "rejected":
        return "rejected", None
    return "missing", None


def _process_numeric_and_canonical(
    item: Mapping[str, object],
    *,
    identity: IdentitySnapshot,
    session_date: date,
    ingested_at: datetime,
    counters: _Counters,
    bars: list[EodPriceBarV1],
    conflicted: frozenset[str],
) -> None:
    category, instrument_id = _classify_identity(item, identity=identity)
    try:
        ticker = _ticker(item.get("T") or item.get("ticker"))
    except RuntimeError:
        ticker = "<missing>"
    if ticker in conflicted:
        return
    numeric = _validate_numeric_bar(item, counters=counters, session_date=session_date)
    if numeric is None:
        return
    if category != "resolved_eligible" or instrument_id is None:
        return
    counters.identity_resolved_and_numeric_valid_count += 1
    flags = ["adjustment_factors_unverified"]
    if numeric.vwap is None:
        flags.append("missing_vwap")
    if numeric.trade_count is None:
        flags.append("missing_trade_count")
    if numeric.volume == 0:
        flags.append("zero_volume")
    try:
        bars.append(
            EodPriceBarV1(
                instrument_id=instrument_id,
                session_date=session_date,
                open=numeric.open,
                high=numeric.high,
                low=numeric.low,
                close=numeric.close,
                volume=numeric.volume,
                vwap=numeric.vwap,
                trade_count=numeric.trade_count,
                notional=Decimal("0"),
                currency="USD",
                split_adjustment_factor=Decimal("1"),
                dividend_adjustment_factor=Decimal("1"),
                total_return_adjustment_factor=Decimal("1"),
                adjusted_close=numeric.close,
                source=MASSIVE_PROVIDER_ID,
                source_record_id=f"{ticker}:{item.get('t')}",
                ingested_at=ingested_at,
                revision=1,
                is_latest_revision=True,
                quality_status=QualityStatus.VALID,
                quality_flags=tuple(flags),
            )
        )
    except ValidationError:
        counters.canonical_validation_failure_count += 1


def _validate_numeric_bar(item: Mapping[str, object], *, counters: _Counters, session_date: date) -> NumericBar | None:
    counters.numeric_classified_count += 1
    try:
        open_ = parse_massive_decimal(item.get("o"), field_name="o", required=True)
        high = parse_massive_decimal(item.get("h"), field_name="h", required=True)
        low = parse_massive_decimal(item.get("l"), field_name="l", required=True)
        close = parse_massive_decimal(item.get("c"), field_name="c", required=True)
        volume = parse_massive_integral(item.get("v"), field_name="v", required=True, allow_negative=True)
        timestamp_ms = parse_massive_integral(item.get("t"), field_name="t", required=True, allow_negative=False)
    except _MissingRequired:
        counters.required_field_missing_count += 1
        return None
    except _NumericFailure:
        counters.numeric_conversion_failure_count += 1
        return None
    try:
        vwap = parse_massive_decimal(item.get("vw"), field_name="vw", required=False)
        trade_count = parse_massive_integral(item.get("n"), field_name="n", required=False, allow_negative=False)
    except _NumericFailure:
        counters.numeric_conversion_failure_count += 1
        return None
    if item.get("vw") is None:
        counters.optional_vwap_missing_count += 1
    if item.get("n") is None:
        counters.optional_trade_count_missing_count += 1
    if min(open_, high, low, close) <= 0:
        counters.nonpositive_price_count += 1
        return None
    if volume < 0:
        counters.negative_volume_count += 1
        return None
    if volume == 0:
        counters.zero_volume_count += 1
    if high < open_ or high < close or high < low or low > open_ or low > close or low > high:
        counters.ohlc_consistency_failure_count += 1
        return None
    timestamp_date = _session_date_from_timestamp_ms(timestamp_ms)
    if timestamp_date is None:
        counters.numeric_conversion_failure_count += 1
        return None
    if timestamp_date != session_date:
        counters.timestamp_session_mismatch_count += 1
        return None
    counters.numeric_valid_count += 1
    return NumericBar(
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        vwap=vwap,
        trade_count=trade_count,
        timestamp_session_date=timestamp_date,
    )


def _gate_failures(c: _Counters, *, request_count: int, adjusted: bool, canonical_count: int) -> tuple[str, ...]:
    failures: list[str] = []
    if c.raw_result_count <= 5000:
        failures.append("raw_result_count_below_gate")
    if request_count != 1:
        failures.append("request_count_not_one")
    if adjusted:
        failures.append("adjusted_not_false")
    if c.identity_classified_count != c.raw_result_count:
        failures.append("identity_count_reconciliation_failed")
    if not c.count_reconciliation_passed:
        failures.append("numeric_count_reconciliation_failed")
    if c.identity_resolved_coverage_ratio < IDENTITY_COVERAGE_GATE:
        failures.append("identity_resolved_coverage_below_gate")
    if c.numeric_conversion_failure_ratio > NUMERIC_FAILURE_RATIO_GATE:
        failures.append("numeric_conversion_failure_ratio_above_gate")
    if c.required_field_missing_ratio > REQUIRED_MISSING_RATIO_GATE:
        failures.append("required_field_missing_ratio_above_gate")
    if c.conflicting_duplicate_ratio > CONFLICTING_DUPLICATE_RATIO_GATE:
        failures.append("conflicting_duplicate_ratio_above_gate")
    for field in (
        "nonpositive_price_count",
        "ohlc_consistency_failure_count",
        "negative_volume_count",
        "timestamp_session_mismatch_count",
        "canonical_validation_failure_count",
    ):
        if getattr(c, field) != 0:
            failures.append(f"{field}_nonzero")
    if canonical_count <= 5000:
        failures.append("canonical_bar_count_below_gate")
    return tuple(failures)


def _quality_warnings(c: _Counters) -> tuple[str, ...]:
    warnings: list[str] = []
    if c.conflicting_duplicate_record_count:
        warnings.append("conflicting_duplicates_isolated")
    if c.exact_duplicate_record_count:
        warnings.append("exact_duplicates_deduplicated")
    if c.optional_vwap_missing_count:
        warnings.append("missing_optional_vwap")
    if c.optional_trade_count_missing_count:
        warnings.append("missing_optional_trade_count")
    if c.zero_volume_count:
        warnings.append("zero_volume_records_present")
    if c.expected_exclusion_bar_count:
        warnings.append("expected_exclusions_present")
    if c.unresolved_eligible_bar_count:
        warnings.append("unresolved_eligible_identities_present")
    return tuple(warnings)


def _verify_table(table: Any, *, expected_schema: Any, expected_count: object, expected_fingerprint: object, table_to_rows: Any) -> None:
    if table.schema != expected_schema:
        raise RuntimeError("identity snapshot schema mismatch")
    if not isinstance(expected_count, int) or table.num_rows != expected_count:
        raise RuntimeError("identity snapshot row count mismatch")
    if not isinstance(expected_fingerprint, str) or records_fingerprint(table_to_rows(table)) != expected_fingerprint:
        raise RuntimeError("identity snapshot fingerprint mismatch")


def _ticker(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("missing ticker")
    return value.strip().upper()


def _bar_signature(item: Mapping[str, object]) -> tuple[object, ...]:
    return tuple(item.get(key) for key in ("T", "ticker", "o", "h", "l", "c", "v", "vw", "n", "t"))


class _MissingRequired(Exception):
    pass


class _NumericFailure(Exception):
    pass


def parse_massive_decimal(value: object, *, field_name: str, required: bool) -> Decimal | None:
    del field_name
    if value is None:
        if required:
            raise _MissingRequired()
        return None
    if isinstance(value, bool):
        raise _NumericFailure()
    if isinstance(value, float) and not math.isfinite(value):
        raise _NumericFailure()
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, int | float):
        decimal_value = Decimal(str(value))
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise _NumericFailure()
        try:
            decimal_value = Decimal(stripped)
        except InvalidOperation as exc:
            raise _NumericFailure() from exc
    else:
        raise _NumericFailure()
    if not decimal_value.is_finite():
        raise _NumericFailure()
    return decimal_value


def parse_massive_integral(value: object, *, field_name: str, required: bool, allow_negative: bool) -> int | None:
    decimal_value = parse_massive_decimal(value, field_name=field_name, required=required)
    if decimal_value is None:
        return None
    if decimal_value != decimal_value.to_integral_value():
        raise _NumericFailure()
    integer_value = int(decimal_value)
    if integer_value < 0 and not allow_negative:
        raise _NumericFailure()
    return integer_value


def _session_date_from_timestamp_ms(timestamp_ms: int) -> date | None:
    try:
        timestamp_utc = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None
    market_date = timestamp_utc.astimezone(MARKET_TZ).date()
    utc_date = timestamp_utc.date()
    if market_date == AUTHORIZED_SESSION_DATE or utc_date == AUTHORIZED_SESSION_DATE:
        return AUTHORIZED_SESSION_DATE
    return market_date


def _safe_root(root: Path) -> Path:
    if root != APPROVED_DATA_ROOT and not str(root).startswith("/tmp/"):
        raise RuntimeError("data root is not approved")
    if root.exists() and root.is_symlink():
        raise RuntimeError("data root must not be a symlink")
    return root.resolve()


def _read_manifest(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("manifest path invalid")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("manifest must be object")
    return data


def parse_date(value: str, *, name: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must use YYYY-MM-DD") from exc
    if parsed != AUTHORIZED_SESSION_DATE:
        raise ValueError(f"{name} is not authorized")
    return parsed


def parse_data_root(value: str) -> Path:
    path = Path(value)
    if path != APPROVED_DATA_ROOT:
        raise ValueError("data root is not approved")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingest-massive-grouped-daily.sh")
    parser.add_argument("--session-date", required=True)
    parser.add_argument("--identity-as-of-date", required=True)
    parser.add_argument("--data-root", required=True)
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
        session_date = parse_date(args.session_date, name="session-date")
        identity_date = parse_date(args.identity_as_of_date, name="identity-as-of-date")
        if session_date != identity_date:
            raise ValueError("session and identity dates must match")
        data_root = parse_data_root(args.data_root)
    except (SystemExit, ValueError) as exc:
        if not isinstance(exc, SystemExit):
            print(f"error={exc}", file=sys.stderr)
            return 2
        return int(exc.code) if isinstance(exc.code, int) else 2
    print("provider=massive")
    print(f"endpoint={ENDPOINT_TEMPLATE.format(session_date=session_date.isoformat())}")
    print(f"session_date={session_date.isoformat()}")
    print("request_limit=1")
    print("adjusted=false")
    try:
        config = load_massive_provider_config_from_file()
        result = ingest_grouped_daily(
            config=config,
            transport=MassiveUrllibTransport(),
            session_date=session_date,
            identity_as_of_date=identity_date,
            data_root=data_root,
        )
    except MassiveCredentialFileError:
        print("status=credential-boundary-error")
        return 1
    except MassiveTransportResponseError as exc:
        print(
            "status=rate-limited"
            if exc.status_code == 429
            else "status=authentication-or-entitlement-failed"
            if exc.status_code in {401, 403}
            else "status=http-error"
        )
        return 1
    except MassiveTransportTimeoutError:
        print("status=timeout")
        return 1
    except MassiveTransportUnavailableError:
        print("status=unavailable")
        return 1
    except MassiveTransportDataError:
        print("status=malformed-response")
        return 1
    except Exception as exc:
        print("status=failed")
        print(f"failure_class={exc.__class__.__name__}")
        return 1
    for line in result.safe_lines():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
