"""Explicit CLI for one approved corporate-action source Apply."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tip_api.services.historical_corporate_action_source_apply import (
    apply_approved_corporate_action_source_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Apply one exact corporate-action source plan, or verify and "
            "complete an interrupted physical-first/marker-last invocation."
        )
    )
    parser.add_argument("--plan-path", type=Path, required=True)
    parser.add_argument("--approved-plan-sha256", required=True)
    parser.add_argument("--expected-plan-logical-fingerprint", required=True)
    parser.add_argument("--expected-current-state-fingerprint", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--verify-then-complete", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = apply_approved_corporate_action_source_plan(
            plan_path=args.plan_path,
            approved_plan_sha256=args.approved_plan_sha256,
            expected_plan_logical_fingerprint=(
                args.expected_plan_logical_fingerprint
            ),
            expected_current_state_fingerprint=(
                args.expected_current_state_fingerprint
            ),
            data_root=args.data_root,
            verify_then_complete=args.verify_then_complete,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "corporate_action_source_apply_rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(asdict(result), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
