"""Massive response mapping into canonical market-data contracts."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Mapping
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import EodPriceBarV1, InstrumentMasterV1, InstrumentStatus, InstrumentType
from tip_api.providers.market_data import ProviderDataError
from tip_api.providers.massive.numeric import InvalidMassiveNumericValue, MissingMassiveNumericValue, parse_massive_decimal, parse_massive_integral

MASSIVE_PROVIDER_ID = "massive_stocks_basic"
MASSIVE_UUID_NAMESPACE = uuid5(NAMESPACE_URL, "trading-intelligence-platform:massive-stocks-basic:v1")


def stable_massive_instrument_id(provider_identity: str) -> UUID:
    identity = _required_string(provider_identity, "provider_identity")
    return uuid5(MASSIVE_UUID_NAMESPACE, identity)


def map_ticker_payload(
    payload: Mapping[str, object],
    *,
    provider_id: str,
    as_of_date: date,
    ingested_at: datetime,
) -> InstrumentMasterV1 | None:
    ticker = _required_string(payload.get("ticker"), "ticker")
    instrument_type = _map_instrument_type(payload.get("type"))
    if instrument_type is None:
        return None
    provider_identity = _provider_identity(payload)
    active = payload.get("active")
    if not isinstance(active, bool):
        raise ProviderDataError(provider_id, "Massive ticker payload has invalid active status")
    valid_to = _optional_date(payload.get("delisted_utc"), "delisted_utc")
    status = InstrumentStatus.ACTIVE if active else InstrumentStatus.INACTIVE
    if valid_to is not None:
        status = InstrumentStatus.DELISTED
    try:
        return InstrumentMasterV1(
            instrument_id=stable_massive_instrument_id(provider_identity),
            issuer_id=None,
            instrument_type=instrument_type,
            status=status,
            ticker=ticker,
            name=_required_string(payload.get("name"), "name"),
            primary_exchange=_required_string(payload.get("primary_exchange"), "primary_exchange"),
            listing_country=_listing_country(payload),
            currency=_currency(payload),
            figi=_optional_string(payload.get("composite_figi"), "composite_figi"),
            cik=_optional_string(payload.get("cik"), "cik"),
            valid_from=as_of_date,
            valid_to=valid_to,
            first_trade_date=None,
            last_trade_date=valid_to,
            as_of_date=as_of_date,
            source=provider_id,
            source_instrument_id=provider_identity,
            ingested_at=ingested_at,
            quality_status=QualityStatus.VALID,
            quality_notes=None,
        )
    except ValidationError as exc:
        raise ProviderDataError(provider_id, "Massive ticker payload failed canonical validation") from exc


def map_grouped_daily_bar_payload(
    payload: Mapping[str, object],
    *,
    provider_id: str,
    instrument_id: UUID,
    session_date: date,
    ingested_at: datetime,
    request_id: str | None,
) -> EodPriceBarV1:
    return _map_bar_payload(
        payload,
        provider_id=provider_id,
        instrument_id=instrument_id,
        session_date=session_date,
        ingested_at=ingested_at,
        request_id=request_id,
    )


def map_custom_bar_payload(
    payload: Mapping[str, object],
    *,
    provider_id: str,
    instrument_id: UUID,
    session_date: date,
    ingested_at: datetime,
    request_id: str | None,
) -> EodPriceBarV1:
    return _map_bar_payload(
        payload,
        provider_id=provider_id,
        instrument_id=instrument_id,
        session_date=session_date,
        ingested_at=ingested_at,
        request_id=request_id,
    )


def _map_bar_payload(
    payload: Mapping[str, object],
    *,
    provider_id: str,
    instrument_id: UUID,
    session_date: date,
    ingested_at: datetime,
    request_id: str | None,
) -> EodPriceBarV1:
    close = _decimal(payload.get("c"), "close")
    source_record_id = _source_record_id(request_id, payload.get("T") or payload.get("ticker"), payload.get("t"))
    try:
        return EodPriceBarV1(
            instrument_id=instrument_id,
            session_date=session_date,
            open=_decimal(payload.get("o"), "open"),
            high=_decimal(payload.get("h"), "high"),
            low=_decimal(payload.get("l"), "low"),
            close=close,
            volume=_non_negative_decimal(payload.get("v"), "volume"),
            vwap=_optional_decimal(payload.get("vw"), "vwap"),
            trade_count=_optional_non_negative_int(payload.get("n"), "trade_count"),
            notional=_optional_decimal(payload.get("notional"), "notional") or Decimal("0"),
            currency="USD",
            split_adjustment_factor=Decimal("1"),
            dividend_adjustment_factor=Decimal("1"),
            total_return_adjustment_factor=Decimal("1"),
            adjusted_close=close,
            source=provider_id,
            source_record_id=source_record_id,
            ingested_at=ingested_at,
            revision=1,
            is_latest_revision=True,
            quality_status=QualityStatus.VALID,
            quality_flags=("adjustment_factors_unverified",),
        )
    except ValidationError as exc:
        raise ProviderDataError(provider_id, "Massive aggregate payload failed canonical validation") from exc


def _provider_identity(payload: Mapping[str, object]) -> str:
    ticker = _required_string(payload.get("ticker"), "ticker").upper()
    composite_figi = (_optional_string(payload.get("composite_figi"), "composite_figi") or "").upper()
    share_class_figi = (_optional_string(payload.get("share_class_figi"), "share_class_figi") or "").upper()
    cik = _optional_string(payload.get("cik"), "cik") or ""
    return f"ticker={ticker}|composite_figi={composite_figi}|share_class_figi={share_class_figi}|cik={cik}"


def _map_instrument_type(value: object) -> InstrumentType | None:
    if not isinstance(value, str):
        raise ProviderDataError(MASSIVE_PROVIDER_ID, "Massive ticker payload has invalid type")
    normalized = value.strip().upper()
    if normalized in {"CS", "COMMON_STOCK"}:
        return InstrumentType.COMMON_STOCK
    if normalized == "ETF":
        return InstrumentType.ETF
    return None


def _listing_country(payload: Mapping[str, object]) -> str:
    locale = _optional_string(payload.get("locale"), "locale")
    if locale is None or locale.upper() == "US":
        return "US"
    return locale.upper()


def _currency(payload: Mapping[str, object]) -> str:
    return _required_string(payload.get("currency_symbol") or payload.get("base_currency_symbol"), "currency_symbol")


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ProviderDataError(MASSIVE_PROVIDER_ID, f"Massive payload missing required field: {field_name}")
    normalized = value.strip()
    if not normalized:
        raise ProviderDataError(MASSIVE_PROVIDER_ID, f"Massive payload missing required field: {field_name}")
    return normalized


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field_name)


def _optional_date(value: object, field_name: str) -> date | None:
    if value is None:
        return None
    text = _required_string(value, field_name)
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ProviderDataError(MASSIVE_PROVIDER_ID, f"Massive payload has invalid date field: {field_name}") from exc


def _decimal(value: object, field_name: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ProviderDataError(MASSIVE_PROVIDER_ID, f"Massive payload has invalid decimal field: {field_name}")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ProviderDataError(MASSIVE_PROVIDER_ID, f"Massive payload has invalid decimal field: {field_name}") from exc
    if not decimal.is_finite():
        raise ProviderDataError(MASSIVE_PROVIDER_ID, f"Massive payload has invalid decimal field: {field_name}")
    return decimal


def _optional_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    return _decimal(value, field_name)


def _non_negative_decimal(value: object, field_name: str) -> Decimal:
    try:
        result = parse_massive_decimal(value, required=True)
    except (MissingMassiveNumericValue, InvalidMassiveNumericValue) as exc:
        raise ProviderDataError(MASSIVE_PROVIDER_ID, f"Massive payload has invalid decimal field: {field_name}") from exc
    assert result is not None
    if result < 0:
        raise ProviderDataError(MASSIVE_PROVIDER_ID, f"Massive payload has invalid decimal field: {field_name}")
    return result


def _non_negative_int(value: object, field_name: str) -> int:
    try:
        result = parse_massive_integral(value, required=True, allow_negative=False)
    except (MissingMassiveNumericValue, InvalidMassiveNumericValue) as exc:
        raise ProviderDataError(MASSIVE_PROVIDER_ID, f"Massive payload has invalid integer field: {field_name}") from exc
    assert result is not None
    return result


def _optional_non_negative_int(value: object, field_name: str) -> int | None:
    try:
        return parse_massive_integral(value, required=False, allow_negative=False)
    except InvalidMassiveNumericValue as exc:
        raise ProviderDataError(MASSIVE_PROVIDER_ID, f"Massive payload has invalid integer field: {field_name}") from exc


def _source_record_id(request_id: str | None, ticker: object, timestamp: object) -> str | None:
    parts = [part for part in (request_id, str(ticker) if ticker is not None else None, str(timestamp) if timestamp is not None else None) if part]
    return ":".join(parts) if parts else None
