"""Inventory-bound no-write planning for signal-eligible Membership."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.data_governance.v1 import PointInTimeEligibility
from tip_api.contracts.market_data.v1 import (
    UniverseMembershipApplyPlanV1,
    UniverseMembershipPartitionManifestV1,
    UniverseMembershipPlanArtifactV1,
    build_universe_membership_apply_plan as build_apply_plan_contract,
    build_universe_membership_canonical_publication,
    universe_membership_candidate_inventory_fingerprint,
)
from tip_api.persistence.parquet.historical_research import (
    MANIFEST_FILE_NAME,
    PARQUET_FILE_NAME,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.universe_membership_knowledge_time import (
    assess_universe_membership_knowledge_time,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
PUBLICATION_DIRECTORY = "universe-membership-publications"
PUBLICATION_POLICY_ID = "next-open-v1"


class UniverseMembershipApplyPlanError(RuntimeError):
    """Raised when a Membership publication plan cannot be proven exactly."""


@dataclass(frozen=True, slots=True)
class UniverseMembershipApplyPlanEvidence:
    plan: UniverseMembershipApplyPlanV1
    plan_path: Path
    plan_sha256: str


InventoryReader = Callable[[Path], str]
RecoveryInventoryReader = Callable[[Path, tuple[Path, ...]], str]


def build_universe_membership_apply_plan(
    *,
    data_root: Path,
    candidate_root: Path,
    candidate_membership_partition: Path,
    provider: str = MASSIVE_PROVIDER_ID,
    assessed_at: datetime,
    created_at: datetime,
    plan_path: Path,
    inventory_reader: InventoryReader = inventory_fingerprint,
) -> UniverseMembershipApplyPlanEvidence:
    """Build and formally reread one plan without touching canonical data."""

    if provider != MASSIVE_PROVIDER_ID:
        raise UniverseMembershipApplyPlanError(
            "Membership Apply plan requires the canonical provider"
        )
    canonical_root = _validated_data_root(data_root)
    assessed_at = normalize_utc_datetime(assessed_at)
    created_at = normalize_utc_datetime(created_at)
    if created_at < assessed_at:
        raise UniverseMembershipApplyPlanError(
            "Apply-plan creation cannot precede its timing assessment"
        )
    assessment = assess_universe_membership_knowledge_time(
        data_root=canonical_root,
        membership_root=candidate_root,
        membership_partition_path=candidate_membership_partition,
        provider=provider,
        assessed_at=assessed_at,
    )
    if assessment.point_in_time_eligibility is not PointInTimeEligibility.SIGNAL_ELIGIBLE:
        raise UniverseMembershipApplyPlanError(
            "only signal-eligible Membership may receive an Apply plan"
        )

    candidate_partition = candidate_membership_partition.resolve(strict=True)
    manifest_path = candidate_partition / MANIFEST_FILE_NAME
    parquet_path = candidate_partition / PARQUET_FILE_NAME
    manifest = _read_membership_manifest(manifest_path)
    _validate_assessment_manifest_binding(assessment, manifest)

    target_membership = _target_membership_partition(canonical_root, manifest)
    target_publication = _target_publication_partition(canonical_root, manifest)
    _require_absent_target(canonical_root, target_membership)
    _require_absent_target(canonical_root, target_publication)

    artifacts = (
        _artifact(
            file_name=MANIFEST_FILE_NAME,
            source=manifest_path,
            target=target_membership / MANIFEST_FILE_NAME,
        ),
        _artifact(
            file_name=PARQUET_FILE_NAME,
            source=parquet_path,
            target=target_membership / PARQUET_FILE_NAME,
        ),
    )
    publication = build_universe_membership_canonical_publication(
        session_date=manifest.session_date,
        methodology_version=manifest.methodology_version,
        membership_partition_path=target_membership.relative_to(
            canonical_root
        ).as_posix(),
        record_count=manifest.record_count,
        membership_logical_fingerprint=manifest.logical_fingerprint,
        membership_manifest_sha256=assessment.membership_manifest_sha256,
        membership_parquet_sha256=assessment.membership_parquet_sha256,
        knowledge_time_assessment=assessment,
        point_in_time_eligibility=PointInTimeEligibility.SIGNAL_ELIGIBLE,
        created_at=created_at,
    )
    publication_bytes = _canonical_json_bytes(publication.model_dump(mode="json"))
    values: dict[str, object] = {
        "created_at": created_at,
        "data_root": str(canonical_root),
        "candidate_root": str(candidate_root),
        "candidate_membership_partition": str(candidate_partition),
        "target_membership_partition": str(target_membership),
        "target_publication_partition": str(target_publication),
        "expected_current_state_fingerprint": inventory_reader(canonical_root),
        "candidate_inventory_fingerprint": (
            universe_membership_candidate_inventory_fingerprint(artifacts)
        ),
        "artifacts": artifacts,
        "publication": publication,
        "publication_manifest_bytes": len(publication_bytes),
        "publication_manifest_sha256": _bytes_sha256(publication_bytes),
        "inventory_change_file_count": 3,
        "inventory_change_bytes": sum(item.size for item in artifacts)
        + len(publication_bytes),
        "target_absent_partition_count": 2,
        "candidate_formal_read_complete": True,
        "target_absence_verified": True,
        "current_inventory_bound": True,
        "knowledge_time_signal_eligible": True,
        "external_request_count": 0,
        "canonical_data_write_count": 0,
        "apply_authorized": False,
        "historical_coverage_authorized": False,
        "research_performance_authorized": False,
    }
    plan = build_apply_plan_contract(**values)
    written_path = _write_plan(plan, plan_path)
    return read_universe_membership_apply_plan(
        plan_path=written_path,
        approved_plan_sha256=_file_sha256(written_path),
        inventory_reader=inventory_reader,
    )


def read_universe_membership_apply_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str | None = None,
    verify_then_complete: bool = False,
    inventory_reader: InventoryReader = inventory_fingerprint,
    recovery_inventory_reader: RecoveryInventoryReader | None = None,
) -> UniverseMembershipApplyPlanEvidence:
    """Revalidate the plan, source bytes, timing gate, targets, and CAS state."""

    path = _validated_plan_file(plan_path)
    plan_sha = _file_sha256(path)
    if approved_plan_sha256 is not None and plan_sha != approved_plan_sha256:
        raise UniverseMembershipApplyPlanError("Membership Apply-plan SHA-256 differs")
    try:
        plan = UniverseMembershipApplyPlanV1.model_validate_json(path.read_bytes())
    except Exception as exc:
        raise UniverseMembershipApplyPlanError(
            "Membership Apply-plan contract is invalid"
        ) from exc
    canonical_root = _validated_data_root(Path(plan.data_root))
    assessment = assess_universe_membership_knowledge_time(
        data_root=canonical_root,
        membership_root=Path(plan.candidate_root),
        membership_partition_path=Path(plan.candidate_membership_partition),
        provider=MASSIVE_PROVIDER_ID,
        assessed_at=plan.publication.knowledge_time_assessment.assessed_at,
    )
    if assessment != plan.publication.knowledge_time_assessment:
        raise UniverseMembershipApplyPlanError(
            "Membership timing assessment changed after planning"
        )
    manifest_path = Path(plan.candidate_membership_partition) / MANIFEST_FILE_NAME
    parquet_path = Path(plan.candidate_membership_partition) / PARQUET_FILE_NAME
    manifest = _read_membership_manifest(manifest_path)
    _validate_assessment_manifest_binding(assessment, manifest)
    target_membership = _target_membership_partition(canonical_root, manifest)
    target_publication = _target_publication_partition(canonical_root, manifest)
    if (
        Path(plan.target_membership_partition) != target_membership
        or Path(plan.target_publication_partition) != target_publication
    ):
        raise UniverseMembershipApplyPlanError(
            "Membership Apply-plan target paths differ"
        )
    expected_artifacts = (
        _artifact(
            file_name=MANIFEST_FILE_NAME,
            source=manifest_path,
            target=target_membership / MANIFEST_FILE_NAME,
        ),
        _artifact(
            file_name=PARQUET_FILE_NAME,
            source=parquet_path,
            target=target_membership / PARQUET_FILE_NAME,
        ),
    )
    if expected_artifacts != plan.artifacts:
        raise UniverseMembershipApplyPlanError(
            "Membership candidate bytes changed after planning"
        )
    publication_values = plan.publication.model_dump(
        mode="python",
        exclude={"logical_fingerprint"},
    )
    publication_values["knowledge_time_assessment"] = (
        plan.publication.knowledge_time_assessment
    )
    expected_publication = build_universe_membership_canonical_publication(
        **publication_values
    )
    publication_bytes = _canonical_json_bytes(
        expected_publication.model_dump(mode="json")
    )
    if (
        expected_publication != plan.publication
        or len(publication_bytes) != plan.publication_manifest_bytes
        or _bytes_sha256(publication_bytes) != plan.publication_manifest_sha256
    ):
        raise UniverseMembershipApplyPlanError(
            "Membership publication marker changed after planning"
        )
    if verify_then_complete:
        _require_recoverable_targets(
            canonical_root,
            target_membership,
            target_publication,
        )
        recovery_reader = (
            recovery_inventory_reader
            if recovery_inventory_reader is not None
            else _recovery_inventory_fingerprint
        )
        current_inventory = recovery_reader(
            canonical_root,
            _recovery_excluded_paths(plan),
        )
    else:
        _require_absent_target(canonical_root, target_membership)
        _require_absent_target(canonical_root, target_publication)
        current_inventory = inventory_reader(canonical_root)
    if current_inventory != plan.expected_current_state_fingerprint:
        raise UniverseMembershipApplyPlanError(
            "canonical inventory changed after Membership planning"
        )
    return UniverseMembershipApplyPlanEvidence(
        plan=plan,
        plan_path=path,
        plan_sha256=plan_sha,
    )


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise UniverseMembershipApplyPlanError("canonical data root is unavailable")
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise UniverseMembershipApplyPlanError(
            "canonical data root is not the approved Dell root"
        )
    return resolved


def _target_membership_partition(
    root: Path,
    manifest: UniverseMembershipPartitionManifestV1,
) -> Path:
    return (
        root
        / "market-data"
        / "universe-membership"
        / "schema_version=1"
        / f"methodology_version={_safe_segment(manifest.methodology_version)}"
        / f"session_date={manifest.session_date.isoformat()}"
    )


def _target_publication_partition(
    root: Path,
    manifest: UniverseMembershipPartitionManifestV1,
) -> Path:
    return (
        root
        / "market-data"
        / PUBLICATION_DIRECTORY
        / "schema_version=1"
        / f"policy_id={PUBLICATION_POLICY_ID}"
        / f"methodology_version={_safe_segment(manifest.methodology_version)}"
        / f"session_date={manifest.session_date.isoformat()}"
    )


def _require_absent_target(root: Path, target: Path) -> None:
    _reject_symlink_chain(root, target)
    if os.path.lexists(target):
        raise UniverseMembershipApplyPlanError(
            "Membership Apply target is no longer absent"
        )


def _require_recoverable_targets(
    root: Path,
    membership: Path,
    publication: Path,
) -> None:
    for target in (membership, publication):
        _reject_symlink_chain(root, target)
        if os.path.lexists(target) and (
            target.is_symlink() or not target.is_dir()
        ):
            raise UniverseMembershipApplyPlanError(
                "Membership recovery target is unsafe"
            )
    if os.path.lexists(publication) and not os.path.lexists(membership):
        raise UniverseMembershipApplyPlanError(
            "Membership publication marker exists without physical Membership"
        )


def _recovery_excluded_paths(
    plan: UniverseMembershipApplyPlanV1,
) -> tuple[Path, ...]:
    membership = Path(plan.target_membership_partition)
    publication = Path(plan.target_publication_partition)
    suffix = plan.logical_fingerprint[:16]
    return (
        membership,
        publication,
        membership.parent / f".{membership.name}.staging.{suffix}",
        publication.parent / f".{publication.name}.staging.{suffix}",
    )


def _recovery_inventory_fingerprint(
    root: Path,
    targets: tuple[Path, ...],
) -> str:
    return inventory_fingerprint(root, exclude_prefixes=targets)


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise UniverseMembershipApplyPlanError("Membership path escaped data root")
    current = target
    while True:
        if current.is_symlink():
            raise UniverseMembershipApplyPlanError("Membership path contains a symlink")
        if current == root:
            return
        current = current.parent


def _read_membership_manifest(path: Path) -> UniverseMembershipPartitionManifestV1:
    if path.is_symlink() or not path.is_file():
        raise UniverseMembershipApplyPlanError("Membership manifest is unavailable")
    try:
        return UniverseMembershipPartitionManifestV1.model_validate_json(
            path.read_bytes()
        )
    except Exception as exc:
        raise UniverseMembershipApplyPlanError(
            "Membership manifest contract is invalid"
        ) from exc


def _validate_assessment_manifest_binding(assessment, manifest) -> None:
    if (
        assessment.session_date != manifest.session_date
        or assessment.methodology_version != manifest.methodology_version
        or assessment.membership_logical_fingerprint != manifest.logical_fingerprint
        or assessment.membership_parquet_sha256 != manifest.physical_sha256
    ):
        raise UniverseMembershipApplyPlanError(
            "Membership timing assessment and manifest differ"
        )


def _artifact(
    *,
    file_name: str,
    source: Path,
    target: Path,
) -> UniverseMembershipPlanArtifactV1:
    if source.is_symlink() or not source.is_file():
        raise UniverseMembershipApplyPlanError(
            "Membership candidate artifact is unavailable"
        )
    metadata = source.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise UniverseMembershipApplyPlanError(
            "Membership candidate artifact is not regular"
        )
    return UniverseMembershipPlanArtifactV1(
        file_name=file_name,
        source_path=str(source),
        target_path=str(target),
        size=metadata.st_size,
        sha256=_file_sha256(source),
    )


def _write_plan(plan: UniverseMembershipApplyPlanV1, path: Path) -> Path:
    if not _is_safe_tmp_plan_path(path) or os.path.lexists(path):
        raise UniverseMembershipApplyPlanError(
            "Membership Apply plan must be a new safe path below /tmp"
        )
    payload = _canonical_json_bytes(plan.model_dump(mode="json"))
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    path.chmod(0o600)
    return path


def _validated_plan_file(path: Path) -> Path:
    if (
        not _is_safe_tmp_plan_path(path)
        or path.is_symlink()
        or not path.is_file()
    ):
        raise UniverseMembershipApplyPlanError("Membership Apply plan is unsafe")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise UniverseMembershipApplyPlanError(
            "Membership Apply plan must be owner-only"
        )
    return path


def _is_safe_tmp_plan_path(path: Path) -> bool:
    temporary_root = Path("/tmp").resolve(strict=True)
    if not path.is_absolute() or temporary_root not in path.parents:
        return False
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir() or parent.resolve(strict=True) != parent:
        return False
    current = parent
    while current != temporary_root:
        if current.is_symlink():
            return False
        current = current.parent
    return True


def _safe_segment(value: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
    if not value or any(character not in allowed for character in value):
        raise UniverseMembershipApplyPlanError(
            "Membership methodology path component is unsafe"
        )
    return value


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
