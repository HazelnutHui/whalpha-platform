"""CLI for one finite continuous Historical Backfill execution."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from tip_api.providers.massive.credential import (
    MassiveCredentialFileError,
    load_massive_provider_config_from_file,
)
from tip_api.providers.massive.transport import MassiveUrllibTransport
from tip_api.services.historical_backfill_continuous_runner import (
    CONTRACT_VERSION,
    DEFAULT_BATCH_SIZE,
    HistoricalBackfillContinuousRunnerError,
    HistoricalBackfillContinuousStoppedError,
    run_historical_backfill_continuous,
)
from tip_api.services.historical_backfill_planner import DEFAULT_TARGET_SESSIONS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--target-session-count", type=int, default=DEFAULT_TARGET_SESSIONS
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required; review uses the separate plan command")
    revision: str | None = None

    def emit_checkpoint(batch_number, batch) -> None:
        payload = batch.as_dict()
        payload["record_type"] = "bounded_batch_checkpoint"
        payload["batch_number"] = batch_number
        payload["implementation_revision"] = revision
        print(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            flush=True,
        )

    try:
        revision = _clean_revision()
        result = run_historical_backfill_continuous(
            config=load_massive_provider_config_from_file(),
            transport=MassiveUrllibTransport(),
            data_root=args.data_root,
            package_root=args.package_root,
            batch_size=args.batch_size,
            target_session_count=args.target_session_count,
            on_batch_complete=emit_checkpoint,
        )
    except HistoricalBackfillContinuousStoppedError as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "continuous_stop",
                    "status": "stopped_transient_retries_exhausted",
                    "implementation_revision": revision,
                    "failed_session": exc.failed_session,
                    "failure_code": exc.failure_code,
                    "completed_batch_count": exc.completed_batch_count,
                    "completed_session_count": exc.completed_session_count,
                    "current_batch_completed_sessions": [
                        asdict(item)
                        for item in exc.current_batch_completed_sessions
                    ],
                    "external_request_count": exc.external_request_count,
                    "transient_retry_count": exc.transient_retry_count,
                    "transient_failure_count": exc.transient_failure_count,
                    "safe_resume_from_canonical": True,
                    "automatic_restart": False,
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
    except (
        HistoricalBackfillContinuousRunnerError,
        MassiveCredentialFileError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "continuous_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "automatic_restart": False,
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
    payload = result.as_dict()
    payload["record_type"] = "continuous_completion"
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
        raise HistoricalBackfillContinuousRunnerError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
