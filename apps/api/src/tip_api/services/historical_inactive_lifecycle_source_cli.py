"""CLI for resumable tmp-only inactive lifecycle source acquisition."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from tip_api.providers.massive.credential import (
    MassiveCredentialFileError,
    load_massive_provider_config_from_file,
)
from tip_api.providers.massive.transport import (
    MassiveTransportDataError,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
    MassiveUrllibTransport,
)
from tip_api.services.historical_inactive_lifecycle_source import (
    CONTRACT_VERSION,
    HistoricalInactiveLifecycleSourceError,
    InactiveLifecycleSourceArtifactV1,
    fetch_historical_inactive_lifecycle_source_package,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor-date", required=True, type=date.fromisoformat)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None

    def progress(
        artifact: InactiveLifecycleSourceArtifactV1,
        record_count: int,
        package_bytes: int,
    ) -> None:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "inactive_lifecycle_source_checkpoint",
                    "implementation_revision": revision,
                    "page_count": artifact.sequence,
                    "record_count": record_count,
                    "package_bytes": package_bytes,
                    "last_page_row_count": artifact.row_count,
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
        result = fetch_historical_inactive_lifecycle_source_package(
            config=load_massive_provider_config_from_file(),
            transport=MassiveUrllibTransport(),
            anchor_date=args.anchor_date,
            package_path=args.package,
            progress=progress,
        )
    except (
        HistoricalInactiveLifecycleSourceError,
        MassiveCredentialFileError,
        MassiveTransportDataError,
        MassiveTransportResponseError,
        MassiveTransportTimeoutError,
        MassiveTransportUnavailableError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "inactive_lifecycle_source_stop",
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
                "record_type": "inactive_lifecycle_source_completion",
                "status": result.status,
                "implementation_revision": revision,
                "anchor_date": manifest.anchor_date.isoformat(),
                "request_count": manifest.request_count,
                "record_count": manifest.record_count,
                "package_bytes": manifest.package_bytes,
                "duplicate_ticker_count": manifest.duplicate_ticker_count,
                "field_presence_counts": manifest.field_presence_counts,
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "pagination_complete": manifest.pagination_complete,
                "point_in_time_eligibility": manifest.point_in_time_eligibility,
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
        raise HistoricalInactiveLifecycleSourceError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
