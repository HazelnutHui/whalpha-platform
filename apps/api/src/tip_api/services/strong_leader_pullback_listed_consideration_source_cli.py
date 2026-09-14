"""CLI for resumable listed-consideration registration-document custody."""

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
from tip_api.services.strong_leader_pullback_listed_consideration_source import (
    CONTRACT_VERSION,
    ListedConsiderationDocumentArtifactV1,
    StrongLeaderPullbackListedConsiderationSourceError,
    acquire_strong_leader_pullback_listed_consideration_source,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--plan-custody-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-custody-root", required=True, type=Path)
    parser.add_argument("--maximum-new-documents", type=int)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None

    def progress(
        artifact: ListedConsiderationDocumentArtifactV1,
        completed: int,
        total: int,
    ) -> None:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "listed_consideration_source_checkpoint",
                    "implementation_revision": revision,
                    "request_sequence": artifact.request_sequence,
                    "completed_document_count": completed,
                    "planned_document_count": total,
                    "document_bytes": artifact.byte_count,
                    "document_sha256": artifact.physical_sha256,
                    "credential_material_retained": False,
                    "identity_assignment_count": 0,
                    "terminal_value_count": 0,
                    "canonical_data_write_count": 0,
                    "research_admission_count": 0,
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
        result = acquire_strong_leader_pullback_listed_consideration_source(
            plan_root=args.plan,
            plan_custody_root=args.plan_custody_root,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            config=config,
            implementation_revision=revision,
            maximum_new_documents=args.maximum_new_documents,
            progress=progress,
        )
    except (
        OSError,
        RuntimeError,
        SecCredentialFileError,
        SecTransportError,
        StrongLeaderPullbackListedConsiderationSourceError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "listed_consideration_source_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "safe_resume_requires_formal_artifact_reread": True,
                    "credential_material_retained": False,
                    "identity_assignment_count": 0,
                    "terminal_value_count": 0,
                    "canonical_data_write_count": 0,
                    "research_admission_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    output = {
        "contract_version": CONTRACT_VERSION,
        "record_type": "listed_consideration_source_progress",
        "status": result.status,
        "implementation_revision": revision,
        "completed_document_count": result.completed_document_count,
        "new_document_count": result.new_document_count,
        "network_request_count": result.network_request_count,
        "credential_material_retained": False,
        "identity_assignment_count": 0,
        "terminal_value_count": 0,
        "canonical_data_write_count": 0,
        "research_admission_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
    }
    if result.manifest is not None:
        output.update(
            {
                "record_type": "listed_consideration_source_completion",
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": result.manifest.logical_fingerprint,
                "total_document_bytes": result.manifest.total_document_bytes,
                "external_request_count": result.manifest.external_request_count,
                "retry_count": result.manifest.retry_count,
            }
        )
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


def _clean_revision() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise StrongLeaderPullbackListedConsiderationSourceError(
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
