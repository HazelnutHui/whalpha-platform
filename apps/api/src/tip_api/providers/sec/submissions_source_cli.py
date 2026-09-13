"""CLI for bounded SEC Submissions bulk-source acquisition."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from tip_api.providers.sec.companyfacts_source import (
    SecCompanyfactsChunkV1,
    SecCompanyfactsFixedIntervalLimiter,
    SecCompanyfactsSourceError,
)
from tip_api.providers.sec.credential import (
    SecCredentialFileError,
    load_sec_provider_config_from_file,
)
from tip_api.providers.sec.submissions_source import (
    CONTRACT_VERSION,
    acquire_sec_submissions_source_package,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--custody-root", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None

    def progress(
        chunk: SecCompanyfactsChunkV1,
        committed_bytes: int,
        total_bytes: int,
    ) -> None:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "sec_submissions_chunk_checkpoint",
                    "implementation_revision": revision,
                    "chunk_sequence": chunk.sequence,
                    "committed_bytes": committed_bytes,
                    "total_bytes": total_bytes,
                    "canonical_data_write_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )

    try:
        revision = _clean_revision()
        config = load_sec_provider_config_from_file()
        result = acquire_sec_submissions_source_package(
            config=config,
            package_path=args.package,
            approved_custody_root=args.custody_root,
            rate_limiter=SecCompanyfactsFixedIntervalLimiter(
                requests_per_second=float(config.max_requests_per_second)
            ),
            progress=progress,
        )
    except (
        SecCompanyfactsSourceError,
        SecCredentialFileError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "safe_resume_requires_formal_checkpoint_reread": True,
                    "credential_material_retained": False,
                    "canonical_data_write_count": 0,
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
                "record_type": "sec_submissions_source_completion",
                "status": result.status,
                "implementation_revision": revision,
                "source_snapshot_date": manifest.remote.last_modified.date().isoformat(),
                "archive_bytes": manifest.archive_bytes,
                "archive_sha256": manifest.archive_sha256,
                "member_count": manifest.member_count,
                "total_uncompressed_bytes": manifest.total_uncompressed_bytes,
                "request_count": manifest.request_count,
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "member_payload_validation_status": (
                    manifest.member_payload_validation_status
                ),
                "credential_material_retained": False,
                "canonical_data_write_count": 0,
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
        raise SecCompanyfactsSourceError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
