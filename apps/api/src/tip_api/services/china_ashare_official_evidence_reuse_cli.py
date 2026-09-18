"""Thin offline CLI for the local official-evidence reuse package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tip_api.services.china_ashare_official_evidence_reuse_build import (
    build_china_ashare_official_evidence_reuse_package,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--priority-plan-package", type=Path, required=True)
    parser.add_argument("--official-event-plan-root", type=Path, action="append", default=[])
    parser.add_argument("--official-document-plan-root", type=Path, action="append", default=[])
    parser.add_argument("--cninfo-plan-root", type=Path, action="append", default=[])
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--replay-custody-root", type=Path, required=True)
    args = parser.parse_args(argv)
    result = build_china_ashare_official_evidence_reuse_package(
        priority_plan_package=args.priority_plan_package,
        official_event_plan_roots=tuple(args.official_event_plan_root),
        official_document_plan_roots=tuple(args.official_document_plan_root),
        cninfo_plan_roots=tuple(args.cninfo_plan_root), custody_root=args.custody_root,
        replay_custody_root=args.replay_custody_root,
    )
    print(json.dumps({
        "package_path": str(result.primary.package_path),
        "package_fingerprint": result.primary.manifest.logical_fingerprint,
        "inventory_fingerprint": result.primary.inventory.logical_fingerprint,
        "census_fingerprint": result.primary.census.logical_fingerprint,
        "warning_batch_fingerprint": result.primary.warning_batch.logical_fingerprint,
        "evidence_count": result.primary.inventory.evidence_count,
        "reusable_request_count": result.primary.census.reusable_request_count,
        "network_required_request_count": result.primary.census.network_required_request_count,
        "warning_request_count": len(result.primary.warning_batch.requests),
        "maximum_total_http_attempts": result.primary.warning_batch.maximum_total_http_attempts,
        "byte_identical_replay": result.byte_identical,
        "network_execution_authorized": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
