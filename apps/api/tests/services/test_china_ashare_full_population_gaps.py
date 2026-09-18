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
from tip_api.persistence.china_ashare_full_population_diagnostic_package import (
    publish_china_ashare_full_population_diagnostic_aggregate,
    publish_china_ashare_full_population_diagnostic_plan,
)
from tip_api.services.china_ashare_full_population_gap_cli import main
from tip_api.services.china_ashare_full_population_gaps import (
    build_and_replay_china_ashare_full_population_gap_checklist,
)


NOW = datetime(2026, 9, 17, 22, 0, tzinfo=UTC)


def test_gap_checklist_is_fail_closed_and_replays_exactly(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    plan, partition, streaming = _artifacts()
    plan_result = publish_china_ashare_full_population_diagnostic_plan(
        custody_root=tmp_path / "diagnostic",
        plan=plan,
    )
    aggregate_result = publish_china_ashare_full_population_diagnostic_aggregate(
        custody_root=tmp_path / "diagnostic",
        plan_result=plan_result,
        partitions=(partition,),
        streaming=streaming,
    )
    result = build_and_replay_china_ashare_full_population_gap_checklist(
        diagnostic_plan_package=plan_result.package_path,
        diagnostic_aggregate_package=aggregate_result.package_path,
        output_custody_root=tmp_path / "gaps",
        replay_custody_root=tmp_path / "gap-replay",
    )

    assert result.byte_identical is True
    assert result.physical_hash_identical is True
    assert result.primary.checklist.admitted_family_count == 0
    assert len(result.primary.checklist.entries) == 5
    assert all(
        entry.disposition == "blocked_missing_evidence"
        and entry.admission_authorized is False
        and entry.external_official_evidence_required is True
        for entry in result.primary.checklist.entries
    )
    assert result.primary.package_path.stat().st_mode & 0o777 == 0o700
    assert result.primary.checklist_path.stat().st_mode & 0o777 == 0o400

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "gaps",
            "--diagnostic-plan-package",
            str(plan_result.package_path),
            "--diagnostic-aggregate-package",
            str(aggregate_result.package_path),
            "--custody-root",
            str(tmp_path / "cli-gaps"),
            "--replay-custody-root",
            str(tmp_path / "cli-replay"),
        ],
    )
    assert main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "exact_replay_complete"
    assert output["byte_identical"] is True
    assert output["admitted_family_count"] == 0
    assert output["measures"]["price_limit_unknown_state_count"] == 1
    assert output["measures"]["adjustment_change_candidate_count"] == 1
    assert output["historical_coverage_authorized"] is False
    assert output["future_return_read_count"] == 0


def test_gap_admin_wrapper_is_executable() -> None:
    path = Path("scripts/admin/build-china-ashare-full-population-gap-checklist.sh")
    assert path.is_file()
    assert path.stat().st_mode & 0o111


def _artifacts():
    plan = build_full_population_diagnostic_plan(
        registered_at=NOW,
        interval_start=date(2026, 9, 15),
        interval_end=date(2026, 9, 16),
        target_session_count=1,
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
        risk_warning_none_count=0,
        risk_warning_present_unspecified_count=1,
        risk_warning_detailed_count=0,
        risk_warning_unknown_count=0,
        price_limit_unknown_count=1,
        source_available_at_null_state_count=1,
        adjustment_first_observation_count=0,
        adjustment_changed_observation_count=1,
        adjustment_noop_observation_count=0,
        first_state_session=date(2026, 9, 16),
        last_state_session=date(2026, 9, 16),
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
        risk_warning_present_unspecified_count=1,
        price_limit_unknown_count=1,
        source_available_at_null_state_count=1,
        adjustment_first_observation_count=0,
        adjustment_changed_observation_count=1,
        adjustment_noop_observation_count=0,
    )
    return plan, partition, streaming
