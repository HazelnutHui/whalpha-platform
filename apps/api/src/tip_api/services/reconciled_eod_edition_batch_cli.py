"""Operator CLI for one approved-input Reconciled EOD construction batch."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from tip_api.services.reconciled_eod_edition_batch import (
    run_reconciled_eod_edition_batch,
)
from tip_api.services.reconciled_eod_source_coverage import (
    read_reconciled_eod_source_coverage,
    resolve_reconciled_eod_batch_sources,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build one bounded batch of Reconciled EOD candidate sessions",
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--coverage-path", type=Path, required=True)
    parser.add_argument("--coverage-file-sha256", required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--edition-id", required=True)
    parser.add_argument("--implementation-revision", required=True)
    parser.add_argument("--created-at", type=datetime.fromisoformat, required=True)
    parser.add_argument(
        "--session",
        type=date.fromisoformat,
        action="append",
        required=True,
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("candidate construction requires --execute")
    evidence = read_reconciled_eod_source_coverage(
        path=args.coverage_path,
        expected_file_sha256=args.coverage_file_sha256,
    )
    session_dates = tuple(args.session)
    sources = resolve_reconciled_eod_batch_sources(
        coverage=evidence.coverage,
        data_root=args.data_root,
        session_dates=session_dates,
    )
    result = run_reconciled_eod_edition_batch(
        data_root=args.data_root,
        candidate_root=args.candidate_root,
        edition_id=args.edition_id,
        implementation_revision=args.implementation_revision,
        sources=sources,
        workers=args.workers,
        created_at=args.created_at,
    )
    print(
        json.dumps(
            {
                "status": result.status,
                "edition_id": result.edition_id,
                "implementation_revision": result.implementation_revision,
                "requested_session_count": result.requested_session_count,
                "worker_count": result.worker_count,
                "published_session_count": result.published_session_count,
                "reused_session_count": result.reused_session_count,
                "failed_session_count": result.failed_session_count,
                "record_count": result.record_count,
                "added_record_count": result.added_record_count,
                "absent_record_count": result.absent_record_count,
                "external_request_count": result.external_request_count,
                "canonical_data_write_count": result.canonical_data_write_count,
                "candidate_session_write_count": (
                    result.candidate_session_write_count
                ),
                "interval_manifest_write_count": (
                    result.interval_manifest_write_count
                ),
                "candidate_authority": result.candidate_authority,
                "production_authority": result.production_authority,
                "research_performance_authorized": (
                    result.research_performance_authorized
                ),
                "sessions": [
                    {
                        "session_date": item.session_date,
                        "status": item.status,
                        "failure_code": item.failure_code,
                        "absent_record_count": item.absent_record_count,
                        "manifest_fingerprint": item.manifest_fingerprint,
                    }
                    for item in result.sessions
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
