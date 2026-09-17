"""CLI for finalizing the complete A-share raw-source expansion census."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tip_api.persistence.china_ashare_source_expansion_completion import (
    publish_china_ashare_source_expansion_completion,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    read_china_ashare_source_expansion_plan,
)
from tip_api.services.china_ashare_source_expansion_completion import (
    build_china_ashare_source_expansion_completion,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-root", type=Path, required=True)
    args = parser.parse_args()
    plan_result = read_china_ashare_source_expansion_plan(plan_root=args.plan_root)
    report = build_china_ashare_source_expansion_completion(
        plan_result=plan_result, evaluated_at=datetime.now(UTC)
    )
    result = publish_china_ashare_source_expansion_completion(
        plan_result=plan_result, report=report
    )
    print(
        json.dumps(
            {
                "status": result.status,
                "package_path": str(result.package_path),
                "report_fingerprint": result.report.logical_fingerprint,
                "partition_count": result.report.partition_count,
                "target_count": result.report.target_count,
                "daily_row_count": result.report.daily_row_count,
                "adjustment_row_count": result.report.adjustment_row_count,
                "daily_zero_row_target_count": (
                    result.report.daily_zero_row_target_count
                ),
                "adjustment_zero_row_target_count": (
                    result.report.adjustment_zero_row_target_count
                ),
                "research_backtest_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
