"""CLI for the first-strategy SEC primary-document acquisition plan."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.services.strong_leader_pullback_sec_document_plan import (
    CONTRACT_VERSION,
    StrongLeaderPullbackSecDocumentPlanError,
    build_strong_leader_pullback_sec_document_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", required=True, type=Path)
    parser.add_argument("--pilot-custody-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-custody-root", required=True, type=Path)
    parser.add_argument(
        "--planned-at",
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
        result = build_strong_leader_pullback_sec_document_plan(
            pilot_root=args.pilot,
            pilot_custody_root=args.pilot_custody_root,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            implementation_revision=revision,
            planned_at=args.planned_at,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "sec_document_plan_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "credential_read_count": 0,
                    "document_write_count": 0,
                    "canonical_data_write_count": 0,
                    "research_admission_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    plan = result.plan
    print(
        json.dumps(
            {
                "contract_version": plan.contract_version,
                "record_type": "sec_document_plan_completion",
                "status": result.status,
                "implementation_revision": revision,
                "planned_request_count": plan.planned_request_count,
                "batch_count": plan.batch_count,
                "plan_sha256": result.plan_sha256,
                "logical_fingerprint": plan.logical_fingerprint,
                "external_request_count": 0,
                "credential_read_count": 0,
                "document_write_count": 0,
                "canonical_data_write_count": 0,
                "research_admission_count": 0,
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
        raise StrongLeaderPullbackSecDocumentPlanError(
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
