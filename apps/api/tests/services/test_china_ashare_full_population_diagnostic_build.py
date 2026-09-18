from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    build_full_population_diagnostic_plan,
    build_full_population_partition_aggregate,
    build_full_population_streaming_aggregate,
)
from tip_api.services import china_ashare_full_population_diagnostic_build as subject


NOW = datetime(2026, 9, 17, 22, 0, tzinfo=UTC)


def test_build_and_replay_uses_partition_local_readers_and_matches_bytes(
    tmp_path, monkeypatch
) -> None:
    plan, partition, streaming = _artifacts()
    source_plan = SimpleNamespace(plan=SimpleNamespace(partitions=(object(),)))
    completion = SimpleNamespace(
        report=SimpleNamespace(partition_count=1, evaluated_at=NOW)
    )
    population = object()
    calls: list[int] = []

    monkeypatch.setattr(
        subject, "read_china_ashare_population_package", lambda **_: population
    )
    monkeypatch.setattr(
        subject, "read_china_ashare_source_expansion_plan", lambda **_: source_plan
    )
    monkeypatch.setattr(
        subject,
        "read_china_ashare_source_expansion_completion",
        lambda **_: completion,
    )
    monkeypatch.setattr(
        subject,
        "read_china_ashare_source_expansion_partition",
        lambda **values: SimpleNamespace(index=values["partition_index"]),
    )

    def read_normalized(**values):
        calls.append(values["source_partition"].index)
        return SimpleNamespace(
            manifest=SimpleNamespace(logical_fingerprint="6" * 64),
            normalized=SimpleNamespace(
                states=(SimpleNamespace(session_date=date(2026, 9, 16)),)
            ),
        )

    monkeypatch.setattr(
        subject, "read_china_ashare_normalized_expansion_partition", read_normalized
    )
    monkeypatch.setattr(
        subject,
        "aggregate_china_ashare_normalized_partition",
        lambda **_: partition,
    )
    monkeypatch.setattr(
        subject, "plan_china_ashare_full_population_diagnostic", lambda **_: plan
    )
    monkeypatch.setattr(
        subject, "merge_china_ashare_partition_aggregates", lambda **_: streaming
    )

    result = subject.build_and_replay_china_ashare_full_population_diagnostic(
        population_package_path=tmp_path / "population",
        source_plan_root=tmp_path / "source-plan",
        source_completion_package=tmp_path / "completion",
        normalized_custody_root=tmp_path / "normalized",
        output_custody_root=tmp_path / "primary",
        replay_custody_root=tmp_path / "replay",
    )

    assert calls == [0, 0]
    assert result.primary.partition_count == 1
    assert result.primary.target_session_count == 1
    assert result.byte_identical is True
    assert result.physical_hashes_identical is True
    assert result.primary_file_sha256s == result.replay_file_sha256s
    assert len(result.primary_file_sha256s) == 4


def test_replay_rejects_shared_custody(tmp_path) -> None:
    with pytest.raises(
        subject.ChinaAshareFullPopulationDiagnosticBuildError,
        match="must be independent",
    ):
        subject.build_and_replay_china_ashare_full_population_diagnostic(
            population_package_path=tmp_path / "population",
            source_plan_root=tmp_path / "source-plan",
            source_completion_package=tmp_path / "completion",
            normalized_custody_root=tmp_path / "normalized",
            output_custody_root=tmp_path / "same",
            replay_custody_root=tmp_path / "same",
        )


def test_replay_rejects_any_physical_difference(tmp_path, monkeypatch) -> None:
    builds = iter((SimpleNamespace(name="primary"), SimpleNamespace(name="replay")))
    monkeypatch.setattr(
        subject,
        "build_china_ashare_full_population_diagnostic",
        lambda **_: next(builds),
    )
    monkeypatch.setattr(
        subject,
        "_package_files",
        lambda result: (("plan/diagnostic-plan.json", result.name.encode()),),
    )

    with pytest.raises(
        subject.ChinaAshareFullPopulationDiagnosticBuildError,
        match="replay differs",
    ):
        subject.build_and_replay_china_ashare_full_population_diagnostic(
            population_package_path=tmp_path / "population",
            source_plan_root=tmp_path / "source-plan",
            source_completion_package=tmp_path / "completion",
            normalized_custody_root=tmp_path / "normalized",
            output_custody_root=tmp_path / "primary",
            replay_custody_root=tmp_path / "replay",
        )


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
        risk_warning_none_count=1,
        risk_warning_present_unspecified_count=0,
        risk_warning_detailed_count=0,
        risk_warning_unknown_count=0,
        price_limit_unknown_count=1,
        source_available_at_null_state_count=1,
        adjustment_first_observation_count=1,
        adjustment_changed_observation_count=0,
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
        risk_warning_present_unspecified_count=0,
        price_limit_unknown_count=1,
        source_available_at_null_state_count=1,
        adjustment_first_observation_count=1,
        adjustment_changed_observation_count=0,
        adjustment_noop_observation_count=0,
    )
    return plan, partition, streaming
