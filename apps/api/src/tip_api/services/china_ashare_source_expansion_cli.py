"""CLI for restartable five-year A-share raw-source expansion."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from tip_api.persistence.china_ashare_population_package import (
    read_china_ashare_population_package,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    completed_source_expansion_partition_indices,
    publish_china_ashare_source_expansion_partition,
    publish_china_ashare_source_expansion_plan,
)
from tip_api.providers.china_ashare.baostock_session import BaoStockClientSession
from tip_api.providers.china_ashare.baostock_source_expansion_adapter import (
    capture_baostock_source_expansion_partition,
)
from tip_api.providers.market_data import ProviderUnavailableError
from tip_api.services.china_ashare_source_expansion import (
    plan_china_ashare_source_expansion,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--population-package", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--partition-size", type=int, default=50)
    parser.add_argument("--maximum-attempts-per-partition", type=int, default=3)
    parser.add_argument(
        "--maximum-new-partitions",
        type=int,
        default=1,
        help="0 captures every remaining partition; positive values set a bound",
    )
    args = parser.parse_args()
    if args.maximum_new_partitions < 0:
        parser.error("--maximum-new-partitions cannot be negative")
    if not 1 <= args.maximum_attempts_per_partition <= 5:
        parser.error("--maximum-attempts-per-partition must be from 1 through 5")
    population = read_china_ashare_population_package(
        package_path=args.population_package
    )
    plan = plan_china_ashare_source_expansion(
        population_package=population,
        partition_size=args.partition_size,
        registered_at=datetime.now(UTC),
    )
    plan_result = publish_china_ashare_source_expansion_plan(
        custody_root=args.custody_root,
        plan=plan,
    )
    completed_before = set(
        completed_source_expansion_partition_indices(plan_result=plan_result)
    )
    pending = tuple(
        item
        for item in plan_result.plan.partitions
        if item.partition_index not in completed_before
    )
    selected = (
        pending
        if args.maximum_new_partitions == 0
        else pending[: args.maximum_new_partitions]
    )
    published_indices = []
    for partition in selected:
        for attempt in range(1, args.maximum_attempts_per_partition + 1):
            try:
                captured_at = datetime.now(UTC)
                with BaoStockClientSession() as session:
                    captured = capture_baostock_source_expansion_partition(
                        session=session,
                        partition=partition,
                        interval_start=plan_result.plan.interval_start,
                        interval_end=plan_result.plan.interval_end,
                        captured_at=captured_at,
                    )
                result = publish_china_ashare_source_expansion_partition(
                    plan_result=plan_result,
                    partition=partition,
                    captured=captured,
                    captured_at=captured_at,
                )
                published_indices.append(partition.partition_index)
                print(
                    json.dumps(
                        {
                            "event": "partition_complete",
                            "partition_index": partition.partition_index,
                            "partition_count": len(plan_result.plan.partitions),
                            "target_count": result.manifest.target_count,
                            "daily_row_count": result.manifest.daily_row_count,
                            "adjustment_row_count": result.manifest.adjustment_row_count,
                            "daily_zero_row_count": len(
                                result.manifest.daily_zero_row_ids
                            ),
                            "adjustment_zero_row_count": len(
                                result.manifest.adjustment_zero_row_ids
                            ),
                            "manifest_fingerprint": result.manifest.logical_fingerprint,
                            "status": result.status,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
                break
            except ProviderUnavailableError:
                if attempt >= args.maximum_attempts_per_partition:
                    raise
                print(
                    json.dumps(
                        {
                            "event": "partition_retry",
                            "partition_index": partition.partition_index,
                            "attempt": attempt,
                            "maximum_attempts": (
                                args.maximum_attempts_per_partition
                            ),
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
                time.sleep(attempt * 3)
    completed_after = completed_source_expansion_partition_indices(
        plan_result=plan_result
    )
    print(
        json.dumps(
            {
                "event": "source_expansion_checkpoint",
                "plan_fingerprint": plan_result.plan.logical_fingerprint,
                "plan_path": str(plan_result.plan_path),
                "target_count": plan_result.plan.target_count,
                "partition_count": len(plan_result.plan.partitions),
                "completed_partition_count": len(completed_after),
                "remaining_partition_count": (
                    len(plan_result.plan.partitions) - len(completed_after)
                ),
                "new_partition_count": len(published_indices),
                "research_backtest_authorized": False,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
