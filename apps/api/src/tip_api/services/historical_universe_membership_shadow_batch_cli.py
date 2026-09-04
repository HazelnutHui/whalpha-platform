"""Network-disabled CLI for a bounded historical membership shadow batch."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from tip_api.services.historical_universe_membership_shadow_batch import (
    run_historical_universe_membership_shadow_batch,
)
from tip_api.services.historical_universe_membership_shadow_cli import (
    _network_disabled,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build up to five adjacent membership shadows into /tmp."
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--session-package",
        action="append",
        required=True,
        help="Explicit SESSION_DATE=IDENTITY_PACKAGE_PATH mapping; repeat per date.",
    )
    parser.add_argument("--catalog-as-of-date", type=date.fromisoformat, required=True)
    parser.add_argument("--evaluated-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        package_paths = _parse_session_packages(args.session_package)
    except ValueError as exc:
        parser.error(str(exc))

    with _network_disabled():
        result = run_historical_universe_membership_shadow_batch(
            data_root=args.data_root,
            package_paths=package_paths,
            catalog_as_of_date=args.catalog_as_of_date,
            evaluated_at=args.evaluated_at,
            output_root=args.output_root,
        )
    print(json.dumps(result.as_dict(), sort_keys=True))
    return 0


def _parse_session_packages(values: list[str]) -> dict[date, Path]:
    result: dict[date, Path] = {}
    for value in values:
        raw_session, separator, raw_path = value.partition("=")
        if not separator or not raw_session or not raw_path:
            raise ValueError("--session-package must use SESSION_DATE=PATH")
        try:
            session = date.fromisoformat(raw_session)
        except ValueError as exc:
            raise ValueError("--session-package contains an invalid date") from exc
        if session in result:
            raise ValueError("--session-package contains a duplicate session")
        result[session] = Path(raw_path)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
