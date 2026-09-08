"""CLI for a canonical-source split-action candidate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from tip_api.services.canonical_split_action_candidate import (
    APPROVED_DATA_ROOT,
    CONTRACT_VERSION,
    CanonicalSplitActionCandidateError,
    build_canonical_source_split_action_candidate,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-publication", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--basis-session", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--calculated-at",
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
        result = build_canonical_source_split_action_candidate(
            data_root=APPROVED_DATA_ROOT,
            source_publication_path=args.source_publication,
            output_root=args.output_root,
            basis_session=args.basis_session,
            calculated_at=args.calculated_at,
            implementation_revision=revision,
        )
    except (
        CanonicalSplitActionCandidateError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "canonical_source_split_action_candidate_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "adjustment_ledger_write_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    candidate = result.candidate
    print(
        json.dumps(
            {
                "contract_version": CONTRACT_VERSION,
                "record_type": "canonical_source_split_action_candidate_completion",
                "status": result.status,
                "implementation_revision": revision,
                "basis_session": candidate.basis_session.isoformat(),
                "source_publication_logical_fingerprint": (
                    candidate.source_publication_logical_fingerprint
                ),
                "split_source_record_count": candidate.split_source_record_count,
                "resolved_active_split_source_record_count": (
                    candidate.resolved_active_split_source_record_count
                ),
                "quarantined_split_source_record_count": (
                    candidate.quarantined_split_source_record_count
                ),
                "resolved_event_group_count": candidate.resolved_event_group_count,
                "clear_event_group_count": candidate.clear_event_group_count,
                "quarantined_event_group_count": (
                    candidate.quarantined_event_group_count
                ),
                "possible_impact_instrument_count": (
                    candidate.possible_impact_instrument_count
                ),
                "file_sha256": result.file_sha256,
                "logical_fingerprint": candidate.logical_fingerprint,
                "external_request_count": 0,
                "canonical_data_write_count": 0,
                "adjustment_ledger_write_count": 0,
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
        raise CanonicalSplitActionCandidateError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
