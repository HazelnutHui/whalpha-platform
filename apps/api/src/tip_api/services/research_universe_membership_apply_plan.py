"""Exact no-write planning for reconstructed research Membership custody."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    ResearchUniverseMembershipApplyPlanV1,
    ResearchUniverseMembershipPlanArtifactV1,
    UniverseMembershipOrigin,
    UniverseMembershipPartitionManifestV1,
    build_research_universe_membership_apply_plan as build_plan_contract,
    build_research_universe_membership_custody,
)
from tip_api.persistence.parquet.historical_research import (
    MANIFEST_FILE_NAME,
    PARQUET_FILE_NAME,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar
from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    RESEARCH_MEMBERSHIP_APPLY_PLAN_NAME,
    validate_offline_artifact_location,
)
from tip_api.services.research_universe_membership_canonical import (
    CUSTODY_FILE_NAME,
    CanonicalResearchUniverseMembershipError,
    read_canonical_research_universe_membership,
    research_membership_partition,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
PLAN_FILE_NAME = RESEARCH_MEMBERSHIP_APPLY_PLAN_NAME


class ResearchUniverseMembershipApplyPlanError(RuntimeError):
    """Raised when research Membership planning evidence does not reconcile."""


@dataclass(frozen=True, slots=True)
class ResearchUniverseMembershipApplyPlanEvidence:
    plan: ResearchUniverseMembershipApplyPlanV1
    plan_path: Path
    plan_sha256: str


def build_research_universe_membership_apply_plan(
    *,
    data_root: Path,
    candidate_membership_partition: Path,
    created_at: datetime,
    plan_path: Path,
    calendar: MarketSessionCalendar | None = None,
) -> ResearchUniverseMembershipApplyPlanEvidence:
    """Bind one reconstructed candidate without writing canonical data."""

    root = _validated_data_root(data_root)
    created_at = normalize_utc_datetime(created_at)
    candidate = candidate_membership_partition.resolve(strict=True)
    manifest_path = candidate / MANIFEST_FILE_NAME
    parquet_path = candidate / PARQUET_FILE_NAME
    manifest = _read_manifest(manifest_path)
    if manifest.origin is not UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME:
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership requires reconstructed origin"
        )
    represented_close = (calendar or ExchangeCalendar()).session_close(
        manifest.session_date
    )
    if manifest.source_data_cutoff <= represented_close:
        raise ResearchUniverseMembershipApplyPlanError(
            "candidate is not later-observed latest-vintage evidence"
        )
    if created_at < manifest.evaluated_at:
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership plan precedes candidate evaluation"
        )
    target = research_membership_partition(
        root,
        methodology_version=manifest.methodology_version,
        session_date=manifest.session_date,
    )
    _require_absent_target(root, target)
    artifacts = (
        _artifact(
            file_name=MANIFEST_FILE_NAME,
            source=manifest_path,
            target=target / MANIFEST_FILE_NAME,
        ),
        _artifact(
            file_name=PARQUET_FILE_NAME,
            source=parquet_path,
            target=target / PARQUET_FILE_NAME,
        ),
    )
    custody = build_research_universe_membership_custody(
        session_date=manifest.session_date,
        represented_session_close_at=represented_close,
        methodology_version=manifest.methodology_version,
        membership_partition_path=target.relative_to(root).as_posix(),
        membership_manifest_sha256=artifacts[0].sha256,
        membership_parquet_sha256=artifacts[1].sha256,
        membership_logical_fingerprint=manifest.logical_fingerprint,
        record_count=manifest.record_count,
        evaluated_base_count=manifest.evaluated_base_count,
        origin=manifest.origin,
        source_fingerprints=manifest.source_fingerprints,
        source_data_cutoff=manifest.source_data_cutoff,
        evaluated_at=manifest.evaluated_at,
        created_at=created_at,
    )
    custody_bytes = _canonical_json_bytes(custody.model_dump(mode="json"))
    values: dict[str, object] = {
        "created_at": created_at,
        "data_root": str(root),
        "candidate_membership_partition": str(candidate),
        "target_membership_partition": str(target),
        "artifacts": artifacts,
        "custody": custody,
        "custody_bytes": len(custody_bytes),
        "custody_sha256": _bytes_sha256(custody_bytes),
        "inventory_change_bytes": sum(item.size for item in artifacts)
        + len(custody_bytes),
    }
    plan = build_plan_contract(**values)
    written = _write_plan(plan, plan_path)
    return read_research_universe_membership_apply_plan(
        plan_path=written,
        approved_plan_sha256=_file_sha256(written),
    )


def read_research_universe_membership_apply_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str | None = None,
    allow_completed_target: bool = False,
) -> ResearchUniverseMembershipApplyPlanEvidence:
    """Revalidate plan bytes, candidate bytes, target, and custody marker."""

    path = _validated_plan_file(plan_path)
    plan_sha = _file_sha256(path)
    if approved_plan_sha256 is not None and plan_sha != approved_plan_sha256:
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership Apply-plan SHA-256 differs"
        )
    try:
        plan = ResearchUniverseMembershipApplyPlanV1.model_validate_json(
            path.read_bytes()
        )
    except Exception as exc:
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership Apply-plan contract is invalid"
        ) from exc
    root = _validated_data_root(Path(plan.data_root))
    candidate = Path(plan.candidate_membership_partition)
    manifest_path = candidate / MANIFEST_FILE_NAME
    parquet_path = candidate / PARQUET_FILE_NAME
    manifest = _read_manifest(manifest_path)
    target = research_membership_partition(
        root,
        methodology_version=manifest.methodology_version,
        session_date=manifest.session_date,
    )
    if Path(plan.target_membership_partition) != target:
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership target path differs"
        )
    expected_artifacts = (
        _artifact(
            file_name=MANIFEST_FILE_NAME,
            source=manifest_path,
            target=target / MANIFEST_FILE_NAME,
        ),
        _artifact(
            file_name=PARQUET_FILE_NAME,
            source=parquet_path,
            target=target / PARQUET_FILE_NAME,
        ),
    )
    if expected_artifacts != plan.artifacts:
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership candidate bytes changed after planning"
        )
    custody_bytes = _canonical_json_bytes(plan.custody.model_dump(mode="json"))
    if (
        len(custody_bytes) != plan.custody_bytes
        or _bytes_sha256(custody_bytes) != plan.custody_sha256
        or plan.custody.membership_logical_fingerprint
        != manifest.logical_fingerprint
        or plan.custody.source_fingerprints != manifest.source_fingerprints
        or plan.custody.source_data_cutoff != manifest.source_data_cutoff
        or plan.custody.evaluated_at != manifest.evaluated_at
    ):
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership custody changed after planning"
        )
    if os.path.lexists(target):
        if not allow_completed_target:
            raise ResearchUniverseMembershipApplyPlanError(
                "research Membership target is no longer absent"
            )
        try:
            completed = read_canonical_research_universe_membership(
                data_root=root,
                methodology_version=manifest.methodology_version,
                session_date=manifest.session_date,
                expected_custody_fingerprint=plan.custody.logical_fingerprint,
            )
        except CanonicalResearchUniverseMembershipError as exc:
            raise ResearchUniverseMembershipApplyPlanError(
                "existing research Membership target differs"
            ) from exc
        if completed.custody_sha256 != plan.custody_sha256:
            raise ResearchUniverseMembershipApplyPlanError(
                "existing research Membership custody bytes differ"
            )
    else:
        _require_absent_target(root, target)
    return ResearchUniverseMembershipApplyPlanEvidence(
        plan=plan,
        plan_path=path,
        plan_sha256=plan_sha,
    )


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership data root is not the approved Dell root"
        )
    return resolved


def _read_manifest(path: Path) -> UniverseMembershipPartitionManifestV1:
    if path.is_symlink() or not path.is_file():
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership candidate manifest is unavailable"
        )
    try:
        return UniverseMembershipPartitionManifestV1.model_validate_json(
            path.read_bytes()
        )
    except Exception as exc:
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership candidate manifest is invalid"
        ) from exc


def _artifact(
    *,
    file_name: str,
    source: Path,
    target: Path,
) -> ResearchUniverseMembershipPlanArtifactV1:
    if source.is_symlink() or not source.is_file():
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership candidate artifact is unavailable"
        )
    metadata = source.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership candidate artifact is not regular"
        )
    return ResearchUniverseMembershipPlanArtifactV1(
        file_name=file_name,
        source_path=str(source),
        target_path=str(target),
        size=metadata.st_size,
        sha256=_file_sha256(source),
    )


def _require_absent_target(root: Path, target: Path) -> None:
    _reject_symlink_chain(root, target)
    if os.path.lexists(target):
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership target is no longer absent"
        )


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership path escaped data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise ResearchUniverseMembershipApplyPlanError(
                "research Membership path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _write_plan(plan: ResearchUniverseMembershipApplyPlanV1, path: Path) -> Path:
    _validate_plan_location(path)
    if os.path.lexists(path):
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership Apply plan must use a new path"
        )
    payload = _canonical_json_bytes(plan.model_dump(mode="json"))
    staging = path.with_name(f".{path.name}.staging")
    if os.path.lexists(staging):
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership plan staging residue requires diagnosis"
        )
    descriptor = os.open(
        staging,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o600,
    )
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise ResearchUniverseMembershipApplyPlanError(
                    "research Membership plan staging write did not progress"
                )
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.link(staging, path, follow_symlinks=False)
    os.unlink(staging)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return path


def _validated_plan_file(path: Path) -> Path:
    _validate_plan_location(path)
    if path.is_symlink() or not path.is_file():
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership Apply plan is unavailable"
        )
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership Apply plan must be owner-only"
        )
    return path


def _validate_plan_location(path: Path) -> None:
    try:
        validate_offline_artifact_location(
            path,
            persistent_names={PLAN_FILE_NAME},
            allow_tmp_descendants=True,
        )
    except OfflineArtifactCustodyError as exc:
        raise ResearchUniverseMembershipApplyPlanError(
            "research Membership Apply plan is outside governed custody"
        ) from exc


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
