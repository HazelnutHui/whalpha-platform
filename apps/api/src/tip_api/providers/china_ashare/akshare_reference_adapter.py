"""AKShare-mediated official-list observations for A-share identity review."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Callable, Mapping, Protocol
from zoneinfo import ZoneInfo

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAshareIdentityResolutionStatus,
    ChinaAshareInstrumentSourceObservationV1,
    ChinaAshareListingStatus,
    ChinaAshareSecurityForm,
)
from tip_api.contracts.common import QualityStatus
from tip_api.providers.china_ashare.protocol import ChinaAshareSourceInstrumentQuery
from tip_api.providers.market_data import ProviderDataError, ProviderUnavailableError


AKSHARE_ASHARE_REFERENCE_PROVIDER_ID = "akshare_official_lists"
_SHANGHAI = ZoneInfo("Asia/Shanghai")
Clock = Callable[[], datetime]


class TabularResult(Protocol):
    def to_dict(self, orient: str) -> list[dict[str, Any]]:
        ...


class AkshareReferenceModule(Protocol):
    def stock_info_sh_name_code(self, symbol: str) -> TabularResult:
        ...

    def stock_info_sz_name_code(self, symbol: str) -> TabularResult:
        ...

    def stock_info_bj_name_code(self) -> TabularResult:
        ...


class AkshareAshareReferenceAdapter:
    """Read current exchange lists without creating stable identity authority."""

    def __init__(
        self,
        *,
        module: AkshareReferenceModule,
        clock: Clock | None = None,
    ) -> None:
        self._module = module
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def provider_id(self) -> str:
        return AKSHARE_ASHARE_REFERENCE_PROVIDER_ID

    def get_current_instrument_observations(
        self,
        query: ChinaAshareSourceInstrumentQuery,
    ) -> tuple[ChinaAshareInstrumentSourceObservationV1, ...]:
        observed_at = self._utc_now()
        current_china_date = observed_at.astimezone(_SHANGHAI).date()
        if query.as_of_date != current_china_date:
            raise ProviderDataError(
                self.provider_id,
                "current-list endpoint cannot be backdated",
            )
        calls = (
            (
                "akshare_sse_main_a_list",
                self._call("stock_info_sh_name_code", symbol="主板A股"),
                ChinaAshareExchange.SSE,
                ChinaAshareBoard.SSE_MAIN,
                ChinaAshareSecurityForm.COMMON_STOCK,
                "证券代码",
                "证券简称",
                "上市日期",
            ),
            (
                "akshare_sse_star_list",
                self._call("stock_info_sh_name_code", symbol="科创板"),
                ChinaAshareExchange.SSE,
                ChinaAshareBoard.STAR,
                ChinaAshareSecurityForm.COMMON_STOCK,
                "证券代码",
                "证券简称",
                "上市日期",
            ),
            (
                "akshare_szse_a_list",
                self._call("stock_info_sz_name_code", symbol="A股列表"),
                ChinaAshareExchange.SZSE,
                None,
                ChinaAshareSecurityForm.COMMON_STOCK,
                "A股代码",
                "A股简称",
                "A股上市日期",
            ),
            (
                "akshare_bse_list",
                self._call("stock_info_bj_name_code"),
                ChinaAshareExchange.BSE,
                ChinaAshareBoard.BSE,
                ChinaAshareSecurityForm.COMMON_STOCK,
                "证券代码",
                "证券简称",
                "上市日期",
            ),
        )
        observations: list[ChinaAshareInstrumentSourceObservationV1] = []
        seen: set[tuple[ChinaAshareExchange, str]] = set()
        for (
            source,
            rows,
            exchange,
            fixed_board,
            security_form,
            code_field,
            name_field,
            list_date_field,
        ) in calls:
            for row in rows:
                code = _code(row, code_field, self.provider_id)
                key = (exchange, code)
                if key in seen:
                    raise ProviderDataError(
                        self.provider_id,
                        "official-list observations contain a duplicate security",
                    )
                seen.add(key)
                board = fixed_board or _szse_board(row, self.provider_id)
                prefix, suffix = {
                    ChinaAshareExchange.SSE: ("sh", "SH"),
                    ChinaAshareExchange.SZSE: ("sz", "SZ"),
                    ChinaAshareExchange.BSE: ("bj", "BJ"),
                }[exchange]
                observations.append(
                    ChinaAshareInstrumentSourceObservationV1(
                        source_security_id=f"{prefix}.{code}",
                        source_code=code,
                        display_ticker=f"{code}.{suffix}",
                        name=_text(row, name_field, self.provider_id),
                        exchange=exchange,
                        board=board,
                        security_form=security_form,
                        listing_status=ChinaAshareListingStatus.LISTED,
                        list_date=_optional_date(row.get(list_date_field), self.provider_id),
                        as_of_date=query.as_of_date,
                        instrument_id=None,
                        resolution_status=ChinaAshareIdentityResolutionStatus.QUARANTINED,
                        source=source,
                        source_available_at=observed_at,
                        ingested_at=observed_at,
                        quality_status=QualityStatus.PENDING_REVIEW,
                        reason_codes=("stable_identity_unproven",),
                    )
                )
        return tuple(
            sorted(observations, key=lambda item: item.source_security_id)
        )

    def _call(self, method_name: str, **kwargs: object) -> tuple[Mapping[str, Any], ...]:
        try:
            method = getattr(self._module, method_name)
            result = method(**kwargs)
            rows = result.to_dict(orient="records")
        except Exception as exc:
            raise ProviderUnavailableError(
                self.provider_id,
                "AKShare reference source call failed",
            ) from exc
        if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
            raise ProviderDataError(self.provider_id, "AKShare reference rows are invalid")
        if not rows:
            raise ProviderDataError(
                self.provider_id,
                "AKShare official-list source returned no rows",
            )
        return tuple(rows)

    def _utc_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ProviderDataError(self.provider_id, "adapter clock returned a naive datetime")
        return value.astimezone(UTC)


def _code(row: Mapping[str, Any], field: str, provider_id: str) -> str:
    value = _text(row, field, provider_id)
    if len(value) != 6 or not value.isdigit():
        raise ProviderDataError(provider_id, "official-list security code is invalid")
    return value


def _text(row: Mapping[str, Any], field: str, provider_id: str) -> str:
    value = row.get(field)
    if value is None or not str(value).strip():
        raise ProviderDataError(provider_id, f"official-list field is missing: {field}")
    return str(value).strip()


def _optional_date(value: Any, provider_id: str) -> date | None:
    if value is None or not str(value).strip() or str(value).strip().lower() in {"nan", "nat"}:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError as exc:
        raise ProviderDataError(provider_id, "official-list listing date is invalid") from exc


def _szse_board(row: Mapping[str, Any], provider_id: str) -> ChinaAshareBoard:
    value = _text(row, "板块", provider_id)
    mapping = {
        "主板": ChinaAshareBoard.SZSE_MAIN,
        "创业板": ChinaAshareBoard.CHINEXT,
    }
    if value not in mapping:
        raise ProviderDataError(provider_id, "SZSE official-list board is unsupported")
    return mapping[value]
