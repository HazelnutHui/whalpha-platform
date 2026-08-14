"""Massive All Tickers point-in-time Instrument Master snapshot ingestion CLI."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import parse_qsl, urlparse

from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    InstrumentMasterV1,
    InstrumentStatus,
    InstrumentType,
    ProviderInstrumentIdentityV1,
    ResolutionMethod,
    ResolutionStatus,
)
from tip_api.ingestion.instrument_identity import canonical_instrument_id_for_identity, select_stable_identity
from tip_api.ingestion.instrument_master_snapshot import InstrumentMasterSnapshotIngestionService
from tip_api.persistence.parquet.instrument_master_snapshot import ParquetInstrumentMasterSnapshotRepository
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.credential import MassiveCredentialFileError, load_massive_provider_config_from_file
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveParamValue,
    MassiveTransportDataError,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
    MassiveUrllibTransport,
)

AUTHORIZED_AS_OF_DATE = date(2026, 8, 13)
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
REFERENCE_TICKERS_PATH = "/v3/reference/tickers"
MAX_PAGES = 20
MAX_RECORDS = 25000
MIN_REQUEST_INTERVAL_SECONDS = Decimal("15")

Clock = Callable[[], float]
Sleeper = Callable[[float], None]


@dataclass
class FixedIntervalRateLimiter:
    """Synchronous fixed-interval limiter with injectable clock and sleeper."""

    interval_seconds: Decimal = MIN_REQUEST_INTERVAL_SECONDS
    clock: Clock = time.monotonic
    sleeper: Sleeper = time.sleep
    _last_request_at: float | None = None

    def wait_before_request(self) -> None:
        now = self.clock()
        if self._last_request_at is not None:
            elapsed = now - self._last_request_at
            delay = float(self.interval_seconds) - elapsed
            if delay > 0:
                self.sleeper(delay)
                now = self.clock()
        self._last_request_at = now


@dataclass(frozen=True)
class ReferenceSnapshotBuildResult:
    """In-memory build result before persistence."""

    instruments: tuple[InstrumentMasterV1, ...]
    identities: tuple[ProviderInstrumentIdentityV1, ...]
    request_count: int
    raw_record_count: int
    unique_ticker_count: int
    duplicate_ticker_count: int
    resolved_count: int
    unresolved_count: int
    ambiguous_count: int
    rejected_count: int
    pagination_complete: bool


def ingest_massive_instrument_master_snapshot(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    as_of_date: date,
    data_root: Path,
    rate_limiter: FixedIntervalRateLimiter | None = None,
    ingested_at: datetime | None = None,
):
    build = fetch_and_build_snapshot(
        config=config,
        transport=transport,
        as_of_date=as_of_date,
        rate_limiter=rate_limiter or FixedIntervalRateLimiter(),
        ingested_at=ingested_at or datetime.now(UTC),
    )
    service = InstrumentMasterSnapshotIngestionService(
        repository=ParquetInstrumentMasterSnapshotRepository(root=data_root),
    )
    return service.publish_snapshot(
        as_of_date=as_of_date,
        provider_id=MASSIVE_PROVIDER_ID,
        instruments=build.instruments,
        identities=build.identities,
        request_count=build.request_count,
        raw_record_count=build.raw_record_count,
        unique_ticker_count=build.unique_ticker_count,
        duplicate_ticker_count=build.duplicate_ticker_count,
        resolved_count=build.resolved_count,
        unresolved_count=build.unresolved_count,
        ambiguous_count=build.ambiguous_count,
        rejected_count=build.rejected_count,
    )


def fetch_and_build_snapshot(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    as_of_date: date,
    rate_limiter: FixedIntervalRateLimiter,
    ingested_at: datetime,
) -> ReferenceSnapshotBuildResult:
    pages, request_count, pagination_complete = _fetch_reference_pages(
        config=config,
        transport=transport,
        as_of_date=as_of_date,
        rate_limiter=rate_limiter,
    )
    if not pagination_complete:
        raise RuntimeError("Massive reference pagination did not complete")
    raw_records: list[Mapping[str, object]] = []
    for page in pages:
        raw_records.extend(_results(page))
    if len(raw_records) > MAX_RECORDS:
        raise RuntimeError("Massive reference record limit exceeded")
    return build_snapshot_from_payloads(
        payloads=tuple(raw_records),
        as_of_date=as_of_date,
        ingested_at=ingested_at,
        request_count=request_count,
        pagination_complete=pagination_complete,
    )


def build_snapshot_from_payloads(
    *,
    payloads: tuple[Mapping[str, object], ...],
    as_of_date: date,
    ingested_at: datetime,
    request_count: int,
    pagination_complete: bool,
) -> ReferenceSnapshotBuildResult:
    seen_tickers: set[str] = set()
    duplicate_tickers: set[str] = set()
    preliminary: list[_PreliminaryIdentity] = []
    for payload in payloads:
        try:
            preliminary.append(_preliminary_identity(payload, as_of_date=as_of_date, ingested_at=ingested_at))
        except _PayloadRejected as exc:
            preliminary.append(exc.identity)
    for item in preliminary:
        if item.provider_ticker in seen_tickers:
            duplicate_tickers.add(item.provider_ticker)
        seen_tickers.add(item.provider_ticker)

    ambiguous_keys = _ambiguous_identity_keys(preliminary)
    instruments: list[InstrumentMasterV1] = []
    identities: list[ProviderInstrumentIdentityV1] = []
    resolved = unresolved = ambiguous = rejected = 0
    for item in preliminary:
        if item.rejection_flag is not None:
            rejected += 1
            identities.append(item.to_identity(ResolutionStatus.REJECTED, ResolutionMethod.UNRESOLVED, None, (item.rejection_flag,)))
            continue
        if item.stable_identity is None:
            unresolved += 1
            identities.append(item.to_identity(ResolutionStatus.UNRESOLVED, ResolutionMethod.UNRESOLVED, None, ("no_stable_security_identifier",)))
            continue
        if item.stable_identity.key in ambiguous_keys:
            ambiguous += 1
            identities.append(item.to_identity(ResolutionStatus.AMBIGUOUS, ResolutionMethod.UNRESOLVED, None, ("stable_identifier_collision",)))
            continue
        instrument_id = canonical_instrument_id_for_identity(item.stable_identity)
        try:
            instrument = item.to_instrument(instrument_id)
        except ValidationError:
            rejected += 1
            identities.append(item.to_identity(ResolutionStatus.REJECTED, ResolutionMethod.UNRESOLVED, None, ("canonical_validation_failed",)))
            continue
        instruments.append(instrument)
        resolved += 1
        identities.append(item.to_identity(ResolutionStatus.RESOLVED, item.stable_identity.resolution_method, instrument_id, ()))
    return ReferenceSnapshotBuildResult(
        instruments=tuple(sorted(instruments, key=lambda record: (str(record.instrument_id), record.ticker))),
        identities=tuple(sorted(identities, key=lambda record: (record.provider_ticker, record.provider_instrument_id or ""))),
        request_count=request_count,
        raw_record_count=len(payloads),
        unique_ticker_count=len(seen_tickers),
        duplicate_ticker_count=len(duplicate_tickers),
        resolved_count=resolved,
        unresolved_count=unresolved,
        ambiguous_count=ambiguous,
        rejected_count=rejected,
        pagination_complete=pagination_complete,
    )


def _fetch_reference_pages(*, config: MassiveProviderConfig, transport: MassiveHttpTransport, as_of_date: date, rate_limiter: FixedIntervalRateLimiter) -> tuple[tuple[Mapping[str, object], ...], int, bool]:
    pages: list[Mapping[str, object]] = []
    path = REFERENCE_TICKERS_PATH
    params: dict[str, MassiveParamValue] = {
        "market": "stocks",
        "active": True,
        "date": as_of_date.isoformat(),
        "limit": 1000,
        "sort": "ticker",
        "order": "asc",
    }
    seen_requests: set[tuple[str, tuple[tuple[str, MassiveParamValue], ...]]] = set()
    for request_number in range(1, MAX_PAGES + 1):
        request_key = (path, tuple(sorted(params.items())))
        if request_key in seen_requests:
            raise RuntimeError("Massive reference pagination loop detected")
        seen_requests.add(request_key)
        rate_limiter.wait_before_request()
        response = transport.get_json(
            path,
            params=params,
            api_key=config.api_key,
            timeout_seconds=config.request_timeout_seconds,
            base_url=config.base_url,
        )
        _validate_page(response)
        pages.append(response)
        if sum(len(_results(page)) for page in pages) > MAX_RECORDS:
            raise RuntimeError("Massive reference record limit exceeded")
        next_url = response.get("next_url")
        if next_url is None:
            return tuple(pages), request_number, True
        path, params = _next_page_request(next_url, base_url=config.base_url)
    raise RuntimeError("Massive reference page limit exceeded")


def _next_page_request(next_url: object, *, base_url: str) -> tuple[str, dict[str, MassiveParamValue]]:
    if not isinstance(next_url, str) or not next_url.strip():
        raise RuntimeError("Massive reference next_url is invalid")
    parsed = urlparse(next_url)
    base = urlparse(base_url)
    if parsed.netloc and parsed.netloc != base.netloc:
        raise RuntimeError("Massive reference next_url host changed")
    if parsed.path != REFERENCE_TICKERS_PATH:
        raise RuntimeError("Massive reference next_url path changed")
    params: dict[str, MassiveParamValue] = {}
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        if key.lower() == "apikey":
            continue
        params[key] = value
    return parsed.path, params


def _validate_page(page: Mapping[str, object]) -> None:
    results = page.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Massive reference page results must be a list")
    for item in results:
        if not isinstance(item, Mapping):
            raise RuntimeError("Massive reference result item must be an object")


def _results(page: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    results = page.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Massive reference page results must be a list")
    return tuple(item for item in results if isinstance(item, Mapping))


@dataclass(frozen=True)
class _PreliminaryIdentity:
    provider_ticker: str
    name: str | None
    primary_exchange: str | None
    instrument_type: InstrumentType | None
    status: InstrumentStatus | None
    provider_instrument_id: str | None
    composite_figi: str | None
    share_class_figi: str | None
    cik: str | None
    currency: str | None
    valid_to: date | None
    source_updated_at: datetime | None
    as_of_date: date
    ingested_at: datetime
    rejection_flag: str | None = None

    @property
    def stable_identity(self):
        return select_stable_identity(
            share_class_figi=self.share_class_figi,
            composite_figi=self.composite_figi,
            provider_instrument_id=self.provider_instrument_id,
        )

    def to_identity(self, status: ResolutionStatus, method: ResolutionMethod, canonical_id, flags: tuple[str, ...]) -> ProviderInstrumentIdentityV1:
        return ProviderInstrumentIdentityV1(
            provider=MASSIVE_PROVIDER_ID,
            as_of_date=self.as_of_date,
            provider_ticker=self.provider_ticker,
            provider_instrument_id=self.provider_instrument_id,
            composite_figi=self.composite_figi,
            share_class_figi=self.share_class_figi,
            cik=self.cik,
            canonical_instrument_id=canonical_id,
            resolution_status=status,
            resolution_method=method,
            valid_from=self.as_of_date,
            valid_to=self.valid_to,
            source_updated_at=self.source_updated_at,
            ingested_at=self.ingested_at,
            quality_status=QualityStatus.VALID if status is ResolutionStatus.RESOLVED else QualityStatus.WARNING if status is ResolutionStatus.UNRESOLVED else QualityStatus.REJECTED,
            quality_flags=flags,
        )

    def to_instrument(self, instrument_id) -> InstrumentMasterV1:
        if self.instrument_type is None or self.status is None or self.name is None or self.primary_exchange is None or self.currency is None:
            raise ValueError("preliminary identity lacks required canonical fields")
        source_identity = self.stable_identity.key if self.stable_identity is not None else self.provider_ticker
        return InstrumentMasterV1(
            instrument_id=instrument_id,
            issuer_id=None,
            instrument_type=self.instrument_type,
            status=self.status,
            ticker=self.provider_ticker,
            name=self.name,
            primary_exchange=self.primary_exchange,
            listing_country="US",
            currency=self.currency,
            figi=self.composite_figi or self.share_class_figi,
            cik=self.cik,
            valid_from=self.as_of_date,
            valid_to=self.valid_to,
            first_trade_date=None,
            last_trade_date=self.valid_to,
            as_of_date=self.as_of_date,
            source=MASSIVE_PROVIDER_ID,
            source_instrument_id=source_identity,
            ingested_at=self.ingested_at,
            quality_status=QualityStatus.VALID,
            quality_notes=None,
        )


class _PayloadRejected(Exception):
    def __init__(self, identity: _PreliminaryIdentity) -> None:
        self.identity = identity
        super().__init__(identity.rejection_flag or "payload rejected")


def _preliminary_identity(payload: Mapping[str, object], *, as_of_date: date, ingested_at: datetime) -> _PreliminaryIdentity:
    ticker = _required_string(payload.get("ticker"), "ticker").upper()
    composite_figi = _optional_string(payload.get("composite_figi"))
    share_class_figi = _optional_string(payload.get("share_class_figi"))
    cik = _optional_string(payload.get("cik"))
    base = {
        "provider_ticker": ticker,
        "provider_instrument_id": _optional_string(payload.get("id") or payload.get("provider_instrument_id")),
        "composite_figi": composite_figi.upper() if composite_figi else None,
        "share_class_figi": share_class_figi.upper() if share_class_figi else None,
        "cik": cik,
        "valid_to": _optional_date(payload.get("delisted_utc")),
        "source_updated_at": _optional_datetime(payload.get("last_updated_utc")),
        "as_of_date": as_of_date,
        "ingested_at": ingested_at,
    }
    instrument_type = _instrument_type(payload.get("type"))
    if instrument_type is None:
        raise _PayloadRejected(_PreliminaryIdentity(name=_optional_string(payload.get("name")), primary_exchange=_optional_string(payload.get("primary_exchange")), instrument_type=None, status=None, currency=_currency(payload), rejection_flag="unsupported_instrument_type", **base))
    name = _optional_string(payload.get("name"))
    primary_exchange = _optional_string(payload.get("primary_exchange"))
    currency = _currency(payload)
    active = payload.get("active")
    if not isinstance(active, bool):
        raise _PayloadRejected(_PreliminaryIdentity(name=name, primary_exchange=primary_exchange, instrument_type=instrument_type, status=None, currency=currency, rejection_flag="invalid_active_status", **base))
    status = InstrumentStatus.ACTIVE if active else InstrumentStatus.INACTIVE
    if base["valid_to"] is not None:
        status = InstrumentStatus.DELISTED
    if not name or not primary_exchange or not currency:
        raise _PayloadRejected(_PreliminaryIdentity(name=name, primary_exchange=primary_exchange, instrument_type=instrument_type, status=status, currency=currency, rejection_flag="missing_required_canonical_field", **base))
    return _PreliminaryIdentity(name=name, primary_exchange=primary_exchange, instrument_type=instrument_type, status=status, currency=currency, rejection_flag=None, **base)


def _ambiguous_identity_keys(items: list[_PreliminaryIdentity]) -> set[str]:
    signatures: dict[str, set[tuple[str, str | None, str | None]]] = {}
    for item in items:
        if item.rejection_flag is not None or item.stable_identity is None:
            continue
        signatures.setdefault(item.stable_identity.key, set()).add((item.provider_ticker, item.name, item.primary_exchange))
    return {key for key, values in signatures.items() if len(values) > 1}


def _instrument_type(value: object) -> InstrumentType | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    if normalized in {"CS", "COMMON_STOCK"}:
        return InstrumentType.COMMON_STOCK
    if normalized == "ETF":
        return InstrumentType.ETF
    return None


def _currency(payload: Mapping[str, object]) -> str | None:
    raw = payload.get("currency_symbol") or payload.get("base_currency_symbol") or payload.get("currency")
    if isinstance(raw, str) and raw.strip():
        value = raw.strip().upper()
        return "USD" if value in {"USD", "$", "US DOLLAR", "US DOLLARS"} else value[:3]
    name = payload.get("currency_name")
    if isinstance(name, str) and name.strip().lower() in {"usd", "us dollar", "us dollars"}:
        return "USD"
    return "USD"


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Massive reference payload missing required field: {field_name}")
    return value.strip()


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _optional_date(value: object) -> date | None:
    text = _optional_string(value)
    if text is None:
        return None
    return date.fromisoformat(text[:10])


def _optional_datetime(value: object) -> datetime | None:
    text = _optional_string(value)
    if text is None:
        return None
    normalized = text.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(UTC)


def parse_as_of_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("as-of date must use YYYY-MM-DD") from exc
    if parsed != AUTHORIZED_AS_OF_DATE:
        raise ValueError("as-of date is not authorized for this operation")
    return parsed


def parse_data_root(value: str) -> Path:
    path = Path(value)
    if path != APPROVED_DATA_ROOT:
        raise ValueError("data root is not approved for this operation")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingest-massive-instrument-master.sh")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--data-root", required=True)
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
        as_of_date = parse_as_of_date(args.as_of_date)
        data_root = parse_data_root(args.data_root)
    except (SystemExit, ValueError) as exc:
        if not isinstance(exc, SystemExit):
            print(f"error={exc}", file=sys.stderr)
            return 2
        return int(exc.code) if isinstance(exc.code, int) else 2
    print("provider=massive")
    print(f"endpoint={REFERENCE_TICKERS_PATH}")
    print(f"as_of_date={as_of_date.isoformat()}")
    print(f"max_pages={MAX_PAGES}")
    print(f"max_records={MAX_RECORDS}")
    print(f"minimum_request_interval_seconds={MIN_REQUEST_INTERVAL_SECONDS}")
    try:
        config = load_massive_provider_config_from_file()
        result = ingest_massive_instrument_master_snapshot(
            config=config,
            transport=MassiveUrllibTransport(),
            as_of_date=as_of_date,
            data_root=data_root,
        )
    except MassiveCredentialFileError:
        print("status=credential-boundary-error")
        return 1
    except MassiveTransportResponseError as exc:
        if exc.status_code in {401, 403}:
            status = "authentication-or-entitlement-failed"
        elif exc.status_code == 429:
            status = "rate-limited"
        else:
            status = "http-error"
        print(f"status={status}")
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
        print(f"status=failed")
        print(f"failure_class={exc.__class__.__name__}")
        return 1
    for line in result.safe_lines():
        print(line)
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
