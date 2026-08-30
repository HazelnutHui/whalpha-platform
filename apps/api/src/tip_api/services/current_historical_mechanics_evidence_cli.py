"""Offline CLI for current EOD/Identity mechanics evidence validation."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from pathlib import Path

from tip_api.persistence.eod_read import EodReadError
from tip_api.persistence.historical_research import HistoricalResearchPersistenceError
from tip_api.persistence.instrument_master import InstrumentMasterSnapshotPersistenceError
from tip_api.services.current_historical_mechanics_evidence import (
    CurrentHistoricalMechanicsEvidenceError,
    assess_current_historical_mechanics_evidence,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate current Dell EOD/Identity bytes as unpublished historical "
            "family evidence."
        )
    )
    parser.add_argument("--data-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with _offline_socket_guard():
            report = assess_current_historical_mechanics_evidence(args.data_root)
    except (
        CurrentHistoricalMechanicsEvidenceError,
        EodReadError,
        HistoricalResearchPersistenceError,
        InstrumentMasterSnapshotPersistenceError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "current_historical_mechanics_evidence_rejected",
                    "error_type": type(exc).__name__,
                    "evidence_publication_performed": False,
                    "historical_coverage_publication_performed": False,
                    "external_request_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(report.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during mechanics validation")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during mechanics validation")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during mechanics validation")

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
