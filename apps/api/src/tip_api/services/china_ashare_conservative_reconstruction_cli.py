"""Thin admin CLI for exact conservative A-share build and replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tip_api.persistence.china_ashare_conservative_reconstruction_package import (
    read_china_ashare_conservative_reconstruction_package,
)
from tip_api.services.china_ashare_conservative_reconstruction_build import (
    build_and_replay_china_ashare_conservative_reconstruction,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build-replay")
    for name in (
        "population-package", "source-plan-root", "diagnostic-plan-package",
        "normalized-custody-root", "market-mechanics-package", "cninfo-plan-root",
        "custody-root", "replay-custody-root",
    ):
        build.add_argument(f"--{name}", type=Path, required=True)
    reread = commands.add_parser("reread")
    reread.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "reread":
        result = read_china_ashare_conservative_reconstruction_package(
            package_path=args.package
        )
        _emit(result=result, replay=False)
        return 0
    result = build_and_replay_china_ashare_conservative_reconstruction(
        population_package_path=args.population_package,
        source_plan_root=args.source_plan_root,
        diagnostic_plan_package=args.diagnostic_plan_package,
        normalized_custody_root=args.normalized_custody_root,
        market_mechanics_package=args.market_mechanics_package,
        cninfo_plan_root=args.cninfo_plan_root,
        output_custody_root=args.custody_root,
        replay_custody_root=args.replay_custody_root,
    )
    _emit(result=result.primary, replay=True)
    return 0


def _emit(*, result, replay: bool) -> None:
    census = result.census
    print(json.dumps({
        "status": "exact_replay_complete" if replay else result.status,
        "package_path": str(result.package_path),
        "package_fingerprint": result.manifest.logical_fingerprint,
        "manifest_physical_sha256": result.manifest_physical_sha256,
        "plan_fingerprint": result.plan.logical_fingerprint,
        "global_census_fingerprint": census.logical_fingerprint,
        "candidate_set_fingerprint": census.candidate_set_fingerprint,
        "partition_count": len(result.partition_manifests),
        "row_count": census.state_count,
        "provisional_include_count": census.provisional_candidate_included_state_count,
        "warning_exclude_count": census.provisional_candidate_excluded_state_count,
        "quarantine_count": census.provisional_quarantined_state_count,
        "official_budget_by_priority": [
            item.model_dump(mode="json")
            for item in census.official_request_budget_by_priority
        ],
        "maximum_official_request_count": census.maximum_official_request_count,
        "avoided_request_count": census.avoided_request_count,
        "byte_identical": replay,
        "physical_hashes_identical": replay,
        "as_operated": False,
        "research_authorized": False,
        "return_construction_authorized": False,
        "historical_coverage_authorized": False,
        "research_backtest_authorized": False,
    }, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
