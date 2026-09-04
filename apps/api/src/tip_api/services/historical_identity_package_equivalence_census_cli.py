"""Network-disabled CLI for the historical Identity equivalence census."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from tip_api.services.historical_identity_package_equivalence_census import (
    run_historical_identity_package_equivalence_census,
    write_historical_identity_package_equivalence_census_report,
)
from tip_api.services.historical_identity_rebuild_profile_map import (
    CURRENT_IDENTITY_REBUILD_PROFILE,
    PRE_ETV_IDENTITY_REBUILD_PROFILE,
)
from tip_api.services.historical_universe_membership_shadow_cli import (
    _network_disabled,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare retained Identity packages with canonical same-day snapshots."
        )
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--package-root",
        action="append",
        type=Path,
        required=True,
        help="Explicit non-overlapping package or package-container root below /tmp.",
    )
    parser.add_argument("--evaluated-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    parser.add_argument(
        "--sample-session",
        action="append",
        type=date.fromisoformat,
        help="Evaluate one to ten explicit canonical sessions instead of the full index.",
    )
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--rebuild-profile",
        choices=(
            CURRENT_IDENTITY_REBUILD_PROFILE,
            PRE_ETV_IDENTITY_REBUILD_PROFILE,
        ),
        default=CURRENT_IDENTITY_REBUILD_PROFILE,
    )
    args = parser.parse_args(argv)
    if args.progress_every < 1:
        parser.error("--progress-every must be positive")

    def progress(
        position: int,
        total: int,
        session: date,
        status: str,
    ) -> None:
        if position == total or position % args.progress_every == 0:
            print(
                json.dumps(
                    {
                        "completed_session_count": position,
                        "total_session_count": total,
                        "latest_session": session.isoformat(),
                        "latest_status": status,
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
                flush=True,
            )

    with _network_disabled():
        result = run_historical_identity_package_equivalence_census(
            data_root=args.data_root,
            package_roots=tuple(args.package_root),
            evaluated_at=args.evaluated_at,
            sample_sessions=(
                tuple(args.sample_session) if args.sample_session is not None else None
            ),
            rebuild_profile=args.rebuild_profile,
            workers=args.workers,
            progress=progress,
        )
        report_path = write_historical_identity_package_equivalence_census_report(
            report=result,
            report_path=args.report_path,
        )
    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "canonical_session_count": result.canonical_session_count,
                "evaluated_session_count": result.evaluated_session_count,
                "scope": result.scope,
                "rebuild_profile": result.rebuild_profile,
                "worker_count": result.worker_count,
                "discovered_identity_package_count": (
                    result.discovered_identity_package_count
                ),
                "exact_equivalent_session_count": (
                    result.exact_equivalent_session_count
                ),
                "duplicate_source_session_count": (
                    result.duplicate_source_session_count
                ),
                "status_counts": dict(result.status_counts),
                "external_request_count": result.external_request_count,
                "canonical_data_write_count": result.canonical_data_write_count,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
