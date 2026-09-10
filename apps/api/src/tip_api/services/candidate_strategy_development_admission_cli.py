"""CLI for the read-only Strong-Leader Pullback admission decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from tip_api.persistence.development_admission_decision import (
    write_development_admission_decision,
)
from tip_api.persistence.development_coverage_census import (
    REPORT_FILE,
    read_development_coverage_census,
)
from tip_api.services.candidate_strategy_development_admission import (
    decide_strong_leader_pullback_development_admission,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Formally reread one development census and freeze an outcome-blind "
            "owner-only admission decision below /tmp."
        )
    )
    parser.add_argument("--census-root", type=Path, required=True)
    parser.add_argument("--decision-revision", required=True)
    parser.add_argument("--decided-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        with _network_disabled():
            census = read_development_coverage_census(output_root=args.census_root)
            census_path = args.census_root / REPORT_FILE
            decision = decide_strong_leader_pullback_development_admission(
                census=census,
                census_physical_sha256=hashlib.sha256(
                    census_path.read_bytes()
                ).hexdigest(),
                decision_revision=args.decision_revision,
                decided_at=args.decided_at,
            )
            path = write_development_admission_decision(
                output_root=args.output_root,
                decision=decision,
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": (
                        "strong_leader_pullback_development_admission_rejected"
                    ),
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "completed",
                "decision_path": str(path),
                "logical_fingerprint": decision.logical_fingerprint,
                "decision_status": decision.decision_status,
                "raw_candidate_session_count": (
                    decision.raw_candidate_session_count
                ),
                "complete_cross_section_session_count": (
                    decision.complete_cross_section_session_count
                ),
                "blocker_codes": decision.blocker_codes,
                "development_authorized": decision.development_authorized,
                "external_request_count": decision.external_request_count,
                "canonical_data_write_count": decision.canonical_data_write_count,
                "production_write_count": decision.production_write_count,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


@contextmanager
def _network_disabled():
    original_socket = socket.socket

    def blocked_socket(*_args: object, **_kwargs: object):
        raise RuntimeError("network access is disabled for development admission")

    socket.socket = blocked_socket  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
