"""CLI for coverage-bound Reconciled EOD source-package reacquisition."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from tip_api.providers.massive.credential import (
    MassiveCredentialFileError,
    load_massive_provider_config_from_file,
)
from tip_api.providers.massive.transport import MassiveUrllibTransport
from tip_api.services.reconciled_eod_source_coverage import (
    ReconciledEodSourceCoverageError,
    read_reconciled_eod_source_coverage,
)
from tip_api.services.reconciled_eod_source_reacquisition import (
    CONTRACT_VERSION,
    ReconciledEodSourceReacquisitionError,
    ReconciledEodSourceReacquisitionStoppedError,
    run_reconciled_eod_source_reacquisition,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reacquire exact missing Reconciled EOD source packages",
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--coverage-path", required=True, type=Path)
    parser.add_argument("--coverage-file-sha256", required=True)
    parser.add_argument(
        "--session-date",
        required=True,
        action="append",
        type=date.fromisoformat,
    )
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None

    def emit_progress(completed: int, total: int, item: object) -> None:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "source_reacquisition_checkpoint",
                    "implementation_revision": revision,
                    "completed_session_count": completed,
                    "requested_session_count": total,
                    "item": asdict(item),
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
        result = run_reconciled_eod_source_reacquisition(
            config=load_massive_provider_config_from_file(),
            transport=MassiveUrllibTransport(),
            data_root=args.data_root,
            package_root=args.package_root,
            coverage=coverage,
            session_dates=tuple(args.session_date),
            progress=emit_progress,
        )
    except ReconciledEodSourceReacquisitionStoppedError as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "source_reacquisition_stop",
                    "status": "stopped_transient_retries_exhausted",
                    "implementation_revision": revision,
                    "failed_session": exc.failed_session.isoformat(),
                    "failure_code": exc.failure_code,
                    "completed_session_count": len(exc.completed_items),
                    "completed_items": [
                        asdict(item) for item in exc.completed_items
                    ],
                    "provider_request_attempt_count": (
                        exc.provider_request_attempt_count
                    ),
                    "transient_retry_count": exc.transient_retry_count,
                    "transient_failure_count": exc.transient_failure_count,
                    "safe_resume_from_package_custody": True,
                    "automatic_restart": False,
                    "canonical_data_write_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                    "production_authority": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    except (
        ReconciledEodSourceCoverageError,
        ReconciledEodSourceReacquisitionError,
        MassiveCredentialFileError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "source_reacquisition_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "automatic_restart": False,
                    "canonical_data_write_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                    "production_authority": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    payload = result.as_dict()
    payload["record_type"] = "source_reacquisition_completion"
    payload["implementation_revision"] = revision
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
        raise ReconciledEodSourceReacquisitionError(
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
