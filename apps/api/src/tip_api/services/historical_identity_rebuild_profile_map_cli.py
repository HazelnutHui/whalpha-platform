"""Network-disabled CLI for the historical Identity rebuild profile map."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tip_api.services.historical_identity_rebuild_profile_map import (
    build_historical_identity_rebuild_profile_map,
    read_historical_identity_rebuild_profile_map,
    write_historical_identity_rebuild_profile_map,
)
from tip_api.services.historical_universe_membership_shadow_cli import (
    _network_disabled,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bind each retained Identity package to its exact rebuild profile."
    )
    parser.add_argument("--current-census-report", type=Path, required=True)
    parser.add_argument("--legacy-census-report", type=Path, required=True)
    parser.add_argument("--generated-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    args = parser.parse_args(argv)

    with _network_disabled():
        profile_map = build_historical_identity_rebuild_profile_map(
            current_census_report_path=args.current_census_report,
            legacy_census_report_path=args.legacy_census_report,
            generated_at=args.generated_at,
        )
        output_path = write_historical_identity_rebuild_profile_map(
            profile_map=profile_map,
            output_path=args.output_path,
        )
        reread = read_historical_identity_rebuild_profile_map(output_path)
    if reread != profile_map:
        raise RuntimeError("formal profile-map reread differs from generated map")

    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "contract_version": profile_map.contract_version,
                "canonical_session_count": profile_map.canonical_session_count,
                "bound_session_count": profile_map.bound_session_count,
                "missing_session_count": len(profile_map.missing_session_dates),
                "unbound_identity_mismatch_session_count": len(
                    profile_map.unbound_identity_mismatch_session_dates
                ),
                "profile_counts": dict(profile_map.profile_counts),
                "logical_fingerprint": profile_map.logical_fingerprint,
                "external_request_count": profile_map.external_request_count,
                "canonical_data_write_count": profile_map.canonical_data_write_count,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
