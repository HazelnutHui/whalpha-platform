"""CLI for the non-authorizing China A-share pilot calendar diagnostic."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tip_api.services.china_ashare_pilot_calendar import (
    inspect_china_ashare_pilot_calendar_package,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare one temporary A-share daily package with the offline XSHG "
            "calendar; this does not authorize research."
        )
    )
    parser.add_argument("--daily-package", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = inspect_china_ashare_pilot_calendar_package(
        daily_package_path=args.daily_package,
        evaluated_at=datetime.now(UTC),
    )
    print(
        json.dumps(
            {
                "calendar_id": report.calendar_id,
                "calendar_version": report.calendar_version,
                "expected_session_count": report.expected_session_count,
                "observed_union_session_count": report.observed_union_session_count,
                "instrument_count": len(report.instrument_coverage),
                "missing_union_session_count": len(
                    report.missing_union_session_dates
                ),
                "unexpected_union_state_count": len(
                    report.unexpected_union_state_dates
                ),
                "library_source_alignment_complete": (
                    report.library_source_alignment_complete
                ),
                "official_exchange_notice_retained": False,
                "calendar_reconciled": False,
                "research_backtest_authorized": False,
                "logical_fingerprint": report.logical_fingerprint,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
