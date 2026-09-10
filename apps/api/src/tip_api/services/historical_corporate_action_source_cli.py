"""CLI for resumable tmp-only Massive corporate-action source acquisition."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
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
from tip_api.services.historical_corporate_action_source import (
    CONTRACT_VERSION,
    CorporateActionSourceArtifactV1,
    CorporateActionSourceKind,
    HistoricalCorporateActionSourceError,
    fetch_historical_corporate_action_source_package,
)
from tip_api.providers.massive.instrument_master_snapshot import (
    FixedIntervalRateLimiter,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kind",
        required=True,
        choices=tuple(item.value for item in CorporateActionSourceKind),
    )
    parser.add_argument("--start-date", required=True, type=date.fromisoformat)
    parser.add_argument("--end-date", required=True, type=date.fromisoformat)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument(
        "--request-interval-seconds", type=Decimal, default=Decimal("0.25")
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None

    def progress(
        artifact: CorporateActionSourceArtifactV1,
        record_count: int,
        package_bytes: int,
    ) -> None:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "corporate_action_source_checkpoint",
                    "implementation_revision": revision,
                    "action_kind": args.kind,
                    "page_count": artifact.sequence,
                    "record_count": record_count,
                    "package_bytes": package_bytes,
                    "last_page_row_count": artifact.row_count,
                    "last_page_sha256": artifact.physical_sha256,
                    "canonical_data_write_count": 0,
                    "adjustment_ledger_write_count": 0,
                    "publication_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )

    try:
        revision = _clean_revision()
        result = fetch_historical_corporate_action_source_package(
            config=load_massive_provider_config_from_file(),
            transport=MassiveUrllibTransport(),
            action_kind=CorporateActionSourceKind(args.kind),
            start_date=args.start_date,
            end_date=args.end_date,
            package_path=args.package,
            rate_limiter=FixedIntervalRateLimiter(
                interval_seconds=args.request_interval_seconds
            ),
            progress=progress,
        )
    except (
        HistoricalCorporateActionSourceError,
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
                    "record_type": "corporate_action_source_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "action_kind": args.kind,
                    "error_type": type(exc).__name__,
                    "safe_resume_requires_formal_checkpoint_reread": True,
                    "automatic_retry": False,
                    "canonical_data_write_count": 0,
                    "adjustment_ledger_write_count": 0,
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
                "record_type": "corporate_action_source_completion",
                "status": result.status,
                "implementation_revision": revision,
                "action_kind": manifest.action_kind.value,
                "start_date": manifest.start_date.isoformat(),
                "end_date": manifest.end_date.isoformat(),
                "request_count": manifest.request_count,
                "record_count": manifest.record_count,
                "package_bytes": manifest.package_bytes,
                "invalid_effective_date_count": (
                    manifest.invalid_effective_date_count
                ),
                "duplicate_source_action_id_count": (
                    manifest.duplicate_source_action_id_count
                ),
                "unexpected_field_counts": manifest.unexpected_field_counts,
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "pagination_complete": manifest.pagination_complete,
                "research_eligibility": manifest.research_eligibility,
                "canonical_data_write_count": 0,
                "adjustment_ledger_write_count": 0,
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
        raise HistoricalCorporateActionSourceError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
