"""CLI for one bounded official FINRA OTC Daily List source partition."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from tip_api.services.finra_otc_daily_list_source import (
    CONTRACT_VERSION,
    FinraOtcDailyListSourceArtifactV1,
    FinraOtcDailyListSourceError,
    acquire_finra_otc_daily_list_source_package,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--custody-root", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None

    def progress(
        artifact: FinraOtcDailyListSourceArtifactV1,
        record_count: int,
        package_bytes: int,
    ) -> None:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "finra_otc_daily_list_checkpoint",
                    "implementation_revision": revision,
                    "page_count": artifact.sequence,
                    "record_count": record_count,
                    "package_bytes": package_bytes,
                    "last_page_sha256": artifact.physical_sha256,
                    "canonical_data_write_count": 0,
                    "publication_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )

    try:
        revision = _clean_revision()
        result = acquire_finra_otc_daily_list_source_package(
            partition_start=args.start,
            partition_end=args.end,
            package_path=args.package,
            approved_custody_root=args.custody_root,
            progress=progress,
        )
    except (FinraOtcDailyListSourceError, OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "finra_otc_daily_list_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "safe_resume_requires_formal_checkpoint_reread": True,
                    "automatic_retry": False,
                    "canonical_data_write_count": 0,
                    "analytics_execution_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    manifest = result.manifest
    print(
        json.dumps(
            {
                "contract_version": CONTRACT_VERSION,
                "record_type": "finra_otc_daily_list_completion",
                "status": result.status,
                "implementation_revision": revision,
                "partition_start": manifest.partition_start.isoformat(),
                "partition_end": manifest.partition_end.isoformat(),
                "request_count": manifest.request_count,
                "record_count": manifest.record_count,
                "duplicate_source_record_count": manifest.duplicate_source_record_count,
                "event_code_counts": manifest.event_code_counts,
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "research_eligibility": manifest.research_eligibility,
                "canonical_data_write_count": 0,
                "analytics_execution_count": 0,
                "publication_count": 0,
                "deployment_count": 0,
            },
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
        raise FinraOtcDailyListSourceError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
