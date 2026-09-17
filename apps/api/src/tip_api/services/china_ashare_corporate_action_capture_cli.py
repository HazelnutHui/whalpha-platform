"""CLI for one explicit A-share corporate-action evidence capture."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tip_api.services.china_ashare_corporate_action_capture import (
    capture_and_publish_china_ashare_corporate_action_evidence,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daily-package", required=True, type=Path)
    parser.add_argument("--custody-root", required=True, type=Path)
    args = parser.parse_args()
    result = capture_and_publish_china_ashare_corporate_action_evidence(
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
                "corporate_action_count": result.report.corporate_action_count,
                "matched_action_count": result.report.matched_action_count,
                "provider_noop_correction_count": (
                    result.report.provider_noop_correction_count
                ),
                "corporate_action_family_complete": (
                    result.report.corporate_action_family_complete
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
