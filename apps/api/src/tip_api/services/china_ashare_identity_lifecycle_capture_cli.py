"""CLI for explicit A-share identity/lifecycle evidence capture."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tip_api.services.china_ashare_identity_lifecycle_capture import (
    capture_and_publish_china_ashare_identity_lifecycle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-package", type=Path, required=True)
    parser.add_argument("--daily-package", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    args = parser.parse_args()
    result = capture_and_publish_china_ashare_identity_lifecycle(
        reference_package_path=args.reference_package,
        daily_package_path=args.daily_package,
        custody_root=args.custody_root,
        captured_at=datetime.now(UTC),
    )
    print(
        json.dumps(
            {
                "status": result.status,
                "package_path": str(result.package_path),
                "manifest_fingerprint": result.manifest.logical_fingerprint,
                "report_fingerprint": result.report.logical_fingerprint,
                "resolved_identity_count": result.report.resolved_identity_count,
                "complete_lifecycle_count": result.report.complete_lifecycle_count,
                "stable_identity_family_complete": (
                    result.report.stable_identity_family_complete
                ),
                "lifecycle_family_complete": result.report.lifecycle_family_complete,
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
