"""Credential-free CLI for the daily EOD automation planner."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from tip_api.services.daily_eod_automation import (
    DailyEodAutomationError,
    DailyEodAutomationPaths,
    PlanStatus,
    plan_daily_eod_automation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read formal Dell state and report the next safe daily EOD action."
    )
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--phase1a-audit", required=True, type=Path)
    parser.add_argument("--prior-phase1b-audit", required=True, type=Path)
    parser.add_argument("--phase1b-audit", required=True, type=Path)
    parser.add_argument("--prior-candidate-audit", required=True, type=Path)
    parser.add_argument("--candidate-audit", required=True, type=Path)
    parser.add_argument("--entry-geometry-audit", required=True, type=Path)
    parser.add_argument("--phase2-audit", required=True, type=Path)
    parser.add_argument("--preview-bundle", required=True, type=Path)
    parser.add_argument("--strategy-channel-audit", required=True, type=Path)
    args = parser.parse_args(argv)
    for name in (
        "data_root",
        "phase1a_audit",
        "prior_phase1b_audit",
        "phase1b_audit",
        "prior_candidate_audit",
        "candidate_audit",
        "entry_geometry_audit",
        "phase2_audit",
        "preview_bundle",
        "strategy_channel_audit",
    ):
        if not getattr(args, name).is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    try:
        with _offline_socket_guard():
            plan = plan_daily_eod_automation(
                target_session=args.as_of_session,
                paths=DailyEodAutomationPaths(
                    data_root=args.data_root,
                    phase1a_audit=args.phase1a_audit,
                    prior_phase1b_audit=args.prior_phase1b_audit,
                    phase1b_audit=args.phase1b_audit,
                    prior_candidate_audit=args.prior_candidate_audit,
                    candidate_audit=args.candidate_audit,
                    entry_geometry_audit=args.entry_geometry_audit,
                    phase2_audit=args.phase2_audit,
                    preview_bundle=args.preview_bundle,
                    strategy_channel_audit=args.strategy_channel_audit,
                ),
            )
    except DailyEodAutomationError as exc:
        parser.error(str(exc))
    print(json.dumps(plan.as_dict(), sort_keys=True, separators=(",", ":")))
    return 1 if plan.status is PlanStatus.BLOCKED else 0


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during daily EOD planning")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during daily EOD planning")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during daily EOD planning")

    socket.socket = GuardedSocket
    socket.create_connection = rejected
    socket.getaddrinfo = rejected
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create
        socket.getaddrinfo = original_getaddrinfo


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
