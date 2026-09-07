"""Formal reader for completed canonical Universe Membership publication."""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from tip_api.contracts.market_data.v1 import (
    UniverseMembershipCanonicalPublicationV1,
    UniverseMembershipDecisionV1,
    UniverseMembershipPartitionManifestV1,
)
from tip_api.persistence.parquet.historical_research import (
    MANIFEST_FILE_NAME,
    PARQUET_FILE_NAME,
    ParquetHistoricalResearchRepository,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.historical_identity_source_custody import (
    read_historical_identity_source_custody,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
PUBLICATION_DIRECTORY = "universe-membership-publications"
PUBLICATION_FILE_NAME = "manifest.json"
PUBLICATION_POLICY_ID = "next-open-v1"


class CanonicalUniverseMembershipError(RuntimeError):
    """Raised when canonical Membership completion cannot be proven."""


@dataclass(frozen=True, slots=True)
class CanonicalUniverseMembershipReadResult:
    membership_partition_path: Path
    publication_partition_path: Path
    publication: UniverseMembershipCanonicalPublicationV1
    publication_sha256: str
    membership_manifest: UniverseMembershipPartitionManifestV1
    records: tuple[UniverseMembershipDecisionV1, ...]


def read_canonical_universe_membership(
    *,
    data_root: Path,
    methodology_version: str,
    session_date: date,
    provider: str = MASSIVE_PROVIDER_ID,
    expected_publication_fingerprint: str | None = None,
) -> CanonicalUniverseMembershipReadResult:
    """Read Membership only when the physical partition and last marker agree."""

    root = _validated_data_root(data_root)
    if provider != MASSIVE_PROVIDER_ID:
        raise CanonicalUniverseMembershipError(
            "canonical Membership requires the canonical provider"
        )
    methodology = _safe_segment(methodology_version)
    membership_partition = _membership_partition(
        root,
        methodology,
        session_date,
    )
    publication_partition = _publication_partition(
        root,
        methodology,
        session_date,
    )
    _validated_partition(
        root,
        membership_partition,
        expected_files={MANIFEST_FILE_NAME, PARQUET_FILE_NAME},
    )
    _validated_partition(
        root,
        publication_partition,
        expected_files={PUBLICATION_FILE_NAME},
    )

    publication_path = publication_partition / PUBLICATION_FILE_NAME
    publication_bytes = _read_regular_file(publication_path)
    try:
        publication = UniverseMembershipCanonicalPublicationV1.model_validate_json(
            publication_bytes
        )
    except Exception as exc:
        raise CanonicalUniverseMembershipError(
            "canonical Membership publication marker is invalid"
        ) from exc
    if publication_bytes != _canonical_json_bytes(
        publication.model_dump(mode="json")
    ):
        raise CanonicalUniverseMembershipError(
            "canonical Membership publication bytes are not canonical"
        )
    if (
        expected_publication_fingerprint is not None
        and publication.logical_fingerprint != expected_publication_fingerprint
    ):
        raise CanonicalUniverseMembershipError(
            "canonical Membership publication fingerprint differs"
        )
    expected_relative = membership_partition.relative_to(root).as_posix()
    if (
        publication.session_date != session_date
        or publication.methodology_version != methodology
        or publication.membership_partition_path != expected_relative
    ):
        raise CanonicalUniverseMembershipError(
            "canonical Membership publication path binding differs"
        )

    manifest_path = membership_partition / MANIFEST_FILE_NAME
    parquet_path = membership_partition / PARQUET_FILE_NAME
    manifest_bytes = _read_regular_file(manifest_path)
    parquet_bytes = _read_regular_file(parquet_path)
    try:
        manifest = UniverseMembershipPartitionManifestV1.model_validate_json(
            manifest_bytes
        )
    except Exception as exc:
        raise CanonicalUniverseMembershipError(
            "canonical Membership physical manifest is invalid"
        ) from exc
    if (
        _bytes_sha256(manifest_bytes) != publication.membership_manifest_sha256
        or _bytes_sha256(parquet_bytes) != publication.membership_parquet_sha256
        or manifest.logical_fingerprint
        != publication.membership_logical_fingerprint
        or manifest.record_count != publication.record_count
        or manifest.methodology_version != methodology
        or manifest.session_date != session_date
    ):
        raise CanonicalUniverseMembershipError(
            "canonical Membership physical evidence differs from publication"
        )
    try:
        records = ParquetHistoricalResearchRepository(
            root
        ).read_universe_membership(membership_partition)
    except Exception as exc:
        raise CanonicalUniverseMembershipError(
            "canonical Membership formal physical read failed"
        ) from exc
    if len(records) != publication.record_count:
        raise CanonicalUniverseMembershipError(
            "canonical Membership record count differs"
        )

    assessment = publication.knowledge_time_assessment
    try:
        source = read_historical_identity_source_custody(
            data_root=root,
            provider=provider,
            session_date=session_date,
        ).manifest
    except Exception as exc:
        raise CanonicalUniverseMembershipError(
            "canonical Membership Identity source custody is unavailable"
        ) from exc
    if (
        source.as_of_date != session_date
        or source.logical_fingerprint
        != assessment.identity_source_logical_fingerprint
        or source.contract_version
        != assessment.identity_source_contract_version
        or source.point_in_time_eligibility
        != assessment.identity_source_point_in_time_eligibility
        or source.source_package_fetched_at > assessment.source_data_cutoff
    ):
        raise CanonicalUniverseMembershipError(
            "canonical Membership Identity source binding differs"
        )
    return CanonicalUniverseMembershipReadResult(
        membership_partition_path=membership_partition,
        publication_partition_path=publication_partition,
        publication=publication,
        publication_sha256=_bytes_sha256(publication_bytes),
        membership_manifest=manifest,
        records=records,
    )


def _membership_partition(root: Path, methodology: str, session: date) -> Path:
    return (
        root
        / "market-data"
        / "universe-membership"
        / "schema_version=1"
        / f"methodology_version={methodology}"
        / f"session_date={session.isoformat()}"
    )


def _publication_partition(root: Path, methodology: str, session: date) -> Path:
    return (
        root
        / "market-data"
        / PUBLICATION_DIRECTORY
        / "schema_version=1"
        / f"policy_id={PUBLICATION_POLICY_ID}"
        / f"methodology_version={methodology}"
        / f"session_date={session.isoformat()}"
    )


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalUniverseMembershipError(
            "canonical Membership data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CanonicalUniverseMembershipError(
            "canonical Membership data root is not the approved Dell root"
        )
    return resolved


def _validated_partition(
    root: Path,
    partition: Path,
    *,
    expected_files: set[str],
) -> None:
    _reject_symlink_chain(root, partition)
    if (
        partition.is_symlink()
        or not partition.is_dir()
        or stat.S_IMODE(partition.stat().st_mode) != 0o755
    ):
        raise CanonicalUniverseMembershipError(
            "canonical Membership partition is missing or unsafe"
        )
    if {item.name for item in partition.iterdir()} != expected_files:
        raise CanonicalUniverseMembershipError(
            "canonical Membership partition file set differs"
        )


def _read_regular_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise CanonicalUniverseMembershipError(
            "canonical Membership file is missing or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o644
    ):
        raise CanonicalUniverseMembershipError(
            "canonical Membership file mode differs"
        )
    return path.read_bytes()


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise CanonicalUniverseMembershipError(
            "canonical Membership path escaped the data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise CanonicalUniverseMembershipError(
                "canonical Membership path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _safe_segment(value: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
    if not value or any(character not in allowed for character in value):
        raise CanonicalUniverseMembershipError(
            "canonical Membership methodology is unsafe"
        )
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
