"""Build the exact restartable source-expansion plan from frozen population."""

from __future__ import annotations

from datetime import datetime

from tip_api.contracts.china_ashare.v1.population import (
    ChinaAsharePopulationDisposition,
)
from tip_api.contracts.china_ashare.v1.source_expansion import (
    ChinaAshareSourceExpansionPlanV1,
    build_source_expansion_partition_spec,
    build_source_expansion_plan,
    build_source_expansion_target,
)
from tip_api.persistence.china_ashare_population_package import (
    ChinaAsharePopulationPackageResultV1,
)


def plan_china_ashare_source_expansion(
    *,
    population_package: ChinaAsharePopulationPackageResultV1,
    partition_size: int,
    registered_at: datetime,
) -> ChinaAshareSourceExpansionPlanV1:
    report = population_package.report
    targets = tuple(
        build_source_expansion_target(
            source_security_id=item.source_security_id,
            listing_date=item.listing_date,
            disposition=item.disposition,
            population_occurrence_fingerprint=item.logical_fingerprint,
        )
        for item in population_package.occurrences
        if item.disposition is not ChinaAsharePopulationDisposition.OUTSIDE_SCOPE
    )
    targets = tuple(sorted(targets, key=lambda item: item.source_security_id))
    if len(targets) != report.expansion_target_count:
        raise ValueError("source expansion target population differs from report")
    partitions = tuple(
        build_source_expansion_partition_spec(
            partition_index=index,
            targets=targets[offset : offset + partition_size],
        )
        for index, offset in enumerate(range(0, len(targets), partition_size))
    )
    return build_source_expansion_plan(
        registered_at=registered_at,
        population_package_fingerprint=population_package.manifest.logical_fingerprint,
        population_occurrence_set_fingerprint=(
            population_package.manifest.occurrence_set_fingerprint
        ),
        interval_start=report.interval_start,
        interval_end=report.interval_end,
        partition_size=partition_size,
        partitions=partitions,
        target_count=len(targets),
        expected_source_request_count=len(targets) * 2,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
