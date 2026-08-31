"""Exact-authorization CLI for the bounded Massive entitlement probe."""

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
from tip_api.providers.massive.historical_entitlement_probe import (
    probe_massive_historical_entitlements,
    required_probe_acknowledgement,
)
from tip_api.providers.massive.transport import MassiveUrllibTransport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-date", required=True, type=date.fromisoformat)
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--acknowledgement")
    args = parser.parse_args(argv)
    if args.review == bool(args.acknowledgement):
        parser.error("choose exactly one of --review or --acknowledgement")
    try:
        revision = _clean_revision()
        required = required_probe_acknowledgement(
            session_date=args.session_date, revision=revision
        )
        if args.review:
            print(f"revision={revision}")
            print(f"session_date={args.session_date.isoformat()}")
            print("maximum_request_count=4")
            print("response_body_retained=false")
            print("data_write_count=0")
            print(f"required_acknowledgement={required}")
            return 0
        if args.acknowledgement != required:
            print("error=authorization-mismatch", file=sys.stderr)
            return 2
        config = load_massive_provider_config_from_file()
        result = probe_massive_historical_entitlements(
            config=config,
            transport=MassiveUrllibTransport(),
            session_date=args.session_date,
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
