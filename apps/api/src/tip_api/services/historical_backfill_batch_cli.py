"""CLI for one bounded resumable Historical Backfill batch."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from tip_api.providers.massive.credential import (
    MassiveCredentialFileError,
    load_massive_provider_config_from_file,
)
from tip_api.providers.massive.transport import MassiveUrllibTransport
from tip_api.services.historical_backfill_batch_runner import (
    CONTRACT_VERSION,
    HistoricalBackfillBatchRunnerError,
    HistoricalBackfillBatchStoppedError,
    run_historical_backfill_batch,
)
from tip_api.services.historical_backfill_planner import DEFAULT_TARGET_SESSIONS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--maximum-sessions", required=True, type=int)
    parser.add_argument(
        "--target-session-count", type=int, default=DEFAULT_TARGET_SESSIONS
    )
    parser.add_argument("--target-first-session", type=date.fromisoformat)
    parser.add_argument("--target-last-session", type=date.fromisoformat)
    parser.add_argument("--request-interval-seconds", type=Decimal)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required; review uses the separate plan command")
    try:
        revision = _clean_revision()
        result = run_historical_backfill_batch(
            config=load_massive_provider_config_from_file(),
            transport=MassiveUrllibTransport(),
            data_root=args.data_root,
            package_root=args.package_root,
            maximum_sessions=args.maximum_sessions,
            target_session_count=args.target_session_count,
            target_first_session=args.target_first_session,
            target_last_session=args.target_last_session,
            request_interval_seconds=args.request_interval_seconds,
        )
    except HistoricalBackfillBatchStoppedError as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "status": "stopped_transient_retries_exhausted",
                    "implementation_revision": revision,
                    "failed_session": exc.failed_session.isoformat(),
                    "failure_code": exc.failure_code,
                    "completed_session_count": len(exc.completed_sessions),
                    "completed_sessions": [
                        asdict(item) for item in exc.completed_sessions
                    ],
                    "external_request_count": exc.external_request_count,
                    "transient_retry_count": exc.transient_retry_count,
                    "transient_failure_count": exc.transient_failure_count,
                    "safe_resume_from_canonical": True,
                    "automatic_retry": False,
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
    except (MassiveCredentialFileError, OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "error_type": type(exc).__name__,
                    "automatic_retry": False,
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
        raise HistoricalBackfillBatchRunnerError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
