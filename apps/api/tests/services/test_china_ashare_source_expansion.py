from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from tip_api.contracts.china_ashare.v1.population import (
    ChinaAsharePopulationDisposition,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    completed_source_expansion_partition_indices,
    publish_china_ashare_source_expansion_partition,
    publish_china_ashare_source_expansion_plan,
    read_china_ashare_source_expansion_partition,
)
from tip_api.providers.china_ashare.baostock_source_expansion_adapter import (
    capture_baostock_source_expansion_partition,
)
from tip_api.services.china_ashare_source_expansion import (
    plan_china_ashare_source_expansion,
)


NOW = datetime(2026, 9, 17, 10, 0, tzinfo=UTC)


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


class FakeSession:
    def query_history_k_data_plus(
        self,
        code: str,
        fields: str,
        start_date: str = "",
        end_date: str = "",
        frequency: str = "d",
        adjustflag: str = "3",
    ) -> FakeCursor:
        rows = []
        if code == "sh.600001":
            rows = [
                [
                    "2026-09-16",
                    code,
                    "10.00",
                    "10.50",
                    "9.90",
                    "10.20",
                    "10.00",
                    "1000",
                    "10200",
                    "1",
                    "0",
                ]
            ]
        return FakeCursor(
            fields=[
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
            ],
            rows=rows,
        )

    def query_adjust_factor(
        self, code: str, start_date: str = "", end_date: str = ""
    ) -> FakeCursor:
        rows = []
        if code == "sh.600001":
            rows = [[code, "2026-09-16", "0.8", "1.2", "1.0"]]
        return FakeCursor(
            fields=[
                "code",
                "dividOperateDate",
                "foreAdjustFactor",
                "backAdjustFactor",
                "adjustFactor",
            ],
            rows=rows,
        )


def _population():
    occurrences = (
        SimpleNamespace(
            source_security_id="sh.600001",
            listing_date=date(2000, 1, 1),
            disposition=ChinaAsharePopulationDisposition.RESOLVED,
            logical_fingerprint="1" * 64,
        ),
        SimpleNamespace(
            source_security_id="sz.000001",
            listing_date=date(2000, 1, 2),
            disposition=ChinaAsharePopulationDisposition.QUARANTINED,
            logical_fingerprint="2" * 64,
        ),
        SimpleNamespace(
            source_security_id="sz.000002",
            listing_date=date(2000, 1, 3),
            disposition=ChinaAsharePopulationDisposition.RESOLVED,
            logical_fingerprint="3" * 64,
        ),
    )
    return SimpleNamespace(
        occurrences=occurrences,
        report=SimpleNamespace(
            expansion_target_count=3,
            interval_start=date(2021, 9, 16),
            interval_end=date(2026, 9, 16),
        ),
        manifest=SimpleNamespace(
            logical_fingerprint="a" * 64,
            occurrence_set_fingerprint="b" * 64,
        ),
    )


def test_source_expansion_plan_is_partitioned_and_time_independent() -> None:
    first = plan_china_ashare_source_expansion(
        population_package=_population(), partition_size=2, registered_at=NOW
    )
    second = plan_china_ashare_source_expansion(
        population_package=_population(),
        partition_size=2,
        registered_at=NOW + timedelta(hours=1),
    )

    assert first.logical_fingerprint == second.logical_fingerprint
    assert first.registered_at != second.registered_at
    assert first.target_count == 3
    assert first.expected_source_request_count == 6
    assert tuple(len(item.targets) for item in first.partitions) == (2, 1)


def test_source_expansion_partition_capture_and_exact_reread(tmp_path: Path) -> None:
    plan = plan_china_ashare_source_expansion(
        population_package=_population(), partition_size=2, registered_at=NOW
    )
    plan_result = publish_china_ashare_source_expansion_plan(
        custody_root=tmp_path / "custody", plan=plan
    )
    partition = plan_result.plan.partitions[0]
    captured = capture_baostock_source_expansion_partition(
        session=FakeSession(),
        partition=partition,
        interval_start=plan.interval_start,
        interval_end=plan.interval_end,
        captured_at=NOW,
    )

    assert len(captured.daily_rows) == 1
    assert len(captured.adjustment_rows) == 1
    assert captured.daily_zero_row_ids == ("sz.000001",)
    assert captured.adjustment_zero_row_ids == ("sz.000001",)
    result = publish_china_ashare_source_expansion_partition(
        plan_result=plan_result,
        partition=partition,
        captured=captured,
        captured_at=NOW,
    )
    reread = read_china_ashare_source_expansion_partition(
        plan_result=plan_result, partition_index=0
    )

    assert result.manifest == reread.manifest
    assert reread.captured == captured
    assert reread.file_count == 3
    assert completed_source_expansion_partition_indices(
        plan_result=plan_result
    ) == (0,)
