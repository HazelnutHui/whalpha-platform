"""Offline CLI for the non-authoritative Candidate segmented shadow."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from pathlib import Path

from tip_api.services.opportunity_candidate_segmented_shadow import (
    CandidateSegmentedShadowError,
    write_candidate_segmented_shadow,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a lossless Candidate V1 per-session shadow under /tmp."
    )
    parser.add_argument("--source-audit", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    if not args.source_audit.is_absolute() or not args.output_dir.is_absolute():
        parser.error("Candidate shadow paths must be absolute")
    try:
        with _offline_socket_guard():
            manifest = write_candidate_segmented_shadow(
                source_audit=args.source_audit,
                output_dir=args.output_dir,
            )
    except (CandidateSegmentedShadowError, OSError) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "completed",
                "output_dir": str(args.output_dir),
                "as_of_session": manifest["as_of_session"],
                "session_count": manifest["session_count"],
                "source_audit_logical_fingerprint": manifest[
                    "source_audit_logical_fingerprint"
                ],
                "shadow_logical_fingerprint": manifest[
                    "logical_content_fingerprint"
                ],
                "business_projection_match": True,
                "publication_authorized": False,
                "external_request_count": 0,
                "production_write_count": 0,
            },
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
            raise RuntimeError("network is prohibited during Candidate shadow creation")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during Candidate shadow creation")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during Candidate shadow creation")

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
