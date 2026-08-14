"""Safe one-request Massive Grouped Daily inspection CLI."""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Mapping, Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import EodPriceBarV1
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

GROUPED_DAILY_ENDPOINT_TEMPLATE = "/v2/aggs/grouped/locale/us/market/stocks/{session_date}"
AUTHORIZED_SESSION_DATE = date(2026, 8, 13)
MARKET_TIMEZONE = ZoneInfo("America/New_York")


class IdentityResolver(Protocol):
    """Resolve provider ticker symbols to canonical instrument IDs."""

    def resolve(self, ticker: str) -> UUID | None:
        """Return a canonical instrument_id or None when unresolved."""
        ...


@dataclass(frozen=True)
class MappingIdentityResolver:
    """Deterministic in-memory resolver used by local tests only."""

    ticker_to_instrument_id: Mapping[str, UUID]

    def resolve(self, ticker: str) -> UUID | None:
        return self.ticker_to_instrument_id.get(ticker.strip().upper())


@dataclass(frozen=True)
class GroupedDailyInspectionResult:
    """Safe aggregate inspection summary for one Grouped Daily response."""

    provider: str
    endpoint: str
    session_date: date
    request_count: int
    adjusted: bool
    raw_result_count: int
    unique_ticker_count: int
    duplicate_ticker_count: int
    valid_ohlcv_count: int
    invalid_record_count: int
    missing_open_count: int
    missing_high_count: int
    missing_low_count: int
    missing_close_count: int
    missing_volume_count: int
    missing_vwap_count: int
    missing_trade_count: int
    zero_volume_count: int
    nonpositive_price_count: int
    ohlc_consistency_failure_count: int
    timestamp_session_mismatch_count: int
    numeric_conversion_failure_count: int
    identity_resolved_count: int
    identity_unresolved_count: int
    canonical_mapping_ready_count: int
    canonical_mapping_failed_count: int
    results_count_mismatch: bool
    publish_ready: bool
    status: str

    def safe_lines(self) -> tuple[str, ...]:
        pairs = (
            ("provider", self.provider),
            ("endpoint", self.endpoint),
            ("session_date", self.session_date.isoformat()),
            ("request_count", self.request_count),
            ("adjusted", str(self.adjusted).lower()),
            ("raw_result_count", self.raw_result_count),
            ("unique_ticker_count", self.unique_ticker_count),
            ("duplicate_ticker_count", self.duplicate_ticker_count),
            ("valid_ohlcv_count", self.valid_ohlcv_count),
            ("invalid_record_count", self.invalid_record_count),
            ("missing_open_count", self.missing_open_count),
            ("missing_high_count", self.missing_high_count),
            ("missing_low_count", self.missing_low_count),
            ("missing_close_count", self.missing_close_count),
            ("missing_volume_count", self.missing_volume_count),
            ("missing_vwap_count", self.missing_vwap_count),
            ("missing_trade_count", self.missing_trade_count),
            ("zero_volume_count", self.zero_volume_count),
            ("nonpositive_price_count", self.nonpositive_price_count),
            ("ohlc_consistency_failure_count", self.ohlc_consistency_failure_count),
            ("timestamp_session_mismatch_count", self.timestamp_session_mismatch_count),
            ("numeric_conversion_failure_count", self.numeric_conversion_failure_count),
            ("identity_resolved_count", self.identity_resolved_count),
            ("identity_unresolved_count", self.identity_unresolved_count),
            ("canonical_mapping_ready_count", self.canonical_mapping_ready_count),
            ("canonical_mapping_failed_count", self.canonical_mapping_failed_count),
            ("results_count_mismatch", str(self.results_count_mismatch).lower()),
            ("publish_ready", str(self.publish_ready).lower()),
            ("status", self.status),
        )
        return tuple(f"{key}={value}" for key, value in pairs)


@dataclass
class _Counters:
    raw_result_count: int = 0
    unique_ticker_count: int = 0
    duplicate_ticker_count: int = 0
    valid_ohlcv_count: int = 0
    invalid_record_count: int = 0
    missing_open_count: int = 0
    missing_high_count: int = 0
    missing_low_count: int = 0
    missing_close_count: int = 0
    missing_volume_count: int = 0
    missing_vwap_count: int = 0
    missing_trade_count: int = 0
    zero_volume_count: int = 0
    nonpositive_price_count: int = 0
    ohlc_consistency_failure_count: int = 0
    timestamp_session_mismatch_count: int = 0
    numeric_conversion_failure_count: int = 0
    identity_resolved_count: int = 0
    identity_unresolved_count: int = 0
    canonical_mapping_ready_count: int = 0
    canonical_mapping_failed_count: int = 0


def inspect_grouped_daily_session(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    session_date: date,
    identity_resolver: IdentityResolver | None = None,
    ingested_at: datetime | None = None,
) -> GroupedDailyInspectionResult:
    """Inspect one Massive Grouped Daily response in memory without publishing."""

    endpoint = GROUPED_DAILY_ENDPOINT_TEMPLATE.format(session_date=session_date.isoformat())
    response = transport.get_json(
        endpoint,
        params={"adjusted": False},
        api_key=config.api_key,
        timeout_seconds=config.request_timeout_seconds,
        base_url=config.base_url,
    )
    return inspect_grouped_daily_payload(
        response,
        endpoint=endpoint,
        session_date=session_date,
        identity_resolver=identity_resolver,
        ingested_at=ingested_at or datetime.now(UTC),
    )


def inspect_grouped_daily_payload(
    payload: Mapping[str, object],
    *,
    endpoint: str,
    session_date: date,
    identity_resolver: IdentityResolver | None = None,
    ingested_at: datetime | None = None,
) -> GroupedDailyInspectionResult:
    """Inspect an already-loaded Grouped Daily payload without network access."""

    status = _payload_status(payload)
    results = payload.get("results")
    if not isinstance(results, list):
        return _empty_result(endpoint=endpoint, session_date=session_date, status="malformed-results")
    counters = _Counters(raw_result_count=len(results))
    seen_tickers: set[str] = set()
    duplicate_tickers: set[str] = set()
    fixed_ingested_at = ingested_at or datetime.now(UTC)
    for record in results:
        if not isinstance(record, Mapping):
            counters.invalid_record_count += 1
            continue
        _inspect_record(
            record,
            counters=counters,
            seen_tickers=seen_tickers,
            duplicate_tickers=duplicate_tickers,
            session_date=session_date,
            identity_resolver=identity_resolver,
            ingested_at=fixed_ingested_at,
        )
    counters.unique_ticker_count = len(seen_tickers)
    counters.duplicate_ticker_count = len(duplicate_tickers)
    expected_count = _provider_result_count(payload)
    results_count_mismatch = expected_count is not None and expected_count != len(results)
    if len(results) == 0 and status == "ok":
        status = "empty-results"
    if results_count_mismatch and status == "ok":
        status = "results-count-mismatch"
    if counters.identity_unresolved_count > 0 and counters.canonical_mapping_ready_count == 0 and status == "ok":
        status = "identity-resolution-blocked"
    return GroupedDailyInspectionResult(
        provider=MASSIVE_PROVIDER_ID,
        endpoint=endpoint,
        session_date=session_date,
        request_count=1,
        adjusted=False,
        raw_result_count=counters.raw_result_count,
        unique_ticker_count=counters.unique_ticker_count,
        duplicate_ticker_count=counters.duplicate_ticker_count,
        valid_ohlcv_count=counters.valid_ohlcv_count,
        invalid_record_count=counters.invalid_record_count,
        missing_open_count=counters.missing_open_count,
        missing_high_count=counters.missing_high_count,
        missing_low_count=counters.missing_low_count,
        missing_close_count=counters.missing_close_count,
        missing_volume_count=counters.missing_volume_count,
        missing_vwap_count=counters.missing_vwap_count,
        missing_trade_count=counters.missing_trade_count,
        zero_volume_count=counters.zero_volume_count,
        nonpositive_price_count=counters.nonpositive_price_count,
        ohlc_consistency_failure_count=counters.ohlc_consistency_failure_count,
        timestamp_session_mismatch_count=counters.timestamp_session_mismatch_count,
        numeric_conversion_failure_count=counters.numeric_conversion_failure_count,
        identity_resolved_count=counters.identity_resolved_count,
        identity_unresolved_count=counters.identity_unresolved_count,
        canonical_mapping_ready_count=counters.canonical_mapping_ready_count,
        canonical_mapping_failed_count=counters.canonical_mapping_failed_count,
        results_count_mismatch=results_count_mismatch,
        publish_ready=False,
        status=status,
    )


def parse_session_date(value: str, *, today: date | None = None) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("session date must use YYYY-MM-DD") from exc
    if parsed >= (today or datetime.now(UTC).date()):
        raise ValueError("session date must be a completed historical date")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="inspect-massive-grouped-daily.sh",
        description="Run one safe Massive Grouped Daily inspection request.",
    )
    parser.add_argument("--session-date", required=True, help="Completed historical session date, YYYY-MM-DD")
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    try:
        session_date = parse_session_date(args.session_date)
    except ValueError as exc:
        print(f"error={exc}", file=sys.stderr)
        return 2
    if session_date != AUTHORIZED_SESSION_DATE:
        print("error=session-date-not-authorized-for-this-operation", file=sys.stderr)
        return 2
    try:
        config = load_massive_provider_config_from_file()
        result = inspect_grouped_daily_session(
            config=config,
            transport=MassiveUrllibTransport(),
            session_date=session_date,
        )
    except MassiveCredentialFileError:
        _print_failure(session_date=session_date, status="credential-boundary-error", request_count=0)
        return 1
    except MassiveTransportResponseError as exc:
        if exc.status_code == 429:
            status = "rate-limited"
        elif exc.status_code in {401, 403}:
            status = "authentication-or-entitlement-failed"
        else:
            status = "http-error"
        _print_failure(session_date=session_date, status=status, request_count=1)
        return 1
    except MassiveTransportTimeoutError:
        _print_failure(session_date=session_date, status="timeout", request_count=1)
        return 1
    except MassiveTransportUnavailableError:
        _print_failure(session_date=session_date, status="unavailable", request_count=1)
        return 1
    except MassiveTransportDataError:
        _print_failure(session_date=session_date, status="malformed-response", request_count=1)
        return 1
    for line in result.safe_lines():
        print(line)
    return 0


def _inspect_record(
    record: Mapping[str, object],
    *,
    counters: _Counters,
    seen_tickers: set[str],
    duplicate_tickers: set[str],
    session_date: date,
    identity_resolver: IdentityResolver | None,
    ingested_at: datetime,
) -> None:
    ticker = _ticker(record.get("T") or record.get("ticker"))
    if ticker is None:
        counters.invalid_record_count += 1
        return
    if ticker in seen_tickers:
        duplicate_tickers.add(ticker)
    seen_tickers.add(ticker)

    open_value = _required_decimal(record, "o", counters, "missing_open_count")
    high_value = _required_decimal(record, "h", counters, "missing_high_count")
    low_value = _required_decimal(record, "l", counters, "missing_low_count")
    close_value = _required_decimal(record, "c", counters, "missing_close_count")
    volume_value = _required_int(record, "v", counters, "missing_volume_count")
    vwap_value = _optional_decimal(record, "vw", counters, "missing_vwap_count")
    trade_count_value = _optional_int(record, "n", counters, "missing_trade_count")
    timestamp_value = _timestamp_matches_session(record.get("t"), session_date)
    if not timestamp_value:
        counters.timestamp_session_mismatch_count += 1

    prices = (open_value, high_value, low_value, close_value)
    prices_present = all(value is not None for value in prices)
    prices_positive = prices_present and all(value > 0 for value in prices if value is not None)
    if prices_present and not prices_positive:
        counters.nonpositive_price_count += 1
    ohlc_consistent = False
    if prices_present and prices_positive:
        assert open_value is not None and high_value is not None and low_value is not None and close_value is not None
        ohlc_consistent = high_value >= open_value and high_value >= close_value and high_value >= low_value and low_value <= open_value and low_value <= close_value and low_value <= high_value
        if not ohlc_consistent:
            counters.ohlc_consistency_failure_count += 1
    if volume_value == 0:
        counters.zero_volume_count += 1

    valid_ohlcv = bool(prices_present and prices_positive and ohlc_consistent and volume_value is not None and volume_value >= 0 and timestamp_value)
    if valid_ohlcv:
        counters.valid_ohlcv_count += 1
    else:
        counters.invalid_record_count += 1

    instrument_id = identity_resolver.resolve(ticker) if identity_resolver is not None else None
    if instrument_id is None:
        counters.identity_unresolved_count += 1
        return
    counters.identity_resolved_count += 1
    if not valid_ohlcv:
        counters.canonical_mapping_failed_count += 1
        return
    try:
        assert open_value is not None and high_value is not None and low_value is not None and close_value is not None and volume_value is not None
        EodPriceBarV1(
            instrument_id=instrument_id,
            session_date=session_date,
            open=open_value,
            high=high_value,
            low=low_value,
            close=close_value,
            volume=volume_value,
            vwap=vwap_value,
            trade_count=trade_count_value,
            notional=Decimal("0"),
            currency="USD",
            split_adjustment_factor=Decimal("1"),
            dividend_adjustment_factor=Decimal("1"),
            total_return_adjustment_factor=Decimal("1"),
            adjusted_close=close_value,
            source=MASSIVE_PROVIDER_ID,
            source_record_id=None,
            ingested_at=ingested_at,
            revision=1,
            is_latest_revision=True,
            quality_status=QualityStatus.VALID,
            quality_flags=("adjustment_factors_unverified", "inspection_only"),
        )
    except (ValidationError, ValueError):
        counters.canonical_mapping_failed_count += 1
    else:
        counters.canonical_mapping_ready_count += 1


def _payload_status(payload: Mapping[str, object]) -> str:
    status = payload.get("status")
    if status is None:
        return "ok"
    if isinstance(status, str) and status.strip().upper() in {"OK", "DELAYED", "SUCCESS"}:
        return "ok"
    return "provider-status-not-ok"


def _provider_result_count(payload: Mapping[str, object]) -> int | None:
    for key in ("resultsCount", "results_count"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return None


def _ticker(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized or None


def _required_decimal(record: Mapping[str, object], key: str, counters: _Counters, missing_attr: str) -> Decimal | None:
    value = record.get(key)
    if value is None:
        setattr(counters, missing_attr, getattr(counters, missing_attr) + 1)
        return None
    return _decimal(value, counters)


def _optional_decimal(record: Mapping[str, object], key: str, counters: _Counters, missing_attr: str) -> Decimal | None:
    value = record.get(key)
    if value is None:
        setattr(counters, missing_attr, getattr(counters, missing_attr) + 1)
        return None
    return _decimal(value, counters)


def _decimal(value: object, counters: _Counters) -> Decimal | None:
    if isinstance(value, bool):
        counters.numeric_conversion_failure_count += 1
        return None
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        counters.numeric_conversion_failure_count += 1
        return None
    if not decimal.is_finite():
        counters.numeric_conversion_failure_count += 1
        return None
    return decimal


def _required_int(record: Mapping[str, object], key: str, counters: _Counters, missing_attr: str) -> int | None:
    value = record.get(key)
    if value is None:
        setattr(counters, missing_attr, getattr(counters, missing_attr) + 1)
        return None
    return _int(value, counters)


def _optional_int(record: Mapping[str, object], key: str, counters: _Counters, missing_attr: str) -> int | None:
    value = record.get(key)
    if value is None:
        setattr(counters, missing_attr, getattr(counters, missing_attr) + 1)
        return None
    return _int(value, counters)


def _int(value: object, counters: _Counters) -> int | None:
    if isinstance(value, bool):
        counters.numeric_conversion_failure_count += 1
        return None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            counters.numeric_conversion_failure_count += 1
            return None
        parsed = int(value)
    elif isinstance(value, Decimal):
        if not value.is_finite() or value != value.to_integral_value():
            counters.numeric_conversion_failure_count += 1
            return None
        parsed = int(value)
    elif isinstance(value, str):
        try:
            decimal = Decimal(value.strip())
        except InvalidOperation:
            counters.numeric_conversion_failure_count += 1
            return None
        if not decimal.is_finite() or decimal != decimal.to_integral_value():
            counters.numeric_conversion_failure_count += 1
            return None
        parsed = int(decimal)
    else:
        counters.numeric_conversion_failure_count += 1
        return None
    if parsed < 0:
        counters.numeric_conversion_failure_count += 1
        return None
    return parsed


def _timestamp_matches_session(value: object, session_date: date) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        timestamp_ms = int(value)
    except (TypeError, ValueError):
        return False
    timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
    return timestamp.astimezone(MARKET_TIMEZONE).date() == session_date


def _empty_result(*, endpoint: str, session_date: date, status: str) -> GroupedDailyInspectionResult:
    return GroupedDailyInspectionResult(
        provider=MASSIVE_PROVIDER_ID,
        endpoint=endpoint,
        session_date=session_date,
        request_count=1,
        adjusted=False,
        raw_result_count=0,
        unique_ticker_count=0,
        duplicate_ticker_count=0,
        valid_ohlcv_count=0,
        invalid_record_count=0,
        missing_open_count=0,
        missing_high_count=0,
        missing_low_count=0,
        missing_close_count=0,
        missing_volume_count=0,
        missing_vwap_count=0,
        missing_trade_count=0,
        zero_volume_count=0,
        nonpositive_price_count=0,
        ohlc_consistency_failure_count=0,
        timestamp_session_mismatch_count=0,
        numeric_conversion_failure_count=0,
        identity_resolved_count=0,
        identity_unresolved_count=0,
        canonical_mapping_ready_count=0,
        canonical_mapping_failed_count=0,
        results_count_mismatch=False,
        publish_ready=False,
        status=status,
    )


def _print_failure(*, session_date: date, status: str, request_count: int) -> None:
    base = _empty_result(
        endpoint=GROUPED_DAILY_ENDPOINT_TEMPLATE.format(session_date=session_date.isoformat()),
        session_date=session_date,
        status=status,
    )
    result = GroupedDailyInspectionResult(**{**base.__dict__, "request_count": request_count})
    for line in result.safe_lines():
        print(line)


if __name__ == "__main__":
    raise SystemExit(main())
