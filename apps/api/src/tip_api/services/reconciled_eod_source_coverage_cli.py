"""Operator CLI for network-free Reconciled EOD source coverage."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from tip_api.services.reconciled_eod_source_coverage import (
    assess_reconciled_eod_source_coverage,
    write_reconciled_eod_source_coverage,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build one immutable Reconciled EOD source-coverage census",
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--first-session", type=date.fromisoformat, required=True)
    parser.add_argument("--last-session", type=date.fromisoformat, required=True)
    parser.add_argument("--created-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--coverage-path", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    coverage = assess_reconciled_eod_source_coverage(
        data_root=args.data_root,
        evaluation_first_session=args.first_session,
        evaluation_last_session=args.last_session,
        created_at=args.created_at,
        workers=args.workers,
    )
    evidence = write_reconciled_eod_source_coverage(
        coverage=coverage,
        path=args.coverage_path,
    )
    print(
        json.dumps(
            {
                "status": coverage.status,
                "coverage_path": str(evidence.path),
                "coverage_file_sha256": evidence.file_sha256,
                "logical_fingerprint": coverage.logical_fingerprint,
                "first_session": coverage.evaluation_first_session.isoformat(),
                "last_session": coverage.evaluation_last_session.isoformat(),
                "target_session_count": coverage.target_session_count,
                "retained_original_session_count": (
                    coverage.retained_original_session_count
                ),
                "later_reacquisition_session_count": (
                    coverage.later_reacquisition_session_count
                ),
                "missing_session_count": coverage.missing_session_count,
                "invalid_session_count": coverage.invalid_session_count,
                "conflict_session_count": coverage.conflict_session_count,
                "external_request_count": coverage.external_request_count,
                "canonical_data_write_count": coverage.canonical_data_write_count,
                "candidate_session_write_count": (
                    coverage.candidate_session_write_count
                ),
                "source_selection_authorized": (
                    coverage.source_selection_authorized
                ),
                "production_authority": coverage.production_authority,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
