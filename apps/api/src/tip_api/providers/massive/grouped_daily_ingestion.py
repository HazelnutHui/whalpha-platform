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
from typing import Mapping
from uuid import UUID
from zoneinfo import ZoneInfo

import pyarrow.parquet as pq

from tip_api.persistence.parquet.instrument_master_snapshot import (
    INSTRUMENT_MASTER_ARROW_SCHEMA,
    PROVIDER_IDENTITY_ARROW_SCHEMA,
    PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA,
    _identity_table_to_rows,
    _instrument_table_to_rows,
    _resolver_table_to_rows,
    records_fingerprint,
)
from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import EodPriceBarV1
from tip_api.persistence.parquet.eod_bars import ParquetEodPriceBarRepository
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
class GroupedDailyIngestionResult:
    provider: str
    endpoint: str
    session_date: date
    identity_as_of_date: date
    request_count: int
    adjusted: bool
    raw_result_count: int
    unique_raw_ticker_count: int
    exact_duplicate_count: int
    conflicting_duplicate_count: int
    resolved_eligible_bar_count: int
    unresolved_eligible_bar_count: int
    expected_exclusion_bar_count: int
    ambiguous_bar_count: int
    rejected_identity_bar_count: int
    missing_identity_bar_count: int
    identity_eligible_denominator: int
    identity_resolved_coverage_ratio: float
    required_field_missing_count: int
    optional_vwap_missing_count: int
    optional_trade_count_missing_count: int
    numeric_conversion_failure_count: int
    nonpositive_price_count: int
    ohlc_consistency_failure_count: int
    negative_volume_count: int
    zero_volume_count: int
    timestamp_session_mismatch_count: int
    canonical_validation_failure_count: int
    canonical_bar_count: int
    written_record_count: int
    content_sha256: str | None
    partition_path: Path | None
    quality_gate_passed: bool
    quality_gate_failures: tuple[str, ...]
    status: str

    def safe_lines(self) -> tuple[str, ...]:
        pairs = (
            ("provider", self.provider), ("endpoint", self.endpoint), ("session_date", self.session_date.isoformat()),
            ("identity_as_of_date", self.identity_as_of_date.isoformat()), ("request_count", self.request_count),
            ("adjusted", str(self.adjusted).lower()), ("raw_result_count", self.raw_result_count),
            ("unique_raw_ticker_count", self.unique_raw_ticker_count), ("exact_duplicate_count", self.exact_duplicate_count),
            ("conflicting_duplicate_count", self.conflicting_duplicate_count), ("resolved_eligible_bar_count", self.resolved_eligible_bar_count),
            ("unresolved_eligible_bar_count", self.unresolved_eligible_bar_count), ("expected_exclusion_bar_count", self.expected_exclusion_bar_count),
            ("ambiguous_bar_count", self.ambiguous_bar_count), ("rejected_identity_bar_count", self.rejected_identity_bar_count),
            ("missing_identity_bar_count", self.missing_identity_bar_count), ("identity_eligible_denominator", self.identity_eligible_denominator),
            ("identity_resolved_coverage_ratio", f"{self.identity_resolved_coverage_ratio:.6f}"),
            ("required_field_missing_count", self.required_field_missing_count), ("optional_vwap_missing_count", self.optional_vwap_missing_count),
            ("optional_trade_count_missing_count", self.optional_trade_count_missing_count), ("numeric_conversion_failure_count", self.numeric_conversion_failure_count),
            ("nonpositive_price_count", self.nonpositive_price_count), ("ohlc_consistency_failure_count", self.ohlc_consistency_failure_count),
            ("negative_volume_count", self.negative_volume_count), ("zero_volume_count", self.zero_volume_count),
            ("timestamp_session_mismatch_count", self.timestamp_session_mismatch_count), ("canonical_validation_failure_count", self.canonical_validation_failure_count),
            ("canonical_bar_count", self.canonical_bar_count), ("written_record_count", self.written_record_count),
            ("content_sha256", self.content_sha256 or ""), ("quality_gate_passed", str(self.quality_gate_passed).lower()),
            ("quality_gate_failures", ",".join(self.quality_gate_failures)), ("publish_ready", str(self.quality_gate_passed).lower()),
            ("status", self.status),
        )
        return tuple(f"{k}={v}" for k, v in pairs)


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
    _verify_table(instrument_table, expected_schema=INSTRUMENT_MASTER_ARROW_SCHEMA, expected_count=manifest.get("instrument_count"), expected_fingerprint=manifest.get("instrument_content_sha256"), table_to_rows=_instrument_table_to_rows)
    _verify_table(identity_table, expected_schema=PROVIDER_IDENTITY_ARROW_SCHEMA, expected_count=manifest.get("identity_count"), expected_fingerprint=manifest.get("identity_content_sha256"), table_to_rows=_identity_table_to_rows)
    _verify_table(resolver_table, expected_schema=PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA, expected_count=manifest.get("resolver_count"), expected_fingerprint=manifest.get("resolver_content_sha256"), table_to_rows=_resolver_table_to_rows)
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
        # resolved rows and exact duplicates can repeat; non-resolved categories are only needed for classification.
        current = status.get(ticker)
        next_status = str(row.get("resolution_status"))
        qflags = tuple(row.get("quality_flags") or ())
        if current is None or current == "resolved":
            status[ticker] = next_status
            flags[ticker] = qflags
    if len(resolver) != manifest.get("resolver_count"):
        raise RuntimeError("resolver count mismatch")
    return IdentitySnapshot(as_of_date=as_of_date, provider_id=provider_id, resolver=resolver, identity_status=status, identity_flags=flags, instrument_ids=instrument_ids, manifest=manifest)


def ingest_grouped_daily(*, config: MassiveProviderConfig, transport: MassiveHttpTransport, session_date: date, identity_as_of_date: date, data_root: Path, ingested_at: datetime | None = None) -> GroupedDailyIngestionResult:
    identity = load_identity_snapshot(data_root, provider_id=MASSIVE_PROVIDER_ID, as_of_date=identity_as_of_date)
    endpoint = ENDPOINT_TEMPLATE.format(session_date=session_date.isoformat())
    response = transport.get_json(endpoint, params={"adjusted": False}, api_key=config.api_key, timeout_seconds=config.request_timeout_seconds, base_url=config.base_url)
    return process_grouped_daily_payload(response, identity=identity, session_date=session_date, endpoint=endpoint, data_root=data_root, ingested_at=ingested_at or datetime.now(UTC), publish=True)


def process_grouped_daily_payload(payload: Mapping[str, object], *, identity: IdentitySnapshot, session_date: date, endpoint: str, data_root: Path, ingested_at: datetime, publish: bool) -> GroupedDailyIngestionResult:
    results = payload.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Grouped Daily results must be a list")
    by_ticker: dict[str, list[Mapping[str, object]]] = {}
    for item in results:
        if not isinstance(item, Mapping):
            continue
        try:
            ticker = _ticker(item.get("T") or item.get("ticker"))
        except RuntimeError:
            ticker = "<missing>"
        by_ticker.setdefault(ticker, []).append(item)
    exact_duplicate_count = 0
    conflicting_duplicate_count = 0
    unique_records: list[Mapping[str, object]] = []
    conflicted: set[str] = set()
    for ticker, items in by_ticker.items():
        sigs = {_bar_signature(item) for item in items}
        if len(items) > 1:
            if len(sigs) == 1:
                exact_duplicate_count += len(items) - 1
            else:
                conflicting_duplicate_count += len(items)
                conflicted.add(ticker)
                continue
        unique_records.append(items[0])
    counters = _Counters(raw_result_count=len(results), unique_raw_ticker_count=len(by_ticker), exact_duplicate_count=exact_duplicate_count, conflicting_duplicate_count=conflicting_duplicate_count)
    bars: list[EodPriceBarV1] = []
    for item in unique_records:
        _process_record(item, identity=identity, session_date=session_date, ingested_at=ingested_at, counters=counters, bars=bars, conflicted=conflicted)
    denominator = counters.resolved_eligible_bar_count + counters.unresolved_eligible_bar_count + counters.ambiguous_bar_count + counters.missing_identity_bar_count
    coverage = counters.resolved_eligible_bar_count / denominator if denominator else 0.0
    failures = _gate_failures(counters, coverage, request_count=1, adjusted=False, canonical_count=len(bars))
    write_result = None
    if publish and not failures:
        write_result = ParquetEodPriceBarRepository(data_root).publish_session(tuple(bars), session_date=session_date, provider_id=MASSIVE_PROVIDER_ID, quality_summary=counters.quality_summary(coverage), identity_snapshot={"as_of_date": identity.as_of_date.isoformat(), "provider_id": identity.provider_id, "snapshot_content_sha256": identity.manifest.get("snapshot_content_sha256"), "resolver_count": len(identity.resolver)})
    return GroupedDailyIngestionResult(provider=MASSIVE_PROVIDER_ID, endpoint=endpoint, session_date=session_date, identity_as_of_date=identity.as_of_date, request_count=1, adjusted=False, raw_result_count=counters.raw_result_count, unique_raw_ticker_count=counters.unique_raw_ticker_count, exact_duplicate_count=counters.exact_duplicate_count, conflicting_duplicate_count=counters.conflicting_duplicate_count, resolved_eligible_bar_count=counters.resolved_eligible_bar_count, unresolved_eligible_bar_count=counters.unresolved_eligible_bar_count, expected_exclusion_bar_count=counters.expected_exclusion_bar_count, ambiguous_bar_count=counters.ambiguous_bar_count, rejected_identity_bar_count=counters.rejected_identity_bar_count, missing_identity_bar_count=counters.missing_identity_bar_count, identity_eligible_denominator=denominator, identity_resolved_coverage_ratio=coverage, required_field_missing_count=counters.required_field_missing_count, optional_vwap_missing_count=counters.optional_vwap_missing_count, optional_trade_count_missing_count=counters.optional_trade_count_missing_count, numeric_conversion_failure_count=counters.numeric_conversion_failure_count, nonpositive_price_count=counters.nonpositive_price_count, ohlc_consistency_failure_count=counters.ohlc_consistency_failure_count, negative_volume_count=counters.negative_volume_count, zero_volume_count=counters.zero_volume_count, timestamp_session_mismatch_count=counters.timestamp_session_mismatch_count, canonical_validation_failure_count=counters.canonical_validation_failure_count, canonical_bar_count=len(bars), written_record_count=write_result.written_record_count if write_result else 0, content_sha256=write_result.content_sha256 if write_result else None, partition_path=write_result.partition_path if write_result else None, quality_gate_passed=not failures, quality_gate_failures=failures, status=write_result.status if write_result else "quality_gate_failed")


@dataclass
class _Counters:
    raw_result_count: int = 0; unique_raw_ticker_count: int = 0; exact_duplicate_count: int = 0; conflicting_duplicate_count: int = 0
    resolved_eligible_bar_count: int = 0; unresolved_eligible_bar_count: int = 0; expected_exclusion_bar_count: int = 0; ambiguous_bar_count: int = 0; rejected_identity_bar_count: int = 0; missing_identity_bar_count: int = 0
    required_field_missing_count: int = 0; optional_vwap_missing_count: int = 0; optional_trade_count_missing_count: int = 0; numeric_conversion_failure_count: int = 0; nonpositive_price_count: int = 0; ohlc_consistency_failure_count: int = 0; negative_volume_count: int = 0; zero_volume_count: int = 0; timestamp_session_mismatch_count: int = 0; canonical_validation_failure_count: int = 0
    def quality_summary(self, coverage: float) -> dict[str, object]:
        return {k: v for k, v in self.__dict__.items()} | {"identity_resolved_coverage_ratio": coverage}


def _process_record(item: Mapping[str, object], *, identity: IdentitySnapshot, session_date: date, ingested_at: datetime, counters: _Counters, bars: list[EodPriceBarV1], conflicted: set[str]) -> None:
    try: ticker = _ticker(item.get("T") or item.get("ticker"))
    except RuntimeError: counters.required_field_missing_count += 1; return
    if ticker in conflicted: return
    status = identity.identity_status.get(ticker)
    instrument_id = identity.resolver.get(ticker)
    if instrument_id is None:
        if status == "unresolved": counters.unresolved_eligible_bar_count += 1
        elif status == "excluded": counters.expected_exclusion_bar_count += 1
        elif status == "ambiguous": counters.ambiguous_bar_count += 1
        elif status == "rejected": counters.rejected_identity_bar_count += 1
        else: counters.missing_identity_bar_count += 1
        return
    counters.resolved_eligible_bar_count += 1
    try:
        open_ = _decimal_required(item.get("o")); high = _decimal_required(item.get("h")); low = _decimal_required(item.get("l")); close = _decimal_required(item.get("c")); volume = _int_required(item.get("v"))
    except _MissingRequired: counters.required_field_missing_count += 1; return
    except _NumericFailure: counters.numeric_conversion_failure_count += 1; return
    vwap = _optional_decimal(item.get("vw")); trade_count = _optional_int(item.get("n"))
    if item.get("vw") is None: counters.optional_vwap_missing_count += 1
    if item.get("n") is None: counters.optional_trade_count_missing_count += 1
    if min(open_, high, low, close) <= 0: counters.nonpositive_price_count += 1; return
    if volume < 0: counters.negative_volume_count += 1; return
    if volume == 0: counters.zero_volume_count += 1
    if high < open_ or high < close or high < low or low > open_ or low > close or low > high: counters.ohlc_consistency_failure_count += 1; return
    if _session_date_from_timestamp(item.get("t")) != session_date: counters.timestamp_session_mismatch_count += 1; return
    flags=["adjustment_factors_unverified"]
    if vwap is None: flags.append("missing_vwap")
    if trade_count is None: flags.append("missing_trade_count")
    if volume == 0: flags.append("zero_volume")
    try:
        bars.append(EodPriceBarV1(instrument_id=instrument_id, session_date=session_date, open=open_, high=high, low=low, close=close, volume=volume, vwap=vwap, trade_count=trade_count, notional=Decimal("0"), currency="USD", split_adjustment_factor=Decimal("1"), dividend_adjustment_factor=Decimal("1"), total_return_adjustment_factor=Decimal("1"), adjusted_close=close, source=MASSIVE_PROVIDER_ID, source_record_id=f"{ticker}:{item.get('t')}", ingested_at=ingested_at, revision=1, is_latest_revision=True, quality_status=QualityStatus.VALID, quality_flags=tuple(flags)))
    except ValidationError:
        counters.canonical_validation_failure_count += 1


def _gate_failures(c: _Counters, coverage: float, *, request_count: int, adjusted: bool, canonical_count: int) -> tuple[str, ...]:
    failures=[]
    if c.raw_result_count <= 5000: failures.append("raw_result_count_below_gate")
    if request_count != 1: failures.append("request_count_not_one")
    if adjusted: failures.append("adjusted_not_false")
    for field in ("conflicting_duplicate_count","numeric_conversion_failure_count","required_field_missing_count","nonpositive_price_count","ohlc_consistency_failure_count","negative_volume_count","timestamp_session_mismatch_count","canonical_validation_failure_count"):
        if getattr(c, field) != 0: failures.append(f"{field}_nonzero")
    if coverage < 0.80: failures.append("identity_resolved_coverage_below_gate")
    if canonical_count <= 5000: failures.append("canonical_bar_count_below_gate")
    return tuple(failures)


def _verify_table(table, *, expected_schema, expected_count, expected_fingerprint, table_to_rows) -> None:
    if table.schema != expected_schema:
        raise RuntimeError("identity snapshot schema mismatch")
    if not isinstance(expected_count, int) or table.num_rows != expected_count:
        raise RuntimeError("identity snapshot row count mismatch")
    if not isinstance(expected_fingerprint, str) or records_fingerprint(table_to_rows(table)) != expected_fingerprint:
        raise RuntimeError("identity snapshot fingerprint mismatch")


def _ticker(value: object) -> str:
    if not isinstance(value, str) or not value.strip(): raise RuntimeError("missing ticker")
    return value.strip().upper()

def _bar_signature(item: Mapping[str, object]) -> tuple[object, ...]:
    return tuple(item.get(k) for k in ("T","ticker","o","h","l","c","v","vw","n","t"))
class _MissingRequired(Exception): pass
class _NumericFailure(Exception): pass

def _decimal_required(value: object) -> Decimal:
    if value is None: raise _MissingRequired()
    return _decimal(value)
def _optional_decimal(value: object) -> Decimal | None:
    if value is None: return None
    return _decimal(value)
def _decimal(value: object) -> Decimal:
    if isinstance(value, bool): raise _NumericFailure()
    if isinstance(value, float) and not math.isfinite(value): raise _NumericFailure()
    try: d=Decimal(str(value))
    except (InvalidOperation, ValueError): raise _NumericFailure()
    if not d.is_finite(): raise _NumericFailure()
    return d
def _int_required(value: object) -> int:
    if value is None: raise _MissingRequired()
    return _int(value)
def _optional_int(value: object) -> int | None:
    if value is None: return None
    return _int(value)
def _int(value: object) -> int:
    d=_decimal(value)
    if d != d.to_integral_value(): raise _NumericFailure()
    return int(d)
def _session_date_from_timestamp(value: object) -> date | None:
    try: ms=_int_required(value)
    except Exception: return None
    return datetime.fromtimestamp(ms/1000, tz=UTC).astimezone(MARKET_TZ).date()

def _safe_root(root: Path) -> Path:
    if root != APPROVED_DATA_ROOT and not str(root).startswith("/tmp/"):
        raise RuntimeError("data root is not approved")
    if root.exists() and root.is_symlink(): raise RuntimeError("data root must not be a symlink")
    return root.resolve()
def _read_manifest(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file(): raise RuntimeError("manifest path invalid")
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict): raise RuntimeError("manifest must be object")
    return data

def parse_date(value: str, *, name: str) -> date:
    try: parsed=date.fromisoformat(value)
    except ValueError as exc: raise ValueError(f"{name} must use YYYY-MM-DD") from exc
    if parsed != AUTHORIZED_SESSION_DATE: raise ValueError(f"{name} is not authorized")
    return parsed

def parse_data_root(value: str) -> Path:
    path=Path(value)
    if path != APPROVED_DATA_ROOT: raise ValueError("data root is not approved")
    return path

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(prog="ingest-massive-grouped-daily.sh")
    parser.add_argument("--session-date", required=True); parser.add_argument("--identity-as-of-date", required=True); parser.add_argument("--data-root", required=True)
    try:
        args=parser.parse_args(sys.argv[1:] if argv is None else argv)
        session_date=parse_date(args.session_date, name="session-date"); identity_date=parse_date(args.identity_as_of_date, name="identity-as-of-date")
        if session_date != identity_date: raise ValueError("session and identity dates must match")
        data_root=parse_data_root(args.data_root)
    except (SystemExit, ValueError) as exc:
        if not isinstance(exc, SystemExit): print(f"error={exc}", file=sys.stderr); return 2
        return int(exc.code) if isinstance(exc.code, int) else 2
    print("provider=massive"); print(f"endpoint={ENDPOINT_TEMPLATE.format(session_date=session_date.isoformat())}"); print(f"session_date={session_date.isoformat()}"); print("request_limit=1"); print("adjusted=false")
    try:
        config=load_massive_provider_config_from_file()
        result=ingest_grouped_daily(config=config, transport=MassiveUrllibTransport(), session_date=session_date, identity_as_of_date=identity_date, data_root=data_root)
    except MassiveCredentialFileError: print("status=credential-boundary-error"); return 1
    except MassiveTransportResponseError as exc: print("status=rate-limited" if exc.status_code==429 else "status=authentication-or-entitlement-failed" if exc.status_code in {401,403} else "status=http-error"); return 1
    except MassiveTransportTimeoutError: print("status=timeout"); return 1
    except MassiveTransportUnavailableError: print("status=unavailable"); return 1
    except MassiveTransportDataError: print("status=malformed-response"); return 1
    except Exception as exc: print("status=failed"); print(f"failure_class={exc.__class__.__name__}"); return 1
    for line in result.safe_lines(): print(line)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
