"""Inventory-bound planning for bounded corporate-action source publication."""

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
from tip_api.contracts.market_data.v1 import (
    CorporateActionSourceApplyPlanV1,
    CorporateActionSourceObservationEvidenceV1,
    CorporateActionSourcePlanArtifactV1,
    CorporateActionSourcePublicationArtifactV1,
    build_corporate_action_source_apply_plan as build_plan_contract,
    build_corporate_action_source_publication,
    corporate_action_source_candidate_inventory_fingerprint,
    corporate_action_source_publication_bytes,
)
from tip_api.persistence.parquet.historical_coverage import (
    ParquetHistoricalCoverageRepository,
)
from tip_api.persistence.parquet.historical_research import (
    MANIFEST_FILE_NAME,
    PARQUET_FILE_NAME,
)
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.historical_corporate_action_repeat_diff import (
    CorporateActionSourceRepeatDiffResult,
    read_historical_corporate_action_repeat_diff,
)
from tip_api.services.historical_corporate_action_resolution_shadow import (
    CorporateActionResolutionShadowWriteResult,
    read_historical_corporate_action_resolution_shadow,
)
from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    validate_offline_artifact_location,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
PUBLICATION_DIRECTORY = "provider-corporate-action-observation-publications"
MAXIMUM_PLAN_BYTES = 16 * 1024 * 1024


class CorporateActionSourcePublicationPlanError(RuntimeError):
    """Raised when a source-observation publication plan cannot be proven."""


@dataclass(frozen=True, slots=True)
class CorporateActionSourcePublicationPlanEvidence:
    plan: CorporateActionSourceApplyPlanV1
    plan_path: Path
    plan_sha256: str


InventoryReader = Callable[[Path], str]
RecoveryInventoryReader = Callable[[Path, tuple[Path, ...]], str]


def build_corporate_action_source_publication_plan(
    *,
    data_root: Path,
    resolution_shadow_root: Path,
    split_repeat_diff_root: Path,
    dividend_repeat_diff_root: Path,
    source_revision: str,
    created_at: datetime,
    plan_path: Path,
    inventory_reader: InventoryReader = inventory_fingerprint,
) -> CorporateActionSourcePublicationPlanEvidence:
    """Build and formally reread one no-write publication plan."""

    root = _validated_data_root(data_root)
    created_at = normalize_utc_datetime(created_at)
    shadow = read_historical_corporate_action_resolution_shadow(
        output_root=resolution_shadow_root
    )
    split_diff = read_historical_corporate_action_repeat_diff(
        output_root=split_repeat_diff_root
    )
    dividend_diff = read_historical_corporate_action_repeat_diff(
        output_root=dividend_repeat_diff_root
    )
    _validate_source_evidence(
        shadow=shadow,
        split_diff=split_diff,
        dividend_diff=dividend_diff,
        created_at=created_at,
    )
    identity = ParquetHistoricalCoverageRepository(root).read_dataset_evidence(
        root / shadow.manifest.identity_evidence_path
    )
    if (
        identity.physical_sha256 != shadow.manifest.identity_evidence_sha256
        or identity.evidence.logical_fingerprint
        != shadow.manifest.identity_evidence_logical_fingerprint
        or len(identity.evidence.sessions) != shadow.manifest.identity_session_count
        or identity.evidence.sessions[0] != shadow.manifest.start_date
        or identity.evidence.sessions[-1] != shadow.manifest.end_date
    ):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action Identity evidence binding differs"
        )

    publication_artifacts: list[CorporateActionSourcePublicationArtifactV1] = []
    plan_artifacts: list[CorporateActionSourcePlanArtifactV1] = []
    target_partitions: list[str] = []
    for item in shadow.manifest.artifacts:
        source_partition = shadow.output_root / item.partition_path
        target_partition = root / item.partition_path
        _require_absent_target(root, target_partition)
        target_partitions.append(str(target_partition))
        manifest_path = source_partition / MANIFEST_FILE_NAME
        parquet_path = source_partition / PARQUET_FILE_NAME
        publication_artifacts.append(
            CorporateActionSourcePublicationArtifactV1(
                event_year=item.event_year,
                partition_path=item.partition_path,
                record_count=item.record_count,
                logical_fingerprint=item.logical_fingerprint,
                manifest_sha256=item.manifest_sha256,
                manifest_bytes=manifest_path.stat().st_size,
                parquet_sha256=item.parquet_sha256,
                parquet_bytes=item.parquet_bytes,
            )
        )
        for file_name, source in (
            (MANIFEST_FILE_NAME, manifest_path),
            (PARQUET_FILE_NAME, parquet_path),
        ):
            plan_artifacts.append(
                _artifact(
                    event_year=item.event_year,
                    file_name=file_name,
                    source=source,
                    target=target_partition / file_name,
                )
            )

    publication = build_corporate_action_source_publication(
        source_revision=source_revision,
        start_date=shadow.manifest.start_date,
        end_date=shadow.manifest.end_date,
        source_observations=(
            _observation_evidence(split_diff),
            _observation_evidence(dividend_diff),
        ),
        identity_evidence_path=shadow.manifest.identity_evidence_path,
        identity_evidence_sha256=shadow.manifest.identity_evidence_sha256,
        identity_evidence_logical_fingerprint=(
            shadow.manifest.identity_evidence_logical_fingerprint
        ),
        identity_session_count=shadow.manifest.identity_session_count,
        resolution_shadow_manifest_sha256=shadow.manifest_sha256,
        resolution_shadow_logical_fingerprint=shadow.manifest.logical_fingerprint,
        source_record_count=shadow.manifest.source_record_count,
        resolved_record_count=_count(shadow.manifest.resolution_status_counts, "resolved"),
        quarantined_record_count=_count(
            shadow.manifest.record_status_counts, "quarantined"
        ),
        artifacts=tuple(publication_artifacts),
        created_at=created_at,
    )
    publication_bytes = corporate_action_source_publication_bytes(publication)
    target_publication = (
        root
        / "market-data"
        / PUBLICATION_DIRECTORY
        / "schema_version=1"
        / f"provider_id={publication.provider_id}"
        / f"coverage_id={publication.logical_fingerprint}"
    )
    _require_absent_target(root, target_publication)
    artifacts = tuple(plan_artifacts)
    values: dict[str, object] = {
        "created_at": created_at,
        "data_root": str(root),
        "resolution_shadow_root": str(shadow.output_root),
        "split_repeat_diff_root": str(split_diff.output_root),
        "dividend_repeat_diff_root": str(dividend_diff.output_root),
        "target_partition_paths": tuple(sorted(target_partitions)),
        "target_publication_partition": str(target_publication),
        "expected_current_state_fingerprint": inventory_reader(root),
        "candidate_inventory_fingerprint": (
            corporate_action_source_candidate_inventory_fingerprint(artifacts)
        ),
        "artifacts": artifacts,
        "publication": publication,
        "publication_manifest_bytes": len(publication_bytes),
        "publication_manifest_sha256": _bytes_sha256(publication_bytes),
        "inventory_change_file_count": len(artifacts) + 1,
        "inventory_change_bytes": sum(item.size for item in artifacts)
        + len(publication_bytes),
        "target_absent_partition_count": len(target_partitions) + 1,
        "candidate_formal_read_complete": True,
        "repeat_diff_formal_read_complete": True,
        "target_absence_verified": True,
        "current_inventory_bound": True,
        "external_request_count": 0,
        "canonical_data_write_count": 0,
        "apply_authorized": False,
        "canonical_corporate_action_authorized": False,
        "adjustment_ledger_authorized": False,
        "historical_coverage_authorized": False,
        "research_performance_authorized": False,
    }
    plan = build_plan_contract(**values)
    written = _write_plan(plan, plan_path)
    return read_corporate_action_source_publication_plan(
        plan_path=written,
        approved_plan_sha256=_file_sha256(written),
        inventory_reader=inventory_reader,
    )


def read_corporate_action_source_publication_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str | None = None,
    verify_then_complete: bool = False,
    inventory_reader: InventoryReader = inventory_fingerprint,
    recovery_inventory_reader: RecoveryInventoryReader | None = None,
) -> CorporateActionSourcePublicationPlanEvidence:
    """Reread every input byte, exact target state, and inventory binding."""

    path = _validated_plan_file(plan_path)
    plan_sha = _file_sha256(path)
    if approved_plan_sha256 is not None and plan_sha != approved_plan_sha256:
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action publication plan SHA-256 differs"
        )
    try:
        plan = CorporateActionSourceApplyPlanV1.model_validate_json(path.read_bytes())
    except Exception as exc:
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action publication plan contract is invalid"
        ) from exc
    root = _validated_data_root(Path(plan.data_root))
    shadow = read_historical_corporate_action_resolution_shadow(
        output_root=Path(plan.resolution_shadow_root)
    )
    split_diff = read_historical_corporate_action_repeat_diff(
        output_root=Path(plan.split_repeat_diff_root)
    )
    dividend_diff = read_historical_corporate_action_repeat_diff(
        output_root=Path(plan.dividend_repeat_diff_root)
    )
    _validate_source_evidence(
        shadow=shadow,
        split_diff=split_diff,
        dividend_diff=dividend_diff,
        created_at=plan.created_at,
    )
    identity = ParquetHistoricalCoverageRepository(root).read_dataset_evidence(
        root / shadow.manifest.identity_evidence_path
    )
    if (
        identity.physical_sha256 != plan.publication.identity_evidence_sha256
        or identity.evidence.logical_fingerprint
        != plan.publication.identity_evidence_logical_fingerprint
    ):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action plan Identity evidence changed"
        )
    expected_artifacts = _plan_artifacts(root, shadow)
    if (
        expected_artifacts != plan.artifacts
        or corporate_action_source_candidate_inventory_fingerprint(expected_artifacts)
        != plan.candidate_inventory_fingerprint
    ):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action candidate bytes changed after planning"
        )
    expected_publication = _publication_from_evidence(
        shadow=shadow,
        split_diff=split_diff,
        dividend_diff=dividend_diff,
        source_revision=plan.publication.source_revision,
        created_at=plan.created_at,
    )
    publication_bytes = corporate_action_source_publication_bytes(expected_publication)
    if (
        expected_publication != plan.publication
        or len(publication_bytes) != plan.publication_manifest_bytes
        or _bytes_sha256(publication_bytes) != plan.publication_manifest_sha256
    ):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action publication marker changed after planning"
        )
    targets = tuple(Path(item) for item in plan.target_partition_paths) + (
        Path(plan.target_publication_partition),
    )
    if verify_then_complete:
        _require_recoverable_targets(root, targets)
        reader = recovery_inventory_reader or _recovery_inventory_fingerprint
        current_inventory = reader(root, _recovery_excluded_paths(plan))
    else:
        for target in targets:
            _require_absent_target(root, target)
        current_inventory = inventory_reader(root)
    if current_inventory != plan.expected_current_state_fingerprint:
        raise CorporateActionSourcePublicationPlanError(
            "canonical inventory changed after corporate-action planning"
        )
    return CorporateActionSourcePublicationPlanEvidence(
        plan=plan,
        plan_path=path,
        plan_sha256=plan_sha,
    )


def _publication_from_evidence(
    *,
    shadow: CorporateActionResolutionShadowWriteResult,
    split_diff: CorporateActionSourceRepeatDiffResult,
    dividend_diff: CorporateActionSourceRepeatDiffResult,
    source_revision: str,
    created_at: datetime,
):
    artifacts = tuple(
        CorporateActionSourcePublicationArtifactV1(
            event_year=item.event_year,
            partition_path=item.partition_path,
            record_count=item.record_count,
            logical_fingerprint=item.logical_fingerprint,
            manifest_sha256=item.manifest_sha256,
            manifest_bytes=(
                shadow.output_root / item.partition_path / MANIFEST_FILE_NAME
            ).stat().st_size,
            parquet_sha256=item.parquet_sha256,
            parquet_bytes=item.parquet_bytes,
        )
        for item in shadow.manifest.artifacts
    )
    return build_corporate_action_source_publication(
        source_revision=source_revision,
        start_date=shadow.manifest.start_date,
        end_date=shadow.manifest.end_date,
        source_observations=(
            _observation_evidence(split_diff),
            _observation_evidence(dividend_diff),
        ),
        identity_evidence_path=shadow.manifest.identity_evidence_path,
        identity_evidence_sha256=shadow.manifest.identity_evidence_sha256,
        identity_evidence_logical_fingerprint=(
            shadow.manifest.identity_evidence_logical_fingerprint
        ),
        identity_session_count=shadow.manifest.identity_session_count,
        resolution_shadow_manifest_sha256=shadow.manifest_sha256,
        resolution_shadow_logical_fingerprint=shadow.manifest.logical_fingerprint,
        source_record_count=shadow.manifest.source_record_count,
        resolved_record_count=_count(shadow.manifest.resolution_status_counts, "resolved"),
        quarantined_record_count=_count(
            shadow.manifest.record_status_counts, "quarantined"
        ),
        artifacts=artifacts,
        created_at=created_at,
    )


def _validate_source_evidence(
    *,
    shadow: CorporateActionResolutionShadowWriteResult,
    split_diff: CorporateActionSourceRepeatDiffResult,
    dividend_diff: CorporateActionSourceRepeatDiffResult,
    created_at: datetime,
) -> None:
    if created_at < max(
        shadow.manifest.materialized_at,
        split_diff.manifest.compared_at,
        dividend_diff.manifest.compared_at,
    ):
        raise CorporateActionSourcePublicationPlanError(
            "publication plan time precedes source evidence"
        )
    pairs = (("split", split_diff), ("dividend", dividend_diff))
    for action_kind, diff in pairs:
        manifest = diff.manifest
        shadow_sha = (
            shadow.manifest.split_source_manifest_sha256
            if action_kind == "split"
            else shadow.manifest.dividend_source_manifest_sha256
        )
        shadow_logical = (
            shadow.manifest.split_source_logical_fingerprint
            if action_kind == "split"
            else shadow.manifest.dividend_source_logical_fingerprint
        )
        shadow_count = (
            shadow.manifest.split_source_record_count
            if action_kind == "split"
            else shadow.manifest.dividend_source_record_count
        )
        if (
            manifest.action_kind.value != action_kind
            or manifest.start_date != shadow.manifest.start_date
            or manifest.end_date != shadow.manifest.end_date
            or manifest.baseline_manifest_sha256 != shadow_sha
            or manifest.baseline_logical_fingerprint != shadow_logical
            or manifest.baseline_record_count != shadow_count
            or manifest.repeat_record_count != shadow_count
            or manifest.unchanged_record_count != shadow_count
            or manifest.changed_record_count != 0
            or manifest.added_record_count != 0
            or manifest.removed_record_count != 0
            or manifest.pagination_shape_changed
            or manifest.baseline_content_fingerprint
            != manifest.repeat_content_fingerprint
        ):
            raise CorporateActionSourcePublicationPlanError(
                "corporate-action repeat evidence is not an exact zero delta"
            )


def _observation_evidence(
    diff: CorporateActionSourceRepeatDiffResult,
) -> CorporateActionSourceObservationEvidenceV1:
    item = diff.manifest
    return CorporateActionSourceObservationEvidenceV1(
        action_kind=item.action_kind.value,
        baseline_manifest_sha256=item.baseline_manifest_sha256,
        baseline_logical_fingerprint=item.baseline_logical_fingerprint,
        baseline_content_fingerprint=item.baseline_content_fingerprint,
        baseline_record_count=item.baseline_record_count,
        repeat_manifest_sha256=item.repeat_manifest_sha256,
        repeat_logical_fingerprint=item.repeat_logical_fingerprint,
        repeat_content_fingerprint=item.repeat_content_fingerprint,
        repeat_diff_manifest_sha256=diff.manifest_sha256,
        repeat_diff_logical_fingerprint=item.logical_fingerprint,
        baseline_completed_at=item.baseline_completed_at,
        repeat_started_at=item.repeat_started_at,
        repeat_completed_at=item.repeat_completed_at,
        unchanged_record_count=item.unchanged_record_count,
        changed_record_count=item.changed_record_count,
        added_record_count=item.added_record_count,
        removed_record_count=item.removed_record_count,
        pagination_shape_changed=item.pagination_shape_changed,
    )


def _plan_artifacts(
    root: Path,
    shadow: CorporateActionResolutionShadowWriteResult,
) -> tuple[CorporateActionSourcePlanArtifactV1, ...]:
    artifacts: list[CorporateActionSourcePlanArtifactV1] = []
    for item in shadow.manifest.artifacts:
        source_partition = shadow.output_root / item.partition_path
        target_partition = root / item.partition_path
        for file_name in (MANIFEST_FILE_NAME, PARQUET_FILE_NAME):
            artifacts.append(
                _artifact(
                    event_year=item.event_year,
                    file_name=file_name,
                    source=source_partition / file_name,
                    target=target_partition / file_name,
                )
            )
    return tuple(artifacts)


def _artifact(
    *, event_year: int, file_name: str, source: Path, target: Path
) -> CorporateActionSourcePlanArtifactV1:
    if source.is_symlink() or not source.is_file():
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action source artifact is unavailable"
        )
    metadata = source.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action source artifact is not regular"
        )
    return CorporateActionSourcePlanArtifactV1(
        event_year=event_year,
        file_name=file_name,
        source_path=str(source),
        target_path=str(target),
        size=metadata.st_size,
        sha256=_file_sha256(source),
    )


def _count(values: tuple[tuple[str, int], ...], key: str) -> int:
    return dict(values).get(key, 0)


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action canonical data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action data root is not the approved Dell root"
        )
    return resolved


def _require_absent_target(root: Path, target: Path) -> None:
    _reject_symlink_chain(root, target)
    if os.path.lexists(target):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action publication target is no longer absent"
        )
    staging = target.parent / f".{target.name}.staging"
    if os.path.lexists(staging):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action publication staging residue requires diagnosis"
        )


def _require_recoverable_targets(root: Path, targets: tuple[Path, ...]) -> None:
    states = []
    for target in targets:
        _reject_symlink_chain(root, target)
        exists = os.path.lexists(target)
        if exists and (target.is_symlink() or not target.is_dir()):
            raise CorporateActionSourcePublicationPlanError(
                "corporate-action recovery target is unsafe"
            )
        states.append(exists)
    marker_exists = states[-1]
    physical = states[:-1]
    if not any(states):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action recovery requires a completed target prefix"
        )
    if marker_exists and not all(physical):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action publication marker exists before all physical partitions"
        )
    if any(physical[index] and not all(physical[: index + 1]) for index in range(len(physical))):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action recovery partition prefix is invalid"
        )


def _recovery_excluded_paths(plan: CorporateActionSourceApplyPlanV1) -> tuple[Path, ...]:
    targets = tuple(Path(item) for item in plan.target_partition_paths) + (
        Path(plan.target_publication_partition),
    )
    return tuple(
        item
        for target in targets
        for item in (
            target,
            target.parent / f".{target.name}.staging.{plan.logical_fingerprint[:16]}",
        )
    )


def _recovery_inventory_fingerprint(root: Path, targets: tuple[Path, ...]) -> str:
    return inventory_fingerprint(root, exclude_prefixes=targets)


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action path escaped the data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise CorporateActionSourcePublicationPlanError(
                "corporate-action publication path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _write_plan(plan: CorporateActionSourceApplyPlanV1, plan_path: Path) -> Path:
    try:
        path = validate_offline_artifact_location(
            plan_path, persistent_names=set(), allow_tmp_descendants=False
        )
    except OfflineArtifactCustodyError as exc:
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action plan path is outside governed custody"
        ) from exc
    if os.path.lexists(path):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action plan path already exists"
        )
    payload = _canonical_json_bytes(plan.model_dump(mode="json"))
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o400)
    try:
        os.write(descriptor, payload)
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return path


def _validated_plan_file(path: Path) -> Path:
    try:
        candidate = validate_offline_artifact_location(
            path, persistent_names=set(), allow_tmp_descendants=False
        )
    except OfflineArtifactCustodyError as exc:
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action plan path is outside governed custody"
        ) from exc
    if candidate.is_symlink() or not candidate.is_file():
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action publication plan is unavailable"
        )
    metadata = candidate.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or metadata.st_size > MAXIMUM_PLAN_BYTES
    ):
        raise CorporateActionSourcePublicationPlanError(
            "corporate-action publication plan custody differs"
        )
    return candidate


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
