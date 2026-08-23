"""Separately authorized, default-dry-run Dashboard Universe rollback CLI."""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.persistence.parquet.dashboard_universe_activation_active import (
    read_active_dashboard_universe_activation,
    read_dashboard_universe_activation_pointer,
    rollback_active_dashboard_universe_activation,
)


ROOT = Path("/data/trading-intelligence-platform")
SESSION = date(2026, 8, 19)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args in (["--help"], ["-h"]):
        print(
            "Usage: rollback-dashboard-universe-activation.sh "
            "[--apply --expected-active-pointer-fingerprint SHA256]"
        )
        return 0
    apply = len(args) == 3 and args[:2] == ["--apply", "--expected-active-pointer-fingerprint"]
    if args and not apply:
        print(
            "apply requires --apply --expected-active-pointer-fingerprint SHA256",
            file=sys.stderr,
        )
        return 2
    pointer = read_dashboard_universe_activation_pointer(ROOT)
    if pointer is None:
        raise RuntimeError("rollback is unavailable without an explicit active pointer")
    active = read_active_dashboard_universe_activation(ROOT, analysis_session=SESSION, validate_sources=True)
    result = {
        "mode": "apply" if apply else "dry-run",
        "status": "rollback_pending" if apply else "dry_run_ready",
        "active_before": pointer.active.model_dump(mode="json"),
        "rollback_target": pointer.rollback.model_dump(mode="json"),
        "active_fingerprint": active.manifest.logical_content_fingerprint,
        "expected_active_pointer_fingerprint": pointer.pointer_content_fingerprint,
        "apply_invocations": 1 if apply else 0,
    }
    if not apply:
        print(json.dumps(result, sort_keys=True))
        return 0
    if args[2] != pointer.pointer_content_fingerprint:
        raise RuntimeError("approved active pointer fingerprint no longer matches preflight")
    replacement = rollback_active_dashboard_universe_activation(
        ROOT,
        analysis_session=SESSION,
        expected_active_pointer_fingerprint=args[2],
        switched_at=datetime.now(UTC),
    )
    result.update(status="completed", active_after=replacement.active.model_dump(mode="json"))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
