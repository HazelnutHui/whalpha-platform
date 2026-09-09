"""Network-disabled CLI for one sparse split-adjustment candidate."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from tip_api.services.canonical_split_adjustment_candidate import (
    build_canonical_split_adjustment_candidate,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build one owner-only sparse split-adjustment candidate."
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--canonical-action-publication-root", required=True, type=Path)
    parser.add_argument("--eod-evidence-path", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--calculated-at", required=True, type=datetime.fromisoformat)
    args = parser.parse_args(argv)
    try:
        result = build_canonical_split_adjustment_candidate(
            data_root=args.data_root,
            canonical_action_publication_root=(
                args.canonical_action_publication_root
            ),
            eod_evidence_path=args.eod_evidence_path,
            output_root=args.output_root,
            source_revision=_clean_revision(),
            calculated_at=args.calculated_at,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "canonical_split_adjustment_candidate_rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    publication = result.publication.publication
    print(
        json.dumps(
            {
                "status": result.status,
                "output_root": str(result.output_root),
                "manifest_sha256": result.publication.manifest_sha256,
                "logical_fingerprint": publication.logical_fingerprint,
                "source_revision": publication.source_revision,
                "basis_session": publication.basis_session.isoformat(),
                "selected_instrument_count": publication.selected_instrument_count,
                "selected_eod_row_count": publication.selected_eod_row_count,
                "record_count": publication.record_count,
                "clear_record_count": publication.clear_record_count,
                "quarantined_record_count": publication.quarantined_record_count,
                "clear_instrument_count": publication.clear_instrument_count,
                "quarantined_instrument_count": (
                    publication.quarantined_instrument_count
                ),
                "adjustment_parquet_bytes": publication.adjustment_parquet_bytes,
                "absent_row_neutrality_authorized": (
                    publication.absent_row_neutrality_authorized
                ),
                "full_adjustment_coverage_authorized": (
                    publication.full_adjustment_coverage_authorized
                ),
                "historical_coverage_authorized": (
                    publication.historical_coverage_authorized
                ),
                "research_performance_authorized": (
                    publication.research_performance_authorized
                ),
                "external_request_count": 0,
                "canonical_data_write_count": 0,
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
        raise RuntimeError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
