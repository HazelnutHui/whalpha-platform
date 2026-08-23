"""Default-dry-run verify-then-link recovery for completed Activation V2."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

from tip_api.persistence.parquet.dashboard_universe_activation_active import (
    ParquetDashboardUniverseActivationV2Repository,
    active_pointer_state_fingerprint,
    read_active_dashboard_universe_activation,
    validate_activation_v2_link_preflight,
)
from tip_api.services.dashboard_universe_activation_v2_cli import (
    EXPECTED_CURRENT,
    ROOT,
    SESSION,
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args in (["--help"], ["-h"]):
        print(
            "Usage: recover-dashboard-universe-activation-v2.sh "
            "[--apply --expected-current-pointer-fingerprint SHA256_OR_absent]"
        )
        return 0
    apply = len(args) == 3 and args[:2] == ["--apply", "--expected-current-pointer-fingerprint"]
    if args and not apply:
        print(
            "apply requires --apply --expected-current-pointer-fingerprint SHA256_OR_absent",
            file=sys.stderr,
        )
        return 2
    completed = validate_activation_v2_link_preflight(ROOT, SESSION)
    current = read_active_dashboard_universe_activation(
        ROOT, analysis_session=SESSION, validate_sources=True
    )
    if current.manifest.logical_content_fingerprint != EXPECTED_CURRENT:
        raise RuntimeError("current Production activation hard gate failed")
    expected_pointer = active_pointer_state_fingerprint(ROOT)
    result = {
        "mode": "apply" if apply else "dry-run",
        "status": "activate_existing_pending" if apply else "dry_run_ready",
        "analysis_session": SESSION.isoformat(),
        "target_logical_content_fingerprint": completed.manifest.logical_content_fingerprint,
        "expected_current_activation_fingerprint": current.manifest.logical_content_fingerprint,
        "expected_current_pointer_fingerprint": expected_pointer,
        "default_universe_id": completed.manifest.default_universe_id,
        "available_universe_ids": list(completed.manifest.available_universe_ids),
        "universes": [
            {
                "universe_id": record.universe_id,
                "member_count": record.member_count,
                "membership_fingerprint": record.membership_fingerprint,
            }
            for record in completed.universes
        ],
        "apply_invocations": 1 if apply else 0,
    }
    if not apply:
        print(json.dumps(result, sort_keys=True))
        return 0
    approved_pointer = args[2]
    if approved_pointer != expected_pointer:
        raise RuntimeError("approved current pointer fingerprint no longer matches preflight")
    pointer = ParquetDashboardUniverseActivationV2Repository(ROOT).activate_existing(
        analysis_session=SESSION,
        expected_current_pointer_fingerprint=approved_pointer,
        expected_current_activation_fingerprint=current.manifest.logical_content_fingerprint,
        expected_target_logical_fingerprint=completed.manifest.logical_content_fingerprint,
        switched_at=datetime.now(UTC),
    )
    result.update(
        status="completed",
        pointer_content_fingerprint=pointer.pointer_content_fingerprint,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
