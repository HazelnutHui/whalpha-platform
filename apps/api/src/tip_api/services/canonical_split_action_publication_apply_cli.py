"""Explicit CLI for one exact canonical split-action publication Apply."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tip_api.services.canonical_split_action_publication_apply import (
    apply_approved_canonical_split_action_publication_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply one exact canonical split-action publication plan."
    )
    parser.add_argument("--plan-path", required=True, type=Path)
    parser.add_argument("--approved-plan-sha256", required=True)
    parser.add_argument("--expected-plan-logical-fingerprint", required=True)
    parser.add_argument("--expected-current-state-fingerprint", required=True)
    parser.add_argument("--data-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = apply_approved_canonical_split_action_publication_plan(
            plan_path=args.plan_path,
            approved_plan_sha256=args.approved_plan_sha256,
            expected_plan_logical_fingerprint=(
                args.expected_plan_logical_fingerprint
            ),
            expected_current_state_fingerprint=(
                args.expected_current_state_fingerprint
            ),
            data_root=args.data_root,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "canonical_split_action_apply_rejected",
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
