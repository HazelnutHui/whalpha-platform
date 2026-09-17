from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.china_ashare.v1.population import (
    ChinaAsharePopulationDisposition,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    completed_source_expansion_partition_indices,
    publish_china_ashare_source_expansion_partition,
    publish_china_ashare_source_expansion_plan,
    read_china_ashare_source_expansion_partition,
)
from tip_api.persistence.china_ashare_normalized_expansion_package import (
    publish_china_ashare_normalized_expansion_partition,
    read_china_ashare_normalized_expansion_partition,
)
from tip_api.persistence.china_ashare_source_expansion_completion import (
    publish_china_ashare_source_expansion_completion,
    read_china_ashare_source_expansion_completion,
)
from tip_api.providers.china_ashare.baostock_source_expansion_adapter import (
    capture_baostock_source_expansion_partition,
)
from tip_api.services.china_ashare_source_expansion import (
    plan_china_ashare_source_expansion,
)
from tip_api.services.china_ashare_source_expansion_completion import (
    build_china_ashare_source_expansion_completion,
)
from tip_api.services.china_ashare_source_expansion_normalization import (
    normalize_china_ashare_source_expansion_partition,
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


class FakeSessionWithQuarantineRows(FakeSession):
    def query_history_k_data_plus(
        self,
        code: str,
        fields: str,
        start_date: str = "",
        end_date: str = "",
        frequency: str = "d",
        adjustflag: str = "3",
    ) -> FakeCursor:
        if code != "sz.000001":
            return super().query_history_k_data_plus(
                code,
                fields,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag=adjustflag,
            )
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
            rows=[
                [
                    "2026-09-16",
                    code,
                    "8.00",
                    "8.20",
                    "7.90",
                    "8.10",
                    "8.00",
                    "2000",
                    "16100",
                    "1",
                    "0",
                ]
            ],
        )

    def query_adjust_factor(
        self, code: str, start_date: str = "", end_date: str = ""
    ) -> FakeCursor:
        if code != "sz.000001":
            return super().query_adjust_factor(
                code, start_date=start_date, end_date=end_date
            )
        return FakeCursor(
            fields=[
                "code",
                "dividOperateDate",
                "foreAdjustFactor",
                "backAdjustFactor",
                "adjustFactor",
            ],
            rows=[[code, "2026-09-16", "1.0", "1.0", "1.0"]],
        )


def _population():
    occurrences = (
        SimpleNamespace(
            source_security_id="sh.600001",
            listing_date=date(2000, 1, 1),
            disposition=ChinaAsharePopulationDisposition.RESOLVED,
            instrument_id=UUID("00000000-0000-0000-0000-000000000001"),
            exchange=ChinaAshareExchange.SSE,
            board=ChinaAshareBoard.SSE_MAIN,
            logical_fingerprint="1" * 64,
        ),
        SimpleNamespace(
            source_security_id="sz.000001",
            listing_date=date(2000, 1, 2),
            disposition=ChinaAsharePopulationDisposition.QUARANTINED,
            instrument_id=None,
            exchange=ChinaAshareExchange.SZSE,
            board=ChinaAshareBoard.UNKNOWN,
            logical_fingerprint="2" * 64,
        ),
        SimpleNamespace(
            source_security_id="sz.000002",
            listing_date=date(2000, 1, 3),
            disposition=ChinaAsharePopulationDisposition.RESOLVED,
            instrument_id=UUID("00000000-0000-0000-0000-000000000003"),
            exchange=ChinaAshareExchange.SZSE,
            board=ChinaAshareBoard.SZSE_MAIN,
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


def test_complete_source_expansion_builds_bound_completion_report(
    tmp_path: Path,
) -> None:
    plan = plan_china_ashare_source_expansion(
        population_package=_population(), partition_size=3, registered_at=NOW
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
    publish_china_ashare_source_expansion_partition(
        plan_result=plan_result,
        partition=partition,
        captured=captured,
        captured_at=NOW,
    )

    report = build_china_ashare_source_expansion_completion(
        plan_result=plan_result, evaluated_at=NOW
    )
    result = publish_china_ashare_source_expansion_completion(
        plan_result=plan_result, report=report
    )
    reread = read_china_ashare_source_expansion_completion(
        package_path=result.package_path
    )

    assert report.partition_count == 1
    assert report.target_count == 3
    assert report.resolved_target_count == 2
    assert report.quarantined_target_count == 1
    assert report.daily_target_with_rows_count == 1
    assert report.daily_zero_row_target_count == 2
    assert report.adjustment_target_with_rows_count == 1
    assert report.adjustment_zero_row_target_count == 2
    assert reread.report == report
    assert reread.file_count == 1


def test_source_expansion_normalization_uses_only_resolved_identity(
    tmp_path: Path,
) -> None:
    population = _population()
    plan = plan_china_ashare_source_expansion(
        population_package=population, partition_size=2, registered_at=NOW
    )
    plan_result = publish_china_ashare_source_expansion_plan(
        custody_root=tmp_path / "custody", plan=plan
    )
    partition = plan_result.plan.partitions[0]
    captured = capture_baostock_source_expansion_partition(
        session=FakeSessionWithQuarantineRows(),
        partition=partition,
        interval_start=plan.interval_start,
        interval_end=plan.interval_end,
        captured_at=NOW,
    )
    source_partition = publish_china_ashare_source_expansion_partition(
        plan_result=plan_result,
        partition=partition,
        captured=captured,
        captured_at=NOW,
    )

    normalized = normalize_china_ashare_source_expansion_partition(
        population_package=population,
        plan_result=plan_result,
        source_partition=source_partition,
    )

    assert len(normalized.bars) == 1
    assert len(normalized.states) == 1
    assert len(normalized.adjustments) == 1
    assert normalized.states[0].trading_status is ChinaAshareTradingStatus.TRADING
    assert normalized.resolved_target_count == 1
    assert normalized.quarantined_target_ids == ("sz.000001",)
    assert normalized.quarantined_daily_row_count == 1
    assert normalized.quarantined_adjustment_row_count == 1
    result = publish_china_ashare_normalized_expansion_partition(
        custody_root=tmp_path / "normalized",
        population_package=population,
        plan_result=plan_result,
        source_partition=source_partition,
        normalized=normalized,
        normalized_at=NOW,
    )
    reread = read_china_ashare_normalized_expansion_partition(
        custody_root=tmp_path / "normalized",
        population_package=population,
        plan_result=plan_result,
        source_partition=source_partition,
    )

    assert result.manifest == reread.manifest
    assert reread.normalized == normalized
    assert reread.file_count == 4
