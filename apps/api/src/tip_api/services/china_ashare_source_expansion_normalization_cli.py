"""CLI for resumable A-share source-expansion normalization."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tip_api.contracts.china_ashare.v1.normalized_expansion import (
    normalized_expansion_run_fingerprint,
)
from tip_api.persistence.china_ashare_normalized_expansion_package import (
    publish_china_ashare_normalized_expansion_partition,
    read_china_ashare_normalized_expansion_partition,
)
from tip_api.persistence.china_ashare_population_package import (
    read_china_ashare_population_package,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    read_china_ashare_source_expansion_partition,
    read_china_ashare_source_expansion_plan,
)
from tip_api.services.china_ashare_source_expansion_normalization import (
    normalize_china_ashare_source_expansion_partition,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--population-package", type=Path, required=True)
    parser.add_argument("--plan-root", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--maximum-new-partitions", type=int, default=0)
    args = parser.parse_args()
    if args.maximum_new_partitions < 0:
        parser.error("--maximum-new-partitions must be non-negative")
    population = read_china_ashare_population_package(
        package_path=args.population_package
    )
    plan_result = read_china_ashare_source_expansion_plan(
        plan_root=args.plan_root
    )
    run_fingerprint = normalized_expansion_run_fingerprint(
        plan_fingerprint=plan_result.plan.logical_fingerprint,
        population_package_fingerprint=population.manifest.logical_fingerprint,
    )
    new_count = 0
    verified_count = 0
    for partition in plan_result.plan.partitions:
        source_path = (
            plan_result.plan_root
            / "partitions"
            / f"{partition.partition_index:05d}"
        )
        if not source_path.exists():
            break
        source_partition = read_china_ashare_source_expansion_partition(
            plan_result=plan_result,
            partition_index=partition.partition_index,
        )
        normalized_path = (
            args.custody_root.expanduser().resolve()
            / f"run={run_fingerprint}"
            / "partitions"
            / f"{partition.partition_index:05d}"
        )
        if normalized_path.exists():
            read_china_ashare_normalized_expansion_partition(
                custody_root=args.custody_root,
                population_package=population,
                plan_result=plan_result,
                source_partition=source_partition,
            )
            verified_count += 1
            continue
        if args.maximum_new_partitions and new_count >= (
            args.maximum_new_partitions
        ):
            break
        normalized = normalize_china_ashare_source_expansion_partition(
            population_package=population,
            plan_result=plan_result,
            source_partition=source_partition,
        )
        result = publish_china_ashare_normalized_expansion_partition(
            custody_root=args.custody_root,
            population_package=population,
            plan_result=plan_result,
            source_partition=source_partition,
            normalized=normalized,
            normalized_at=datetime.now(UTC),
        )
        new_count += 1
        print(
            json.dumps(
                {
                    "event": "normalized_partition_complete",
                    "partition_index": partition.partition_index,
                    "status": result.status,
                    "target_count": result.manifest.target_count,
                    "resolved_target_count": (
                        result.manifest.resolved_target_count
                    ),
                    "quarantined_target_count": (
                        result.manifest.quarantined_target_count
                    ),
                    "normalized_bar_count": (
                        result.manifest.normalized_bar_count
                    ),
                    "normalized_state_count": (
                        result.manifest.normalized_state_count
                    ),
                    "normalized_adjustment_count": (
                        result.manifest.normalized_adjustment_count
                    ),
                },
                sort_keys=True,
            ),
            flush=True,
        )
    print(
        json.dumps(
            {
                "event": "normalization_run_checkpoint",
                "run_fingerprint": run_fingerprint,
                "verified_partition_count": verified_count,
                "new_partition_count": new_count,
                "source_plan_partition_count": len(plan_result.plan.partitions),
                "canonical_apply_authorized": False,
                "research_backtest_authorized": False,
                "product_publication_authorized": False,
                "deployment_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
