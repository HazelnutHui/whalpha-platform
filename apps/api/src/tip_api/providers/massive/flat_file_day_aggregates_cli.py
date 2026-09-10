"""Exact-authorization fetch CLI for one Massive Day Aggregates Flat File."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from tip_api.providers.massive.flat_file_day_aggregates import (
    MAXIMUM_COMPRESSED_BYTES,
    Boto3MassiveFlatFileTransport,
    MassiveFlatFileCredentialError,
    MassiveFlatFileError,
    day_aggregate_object_key,
    fetch_flat_file_day_aggregate_package,
    load_massive_flat_file_config_from_file,
    safe_flat_file_evidence,
    validate_flat_file_package_target,
)


CONTRACT_VERSION = "massive-flat-file-day-aggregate-fetch/1.0"


def required_acknowledgement(
    *,
    session_date: date,
    package_path: Path,
    revision: str,
) -> str:
    normalized_revision = revision.strip().lower()
    if len(normalized_revision) != 40 or any(
        item not in "0123456789abcdef" for item in normalized_revision
    ):
        raise ValueError("revision must be a full Git SHA")
    payload = {
        "contract_version": CONTRACT_VERSION,
        "maximum_compressed_bytes": MAXIMUM_COMPRESSED_BYTES,
        "object_key": day_aggregate_object_key(session_date),
        "package_path": str(package_path),
        "revision": normalized_revision,
        "session_date": session_date.isoformat(),
    }
    binding = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"I_AUTHORIZE_MASSIVE_FLAT_FILE_FETCH_{binding}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-date", required=True, type=date.fromisoformat)
    parser.add_argument("--package-path", required=True, type=Path)
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--acknowledgement")
    args = parser.parse_args(argv)
    if args.review == bool(args.acknowledgement):
        parser.error("choose exactly one of --review or --acknowledgement")
    try:
        revision = _clean_revision()
        required = required_acknowledgement(
            session_date=args.session_date,
            package_path=args.package_path,
            revision=revision,
        )
        validate_flat_file_package_target(
            package_path=args.package_path,
            session_date=args.session_date,
        )
        if args.review:
            print(f"revision={revision}")
            print(f"session_date={args.session_date.isoformat()}")
            print(f"object_key={day_aggregate_object_key(args.session_date)}")
            print("maximum_request_count=1")
            print(f"maximum_compressed_bytes={MAXIMUM_COMPRESSED_BYTES}")
            print(f"package_path={args.package_path}")
            print(f"required_acknowledgement={required}")
            return 0
        if args.acknowledgement != required:
            print("error=authorization-mismatch", file=sys.stderr)
            return 2
        config = load_massive_flat_file_config_from_file()
        manifest = fetch_flat_file_day_aggregate_package(
            config=config,
            transport=Boto3MassiveFlatFileTransport(config),
            session_date=args.session_date,
            package_path=args.package_path,
        )
    except (
        MassiveFlatFileCredentialError,
        MassiveFlatFileError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "error_type": type(exc).__name__,
                    "data_write_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {"status": "fetched", **safe_flat_file_evidence(manifest)},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def _clean_revision() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise MassiveFlatFileError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
