"""CLI for the network-free FINRA/Massive candidate corroboration census."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from tip_api.services.finra_massive_action_cross_source_census import (
    FinraMassiveActionCrossSourceCensusError,
    census_finra_massive_action_sources,
    read_sealed_finra_massive_action_cross_source_census,
    seal_finra_massive_action_cross_source_census,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--finra-root", required=True, type=Path)
    parser.add_argument("--massive-root", required=True, type=Path)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)
    try:
        result = census_finra_massive_action_sources(
            finra_custody_root=args.finra_root,
            massive_custody_root=args.massive_root,
            range_start=args.start,
            range_end=args.end,
        )
        if args.output_root is not None:
            seal_finra_massive_action_cross_source_census(
                output_root=args.output_root, census=result
            )
            result = read_sealed_finra_massive_action_cross_source_census(
                output_root=args.output_root,
                range_start=args.start,
                range_end=args.end,
            )
    except (FinraMassiveActionCrossSourceCensusError, OSError, RuntimeError, ValueError) as exc:
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
