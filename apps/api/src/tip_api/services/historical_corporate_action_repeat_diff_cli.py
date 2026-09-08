"""CLI for a disconnected corporate-action source repeat diff."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from tip_api.services.historical_corporate_action_repeat_diff import (
    CONTRACT_VERSION,
    HistoricalCorporateActionRepeatDiffError,
    build_historical_corporate_action_repeat_diff,
)
from tip_api.services.historical_corporate_action_source import (
    CorporateActionSourceKind,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kind",
        required=True,
        choices=tuple(item.value for item in CorporateActionSourceKind),
    )
    parser.add_argument("--start-date", required=True, type=date.fromisoformat)
    parser.add_argument("--end-date", required=True, type=date.fromisoformat)
    parser.add_argument("--baseline-package", required=True, type=Path)
    parser.add_argument("--repeat-package", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument(
        "--compared-at",
        required=True,
        type=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")),
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None
    try:
        revision = _clean_revision()
        result = build_historical_corporate_action_repeat_diff(
            baseline_package_path=args.baseline_package,
            repeat_package_path=args.repeat_package,
            output_root=args.output_root,
            action_kind=CorporateActionSourceKind(args.kind),
            start_date=args.start_date,
            end_date=args.end_date,
            compared_at=args.compared_at,
        )
    except (
        HistoricalCorporateActionRepeatDiffError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        del exc
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "corporate_action_source_repeat_diff_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "action_kind": args.kind,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "adjustment_ledger_write_count": 0,
                    "analytics_execution_count": 0,
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
                "contract_version": CONTRACT_VERSION,
                "record_type": "corporate_action_source_repeat_diff_completion",
                "status": result.status,
                "implementation_revision": revision,
                "action_kind": manifest.action_kind.value,
                "start_date": manifest.start_date.isoformat(),
                "end_date": manifest.end_date.isoformat(),
                "baseline_record_count": manifest.baseline_record_count,
                "repeat_record_count": manifest.repeat_record_count,
                "unchanged_record_count": manifest.unchanged_record_count,
                "changed_record_count": manifest.changed_record_count,
                "added_record_count": manifest.added_record_count,
                "removed_record_count": manifest.removed_record_count,
                "changed_field_counts": manifest.changed_field_counts,
                "effective_date_changed_record_count": (
                    manifest.effective_date_changed_record_count
                ),
                "provider_ticker_changed_record_count": (
                    manifest.provider_ticker_changed_record_count
                ),
                "pagination_shape_changed": manifest.pagination_shape_changed,
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "point_in_time_eligibility": manifest.point_in_time_eligibility,
                "external_request_count": 0,
                "canonical_data_write_count": 0,
                "adjustment_ledger_write_count": 0,
                "analytics_execution_count": 0,
                "publication_count": 0,
                "deployment_count": 0,
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
        raise HistoricalCorporateActionRepeatDiffError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
