"""CLI for the bounded official A-share calendar evidence capture."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tip_api.services.china_ashare_calendar_evidence import (
    capture_and_publish_official_calendar_evidence,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Retain exact SSE/SZSE annual closure notices and reconcile them "
            "with one temporary A-share pilot package."
        )
    )
    parser.add_argument("--daily-package", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = capture_and_publish_official_calendar_evidence(
        daily_package_path=args.daily_package,
        custody_root=args.custody_root,
        captured_at=datetime.now(UTC),
    )
    report = result.report
    print(
        json.dumps(
            {
                "calendar_package_path": str(result.package_path),
                "file_count": result.file_count,
                "total_bytes": result.total_bytes,
                "notice_count": report.notice_count,
                "expected_session_count": report.expected_session_count,
                "official_weekday_closure_count": len(
                    report.official_weekday_closure_dates
                ),
                "official_exchange_notice_retained": (
                    report.official_exchange_notice_retained
                ),
                "calendar_reconciled": report.calendar_reconciled,
                "research_backtest_authorized": False,
                "report_fingerprint": report.logical_fingerprint,
                "package_fingerprint": result.manifest.logical_fingerprint,
                "status": result.status,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
