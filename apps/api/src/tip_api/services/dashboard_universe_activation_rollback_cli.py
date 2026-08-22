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
        print("Usage: rollback-dashboard-universe-activation.sh [--apply]")
        return 0
    if args not in ([], ["--apply"]):
        print("only --apply is accepted", file=sys.stderr)
        return 2
    pointer = read_dashboard_universe_activation_pointer(ROOT)
    if pointer is None:
        raise RuntimeError("rollback is unavailable without an explicit active pointer")
    active = read_active_dashboard_universe_activation(ROOT, analysis_session=SESSION, validate_sources=True)
    result = {
        "mode": "apply" if args else "dry-run",
        "status": "rollback_pending" if args else "dry_run_ready",
        "active_before": pointer.active.model_dump(mode="json"),
        "rollback_target": pointer.rollback.model_dump(mode="json"),
        "active_fingerprint": active.manifest.logical_content_fingerprint,
        "apply_invocations": 1 if args else 0,
    }
    if not args:
        print(json.dumps(result, sort_keys=True))
        return 0
    replacement = rollback_active_dashboard_universe_activation(
        ROOT,
        analysis_session=SESSION,
        expected_active_fingerprint=active.manifest.logical_content_fingerprint,
        switched_at=datetime.now(UTC),
    )
    result.update(status="completed", active_after=replacement.active.model_dump(mode="json"))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
