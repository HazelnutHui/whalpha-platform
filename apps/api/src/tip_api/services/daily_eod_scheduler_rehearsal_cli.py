"""CLI for the credential-free synthetic scheduler rehearsal."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager

from tip_api.services.daily_eod_readiness import (
    DailyEodReadinessPolicy,
    ProviderRecencyProfile,
)
from tip_api.services.daily_eod_scheduler_rehearsal import (
    review_daily_eod_scheduler_rehearsal,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the credential-free synthetic scheduler rehearsal."
    )
    parser.add_argument(
        "--provider-recency-profile",
        choices=tuple(item.value for item in ProviderRecencyProfile),
        default=ProviderRecencyProfile.MASSIVE_STOCKS_BASIC_END_OF_DAY.value,
    )
    args = parser.parse_args(argv)
    with _offline_socket_guard():
        report = review_daily_eod_scheduler_rehearsal(
            policy=DailyEodReadinessPolicy(
                provider_recency_profile=ProviderRecencyProfile(
                    args.provider_recency_profile
                )
            )
        )
    print(json.dumps(report.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during scheduler rehearsal")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during scheduler rehearsal")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during scheduler rehearsal")

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
