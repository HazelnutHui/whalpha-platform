"""Default-review CLI for the finite daily Membership sidecar runner."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.services.daily_eod_automation import DailyEodAutomationError
from tip_api.services.daily_eod_workspace import (
    DailyEodWorkspaceError,
    derive_daily_eod_workspace_layout,
)
from tip_api.services.daily_universe_membership_runner import (
    DEFAULT_MAXIMUM_ACTIONS,
    DEFAULT_MAXIMUM_ELAPSED_SECONDS,
    DailyUniverseMembershipRunConfig,
    DailyUniverseMembershipRunnerError,
    MembershipRunStatus,
    run_bounded_daily_universe_membership,
)
from tip_api.services.daily_universe_membership_sidecar import (
    DailyUniverseMembershipSidecarError,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketCalendarError
from tip_api.services.universe_membership_knowledge_time_cli import (
    _offline_socket_guard,
)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _validate_arguments(parser, args)
    started_at = args.started_at or datetime.now(UTC)
    try:
        repository_root = _source_repository_root()
        prior_session = ExchangeCalendar().previous_session(args.as_of_session)
        layout = derive_daily_eod_workspace_layout(
            workspace_root=args.workspace_root,
            data_root=args.data_root,
            repository_root=repository_root,
            target_session=args.as_of_session,
            prior_session=prior_session,
        )
        config = DailyUniverseMembershipRunConfig(
            target_session=args.as_of_session,
            data_root=args.data_root,
            catalog_as_of_date=args.catalog_as_of_date,
            candidate_root=layout.universe_membership_candidate_root,
            apply_plan_path=layout.universe_membership_apply_plan,
            primary_automation_paths=layout.as_automation_paths(),
        )
        with _offline_socket_guard():
            result = run_bounded_daily_universe_membership(
                config=config,
                started_at=started_at,
                execute=args.execute,
                maximum_actions=args.maximum_actions,
                maximum_elapsed_seconds=args.maximum_elapsed_seconds,
            )
    except (
        DailyUniverseMembershipRunnerError,
        DailyUniverseMembershipSidecarError,
        DailyEodAutomationError,
        DailyEodWorkspaceError,
        MarketCalendarError,
        OSError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "daily_membership_bounded_run_rejected",
                    "error_type": type(exc).__name__,
                    "execution_enabled": args.execute,
                    "automatic_retry_enabled": False,
                    "automatic_recovery_enabled": False,
                    "website_pipeline_blocked": False,
                    "primary_pipeline_invocation_count": 0,
                    "external_request_count": 0,
                    "production_write_count": 0,
                    "canonical_membership_apply_performed": False,
                    "scheduler_installation_performed": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    payload = result.as_dict()
    payload["started_at_source"] = (
        "explicit_argument" if args.started_at is not None else "system_utc_clock"
    )
    payload["workspace_layout_fingerprint"] = layout.logical_content_fingerprint
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    if result.status in {
        MembershipRunStatus.BLOCKED,
        MembershipRunStatus.ACTION_FAILED,
    }:
        return 1
    if result.status is MembershipRunStatus.BUDGET_EXHAUSTED:
        return 2
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Review or execute at most two Dell-local Membership sidecar "
            "workspace actions, always stopping before canonical Apply."
        )
    )
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--catalog-as-of-date",
        required=True,
        type=date.fromisoformat,
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--started-at", type=datetime.fromisoformat)
    parser.add_argument("--maximum-actions", type=int, default=DEFAULT_MAXIMUM_ACTIONS)
    parser.add_argument(
        "--maximum-elapsed-seconds",
        type=int,
        default=DEFAULT_MAXIMUM_ELAPSED_SECONDS,
    )
    parser.add_argument("--execute", action="store_true")
    return parser


def _validate_arguments(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    for name in ("data_root", "workspace_root"):
        if not getattr(args, name).is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    if args.workspace_root.name != "daily-eod":
        parser.error("--workspace-root basename must be daily-eod")
    if args.started_at is not None and (
        args.started_at.tzinfo is None or args.started_at.utcoffset() is None
    ):
        parser.error("--started-at must be timezone aware")


def _source_repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise DailyEodWorkspaceError("executing source repository root is unavailable")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
