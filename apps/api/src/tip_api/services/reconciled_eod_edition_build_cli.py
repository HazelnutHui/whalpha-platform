"""CLI for resumable complete Reconciled EOD candidate construction."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from tip_api.persistence.parquet.reconciled_eod_edition import (
    ReconciledEodEditionPersistenceError,
)
from tip_api.services.reconciled_eod_edition_build import (
    CONTRACT_VERSION,
    ReconciledEodEditionBuildError,
    ReconciledEodEditionBuildStoppedError,
    run_reconciled_eod_edition_build,
)
from tip_api.services.reconciled_eod_source_coverage import (
    ReconciledEodSourceCoverageError,
    read_reconciled_eod_source_coverage,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and seal one complete Reconciled EOD candidate edition",
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--coverage-path", required=True, type=Path)
    parser.add_argument("--coverage-file-sha256", required=True)
    parser.add_argument("--candidate-root", required=True, type=Path)
    parser.add_argument("--edition-id", required=True)
    parser.add_argument("--created-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None

    def emit_progress(checkpoint: object) -> None:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "edition_build_checkpoint",
                    "implementation_revision": revision,
                    "checkpoint": asdict(checkpoint),
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "production_authority": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )

    try:
        revision = _clean_revision()
        coverage = read_reconciled_eod_source_coverage(
            path=args.coverage_path,
            expected_file_sha256=args.coverage_file_sha256,
        ).coverage
        result = run_reconciled_eod_edition_build(
            coverage=coverage,
            data_root=args.data_root,
            candidate_root=args.candidate_root,
            edition_id=args.edition_id,
            implementation_revision=revision,
            created_at=args.created_at,
            workers=args.workers,
            batch_size=args.batch_size,
            progress=emit_progress,
        )
    except ReconciledEodEditionBuildStoppedError as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "edition_build_stop",
                    "status": "stopped_with_failures",
                    "implementation_revision": revision,
                    "failed_sessions": exc.failed_sessions,
                    "checkpoint": asdict(exc.checkpoint),
                    "completed_batch_count": len(exc.completed_checkpoints),
                    "safe_resume_from_completed_sessions": True,
                    "automatic_restart": False,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "interval_manifest_write_count": 0,
                    "production_authority": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    except (
        ReconciledEodEditionBuildError,
        ReconciledEodEditionPersistenceError,
        ReconciledEodSourceCoverageError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "edition_build_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "automatic_restart": False,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "interval_manifest_write_count": 0,
                    "production_authority": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    payload = result.as_dict()
    payload["record_type"] = "edition_build_completion"
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


def _clean_revision() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise ReconciledEodEditionBuildError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
