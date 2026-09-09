"""Network-prohibited CLI for daily Membership sidecar planning."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.services.daily_eod_automation import plan_daily_eod_automation
from tip_api.services.daily_eod_automation_cli import _offline_socket_guard
from tip_api.services.daily_eod_workspace import derive_daily_eod_workspace_layout
from tip_api.services.daily_universe_membership_sidecar import (
    MembershipSidecarStatus,
    plan_daily_universe_membership_sidecar,
)
from tip_api.services.market_calendar import ExchangeCalendar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read formal Dell state and report the next independent daily "
            "Universe Membership research action."
        )
    )
    parser.add_argument("--checked-at", type=datetime.fromisoformat)
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--catalog-as-of-date",
        required=True,
        type=date.fromisoformat,
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--repository-root", required=True, type=Path)
    args = parser.parse_args(argv)
    for name in ("data_root", "workspace_root", "repository_root"):
        if not getattr(args, name).is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    checked_at = args.checked_at or datetime.now(tz=UTC)
    try:
        with _offline_socket_guard():
            calendar = ExchangeCalendar()
            prior_session = calendar.previous_session(args.as_of_session)
            layout = derive_daily_eod_workspace_layout(
                workspace_root=args.workspace_root,
                data_root=args.data_root,
                repository_root=args.repository_root,
                target_session=args.as_of_session,
                prior_session=prior_session,
            )
            primary = plan_daily_eod_automation(
                target_session=args.as_of_session,
                paths=layout.as_automation_paths(),
            )
            plan = plan_daily_universe_membership_sidecar(
                checked_at=checked_at,
                target_session=args.as_of_session,
                data_root=args.data_root,
                catalog_as_of_date=args.catalog_as_of_date,
                candidate_root=layout.universe_membership_candidate_root,
                apply_plan_path=layout.universe_membership_apply_plan,
                primary_automation_plan=primary,
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "daily_membership_sidecar_plan_rejected",
                    "error_type": type(exc).__name__,
                    "website_pipeline_blocked": False,
                    "apply_authorized": False,
                    "scheduler_enabled": False,
                    "external_request_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    payload = plan.as_dict()
    payload["checked_at_source"] = (
        "explicit_argument" if args.checked_at is not None else "system_utc_clock"
    )
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 1 if plan.status is MembershipSidecarStatus.BLOCKED else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
