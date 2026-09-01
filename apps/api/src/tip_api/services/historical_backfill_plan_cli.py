"""Socket-guarded CLI for an exact current historical backfill plan."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from pathlib import Path

from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.current_historical_mechanics_evidence import (
    assess_current_historical_mechanics_evidence,
)
from tip_api.services.historical_backfill_planner import (
    DEFAULT_TARGET_SESSIONS,
    HistoricalBackfillInventoryV1,
    HistoricalBackfillPlannerError,
    HistoricalBackfillRequestV1,
    plan_historical_research_backfill,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Formally reread current Dell EOD/Identity and build a non-authorizing "
            "historical research backfill plan."
        )
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument(
        "--target-session-count",
        type=int,
        default=DEFAULT_TARGET_SESSIONS,
    )
    args = parser.parse_args(argv)
    try:
        with _offline_socket_guard():
            mechanics = assess_current_historical_mechanics_evidence(args.data_root)
            descriptors = CanonicalEodReadRepository(args.data_root).list_sessions()
            sessions = tuple(item.session_date for item in descriptors)
            identity_sessions = tuple(item.identity_as_of_date for item in descriptors)
            if (
                len(sessions) != mechanics.observed_session_count
                or sessions[0].isoformat() != mechanics.first_session
                or sessions[-1].isoformat() != mechanics.last_session
            ):
                raise HistoricalBackfillPlannerError(
                    "formal mechanics evidence differs from the canonical index"
                )
            plan = plan_historical_research_backfill(
                inventory=HistoricalBackfillInventoryV1(
                    inventory_fingerprint=inventory_fingerprint(args.data_root),
                    completed_eod_sessions=sessions,
                    completed_identity_sessions=identity_sessions,
                ),
                request=HistoricalBackfillRequestV1(
                    target_session_count=args.target_session_count
                ),
            )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "historical_backfill_plan_rejected",
                    "error_type": type(exc).__name__,
                    "network_allowed": False,
                    "external_request_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(plan.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during backfill planning")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during backfill planning")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during backfill planning")

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
