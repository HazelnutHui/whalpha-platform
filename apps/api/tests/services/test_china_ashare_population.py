from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from tip_api.contracts.china_ashare.v1.population import (
    ChinaAsharePopulationDisposition,
    build_baostock_basic_record,
)
from tip_api.persistence.china_ashare_population_package import (
    publish_china_ashare_population_package,
    read_china_ashare_population_package,
)
from tip_api.providers.china_ashare.baostock_population_adapter import (
    capture_baostock_security_basic,
)
from tip_api.providers.market_data import ProviderDataError
from tip_api.services.china_ashare_population import build_five_year_population


NOW = datetime(2026, 9, 17, 8, 0, tzinfo=UTC)
IDENTITY_FINGERPRINT = "a" * 64


@dataclass
class FakeCursor:
    fields: list[str]
    rows: list[list[str]]
    error_code: str = "0"
    error_msg: str = ""
    _index: int = field(default=-1, init=False)

    def next(self) -> bool:
        self._index += 1
        return self._index < len(self.rows)

    def get_row_data(self) -> list[str]:
        return self.rows[self._index]


@dataclass
class FakeBasicSession:
    cursor: FakeCursor

    def query_stock_basic(self, code: str = "", code_name: str = "") -> FakeCursor:
        return self.cursor


def _basic(source_id: str, listing_date: date, *, out_date: date | None = None):
    return build_baostock_basic_record(
        source_security_id=source_id,
        current_name=source_id,
        listing_date=listing_date,
        out_date=out_date,
        provider_type="1",
        provider_status="1" if out_date is None else "0",
        ingested_at=NOW,
    )


def _identity_package(tmp_path: Path):
    raw = tmp_path / "identity"
    (raw / "raw").mkdir(parents=True)
    payloads = {
        "sse_main_current": json.dumps(
            {
                "result": [
                    {
                        "A_STOCK_CODE": "600001",
                        "SEC_NAME_CN": "上证主板",
                        "LIST_DATE": "20000101",
                    }
                ]
            }
        ).encode(),
        "sse_star_current": json.dumps(
            {
                "result": [
                    {
                        "A_STOCK_CODE": "688001",
                        "SEC_NAME_CN": "科创样本",
                        "LIST_DATE": "20200101",
                    }
                ]
            }
        ).encode(),
        "szse_a_current": b"current-xlsx",
        "sse_delist": json.dumps(
            {
                "result": [
                    {
                        "A_STOCK_CODE": "600002",
                        "B_STOCK_CODE": "900002",
                        "COMPANY_ABBR": "上证退市",
                        "LIST_DATE": "20000102",
                        "DELIST_DATE": "20220102",
                        "LIST_BOARD": "1",
                        "STOCK_TYPE": "1",
                    },
                    {
                        "A_STOCK_CODE": "688002",
                        "B_STOCK_CODE": "-",
                        "COMPANY_ABBR": "科创退市",
                        "LIST_DATE": "20200102",
                        "DELIST_DATE": "20230102",
                        "LIST_BOARD": "2",
                        "STOCK_TYPE": "8",
                    },
                    {
                        "A_STOCK_CODE": "600002",
                        "B_STOCK_CODE": "900002",
                        "COMPANY_ABBR": "沪市B股",
                        "LIST_DATE": "20000102",
                        "DELIST_DATE": "20220102",
                        "LIST_BOARD": "1",
                        "STOCK_TYPE": "2",
                    },
                ]
            }
        ).encode(),
        "szse_delist": b"delist-xlsx",
    }
    artifacts = []
    for kind, payload in payloads.items():
        suffix = "json" if payload.startswith(b"{") else "xlsx"
        relative_path = f"raw/{kind}.{suffix}"
        path = raw / relative_path
        path.write_bytes(payload)
        artifacts.append(
            SimpleNamespace(
                artifact_kind=kind,
                relative_path=relative_path,
                content_type=(
                    "application/json"
                    if suffix == "json"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                byte_size=len(payload),
                physical_sha256=hashlib.sha256(payload).hexdigest(),
            )
        )
    return SimpleNamespace(
        package_path=raw,
        manifest=SimpleNamespace(
            logical_fingerprint=IDENTITY_FINGERPRINT,
            raw_artifacts=tuple(artifacts),
        ),
    )


def _mock_excel(monkeypatch: pytest.MonkeyPatch) -> None:
    def read_excel(stream):
        if stream.getvalue() == b"current-xlsx":
            return pd.DataFrame(
                [
                    {
                        "A股代码": "000001",
                        "A股简称": "深证主板",
                        "板块": "主板",
                        "A股上市日期": "20000103",
                    }
                ]
            )
        return pd.DataFrame(
            [
                {
                    "证券代码": "000003",
                    "证券简称": "深证退市",
                    "上市日期": "20000104",
                    "终止上市日期": "20220104",
                },
                {
                    "证券代码": "200001",
                    "证券简称": "深证B股",
                    "上市日期": "20000105",
                    "终止上市日期": "20220105",
                },
            ]
        )

    monkeypatch.setattr(pd, "read_excel", read_excel)


def test_baostock_population_capture_filters_non_stock_rows() -> None:
    session = FakeBasicSession(
        FakeCursor(
            fields=["code", "code_name", "ipoDate", "outDate", "type", "status"],
            rows=[
                ["sh.600001", "上证主板", "2000-01-01", "", "1", "1"],
                ["sh.000001", "上证指数", "1991-07-15", "", "2", "1"],
            ],
        )
    )

    records = capture_baostock_security_basic(session=session, ingested_at=NOW)

    assert tuple(item.source_security_id for item in records) == ("sh.600001",)


def test_baostock_population_capture_rejects_duplicate_source_ids() -> None:
    session = FakeBasicSession(
        FakeCursor(
            fields=["code", "code_name", "ipoDate", "outDate", "type", "status"],
            rows=[
                ["sh.600001", "一", "2000-01-01", "", "1", "1"],
                ["sh.600001", "二", "2000-01-01", "", "1", "1"],
            ],
        )
    )

    with pytest.raises(ProviderDataError, match="duplicated"):
        capture_baostock_security_basic(session=session, ingested_at=NOW)


def test_population_freeze_partitions_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity_package(tmp_path)
    _mock_excel(monkeypatch)
    basic = (
        _basic("sh.600001", date(2000, 1, 1)),
        _basic("sh.600002", date(2000, 1, 1), out_date=date(2021, 12, 31)),
        _basic("sh.688001", date(2020, 1, 1)),
        _basic("sh.688002", date(2020, 1, 2), out_date=date(2023, 1, 1)),
        _basic("sz.000001", date(2000, 1, 3)),
        _basic("sz.000003", date(2000, 1, 4), out_date=date(2022, 1, 3)),
    )

    occurrences, report = build_five_year_population(
        identity_lifecycle_package=identity,
        baostock_basic_records=basic,
        interval_start=date(2021, 9, 16),
        interval_end=date(2026, 9, 16),
        evaluated_at=NOW,
    )

    assert report.official_candidate_count == 8
    assert report.resolved_count == 5
    assert report.quarantined_count == 1
    assert report.outside_scope_count == 2
    assert report.expansion_target_count == 6
    assert report.current_resolved_count == 3
    assert report.delisted_resolved_count == 2
    assert report.cross_source_listing_date_conflict_count == 1
    assert report.unresolved_board_count == 1
    assert report.research_backtest_authorized is False
    dispositions = {
        item.source_security_id: item.disposition for item in occurrences
    }
    assert dispositions["sh.688002"] is ChinaAsharePopulationDisposition.RESOLVED
    assert dispositions["sz.000003"] is ChinaAsharePopulationDisposition.QUARANTINED
    assert dispositions["sh.900002"] is ChinaAsharePopulationDisposition.OUTSIDE_SCOPE
    result = publish_china_ashare_population_package(
        custody_root=tmp_path / "custody",
        identity_lifecycle_package=identity,
        baostock_basic_records=basic,
        occurrences=occurrences,
        report=report,
        created_at=NOW,
    )
    reread = read_china_ashare_population_package(package_path=result.package_path)
    assert reread.manifest == result.manifest
    assert reread.report == report
    assert reread.occurrences == occurrences
    assert reread.status == "exact_reread_complete"
