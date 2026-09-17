"""Raw, source-keyed BaoStock capture for restartable A-share expansion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping

from tip_api.contracts.china_ashare.v1.source_expansion import (
    ChinaAshareRawAdjustmentSourceRowV1,
    ChinaAshareRawDailySourceRowV1,
    ChinaAshareSourceExpansionPartitionSpecV1,
)
from tip_api.providers.china_ashare.baostock_adapter import (
    BAOSTOCK_ASHARE_PROVIDER_ID,
    BaoStockCursor,
    BaoStockSession,
)
from tip_api.providers.market_data import ProviderDataError, ProviderUnavailableError


_DAILY_FIELDS = (
    "date",
    "code",
    "open",
    "high",
    "low",
    "close",
    "preclose",
    "volume",
    "amount",
    "tradestatus",
    "isST",
)
_ADJUSTMENT_FIELDS = (
    "code",
    "dividOperateDate",
    "foreAdjustFactor",
    "backAdjustFactor",
    "adjustFactor",
)


@dataclass(frozen=True, slots=True)
class CapturedChinaAshareSourceExpansionPartitionV1:
    daily_rows: tuple[ChinaAshareRawDailySourceRowV1, ...]
    adjustment_rows: tuple[ChinaAshareRawAdjustmentSourceRowV1, ...]
    daily_zero_row_ids: tuple[str, ...]
    adjustment_zero_row_ids: tuple[str, ...]
    source_request_count: int


def capture_baostock_source_expansion_partition(
    *,
    session: BaoStockSession,
    partition: ChinaAshareSourceExpansionPartitionSpecV1,
    interval_start: date,
    interval_end: date,
    captured_at: datetime,
) -> CapturedChinaAshareSourceExpansionPartitionV1:
    daily_rows = []
    adjustment_rows = []
    daily_zero = []
    adjustment_zero = []
    for target in partition.targets:
        source_id = target.source_security_id
        daily_start = max(interval_start, target.listing_date)
        daily = _read_cursor(
            session.query_history_k_data_plus(
                source_id,
                ",".join(_DAILY_FIELDS),
                start_date=daily_start.isoformat(),
                end_date=interval_end.isoformat(),
                frequency="d",
                adjustflag="3",
            ),
            required_fields=_DAILY_FIELDS,
        )
        if not daily:
            daily_zero.append(source_id)
        for row in daily:
            if str(row["code"]).strip().lower() != source_id:
                raise ProviderDataError(
                    BAOSTOCK_ASHARE_PROVIDER_ID,
                    "source expansion daily security differs from request",
                )
            session_date = _date(row["date"], "date")
            if not daily_start <= session_date <= interval_end:
                raise ProviderDataError(
                    BAOSTOCK_ASHARE_PROVIDER_ID,
                    "source expansion daily row falls outside request",
                )
            daily_rows.append(
                ChinaAshareRawDailySourceRowV1(
                    source_security_id=source_id,
                    session_date=session_date,
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    pre_close=row["preclose"],
                    volume=row["volume"],
                    amount=row["amount"],
                    provider_trade_status=row["tradestatus"],
                    provider_risk_warning=row["isST"],
                    ingested_at=captured_at,
                )
            )
        adjustments = _read_cursor(
            session.query_adjust_factor(
                source_id,
                start_date=target.listing_date.isoformat(),
                end_date=interval_end.isoformat(),
            ),
            required_fields=_ADJUSTMENT_FIELDS,
        )
        if not adjustments:
            adjustment_zero.append(source_id)
        for row in adjustments:
            if str(row["code"]).strip().lower() != source_id:
                raise ProviderDataError(
                    BAOSTOCK_ASHARE_PROVIDER_ID,
                    "source expansion adjustment security differs from request",
                )
            session_date = _date(row["dividOperateDate"], "dividOperateDate")
            if not target.listing_date <= session_date <= interval_end:
                raise ProviderDataError(
                    BAOSTOCK_ASHARE_PROVIDER_ID,
                    "source expansion adjustment row falls outside request",
                )
            adjustment_rows.append(
                ChinaAshareRawAdjustmentSourceRowV1(
                    source_security_id=source_id,
                    session_date=session_date,
                    provider_factor=row["adjustFactor"],
                    fore_adjust_factor=row["foreAdjustFactor"],
                    back_adjust_factor=row["backAdjustFactor"],
                    ingested_at=captured_at,
                )
            )
    ordered_daily = tuple(
        sorted(daily_rows, key=lambda item: (item.source_security_id, item.session_date))
    )
    ordered_adjustments = tuple(
        sorted(
            adjustment_rows,
            key=lambda item: (item.source_security_id, item.session_date),
        )
    )
    _unique_daily(ordered_daily)
    _unique_adjustments(ordered_adjustments)
    return CapturedChinaAshareSourceExpansionPartitionV1(
        daily_rows=ordered_daily,
        adjustment_rows=ordered_adjustments,
        daily_zero_row_ids=tuple(sorted(daily_zero)),
        adjustment_zero_row_ids=tuple(sorted(adjustment_zero)),
        source_request_count=len(partition.targets) * 2,
    )


def _read_cursor(
    cursor: BaoStockCursor, *, required_fields: tuple[str, ...]
) -> tuple[Mapping[str, str], ...]:
    if str(cursor.error_code) != "0":
        raise ProviderUnavailableError(
            BAOSTOCK_ASHARE_PROVIDER_ID, "BaoStock expansion request failed"
        )
    fields = tuple(cursor.fields)
    if len(fields) != len(set(fields)) or any(item not in fields for item in required_fields):
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID, "BaoStock expansion schema differs"
        )
    rows = []
    while str(cursor.error_code) == "0" and cursor.next():
        values = cursor.get_row_data()
        if len(values) != len(fields):
            raise ProviderDataError(
                BAOSTOCK_ASHARE_PROVIDER_ID, "BaoStock expansion row width differs"
            )
        rows.append(dict(zip(fields, values, strict=True)))
    if str(cursor.error_code) != "0":
        raise ProviderUnavailableError(
            BAOSTOCK_ASHARE_PROVIDER_ID, "BaoStock expansion cursor failed"
        )
    return tuple(rows)


def _date(value: object, field_name: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            f"BaoStock expansion {field_name} is invalid",
        ) from exc


def _unique_daily(rows: tuple[ChinaAshareRawDailySourceRowV1, ...]) -> None:
    keys = tuple((item.source_security_id, item.session_date) for item in rows)
    if keys != tuple(sorted(set(keys))):
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID, "BaoStock expansion daily rows differ"
        )


def _unique_adjustments(
    rows: tuple[ChinaAshareRawAdjustmentSourceRowV1, ...],
) -> None:
    keys = tuple((item.source_security_id, item.session_date) for item in rows)
    if keys != tuple(sorted(set(keys))):
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID, "BaoStock expansion adjustment rows differ"
        )
