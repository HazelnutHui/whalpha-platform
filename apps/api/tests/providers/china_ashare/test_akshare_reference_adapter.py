from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAshareIdentityResolutionStatus,
    ChinaAshareSecurityForm,
)
from tip_api.providers.china_ashare import (
    AkshareAshareReferenceAdapter,
    ChinaAshareSourceInstrumentQuery,
)
from tip_api.providers.market_data import ProviderDataError


NOW = datetime(2026, 9, 16, 8, 0, tzinfo=UTC)


class FakeTable:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def to_dict(self, orient: str) -> list[dict[str, object]]:
        assert orient == "records"
        return self.rows


class FakeAkshareModule:
    def stock_info_sh_name_code(self, symbol: str) -> FakeTable:
        rows = {
            "主板A股": [
                {"证券代码": "600519", "证券简称": "贵州茅台", "上市日期": "2001-08-27"}
            ],
            "科创板": [
                {"证券代码": "688001", "证券简称": "示例科创", "上市日期": "2019-07-22"}
            ],
        }
        return FakeTable(rows[symbol])

    def stock_info_sz_name_code(self, symbol: str) -> FakeTable:
        rows = {
            "A股列表": [
                {"板块": "主板", "A股代码": "000001", "A股简称": "平安银行", "A股上市日期": "1991-04-03"},
                {"板块": "创业板", "A股代码": "300001", "A股简称": "示例创业", "A股上市日期": "2009-10-30"},
            ],
        }
        return FakeTable(rows[symbol])

    def stock_info_bj_name_code(self) -> FakeTable:
        return FakeTable(
            [{"证券代码": "430017", "证券简称": "星昊医药", "上市日期": "2023-05-31"}]
        )

    def stock_info_sh_delist(self, symbol: str) -> FakeTable:
        assert symbol == "全部"
        return FakeTable(
            [{"公司代码": "600001", "公司简称": "示例沪退", "上市日期": "1998-01-22", "暂停上市日期": "2009-12-29"}]
        )

    def stock_info_sz_delist(self, symbol: str) -> FakeTable:
        assert symbol == "终止上市公司"
        return FakeTable(
            [{"证券代码": "000003", "证券简称": "示例深退", "上市日期": "1991-07-03", "终止上市日期": "2002-06-14"}]
        )


def test_official_lists_prove_form_and_board_but_not_stable_identity() -> None:
    adapter = AkshareAshareReferenceAdapter(
        module=FakeAkshareModule(),
        clock=lambda: NOW,
    )

    rows = adapter.get_current_instrument_observations(
        ChinaAshareSourceInstrumentQuery(as_of_date=date(2026, 9, 16))
    )

    assert len(rows) == 5
    assert all(
        row.resolution_status is ChinaAshareIdentityResolutionStatus.QUARANTINED
        and row.instrument_id is None
        for row in rows
    )
    by_id = {row.source_security_id: row for row in rows}
    assert by_id["sh.600519"].board is ChinaAshareBoard.SSE_MAIN
    assert by_id["sh.688001"].board is ChinaAshareBoard.STAR
    assert by_id["sz.300001"].board is ChinaAshareBoard.CHINEXT
    assert by_id["bj.430017"].exchange is ChinaAshareExchange.BSE
    assert by_id["bj.430017"].security_form is ChinaAshareSecurityForm.COMMON_STOCK


def test_current_list_endpoint_cannot_be_backdated() -> None:
    adapter = AkshareAshareReferenceAdapter(
        module=FakeAkshareModule(),
        clock=lambda: NOW,
    )

    with pytest.raises(ProviderDataError, match="cannot be backdated"):
        adapter.get_current_instrument_observations(
            ChinaAshareSourceInstrumentQuery(as_of_date=date(2026, 9, 15))
        )


def test_lifecycle_sources_preserve_ambiguous_sse_semantics() -> None:
    adapter = AkshareAshareReferenceAdapter(
        module=FakeAkshareModule(),
        clock=lambda: NOW,
    )

    rows = adapter.get_lifecycle_observations(
        ChinaAshareSourceInstrumentQuery(as_of_date=date(2026, 9, 16))
    )

    assert len(rows) == 2
    by_key = {row.source_subject_key: row for row in rows}
    assert by_key["sse_issuer.600001"].event_type.value == (
        "paused_or_terminated_listing"
    )
    assert by_key["sse_issuer.600001"].source_security_id is None
    assert "source_status_conflates_pause_and_termination" in (
        by_key["sse_issuer.600001"].reason_codes
    )
    assert "issuer_security_identity_unproven" in (
        by_key["sse_issuer.600001"].reason_codes
    )
    assert by_key["szse_security.000003"].event_type.value == "terminated_listing"
    assert by_key["szse_security.000003"].source_security_id == "sz.000003"


def test_unknown_szse_board_fails_closed() -> None:
    module = FakeAkshareModule()
    module.stock_info_sz_name_code = lambda symbol: (
        FakeTable(
            [{"板块": "未知板", "A股代码": "000001", "A股简称": "示例", "A股上市日期": "1991-04-03"}]
        )
        if symbol == "A股列表"
        else FakeTable([])
    )
    adapter = AkshareAshareReferenceAdapter(module=module, clock=lambda: NOW)

    with pytest.raises(ProviderDataError, match="board is unsupported"):
        adapter.get_current_instrument_observations(
            ChinaAshareSourceInstrumentQuery(as_of_date=date(2026, 9, 16))
        )


def test_empty_official_list_is_not_treated_as_an_empty_board() -> None:
    module = FakeAkshareModule()
    module.stock_info_bj_name_code = lambda: FakeTable([])
    adapter = AkshareAshareReferenceAdapter(module=module, clock=lambda: NOW)

    with pytest.raises(ProviderDataError, match="returned no rows"):
        adapter.get_current_instrument_observations(
            ChinaAshareSourceInstrumentQuery(as_of_date=date(2026, 9, 16))
        )
