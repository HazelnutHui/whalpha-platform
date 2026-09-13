"""CLI for bounded, resumable five-year research Membership continuation."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from tip_api.services.five_year_research_membership_continuation import (
    execute_five_year_research_membership_continuation,
    prepare_five_year_research_membership_continuation,
)
from tip_api.services.five_year_research_foundation_census import (
    RESEARCH_MEMBERSHIP_METHODOLOGIES,
    RESEARCH_MEMBERSHIP_METHODOLOGY,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or build missing rolling five-year research Membership "
            "sessions into owner-only /tmp custody."
        )
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--catalog-as-of-date", type=date.fromisoformat, required=True)
    parser.add_argument("--evaluated-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument(
        "--methodology-version",
        choices=RESEARCH_MEMBERSHIP_METHODOLOGIES,
        default=RESEARCH_MEMBERSHIP_METHODOLOGY,
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-limit", type=int)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    plan = prepare_five_year_research_membership_continuation(
        data_root=args.data_root,
        candidate_root=args.candidate_root,
        catalog_as_of_date=args.catalog_as_of_date,
        evaluated_at=args.evaluated_at,
        code_revision=args.code_revision,
        methodology_version=args.methodology_version,
    )
    print(
        json.dumps(
            {"event": "plan", **plan.model_dump(mode="json")},
            sort_keys=True,
            separators=(",", ":"),
        ),
        flush=True,
    )
    if not args.execute:
        return 0

    def progress(payload: dict[str, object]) -> None:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")), flush=True)

    result = execute_five_year_research_membership_continuation(
        plan,
        workers=args.workers,
        batch_limit=args.batch_limit,
        progress=progress,
    )
    print(
        json.dumps(
            {"event": "result", **result.model_dump(mode="json")},
            sort_keys=True,
            separators=(",", ":"),
        ),
        flush=True,
    )
    return 1 if result.failed_batch_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
