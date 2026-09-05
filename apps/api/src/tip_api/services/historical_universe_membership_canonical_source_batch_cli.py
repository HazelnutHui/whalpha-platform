"""Network-disabled CLI for canonical-source historical membership shadows."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from tip_api.services.historical_universe_membership_shadow_batch import (
    run_historical_universe_membership_canonical_source_batch,
)
from tip_api.services.historical_universe_membership_shadow_cli import (
    _network_disabled,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build up to five adjacent membership shadows from canonical "
            "normalized Identity sources into /tmp."
        )
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--session-date",
        action="append",
        type=date.fromisoformat,
        required=True,
        help="XNYS session date; repeat for up to five adjacent sessions.",
    )
    parser.add_argument("--catalog-as-of-date", type=date.fromisoformat, required=True)
    parser.add_argument("--evaluated-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)

    with _network_disabled():
        result = run_historical_universe_membership_canonical_source_batch(
            data_root=args.data_root,
            sessions=tuple(args.session_date),
            catalog_as_of_date=args.catalog_as_of_date,
            evaluated_at=args.evaluated_at,
            output_root=args.output_root,
        )
    print(json.dumps(result.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
