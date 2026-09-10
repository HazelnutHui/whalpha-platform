"""CLI for the disconnected, tmp-only inactive-lifecycle resolution shadow."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    MANIFEST_CONTRACT_VERSION,
)
from tip_api.services.historical_inactive_lifecycle_resolution_shadow import (
    HistoricalInactiveLifecycleResolutionShadowError,
    build_historical_inactive_lifecycle_resolution_shadow,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a network-disabled inactive-lifecycle resolution shadow."
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--source-package", required=True, type=Path)
    parser.add_argument("--source-custody-root", type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--anchor-date", required=True, type=date.fromisoformat)
    parser.add_argument("--materialized-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")

    revision: str | None = None
    try:
        revision = _clean_revision()
        result = build_historical_inactive_lifecycle_resolution_shadow(
            data_root=args.data_root,
            source_package_path=args.source_package,
            output_root=args.output_root,
            anchor_date=args.anchor_date,
            materialized_at=args.materialized_at,
            source_custody_root=args.source_custody_root,
        )
    except (HistoricalInactiveLifecycleResolutionShadowError, OSError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "contract_version": MANIFEST_CONTRACT_VERSION,
                    "record_type": "inactive_lifecycle_resolution_shadow_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1

    manifest = result.manifest
    print(
        json.dumps(
            {
                "contract_version": manifest.contract_version,
                "record_type": "inactive_lifecycle_resolution_shadow_completion",
                "status": result.status,
                "implementation_revision": revision,
                "anchor_date": manifest.anchor_date.isoformat(),
                "source_record_count": manifest.source_package_record_count,
                "canonical_history_session_count": manifest.canonical_history_session_count,
                "canonical_history_unique_instrument_count": (
                    manifest.canonical_history_unique_instrument_count
                ),
                "disposition_counts": dict(manifest.disposition_counts),
                "resolution_status_counts": dict(manifest.resolution_status_counts),
                "reason_counts": dict(manifest.reason_counts),
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "external_request_count": 0,
                "canonical_data_write_count": 0,
                "analytics_execution_count": 0,
                "publication_count": 0,
                "deployment_count": 0,
                "scheduler_change_count": 0,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def _clean_revision() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "repository must be clean"
        )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
