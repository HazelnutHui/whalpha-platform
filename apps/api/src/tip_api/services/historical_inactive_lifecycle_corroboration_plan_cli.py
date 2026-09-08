"""CLI for the offline inactive-lifecycle corroboration plan."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date, datetime
from pathlib import Path

from tip_api.services.historical_inactive_lifecycle_corroboration_plan import (
    HistoricalInactiveLifecycleCorroborationPlanError,
    build_historical_inactive_lifecycle_corroboration_plan,
    read_historical_inactive_lifecycle_corroboration_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build or verify a network-disabled inactive-lifecycle "
            "corroboration plan."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--shadow-root", required=True, type=Path)
    build_parser.add_argument("--anchor-date", required=True, type=date.fromisoformat)
    build_parser.add_argument("--plan-path", required=True, type=Path)
    build_parser.add_argument("--planned-at", required=True, type=datetime.fromisoformat)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--plan-path", required=True, type=Path)
    verify_parser.add_argument("--approved-plan-sha256", required=True)
    args = parser.parse_args(argv)

    revision: str | None = None
    try:
        if args.command == "build":
            revision = _clean_revision()
            evidence = build_historical_inactive_lifecycle_corroboration_plan(
                shadow_root=args.shadow_root,
                anchor_date=args.anchor_date,
                plan_path=args.plan_path,
                planned_at=args.planned_at,
                implementation_revision=revision,
            )
        else:
            evidence = read_historical_inactive_lifecycle_corroboration_plan(
                plan_path=args.plan_path,
                approved_plan_sha256=args.approved_plan_sha256,
            )
    except (
        HistoricalInactiveLifecycleCorroborationPlanError,
        OSError,
        subprocess.SubprocessError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "inactive_lifecycle_corroboration_plan_rejected",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "acquisition_authorized": False,
                    "canonical_lifecycle_authorized": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1

    plan = evidence.plan
    print(
        json.dumps(
            {
                "status": evidence.status,
                "plan_path": str(evidence.plan_path),
                "plan_sha256": evidence.plan_sha256,
                "plan_logical_fingerprint": plan.logical_fingerprint,
                "implementation_revision": plan.implementation_revision,
                "anchor_date": plan.anchor_date.isoformat(),
                "shadow_manifest_sha256": plan.shadow_manifest_sha256,
                "shadow_review_candidate_count": (
                    plan.shadow_review_candidate_count
                ),
                "shadow_quarantined_count": plan.shadow_quarantined_count,
                "primary_exchange_counts": dict(plan.primary_exchange_counts),
                "route_counts": dict(plan.route_counts),
                "status_counts": dict(plan.status_counts),
                "provider_last_updated_present_count": (
                    plan.provider_last_updated_present_count
                ),
                "point_in_time_eligible_count": plan.point_in_time_eligible_count,
                "ticker_locator_retained_count": plan.ticker_locator_retained_count,
                "external_request_count": plan.external_request_count,
                "canonical_data_write_count": plan.canonical_data_write_count,
                "acquisition_authorized": plan.acquisition_authorized,
                "canonical_lifecycle_authorized": (
                    plan.canonical_lifecycle_authorized
                ),
                "historical_coverage_authorized": (
                    plan.historical_coverage_authorized
                ),
                "research_performance_authorized": (
                    plan.research_performance_authorized
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def _clean_revision() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise HistoricalInactiveLifecycleCorroborationPlanError(
            "repository must be clean"
        )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
