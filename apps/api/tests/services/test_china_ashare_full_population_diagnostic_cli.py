from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    build_full_population_diagnostic_plan,
    build_full_population_partition_aggregate,
    build_full_population_streaming_aggregate,
)
from tip_api.services.china_ashare_full_population_diagnostic_cli import main


def test_cli_publishes_plan_and_small_aggregate(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    plan, partition, streaming = _artifacts()
    plan_input = tmp_path / "plan.json"
    partitions_input = tmp_path / "partitions.json"
    streaming_input = tmp_path / "streaming.json"
    plan_input.write_text(plan.model_dump_json(), encoding="utf-8")
    partitions_input.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "rows": [partition.model_dump(mode="json")],
            }
        ),
        encoding="utf-8",
    )
    streaming_input.write_text(streaming.model_dump_json(), encoding="utf-8")
    custody = tmp_path / "custody"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "diagnostic",
            "publish-plan",
            "--plan-json",
            str(plan_input),
            "--custody-root",
            str(custody),
        ],
    )
    assert main() == 0
    plan_output = json.loads(capsys.readouterr().out)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "diagnostic",
            "publish-aggregate",
            "--plan-package",
            plan_output["package_path"],
            "--partition-aggregates-json",
            str(partitions_input),
            "--streaming-aggregate-json",
            str(streaming_input),
            "--custody-root",
            str(custody),
        ],
    )
    assert main() == 0
    aggregate_output = json.loads(capsys.readouterr().out)

    assert plan_output["status"] == "published"
    assert aggregate_output["status"] == "published"
    assert aggregate_output["partition_count"] == 1
    assert aggregate_output["future_return_read_count"] == 0
    assert aggregate_output["full_universe_rows_materialized"] is False
    assert aggregate_output["research_backtest_authorized"] is False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "diagnostic",
            "reread-aggregate",
            "--plan-package",
            plan_output["package_path"],
            "--aggregate-package",
            aggregate_output["package_path"],
        ],
    )
    assert main() == 0
    reread_output = json.loads(capsys.readouterr().out)
    assert reread_output["status"] == "exact_reread_complete"
    assert reread_output["streaming_aggregate_fingerprint"] == (
        aggregate_output["streaming_aggregate_fingerprint"]
    )


def test_admin_wrapper_is_executable() -> None:
    wrapper = Path("scripts/admin/persist-china-ashare-full-population-diagnostic.sh")
    assert wrapper.is_file()
    assert wrapper.stat().st_mode & 0o111


def _artifacts():
    plan = build_full_population_diagnostic_plan(
        registered_at=datetime(2026, 9, 17, 22, 0, tzinfo=UTC),
        interval_start=date(2026, 9, 15),
        interval_end=date(2026, 9, 16),
        target_session_count=2,
        target_count=1,
        population_package_fingerprint="1" * 64,
        source_plan_fingerprint="2" * 64,
        source_completion_fingerprint="3" * 64,
        normalized_run_fingerprint="4" * 64,
        source_partition_manifest_fingerprints=("5" * 64,),
        normalized_partition_manifest_fingerprints=("6" * 64,),
    )
    partition = build_full_population_partition_aggregate(
        partition_index=0,
        source_partition_manifest_fingerprint="5" * 64,
        normalized_partition_manifest_fingerprint="6" * 64,
        target_count=1,
        resolved_target_count=1,
        quarantined_target_count=0,
        bar_count=1,
        state_count=1,
        adjustment_count=1,
        trading_state_count=1,
        suspended_state_count=0,
        resumed_state_count=0,
        not_listed_state_count=0,
        unknown_trading_state_count=0,
        risk_warning_none_count=1,
        risk_warning_present_unspecified_count=0,
        risk_warning_detailed_count=0,
        risk_warning_unknown_count=0,
        price_limit_unknown_count=1,
        source_available_at_null_state_count=1,
        adjustment_first_observation_count=1,
        adjustment_changed_observation_count=0,
        adjustment_noop_observation_count=0,
        first_state_session=date(2026, 9, 15),
        last_state_session=date(2026, 9, 15),
    )
    streaming = build_full_population_streaming_aggregate(
        plan_fingerprint=plan.logical_fingerprint,
        partition_aggregate_fingerprints=(partition.logical_fingerprint,),
        target_count=1,
        resolved_target_count=1,
        quarantined_target_count=0,
        bar_count=1,
        state_count=1,
        adjustment_count=1,
        suspended_state_count=0,
        risk_warning_present_unspecified_count=0,
        price_limit_unknown_count=1,
        source_available_at_null_state_count=1,
        adjustment_first_observation_count=1,
        adjustment_changed_observation_count=0,
        adjustment_noop_observation_count=0,
    )
    return plan, partition, streaming
