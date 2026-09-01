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
    ProviderTickerResolverV1,
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
    resolvers: tuple[ProviderTickerResolverV1, ...]
    request_count: int
    raw_record_count: int
    eligible_record_count: int
    expected_exclusion_count: int
    malformed_rejected_count: int
    resolved_eligible_count: int
    unresolved_eligible_count: int
    ambiguous_ticker_record_count: int
    stable_identifier_collision_count: int
    unique_provider_ticker_count: int
    duplicate_provider_ticker_count: int
    type_counts: tuple[tuple[str, int], ...]
    category_counts: tuple[tuple[str, int], ...]
    ambiguous_ticker_samples: tuple[str, ...]
    unknown_type_counts: tuple[tuple[str, int], ...]
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
    del config, transport, as_of_date, data_root, rate_limiter, ingested_at
    raise RuntimeError(
        "direct network-to-production Identity ingestion is disabled; "
        "use fetch-only, plan, and approved apply"
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
    prelim: list[_PreliminaryIdentity] = []
    type_counter: dict[str, int] = {}
    unknown_type_counter: dict[str, int] = {}
    for payload in payloads:
        raw_type = _type_code(payload.get("type"))
        type_counter[raw_type] = type_counter.get(raw_type, 0) + 1
        item = _preliminary_identity(payload, as_of_date=as_of_date, ingested_at=ingested_at)
        if item.category == "malformed":
            unknown_type_counter[raw_type] = unknown_type_counter.get(raw_type, 0) + 1
        prelim.append(item)

    stable_collision_keys = _stable_identifier_collision_keys(prelim)
    ticker_ambiguous = _ticker_ambiguity_tickers(prelim, stable_collision_keys)
    exact_duplicate_keys = _exact_duplicate_keys(prelim)
    instruments: list[InstrumentMasterV1] = []
    identities: list[ProviderInstrumentIdentityV1] = []
    resolvers: list[ProviderTickerResolverV1] = []
    category_counts: dict[str, int] = {}
    for item in prelim:
        category_counts[item.category] = category_counts.get(item.category, 0) + 1
        if item.category == "excluded":
            identities.append(item.to_identity(ResolutionStatus.EXCLUDED, ResolutionMethod.UNRESOLVED, None, (item.reason or "expected_exclusion",)))
            continue
        if item.category == "malformed":
            identities.append(item.to_identity(ResolutionStatus.REJECTED, ResolutionMethod.UNRESOLVED, None, (item.reason or "malformed",)))
            continue
        if item.stable_identity is None:
            identities.append(item.to_identity(ResolutionStatus.UNRESOLVED, ResolutionMethod.UNRESOLVED, None, ("no_stable_security_identifier",)))
            continue
        if item.stable_identity.key in stable_collision_keys:
            identities.append(item.to_identity(ResolutionStatus.AMBIGUOUS, ResolutionMethod.UNRESOLVED, None, ("stable_identifier_collision",)))
            continue
        if item.provider_ticker in ticker_ambiguous:
            identities.append(item.to_identity(ResolutionStatus.AMBIGUOUS, ResolutionMethod.UNRESOLVED, None, ("ticker_level_ambiguity",)))
            continue
        instrument_id = canonical_instrument_id_for_identity(item.stable_identity)
        try:
            instrument = item.to_instrument(instrument_id)
        except (ValidationError, ValueError):
            identities.append(item.to_identity(ResolutionStatus.REJECTED, ResolutionMethod.UNRESOLVED, None, ("canonical_validation_failed",)))
            category_counts["eligible"] -= 1
            category_counts["malformed"] = category_counts.get("malformed", 0) + 1
            continue
        # exact duplicate records share ticker and stable ID; keep one canonical instrument/resolver.
        if item.exact_key in exact_duplicate_keys and any(existing.instrument_id == instrument.instrument_id for existing in instruments):
            identities.append(item.to_identity(ResolutionStatus.RESOLVED, item.stable_identity.resolution_method, instrument_id, ("exact_duplicate",)))
            continue
        instruments.append(instrument)
        identities.append(item.to_identity(ResolutionStatus.RESOLVED, item.stable_identity.resolution_method, instrument_id, ()))
        resolvers.append(ProviderTickerResolverV1(provider=MASSIVE_PROVIDER_ID, as_of_date=as_of_date, provider_ticker=item.provider_ticker, canonical_instrument_id=instrument_id, resolution_method=item.stable_identity.resolution_method.value, source_identity_key=item.stable_identity.key, ingested_at=ingested_at))

    unique_tickers = {item.provider_ticker for item in prelim}
    duplicate_tickers = {ticker for ticker in unique_tickers if sum(1 for item in prelim if item.provider_ticker == ticker) > 1}
    resolved_eligible = sum(1 for identity in identities if identity.resolution_status is ResolutionStatus.RESOLVED and "exact_duplicate" not in identity.quality_flags)
    unresolved_eligible = sum(1 for identity in identities if identity.resolution_status is ResolutionStatus.UNRESOLVED)
    ambiguous_ticker_records = sum(1 for identity in identities if "ticker_level_ambiguity" in identity.quality_flags)
    stable_collision_records = sum(1 for identity in identities if "stable_identifier_collision" in identity.quality_flags)
    malformed = sum(1 for identity in identities if identity.resolution_status is ResolutionStatus.REJECTED)
    excluded = sum(1 for identity in identities if identity.resolution_status is ResolutionStatus.EXCLUDED)
    eligible = (
        resolved_eligible
        + unresolved_eligible
        + ambiguous_ticker_records
        + stable_collision_records
    )
    return ReferenceSnapshotBuildResult(
        instruments=tuple(sorted(instruments, key=lambda record: (str(record.instrument_id), record.ticker))),
        identities=tuple(sorted(identities, key=lambda record: (record.provider_ticker, record.provider_instrument_id or "", record.composite_figi or "", record.share_class_figi or ""))),
        resolvers=tuple(sorted(resolvers, key=lambda record: (record.provider_ticker, str(record.canonical_instrument_id)))),
        request_count=request_count,
        raw_record_count=len(payloads),
        eligible_record_count=eligible,
        expected_exclusion_count=excluded,
        malformed_rejected_count=malformed,
        resolved_eligible_count=resolved_eligible,
        unresolved_eligible_count=unresolved_eligible,
        ambiguous_ticker_record_count=ambiguous_ticker_records,
        stable_identifier_collision_count=stable_collision_records,
        unique_provider_ticker_count=len(unique_tickers),
        duplicate_provider_ticker_count=len(duplicate_tickers),
        type_counts=tuple(sorted(type_counter.items())),
        category_counts=tuple(sorted(category_counts.items())),
        ambiguous_ticker_samples=tuple(sorted(ticker_ambiguous)[:5]),
        unknown_type_counts=tuple(sorted(unknown_type_counter.items())),
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
        path, params = _next_page_request(next_url, base_url=config.base_url, expected_date=as_of_date)
    raise RuntimeError("Massive reference page limit exceeded")


def _next_page_request(next_url: object, *, base_url: str, expected_date: date | None = None) -> tuple[str, dict[str, MassiveParamValue]]:
    if not isinstance(next_url, str) or not next_url.strip():
        raise RuntimeError("Massive reference next_url is invalid")
    parsed = urlparse(next_url)
    base = urlparse(base_url)
    if parsed.scheme and parsed.scheme != "https":
        raise RuntimeError("Massive reference next_url scheme changed")
    if parsed.netloc and parsed.netloc != base.netloc:
        raise RuntimeError("Massive reference next_url host changed")
    if parsed.path != REFERENCE_TICKERS_PATH:
        raise RuntimeError("Massive reference next_url path changed")
    params: dict[str, MassiveParamValue] = {}
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        if key.lower() == "apikey":
            continue
        params[key] = value
    if expected_date is not None and "date" in params and params["date"] != expected_date.isoformat():
        raise RuntimeError("Massive reference next_url date changed")
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
    category: str
    reason: str | None = None

    @property
    def stable_identity(self):
        return select_stable_identity(share_class_figi=self.share_class_figi, composite_figi=self.composite_figi, provider_instrument_id=self.provider_instrument_id)

    @property
    def exact_key(self) -> tuple[str, str | None, str | None, str | None]:
        return (self.provider_ticker, self.share_class_figi, self.composite_figi, self.provider_instrument_id)

    def to_identity(self, status: ResolutionStatus, method: ResolutionMethod, canonical_id, flags: tuple[str, ...]) -> ProviderInstrumentIdentityV1:
        quality = QualityStatus.VALID if status is ResolutionStatus.RESOLVED else QualityStatus.WARNING if status in {ResolutionStatus.UNRESOLVED, ResolutionStatus.EXCLUDED} else QualityStatus.REJECTED
        return ProviderInstrumentIdentityV1(provider=MASSIVE_PROVIDER_ID, as_of_date=self.as_of_date, provider_ticker=self.provider_ticker, provider_instrument_id=self.provider_instrument_id, composite_figi=self.composite_figi, share_class_figi=self.share_class_figi, cik=self.cik, canonical_instrument_id=canonical_id, resolution_status=status, resolution_method=method, valid_from=self.as_of_date, valid_to=self.valid_to, source_updated_at=self.source_updated_at, ingested_at=self.ingested_at, quality_status=quality, quality_flags=flags)

    def to_instrument(self, instrument_id) -> InstrumentMasterV1:
        if self.instrument_type is None or self.status is None or self.name is None or self.primary_exchange is None or self.currency is None or self.stable_identity is None:
            raise ValueError("preliminary identity lacks required canonical fields")
        return InstrumentMasterV1(instrument_id=instrument_id, issuer_id=None, instrument_type=self.instrument_type, status=self.status, ticker=self.provider_ticker, name=self.name, primary_exchange=self.primary_exchange, listing_country="US", currency=self.currency, figi=self.composite_figi or self.share_class_figi, cik=self.cik, valid_from=self.as_of_date, valid_to=self.valid_to, first_trade_date=None, last_trade_date=self.valid_to, as_of_date=self.as_of_date, source=MASSIVE_PROVIDER_ID, source_instrument_id=self.stable_identity.key, ingested_at=self.ingested_at, quality_status=QualityStatus.VALID, quality_notes=None)


def _preliminary_identity(payload: Mapping[str, object], *, as_of_date: date, ingested_at: datetime) -> _PreliminaryIdentity:
    try:
        ticker = _required_string(payload.get("ticker"), "ticker").upper()
    except RuntimeError:
        ticker = "UNKNOWN"
        return _minimal_identity(ticker, as_of_date, ingested_at, "malformed", "missing_required_ticker")
    composite_figi = _upper_optional(payload.get("composite_figi"))
    share_class_figi = _upper_optional(payload.get("share_class_figi"))
    cik = _optional_string(payload.get("cik"))
    raw_type = _type_code(payload.get("type"))
    type_decision = _type_decision(raw_type)
    base = dict(provider_ticker=ticker, provider_instrument_id=_upper_optional(payload.get("id") or payload.get("provider_instrument_id")), composite_figi=composite_figi, share_class_figi=share_class_figi, cik=cik, valid_to=_optional_date(payload.get("delisted_utc")), source_updated_at=_optional_datetime(payload.get("last_updated_utc")), as_of_date=as_of_date, ingested_at=ingested_at)
    if type_decision[0] == "excluded":
        return _PreliminaryIdentity(name=_optional_string(payload.get("name")), primary_exchange=_optional_string(payload.get("primary_exchange")), instrument_type=None, status=None, currency=_currency(payload), category="excluded", reason=type_decision[1], **base)
    if type_decision[0] == "malformed":
        return _PreliminaryIdentity(name=_optional_string(payload.get("name")), primary_exchange=_optional_string(payload.get("primary_exchange")), instrument_type=None, status=None, currency=_currency(payload), category="malformed", reason=type_decision[1], **base)
    name = _optional_string(payload.get("name"))
    primary_exchange = _optional_string(payload.get("primary_exchange"))
    currency = _currency(payload)
    active = payload.get("active")
    if not isinstance(active, bool):
        return _PreliminaryIdentity(name=name, primary_exchange=primary_exchange, instrument_type=type_decision[2], status=None, currency=currency, category="malformed", reason="invalid_active_status", **base)
    status = InstrumentStatus.DELISTED if base["valid_to"] is not None else InstrumentStatus.ACTIVE if active else InstrumentStatus.INACTIVE
    if not name or not primary_exchange or not currency:
        return _PreliminaryIdentity(name=name, primary_exchange=primary_exchange, instrument_type=type_decision[2], status=status, currency=currency, category="malformed", reason="missing_required_canonical_field", **base)
    return _PreliminaryIdentity(name=name, primary_exchange=primary_exchange, instrument_type=type_decision[2], status=status, currency=currency, category="eligible", reason=None, **base)


def _minimal_identity(ticker: str, as_of_date: date, ingested_at: datetime, category: str, reason: str) -> _PreliminaryIdentity:
    return _PreliminaryIdentity(provider_ticker=ticker, name=None, primary_exchange=None, instrument_type=None, status=None, provider_instrument_id=None, composite_figi=None, share_class_figi=None, cik=None, currency=None, valid_to=None, source_updated_at=None, as_of_date=as_of_date, ingested_at=ingested_at, category=category, reason=reason)


def _stable_identifier_collision_keys(items: list[_PreliminaryIdentity]) -> set[str]:
    signatures: dict[str, set[tuple[str, str | None, str | None]]] = {}
    for item in items:
        if item.category != "eligible" or item.stable_identity is None:
            continue
        signatures.setdefault(item.stable_identity.key, set()).add((item.provider_ticker, item.name, item.primary_exchange))
    return {key for key, values in signatures.items() if len(values) > 1}


def _ticker_ambiguity_tickers(items: list[_PreliminaryIdentity], stable_collision_keys: set[str]) -> set[str]:
    identities_by_ticker: dict[str, set[str]] = {}
    for item in items:
        if item.category != "eligible" or item.stable_identity is None or item.stable_identity.key in stable_collision_keys:
            continue
        identities_by_ticker.setdefault(item.provider_ticker, set()).add(item.stable_identity.key)
    return {ticker for ticker, keys in identities_by_ticker.items() if len(keys) > 1}


def _exact_duplicate_keys(items: list[_PreliminaryIdentity]) -> set[tuple[str, str | None, str | None, str | None]]:
    counts: dict[tuple[str, str | None, str | None, str | None], int] = {}
    for item in items:
        counts[item.exact_key] = counts.get(item.exact_key, 0) + 1
    return {key for key, count in counts.items() if count > 1}


def _type_code(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "<missing>"
    return value.strip().upper()


def _type_decision(raw_type: str):
    if raw_type in {"CS", "COMMON_STOCK", "ADRC", "ADRP", "ADRR"}:
        return ("eligible", "eligible_common_equity", InstrumentType.COMMON_STOCK)
    if raw_type == "ETF":
        return ("eligible", "eligible_etf", InstrumentType.ETF)
    exclusions = {
        "PFD": "preferred_stock", "PREF": "preferred_stock", "PREFERRED": "preferred_stock",
        "WARRANT": "warrant", "WRT": "warrant", "RIGHT": "right", "RIGHTS": "right", "UNIT": "unit",
        "BOND": "bond", "STRUCT": "structured_product", "SP": "structured_product",
        "CEF": "closed_end_fund", "FUND": "fund", "MF": "mutual_fund", "MMF": "money_market_fund",
        "ETN": "etn", "ETS": "etn", "TRUST": "trust_or_partnership", "LP": "trust_or_partnership", "MLP": "trust_or_partnership",
        "INDEX": "non_equity", "TEST": "test_or_placeholder",
    }
    if raw_type in exclusions:
        return ("excluded", exclusions[raw_type], None)
    if raw_type == "<missing>":
        return ("malformed", "missing_provider_type", None)
    return ("malformed", f"unknown_provider_type_{raw_type}", None)


def _upper_optional(value: object) -> str | None:
    text = _optional_string(value)
    return text.upper() if text else None


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
    if value is None or not isinstance(value, str):
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
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)

def parse_as_of_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("as-of date must use YYYY-MM-DD") from exc
    if parsed >= date.today():
        raise ValueError("as-of date must be a completed historical date")
    return parsed


def parse_data_root(value: str) -> Path:
    path = Path(value)
    if path != APPROVED_DATA_ROOT:
        raise ValueError("data root is not approved for this operation")
    return path


def main(argv: list[str] | None = None) -> int:
    from tip_api.providers.massive.same_day_catchup import identity_main

    try:
        return identity_main(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2


if __name__ == "__main__":
    raise SystemExit(main())
