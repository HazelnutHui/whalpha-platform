"""CLI for private dashboard snapshot exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tip_api.services.private_dashboard_snapshot import DashboardSnapshotError, build_private_dashboard_snapshot, validate_release_id

APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build private dashboard JSON snapshot from completed canonical datasets.")
    parser.add_argument("--data-root", type=Path, default=APPROVED_DATA_ROOT)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--release-id", default=None)
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[5]
    output_root = args.output_root or (repo_root / "build" / "private-dashboard")
    allowed_output_root = repo_root / "build" / "private-dashboard"

    if args.release_id is not None:
        validate_release_id(args.release_id)
    if args.data_root.resolve(strict=True) != APPROVED_DATA_ROOT:
        raise DashboardSnapshotError("data-root must be the approved production data root for this operational exporter")

    result = build_private_dashboard_snapshot(
        data_root=args.data_root,
        output_root=output_root,
        release_id=args.release_id,
        allowed_output_root=allowed_output_root,
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "release_id": result.release_id,
                "current_session_date": result.manifest.current_session_date,
                "previous_session_date": result.manifest.previous_session_date,
                "summary_file": result.manifest.summary_file,
                "mover_gainer_count": result.manifest.mover_gainer_count,
                "mover_loser_count": result.manifest.mover_loser_count,
                "liquidity_node_count": result.manifest.liquidity_node_count,
                "access_classification": result.manifest.access_classification,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
