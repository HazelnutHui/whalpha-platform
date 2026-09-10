"""Formal reader for research-only reconstructed Universe Membership custody."""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from tip_api.contracts.market_data.v1 import (
    RESEARCH_UNIVERSE_MEMBERSHIP_PATH_EVIDENCE_TIER,
    ResearchUniverseMembershipCustodyV1,
    UniverseMembershipDecisionV1,
    UniverseMembershipOrigin,
    UniverseMembershipPartitionManifestV1,
)
from tip_api.persistence.parquet.historical_research import (
    MANIFEST_FILE_NAME,
    PARQUET_FILE_NAME,
    read_universe_membership_partition_content,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
FAMILY_DIRECTORY = "research-universe-membership"
CUSTODY_FILE_NAME = "research-custody.json"


class CanonicalResearchUniverseMembershipError(RuntimeError):
    """Raised when research Membership completion cannot be proven."""


@dataclass(frozen=True, slots=True)
class CanonicalResearchUniverseMembershipReadResult:
    membership_partition_path: Path
    custody: ResearchUniverseMembershipCustodyV1
    custody_sha256: str
    membership_manifest: UniverseMembershipPartitionManifestV1
    records: tuple[UniverseMembershipDecisionV1, ...]


def read_canonical_research_universe_membership(
    *,
    data_root: Path,
    methodology_version: str,
    session_date: date,
    expected_custody_fingerprint: str | None = None,
    read_records: bool = True,
) -> CanonicalResearchUniverseMembershipReadResult:
    """Read one partition only after marker, bytes, manifest, and rows agree."""

    root = _validated_data_root(data_root)
    methodology = _safe_segment(methodology_version)
    partition = research_membership_partition(
        root,
        methodology_version=methodology,
        session_date=session_date,
    )
    _validated_partition(root, partition)

    custody_bytes = _read_regular_file(partition / CUSTODY_FILE_NAME)
    try:
        custody = ResearchUniverseMembershipCustodyV1.model_validate_json(
            custody_bytes
        )
    except Exception as exc:
        raise CanonicalResearchUniverseMembershipError(
            "research Membership custody marker is invalid"
        ) from exc
    if custody_bytes != _canonical_json_bytes(custody.model_dump(mode="json")):
        raise CanonicalResearchUniverseMembershipError(
            "research Membership custody bytes are not canonical"
        )
    if (
        expected_custody_fingerprint is not None
        and custody.logical_fingerprint != expected_custody_fingerprint
    ):
        raise CanonicalResearchUniverseMembershipError(
            "research Membership custody fingerprint differs"
        )
    if (
        custody.session_date != session_date
        or custody.methodology_version != methodology
        or custody.membership_partition_path
        != partition.relative_to(root).as_posix()
    ):
        raise CanonicalResearchUniverseMembershipError(
            "research Membership custody path binding differs"
        )

    manifest_path = partition / MANIFEST_FILE_NAME
    parquet_path = partition / PARQUET_FILE_NAME
    manifest_bytes = _read_regular_file(manifest_path)
    _validate_regular_file(parquet_path)
    try:
        manifest = UniverseMembershipPartitionManifestV1.model_validate_json(
            manifest_bytes
        )
    except Exception as exc:
        raise CanonicalResearchUniverseMembershipError(
            "research Membership manifest is invalid"
        ) from exc
    if (
        _bytes_sha256(manifest_bytes) != custody.membership_manifest_sha256
        or _file_sha256(parquet_path) != custody.membership_parquet_sha256
        or manifest.logical_fingerprint
        != custody.membership_logical_fingerprint
        or manifest.record_count != custody.record_count
        or manifest.evaluated_base_count != custody.evaluated_base_count
        or manifest.methodology_version != methodology
        or manifest.session_date != session_date
        or manifest.origin is not UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME
        or manifest.source_fingerprints != custody.source_fingerprints
        or manifest.source_data_cutoff != custody.source_data_cutoff
        or manifest.evaluated_at != custody.evaluated_at
    ):
        raise CanonicalResearchUniverseMembershipError(
            "research Membership physical evidence differs from custody"
        )
    records: tuple[UniverseMembershipDecisionV1, ...] = ()
    if read_records:
        try:
            records = read_universe_membership_partition_content(partition)
        except Exception as exc:
            raise CanonicalResearchUniverseMembershipError(
                "research Membership formal physical read failed"
            ) from exc
        if (
            len(records) != custody.record_count
            or any(
                record.session_date != session_date
                or record.methodology_version != methodology
                or record.origin is not UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME
                for record in records
            )
        ):
            raise CanonicalResearchUniverseMembershipError(
                "research Membership record scope differs"
            )
    return CanonicalResearchUniverseMembershipReadResult(
        membership_partition_path=partition,
        custody=custody,
        custody_sha256=_bytes_sha256(custody_bytes),
        membership_manifest=manifest,
        records=records,
    )


def research_membership_partition(
    root: Path,
    *,
    methodology_version: str,
    session_date: date,
) -> Path:
    return (
        root
        / "market-data"
        / FAMILY_DIRECTORY
        / "schema_version=1"
        / f"evidence_tier={RESEARCH_UNIVERSE_MEMBERSHIP_PATH_EVIDENCE_TIER}"
        / f"methodology_version={_safe_segment(methodology_version)}"
        / f"session_date={session_date.isoformat()}"
    )


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalResearchUniverseMembershipError(
            "research Membership data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CanonicalResearchUniverseMembershipError(
            "research Membership data root is not the approved Dell root"
        )
    return resolved


def _validated_partition(root: Path, partition: Path) -> None:
    _reject_symlink_chain(root, partition)
    if (
        partition.is_symlink()
        or not partition.is_dir()
        or stat.S_IMODE(partition.stat().st_mode) != 0o755
    ):
        raise CanonicalResearchUniverseMembershipError(
            "research Membership partition is missing or unsafe"
        )
    if {item.name for item in partition.iterdir()} != {
        MANIFEST_FILE_NAME,
        PARQUET_FILE_NAME,
        CUSTODY_FILE_NAME,
    }:
        raise CanonicalResearchUniverseMembershipError(
            "research Membership partition file set differs"
        )


def _read_regular_file(path: Path) -> bytes:
    _validate_regular_file(path)
    return path.read_bytes()


def _validate_regular_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise CanonicalResearchUniverseMembershipError(
            "research Membership file is missing or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o644
    ):
        raise CanonicalResearchUniverseMembershipError(
            "research Membership file mode differs"
        )


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise CanonicalResearchUniverseMembershipError(
            "research Membership path escaped data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise CanonicalResearchUniverseMembershipError(
                "research Membership path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _safe_segment(value: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
    if not value or any(character not in allowed for character in value):
        raise CanonicalResearchUniverseMembershipError(
            "research Membership methodology is unsafe"
        )
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
