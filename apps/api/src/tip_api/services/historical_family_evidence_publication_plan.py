"""Deterministic no-write planning for current EOD and Identity evidence."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from tip_api.contracts.market_data.v1 import (
    CURRENT_HISTORICAL_FAMILY_EVIDENCE_PLAN_FAMILIES,
    CurrentHistoricalFamilyEvidencePublicationPlanV1,
    build_current_historical_family_evidence_plan_item,
    build_current_historical_family_evidence_publication_plan as build_plan_contract,
    current_historical_family_evidence_plan_family_set_fingerprint,
)
from tip_api.persistence.parquet.historical_coverage import (
    HistoricalDatasetEvidenceValidationResult,
    ParquetHistoricalCoverageRepository,
)
from tip_api.services.current_historical_mechanics_evidence import (
    validate_current_historical_family_evidence,
)
from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    validate_offline_artifact_location,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
MAXIMUM_PLAN_BYTES = 16 * 1024 * 1024


class HistoricalFamilyEvidencePublicationPlanError(RuntimeError):
    """Raised when a two-family no-write plan cannot be proven exactly."""


@dataclass(frozen=True, slots=True)
class HistoricalFamilyEvidencePublicationPlanEvidence:
    plan: CurrentHistoricalFamilyEvidencePublicationPlanV1
    plan_path: Path
    plan_sha256: str
    external_request_count: int = 0
    canonical_data_write_count: int = 0
    apply_authorized: bool = False
    historical_coverage_authorized: bool = False


def build_current_historical_family_evidence_publication_plan(
    *,
    data_root: Path,
    plan_path: Path,
) -> HistoricalFamilyEvidencePublicationPlanEvidence:
    """Build one immutable `/tmp` plan without publishing canonical evidence."""

    root = _validated_data_root(data_root)
    validations = _ordered_unpublished_validations(
        validate_current_historical_family_evidence(root)
    )
    families = tuple(
        build_current_historical_family_evidence_plan_item(item.evidence)
        for item in validations
    )
    for family, validation in zip(families, validations, strict=True):
        if (
            validation.proposed_evidence_path != root / family.target_path
            or validation.physical_sha256 != family.evidence_manifest_sha256
        ):
            raise HistoricalFamilyEvidencePublicationPlanError(
                "family-evidence repository target binding differs"
            )
    sessions = families[0].evidence.sessions
    values: dict[str, object] = {
        "planned_from_evidence_at": max(
            item.evidence.created_at for item in families
        ),
        "data_root": str(root),
        "first_session": sessions[0],
        "last_session": sessions[-1],
        "session_count": len(sessions),
        "families": families,
        "family_set_fingerprint": (
            current_historical_family_evidence_plan_family_set_fingerprint(
                families
            )
        ),
        "inventory_change_file_count": 2,
        "inventory_change_bytes": sum(
            item.evidence_manifest_bytes for item in families
        ),
        "target_absent_count": 2,
        "source_formal_read_complete": True,
        "target_absence_verified": True,
        "recovery_policy": "verify_exact_then_complete",
        "external_request_count": 0,
        "canonical_data_write_count": 0,
        "apply_authorized": False,
        "historical_coverage_authorized": False,
        "research_development_authorized": False,
        "research_performance_authorized": False,
    }
    plan = build_plan_contract(**values)
    target = _write_plan(plan=plan, plan_path=plan_path)
    reread, plan_sha = _read_plan_file(target)
    if reread != plan:
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication plan changed after writing"
        )
    return HistoricalFamilyEvidencePublicationPlanEvidence(
        plan=plan,
        plan_path=target,
        plan_sha256=plan_sha,
    )


def read_current_historical_family_evidence_publication_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str | None = None,
) -> HistoricalFamilyEvidencePublicationPlanEvidence:
    """Reread the plan, every source byte, and both absent targets."""

    plan, plan_sha = _read_plan_file(plan_path)
    if approved_plan_sha256 is not None:
        _validate_sha256(approved_plan_sha256, "approved plan SHA-256")
        if plan_sha != approved_plan_sha256:
            raise HistoricalFamilyEvidencePublicationPlanError(
                "family-evidence publication plan SHA-256 differs"
            )
    root = _validated_data_root(Path(plan.data_root))
    repository = ParquetHistoricalCoverageRepository(root)
    validations = tuple(
        repository.validate_dataset_evidence(item.evidence)
        for item in plan.families
    )
    validations = _ordered_unpublished_validations(validations)
    for item, validation in zip(plan.families, validations, strict=True):
        if (
            validation.evidence != item.evidence
            or validation.proposed_evidence_path != root / item.target_path
            or validation.physical_sha256 != item.evidence_manifest_sha256
        ):
            raise HistoricalFamilyEvidencePublicationPlanError(
                "family-evidence source or target binding changed after planning"
            )
    return HistoricalFamilyEvidencePublicationPlanEvidence(
        plan=plan,
        plan_path=plan_path,
        plan_sha256=plan_sha,
    )


def _ordered_unpublished_validations(
    validations: tuple[HistoricalDatasetEvidenceValidationResult, ...],
) -> tuple[HistoricalDatasetEvidenceValidationResult, ...]:
    ordered = tuple(
        sorted(validations, key=lambda item: item.evidence.family.value)
    )
    if tuple(item.evidence.family for item in ordered) != (
        CURRENT_HISTORICAL_FAMILY_EVIDENCE_PLAN_FAMILIES
    ):
        raise HistoricalFamilyEvidencePublicationPlanError(
            "current family-evidence set is incomplete"
        )
    sessions = ordered[0].evidence.sessions
    if any(item.evidence.sessions != sessions for item in ordered[1:]):
        raise HistoricalFamilyEvidencePublicationPlanError(
            "current family-evidence session coverage differs"
        )
    if any(
        item.publication_exists or item.status != "validated_not_published"
        for item in ordered
    ):
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication target is no longer absent"
        )
    return ordered


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute():
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence data root must be absolute"
        )
    try:
        root = path.resolve(strict=True)
        approved = APPROVED_DATA_ROOT.resolve(strict=True)
    except OSError as exc:
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence data root is unavailable"
        ) from exc
    if (
        root != approved
        or root != path.absolute()
        or path.is_symlink()
        or not root.is_dir()
    ):
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence data root differs from the approved Dell root"
        )
    return root


def _write_plan(
    *,
    plan: CurrentHistoricalFamilyEvidencePublicationPlanV1,
    plan_path: Path,
) -> Path:
    _validate_plan_location(plan_path)
    if os.path.lexists(plan_path):
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication plan must use a new path"
        )
    staging = plan_path.with_name(f".{plan_path.name}.staging")
    if os.path.lexists(staging):
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication-plan staging residue requires diagnosis"
        )
    payload = _canonical_json_bytes(plan.model_dump(mode="json"))
    descriptor = os.open(
        staging,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o400,
    )
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise HistoricalFamilyEvidencePublicationPlanError(
                    "family-evidence publication-plan write did not progress"
                )
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(staging, plan_path, follow_symlinks=False)
    except FileExistsError as exc:
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication plan appeared during atomic write"
        ) from exc
    finally:
        if os.path.lexists(staging):
            os.unlink(staging)
    _fsync_directory(plan_path.parent)
    return plan_path


def _read_plan_file(
    path: Path,
) -> tuple[CurrentHistoricalFamilyEvidencePublicationPlanV1, str]:
    _validate_plan_location(path)
    staging = path.with_name(f".{path.name}.staging")
    if os.path.lexists(staging):
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication-plan staging residue requires diagnosis"
        )
    if path.is_symlink() or not path.is_file():
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication plan is unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or metadata.st_size > MAXIMUM_PLAN_BYTES
    ):
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication-plan custody differs"
        )
    raw = path.read_bytes()
    try:
        plan = CurrentHistoricalFamilyEvidencePublicationPlanV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication-plan contract is invalid"
        ) from exc
    if raw != _canonical_json_bytes(plan.model_dump(mode="json")):
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication-plan bytes are not canonical"
        )
    return plan, hashlib.sha256(raw).hexdigest()


def _validate_plan_location(path: Path) -> None:
    try:
        validate_offline_artifact_location(
            path,
            persistent_names=set(),
            allow_tmp_descendants=False,
        )
    except OfflineArtifactCustodyError as exc:
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication plan is outside direct /tmp custody"
        ) from exc
    if path.name.startswith("."):
        raise HistoricalFamilyEvidencePublicationPlanError(
            "family-evidence publication plan must be visible"
        )


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _validate_sha256(value: str, field_name: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise HistoricalFamilyEvidencePublicationPlanError(
            f"{field_name} is malformed"
        )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
