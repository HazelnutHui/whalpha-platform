"""CLI for bounded A-share market-mechanics evidence capture."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tip_api.services.china_ashare_market_mechanics import (
    capture_and_publish_pilot_market_mechanics,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Capture official A-share trading-rule and fee evidence, reconcile "
            "pilot price limits, and retain an immutable non-activated package."
        )
    )
    parser.add_argument("--daily-package", type=Path, required=True)
    parser.add_argument("--calendar-package", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = capture_and_publish_pilot_market_mechanics(
        daily_package_path=args.daily_package,
        calendar_package_path=args.calendar_package,
        custody_root=args.custody_root,
        captured_at=datetime.now(UTC),
    )
    report = result.report
    print(
        json.dumps(
            {
                "market_mechanics_package_path": str(result.package_path),
                "file_count": result.file_count,
                "total_bytes": result.total_bytes,
                "source_reference_count": report.source_reference_count,
                "trading_rule_count": report.trading_rule_count,
                "fee_rule_count": report.fee_rule_count,
                "price_limit_decision_count": report.price_limit_decision_count,
                "price_limit_violation_count": report.price_limit_violation_count,
                "unresolved_rule_count": report.unresolved_rule_count,
                "effective_dated_rules_reconciled": (
                    report.effective_dated_rules_reconciled
                ),
                "effective_dated_fees_reconciled": (
                    report.effective_dated_fees_reconciled
                ),
                "account_cost_scenario_registered": (
                    report.account_cost_scenario_registered
                ),
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
