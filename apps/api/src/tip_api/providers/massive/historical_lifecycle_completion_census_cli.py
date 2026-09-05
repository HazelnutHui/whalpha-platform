"""Bounded aggregate-only inactive lifecycle pagination completion census."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import date

from tip_api.providers.massive.credential import (
    MassiveCredentialFileError,
    load_massive_provider_config_from_file,
)
from tip_api.providers.massive.historical_lifecycle_probe import (
    COMPLETION_CENSUS_MAXIMUM_REQUEST_COUNT,
    COMPLETION_CENSUS_MAXIMUM_RESULT_COUNT,
    PAGE_LIMIT,
    census_complete_massive_historical_lifecycle_pagination,
)
from tip_api.providers.massive.transport import MassiveUrllibTransport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor-date", required=True, type=date.fromisoformat)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    try:
        if args.anchor_date >= date.today():
            raise ValueError("anchor date must be historical")
        revision = _clean_revision()
        result = census_complete_massive_historical_lifecycle_pagination(
            config=load_massive_provider_config_from_file(),
            transport=MassiveUrllibTransport(),
            anchor_date=args.anchor_date,
            before_request=lambda index: time.sleep(15) if index else None,
        )
    except (MassiveCredentialFileError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "error_type": type(exc).__name__,
                    "response_body_retained": False,
                    "data_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    payload = result.as_dict()
    payload.update(
        {
            "implementation_revision": revision,
            "maximum_request_count": COMPLETION_CENSUS_MAXIMUM_REQUEST_COUNT,
            "maximum_result_count": COMPLETION_CENSUS_MAXIMUM_RESULT_COUNT,
            "page_limit": PAGE_LIMIT,
        }
    )
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


def _clean_revision() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise RuntimeError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
