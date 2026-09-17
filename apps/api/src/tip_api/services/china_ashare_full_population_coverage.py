"""Verify the exact normalized A-share run behind the coverage report."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq
from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    NORMALIZED_RUN_FINGERPRINT,
    ChinaAshareFullPopulationDiagnosticPlanV1,
    ChinaAshareFullPopulationPartitionAggregateV1,
    ChinaAshareFullPopulationCoverageReportV1,
    ChinaAshareFullPopulationStreamingAggregateV1,
    build_full_population_partition_aggregate,
    build_full_population_diagnostic_plan,
    build_full_population_streaming_aggregate,
    china_ashare_full_population_coverage_report_v1,
)
from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.china_ashare.v1.normalized_expansion import (
    ChinaAshareNormalizedExpansionPartitionManifestV1,
)
from tip_api.persistence.china_ashare_population_package import (
    ChinaAsharePopulationPackageResultV1,
)
from tip_api.persistence.china_ashare_normalized_expansion_package import (
    ADJUSTMENT_FILE,
    BAR_FILE,
    MANIFEST_FILE,
    STATE_FILE,
    ChinaAshareNormalizedExpansionPartitionResultV1,
)
from tip_api.persistence.china_ashare_source_expansion_completion import (
    ChinaAshareSourceExpansionCompletionResultV1,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    ChinaAshareSourceExpansionPlanResultV1,
)


class ChinaAshareFullPopulationCoverageError(RuntimeError):
    pass


def plan_china_ashare_full_population_diagnostic(
    *,
    population_package: ChinaAsharePopulationPackageResultV1,
    source_plan: ChinaAshareSourceExpansionPlanResultV1,
    source_completion: ChinaAshareSourceExpansionCompletionResultV1,
    normalized_manifests: tuple[
        ChinaAshareNormalizedExpansionPartitionManifestV1, ...
    ],
    target_session_count: int,
    registered_at: datetime,
) -> ChinaAshareFullPopulationDiagnosticPlanV1:
    """Bind exact-reader outputs before any partition aggregation begins."""

    population_fingerprint = population_package.manifest.logical_fingerprint
    plan_fingerprint = source_plan.plan.logical_fingerprint
    completion = source_completion.report
    if (
        source_plan.plan.population_package_fingerprint != population_fingerprint
        or completion.population_package_fingerprint != population_fingerprint
        or completion.plan_fingerprint != plan_fingerprint
        or completion.partition_count != len(normalized_manifests)
        or completion.target_count != source_plan.plan.target_count
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "diagnostic source package bindings differ"
        )
    if tuple(item.partition_index for item in normalized_manifests) != tuple(
        range(len(normalized_manifests))
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "normalized manifests are not complete and ordered"
        )
    source_manifest_fingerprints = tuple(
        item.source_partition_manifest_fingerprint for item in normalized_manifests
    )
    if source_manifest_fingerprints != completion.partition_manifest_fingerprints:
        raise ChinaAshareFullPopulationCoverageError(
            "normalized manifests differ from source completion"
        )
    if any(
        item.plan_fingerprint != plan_fingerprint
        or item.population_package_fingerprint != population_fingerprint
        for item in normalized_manifests
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "normalized manifest source bindings differ"
        )
    run_fingerprints = {item.run_fingerprint for item in normalized_manifests}
    if len(run_fingerprints) != 1:
        raise ChinaAshareFullPopulationCoverageError(
            "normalized manifest run bindings differ"
        )
    return build_full_population_diagnostic_plan(
        registered_at=registered_at,
        interval_start=source_plan.plan.interval_start,
        interval_end=source_plan.plan.interval_end,
        target_session_count=target_session_count,
        target_count=source_plan.plan.target_count,
        population_package_fingerprint=population_fingerprint,
        source_plan_fingerprint=plan_fingerprint,
        source_completion_fingerprint=completion.logical_fingerprint,
        normalized_run_fingerprint=next(iter(run_fingerprints)),
        source_partition_manifest_fingerprints=source_manifest_fingerprints,
        normalized_partition_manifest_fingerprints=tuple(
            item.logical_fingerprint for item in normalized_manifests
        ),
        future_return_read_count=0,
        full_universe_rows_materialized=False,
        adjusted_return_authorized=False,
        research_backtest_authorized=False,
        canonical_apply_authorized=False,
        product_publication_authorized=False,
    )


def aggregate_china_ashare_normalized_partition(
    *, partition: ChinaAshareNormalizedExpansionPartitionResultV1
) -> ChinaAshareFullPopulationPartitionAggregateV1:
    """Aggregate one exact-reader result without retaining another partition."""

    manifest = partition.manifest
    normalized = partition.normalized
    if (
        len(normalized.bars) != manifest.normalized_bar_count
        or len(normalized.states) != manifest.normalized_state_count
        or len(normalized.adjustments) != manifest.normalized_adjustment_count
        or normalized.resolved_target_count != manifest.resolved_target_count
        or len(normalized.quarantined_target_ids)
        != manifest.quarantined_target_count
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "normalized partition rows differ from manifest"
        )

    trading_counts = {
        status: sum(item.trading_status is status for item in normalized.states)
        for status in ChinaAshareTradingStatus
    }
    risk_counts = {
        status: sum(item.risk_warning_status is status for item in normalized.states)
        for status in ChinaAshareRiskWarningStatus
    }
    detailed_risk_count = sum(
        risk_counts[status]
        for status in (
            ChinaAshareRiskWarningStatus.OTHER_RISK_WARNING,
            ChinaAshareRiskWarningStatus.DELISTING_RISK_WARNING,
            ChinaAshareRiskWarningStatus.COMBINED_RISK_WARNING,
            ChinaAshareRiskWarningStatus.DELISTING_PERIOD,
        )
    )
    first_adjustments = 0
    changed_adjustments = 0
    noop_adjustments = 0
    previous_key: tuple[str, object] | None = None
    previous_factors: tuple[object, object, object] | None = None
    for item in normalized.adjustments:
        key = (str(item.instrument_id), item.session_date)
        if previous_key is not None and key <= previous_key:
            raise ChinaAshareFullPopulationCoverageError(
                "normalized adjustment keys are not strictly ordered"
            )
        factors = (
            item.provider_factor,
            item.fore_adjust_factor,
            item.back_adjust_factor,
        )
        if previous_key is None or key[0] != previous_key[0]:
            first_adjustments += 1
        elif factors == previous_factors:
            noop_adjustments += 1
        else:
            changed_adjustments += 1
        previous_key = key
        previous_factors = factors

    sessions = tuple(item.session_date for item in normalized.states)
    return build_full_population_partition_aggregate(
        partition_index=manifest.partition_index,
        source_partition_manifest_fingerprint=(
            manifest.source_partition_manifest_fingerprint
        ),
        normalized_partition_manifest_fingerprint=manifest.logical_fingerprint,
        target_count=manifest.target_count,
        resolved_target_count=manifest.resolved_target_count,
        quarantined_target_count=manifest.quarantined_target_count,
        bar_count=len(normalized.bars),
        state_count=len(normalized.states),
        adjustment_count=len(normalized.adjustments),
        trading_state_count=trading_counts[ChinaAshareTradingStatus.TRADING],
        suspended_state_count=trading_counts[ChinaAshareTradingStatus.SUSPENDED],
        resumed_state_count=trading_counts[ChinaAshareTradingStatus.RESUMED],
        not_listed_state_count=trading_counts[ChinaAshareTradingStatus.NOT_LISTED],
        unknown_trading_state_count=trading_counts[ChinaAshareTradingStatus.UNKNOWN],
        risk_warning_none_count=risk_counts[ChinaAshareRiskWarningStatus.NONE],
        risk_warning_present_unspecified_count=risk_counts[
            ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED
        ],
        risk_warning_detailed_count=detailed_risk_count,
        risk_warning_unknown_count=risk_counts[ChinaAshareRiskWarningStatus.UNKNOWN],
        price_limit_unknown_count=sum(
            item.price_limit_regime is ChinaAsharePriceLimitRegime.UNKNOWN
            for item in normalized.states
        ),
        source_available_at_null_state_count=sum(
            item.source_available_at is None for item in normalized.states
        ),
        adjustment_first_observation_count=first_adjustments,
        adjustment_changed_observation_count=changed_adjustments,
        adjustment_noop_observation_count=noop_adjustments,
        first_state_session=min(sessions, default=None),
        last_state_session=max(sessions, default=None),
        full_universe_rows_materialized=False,
        future_return_read_count=0,
        research_backtest_authorized=False,
    )


def merge_china_ashare_partition_aggregates(
    *,
    plan: ChinaAshareFullPopulationDiagnosticPlanV1,
    partitions: tuple[ChinaAshareFullPopulationPartitionAggregateV1, ...],
) -> ChinaAshareFullPopulationStreamingAggregateV1:
    """Merge only ordered counters; callers may release each source partition."""

    if len(partitions) != len(plan.normalized_partition_manifest_fingerprints):
        raise ChinaAshareFullPopulationCoverageError(
            "partition aggregate count differs from diagnostic plan"
        )
    if tuple(item.partition_index for item in partitions) != tuple(
        range(len(partitions))
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "partition aggregates are not complete and ordered"
        )
    for index, item in enumerate(partitions):
        if (
            item.source_partition_manifest_fingerprint
            != plan.source_partition_manifest_fingerprints[index]
            or item.normalized_partition_manifest_fingerprint
            != plan.normalized_partition_manifest_fingerprints[index]
        ):
            raise ChinaAshareFullPopulationCoverageError(
                "partition aggregate input binding differs from diagnostic plan"
            )

    def total(field: str) -> int:
        return sum(int(getattr(item, field)) for item in partitions)

    if total("target_count") != plan.target_count:
        raise ChinaAshareFullPopulationCoverageError(
            "partition aggregate targets differ from diagnostic plan"
        )
    return build_full_population_streaming_aggregate(
        plan_fingerprint=plan.logical_fingerprint,
        partition_aggregate_fingerprints=tuple(
            item.logical_fingerprint for item in partitions
        ),
        target_count=total("target_count"),
        resolved_target_count=total("resolved_target_count"),
        quarantined_target_count=total("quarantined_target_count"),
        bar_count=total("bar_count"),
        state_count=total("state_count"),
        adjustment_count=total("adjustment_count"),
        suspended_state_count=total("suspended_state_count"),
        risk_warning_present_unspecified_count=total(
            "risk_warning_present_unspecified_count"
        ),
        price_limit_unknown_count=total("price_limit_unknown_count"),
        source_available_at_null_state_count=total(
            "source_available_at_null_state_count"
        ),
        adjustment_first_observation_count=total(
            "adjustment_first_observation_count"
        ),
        adjustment_changed_observation_count=total(
            "adjustment_changed_observation_count"
        ),
        adjustment_noop_observation_count=total(
            "adjustment_noop_observation_count"
        ),
        full_universe_rows_materialized=False,
        future_return_read_count=0,
        research_backtest_authorized=False,
        canonical_apply_authorized=False,
        product_publication_authorized=False,
    )


def verify_china_ashare_full_population_coverage(
    *, normalized_run_root: Path
) -> ChinaAshareFullPopulationCoverageReportV1:
    root = normalized_run_root.expanduser().resolve()
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.name != f"run={NORMALIZED_RUN_FINGERPRINT}"
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion run root is invalid"
        )
    partitions_root = root / "partitions"
    if partitions_root.is_symlink() or not partitions_root.is_dir():
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion partitions root is invalid"
        )
    partition_paths = tuple(
        sorted(item for item in partitions_root.iterdir() if item.is_dir())
    )
    if len(partition_paths) != 109 or tuple(item.name for item in partition_paths) != (
        tuple(f"{index:05d}" for index in range(109))
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion partition set differs"
        )

    manifests = tuple(_read_partition_manifest(item) for item in partition_paths)
    report = china_ashare_full_population_coverage_report_v1()
    sums = {
        field: sum(int(getattr(item, field)) for item in manifests)
        for field in (
            "target_count",
            "resolved_target_count",
            "quarantined_target_count",
            "normalized_bar_count",
            "normalized_state_count",
            "normalized_adjustment_count",
            "suspended_state_count",
            "risk_warning_present_state_count",
        )
    }
    expected = {
        "target_count": report.target_count,
        "resolved_target_count": report.resolved_target_count,
        "quarantined_target_count": report.quarantined_target_count,
        "normalized_bar_count": report.normalized_bar_count,
        "normalized_state_count": report.normalized_state_count,
        "normalized_adjustment_count": report.normalized_adjustment_observation_count,
        "suspended_state_count": report.suspended_state_count,
        "risk_warning_present_state_count": report.risk_warning_present_unspecified_count,
    }
    if sums != expected:
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion aggregate differs from frozen coverage report"
        )

    unknown_count = 0
    source_null_count = 0
    for partition_path in partition_paths:
        parquet = pq.ParquetFile(partition_path / STATE_FILE)
        for batch in parquet.iter_batches(
            batch_size=65_536,
            columns=["price_limit_regime", "source_available_at"],
        ):
            unknown_count += int(
                pc.sum(pc.equal(batch["price_limit_regime"], "unknown")).as_py()
                or 0
            )
            source_null_count += batch["source_available_at"].null_count
    if (
        unknown_count != report.price_limit_regime_unknown_count
        or source_null_count != report.source_available_at_null_count
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion point-in-time boundary differs"
        )
    return report


def _read_partition_manifest(
    partition_root: Path,
) -> ChinaAshareNormalizedExpansionPartitionManifestV1:
    if partition_root.is_symlink():
        raise ChinaAshareFullPopulationCoverageError("partition path is unsafe")
    manifest_path = partition_root / MANIFEST_FILE
    try:
        manifest = ChinaAshareNormalizedExpansionPartitionManifestV1.model_validate_json(
            _read(manifest_path, maximum_bytes=16 * 1024 * 1024)
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion partition manifest is invalid"
        ) from exc
    if (
        manifest.run_fingerprint != NORMALIZED_RUN_FINGERPRINT
        or manifest.partition_index != int(partition_root.name)
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion partition binding differs"
        )
    for name, expected_size, expected_hash in (
        (BAR_FILE, manifest.bar_parquet_bytes, manifest.bar_parquet_sha256),
        (STATE_FILE, manifest.state_parquet_bytes, manifest.state_parquet_sha256),
        (
            ADJUSTMENT_FILE,
            manifest.adjustment_parquet_bytes,
            manifest.adjustment_parquet_sha256,
        ),
    ):
        path = partition_root / name
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != expected_size
            or _file_sha256(path) != expected_hash
        ):
            raise ChinaAshareFullPopulationCoverageError(
                "normalized expansion partition payload differs"
            )
    return manifest


def _read(path: Path, *, maximum_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ChinaAshareFullPopulationCoverageError("coverage input is absent or unsafe")
    size = path.stat().st_size
    if size <= 0 or size > maximum_bytes:
        raise ChinaAshareFullPopulationCoverageError("coverage input size is invalid")
    return path.read_bytes()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
