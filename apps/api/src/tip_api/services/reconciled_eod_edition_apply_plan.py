"""Build and formally reread an exact whole-edition EOD Apply plan."""

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
    ReconciledEodEditionApplyArtifactV1,
    ReconciledEodEditionApplyPlanV1,
    reconciled_eod_apply_inventory_fingerprint,
    seal_reconciled_eod_apply_plan,
)
from tip_api.contracts.market_data.v1.reconciled_eod_edition import DATASET_NAME
from tip_api.persistence.parquet.reconciled_eod_edition import (
    CONTRACT_VERSION_PARTITION,
    INTERVAL_MANIFEST_FILE_NAME,
    MANIFEST_FILE_NAME,
    ValidatedReconciledEodEdition,
    validate_reconciled_eod_edition,
)
from tip_api.persistence.parquet.eod_bars import PARQUET_FILE_NAME
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
PLAN_FILE_NAME = "apply-plan.json"
MAXIMUM_PLAN_BYTES = 16 * 1024 * 1024


class ReconciledEodEditionApplyPlanError(RuntimeError):
    """Fail-closed error for a whole-edition Apply plan."""


@dataclass(frozen=True, slots=True)
class ReconciledEodEditionApplyPlanEvidence:
    plan_path: Path
    plan: ReconciledEodEditionApplyPlanV1
    plan_sha256: str
    candidate: ValidatedReconciledEodEdition


InventoryReader = Callable[[Path], str]


def build_reconciled_eod_edition_apply_plan(
    *,
    data_root: Path,
    candidate_root: Path,
    plan_path: Path,
    edition_id: str,
    planner_revision: str,
    created_at: datetime,
    inventory_reader: InventoryReader = inventory_fingerprint,
) -> ReconciledEodEditionApplyPlanEvidence:
    """Bind one complete candidate edition to one absent canonical target."""

    with _network_prohibited():
        root = _validated_data_root(data_root)
        candidate_root = _validated_candidate_root(candidate_root)
        plan_path = _validated_plan_target(plan_path, candidate_root=candidate_root)
        candidate = _formal_candidate_read(
            candidate_root=candidate_root,
            edition_id=edition_id,
        )
        created_at = normalize_utc_datetime(created_at)
        if created_at < candidate.manifest.created_at:
            raise ReconciledEodEditionApplyPlanError(
                "reconciled EOD Apply plan precedes candidate completion"
            )
        target = _edition_path(root, edition_id=edition_id)
        if os.path.lexists(target):
            raise ReconciledEodEditionApplyPlanError(
                "reconciled EOD target edition already exists"
            )
        artifacts = _candidate_artifacts(
            candidate=candidate,
            candidate_root=candidate_root,
        )
        plan = seal_reconciled_eod_apply_plan(
            {
                "created_at": created_at,
                "planner_revision": planner_revision,
                "candidate_implementation_revision": (
                    candidate.manifest.implementation_revision
                ),
                "edition_id": edition_id,
                "data_root": str(root),
                "candidate_location_fingerprint": _location_fingerprint(
                    candidate_root
                ),
                "target_edition_path": str(target),
                "expected_current_state_fingerprint": inventory_reader(root),
                "candidate_interval_manifest_fingerprint": (
                    candidate.manifest.logical_fingerprint
                ),
                "candidate_inventory_fingerprint": (
                    reconciled_eod_apply_inventory_fingerprint(artifacts)
                ),
                "candidate_session_count": len(candidate.session_manifests),
                "candidate_record_count": sum(
                    item.diff.rebuilt_record_count
                    for item in candidate.session_manifests
                ),
                "candidate_added_record_count": sum(
                    item.diff.added_record_count
                    for item in candidate.session_manifests
                ),
                "candidate_absent_record_count": sum(
                    item.diff.absent_record_count
                    for item in candidate.session_manifests
                ),
                "candidate_provenance_only_change_count": sum(
                    item.diff.provenance_only_change_count
                    for item in candidate.session_manifests
                ),
                "artifacts": artifacts,
                "inventory_change_file_count": len(artifacts),
                "inventory_change_bytes": sum(item.size for item in artifacts),
            }
        )
        _write_plan(plan_path, plan)
        approved_plan_sha256 = _file_sha256(plan_path)
        reread = _read_plan_contract(
            path=_validated_plan_file(plan_path),
            approved_plan_sha256=approved_plan_sha256,
        )
        if reread != plan:
            raise ReconciledEodEditionApplyPlanError(
                "reconciled EOD Apply plan changed during formal reread"
            )
        return ReconciledEodEditionApplyPlanEvidence(
            plan_path=plan_path,
            plan=plan,
            plan_sha256=approved_plan_sha256,
            candidate=candidate,
        )


def read_reconciled_eod_edition_apply_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    allow_completed_target: bool = False,
) -> ReconciledEodEditionApplyPlanEvidence:
    """Formally reread a byte-approved plan and every candidate artifact."""

    path = _validated_plan_file(plan_path)
    plan = _read_plan_contract(
        path=path,
        approved_plan_sha256=approved_plan_sha256,
    )
    root = _validated_data_root(Path(plan.data_root))
    candidate_root = _validated_candidate_root(path.parent)
    if path.parent != candidate_root or path.name != PLAN_FILE_NAME:
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD Apply plan custody differs"
        )
    if _location_fingerprint(candidate_root) != plan.candidate_location_fingerprint:
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD candidate location differs"
        )
    candidate = _formal_candidate_read(
        candidate_root=candidate_root,
        edition_id=plan.edition_id,
    )
    target = _edition_path(root, edition_id=plan.edition_id)
    if Path(plan.target_edition_path) != target:
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD Apply target differs"
        )
    expected_artifacts = _candidate_artifacts(
        candidate=candidate,
        candidate_root=candidate_root,
    )
    if expected_artifacts != plan.artifacts:
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD planned artifacts differ"
        )
    if (
        candidate.manifest.logical_fingerprint
        != plan.candidate_interval_manifest_fingerprint
        or candidate.manifest.implementation_revision
        != plan.candidate_implementation_revision
        or len(candidate.session_manifests) != plan.candidate_session_count
        or sum(
            item.diff.rebuilt_record_count for item in candidate.session_manifests
        )
        != plan.candidate_record_count
        or sum(item.diff.added_record_count for item in candidate.session_manifests)
        != plan.candidate_added_record_count
        or sum(item.diff.absent_record_count for item in candidate.session_manifests)
        != plan.candidate_absent_record_count
        or sum(
            item.diff.provenance_only_change_count
            for item in candidate.session_manifests
        )
        != plan.candidate_provenance_only_change_count
    ):
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD candidate summary differs"
        )
    if os.path.lexists(target):
        if not allow_completed_target:
            raise ReconciledEodEditionApplyPlanError(
                "reconciled EOD target appeared after planning"
            )
    return ReconciledEodEditionApplyPlanEvidence(
        plan_path=path,
        plan=plan,
        plan_sha256=approved_plan_sha256,
        candidate=candidate,
    )


def _formal_candidate_read(
    *,
    candidate_root: Path,
    edition_id: str,
) -> ValidatedReconciledEodEdition:
    try:
        return validate_reconciled_eod_edition(
            root=candidate_root,
            edition_id=edition_id,
        )
    except Exception as exc:
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD candidate failed formal reread"
        ) from exc


def _candidate_artifacts(
    *,
    candidate: ValidatedReconciledEodEdition,
    candidate_root: Path,
) -> tuple[ReconciledEodEditionApplyArtifactV1, ...]:
    edition_path = candidate.edition_path
    relative_paths = tuple(
        path
        for session in candidate.session_manifests
        for path in (
            f"session_date={session.session_date.isoformat()}/{MANIFEST_FILE_NAME}",
            f"session_date={session.session_date.isoformat()}/{PARQUET_FILE_NAME}",
        )
    ) + (INTERVAL_MANIFEST_FILE_NAME,)
    known_hashes = {
        f"session_date={session.session_date.isoformat()}/{PARQUET_FILE_NAME}": (
            session.parquet_sha256
        )
        for session in candidate.session_manifests
    }
    artifacts: list[ReconciledEodEditionApplyArtifactV1] = []
    for relative in relative_paths:
        source = edition_path / relative
        _owner_only_candidate_artifact(
            path=source,
            candidate_root=candidate_root,
        )
        metadata = source.stat()
        artifacts.append(
            ReconciledEodEditionApplyArtifactV1(
                relative_path=relative,
                size=metadata.st_size,
                sha256=known_hashes.get(relative) or _file_sha256(source),
            )
        )
    return tuple(artifacts)


def _edition_path(root: Path, *, edition_id: str) -> Path:
    return (
        root
        / "market-data"
        / DATASET_NAME
        / f"contract_version={CONTRACT_VERSION_PARTITION}"
        / f"edition_id={edition_id}"
    )


def _location_fingerprint(path: Path) -> str:
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ReconciledEodEditionApplyPlanError(
            "canonical data root is unavailable"
        )
    try:
        resolved = path.resolve(strict=True)
        approved = APPROVED_DATA_ROOT.resolve(strict=True)
    except OSError as exc:
        raise ReconciledEodEditionApplyPlanError(
            "canonical data root is unavailable"
        ) from exc
    if resolved != path or resolved != approved:
        raise ReconciledEodEditionApplyPlanError(
            "canonical data root is not the approved Dell root"
        )
    return resolved


def _validated_candidate_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD candidate root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD candidate root is indirect"
        )
    metadata = path.stat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD candidate root is not owner-only"
        )
    return resolved


def _validated_plan_target(path: Path, *, candidate_root: Path) -> Path:
    if not path.is_absolute() or path.parent != candidate_root or path.name != PLAN_FILE_NAME:
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD Apply plan target is invalid"
        )
    if os.path.lexists(path) and (path.is_symlink() or not path.is_file()):
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD Apply plan target is unsafe"
        )
    return path


def _validated_plan_file(path: Path) -> Path:
    if not path.is_absolute() or path.name != PLAN_FILE_NAME:
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD Apply plan path is invalid"
        )
    candidate_root = _validated_candidate_root(path.parent)
    if candidate_root != path.parent or path.is_symlink() or not path.is_file():
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD Apply plan is unavailable"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o400
    ):
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD Apply plan custody differs"
        )
    return path


def _owner_only_candidate_artifact(*, path: Path, candidate_root: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD candidate artifact is unavailable"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD candidate artifact is not owner-only"
        )
    current = path.parent
    while True:
        directory = current.stat()
        if (
            current.is_symlink()
            or not stat.S_ISDIR(directory.st_mode)
            or directory.st_uid != os.getuid()
            or stat.S_IMODE(directory.st_mode) != 0o700
        ):
            raise ReconciledEodEditionApplyPlanError(
                "reconciled EOD candidate directory custody differs"
            )
        if current == candidate_root:
            return
        if candidate_root not in current.parents:
            raise ReconciledEodEditionApplyPlanError(
                "reconciled EOD candidate artifact escapes its root"
            )
        current = current.parent


def _write_plan(path: Path, plan: ReconciledEodEditionApplyPlanV1) -> None:
    payload = _pretty_json(plan.model_dump(mode="json"))
    if os.path.lexists(path):
        if (
            path.is_symlink()
            or not path.is_file()
            or stat.S_IMODE(path.stat().st_mode) != 0o400
            or path.stat().st_uid != os.getuid()
            or path.read_bytes() != payload
        ):
            raise ReconciledEodEditionApplyPlanError(
                "existing reconciled EOD Apply plan differs"
            )
        return
    temporary = path.parent / f".{path.name}.tmp.{os.getpid()}"
    descriptor = os.open(
        temporary,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o400,
    )
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise ReconciledEodEditionApplyPlanError(
                    "reconciled EOD Apply plan write did not progress"
                )
            remaining = remaining[written:]
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.replace(path)
    _fsync_directory(path.parent)


def _read_plan_contract(
    *,
    path: Path,
    approved_plan_sha256: str,
) -> ReconciledEodEditionApplyPlanV1:
    raw = path.read_bytes()
    if (
        not raw
        or len(raw) > MAXIMUM_PLAN_BYTES
        or hashlib.sha256(raw).hexdigest() != approved_plan_sha256
    ):
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD Apply plan bytes differ"
        )
    try:
        plan = ReconciledEodEditionApplyPlanV1.model_validate_json(raw)
    except Exception as exc:
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD Apply plan contract is invalid"
        ) from exc
    if raw != _pretty_json(plan.model_dump(mode="json")):
        raise ReconciledEodEditionApplyPlanError(
            "reconciled EOD Apply plan is not canonical JSON"
        )
    return plan


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
    original_getaddrinfo = socket.getaddrinfo

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise ReconciledEodEditionApplyPlanError(
            "network is prohibited while planning reconciled EOD Apply"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    socket.getaddrinfo = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
