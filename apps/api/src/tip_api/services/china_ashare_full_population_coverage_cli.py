"""CLI for exact A-share full-population coverage verification and custody."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tip_api.persistence.china_ashare_full_population_coverage import (
    publish_china_ashare_full_population_coverage,
)
from tip_api.services.china_ashare_full_population_coverage import (
    verify_china_ashare_full_population_coverage,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normalized-run-root", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    args = parser.parse_args()
    report = verify_china_ashare_full_population_coverage(
        normalized_run_root=args.normalized_run_root
    )
    result = publish_china_ashare_full_population_coverage(
        custody_root=args.custody_root, report=report
    )
    print(
        json.dumps(
            {
                "status": result.status,
                "package_path": str(result.package_path),
                "report_fingerprint": result.report.logical_fingerprint,
                "report_physical_sha256": result.report_physical_sha256,
                "family_count": len(result.report.families),
                "historical_coverage_admitted": False,
                "research_backtest_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
