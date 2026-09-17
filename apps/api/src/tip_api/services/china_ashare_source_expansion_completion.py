"""Aggregate the exact complete A-share raw-source expansion census."""

from __future__ import annotations

from datetime import date, datetime

from tip_api.contracts.china_ashare.v1.population import (
    ChinaAsharePopulationDisposition,
)
from tip_api.contracts.china_ashare.v1.source_expansion_completion import (
    ChinaAshareSourceExpansionCompletionReportV1,
    build_source_expansion_completion_report,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    ChinaAshareSourceExpansionPlanResultV1,
    read_china_ashare_source_expansion_partition,
)


def build_china_ashare_source_expansion_completion(
    *,
    plan_result: ChinaAshareSourceExpansionPlanResultV1,
    evaluated_at: datetime,
) -> ChinaAshareSourceExpansionCompletionReportV1:
    plan = plan_result.plan
    targets = tuple(target for item in plan.partitions for target in item.targets)
    source_request_count = 0
    daily_row_count = 0
    adjustment_row_count = 0
    daily_zero_row_target_count = 0
    adjustment_zero_row_target_count = 0
    suspended_row_count = 0
    risk_warning_present_row_count = 0
    first_daily_session: date | None = None
    last_daily_session: date | None = None
    partition_manifest_fingerprints: list[str] = []
    for partition in plan.partitions:
        partition_path = (
            plan_result.plan_root
            / "partitions"
            / f"{partition.partition_index:05d}"
        )
        if not partition_path.exists():
            raise ValueError("source expansion plan is not complete")
        result = read_china_ashare_source_expansion_partition(
            plan_result=plan_result,
            partition_index=partition.partition_index,
        )
        source_request_count += result.manifest.source_request_count
        daily_row_count += result.manifest.daily_row_count
        adjustment_row_count += result.manifest.adjustment_row_count
        daily_zero_row_target_count += len(result.manifest.daily_zero_row_ids)
        adjustment_zero_row_target_count += len(
            result.manifest.adjustment_zero_row_ids
        )
        suspended_row_count += sum(
            row.provider_trade_status == "0" for row in result.captured.daily_rows
        )
        risk_warning_present_row_count += sum(
            row.provider_risk_warning == "1" for row in result.captured.daily_rows
        )
        if result.captured.daily_rows:
            partition_first = min(
                row.session_date for row in result.captured.daily_rows
            )
            partition_last = max(
                row.session_date for row in result.captured.daily_rows
            )
            first_daily_session = (
                partition_first
                if first_daily_session is None
                else min(first_daily_session, partition_first)
            )
            last_daily_session = (
                partition_last
                if last_daily_session is None
                else max(last_daily_session, partition_last)
            )
        partition_manifest_fingerprints.append(result.manifest.logical_fingerprint)
    return build_source_expansion_completion_report(
        evaluated_at=evaluated_at,
        plan_fingerprint=plan.logical_fingerprint,
        population_package_fingerprint=plan.population_package_fingerprint,
        interval_start=plan.interval_start,
        interval_end=plan.interval_end,
        partition_count=len(plan.partitions),
        target_count=len(targets),
        resolved_target_count=sum(
            item.disposition is ChinaAsharePopulationDisposition.RESOLVED
            for item in targets
        ),
        quarantined_target_count=sum(
            item.disposition is ChinaAsharePopulationDisposition.QUARANTINED
            for item in targets
        ),
        source_request_count=source_request_count,
        daily_row_count=daily_row_count,
        adjustment_row_count=adjustment_row_count,
        daily_target_with_rows_count=(
            len(targets) - daily_zero_row_target_count
        ),
        daily_zero_row_target_count=daily_zero_row_target_count,
        adjustment_target_with_rows_count=(
            len(targets) - adjustment_zero_row_target_count
        ),
        adjustment_zero_row_target_count=adjustment_zero_row_target_count,
        suspended_row_count=suspended_row_count,
        risk_warning_present_row_count=risk_warning_present_row_count,
        first_daily_session=first_daily_session,
        last_daily_session=last_daily_session,
        partition_manifest_fingerprints=tuple(partition_manifest_fingerprints),
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
