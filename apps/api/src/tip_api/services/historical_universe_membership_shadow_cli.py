"""Network-disabled, /tmp-only historical Universe Membership shadow CLI."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.services.historical_universe_membership_shadow import (
    build_historical_universe_membership_shadow,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build one source-bound historical membership shadow into /tmp."
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--identity-package", type=Path, required=True)
    parser.add_argument("--session-date", type=date.fromisoformat, required=True)
    parser.add_argument("--catalog-as-of-date", type=date.fromisoformat, required=True)
    parser.add_argument("--evaluated-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)

    data_root = args.data_root.resolve(strict=True)
    package_path = args.identity_package.resolve(strict=True)
    output_root = args.output_root.resolve(strict=False)
    temporary_root = Path("/tmp").resolve(strict=True)
    if temporary_root not in output_root.parents:
        parser.error("--output-root must be a child of /tmp")
    if any(_paths_overlap(output_root, item) for item in (data_root, package_path)):
        parser.error("source and output paths must be disjoint")

    with _network_disabled():
        shadow = build_historical_universe_membership_shadow(
            data_root=data_root,
            package_path=package_path,
            session_date=args.session_date,
            catalog_as_of_date=args.catalog_as_of_date,
            evaluated_at=args.evaluated_at,
        )
        reconstruction = shadow.reconstruction
        repository = ParquetHistoricalResearchRepository(
            output_root,
            created_at=args.evaluated_at,
        )
        result = repository.publish_universe_membership(
            reconstruction.records,
            methodology_version=reconstruction.methodology_version,
            session_date=reconstruction.session_date,
        )
        reread = repository.read_universe_membership(result.partition_path)
    if reread != reconstruction.records:
        raise RuntimeError("formal membership reread differs from shadow records")

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
                "source_data_cutoff": shadow.source_data_cutoff.isoformat(),
                "raw_provider_record_count": shadow.raw_provider_record_count,
                "canonical_evidence_count": shadow.canonical_evidence_count,
                "source_quarantined_instrument_count": (
                    shadow.source_quarantined_instrument_count
                ),
                "evidence_quality_gate_failures": list(
                    shadow.evidence_quality_gate_failures
                ),
                "partition_path": str(result.partition_path),
                "logical_fingerprint": result.logical_fingerprint,
                "physical_sha256": result.physical_sha256,
                "external_request_count": 0,
                "canonical_data_write_count": 0,
            },
            sort_keys=True,
        )
    )
    return 0


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


@contextmanager
def _network_disabled():
    original_socket = socket.socket

    def blocked_socket(*_args: object, **_kwargs: object):
        raise RuntimeError("network access is disabled for historical membership shadow")

    socket.socket = blocked_socket  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]


if __name__ == "__main__":
    raise SystemExit(main())
