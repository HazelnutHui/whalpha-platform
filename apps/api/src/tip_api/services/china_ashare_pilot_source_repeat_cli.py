"""CLI for an offline China A-share pilot source-repeat comparison."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tip_api.services.china_ashare_pilot_source_repeat import (
    compare_china_ashare_pilot_daily_packages,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two temporary A-share daily packages without network or "
            "canonical writes."
        )
    )
    parser.add_argument("--baseline-package", type=Path, required=True)
    parser.add_argument("--repeat-package", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = compare_china_ashare_pilot_daily_packages(
        baseline_package_path=args.baseline_package,
        repeat_package_path=args.repeat_package,
        compared_at=datetime.now(UTC),
    )
    print(
        json.dumps(
            {
                "status": result.status,
                "output_path": str(result.output_path),
                "total_change_count": result.report.total_change_count,
                "economic_values_stable": result.report.economic_values_stable,
                "source_repeat_qualified": result.report.source_repeat_qualified,
                "research_backtest_authorized": False,
                "canonical_apply_authorized": False,
                "deployment_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
