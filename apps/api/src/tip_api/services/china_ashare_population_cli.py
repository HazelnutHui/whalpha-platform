"""CLI for freezing the five-year A-share source population."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.services.china_ashare_population_capture import (
    capture_and_publish_china_ashare_population,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity-lifecycle-package", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--interval-start", type=date.fromisoformat, required=True)
    parser.add_argument("--interval-end", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    result = capture_and_publish_china_ashare_population(
        identity_lifecycle_package_path=args.identity_lifecycle_package,
        custody_root=args.custody_root,
        interval_start=args.interval_start,
        interval_end=args.interval_end,
        captured_at=datetime.now(UTC),
    )
    print(
        json.dumps(
            {
                "status": result.status,
                "package_path": str(result.package_path),
                "manifest_fingerprint": result.manifest.logical_fingerprint,
                "report_fingerprint": result.report.logical_fingerprint,
                "official_candidate_count": result.report.official_candidate_count,
                "expansion_target_count": result.report.expansion_target_count,
                "resolved_count": result.report.resolved_count,
                "quarantined_count": result.report.quarantined_count,
                "outside_scope_count": result.report.outside_scope_count,
                "listing_date_conflict_count": (
                    result.report.cross_source_listing_date_conflict_count
                ),
                "unresolved_board_count": result.report.unresolved_board_count,
                "full_market_expansion_authorized": (
                    result.report.full_market_expansion_authorized
                ),
                "research_backtest_authorized": (
                    result.report.research_backtest_authorized
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
