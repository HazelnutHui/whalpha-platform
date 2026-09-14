"""CLI for one-document listed-consideration residual source custody."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from tip_api.providers.sec.credential import (
    SecCredentialFileError,
    load_sec_provider_config_from_file,
)
from tip_api.providers.sec.transport import SecTransportError
from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_source as source,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--plan-custody-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-custody-root", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None

    def progress(artifact: object) -> None:
        print(
            json.dumps(
                {
                    "contract_version": source.CONTRACT_VERSION,
                    "record_type": "residual_source_checkpoint",
                    "implementation_revision": revision,
                    "request_sequence": getattr(artifact, "request_sequence"),
                    "completed_document_count": 1,
                    "planned_document_count": 1,
                    "document_bytes": getattr(artifact, "byte_count"),
                    "document_sha256": getattr(artifact, "physical_sha256"),
                    "credential_material_retained": False,
                    "identity_assignment_count": 0,
                    "terminal_value_count": 0,
                    "canonical_data_write_count": 0,
                    "research_admission_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            flush=True,
        )

    try:
        revision = _clean_revision()
        config = load_sec_provider_config_from_file()
        result = (
            source.acquire_strong_leader_pullback_listed_consideration_residual_source(
                plan_root=args.plan,
                plan_custody_root=args.plan_custody_root,
                output_root=args.output_root,
                output_custody_root=args.output_custody_root,
                config=config,
                implementation_revision=revision,
                progress=progress,
            )
        )
    except (
        OSError,
        RuntimeError,
        SecCredentialFileError,
        SecTransportError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": source.CONTRACT_VERSION,
                    "record_type": "residual_source_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "safe_resume_requires_formal_artifact_reread": True,
                    "credential_material_retained": False,
                    "identity_assignment_count": 0,
                    "terminal_value_count": 0,
                    "canonical_data_write_count": 0,
                    "research_admission_count": 0,
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
                "contract_version": source.CONTRACT_VERSION,
                "record_type": "residual_source_completion",
                "status": result.status,
                "implementation_revision": revision,
                "completed_document_count": manifest.completed_document_count,
                "new_document_count": result.new_document_count,
                "network_request_count": result.network_request_count,
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "total_document_bytes": manifest.total_document_bytes,
                "external_request_count": manifest.external_request_count,
                "retry_count": manifest.retry_count,
                "credential_material_retained": False,
                "identity_assignment_count": 0,
                "terminal_value_count": 0,
                "canonical_data_write_count": 0,
                "research_admission_count": 0,
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
        raise source.StrongLeaderPullbackListedConsiderationResidualSourceError(
            "repository must be clean"
        )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
