from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    build_full_population_diagnostic_plan,
    china_ashare_full_population_coverage_report_v1,
)
from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareBoard,
    ChinaAshareDailyBarV1,
    ChinaAshareDailyTradingStateV1,
    ChinaAshareExchange,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.china_ashare.v1.normalized_expansion import (
    build_normalized_expansion_partition_manifest,
)
from tip_api.contracts.common import QualityStatus
from tip_api.persistence.china_ashare_full_population_coverage import (
    ChinaAshareFullPopulationCoverageCustodyError,
    publish_china_ashare_full_population_coverage,
    read_china_ashare_full_population_coverage,
)
from tip_api.persistence.china_ashare_normalized_expansion_package import (
    ChinaAshareNormalizedExpansionPartitionResultV1,
)
from tip_api.services.china_ashare_full_population_coverage import (
    ChinaAshareFullPopulationCoverageError,
    aggregate_china_ashare_normalized_partition,
    merge_china_ashare_partition_aggregates,
    plan_china_ashare_full_population_diagnostic,
    verify_china_ashare_full_population_coverage,
)
from tip_api.services.china_ashare_source_expansion_normalization import (
    NormalizedChinaAshareSourceExpansionPartitionV1,
)


NOW = datetime(2026, 9, 17, 21, 0, tzinfo=UTC)
FIRST_ID = UUID("00000000-0000-0000-0000-000000000001")
SECOND_ID = UUID("00000000-0000-0000-0000-000000000002")


def test_coverage_report_publishes_and_exactly_rereads(tmp_path: Path) -> None:
    report = china_ashare_full_population_coverage_report_v1()
    root = tmp_path / "coverage"

    published = publish_china_ashare_full_population_coverage(
        custody_root=root, report=report
    )
    reread = read_china_ashare_full_population_coverage(
        package_path=published.package_path
    )
    duplicate = publish_china_ashare_full_population_coverage(
        custody_root=root, report=report
    )

    assert published.status == "published"
    assert reread.status == "exact_reread_complete"
    assert duplicate.status == "already_present"
    assert reread.report == report
    assert published.report_physical_sha256 == reread.report_physical_sha256
    assert (published.package_path.stat().st_mode & 0o777) == 0o700
    assert (published.report_path.stat().st_mode & 0o777) == 0o400


def test_coverage_report_rejects_custody_drift(tmp_path: Path) -> None:
    published = publish_china_ashare_full_population_coverage(
        custody_root=tmp_path / "coverage",
        report=china_ashare_full_population_coverage_report_v1(),
    )
    published.report_path.chmod(0o600)

    with pytest.raises(
        ChinaAshareFullPopulationCoverageCustodyError,
        match="custody differs",
    ):
        read_china_ashare_full_population_coverage(
            package_path=published.package_path
        )


def test_coverage_verifier_rejects_unbound_run_root(tmp_path: Path) -> None:
    with pytest.raises(
        ChinaAshareFullPopulationCoverageError,
        match="run root is invalid",
    ):
        verify_china_ashare_full_population_coverage(
            normalized_run_root=tmp_path / "wrong"
        )


def test_diagnostic_plan_binds_registered_time_and_keeps_authority_closed() -> None:
    values = _plan_values()
    first = build_full_population_diagnostic_plan(registered_at=NOW, **values)
    second = build_full_population_diagnostic_plan(
        registered_at=NOW + timedelta(hours=1), **values
    )

    assert first.logical_fingerprint != second.logical_fingerprint
    assert first.registered_at != second.registered_at
    assert first.future_return_read_count == 0
    assert first.full_universe_rows_materialized is False
    assert first.research_backtest_authorized is False


def test_single_partition_aggregate_is_streamable_and_deterministic(
    tmp_path: Path,
) -> None:
    partition = _normalized_partition(tmp_path)

    first = aggregate_china_ashare_normalized_partition(partition=partition)
    second = aggregate_china_ashare_normalized_partition(partition=partition)
    plan = build_full_population_diagnostic_plan(
        registered_at=NOW,
        normalized_partition_manifest_fingerprints=(
            partition.manifest.logical_fingerprint,
        ),
        source_partition_manifest_fingerprints=(
            partition.manifest.source_partition_manifest_fingerprint,
        ),
        **{key: value for key, value in _plan_values().items() if "partition" not in key},
    )
    merged = merge_china_ashare_partition_aggregates(
        plan=plan, partitions=(first,)
    )

    assert first == second
    assert first.state_count == 3
    assert first.bar_count == 2
    assert first.suspended_state_count == 1
    assert first.risk_warning_present_unspecified_count == 1
    assert first.risk_warning_detailed_count == 1
    assert first.price_limit_unknown_count == 3
    assert first.source_available_at_null_state_count == 3
    assert first.adjustment_first_observation_count == 2
    assert first.adjustment_changed_observation_count == 1
    assert first.adjustment_noop_observation_count == 1
    assert first.full_universe_rows_materialized is False
    assert merged.partition_aggregate_fingerprints == (first.logical_fingerprint,)
    assert merged.adjustment_count == 4
    assert merged.future_return_read_count == 0
    assert merged.research_backtest_authorized is False


def test_diagnostic_plan_binds_exact_reader_results(tmp_path: Path) -> None:
    partition = _normalized_partition(tmp_path)
    population = SimpleNamespace(
        manifest=SimpleNamespace(logical_fingerprint="1" * 64)
    )
    source_plan = SimpleNamespace(
        plan=SimpleNamespace(
            logical_fingerprint="2" * 64,
            population_package_fingerprint="1" * 64,
            interval_start=date(2026, 9, 15),
            interval_end=date(2026, 9, 16),
            target_count=2,
        )
    )
    source_completion = SimpleNamespace(
        report=SimpleNamespace(
            logical_fingerprint="3" * 64,
            population_package_fingerprint="1" * 64,
            plan_fingerprint="2" * 64,
            partition_count=1,
            target_count=2,
            partition_manifest_fingerprints=("5" * 64,),
        )
    )

    plan = plan_china_ashare_full_population_diagnostic(
        population_package=population,
        source_plan=source_plan,
        source_completion=source_completion,
        normalized_manifests=(partition.manifest,),
        target_session_count=2,
        registered_at=NOW,
    )

    assert plan.population_package_fingerprint == "1" * 64
    assert plan.source_completion_fingerprint == "3" * 64
    assert plan.normalized_partition_manifest_fingerprints == (
        partition.manifest.logical_fingerprint,
    )
    assert plan.future_return_read_count == 0


def _plan_values() -> dict[str, object]:
    return {
        "interval_start": date(2026, 9, 15),
        "interval_end": date(2026, 9, 16),
        "target_session_count": 2,
        "target_count": 2,
        "population_package_fingerprint": "1" * 64,
        "source_plan_fingerprint": "2" * 64,
        "source_completion_fingerprint": "3" * 64,
        "normalized_run_fingerprint": "4" * 64,
        "source_partition_manifest_fingerprints": ("5" * 64,),
        "normalized_partition_manifest_fingerprints": ("6" * 64,),
    }


def _normalized_partition(
    tmp_path: Path,
) -> ChinaAshareNormalizedExpansionPartitionResultV1:
    states = (
        _state(FIRST_ID, date(2026, 9, 15), ChinaAshareTradingStatus.TRADING),
        _state(
            FIRST_ID,
            date(2026, 9, 16),
            ChinaAshareTradingStatus.SUSPENDED,
            risk=ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED,
        ),
        _state(
            SECOND_ID,
            date(2026, 9, 15),
            ChinaAshareTradingStatus.TRADING,
            risk=ChinaAshareRiskWarningStatus.OTHER_RISK_WARNING,
        ),
    )
    bars = (
        _bar(FIRST_ID, date(2026, 9, 15)),
        _bar(SECOND_ID, date(2026, 9, 15)),
    )
    adjustments = (
        _adjustment(FIRST_ID, date(2026, 9, 14), "1"),
        _adjustment(FIRST_ID, date(2026, 9, 15), "1.1"),
        _adjustment(FIRST_ID, date(2026, 9, 16), "1.1"),
        _adjustment(SECOND_ID, date(2026, 9, 15), "1"),
    )
    normalized = NormalizedChinaAshareSourceExpansionPartitionV1(
        bars=bars,
        states=states,
        adjustments=adjustments,
        resolved_target_count=2,
        quarantined_target_ids=(),
        quarantined_daily_row_count=0,
        quarantined_adjustment_row_count=0,
    )
    manifest = build_normalized_expansion_partition_manifest(
        run_fingerprint="4" * 64,
        plan_fingerprint="2" * 64,
        population_package_fingerprint="1" * 64,
        source_partition_manifest_fingerprint="5" * 64,
        partition_index=0,
        normalized_at=NOW,
        target_count=2,
        resolved_target_count=2,
        quarantined_target_count=0,
        source_daily_row_count=3,
        source_adjustment_row_count=4,
        normalized_bar_count=2,
        normalized_state_count=3,
        normalized_adjustment_count=4,
        suspended_state_count=1,
        unknown_trading_state_count=0,
        risk_warning_present_state_count=2,
        quarantined_daily_row_count=0,
        quarantined_adjustment_row_count=0,
        quarantined_target_ids=(),
        bar_parquet_bytes=1,
        bar_parquet_sha256="7" * 64,
        state_parquet_bytes=1,
        state_parquet_sha256="8" * 64,
        adjustment_parquet_bytes=1,
        adjustment_parquet_sha256="9" * 64,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    return ChinaAshareNormalizedExpansionPartitionResultV1(
        manifest=manifest,
        normalized=normalized,
        run_root=tmp_path,
        partition_path=tmp_path,
        manifest_path=tmp_path / "manifest.json",
        manifest_physical_sha256="a" * 64,
        file_count=4,
        total_bytes=4,
        status="exact_reread_complete",
    )


def _state(
    instrument_id: UUID,
    session: date,
    trading: ChinaAshareTradingStatus,
    *,
    risk: ChinaAshareRiskWarningStatus = ChinaAshareRiskWarningStatus.NONE,
) -> ChinaAshareDailyTradingStateV1:
    return ChinaAshareDailyTradingStateV1(
        instrument_id=instrument_id,
        session_date=session,
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        trading_status=trading,
        risk_warning_status=risk,
        price_limit_regime=ChinaAsharePriceLimitRegime.UNKNOWN,
        pre_close=Decimal("10"),
        exact_limit_prices_source_observed=False,
        source="fixture",
        source_available_at=None,
        ingested_at=NOW,
        quality_status=QualityStatus.WARNING,
        reason_codes=("price_limit_unknown",),
    )


def _bar(instrument_id: UUID, session: date) -> ChinaAshareDailyBarV1:
    return ChinaAshareDailyBarV1(
        instrument_id=instrument_id,
        session_date=session,
        open=Decimal("10"),
        high=Decimal("11"),
        low=Decimal("9"),
        close=Decimal("10"),
        pre_close=Decimal("10"),
        volume_shares=Decimal("100"),
        turnover_amount_cny=Decimal("1000"),
        source="fixture",
        source_record_id=f"fixture:{instrument_id}:{session.isoformat()}",
        source_available_at=None,
        ingested_at=NOW,
        revision=1,
        quality_status=QualityStatus.WARNING,
        reason_codes=("source_available_time_unreported",),
    )


def _adjustment(
    instrument_id: UUID, session: date, factor: str
) -> ChinaAshareAdjustmentFactorObservationV1:
    return ChinaAshareAdjustmentFactorObservationV1(
        instrument_id=instrument_id,
        session_date=session,
        provider_factor=Decimal(factor),
        fore_adjust_factor=Decimal(factor),
        back_adjust_factor=Decimal(factor),
        provider_semantics="fixture source observation only",
        source="fixture",
        source_available_at=None,
        ingested_at=NOW,
        normalized_return_authorized=False,
        quality_status=QualityStatus.WARNING,
        reason_codes=("return_semantics_unreconciled",),
    )
