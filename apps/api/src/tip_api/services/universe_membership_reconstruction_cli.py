"""Read-only-source, temporary-output Daily Universe Membership pilot."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tip_api.persistence.parquet.historical_research import ParquetHistoricalResearchRepository
from tip_api.persistence.parquet.superseding_full_base import read_completed_superseding_full_base
from tip_api.services.universe_membership_reconstruction import reconstruct_from_superseding_full_base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconstruct one point-in-time membership partition into /tmp.")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--analysis-session", required=True)
    parser.add_argument("--evaluated-at", required=True)
    args = parser.parse_args(argv)

    source_root = args.source_root.resolve(strict=True)
    output_root = args.output_root.resolve(strict=False)
    temporary_root = Path("/tmp").resolve(strict=True)
    if temporary_root not in output_root.parents:
        raise RuntimeError("pilot output must be a child of /tmp")
    if source_root == output_root or source_root in output_root.parents or output_root in source_root.parents:
        raise RuntimeError("source and output roots must be disjoint")

    from datetime import date

    analysis_session = date.fromisoformat(args.analysis_session)
    evaluated_at = datetime.fromisoformat(args.evaluated_at)
    completed = read_completed_superseding_full_base(source_root, analysis_session=analysis_session)
    reconstruction = reconstruct_from_superseding_full_base(completed, evaluated_at=evaluated_at)
    repository = ParquetHistoricalResearchRepository(output_root, created_at=evaluated_at)
    result = repository.publish_universe_membership(
        reconstruction.records,
        methodology_version=reconstruction.methodology_version,
        session_date=reconstruction.session_date,
    )
    reread = repository.read_universe_membership(result.partition_path)
    if reread != reconstruction.records:
        raise RuntimeError("formal membership reread differs from reconstructed records")
    print(
        json.dumps(
            {
                "status": result.status,
                "session_date": reconstruction.session_date.isoformat(),
                "origin": "reconstructed_point_in_time",
                "methodology_version": reconstruction.methodology_version,
                "evaluated_base_count": reconstruction.evaluated_base_count,
                "evaluated_base_fingerprint": reconstruction.evaluated_base_fingerprint,
                "record_count": result.record_count,
                "included_counts": dict(reconstruction.included_counts),
                "excluded_counts": dict(reconstruction.excluded_counts),
                "quarantined_counts": dict(reconstruction.quarantined_counts),
                "partition_path": str(result.partition_path),
                "logical_fingerprint": result.logical_fingerprint,
                "physical_sha256": result.physical_sha256,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
