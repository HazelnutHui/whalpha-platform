"""BaoStock adapter that emits unpromoted China A-share source observations.

The adapter has no import-time BaoStock dependency and performs no login or
network setup.  A caller must inject an already established session.  This
keeps ordinary tests offline and prevents an adapter from silently granting
canonical, research, Product, or redistribution authority.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Callable, Mapping, Protocol

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareBoard,
    ChinaAshareDailyBarV1,
    ChinaAshareDailyTradingStateV1,
    ChinaAshareExchange,
    ChinaAshareIdentityResolutionStatus,
    ChinaAshareInstrumentSourceObservationV1,
    ChinaAshareListingStatus,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareSecurityForm,
    ChinaAshareSourceSecuritySnapshotStateV1,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.common import QualityStatus
from tip_api.providers.china_ashare.protocol import (
    ChinaAshareDailySourceBatchV1,
    ChinaAshareIdentityBindingV1,
    ChinaAshareInstrumentSourceBatchV1,
    ChinaAshareSourceCapability,
    ChinaAshareSourceDailyQuery,
    ChinaAshareSourceInstrumentQuery,
)
from tip_api.providers.market_data import ProviderDataError, ProviderUnavailableError


BAOSTOCK_ASHARE_PROVIDER_ID = "baostock_ashare"
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
Clock = Callable[[], datetime]


class BaoStockCursor(Protocol):
    error_code: str
    error_msg: str
    fields: list[str]

    def next(self) -> bool:
        ...

    def get_row_data(self) -> list[str]:
        ...


class BaoStockSession(Protocol):
    def query_all_stock(self, day: str = "") -> BaoStockCursor:
        ...

    def query_history_k_data_plus(
        self,
        code: str,
        fields: str,
        start_date: str = "",
        end_date: str = "",
        frequency: str = "d",
        adjustflag: str = "3",
    ) -> BaoStockCursor:
        ...

    def query_adjust_factor(
        self,
        code: str,
        start_date: str = "",
        end_date: str = "",
    ) -> BaoStockCursor:
        ...


class BaoStockAshareSourceAdapter:
    _capabilities = frozenset(
        {
            ChinaAshareSourceCapability.INSTRUMENT_SNAPSHOT,
            ChinaAshareSourceCapability.RAW_DAILY_BAR,
            ChinaAshareSourceCapability.DAILY_TRADING_STATE,
            ChinaAshareSourceCapability.ADJUSTMENT_FACTOR_OBSERVATION,
        }
    )

    def __init__(
        self,
        *,
        session: BaoStockSession,
        clock: Clock | None = None,
    ) -> None:
        self._session = session
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def provider_id(self) -> str:
        return BAOSTOCK_ASHARE_PROVIDER_ID

    @property
    def capabilities(self) -> frozenset[ChinaAshareSourceCapability]:
        return self._capabilities

    def get_instrument_observations(
        self,
        query: ChinaAshareSourceInstrumentQuery,
        *,
        identity_bindings: tuple[ChinaAshareIdentityBindingV1, ...] = (),
    ) -> tuple[ChinaAshareInstrumentSourceObservationV1, ...]:
        return self.get_instrument_snapshot(
            query,
            identity_bindings=identity_bindings,
        ).instruments

    def get_instrument_snapshot(
        self,
        query: ChinaAshareSourceInstrumentQuery,
        *,
        identity_bindings: tuple[ChinaAshareIdentityBindingV1, ...] = (),
    ) -> ChinaAshareInstrumentSourceBatchV1:
        bindings = _binding_map(identity_bindings)
        rows = self._read_cursor(
            self._session.query_all_stock(day=query.as_of_date.isoformat()),
            required_fields=("code", "tradeStatus", "code_name"),
        )
        if not rows:
            raise ProviderDataError(
                self.provider_id,
                "BaoStock instrument snapshot returned no rows",
            )
        ingested_at = self._utc_now()
        observations: list[ChinaAshareInstrumentSourceObservationV1] = []
        source_states: list[ChinaAshareSourceSecuritySnapshotStateV1] = []
        seen: set[str] = set()
        for row in rows:
            source_id = _source_security_id(row["code"])
            if source_id in seen:
                raise ProviderDataError(self.provider_id, "duplicate instrument source identifier")
            seen.add(source_id)
            exchange, source_code, display_ticker = _source_identity(source_id)
            binding = bindings.get(source_id)
            resolved = binding is not None
            reasons = () if resolved else (
                "source_proven_board_missing",
                "source_proven_security_form_missing",
                "stable_identity_unproven",
            )
            observations.append(
                ChinaAshareInstrumentSourceObservationV1(
                    source_security_id=source_id,
                    source_code=source_code,
                    display_ticker=display_ticker,
                    name=_required_text(row["code_name"], field_name="code_name"),
                    exchange=exchange,
                    board=binding.board if binding is not None else ChinaAshareBoard.UNKNOWN,
                    security_form=(
                        binding.security_form
                        if binding is not None
                        else ChinaAshareSecurityForm.UNKNOWN
                    ),
                    listing_status=ChinaAshareListingStatus.LISTED,
                    as_of_date=query.as_of_date,
                    instrument_id=binding.instrument_id if binding is not None else None,
                    resolution_status=(
                        ChinaAshareIdentityResolutionStatus.RESOLVED
                        if resolved
                        else ChinaAshareIdentityResolutionStatus.QUARANTINED
                    ),
                    source=self.provider_id,
                    source_available_at=None,
                    ingested_at=ingested_at,
                    quality_status=(
                        QualityStatus.VALID if resolved else QualityStatus.PENDING_REVIEW
                    ),
                    reason_codes=reasons,
                )
            )
            trading_status = _trading_status(row["tradeStatus"])
            source_states.append(
                ChinaAshareSourceSecuritySnapshotStateV1(
                    source_security_id=source_id,
                    session_date=query.as_of_date,
                    trading_status=trading_status,
                    source=self.provider_id,
                    source_available_at=None,
                    ingested_at=ingested_at,
                    quality_status=(
                        QualityStatus.WARNING
                        if trading_status is ChinaAshareTradingStatus.UNKNOWN
                        else QualityStatus.VALID
                    ),
                    reason_codes=(
                        ("source_available_time_unreported", "trading_status_unavailable")
                        if trading_status is ChinaAshareTradingStatus.UNKNOWN
                        else ("source_available_time_unreported",)
                    ),
                )
            )
        return ChinaAshareInstrumentSourceBatchV1(
            provider_id=self.provider_id,
            query=query,
            instruments=tuple(
                sorted(observations, key=lambda item: item.source_security_id)
            ),
            source_states=tuple(
                sorted(source_states, key=lambda item: item.source_security_id)
            ),
            source_request_count=1,
        )

    def get_daily_observations(
        self,
        query: ChinaAshareSourceDailyQuery,
        *,
        identity_bindings: tuple[ChinaAshareIdentityBindingV1, ...],
    ) -> ChinaAshareDailySourceBatchV1:
        bindings = _required_bindings(query, identity_bindings, self.provider_id)
        ingested_at = self._utc_now()
        bars: list[ChinaAshareDailyBarV1] = []
        states: list[ChinaAshareDailyTradingStateV1] = []
        seen_rows: set[tuple[str, date]] = set()
        for source_id in query.source_security_ids:
            rows = self._read_cursor(
                self._session.query_history_k_data_plus(
                    source_id,
                    ",".join(_DAILY_FIELDS),
                    start_date=query.start_date.isoformat(),
                    end_date=query.end_date.isoformat(),
                    frequency="d",
                    adjustflag="3",
                ),
                required_fields=_DAILY_FIELDS,
            )
            binding = bindings[source_id]
            exchange, _, _ = _source_identity(source_id)
            for row in rows:
                row_source_id = _source_security_id(row["code"])
                if row_source_id != source_id:
                    raise ProviderDataError(self.provider_id, "daily row security differs from request")
                session_date = _iso_date(row["date"], field_name="date")
                if not query.start_date <= session_date <= query.end_date:
                    raise ProviderDataError(self.provider_id, "daily row falls outside requested interval")
                business_key = (source_id, session_date)
                if business_key in seen_rows:
                    raise ProviderDataError(self.provider_id, "duplicate daily source row")
                seen_rows.add(business_key)
                trading_status = _trading_status(row["tradestatus"])
                risk_warning = _risk_warning_status(row["isST"])
                reasons = [
                    "price_limit_requires_official_rule_resolution",
                    "source_available_time_unreported",
                ]
                if risk_warning is ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED:
                    reasons.append("risk_warning_subtype_unavailable")
                elif risk_warning is ChinaAshareRiskWarningStatus.UNKNOWN:
                    reasons.append("risk_warning_state_unavailable")
                states.append(
                    ChinaAshareDailyTradingStateV1(
                        instrument_id=binding.instrument_id,
                        session_date=session_date,
                        exchange=exchange,
                        board=binding.board,
                        trading_status=trading_status,
                        risk_warning_status=risk_warning,
                        price_limit_regime=ChinaAsharePriceLimitRegime.UNKNOWN,
                        pre_close=_optional_decimal(row["preclose"], field_name="preclose"),
                        up_limit=None,
                        down_limit=None,
                        exact_limit_prices_source_observed=False,
                        source=self.provider_id,
                        source_available_at=None,
                        ingested_at=ingested_at,
                        quality_status=QualityStatus.WARNING,
                        reason_codes=tuple(reasons),
                    )
                )
                if trading_status is ChinaAshareTradingStatus.SUSPENDED:
                    continue
                bars.append(
                    ChinaAshareDailyBarV1(
                        instrument_id=binding.instrument_id,
                        session_date=session_date,
                        open=_required_decimal(row["open"], field_name="open"),
                        high=_required_decimal(row["high"], field_name="high"),
                        low=_required_decimal(row["low"], field_name="low"),
                        close=_required_decimal(row["close"], field_name="close"),
                        pre_close=_required_decimal(row["preclose"], field_name="preclose"),
                        volume_shares=_required_decimal(row["volume"], field_name="volume"),
                        turnover_amount_cny=_required_decimal(row["amount"], field_name="amount"),
                        source=self.provider_id,
                        source_record_id=f"{source_id}:{session_date.isoformat()}",
                        source_available_at=None,
                        ingested_at=ingested_at,
                        revision=1,
                        quality_status=QualityStatus.WARNING,
                        reason_codes=("source_available_time_unreported",),
                    )
                )
        bars.sort(key=lambda item: (str(item.instrument_id), item.session_date))
        states.sort(key=lambda item: (str(item.instrument_id), item.session_date))
        return ChinaAshareDailySourceBatchV1(
            provider_id=self.provider_id,
            query=query,
            bars=tuple(bars),
            trading_states=tuple(states),
            source_request_count=len(query.source_security_ids),
        )

    def get_adjustment_factor_observations(
        self,
        query: ChinaAshareSourceDailyQuery,
        *,
        identity_bindings: tuple[ChinaAshareIdentityBindingV1, ...],
    ) -> tuple[ChinaAshareAdjustmentFactorObservationV1, ...]:
        bindings = _required_bindings(query, identity_bindings, self.provider_id)
        ingested_at = self._utc_now()
        observations: list[ChinaAshareAdjustmentFactorObservationV1] = []
        seen: set[tuple[str, date]] = set()
        for source_id in query.source_security_ids:
            rows = self._read_cursor(
                self._session.query_adjust_factor(
                    source_id,
                    start_date=query.start_date.isoformat(),
                    end_date=query.end_date.isoformat(),
                ),
                required_fields=_ADJUSTMENT_FIELDS,
            )
            for row in rows:
                row_source_id = _source_security_id(row["code"])
                if row_source_id != source_id:
                    raise ProviderDataError(self.provider_id, "adjustment row security differs from request")
                session_date = _iso_date(
                    row["dividOperateDate"],
                    field_name="dividOperateDate",
                )
                if not query.start_date <= session_date <= query.end_date:
                    raise ProviderDataError(self.provider_id, "adjustment row falls outside requested interval")
                key = (source_id, session_date)
                if key in seen:
                    raise ProviderDataError(self.provider_id, "duplicate adjustment source row")
                seen.add(key)
                observations.append(
                    ChinaAshareAdjustmentFactorObservationV1(
                        instrument_id=bindings[source_id].instrument_id,
                        session_date=session_date,
                        provider_factor=_required_decimal(
                            row["adjustFactor"],
                            field_name="adjustFactor",
                        ),
                        fore_adjust_factor=_required_decimal(
                            row["foreAdjustFactor"],
                            field_name="foreAdjustFactor",
                        ),
                        back_adjust_factor=_required_decimal(
                            row["backAdjustFactor"],
                            field_name="backAdjustFactor",
                        ),
                        provider_semantics=(
                            "BaoStock adjustFactor, foreAdjustFactor, and "
                            "backAdjustFactor source observation; direction and "
                            "total-return semantics are not reconciled"
                        ),
                        source=self.provider_id,
                        source_available_at=None,
                        ingested_at=ingested_at,
                        normalized_return_authorized=False,
                        quality_status=QualityStatus.WARNING,
                        reason_codes=(
                            "return_semantics_unreconciled",
                            "source_available_time_unreported",
                        ),
                    )
                )
        return tuple(
            sorted(
                observations,
                key=lambda item: (str(item.instrument_id), item.session_date),
            )
        )

    def _read_cursor(
        self,
        cursor: BaoStockCursor,
        *,
        required_fields: tuple[str, ...],
    ) -> tuple[Mapping[str, str], ...]:
        if str(cursor.error_code) != "0":
            raise ProviderUnavailableError(self.provider_id, "BaoStock source request failed")
        fields = tuple(cursor.fields)
        if len(fields) != len(set(fields)) or any(field not in fields for field in required_fields):
            raise ProviderDataError(self.provider_id, "BaoStock response schema differs")
        rows: list[Mapping[str, str]] = []
        while str(cursor.error_code) == "0" and cursor.next():
            values = cursor.get_row_data()
            if len(values) != len(fields):
                raise ProviderDataError(self.provider_id, "BaoStock response row width differs")
            rows.append(dict(zip(fields, values, strict=True)))
        if str(cursor.error_code) != "0":
            raise ProviderUnavailableError(self.provider_id, "BaoStock cursor failed during read")
        return tuple(rows)

    def _utc_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ProviderDataError(self.provider_id, "adapter clock returned a naive datetime")
        return value.astimezone(UTC)


def _binding_map(
    bindings: tuple[ChinaAshareIdentityBindingV1, ...],
) -> dict[str, ChinaAshareIdentityBindingV1]:
    result: dict[str, ChinaAshareIdentityBindingV1] = {}
    instrument_ids = set()
    for binding in bindings:
        if binding.source_security_id in result or binding.instrument_id in instrument_ids:
            raise ValueError("identity bindings must be one-to-one")
        result[binding.source_security_id] = binding
        instrument_ids.add(binding.instrument_id)
    return result


def _required_bindings(
    query: ChinaAshareSourceDailyQuery,
    bindings: tuple[ChinaAshareIdentityBindingV1, ...],
    provider_id: str,
) -> dict[str, ChinaAshareIdentityBindingV1]:
    result = _binding_map(bindings)
    missing = tuple(item for item in query.source_security_ids if item not in result)
    if missing:
        raise ProviderDataError(provider_id, "daily source request lacks stable identity bindings")
    return result


def _source_security_id(value: str) -> str:
    normalized = _required_text(value, field_name="code").lower()
    _source_identity(normalized)
    return normalized


def _source_identity(
    source_security_id: str,
) -> tuple[ChinaAshareExchange, str, str]:
    try:
        prefix, source_code = source_security_id.split(".", 1)
    except ValueError as exc:
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            "BaoStock security identifier is malformed",
        ) from exc
    exchanges = {
        "sh": (ChinaAshareExchange.SSE, "SH"),
        "sz": (ChinaAshareExchange.SZSE, "SZ"),
        "bj": (ChinaAshareExchange.BSE, "BJ"),
    }
    if prefix not in exchanges or len(source_code) != 6 or not source_code.isdigit():
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            "BaoStock security identifier is malformed",
        )
    exchange, suffix = exchanges[prefix]
    return exchange, source_code, f"{source_code}.{suffix}"


def _trading_status(value: str) -> ChinaAshareTradingStatus:
    normalized = str(value).strip()
    if normalized == "1":
        return ChinaAshareTradingStatus.TRADING
    if normalized == "0":
        return ChinaAshareTradingStatus.SUSPENDED
    return ChinaAshareTradingStatus.UNKNOWN


def _risk_warning_status(value: str) -> ChinaAshareRiskWarningStatus:
    normalized = str(value).strip()
    if normalized == "0":
        return ChinaAshareRiskWarningStatus.NONE
    if normalized == "1":
        return ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED
    return ChinaAshareRiskWarningStatus.UNKNOWN


def _iso_date(value: str, *, field_name: str) -> date:
    try:
        return date.fromisoformat(_required_text(value, field_name=field_name))
    except ValueError as exc:
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            f"BaoStock {field_name} is invalid",
        ) from exc


def _required_decimal(value: str, *, field_name: str) -> Decimal:
    normalized = _required_text(value, field_name=field_name)
    try:
        result = Decimal(normalized)
    except InvalidOperation as exc:
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            f"BaoStock {field_name} is invalid",
        ) from exc
    if not result.is_finite():
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            f"BaoStock {field_name} is invalid",
        )
    return result


def _optional_decimal(value: str, *, field_name: str) -> Decimal | None:
    if value is None or not str(value).strip():
        return None
    return _required_decimal(value, field_name=field_name)


def _required_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProviderDataError(
            BAOSTOCK_ASHARE_PROVIDER_ID,
            f"BaoStock {field_name} is missing",
        )
    return value.strip()
