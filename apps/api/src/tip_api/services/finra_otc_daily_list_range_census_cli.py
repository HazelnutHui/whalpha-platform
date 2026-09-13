"""Read-only CLI for the complete FINRA OTC source range."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from tip_api.services.finra_otc_daily_list_range_census import (
    FinraOtcDailyListRangeCensusError,
    census_finra_otc_daily_list_range,
    read_sealed_finra_otc_daily_list_range_census,
    seal_finra_otc_daily_list_range_census,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--custody-root", required=True, type=Path)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = census_finra_otc_daily_list_range(
            custody_root=args.custody_root,
            range_start=args.start,
            range_end=args.end,
        )
        if args.seal:
            seal_finra_otc_daily_list_range_census(
                custody_root=args.custody_root,
                census=result,
            )
            result = read_sealed_finra_otc_daily_list_range_census(
                custody_root=args.custody_root,
                range_start=args.start,
                range_end=args.end,
            )
    except (FinraOtcDailyListRangeCensusError, OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {"status": "stopped", "error_type": type(exc).__name__},
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
