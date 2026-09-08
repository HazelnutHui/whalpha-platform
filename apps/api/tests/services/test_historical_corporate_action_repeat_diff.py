from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.services.historical_corporate_action_repeat_diff import (
    HistoricalCorporateActionRepeatDiffError,
    build_historical_corporate_action_repeat_diff,
    read_historical_corporate_action_repeat_diff,
)
from tip_api.services.historical_corporate_action_source import (
    CorporateActionSourceKind,
    fetch_historical_corporate_action_source_package,
)


START = date(2026, 8, 20)
END = date(2026, 8, 22)
BASELINE_AT = datetime(2026, 9, 1, tzinfo=UTC)
REPEAT_AT = datetime(2026, 9, 2, tzinfo=UTC)
COMPARED_AT = datetime(2026, 9, 3, tzinfo=UTC)


class FixtureTransport:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def get_json(self, *args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        return {"status": "OK", "results": self.rows}


class NoWait:
    def wait_before_request(self) -> None:
        return None


def _source_package(
    root: Path,
    *,
    kind: CorporateActionSourceKind,
    observed_at: datetime,
    rows: list[dict[str, object]],
) -> Path:
    root.mkdir(mode=0o700)
    target = root / f"{kind.value}={START}_{END}"
    fetch_historical_corporate_action_source_package(
        config=MassiveProviderConfig(api_key=SecretStr("fixture-secret")),
        transport=FixtureTransport(rows),  # type: ignore[arg-type]
        action_kind=kind,
        start_date=START,
        end_date=END,
        package_path=target,
        rate_limiter=NoWait(),  # type: ignore[arg-type]
        clock=lambda: observed_at,
    )
    return target


def _split(
    source_id: str | None,
    *,
    ticker: str = "AAA",
    execution_date: str = "2026-08-20",
    split_to: int = 2,
) -> dict[str, object]:
    return {
        "adjustment_type": "forward_split",
        "execution_date": execution_date,
        "historical_adjustment_factor": 0.5,
        "id": source_id,
        "split_from": 1,
        "split_to": split_to,
        "ticker": ticker,
    }


def _dividend(ex_date: str) -> dict[str, object]:
    return {
        "cash_amount": 0.25,
        "currency": "USD",
        "distribution_type": "recurring",
        "ex_dividend_date": ex_date,
        "frequency": 4,
        "id": "dividend-change",
        "ticker": "AAA",
    }


def _inputs(tmp_path: Path) -> dict[str, object]:
    baseline = _source_package(
        tmp_path / "baseline",
        kind=CorporateActionSourceKind.SPLIT,
        observed_at=BASELINE_AT,
        rows=[
            _split("same"),
            _split("changed"),
            _split("removed", ticker="REM"),
        ],
    )
    repeat = _source_package(
        tmp_path / "repeat",
        kind=CorporateActionSourceKind.SPLIT,
        observed_at=REPEAT_AT,
        rows=[
            _split("same"),
            _split("added", ticker="ADD"),
            _split(
                "changed",
                ticker="BBB",
                execution_date="2026-08-22",
                split_to=3,
            ),
        ],
    )
    return {
        "baseline_package_path": baseline,
        "repeat_package_path": repeat,
        "output_root": tmp_path / "diff",
        "action_kind": CorporateActionSourceKind.SPLIT,
        "start_date": START,
        "end_date": END,
        "compared_at": COMPARED_AT,
    }


def test_builds_one_complete_owner_only_repeat_diff(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)

    result = build_historical_corporate_action_repeat_diff(**inputs)  # type: ignore[arg-type]

    manifest = result.manifest
    assert result.status == "published"
    assert manifest.baseline_record_count == 3
    assert manifest.repeat_record_count == 3
    assert manifest.unchanged_record_count == 1
    assert manifest.changed_record_count == 1
    assert manifest.added_record_count == 1
    assert manifest.removed_record_count == 1
    assert dict(manifest.changed_field_counts) == {
        "execution_date": 1,
        "split_to": 1,
        "ticker": 1,
    }
    assert manifest.effective_date_changed_record_count == 1
    assert manifest.provider_ticker_changed_record_count == 1
    assert manifest.pagination_shape_changed is False
    assert manifest.external_request_count == 0
    assert {item.change_type for item in result.changes} == {
        "added",
        "changed",
        "removed",
    }
    assert result.output_root.stat().st_mode & 0o777 == 0o700
    assert {path.name for path in result.output_root.iterdir()} == {
        "diff.json",
        "changes.json",
    }
    assert all(
        path.stat().st_mode & 0o777 == 0o400
        for path in result.output_root.iterdir()
    )

    reread = read_historical_corporate_action_repeat_diff(
        output_root=result.output_root
    )
    assert reread.manifest == result.manifest
    assert reread.changes == result.changes


def test_exact_rerun_is_idempotent(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    first = build_historical_corporate_action_repeat_diff(**inputs)  # type: ignore[arg-type]
    second = build_historical_corporate_action_repeat_diff(**inputs)  # type: ignore[arg-type]

    assert second.status == "already_present"
    assert second.manifest == first.manifest
    assert second.changes == first.changes


def test_identical_content_has_no_change_records(tmp_path: Path) -> None:
    rows = [_split("same")]
    baseline = _source_package(
        tmp_path / "baseline",
        kind=CorporateActionSourceKind.SPLIT,
        observed_at=BASELINE_AT,
        rows=rows,
    )
    repeat = _source_package(
        tmp_path / "repeat",
        kind=CorporateActionSourceKind.SPLIT,
        observed_at=REPEAT_AT,
        rows=rows,
    )

    result = build_historical_corporate_action_repeat_diff(
        baseline_package_path=baseline,
        repeat_package_path=repeat,
        output_root=tmp_path / "diff",
        action_kind=CorporateActionSourceKind.SPLIT,
        start_date=START,
        end_date=END,
        compared_at=COMPARED_AT,
    )

    assert result.manifest.unchanged_record_count == 1
    assert result.manifest.changed_record_count == 0
    assert result.manifest.added_record_count == 0
    assert result.manifest.removed_record_count == 0
    assert result.changes == ()


def test_dividend_effective_date_change_is_counted(tmp_path: Path) -> None:
    baseline = _source_package(
        tmp_path / "baseline",
        kind=CorporateActionSourceKind.DIVIDEND,
        observed_at=BASELINE_AT,
        rows=[_dividend("2026-08-20")],
    )
    repeat = _source_package(
        tmp_path / "repeat",
        kind=CorporateActionSourceKind.DIVIDEND,
        observed_at=REPEAT_AT,
        rows=[_dividend("2026-08-22")],
    )

    result = build_historical_corporate_action_repeat_diff(
        baseline_package_path=baseline,
        repeat_package_path=repeat,
        output_root=tmp_path / "diff",
        action_kind=CorporateActionSourceKind.DIVIDEND,
        start_date=START,
        end_date=END,
        compared_at=COMPARED_AT,
    )

    assert result.manifest.changed_record_count == 1
    assert result.manifest.effective_date_changed_record_count == 1
    assert dict(result.manifest.changed_field_counts) == {"ex_dividend_date": 1}


def test_missing_provider_action_id_stops_comparison(tmp_path: Path) -> None:
    baseline = _source_package(
        tmp_path / "baseline",
        kind=CorporateActionSourceKind.SPLIT,
        observed_at=BASELINE_AT,
        rows=[_split(None)],
    )
    repeat = _source_package(
        tmp_path / "repeat",
        kind=CorporateActionSourceKind.SPLIT,
        observed_at=REPEAT_AT,
        rows=[_split(None)],
    )

    with pytest.raises(
        HistoricalCorporateActionRepeatDiffError,
        match="every provider action ID",
    ):
        build_historical_corporate_action_repeat_diff(
            baseline_package_path=baseline,
            repeat_package_path=repeat,
            output_root=tmp_path / "diff",
            action_kind=CorporateActionSourceKind.SPLIT,
            start_date=START,
            end_date=END,
            compared_at=COMPARED_AT,
        )


def test_repeat_observation_must_follow_baseline(tmp_path: Path) -> None:
    baseline = _source_package(
        tmp_path / "baseline",
        kind=CorporateActionSourceKind.SPLIT,
        observed_at=REPEAT_AT,
        rows=[_split("same")],
    )
    repeat = _source_package(
        tmp_path / "repeat",
        kind=CorporateActionSourceKind.SPLIT,
        observed_at=BASELINE_AT,
        rows=[_split("same")],
    )

    with pytest.raises(
        HistoricalCorporateActionRepeatDiffError,
        match="does not follow",
    ):
        build_historical_corporate_action_repeat_diff(
            baseline_package_path=baseline,
            repeat_package_path=repeat,
            output_root=tmp_path / "diff",
            action_kind=CorporateActionSourceKind.SPLIT,
            start_date=START,
            end_date=END,
            compared_at=COMPARED_AT,
        )


def test_tampered_change_artifact_fails_formal_reread(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    result = build_historical_corporate_action_repeat_diff(**inputs)  # type: ignore[arg-type]
    path = result.output_root / "changes.json"
    path.chmod(0o600)
    payload = json.loads(path.read_text())
    payload["changes"][0]["source_action_id"] = "tampered"
    path.write_text(json.dumps(payload))
    path.chmod(0o400)

    with pytest.raises(HistoricalCorporateActionRepeatDiffError):
        read_historical_corporate_action_repeat_diff(output_root=result.output_root)
