"""Thin CLI for the offline-only official evidence priority plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tip_api.services.china_ashare_official_evidence_priority_build import (
    build_and_replay_china_ashare_official_evidence_priority_plan,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-package", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--replay-custody-root", type=Path, required=True)
    args = parser.parse_args()
    result = build_and_replay_china_ashare_official_evidence_priority_plan(
        input_package_path=args.input_package,
        output_custody_root=args.custody_root,
        replay_custody_root=args.replay_custody_root,
    )
    plan = result.primary.plan
    print(
        json.dumps(
            {
                "status": "exact_replay_complete",
                "package_path": str(result.primary.package_path),
                "package_fingerprint": result.primary.manifest.logical_fingerprint,
                "manifest_physical_sha256": (
                    result.primary.manifest_physical_sha256
                ),
                "plan_fingerprint": plan.logical_fingerprint,
                "input_package_fingerprint": plan.input_package_fingerprint,
                "interval_start": plan.interval_start.isoformat(),
                "interval_end": plan.interval_end.isoformat(),
                "request_count": len(plan.requests),
                "tiers": [item.model_dump(mode="json") for item in plan.tiers],
                "corporate_action_candidate_security_count": (
                    plan.corporate_action_candidate_security_count
                ),
                "corporate_action_candidate_window_count": (
                    plan.corporate_action_candidate_window_count
                ),
                "corporate_action_request_count": 0,
                "forward_reverse_identical": result.forward_reverse_identical,
                "byte_identical": result.byte_identical,
                "physical_hashes_identical": result.physical_hashes_identical,
                "physical_sha256s": dict(result.physical_sha256s),
                "network_execution_authorized": False,
                "outcome_read_count": 0,
                "return_construction_authorized": False,
                "historical_coverage_authorized": False,
                "factor_discovery_authorized": False,
                "research_backtest_authorized": False,
                "product_publication_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
