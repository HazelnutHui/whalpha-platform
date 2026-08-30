"""Credential-free CLI for one strategy research readiness assessment."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from pathlib import Path

from tip_api.contracts.analytics.v1 import (
    strong_stock_pullback_research_experiment_v1,
)
from tip_api.persistence.eod_read import EodReadError
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.strategy_research_readiness import (
    StrategyResearchReadinessError,
    assess_strategy_research_readiness,
    canonical_eod_identity_evidence,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Assess one strategy experiment against Dell-local historical evidence."
        )
    )
    parser.add_argument("--data-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with _offline_socket_guard():
            descriptors = CanonicalEodReadRepository(args.data_root).list_sessions()
            canonical = canonical_eod_identity_evidence(descriptors)
            assessment = assess_strategy_research_readiness(
                experiment=strong_stock_pullback_research_experiment_v1(),
                canonical_evidence=canonical,
            )
    except (
        EodReadError,
        OSError,
        RuntimeError,
        StrategyResearchReadinessError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "strategy_research_readiness_rejected",
                    "error_type": type(exc).__name__,
                    "development_authorized": False,
                    "performance_claims_authorized": False,
                    "external_request_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(assessment.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during research readiness")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during research readiness")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during research readiness")

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
