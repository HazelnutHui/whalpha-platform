"""Network-prohibited CLI for prospective daily Membership preparation."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from tip_api.services.daily_universe_membership_continuation import (
    prepare_daily_universe_membership_candidate,
)
from tip_api.services.universe_membership_knowledge_time_cli import (
    _offline_socket_guard,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build or reuse one prospective daily Membership candidate and "
            "classify its next-open eligibility without canonical writes."
        )
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--session-date", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--catalog-as-of-date",
        required=True,
        type=date.fromisoformat,
    )
    parser.add_argument("--evaluated-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--assessed-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--candidate-root", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        with _offline_socket_guard():
            result = prepare_daily_universe_membership_candidate(
                data_root=args.data_root,
                session_date=args.session_date,
                catalog_as_of_date=args.catalog_as_of_date,
                evaluated_at=args.evaluated_at,
                assessed_at=args.assessed_at,
                candidate_root=args.candidate_root,
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "daily_membership_continuation_rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "publication_authorized": False,
                    "scheduler_enabled": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
