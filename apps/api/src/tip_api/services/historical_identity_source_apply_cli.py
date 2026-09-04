"""Explicit CLI for one approved historical Identity source Apply or recovery."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tip_api.services.historical_identity_source_apply import (
    apply_approved_historical_identity_source_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Apply one exact historical Identity source plan, or verify and "
            "complete an interrupted invocation."
        )
    )
    parser.add_argument("--plan-path", type=Path, required=True)
    parser.add_argument("--approved-plan-sha256", required=True)
    parser.add_argument("--expected-plan-logical-fingerprint", required=True)
    parser.add_argument("--expected-current-state-fingerprint", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--verify-then-complete", action="store_true")
    parser.add_argument("--formal-read-workers", type=int, default=4)
    args = parser.parse_args(argv)

    result = apply_approved_historical_identity_source_plan(
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
        formal_read_workers=args.formal_read_workers,
    )
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
