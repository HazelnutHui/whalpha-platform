"""Admin CLI for separately authorized Dashboard Snapshot V2 rollback."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tip_api.persistence.parquet.dashboard_snapshot_active import (
    DashboardSnapshotPublicationError,
    read_dashboard_snapshot_pointer,
    rollback,
)

ROOT = Path("/data/trading-intelligence-platform")
REPO_ROOT = Path(__file__).resolve().parents[5]
LEGACY_ROOT = REPO_ROOT / "build/private-dashboard"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dry-run or execute a separately approved Dashboard Snapshot V2 rollback."
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-active-pointer-fingerprint")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.apply and not args.expected_active_pointer_fingerprint:
        _parser().error("rollback --apply requires an approved active pointer fingerprint")
    if not args.apply and args.expected_active_pointer_fingerprint:
        _parser().error("expected pointer fingerprint is only accepted with --apply")
    if args.apply:
        result = rollback(
            root=ROOT,
            legacy_root=LEGACY_ROOT,
            expected_pointer_fingerprint=args.expected_active_pointer_fingerprint,
            apply=True,
        )
        print(json.dumps({
            "status": "rollback_completed",
            "release_id": result.manifest.release_id,
            "active_pointer_fingerprint": (
                result.pointer.pointer_content_fingerprint if result.pointer else None
            ),
        }, sort_keys=True))
        return 0
    current = rollback(
        root=ROOT,
        legacy_root=LEGACY_ROOT,
        expected_pointer_fingerprint=_current_pointer_fingerprint(),
        apply=False,
    )
    pointer = read_dashboard_snapshot_pointer(ROOT)
    assert pointer is not None
    print(json.dumps({
        "status": "rollback_dry_run_ready",
        "approved_active_pointer_fingerprint": pointer.pointer_content_fingerprint,
        "rollback_release_id": current.manifest.release_id,
        "rollback_reference": current.reference.model_dump(mode="json"),
        "production_writes": 0,
    }, sort_keys=True))
    return 0


def _current_pointer_fingerprint() -> str:
    pointer = read_dashboard_snapshot_pointer(ROOT)
    if pointer is None:
        raise DashboardSnapshotPublicationError("snapshot pointer does not exist")
    return pointer.pointer_content_fingerprint


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DashboardSnapshotPublicationError as exc:
        print(str(exc), file=__import__("sys").stderr)
        raise SystemExit(1)
