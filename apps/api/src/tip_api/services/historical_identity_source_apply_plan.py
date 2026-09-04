"""Inventory-bound, no-write planning for historical Identity source custody."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import socket
import stat
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1.historical_identity_source_apply_plan import (
    HistoricalIdentitySourceApplyPlanV1,
    HistoricalIdentitySourcePlanArtifactV1,
    HistoricalIdentitySourcePlanSessionV1,
)
from tip_api.contracts.market_data.v1.historical_identity_source_custody import (
    DATASET_NAME,
    historical_identity_source_fingerprint,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.historical_identity_rebuild_profile_map import (
    HistoricalIdentityRebuildProfileBindingV1,
    HistoricalIdentityRebuildProfileMapV1,
)
from tip_api.services.historical_identity_source_custody import (
    MANIFEST_FILE,
    PARQUET_FILE,
    read_historical_identity_source_custody_candidate,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
SCHEMA_PARTITION = "1"


class HistoricalIdentitySourceApplyPlanError(RuntimeError):
    """Fail-closed error at the no-write historical source planning boundary."""


@dataclass(frozen=True, slots=True)
class HistoricalIdentitySourceApplyPlanEvidence:
    plan: HistoricalIdentitySourceApplyPlanV1
    plan_path: Path
    plan_sha256: str


InventoryReader = Callable[[Path], str]
RecoveryInventoryReader = Callable[[Path, tuple[Path, ...]], str]


@dataclass(frozen=True, slots=True)
class _CandidatePlanSession:
    session: HistoricalIdentitySourcePlanSessionV1
    source_partition: Path


def build_historical_identity_source_apply_plan(
    *,
    data_root: Path,
    candidate_root: Path,
    profile_map: HistoricalIdentityRebuildProfileMapV1,
    created_at: datetime,
    plan_path: Path,
    workers: int = 1,
    sessions: tuple[date, ...] | None = None,
    inventory_reader: InventoryReader = inventory_fingerprint,
) -> HistoricalIdentitySourceApplyPlanEvidence:
    """Create one complete or explicit append-only no-write Apply plan."""

    canonical_root = _validated_data_root(data_root)
    source_root = _validated_candidate_root(candidate_root)
    if not 1 <= workers <= 4:
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply-plan workers must be between one and four"
        )
    created_at = normalize_utc_datetime(created_at)
    target_dataset_root = _dataset_root(canonical_root)
    seen_dates: set[object] = set()
    for binding in profile_map.bindings:
        if binding.session_date in seen_dates:
            raise HistoricalIdentitySourceApplyPlanError(
                "historical source profile map contains a duplicate session"
            )
        seen_dates.add(binding.session_date)
    selected_bindings = _selected_bindings(profile_map, sessions)
    jobs = tuple(
        (source_root, binding, profile_map.logical_fingerprint)
        for binding in selected_bindings
    )
    if workers == 1:
        candidate_rows = [_read_candidate_for_plan(job) for job in jobs]
    else:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=_disable_network_in_worker,
        ) as executor:
            candidate_rows = list(executor.map(_read_candidate_for_plan, jobs))
    candidate_rows.sort(key=lambda item: item.session.session_date)
    planned_sessions: list[HistoricalIdentitySourcePlanSessionV1] = []
    artifacts: list[HistoricalIdentitySourcePlanArtifactV1] = []
    for candidate in candidate_rows:
        session = candidate.session
        target_partition = _partition_path(
            target_dataset_root,
            session.session_date.isoformat(),
        )
        _reject_symlink_chain(canonical_root, target_partition)
        if os.path.lexists(target_partition):
            raise HistoricalIdentitySourceApplyPlanError(
                "historical source target partition is no longer absent"
            )
        manifest_path = candidate.source_partition / MANIFEST_FILE
        parquet_path = candidate.source_partition / PARQUET_FILE
        planned_sessions.append(session)
        artifacts.extend(
            (
                HistoricalIdentitySourcePlanArtifactV1(
                    session_date=session.session_date,
                    file_name=MANIFEST_FILE,
                    source_path=str(manifest_path),
                    target_path=str(target_partition / MANIFEST_FILE),
                    size=session.manifest_bytes,
                    sha256=session.manifest_sha256,
                ),
                HistoricalIdentitySourcePlanArtifactV1(
                    session_date=session.session_date,
                    file_name=PARQUET_FILE,
                    source_path=str(parquet_path),
                    target_path=str(target_partition / PARQUET_FILE),
                    size=session.parquet_bytes,
                    sha256=session.parquet_sha256,
                ),
            )
        )
    if len(planned_sessions) != len(selected_bindings):
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source candidate session count differs from selection"
        )
    session_rows = tuple(planned_sessions)
    artifact_rows = tuple(artifacts)
    dates = [item.session_date.isoformat() for item in session_rows]
    base = {
        "contract_version": "historical-identity-source-apply-plan/1.0",
        "operation": "publish_historical_identity_source_custody",
        "status": "ready_for_separate_review",
        "created_at": created_at,
        "data_root": str(canonical_root),
        "candidate_root": str(source_root),
        "target_dataset_root": str(target_dataset_root),
        "dataset_name": DATASET_NAME,
        "provider": MASSIVE_PROVIDER_ID,
        "identity_profile_map_fingerprint": profile_map.logical_fingerprint,
        "expected_current_state_fingerprint": inventory_reader(canonical_root),
        "session_index_fingerprint": historical_identity_source_fingerprint(dates),
        "candidate_inventory_fingerprint": _candidate_inventory_fingerprint(
            artifact_rows
        ),
        "first_session": session_rows[0].session_date,
        "last_session": session_rows[-1].session_date,
        "session_count": len(session_rows),
        "current_profile_session_count": sum(
            item.identity_rebuild_profile == "current_v1" for item in session_rows
        ),
        "legacy_profile_session_count": sum(
            item.identity_rebuild_profile == "pre_etv_governance_v1"
            for item in session_rows
        ),
        "record_count": sum(item.record_count for item in session_rows),
        "source_request_count": sum(
            item.source_request_count for item in session_rows
        ),
        "source_response_bytes": sum(
            item.source_response_bytes for item in session_rows
        ),
        "normalized_parquet_bytes": sum(
            item.parquet_bytes for item in session_rows
        ),
        "manifest_bytes": sum(item.manifest_bytes for item in session_rows),
        "inventory_change_file_count": len(artifact_rows),
        "inventory_change_bytes": sum(item.size for item in artifact_rows),
        "target_absent_partition_count": len(session_rows),
        "sessions": session_rows,
        "artifacts": artifact_rows,
        "candidate_formal_read_complete": True,
        "target_absence_verified": True,
        "current_inventory_bound": True,
        "external_request_count": 0,
        "canonical_data_write_count": 0,
        "universe_membership_write_count": 0,
        "apply_authorized": False,
        "historical_coverage_authorized": False,
        "research_performance_authorized": False,
    }
    plan = HistoricalIdentitySourceApplyPlanV1.model_validate(
        {
            **base,
            "logical_fingerprint": historical_identity_source_fingerprint(
                _json_ready(base)
            ),
        }
    )
    target = _write_plan(plan=plan, plan_path=plan_path)
    return read_historical_identity_source_apply_plan(
        plan_path=target,
        approved_plan_sha256=_file_sha256(target),
        inventory_reader=inventory_reader,
    )


def _selected_bindings(
    profile_map: HistoricalIdentityRebuildProfileMapV1,
    sessions: tuple[date, ...] | None,
) -> tuple[HistoricalIdentityRebuildProfileBindingV1, ...]:
    if sessions is None:
        return profile_map.bindings
    if (
        not sessions
        or sessions != tuple(sorted(sessions))
        or len(sessions) != len(set(sessions))
    ):
        raise HistoricalIdentitySourceApplyPlanError(
            "explicit sessions must be nonempty, unique, and ordered"
        )
    binding_by_session = {
        binding.session_date: binding for binding in profile_map.bindings
    }
    if set(sessions) - set(binding_by_session):
        raise HistoricalIdentitySourceApplyPlanError(
            "explicit session is not profile-bound"
        )
    return tuple(binding_by_session[session] for session in sessions)


def read_historical_identity_source_apply_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str | None = None,
    verify_then_complete: bool = False,
    inventory_reader: InventoryReader = inventory_fingerprint,
    recovery_inventory_reader: RecoveryInventoryReader | None = None,
) -> HistoricalIdentitySourceApplyPlanEvidence:
    """Reread a plan and revalidate every source byte and the canonical pre-state."""

    path = _validated_plan_file(plan_path)
    plan_sha256 = _file_sha256(path)
    if approved_plan_sha256 is not None and plan_sha256 != approved_plan_sha256:
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply-plan file hash differs"
        )
    try:
        plan = HistoricalIdentitySourceApplyPlanV1.model_validate_json(
            path.read_bytes()
        )
    except Exception as exc:
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply plan is invalid"
        ) from exc
    canonical_root = _validated_data_root(Path(plan.data_root))
    candidate_root = _validated_candidate_root(Path(plan.candidate_root))
    expected_dataset_root = _dataset_root(canonical_root)
    if Path(plan.target_dataset_root) != expected_dataset_root:
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply-plan target root differs"
        )
    expected_artifacts: list[HistoricalIdentitySourcePlanArtifactV1] = []
    target_partitions: list[Path] = []
    for session in plan.sessions:
        source_partition = _partition_path(
            _dataset_root(candidate_root),
            session.session_date.isoformat(),
        )
        target_partition = _partition_path(
            expected_dataset_root,
            session.session_date.isoformat(),
        )
        target_partitions.append(target_partition)
        _owner_only_directory(source_partition, candidate_root)
        _reject_symlink_chain(canonical_root, target_partition)
        if os.path.lexists(target_partition):
            if not verify_then_complete:
                raise HistoricalIdentitySourceApplyPlanError(
                    "historical source target partition is no longer absent"
                )
            _validate_completed_target(target_partition, session)
        for file_name, size, sha256 in (
            (MANIFEST_FILE, session.manifest_bytes, session.manifest_sha256),
            (PARQUET_FILE, session.parquet_bytes, session.parquet_sha256),
        ):
            source_path = source_partition / file_name
            _owner_read_only_file(source_path)
            if (
                source_path.stat().st_size != size
                or _file_sha256(source_path) != sha256
            ):
                raise HistoricalIdentitySourceApplyPlanError(
                    "historical source planned artifact custody differs"
                )
            expected_artifacts.append(
                HistoricalIdentitySourcePlanArtifactV1(
                    session_date=session.session_date,
                    file_name=file_name,
                    source_path=str(source_path),
                    target_path=str(target_partition / file_name),
                    size=size,
                    sha256=sha256,
                )
            )
    artifacts = tuple(expected_artifacts)
    if artifacts != plan.artifacts or (
        _candidate_inventory_fingerprint(artifacts)
        != plan.candidate_inventory_fingerprint
    ):
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply-plan candidate inventory differs"
        )
    session_dates = [item.session_date.isoformat() for item in plan.sessions]
    if (
        historical_identity_source_fingerprint(session_dates)
        != plan.session_index_fingerprint
    ):
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply-plan session index differs"
        )
    if verify_then_complete:
        recovery_reader = (
            recovery_inventory_reader
            if recovery_inventory_reader is not None
            else _recovery_inventory_fingerprint
        )
        current_inventory = recovery_reader(
            canonical_root,
            tuple(target_partitions),
        )
    else:
        current_inventory = inventory_reader(canonical_root)
    if current_inventory != plan.expected_current_state_fingerprint:
        raise HistoricalIdentitySourceApplyPlanError(
            "canonical inventory changed after historical source planning"
        )
    return HistoricalIdentitySourceApplyPlanEvidence(
        plan=plan,
        plan_path=path,
        plan_sha256=plan_sha256,
    )


def _read_candidate_for_plan(
    job: tuple[
        Path,
        HistoricalIdentityRebuildProfileBindingV1,
        str,
    ],
) -> _CandidatePlanSession:
    source_root, binding, profile_map_fingerprint = job
    source = read_historical_identity_source_custody_candidate(
        root=source_root,
        provider=MASSIVE_PROVIDER_ID,
        session_date=binding.session_date,
    )
    manifest = source.manifest
    if (
        manifest.identity_profile_map_fingerprint != profile_map_fingerprint
        or manifest.identity_profile_binding_fingerprint
        != binding.logical_fingerprint
        or manifest.identity_rebuild_profile != binding.rebuild_profile
        or manifest.canonical_snapshot_fingerprint
        != binding.canonical_snapshot_fingerprint
        or manifest.canonical_instrument_fingerprint
        != binding.canonical_instrument_fingerprint
        or manifest.canonical_identity_fingerprint
        != binding.canonical_identity_fingerprint
        or manifest.canonical_resolver_fingerprint
        != binding.canonical_resolver_fingerprint
    ):
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source candidate differs from its profile binding"
        )
    manifest_path = source.partition_path / MANIFEST_FILE
    parquet_path = source.partition_path / PARQUET_FILE
    return _CandidatePlanSession(
        session=HistoricalIdentitySourcePlanSessionV1(
            session_date=binding.session_date,
            identity_rebuild_profile=manifest.identity_rebuild_profile,
            record_count=manifest.record_count,
            source_request_count=manifest.source_request_count,
            source_response_bytes=sum(
                item.source_response_bytes for item in manifest.source_artifacts
            ),
            parquet_bytes=parquet_path.stat().st_size,
            manifest_bytes=manifest_path.stat().st_size,
            content_fingerprint=manifest.content_fingerprint,
            parquet_sha256=manifest.parquet_sha256,
            manifest_sha256=source.manifest_sha256,
            logical_fingerprint=manifest.logical_fingerprint,
            canonical_snapshot_fingerprint=manifest.canonical_snapshot_fingerprint,
            canonical_instrument_fingerprint=(
                manifest.canonical_instrument_fingerprint
            ),
            canonical_identity_fingerprint=manifest.canonical_identity_fingerprint,
            canonical_resolver_fingerprint=manifest.canonical_resolver_fingerprint,
        ),
        source_partition=source.partition_path,
    )


def _disable_network_in_worker() -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise HistoricalIdentitySourceApplyPlanError(
            "network access is disabled in historical source planning workers"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]


def _candidate_inventory_fingerprint(
    artifacts: tuple[HistoricalIdentitySourcePlanArtifactV1, ...],
) -> str:
    return historical_identity_source_fingerprint(
        [item.model_dump(mode="json") for item in artifacts]
    )


def _validate_completed_target(
    target: Path,
    session: HistoricalIdentitySourcePlanSessionV1,
) -> None:
    if (
        target.is_symlink()
        or not target.is_dir()
        or stat.S_IMODE(target.stat().st_mode) != 0o755
    ):
        raise HistoricalIdentitySourceApplyPlanError(
            "completed historical source target directory differs"
        )
    entries = {item.name for item in target.iterdir()}
    if entries != {MANIFEST_FILE, PARQUET_FILE}:
        raise HistoricalIdentitySourceApplyPlanError(
            "completed historical source target file set differs"
        )
    for file_name, size, sha256 in (
        (MANIFEST_FILE, session.manifest_bytes, session.manifest_sha256),
        (PARQUET_FILE, session.parquet_bytes, session.parquet_sha256),
    ):
        path = target / file_name
        if path.is_symlink() or not path.is_file():
            raise HistoricalIdentitySourceApplyPlanError(
                "completed historical source target artifact is unavailable"
            )
        metadata = path.stat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o644
            or metadata.st_size != size
            or _file_sha256(path) != sha256
        ):
            raise HistoricalIdentitySourceApplyPlanError(
                "completed historical source target artifact differs"
            )


def _recovery_inventory_fingerprint(
    root: Path,
    targets: tuple[Path, ...],
) -> str:
    return inventory_fingerprint(root, exclude_prefixes=targets)


def _dataset_root(root: Path) -> Path:
    return (
        root
        / "market-data"
        / DATASET_NAME
        / f"schema_version={SCHEMA_PARTITION}"
        / f"provider={MASSIVE_PROVIDER_ID}"
    )


def _partition_path(dataset_root: Path, session_text: str) -> Path:
    return dataset_root / f"as_of_date={session_text}"


def _validated_data_root(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise HistoricalIdentitySourceApplyPlanError(
            "canonical data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != APPROVED_DATA_ROOT:
        raise HistoricalIdentitySourceApplyPlanError(
            "canonical data root is not the approved Dell root"
        )
    return resolved


def _validated_candidate_root(path: Path) -> Path:
    temporary_root = Path("/tmp").resolve(strict=True)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source candidate root is unavailable"
        )
    if temporary_root not in path.parents:
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source candidate root must be below /tmp"
        )
    _reject_symlink_chain(temporary_root, path)
    resolved = path.resolve(strict=True)
    if resolved != path or stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source candidate root is not owner-only and direct"
        )
    return resolved


def _owner_only_directory(path: Path, root: Path) -> None:
    _reject_symlink_chain(root, path)
    current = path
    while True:
        if not current.is_dir() or stat.S_IMODE(current.stat().st_mode) != 0o700:
            raise HistoricalIdentitySourceApplyPlanError(
                "historical source candidate directory chain is not owner-only"
            )
        if current == root:
            return
        current = current.parent


def _owner_read_only_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source planned artifact is unavailable"
        )
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o400:
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source planned artifact is not owner-read-only"
        )


def _validated_plan_file(path: Path) -> Path:
    temporary_root = Path("/tmp").resolve(strict=True)
    if not path.is_absolute() or temporary_root not in path.parents:
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply plan must be below /tmp"
        )
    _reject_symlink_chain(temporary_root, path)
    if path.is_symlink() or not path.is_file():
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply plan is unavailable"
        )
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply plan is not owner-readable"
        )
    return path.resolve(strict=True)


def _write_plan(
    *,
    plan: HistoricalIdentitySourceApplyPlanV1,
    plan_path: Path,
) -> Path:
    temporary_root = Path("/tmp").resolve(strict=True)
    if not plan_path.is_absolute() or temporary_root not in plan_path.parents:
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply-plan target must be below /tmp"
        )
    parent = plan_path.parent
    _reject_symlink_chain(temporary_root, parent)
    if parent.is_symlink() or not parent.is_dir():
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply-plan parent is unavailable"
        )
    target = parent / plan_path.name
    if os.path.lexists(target):
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply-plan target already exists"
        )
    staging = parent / f".{target.name}.staging"
    if os.path.lexists(staging):
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source Apply-plan staging path already exists"
        )
    raw = (
        json.dumps(plan.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    descriptor = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        staging.replace(target)
        _fsync_directory(parent)
    except Exception:
        if os.path.lexists(staging) and not staging.is_symlink():
            staging.unlink()
        raise
    return target


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if not root.is_absolute() or not target.is_absolute() or (
        target != root and root not in target.parents
    ):
        raise HistoricalIdentitySourceApplyPlanError(
            "historical source plan path escapes its root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise HistoricalIdentitySourceApplyPlanError(
                "historical source plan path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_ready(value: object) -> object:
    return to_jsonable_python(value)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
