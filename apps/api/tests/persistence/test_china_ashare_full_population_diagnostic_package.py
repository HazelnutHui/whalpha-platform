from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    build_full_population_diagnostic_plan,
    build_full_population_partition_aggregate,
    build_full_population_streaming_aggregate,
)
from tip_api.persistence.china_ashare_full_population_diagnostic_package import (
    ChinaAshareFullPopulationDiagnosticPackageError,
    publish_china_ashare_full_population_diagnostic_aggregate,
    publish_china_ashare_full_population_diagnostic_plan,
    read_china_ashare_full_population_diagnostic_aggregate,
    read_china_ashare_full_population_diagnostic_plan,
)


NOW = datetime(2026, 9, 17, 22, 0, tzinfo=UTC)


def test_plan_and_small_aggregate_publish_and_exactly_reread(
    tmp_path: Path,
) -> None:
    plan, partitions, streaming = _artifacts()
    plan_result = publish_china_ashare_full_population_diagnostic_plan(
        custody_root=tmp_path / "custody",
        plan=plan,
    )
    aggregate_result = publish_china_ashare_full_population_diagnostic_aggregate(
        custody_root=tmp_path / "custody",
        plan_result=plan_result,
        partitions=partitions,
        streaming=streaming,
    )
    reread_plan = read_china_ashare_full_population_diagnostic_plan(
        package_path=plan_result.package_path
    )
    reread_aggregate = read_china_ashare_full_population_diagnostic_aggregate(
        plan_result=reread_plan,
        package_path=aggregate_result.package_path,
    )
    duplicate = publish_china_ashare_full_population_diagnostic_aggregate(
        custody_root=tmp_path / "custody",
        plan_result=reread_plan,
        partitions=partitions,
        streaming=streaming,
    )

    assert plan_result.status == "published"
    assert aggregate_result.status == "published"
    assert reread_plan.status == "exact_reread_complete"
    assert reread_aggregate.status == "exact_reread_complete"
    assert duplicate.status == "already_present"
    assert reread_aggregate.partitions == partitions
    assert reread_aggregate.streaming == streaming
    assert reread_aggregate.file_count == 3
    assert reread_aggregate.manifest.future_return_read_count == 0
    assert reread_aggregate.manifest.full_universe_rows_materialized is False
    assert (plan_result.package_path.stat().st_mode & 0o777) == 0o700
    assert (plan_result.plan_path.stat().st_mode & 0o777) == 0o400
    assert (aggregate_result.package_path.stat().st_mode & 0o777) == 0o700
    assert all(
        item.stat().st_mode & 0o777 == 0o400
        for item in aggregate_result.package_path.iterdir()
    )


def test_aggregate_reread_rejects_permissions_and_closed_set_drift(
    tmp_path: Path,
) -> None:
    plan, partitions, streaming = _artifacts()
    plan_result = publish_china_ashare_full_population_diagnostic_plan(
        custody_root=tmp_path / "custody",
        plan=plan,
    )
    result = publish_china_ashare_full_population_diagnostic_aggregate(
        custody_root=tmp_path / "custody",
        plan_result=plan_result,
        partitions=partitions,
        streaming=streaming,
    )
    result.manifest_path.chmod(0o600)
    with pytest.raises(
        ChinaAshareFullPopulationDiagnosticPackageError,
        match="permissions differ",
    ):
        read_china_ashare_full_population_diagnostic_aggregate(
            plan_result=plan_result,
            package_path=result.package_path,
        )

    result.manifest_path.chmod(0o400)
    extra = result.package_path / "unexpected.json"
    extra.write_text("{}", encoding="utf-8")
    extra.chmod(0o400)
    with pytest.raises(
        ChinaAshareFullPopulationDiagnosticPackageError,
        match="file set differs",
    ):
        read_china_ashare_full_population_diagnostic_aggregate(
            plan_result=plan_result,
            package_path=result.package_path,
        )


def test_aggregate_reread_rejects_hash_size_and_schema_drift(
    tmp_path: Path,
) -> None:
    plan, partitions, streaming = _artifacts()
    plan_result = publish_china_ashare_full_population_diagnostic_plan(
        custody_root=tmp_path / "custody",
        plan=plan,
    )
    result = publish_china_ashare_full_population_diagnostic_aggregate(
        custody_root=tmp_path / "custody",
        plan_result=plan_result,
        partitions=partitions,
        streaming=streaming,
    )
    partition_path = result.package_path / "partition-aggregates.json"
    original_payload = partition_path.read_bytes()
    partition_path.chmod(0o600)
    partition_path.write_text(
        '{"rows":[],"schema_version":"2.0"}\n', encoding="utf-8"
    )
    partition_path.chmod(0o400)

    with pytest.raises(
        ChinaAshareFullPopulationDiagnosticPackageError,
        match="document is invalid",
    ):
        read_china_ashare_full_population_diagnostic_aggregate(
            plan_result=plan_result,
            package_path=result.package_path,
        )

    partition_path.chmod(0o600)
    partition_path.write_bytes(original_payload + b" ")
    partition_path.chmod(0o400)
    with pytest.raises(
        ChinaAshareFullPopulationDiagnosticPackageError,
        match="binding differs",
    ):
        read_china_ashare_full_population_diagnostic_aggregate(
            plan_result=plan_result,
            package_path=result.package_path,
        )


def test_aggregate_reread_rejects_path_binding_drift(tmp_path: Path) -> None:
    plan, partitions, streaming = _artifacts()
    plan_result = publish_china_ashare_full_population_diagnostic_plan(
        custody_root=tmp_path / "custody",
        plan=plan,
    )
    result = publish_china_ashare_full_population_diagnostic_aggregate(
        custody_root=tmp_path / "custody",
        plan_result=plan_result,
        partitions=partitions,
        streaming=streaming,
    )
    moved = result.package_path.with_name("aggregate=" + "f" * 64)
    result.package_path.rename(moved)

    with pytest.raises(
        ChinaAshareFullPopulationDiagnosticPackageError,
        match="binding differs",
    ):
        read_china_ashare_full_population_diagnostic_aggregate(
            plan_result=plan_result,
            package_path=moved,
        )


def test_plan_reread_rejects_symlink_path(tmp_path: Path) -> None:
    plan, _, _ = _artifacts()
    result = publish_china_ashare_full_population_diagnostic_plan(
        custody_root=tmp_path / "custody",
        plan=plan,
    )
    link = tmp_path / "plan-link"
    link.symlink_to(result.package_path, target_is_directory=True)

    with pytest.raises(
        ChinaAshareFullPopulationDiagnosticPackageError,
        match="cannot be a symlink",
    ):
        read_china_ashare_full_population_diagnostic_plan(package_path=link)


def _artifacts():
    plan = build_full_population_diagnostic_plan(
        registered_at=NOW,
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
    return plan, (partition,), streaming
