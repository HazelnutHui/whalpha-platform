from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareBoard,
    ChinaAshareIdentityResolutionStatus,
    ChinaAshareRiskWarningStatus,
    ChinaAshareSecurityForm,
    ChinaAshareTradingStatus,
)
from tip_api.providers.china_ashare import (
    BaoStockAshareSourceAdapter,
    ChinaAshareIdentityBindingV1,
    ChinaAshareSourceDailyQuery,
    ChinaAshareSourceInstrumentQuery,
)
from tip_api.providers.market_data import ProviderDataError, ProviderUnavailableError


NOW = datetime(2026, 9, 16, 8, 0, tzinfo=UTC)
INSTRUMENT_ID = UUID("00000000-0000-0000-0000-000000006005")
FINGERPRINT = "a" * 64


@dataclass
class FakeCursor:
    fields: list[str]
    rows: list[list[str]]
    error_code: str = "0"
    error_msg: str = ""
    fail_after_rows: bool = False
    _index: int = field(default=-1, init=False)

    def next(self) -> bool:
        self._index += 1
        if self.fail_after_rows and self._index >= len(self.rows):
            self.error_code = "1001"
            self.error_msg = "simulated cursor failure"
            return False
        return self._index < len(self.rows)

    def get_row_data(self) -> list[str]:
        return self.rows[self._index]


@dataclass
class FakeBaoStockSession:
    instrument_cursor: FakeCursor
    daily_cursors: dict[str, FakeCursor]
    adjustment_cursors: dict[str, FakeCursor]
    history_calls: list[dict[str, str]] = field(default_factory=list)

    def query_all_stock(self, day: str = "") -> FakeCursor:
        return self.instrument_cursor

    def query_history_k_data_plus(
        self,
        code: str,
        fields: str,
        start_date: str = "",
        end_date: str = "",
        frequency: str = "d",
        adjustflag: str = "3",
    ) -> FakeCursor:
        self.history_calls.append(
            {
                "code": code,
                "fields": fields,
                "start_date": start_date,
                "end_date": end_date,
                "frequency": frequency,
                "adjustflag": adjustflag,
            }
        )
        return self.daily_cursors[code]

    def query_adjust_factor(
        self,
        code: str,
        start_date: str = "",
        end_date: str = "",
    ) -> FakeCursor:
        return self.adjustment_cursors[code]


def _instrument_cursor() -> FakeCursor:
    return FakeCursor(
        fields=["code", "tradeStatus", "code_name"],
        rows=[["sh.600519", "1", "贵州茅台"]],
    )


def _daily_cursor(*, duplicate: bool = False) -> FakeCursor:
    fields = [
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
    ]
    active = [
        "2026-09-14",
        "sh.600519",
        "1500.00",
        "1530.00",
        "1490.00",
        "1520.00",
        "1498.00",
        "123400",
        "186500000.00",
        "1",
        "0",
    ]
    suspended = [
        "2026-09-15",
        "sh.600519",
        "",
        "",
        "",
        "",
        "1520.00",
        "0",
        "0",
        "0",
        "1",
    ]
    rows = [active, suspended]
    if duplicate:
        rows.append(active.copy())
    return FakeCursor(fields=fields, rows=rows)


def _adjustment_cursor() -> FakeCursor:
    return FakeCursor(
        fields=[
            "code",
            "dividOperateDate",
            "foreAdjustFactor",
            "backAdjustFactor",
            "adjustFactor",
        ],
        rows=[["sh.600519", "2026-09-14", "0.75", "1.25", "1.125"]],
    )


def _session(*, duplicate_daily: bool = False) -> FakeBaoStockSession:
    return FakeBaoStockSession(
        instrument_cursor=_instrument_cursor(),
        daily_cursors={"sh.600519": _daily_cursor(duplicate=duplicate_daily)},
        adjustment_cursors={"sh.600519": _adjustment_cursor()},
    )


def _binding() -> ChinaAshareIdentityBindingV1:
    return ChinaAshareIdentityBindingV1(
        source_security_id="sh.600519",
        instrument_id=INSTRUMENT_ID,
        board=ChinaAshareBoard.SSE_MAIN,
        security_form=ChinaAshareSecurityForm.COMMON_STOCK,
        evidence_fingerprints=(FINGERPRINT,),
    )


def _daily_query() -> ChinaAshareSourceDailyQuery:
    return ChinaAshareSourceDailyQuery(
        source_security_ids=("sh.600519",),
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 15),
    )


def test_instrument_name_and_code_do_not_create_positive_identity() -> None:
    adapter = BaoStockAshareSourceAdapter(session=_session(), clock=lambda: NOW)

    rows = adapter.get_instrument_observations(
        ChinaAshareSourceInstrumentQuery(as_of_date=date(2026, 9, 16))
    )

    assert len(rows) == 1
    assert rows[0].resolution_status is ChinaAshareIdentityResolutionStatus.QUARANTINED
    assert rows[0].instrument_id is None
    assert rows[0].board is ChinaAshareBoard.UNKNOWN
    assert rows[0].security_form is ChinaAshareSecurityForm.UNKNOWN
    assert "stable_identity_unproven" in rows[0].reason_codes


def test_instrument_snapshot_preserves_provider_keyed_trading_state() -> None:
    adapter = BaoStockAshareSourceAdapter(session=_session(), clock=lambda: NOW)

    batch = adapter.get_instrument_snapshot(
        ChinaAshareSourceInstrumentQuery(as_of_date=date(2026, 9, 16))
    )

    assert len(batch.instruments) == 1
    assert len(batch.source_states) == 1
    assert batch.source_states[0].source_security_id == "sh.600519"
    assert batch.source_states[0].trading_status is ChinaAshareTradingStatus.TRADING
    assert batch.source_request_count == 1


def test_separately_proven_binding_can_resolve_source_observation() -> None:
    adapter = BaoStockAshareSourceAdapter(session=_session(), clock=lambda: NOW)

    rows = adapter.get_instrument_observations(
        ChinaAshareSourceInstrumentQuery(as_of_date=date(2026, 9, 16)),
        identity_bindings=(_binding(),),
    )

    assert rows[0].resolution_status is ChinaAshareIdentityResolutionStatus.RESOLVED
    assert rows[0].instrument_id == INSTRUMENT_ID
    assert rows[0].board is ChinaAshareBoard.SSE_MAIN


def test_daily_request_is_unadjusted_and_suspension_does_not_fabricate_bar() -> None:
    session = _session()
    adapter = BaoStockAshareSourceAdapter(session=session, clock=lambda: NOW)

    batch = adapter.get_daily_observations(
        _daily_query(),
        identity_bindings=(_binding(),),
    )

    assert len(batch.trading_states) == 2
    assert len(batch.bars) == 1
    assert batch.bars[0].adjustment_basis == "unadjusted"
    assert batch.bars[0].close == Decimal("1520.00")
    assert batch.trading_states[1].trading_status is ChinaAshareTradingStatus.SUSPENDED
    assert (
        batch.trading_states[1].risk_warning_status
        is ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED
    )
    assert batch.trading_states[1].exact_limit_prices_source_observed is False
    assert session.history_calls[0]["adjustflag"] == "3"


def test_daily_history_requires_stable_identity_binding() -> None:
    adapter = BaoStockAshareSourceAdapter(session=_session(), clock=lambda: NOW)

    with pytest.raises(ProviderDataError, match="stable identity"):
        adapter.get_daily_observations(_daily_query(), identity_bindings=())


def test_adjustment_factor_remains_non_authoritative_for_returns() -> None:
    adapter = BaoStockAshareSourceAdapter(session=_session(), clock=lambda: NOW)

    rows = adapter.get_adjustment_factor_observations(
        _daily_query(),
        identity_bindings=(_binding(),),
    )

    assert len(rows) == 1
    assert rows[0].provider_factor == Decimal("1.125")
    assert rows[0].fore_adjust_factor == Decimal("0.75")
    assert rows[0].back_adjust_factor == Decimal("1.25")
    assert rows[0].normalized_return_authorized is False
    assert "return_semantics_unreconciled" in rows[0].reason_codes


def test_duplicate_daily_source_row_is_rejected() -> None:
    adapter = BaoStockAshareSourceAdapter(
        session=_session(duplicate_daily=True),
        clock=lambda: NOW,
    )

    with pytest.raises(ProviderDataError, match="duplicate daily"):
        adapter.get_daily_observations(
            _daily_query(),
            identity_bindings=(_binding(),),
        )


def test_cursor_error_is_not_silently_treated_as_empty_data() -> None:
    session = _session()
    session.instrument_cursor.error_code = "1001"
    adapter = BaoStockAshareSourceAdapter(session=session, clock=lambda: NOW)

    with pytest.raises(ProviderUnavailableError, match="source request failed"):
        adapter.get_instrument_observations(
            ChinaAshareSourceInstrumentQuery(as_of_date=date(2026, 9, 16))
        )


def test_empty_instrument_snapshot_is_not_treated_as_an_empty_market() -> None:
    session = _session()
    session.instrument_cursor.rows = []
    adapter = BaoStockAshareSourceAdapter(session=session, clock=lambda: NOW)

    with pytest.raises(ProviderDataError, match="returned no rows"):
        adapter.get_instrument_observations(
            ChinaAshareSourceInstrumentQuery(as_of_date=date(2026, 9, 16))
        )


def test_daily_query_deduplicates_and_orders_source_ids() -> None:
    query = ChinaAshareSourceDailyQuery(
        source_security_ids=("SZ.000001", "sh.600519", "sz.000001"),
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 15),
    )

    assert query.source_security_ids == ("sh.600519", "sz.000001")
