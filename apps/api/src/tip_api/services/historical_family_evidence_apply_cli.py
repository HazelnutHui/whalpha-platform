"""Explicit offline CLI for one approved two-family evidence Apply."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tip_api.services.historical_family_evidence_apply import (
    apply_approved_current_historical_family_evidence_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Apply one exact current EOD/Identity family-evidence plan, or "
            "verify and complete its ordered-prefix recovery state."
        )
    )
    parser.add_argument("--plan-path", type=Path, required=True)
    parser.add_argument("--approved-plan-sha256", required=True)
    parser.add_argument("--expected-plan-logical-fingerprint", required=True)
    parser.add_argument("--expected-family-set-fingerprint", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--verify-then-complete", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = apply_approved_current_historical_family_evidence_plan(
            plan_path=args.plan_path,
            approved_plan_sha256=args.approved_plan_sha256,
            expected_plan_logical_fingerprint=(
                args.expected_plan_logical_fingerprint
            ),
            expected_family_set_fingerprint=(
                args.expected_family_set_fingerprint
            ),
            data_root=args.data_root,
            verify_then_complete=args.verify_then_complete,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "historical_family_evidence_apply_rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "overwritten_partition_count": 0,
                    "deleted_partition_count": 0,
                    "historical_coverage_authorized": False,
                    "research_development_authorized": False,
                    "research_performance_authorized": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1

    print(
        json.dumps(
            asdict(result),
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
