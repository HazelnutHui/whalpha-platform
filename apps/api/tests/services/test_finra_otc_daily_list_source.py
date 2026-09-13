from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from tip_api.services import finra_otc_daily_list_source as module
from tip_api.services.finra_otc_daily_list_source import (
    FinraOtcDailyListSourceError,
    acquire_finra_otc_daily_list_source_package,
    read_finra_otc_daily_list_source_payloads,
    read_finra_otc_daily_list_source_package,
)


START = date(2021, 9, 9)
END = date(2021, 9, 30)


class FixtureTransport:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, object]] = []

    def post_json(self, **kwargs: object):
        self.calls.append(kwargs["payload"])  # type: ignore[arg-type]
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FixtureLimiter:
    def __init__(self) -> None:
        self.count = 0

    def wait_before_request(self) -> None:
        self.count += 1


def _clock(count: int = 20, *, offset: int = 0):
    start = datetime(2026, 9, 10, 12, tzinfo=UTC) + timedelta(seconds=offset)
    values = iter(start + timedelta(seconds=index) for index in range(count))
    return lambda: next(values)


def _headers(*, offset: int, total: int) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Data-Version": "1",
        "Record-Total": str(total),
        "Record-Limit": "500",
        "Record-Max-Limit": "5000",
        "Record-Offset": str(offset),
        "Response-Payload-Max-Size": "3mb",
    }


def _row(identifier: int, day: str = "2021-09-09") -> dict[str, object]:
    return {
        "OTCDailyListID": identifier,
        "calendarDay": day,
        "dailyListEventCode": "SC",
        "oldSymbolCode": "OLD",
        "newSymbolCode": "NEW",
        "changeSymbolFlag": "Y",
    }


def _target(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "finra"
    root.mkdir(mode=0o700)
    return root, root / f"period={START.isoformat()}--{END.isoformat()}"


def test_acquire_pages_and_formally_rereads_owner_only_package(tmp_path: Path) -> None:
    root, target = _target(tmp_path)
    first = [_row(index) for index in range(1, 501)]
    second = [_row(501)]
    transport = FixtureTransport(
        [(first, _headers(offset=0, total=501)), (second, _headers(offset=500, total=501))]
    )
    limiter = FixtureLimiter()

    result = acquire_finra_otc_daily_list_source_package(
        partition_start=START,
        partition_end=END,
        package_path=target,
        approved_custody_root=root,
        transport=transport,
        rate_limiter=limiter,  # type: ignore[arg-type]
        clock=_clock(),
    )

    assert result.status == "published"
    assert result.manifest.request_count == 2
    assert result.manifest.record_count == 501
    assert result.manifest.event_code_counts == (("SC", 501),)
    assert result.manifest.research_eligibility == "official_otc_corroboration_only"
    assert limiter.count == 2
    assert transport.calls[1]["offset"] == 500
    assert target.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o400 for path in target.iterdir())
    assert read_finra_otc_daily_list_source_package(
        package_path=target,
        expected_partition_start=START,
        expected_partition_end=END,
        approved_custody_root=root,
    ) == result.manifest
    payloads = read_finra_otc_daily_list_source_payloads(
        package_path=target,
        expected_partition_start=START,
        expected_partition_end=END,
        approved_custody_root=root,
    )
    assert payloads.manifest == result.manifest
    assert sum(len(page.rows) for page in payloads.pages) == 501
    assert payloads.manifest_sha256 == result.manifest_sha256


def test_resume_reuses_sealed_page_after_interruption(tmp_path: Path) -> None:
    root, target = _target(tmp_path)
    first = [_row(index) for index in range(1, 501)]
    with pytest.raises(FinraOtcDailyListSourceError):
        acquire_finra_otc_daily_list_source_package(
            partition_start=START,
            partition_end=END,
            package_path=target,
            approved_custody_root=root,
            transport=FixtureTransport(
                [
                    (first, _headers(offset=0, total=501)),
                    FinraOtcDailyListSourceError("fixture interruption"),
                ]
            ),
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )
    resumed = FixtureTransport(
        [([_row(501)], _headers(offset=500, total=501))]
    )
    result = acquire_finra_otc_daily_list_source_package(
        partition_start=START,
        partition_end=END,
        package_path=target,
        approved_custody_root=root,
        transport=resumed,
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(offset=100),
    )
    assert result.status == "recovered_and_published"
    assert len(resumed.calls) == 1
    assert resumed.calls[0]["offset"] == 500


def test_resume_adopts_exact_orphan_page(monkeypatch, tmp_path: Path) -> None:
    root, target = _target(tmp_path)
    original = module._write_checkpoint

    def crash(partial, checkpoint) -> None:
        if checkpoint.artifacts:
            raise RuntimeError("injected crash")
        original(partial, checkpoint)

    monkeypatch.setattr(module, "_write_checkpoint", crash)
    with pytest.raises(RuntimeError):
        acquire_finra_otc_daily_list_source_package(
            partition_start=START,
            partition_end=END,
            package_path=target,
            approved_custody_root=root,
            transport=FixtureTransport([([_row(1)], _headers(offset=0, total=1))]),
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )
    monkeypatch.setattr(module, "_write_checkpoint", original)
    result = acquire_finra_otc_daily_list_source_package(
        partition_start=START,
        partition_end=END,
        package_path=target,
        approved_custody_root=root,
        transport=FixtureTransport([]),
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(offset=100),
    )
    assert result.status == "recovered_and_published"


@pytest.mark.parametrize(
    ("rows", "headers", "match"),
    [
        ([_row(1, "2021-10-01")], _headers(offset=0, total=1), "outside"),
        ([_row(1)], {**_headers(offset=0, total=1), "Data-Version": "2"}, ""),
        ([_row(1)], {**_headers(offset=1, total=1)}, "offset"),
    ],
)
def test_invalid_source_facts_fail_closed(
    tmp_path: Path,
    rows: list[dict[str, object]],
    headers: dict[str, str],
    match: str,
) -> None:
    root, target = _target(tmp_path)
    if not match:
        result = acquire_finra_otc_daily_list_source_package(
            partition_start=START,
            partition_end=END,
            package_path=target,
            approved_custody_root=root,
            transport=FixtureTransport([(rows, headers)]),
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )
        assert result.manifest.data_version == 2
        return
    with pytest.raises(FinraOtcDailyListSourceError, match=match):
        acquire_finra_otc_daily_list_source_package(
            partition_start=START,
            partition_end=END,
            package_path=target,
            approved_custody_root=root,
            transport=FixtureTransport([(rows, headers)]),
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )


def test_header_or_row_schema_drift_fails_closed(tmp_path: Path) -> None:
    root, target = _target(tmp_path)
    with pytest.raises(FinraOtcDailyListSourceError, match="bounds changed"):
        acquire_finra_otc_daily_list_source_package(
            partition_start=START,
            partition_end=END,
            package_path=target,
            approved_custody_root=root,
            transport=FixtureTransport(
                [([_row(1)], {**_headers(offset=0, total=1), "Record-Limit": "1000"})]
            ),
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )
    root2 = tmp_path / "finra2"
    root2.mkdir(mode=0o700)
    target2 = root2 / f"period={START.isoformat()}--{END.isoformat()}"
    with pytest.raises(FinraOtcDailyListSourceError, match="unrequested"):
        acquire_finra_otc_daily_list_source_package(
            partition_start=START,
            partition_end=END,
            package_path=target2,
            approved_custody_root=root2,
            transport=FixtureTransport(
                [([{**_row(1), "futureField": "x"}], _headers(offset=0, total=1))]
            ),
            rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
            clock=_clock(),
        )


def test_completed_package_tamper_is_rejected(tmp_path: Path) -> None:
    root, target = _target(tmp_path)
    acquire_finra_otc_daily_list_source_package(
        partition_start=START,
        partition_end=END,
        package_path=target,
        approved_custody_root=root,
        transport=FixtureTransport([([_row(1)], _headers(offset=0, total=1))]),
        rate_limiter=FixtureLimiter(),  # type: ignore[arg-type]
        clock=_clock(),
    )
    page = target / "response-00001.json"
    page.chmod(0o600)
    values = json.loads(page.read_text(encoding="utf-8"))
    values["rows"][0]["oldSymbolCode"] = "TAMPER"
    page.write_text(json.dumps(values), encoding="utf-8")
    page.chmod(0o400)
    with pytest.raises(FinraOtcDailyListSourceError, match="custody differs"):
        read_finra_otc_daily_list_source_package(
            package_path=target,
            expected_partition_start=START,
            expected_partition_end=END,
            approved_custody_root=root,
        )
