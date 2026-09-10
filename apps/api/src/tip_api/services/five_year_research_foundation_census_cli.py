"""Offline entry point for the ADR 0196 five-year foundation census."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from pathlib import Path

from tip_api.services.five_year_research_foundation_census import (
    FiveYearResearchFoundationCensusError,
    assess_five_year_research_foundation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Formally reread Dell canonical families and emit the rolling "
            "five-year point-in-time coverage census without writes."
        )
    )
    parser.add_argument("--data-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with _offline_socket_guard():
            report = assess_five_year_research_foundation(args.data_root)
    except (FiveYearResearchFoundationCensusError, OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "five_year_foundation_census_rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_write_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(
        json.dumps(
            report.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during five-year census")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during five-year census")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during five-year census")

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
