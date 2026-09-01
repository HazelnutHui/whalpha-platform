"""Exact-authorization CLI for the inactive-security lifecycle probe."""

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
    MAXIMUM_REQUEST_COUNT,
    PAGE_LIMIT,
    probe_massive_historical_lifecycle_coverage,
    required_lifecycle_probe_acknowledgement,
)
from tip_api.providers.massive.transport import MassiveUrllibTransport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor-date", required=True, type=date.fromisoformat)
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--acknowledgement")
    args = parser.parse_args(argv)
    if args.review == bool(args.acknowledgement):
        parser.error("choose exactly one of --review or --acknowledgement")
    try:
        revision = _clean_revision()
        required = required_lifecycle_probe_acknowledgement(
            anchor_date=args.anchor_date, revision=revision
        )
        if args.review:
            print(f"revision={revision}")
            print(f"anchor_date={args.anchor_date.isoformat()}")
            print(f"maximum_request_count={MAXIMUM_REQUEST_COUNT}")
            print(f"page_limit={PAGE_LIMIT}")
            print("response_body_retained=false")
            print("data_write_count=0")
            print(f"required_acknowledgement={required}")
            return 0
        if args.acknowledgement != required:
            print("error=authorization-mismatch", file=sys.stderr)
            return 2
        result = probe_massive_historical_lifecycle_coverage(
            config=load_massive_provider_config_from_file(),
            transport=MassiveUrllibTransport(),
            anchor_date=args.anchor_date,
            before_request=lambda index: time.sleep(15) if index else None,
        )
    except (MassiveCredentialFileError, RuntimeError, ValueError) as exc:
        print(f"error={type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")))
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


if __name__ == "__main__":
    raise SystemExit(main())
