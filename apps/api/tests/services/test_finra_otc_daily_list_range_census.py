from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tip_api.services.finra_otc_daily_list_range_census import (
    FinraOtcDailyListRangeCensusError,
    census_finra_otc_daily_list_range,
    read_sealed_finra_otc_daily_list_range_census,
    seal_finra_otc_daily_list_range_census,
)
from tip_api.services.finra_otc_daily_list_source import (
    acquire_finra_otc_daily_list_source_package,
)


class FixtureTransport:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def post_json(self, **kwargs: object):
        offset = int(kwargs["payload"]["offset"])  # type: ignore[index]
        rows = self.rows[offset : offset + 500]
        return rows, {
            "Content-Type": "application/json",
            "Data-Version": "1",
            "Record-Total": str(len(self.rows)),
            "Record-Limit": "500",
            "Record-Max-Limit": "5000",
            "Record-Offset": str(offset),
            "Response-Payload-Max-Size": "3mb",
        }


class NoWait:
    def wait_before_request(self) -> None:
        return None


def _row(identifier: int, day: str) -> dict[str, object]:
    return {
        "OTCDailyListID": identifier,
        "calendarDay": day,
        "dailyListEventCode": "SC",
        "oldSymbolCode": "OLD",
        "newSymbolCode": "NEW",
    }


def _acquire(root: Path, start: date, end: date, rows: list[dict[str, object]]) -> None:
    acquire_finra_otc_daily_list_source_package(
        partition_start=start,
        partition_end=end,
        package_path=root / f"period={start.isoformat()}--{end.isoformat()}",
        approved_custody_root=root,
        transport=FixtureTransport(rows),
        rate_limiter=NoWait(),  # type: ignore[arg-type]
        clock=lambda: datetime(2026, 9, 10, 13, tzinfo=UTC),
    )


def test_census_rereads_contiguous_range_and_preserves_repeated_ids(tmp_path: Path) -> None:
    root = tmp_path / "finra"
    root.mkdir(mode=0o700)
    _acquire(root, date(2026, 1, 15), date(2026, 1, 31), [_row(7, "2026-01-20")])
    _acquire(
        root,
        date(2026, 2, 1),
        date(2026, 2, 9),
        [_row(7, "2026-02-02"), _row(8, "2026-02-03")],
    )

    result = census_finra_otc_daily_list_range(
        custody_root=root,
        range_start=date(2026, 1, 15),
        range_end=date(2026, 2, 9),
        evaluated_at=datetime(2026, 9, 10, 14, tzinfo=UTC),
    )

    assert result.coverage_status == "complete_with_repeated_identifiers"
    assert result.package_count == 2
    assert result.record_count == 3
    assert result.unique_source_identifier_count == 2
    assert result.repeated_source_identifier_group_count == 1
    assert result.repeated_source_identifier_additional_occurrence_count == 1
    assert result.repeated_source_identifiers[0].source_identifier == 7
    assert result.repeated_source_identifiers[0].distinct_payload_count == 2
    assert result.network_request_count == 0
    target = seal_finra_otc_daily_list_range_census(
        custody_root=root,
        census=result,
    )
    assert target.stat().st_mode & 0o777 == 0o400
    assert read_sealed_finra_otc_daily_list_range_census(
        custody_root=root,
        range_start=date(2026, 1, 15),
        range_end=date(2026, 2, 9),
    ) == result
    with pytest.raises(FileExistsError):
        seal_finra_otc_daily_list_range_census(
            custody_root=root,
            census=result,
        )


def test_census_fails_when_an_exact_month_is_missing(tmp_path: Path) -> None:
    root = tmp_path / "finra"
    root.mkdir(mode=0o700)
    _acquire(root, date(2026, 1, 15), date(2026, 1, 31), [_row(7, "2026-01-20")])

    with pytest.raises((FinraOtcDailyListRangeCensusError, RuntimeError)):
        census_finra_otc_daily_list_range(
            custody_root=root,
            range_start=date(2026, 1, 15),
            range_end=date(2026, 2, 9),
        )
