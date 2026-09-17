"""CLI for the bounded A-share daily Universe gate."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tip_api.services.china_ashare_daily_universe_capture import (
    build_and_publish_china_ashare_daily_universe,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily-package", type=Path, required=True)
    parser.add_argument("--identity-lifecycle-package", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    args = parser.parse_args()
    result = build_and_publish_china_ashare_daily_universe(
        daily_package_path=args.daily_package,
        identity_lifecycle_package_path=args.identity_lifecycle_package,
        custody_root=args.custody_root,
        evaluated_at=datetime.now(UTC),
    )
    print(
        json.dumps(
            {
                "status": result.status,
                "package_path": str(result.package_path),
                "manifest_fingerprint": result.manifest.logical_fingerprint,
                "report_fingerprint": result.report.logical_fingerprint,
                "decision_count": result.report.decision_count,
                "included_count": result.report.included_count,
                "excluded_count": result.report.excluded_count,
                "quarantined_count": result.report.quarantined_count,
                "performance_eligible_count": (
                    result.report.performance_eligible_count
                ),
                "daily_universe_family_complete": (
                    result.report.daily_universe_family_complete
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
