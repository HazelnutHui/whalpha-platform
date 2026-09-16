"""CLI for one bounded temporary China A-share pilot reference capture."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from tip_api.providers.china_ashare import (
    AkshareAshareReferenceAdapter,
    BaoStockAshareSourceAdapter,
    BaoStockClientSession,
)
from tip_api.services.china_ashare_pilot_reference import (
    build_default_china_ashare_pilot_plan,
    capture_china_ashare_pilot_reference,
)


_SHANGHAI = ZoneInfo("Asia/Shanghai")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Capture a bounded normalized A-share reference pilot below /tmp; "
            "this grants no canonical, research, Product, or deployment authority."
        )
    )
    parser.add_argument("--baostock-snapshot-date", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--custody-root",
        type=Path,
        default=Path("/tmp/china-a-share-research-pilot"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    observed_at = datetime.now(UTC)
    official_date = observed_at.astimezone(_SHANGHAI).date()
    plan = build_default_china_ashare_pilot_plan(
        planned_at=observed_at,
        official_reference_as_of_date=official_date,
        baostock_snapshot_date=args.baostock_snapshot_date,
    )
    try:
        import akshare as akshare_module
    except ImportError as exc:
        raise SystemExit("AKShare optional dependency is unavailable") from exc
    official_adapter = AkshareAshareReferenceAdapter(
        module=akshare_module,
        clock=lambda: observed_at,
    )
    with BaoStockClientSession() as session:
        result = capture_china_ashare_pilot_reference(
            custody_root=args.custody_root,
            plan=plan,
            official_adapter=official_adapter,
            baostock_adapter=BaoStockAshareSourceAdapter(
                session=session,
                clock=lambda: observed_at,
            ),
            created_at=observed_at,
        )
    print(
        json.dumps(
            {
                "status": result.status,
                "package_path": str(result.package_path),
                "official_reference_as_of_date": (
                    result.plan.official_reference_as_of_date.isoformat()
                ),
                "baostock_snapshot_date": (
                    result.plan.baostock_snapshot_date.isoformat()
                ),
                "reference_evidence_complete": (
                    result.quality_report.reference_evidence_complete
                ),
                "official_current_missing_ids": (
                    result.quality_report.official_current_missing_ids
                ),
                "baostock_snapshot_missing_ids": (
                    result.quality_report.baostock_snapshot_missing_ids
                ),
                "lifecycle_missing_keys": (
                    result.quality_report.lifecycle_missing_keys
                ),
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
