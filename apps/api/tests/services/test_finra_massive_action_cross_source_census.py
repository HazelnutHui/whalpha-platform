from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.services.finra_massive_action_cross_source_census import (
    census_finra_massive_action_sources,
    read_sealed_finra_massive_action_cross_source_census,
    seal_finra_massive_action_cross_source_census,
)
from tip_api.services.finra_otc_daily_list_range_census import (
    census_finra_otc_daily_list_range,
    seal_finra_otc_daily_list_range_census,
)
from tip_api.services.finra_otc_daily_list_source import (
    acquire_finra_otc_daily_list_source_package,
)
from tip_api.services.historical_corporate_action_source import (
    CorporateActionSourceKind,
    fetch_historical_corporate_action_source_package,
)


START = date(2026, 1, 1)
END = date(2026, 1, 31)


class FinraFixtureTransport:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def post_json(self, **kwargs: object):
        offset = int(kwargs["payload"]["offset"])  # type: ignore[index]
        return self.rows[offset : offset + 500], {
            "Content-Type": "application/json",
            "Data-Version": "1",
            "Record-Total": str(len(self.rows)),
            "Record-Limit": "500",
            "Record-Max-Limit": "5000",
            "Record-Offset": str(offset),
            "Response-Payload-Max-Size": "3mb",
        }


class MassiveFixtureTransport:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def get_json(self, *args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        return {"status": "OK", "request_id": "not-retained", "results": self.rows}


class NoWait:
    interval_seconds = Decimal("0.25")

    def wait_before_request(self) -> None:
        return None


def _finra_row(identifier: int, **values: object) -> dict[str, object]:
    return {
        "OTCDailyListID": identifier,
        "calendarDay": "2026-01-10",
        "dailyListEventCode": "DA",
        "oldSymbolCode": "AAA",
        "newSymbolCode": "AAA",
        "securityAddFlag": "N",
        "securityDeleteFlag": "N",
        "changeSymbolFlag": "N",
        "changeSecurityDescriptionFlag": "N",
        "changeSecurityAttributeFlag": "N",
        "bankruptcyFlag": "N",
        **values,
    }


def _split(identifier: str, ticker: str, split_from: float, split_to: float) -> dict[str, object]:
    return {
        "adjustment_type": "forward_split" if split_to > split_from else "reverse_split",
        "execution_date": "2026-01-15",
        "id": identifier,
        "split_from": split_from,
        "split_to": split_to,
        "ticker": ticker,
    }


def _dividend(identifier: str, ticker: str, amount: float) -> dict[str, object]:
    return {
        "cash_amount": amount,
        "currency": "USD",
        "distribution_type": "recurring",
        "ex_dividend_date": "2026-01-20",
        "id": identifier,
        "ticker": ticker,
    }


def _build_sources(tmp_path: Path) -> tuple[Path, Path]:
    finra_root = tmp_path / "finra"
    finra_root.mkdir(mode=0o700)
    rows = [
        _finra_row(1, exDate="2026-01-15", forwardSplitRate="2:1"),
        _finra_row(2, oldSymbolCode="BBB", newSymbolCode="BBB", exDate="2026-01-15", reverseSplitRate="1:10"),
        _finra_row(3, oldSymbolCode="DUP", newSymbolCode="DUP", exDate="2026-01-15", forwardSplitRate="3:1"),
        _finra_row(4, oldSymbolCode="NONE", newSymbolCode="NONE", exDate="2025-12-31", forwardSplitRate="2:1"),
        _finra_row(5, exDate="2026-01-20", cashAmountText="0.25"),
        _finra_row(6, oldSymbolCode="BBB", newSymbolCode="BBB", exDate="2026-01-20", cashAmountText="0.99"),
        _finra_row(7, oldSymbolCode="DUP", newSymbolCode="DUP", exDate="2026-01-20", cashAmountText="0.50"),
        _finra_row(8, oldSymbolCode="NONE", newSymbolCode=None, exDate="2026-01-20"),
    ]
    acquire_finra_otc_daily_list_source_package(
        partition_start=START,
        partition_end=END,
        package_path=finra_root / f"period={START.isoformat()}--{END.isoformat()}",
        approved_custody_root=finra_root,
        transport=FinraFixtureTransport(rows),
        rate_limiter=NoWait(),  # type: ignore[arg-type]
        clock=lambda: datetime(2026, 2, 1, tzinfo=UTC),
    )
    finra_census = census_finra_otc_daily_list_range(
        custody_root=finra_root,
        range_start=START,
        range_end=END,
        evaluated_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    seal_finra_otc_daily_list_range_census(
        custody_root=finra_root, census=finra_census
    )

    massive_root = tmp_path / "massive"
    massive_root.mkdir(mode=0o700)
    split_rows = [
        _split("split-a", "AAA", 1, 2),
        _split("split-b", "BBB", 5, 1),
        _split("split-duplicate-provider-id", "DUP", 1, 3),
        _split("split-duplicate-provider-id", "DUP", 1, 4),
    ]
    dividend_rows = [
        _dividend("div-a", "AAA", 0.25),
        _dividend("div-b", "BBB", 0.50),
        _dividend("div-duplicate-provider-id", "DUP", 0.50),
        _dividend("div-duplicate-provider-id", "DUP", 0.75),
    ]
    config = MassiveProviderConfig(api_key=SecretStr("fixture-secret"))
    for kind, source_rows in (
        (CorporateActionSourceKind.SPLIT, split_rows),
        (CorporateActionSourceKind.DIVIDEND, dividend_rows),
    ):
        fetch_historical_corporate_action_source_package(
            config=config,
            transport=MassiveFixtureTransport(source_rows),  # type: ignore[arg-type]
            action_kind=kind,
            start_date=START,
            end_date=END,
            package_path=massive_root / f"{kind.value}={START.isoformat()}_{END.isoformat()}",
            rate_limiter=NoWait(),  # type: ignore[arg-type]
            clock=lambda: datetime(2026, 2, 1, tzinfo=UTC),
        )
    return finra_root, massive_root


def test_census_measures_candidate_agreement_without_resolving_identity(tmp_path: Path) -> None:
    finra_root, massive_root = _build_sources(tmp_path)

    result = census_finra_massive_action_sources(
        finra_custody_root=finra_root,
        massive_custody_root=massive_root,
        range_start=START,
        range_end=END,
        evaluated_at=datetime(2026, 2, 2, tzinfo=UTC),
    )

    assert result.finra_record_count == 8
    assert result.non_action_observation_count == 1
    assert result.overlapping_action_family_count == 0
    assert result.split.finra_observation_count == 4
    assert result.split.effective_date_in_scope_count == 3
    assert result.split.candidate_key_none_count == 1
    assert result.split.candidate_key_unique_count == 2
    assert result.split.candidate_key_ambiguous_count == 1
    assert result.split.numeric_match_unique_count == 2
    assert result.split.unique_key_numeric_equal_count == 1
    assert result.split.unique_key_numeric_disagree_count == 1
    assert result.split.ambiguous_key_unique_numeric_count == 1
    assert result.dividend.finra_observation_count == 3
    assert result.dividend.candidate_key_unique_count == 2
    assert result.dividend.candidate_key_ambiguous_count == 1
    assert result.dividend.numeric_match_unique_count == 2
    assert result.dividend.unique_key_numeric_equal_count == 1
    assert result.dividend.unique_key_numeric_disagree_count == 1
    assert result.stable_identity_resolution_count == 0
    assert result.canonical_action_write_count == 0
    assert result.network_request_count == 0

    output_root = tmp_path / "output"
    output_root.mkdir(mode=0o700)
    target = seal_finra_massive_action_cross_source_census(
        output_root=output_root, census=result
    )
    assert target.stat().st_mode & 0o777 == 0o400
    assert read_sealed_finra_massive_action_cross_source_census(
        output_root=output_root, range_start=START, range_end=END
    ) == result
    with pytest.raises(FileExistsError):
        seal_finra_massive_action_cross_source_census(
            output_root=output_root, census=result
        )


def test_census_stops_if_sealed_finra_range_is_absent(tmp_path: Path) -> None:
    finra_root, massive_root = _build_sources(tmp_path)
    sealed = finra_root / f"range-census={START.isoformat()}--{END.isoformat()}.json"
    sealed.chmod(0o600)
    sealed.unlink()

    with pytest.raises(RuntimeError):
        census_finra_massive_action_sources(
            finra_custody_root=finra_root,
            massive_custody_root=massive_root,
            range_start=START,
            range_end=END,
        )
