"""CLI for the read-only Strong-Leader Pullback development census."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import stat
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from tip_api.contracts.analytics.v1.candidate_strategy_development_coverage import (
    STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY,
    StrongLeaderPullbackDevelopmentCoverageCensusV1,
)
from tip_api.contracts.market_data.v1 import (
    UniverseMembershipPartitionManifestV1,
)
from tip_api.persistence.development_coverage_census import (
    write_development_coverage_census,
)
from tip_api.persistence.parquet.canonical_corporate_action import (
    read_canonical_split_action_publication,
)
from tip_api.persistence.parquet.canonical_split_adjustment import (
    read_canonical_split_adjustment_publication,
)
from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.candidate_strategy_development_coverage import (
    ReconstructedMembershipSessionEvidence,
    build_strong_leader_pullback_development_coverage_census,
)
from tip_api.services.historical_identity_source_custody import (
    read_historical_identity_source_custody,
)
from tip_api.services.market_calendar import ExchangeCalendar


class StrongLeaderPullbackDevelopmentCoverageCliError(RuntimeError):
    """Raised when filesystem evidence for the census is unsafe or incomplete."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Formally reread Dell evidence and create one outcome-blind, "
            "owner-only development coverage census below /tmp."
        )
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--membership-shadow-root", type=Path, required=True)
    parser.add_argument("--split-action-publication-root", type=Path, required=True)
    parser.add_argument(
        "--split-adjustment-publication-root", type=Path, required=True
    )
    parser.add_argument("--source-revision", required=True)
    parser.add_argument(
        "--calculated-at", type=datetime.fromisoformat, required=True
    )
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        report_path, report = run_development_coverage_census(
            data_root=args.data_root,
            membership_shadow_root=args.membership_shadow_root,
            split_action_publication_root=(
                args.split_action_publication_root
            ),
            split_adjustment_publication_root=(
                args.split_adjustment_publication_root
            ),
            source_revision=args.source_revision,
            calculated_at=args.calculated_at,
            output_root=args.output_root,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": (
                        "strong_leader_pullback_development_census_rejected"
                    ),
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1

    print(
        json.dumps(
            {
                "status": "completed",
                "report_path": str(report_path),
                "logical_fingerprint": report.logical_fingerprint,
                "first_session": report.first_session.isoformat(),
                "last_session": report.last_session.isoformat(),
                "session_count": report.session_count,
                "instrument_count": report.instrument_count,
                "primary_decision_count": report.primary_decision_count,
                "primary_included_count": report.primary_included_count,
                "primary_excluded_count": report.primary_excluded_count,
                "primary_quarantined_count": report.primary_quarantined_count,
                "raw_feature_path_complete_count": (
                    report.raw_feature_path_complete_count
                ),
                "sparse_clear_split_exposure_count": (
                    report.sparse_clear_split_exposure_count
                ),
                "split_quarantined_path_count": (
                    report.split_quarantined_path_count
                ),
                "absent_row_neutrality_unproven_path_count": (
                    report.absent_row_neutrality_unproven_path_count
                ),
                "lifecycle_unavailable_path_count": (
                    report.lifecycle_unavailable_path_count
                ),
                "all_required_evidence_complete_count": (
                    report.all_required_evidence_complete_count
                ),
                "development_authorized": report.development_authorized,
                "external_request_count": report.external_request_count,
                "canonical_data_write_count": report.canonical_data_write_count,
                "production_write_count": report.production_write_count,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def run_development_coverage_census(
    *,
    data_root: Path,
    membership_shadow_root: Path,
    split_action_publication_root: Path,
    split_adjustment_publication_root: Path,
    source_revision: str,
    calculated_at: datetime,
    output_root: Path,
) -> tuple[Path, StrongLeaderPullbackDevelopmentCoverageCensusV1]:
    with _network_disabled():
        return _run_development_coverage_census(
            data_root=data_root,
            membership_shadow_root=membership_shadow_root,
            split_action_publication_root=split_action_publication_root,
            split_adjustment_publication_root=split_adjustment_publication_root,
            source_revision=source_revision,
            calculated_at=calculated_at,
            output_root=output_root,
        )


def _run_development_coverage_census(
    *,
    data_root: Path,
    membership_shadow_root: Path,
    split_action_publication_root: Path,
    split_adjustment_publication_root: Path,
    source_revision: str,
    calculated_at: datetime,
    output_root: Path,
) -> tuple[Path, StrongLeaderPullbackDevelopmentCoverageCensusV1]:
    data_root = _validated_data_root(data_root)
    shadow_root = _validated_shadow_root(membership_shadow_root)
    partitions = _discover_membership_partitions(shadow_root)
    action_source = read_canonical_split_action_publication(
        data_root=data_root,
        publication_root=split_action_publication_root,
    )
    adjustment_source = read_canonical_split_adjustment_publication(
        data_root=data_root,
        publication_root=split_adjustment_publication_root,
    )
    calendar = ExchangeCalendar()
    report = build_strong_leader_pullback_development_coverage_census(
        membership_sessions=_membership_evidence(
            data_root=data_root,
            shadow_root=shadow_root,
            partitions=partitions,
        ),
        split_action_publication=action_source.publication,
        split_actions=action_source.actions,
        split_action_manifest_sha256=action_source.manifest_sha256,
        split_adjustment_publication=adjustment_source.publication,
        split_adjustments=adjustment_source.records,
        split_adjustment_manifest_sha256=adjustment_source.manifest_sha256,
        source_revision=source_revision,
        calculated_at=calculated_at,
        calendar=calendar,
    )
    report_path = write_development_coverage_census(
        output_root=output_root,
        report=report,
    )
    return report_path, report


def _membership_evidence(
    *,
    data_root: Path,
    shadow_root: Path,
    partitions: dict[date, Path],
) -> Iterator[ReconstructedMembershipSessionEvidence]:
    for session_date, partition in sorted(partitions.items()):
        batch_root = _batch_root(shadow_root, partition)
        repository = ParquetHistoricalResearchRepository(batch_root)
        records = repository.read_universe_membership(partition)
        manifest_path = partition / "manifest.json"
        manifest_raw = manifest_path.read_bytes()
        manifest = UniverseMembershipPartitionManifestV1.model_validate_json(
            manifest_raw
        )
        identity = read_historical_identity_source_custody(
            data_root=data_root,
            provider=MASSIVE_PROVIDER_ID,
            session_date=session_date,
        )
        yield ReconstructedMembershipSessionEvidence(
            manifest=manifest,
            manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
            records=records,
            identity_source_logical_fingerprint=identity.manifest.logical_fingerprint,
            identity_source_record_count=identity.manifest.record_count,
            identity_source_content_fingerprint=identity.manifest.content_fingerprint,
            identity_source_manifest_sha256=identity.manifest_sha256,
            identity_source_parquet_sha256=identity.manifest.parquet_sha256,
            identity_source_materialized_at=identity.manifest.materialized_at,
        )


def _discover_membership_partitions(shadow_root: Path) -> dict[date, Path]:
    partitions: dict[date, Path] = {}
    for current, directories, files in os.walk(shadow_root, followlinks=False):
        current_path = Path(current)
        for name in (*directories, *files):
            if (current_path / name).is_symlink():
                raise StrongLeaderPullbackDevelopmentCoverageCliError(
                    "Membership shadow contains a symlink"
                )
        if "manifest.json" not in files:
            continue
        relative = current_path.relative_to(shadow_root)
        parts = relative.parts
        if len(parts) != 6 or parts[1:5] != (
            "market-data",
            "universe-membership",
            "schema_version=1",
            (
                "methodology_version="
                f"{STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY}"
            ),
        ):
            continue
        if not parts[0].startswith("batch-") or not parts[5].startswith(
            "session_date="
        ):
            raise StrongLeaderPullbackDevelopmentCoverageCliError(
                "Membership shadow partition layout differs"
            )
        try:
            session_date = date.fromisoformat(parts[5].removeprefix("session_date="))
        except ValueError as exc:
            raise StrongLeaderPullbackDevelopmentCoverageCliError(
                "Membership shadow session key is malformed"
            ) from exc
        if not (
            STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION
            <= session_date
            <= STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION
        ):
            continue
        if session_date in partitions:
            raise StrongLeaderPullbackDevelopmentCoverageCliError(
                "Membership shadow contains a duplicate census session"
            )
        partitions[session_date] = current_path
    return partitions


def _batch_root(shadow_root: Path, partition: Path) -> Path:
    relative = partition.relative_to(shadow_root)
    batch_root = shadow_root / relative.parts[0]
    if (
        batch_root.is_symlink()
        or not batch_root.is_dir()
        or batch_root.resolve(strict=True) != batch_root
    ):
        raise StrongLeaderPullbackDevelopmentCoverageCliError(
            "Membership shadow batch custody differs"
        )
    return batch_root


def _validated_data_root(path: Path) -> Path:
    expected = Path("/data/trading-intelligence-platform")
    root = path.absolute()
    if (
        root != expected
        or root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
    ):
        raise StrongLeaderPullbackDevelopmentCoverageCliError(
            "canonical data root differs"
        )
    return root


def _validated_shadow_root(path: Path) -> Path:
    root = path.absolute()
    temporary_root = Path("/tmp").resolve(strict=True)
    if (
        root.parent != temporary_root
        or not root.name.startswith("whalpha-canonical-membership-full-shadow-")
        or root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
    ):
        raise StrongLeaderPullbackDevelopmentCoverageCliError(
            "Membership shadow root custody differs"
        )
    return root


@contextmanager
def _network_disabled():
    original_socket = socket.socket

    def blocked_socket(*_args: object, **_kwargs: object):
        raise RuntimeError("network access is disabled for development census")

    socket.socket = blocked_socket  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
