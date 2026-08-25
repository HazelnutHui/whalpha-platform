"""Generate or verify one read-only, tmp-only Market Regime preview bundle."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.services.market_regime_preview import (
    build_market_regime_preview_bundle,
    read_market_regime_preview_bundle,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a canonical local Market Regime preview bundle from explicit Phase 1/2 audits."
    )
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument("--phase1a-audit", required=True, type=Path)
    parser.add_argument("--phase1b-audit", required=True, type=Path)
    parser.add_argument("--phase2-audit", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verify-output", action="store_true")
    args = parser.parse_args(argv)
    for name in ("phase1a_audit", "phase1b_audit", "phase2_audit", "output_dir"):
        if not getattr(args, name).is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    with _offline_socket_guard():
        if args.verify_output:
            completed = read_market_regime_preview_bundle(args.output_dir)
        else:
            completed = build_market_regime_preview_bundle(
                phase1a_audit_dir=args.phase1a_audit,
                phase1b_audit_dir=args.phase1b_audit,
                phase2_audit_dir=args.phase2_audit,
                output_dir=args.output_dir,
                generated_at=datetime.now(UTC),
            )
    if completed.payload.as_of_session != args.as_of_session:
        parser.error("--as-of-session differs from the completed source audits")
    print(json.dumps({
        "status": "completed",
        "as_of_session": completed.payload.as_of_session.isoformat(),
        "output_dir": str(completed.path),
        "payload_logical_fingerprint": completed.payload.logical_fingerprint,
        "manifest_logical_fingerprint": completed.manifest.manifest_logical_fingerprint,
        "universes": len(completed.payload.universes),
        "relationships": len(completed.payload.relationships),
        "external_request_count": 0,
        "production_write_count": 0,
    }, sort_keys=True, separators=(",", ":")))
    return 0


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddr = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):
            raise RuntimeError("network prohibited during preview bundle generation")

        def connect_ex(self, *args, **kwargs):
            raise RuntimeError("network prohibited during preview bundle generation")

    def rejected(*args, **kwargs):
        raise RuntimeError("network prohibited during preview bundle generation")

    socket.socket = GuardedSocket
    socket.create_connection = rejected
    socket.getaddrinfo = rejected
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create
        socket.getaddrinfo = original_getaddr


if __name__ == "__main__":
    raise SystemExit(main())
