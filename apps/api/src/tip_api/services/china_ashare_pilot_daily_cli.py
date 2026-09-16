"""CLI for the bounded temporary China A-share five-year daily pilot."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tip_api.persistence.china_ashare_pilot_package import (
    read_china_ashare_pilot_reference_package,
)
from tip_api.providers.china_ashare import (
    BaoStockAshareSourceAdapter,
    BaoStockClientSession,
)
from tip_api.services.china_ashare_pilot_reference import (
    capture_china_ashare_pilot_daily,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Capture a normalized five-year A-share daily pilot below /tmp; "
            "this grants no canonical, return, research, Product, or deployment authority."
        )
    )
    parser.add_argument("--reference-package", type=Path, required=True)
    parser.add_argument(
        "--custody-root",
        type=Path,
        default=Path("/tmp/china-a-share-research-pilot"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    reference = read_china_ashare_pilot_reference_package(
        package_path=args.reference_package
    )
    captured_at = datetime.now(UTC)
    with BaoStockClientSession() as session:
        result = capture_china_ashare_pilot_daily(
            custody_root=args.custody_root,
            plan=reference.plan,
            reference_package_fingerprint=reference.manifest.logical_fingerprint,
            reference_evidence=reference.captured,
            baostock_adapter=BaoStockAshareSourceAdapter(
                session=session,
                clock=lambda: captured_at,
            ),
            created_at=captured_at,
        )
    report = result.quality_report
    print(
        json.dumps(
            {
                "status": result.status,
                "package_path": str(result.package_path),
                "daily_requested_count": len(report.daily_requested_ids),
                "quarantined_count": len(report.quarantined_ids),
                "daily_bar_count": report.daily_bar_count,
                "daily_state_count": report.daily_state_count,
                "suspended_state_count": report.suspended_state_count,
                "risk_warning_state_count": report.risk_warning_state_count,
                "adjustment_observation_count": (
                    report.adjustment_observation_count
                ),
                "diverse_scenarios_observed": report.diverse_scenarios_observed,
                "calendar_reconciled": False,
                "adjustment_semantics_reconciled": False,
                "research_backtest_authorized": False,
                "canonical_apply_authorized": False,
                "product_publication_authorized": False,
                "deployment_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
