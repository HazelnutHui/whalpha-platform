"""Network-disabled CLI for normalized historical Identity source custody."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from tip_api.services.historical_identity_rebuild_profile_map import (
    read_historical_identity_rebuild_profile_map,
)
from tip_api.services.historical_identity_source_custody import (
    run_historical_identity_source_custody_batch,
)
from tip_api.services.historical_universe_membership_shadow_cli import (
    _network_disabled,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize a bounded batch of profile-bound Identity source packages "
            "below an owner-only /tmp root."
        )
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--profile-map", type=Path, required=True)
    parser.add_argument(
        "--package-root",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--materialized-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--maximum-sessions", type=int, default=20)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--session", type=date.fromisoformat, action="append")
    args = parser.parse_args(argv)

    with _network_disabled():
        profile_map = read_historical_identity_rebuild_profile_map(args.profile_map)
        result = run_historical_identity_source_custody_batch(
            data_root=args.data_root,
            package_roots=tuple(args.package_root),
            output_root=args.output_root,
            profile_map=profile_map,
            materialized_at=args.materialized_at,
            maximum_sessions=args.maximum_sessions,
            workers=args.workers,
            sessions=None if args.session is None else tuple(args.session),
        )
    print(
        json.dumps(
            {
                "contract_version": result.contract_version,
                "worker_count": result.worker_count,
                "maximum_sessions": result.maximum_sessions,
                "bound_session_count": result.bound_session_count,
                "completed_before_count": result.completed_before_count,
                "selected_session_count": result.selected_session_count,
                "completed_after_count": result.completed_after_count,
                "remaining_session_count": result.remaining_session_count,
                "status": result.status,
                "published_session_count": sum(
                    item.status == "published" for item in result.items
                ),
                "already_present_session_count": sum(
                    item.status == "already_present" for item in result.items
                ),
                "record_count": sum(item.record_count for item in result.items),
                "source_response_bytes": sum(
                    item.source_response_bytes for item in result.items
                ),
                "normalized_parquet_bytes": sum(
                    item.normalized_parquet_bytes for item in result.items
                ),
                "external_request_count": result.external_request_count,
                "canonical_data_write_count": result.canonical_data_write_count,
                "universe_membership_write_count": (
                    result.universe_membership_write_count
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
