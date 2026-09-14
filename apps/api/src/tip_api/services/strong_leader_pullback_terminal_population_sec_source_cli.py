"""CLI for corrected-population SEC source custody."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from tip_api.providers.sec.credential import load_sec_provider_config_from_file
from tip_api.services import strong_leader_pullback_terminal_population_sec_source as service


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
    try:
        revision = _clean_revision()
        result = service.acquire_strong_leader_pullback_terminal_population_sec_source(
            plan_root=args.plan,
            plan_custody_root=args.plan_custody_root,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            config=load_sec_provider_config_from_file(),
            implementation_revision=revision,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "contract_version": service.CONTRACT_VERSION,
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "credential_material_retained": False,
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
    manifest = result.manifest
    print(
        json.dumps(
            {
                "contract_version": manifest.contract_version,
                "status": result.status,
                "implementation_revision": revision,
                "completed_document_count": result.completed_document_count,
                "new_document_count": result.new_document_count,
                "network_request_count": result.network_request_count,
                "retry_count": manifest.retry_count,
                "total_document_bytes": manifest.total_document_bytes,
                "content_type_counts": manifest.content_type_counts,
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "credential_material_retained": False,
                "canonical_data_write_count": 0,
                "research_admission_count": 0,
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
        raise service.StrongLeaderPullbackTerminalPopulationSecSourceError(
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
