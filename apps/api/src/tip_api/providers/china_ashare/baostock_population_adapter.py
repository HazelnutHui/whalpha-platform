"""Bounded BaoStock security-basic capture for A-share population review."""

from __future__ import annotations

from datetime import date, datetime

from tip_api.contracts.china_ashare.v1.population import (
    ChinaAshareBaoStockBasicRecordV1,
    build_baostock_basic_record,
)
from tip_api.providers.china_ashare.baostock_adapter import (
    BAOSTOCK_ASHARE_PROVIDER_ID,
    BaoStockSession,
)
from tip_api.providers.market_data import ProviderDataError, ProviderUnavailableError


_FIELDS = ("code", "code_name", "ipoDate", "outDate", "type", "status")


def capture_baostock_security_basic(
    *, session: BaoStockSession, ingested_at: datetime
) -> tuple[ChinaAshareBaoStockBasicRecordV1, ...]:
    cursor = session.query_stock_basic(code="", code_name="")
    if str(cursor.error_code) != "0":
        raise ProviderUnavailableError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            "BaoStock security-basic request failed",
        )
    fields = tuple(cursor.fields)
    if len(fields) != len(set(fields)) or any(item not in fields for item in _FIELDS):
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            "BaoStock security-basic schema differs",
        )
    rows = []
    seen = set()
    while str(cursor.error_code) == "0" and cursor.next():
        values = cursor.get_row_data()
        if len(values) != len(fields):
            raise ProviderDataError(
                BAOSTOCK_ASHARE_PROVIDER_ID,
                "BaoStock security-basic row width differs",
            )
        raw = dict(zip(fields, values, strict=True))
        source_id = str(raw["code"]).strip().lower()
        if source_id in seen:
            raise ProviderDataError(
                BAOSTOCK_ASHARE_PROVIDER_ID,
                "BaoStock security-basic source ID is duplicated",
        )
        seen.add(source_id)
        if str(raw["type"]).strip() != "1":
            continue
        listing_date = _date(raw["ipoDate"], field_name="ipoDate")
        out_date = _date(raw["outDate"], field_name="outDate", optional=True)
        rows.append(
            build_baostock_basic_record(
                source_security_id=source_id,
                current_name=str(raw["code_name"]).strip(),
                listing_date=listing_date,
                out_date=out_date,
                provider_type=str(raw["type"]).strip(),
                provider_status=str(raw["status"]).strip(),
                ingested_at=ingested_at,
            )
        )
    if str(cursor.error_code) != "0":
        raise ProviderUnavailableError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            "BaoStock security-basic cursor failed",
        )
    if not rows:
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            "BaoStock security-basic response is empty",
        )
    return tuple(sorted(rows, key=lambda item: item.source_security_id))


def _date(value: object, *, field_name: str, optional: bool = False) -> date | None:
    text = str(value or "").strip()
    if optional and not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            f"BaoStock {field_name} is invalid",
        ) from exc
