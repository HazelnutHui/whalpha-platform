"""Build an inventory-bound plan for canonical split-adjustment publication."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    CanonicalSplitAdjustmentApplyPlanV1,
    CanonicalSplitAdjustmentPlanArtifactV1,
    build_canonical_split_adjustment_apply_plan,
)
from tip_api.persistence.parquet.canonical_split_adjustment import (
    MANIFEST_FILE,
    PARQUET_FILE,
    CanonicalSplitAdjustmentPersistenceError,
    CanonicalSplitAdjustmentPublicationRead,
    read_canonical_split_adjustment_candidate,
)
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.canonical_split_adjustment_candidate import (
    CanonicalSplitAdjustmentCandidateError,
    build_canonical_split_adjustment_candidate,
)


CONTRACT_VERSION = "canonical-split-adjustment-apply-plan/1.0"
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
MAXIMUM_PLAN_BYTES = 16 * 1024 * 1024


class CanonicalSplitAdjustmentPublicationPlanError(RuntimeError):
    """Raised when the split-adjustment publication plan cannot be trusted."""


@dataclass(frozen=True, slots=True)
class CanonicalSplitAdjustmentPublicationPlanEvidence:
    plan_path: Path
    plan: CanonicalSplitAdjustmentApplyPlanV1
    plan_sha256: str
    candidate_publication: CanonicalSplitAdjustmentPublicationRead


InventoryReader = Callable[[Path], str]


def build_canonical_split_adjustment_publication_plan(
    *,
    data_root: Path,
    candidate_root: Path,
    plan_path: Path,
    planner_source_revision: str,
    created_at: datetime,
    inventory_reader: InventoryReader = inventory_fingerprint,
) -> CanonicalSplitAdjustmentPublicationPlanEvidence:
    """Bind one exact owner-only candidate to an absent canonical target."""

    with _network_prohibited():
        root = _validated_data_root(data_root)
        created_at = normalize_utc_datetime(created_at)
        candidate_target = _validated_tmp_target(candidate_root)
        plan_target = _validated_tmp_file_target(plan_path)
        candidate = _read_and_rederive_candidate(root, candidate_target)
        publication = candidate.publication
        if created_at < publication.calculated_at:
            raise CanonicalSplitAdjustmentPublicationPlanError(
                "split-adjustment plan precedes candidate calculation"
            )
        target_root = (
            root
            / "market-data"
            / "adjustment-ledger"
            / "schema_version=1"
            / f"methodology_version={publication.methodology_version}"
            / f"basis_session={publication.basis_session.isoformat()}"
            / f"coverage_id={publication.logical_fingerprint}"
        )
        if os.path.lexists(target_root):
            raise CanonicalSplitAdjustmentPublicationPlanError(
                "canonical split-adjustment target already exists"
            )
        artifacts = tuple(
            CanonicalSplitAdjustmentPlanArtifactV1(
                file_name=file_name,
                source_path=str(candidate_target / file_name),
                target_path=str(target_root / file_name),
                size=(candidate_target / file_name).stat().st_size,
                sha256=_file_sha256(candidate_target / file_name),
            )
            for file_name in (PARQUET_FILE, MANIFEST_FILE)
        )
        plan = build_canonical_split_adjustment_apply_plan(
            contract_version=CONTRACT_VERSION,
            operation="publish_canonical_split_adjustment",
            status="ready_for_separate_review",
            planner_source_revision=planner_source_revision,
            created_at=created_at,
            data_root=str(root),
            candidate_root=str(candidate_target),
            target_publication_root=str(target_root),
            expected_current_state_fingerprint=inventory_reader(root),
            artifacts=artifacts,
            publication=publication,
            inventory_change_file_count=2,
            inventory_change_bytes=sum(item.size for item in artifacts),
            target_absent_count=1,
            external_request_count=0,
            overwritten_file_count=0,
            deleted_file_count=0,
            apply_authorized=False,
            absent_row_neutrality_authorized=False,
            total_return_adjustment_authorized=False,
            full_adjustment_coverage_authorized=False,
            historical_coverage_authorized=False,
            research_performance_authorized=False,
        )
        _write_plan(plan_target, plan)
        return read_canonical_split_adjustment_publication_plan(
            plan_path=plan_target,
            approved_plan_sha256=_file_sha256(plan_target),
        )


def read_canonical_split_adjustment_publication_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
) -> CanonicalSplitAdjustmentPublicationPlanEvidence:
    path = _validated_existing_tmp_file(plan_path)
    raw = path.read_bytes()
    if (
        len(raw) < 1
        or len(raw) > MAXIMUM_PLAN_BYTES
        or hashlib.sha256(raw).hexdigest() != approved_plan_sha256
    ):
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "canonical split-adjustment plan bytes differ"
        )
    try:
        plan = CanonicalSplitAdjustmentApplyPlanV1.model_validate_json(raw)
    except Exception as exc:
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "canonical split-adjustment plan contract is invalid"
        ) from exc
    if raw != _pretty_json(plan.model_dump(mode="json")):
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "canonical split-adjustment plan is not canonical JSON"
        )
    root = _validated_data_root(Path(plan.data_root))
    candidate = _read_and_rederive_candidate(root, Path(plan.candidate_root))
    if candidate.publication != plan.publication:
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "canonical split-adjustment plan publication differs"
        )
    for artifact in plan.artifacts:
        source = Path(artifact.source_path)
        if (
            source.is_symlink()
            or not source.is_file()
            or stat.S_IMODE(source.stat().st_mode) != 0o400
            or source.stat().st_uid != os.getuid()
            or source.stat().st_size != artifact.size
            or _file_sha256(source) != artifact.sha256
        ):
            raise CanonicalSplitAdjustmentPublicationPlanError(
                "canonical split-adjustment plan artifact differs"
            )
    return CanonicalSplitAdjustmentPublicationPlanEvidence(
        plan_path=path,
        plan=plan,
        plan_sha256=approved_plan_sha256,
        candidate_publication=candidate,
    )


def _read_and_rederive_candidate(
    root: Path,
    candidate_root: Path,
) -> CanonicalSplitAdjustmentPublicationRead:
    try:
        current = read_canonical_split_adjustment_candidate(
            output_root=candidate_root
        )
        publication = current.publication
        rebuilt = build_canonical_split_adjustment_candidate(
            data_root=root,
            canonical_action_publication_root=Path(
                publication.canonical_action_publication_path
            ).parent,
            eod_evidence_path=Path(publication.eod_evidence_path),
            output_root=candidate_root,
            source_revision=publication.source_revision,
            calculated_at=publication.calculated_at,
        )
    except (
        CanonicalSplitAdjustmentPersistenceError,
        CanonicalSplitAdjustmentCandidateError,
    ) as exc:
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "split-adjustment candidate failed exact rederivation"
        ) from exc
    if (
        rebuilt.status != "already_present"
        or rebuilt.publication != current
    ):
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "split-adjustment candidate rederivation differs"
        )
    return current


def _write_plan(
    path: Path,
    plan: CanonicalSplitAdjustmentApplyPlanV1,
) -> None:
    payload = _pretty_json(plan.model_dump(mode="json"))
    if path.exists() or path.is_symlink():
        if (
            path.is_symlink()
            or not path.is_file()
            or stat.S_IMODE(path.stat().st_mode) != 0o400
            or path.stat().st_uid != os.getuid()
            or path.read_bytes() != payload
        ):
            raise CanonicalSplitAdjustmentPublicationPlanError(
                "existing canonical split-adjustment plan differs"
            )
        return
    temporary = path.parent / f".{path.name}.tmp.{os.getpid()}"
    descriptor = os.open(
        temporary,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o400,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise CanonicalSplitAdjustmentPublicationPlanError(
                    "canonical split-adjustment plan write was incomplete"
                )
            view = view[written:]
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.replace(path)
    _fsync_directory(path.parent)


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "canonical split-adjustment data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "canonical split-adjustment data root is not approved"
        )
    return resolved


def _validated_tmp_target(path: Path) -> Path:
    target = path.absolute()
    tmp = Path("/tmp").resolve(strict=True)
    if target == tmp or tmp not in target.parents:
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "split-adjustment publication input must be below /tmp"
        )
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "split-adjustment publication input parent is unsafe"
        )
    return target


def _validated_tmp_file_target(path: Path) -> Path:
    target = _validated_tmp_target(path)
    if target.exists() and (target.is_symlink() or not target.is_file()):
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "canonical split-adjustment plan target is unsafe"
        )
    return target


def _validated_existing_tmp_file(path: Path) -> Path:
    target = _validated_tmp_file_target(path)
    if (
        target.is_symlink()
        or not target.is_file()
        or stat.S_IMODE(target.stat().st_mode) != 0o400
        or target.stat().st_uid != os.getuid()
    ):
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "canonical split-adjustment plan is unavailable"
        )
    return target


def _pretty_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise CanonicalSplitAdjustmentPublicationPlanError(
            "network is prohibited while planning canonical split adjustments"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
