"""CLI for fail-closed A-share dynamic gap checklist and replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tip_api.services.china_ashare_full_population_gaps import (
    build_and_replay_china_ashare_full_population_gap_checklist,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnostic-plan-package", type=Path, required=True)
    parser.add_argument("--diagnostic-aggregate-package", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--replay-custody-root", type=Path, required=True)
    args = parser.parse_args()
    result = build_and_replay_china_ashare_full_population_gap_checklist(
        diagnostic_plan_package=args.diagnostic_plan_package,
        diagnostic_aggregate_package=args.diagnostic_aggregate_package,
        output_custody_root=args.custody_root,
        replay_custody_root=args.replay_custody_root,
    )
    checklist = result.primary.checklist
    print(
        json.dumps(
            {
                "status": "exact_replay_complete",
                "package_path": str(result.primary.package_path),
                "checklist_fingerprint": checklist.logical_fingerprint,
                "physical_sha256": result.primary.physical_sha256,
                "total_bytes": result.primary.total_bytes,
                "family_count": len(checklist.entries),
                "admitted_family_count": checklist.admitted_family_count,
                "measures": {
                    measure.measure_id: measure.count
                    for entry in checklist.entries
                    for measure in entry.measures
                },
                "byte_identical": result.byte_identical,
                "physical_hash_identical": result.physical_hash_identical,
                "future_return_read_count": 0,
                "full_universe_rows_materialized": False,
                "historical_coverage_authorized": False,
                "research_backtest_authorized": False,
                "factor_discovery_authorized": False,
                "product_publication_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
