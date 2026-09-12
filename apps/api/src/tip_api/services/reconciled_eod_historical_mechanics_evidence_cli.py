"""Offline CLI for one reconciled EOD edition's family evidence."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from pathlib import Path

from tip_api.persistence.historical_research import HistoricalResearchPersistenceError
from tip_api.persistence.instrument_master import InstrumentMasterSnapshotPersistenceError
from tip_api.persistence.parquet.reconciled_eod_edition import (
    ReconciledEodEditionPersistenceError,
)
from tip_api.services.reconciled_eod_historical_mechanics_evidence import (
    DEFAULT_VALIDATION_WORKERS,
    ReconciledEodHistoricalMechanicsEvidenceError,
    assess_reconciled_eod_historical_mechanics_evidence,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one exact reconciled EOD edition and matching Identity as "
            "unpublished historical family evidence."
        )
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--edition-id", required=True)
    parser.add_argument("--expected-interval-fingerprint", required=True)
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_VALIDATION_WORKERS,
        help="Bounded local validation process count (1-32).",
    )
    args = parser.parse_args(argv)
    try:
        with _offline_socket_guard():
            report = assess_reconciled_eod_historical_mechanics_evidence(
                data_root=args.data_root,
                edition_id=args.edition_id,
                expected_interval_manifest_fingerprint=(
                    args.expected_interval_fingerprint
                ),
                max_workers=args.workers,
            )
    except (
        ReconciledEodHistoricalMechanicsEvidenceError,
        ReconciledEodEditionPersistenceError,
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
                    "reason_code": (
                        "reconciled_eod_historical_mechanics_evidence_rejected"
                    ),
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
