"""Recoverable physical-first, marker-last Apply for Universe Membership."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import socket
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from tip_api.contracts.market_data.v1 import (
    UniverseMembershipApplyPlanV1,
    UniverseMembershipPlanArtifactV1,
)
from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services import universe_membership_canonical as canonical_service
from tip_api.services.universe_membership_apply_plan import (
    RecoveryInventoryReader,
    UniverseMembershipApplyPlanError,
    UniverseMembershipApplyPlanEvidence,
    read_universe_membership_apply_plan,
)
from tip_api.services.universe_membership_canonical import (
    CanonicalUniverseMembershipError,
    read_canonical_universe_membership,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
LOCK_ROOT = Path("/tmp")
_SHA256_LENGTH = 64


class UniverseMembershipApplyError(RuntimeError):
    """Fail-closed error for canonical Universe Membership publication."""


@dataclass(frozen=True, slots=True)
class UniverseMembershipApplyResult:
    status: str
    plan_sha256: str
    plan_logical_fingerprint: str
    expected_current_state_fingerprint: str
    post_state_fingerprint: str
    membership_partition_published: bool
    membership_partition_reused: bool
    publication_marker_published: bool
    publication_marker_reused: bool
    published_file_count: int
    published_bytes: int
    formal_reread_record_count: int
    publication_fingerprint: str
    publication_sha256: str
    external_request_count: int = 0
    overwritten_partition_count: int = 0
    deleted_partition_count: int = 0
    historical_coverage_authorized: bool = False
    research_performance_authorized: bool = False


InventoryReader = Callable[[Path], str]


def apply_approved_universe_membership_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_current_state_fingerprint: str,
    data_root: Path,
    verify_then_complete: bool = False,
    inventory_reader: InventoryReader = inventory_fingerprint,
    recovery_inventory_reader: RecoveryInventoryReader | None = None,
) -> UniverseMembershipApplyResult:
    """Apply or verify-and-complete one exact Membership publication plan."""

    canonical_root = _validated_data_root(data_root)
    _validate_fingerprint(approved_plan_sha256, "approved plan SHA-256")
    _validate_fingerprint(
        expected_plan_logical_fingerprint,
        "expected plan logical fingerprint",
    )
    _validate_fingerprint(
        expected_current_state_fingerprint,
        "expected current-state fingerprint",
    )
    evidence = _read_plan(
        plan_path=plan_path,
        approved_plan_sha256=approved_plan_sha256,
        verify_then_complete=verify_then_complete,
        inventory_reader=inventory_reader,
        recovery_inventory_reader=recovery_inventory_reader,
    )
    _validate_execution_binding(
        evidence=evidence,
        approved_plan_sha256=approved_plan_sha256,
        expected_plan_logical_fingerprint=expected_plan_logical_fingerprint,
        expected_current_state_fingerprint=expected_current_state_fingerprint,
        data_root=canonical_root,
    )

    lock_path = LOCK_ROOT / (
        "tip-same-day-catchup-"
        + hashlib.sha256(str(canonical_root).encode("utf-8")).hexdigest()[:16]
        + ".lock"
    )
    try:
        descriptor = os.open(
            lock_path,
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
        )
    except OSError as exc:
        raise UniverseMembershipApplyError(
            "Membership publication lock is unavailable"
        ) from exc
    with os.fdopen(descriptor, "r+b") as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise UniverseMembershipApplyError(
                "Membership publication lock is not a regular file"
            )
        os.fchmod(lock.fileno(), 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        locked = _read_plan(
            plan_path=plan_path,
            approved_plan_sha256=approved_plan_sha256,
            verify_then_complete=verify_then_complete,
            inventory_reader=inventory_reader,
            recovery_inventory_reader=recovery_inventory_reader,
        )
        if locked != evidence:
            raise UniverseMembershipApplyError(
                "Membership Apply plan changed before locked execution"
            )
        _validate_execution_binding(
            evidence=locked,
            approved_plan_sha256=approved_plan_sha256,
            expected_plan_logical_fingerprint=(
                expected_plan_logical_fingerprint
            ),
            expected_current_state_fingerprint=(
                expected_current_state_fingerprint
            ),
            data_root=canonical_root,
        )

        plan = locked.plan
        membership_target = Path(plan.target_membership_partition)
        publication_target = Path(plan.target_publication_partition)
        membership_published = False
        membership_reused = False
        marker_published = False
        marker_reused = False
        published_file_count = 0
        published_bytes = 0
        with _network_prohibited():
            if verify_then_complete and not (
                os.path.lexists(membership_target)
                or os.path.lexists(publication_target)
            ):
                for target in (membership_target, publication_target):
                    if os.path.lexists(
                        _staging_path(target, plan.logical_fingerprint)
                    ):
                        raise UniverseMembershipApplyError(
                            "Membership recovery staging path already exists"
                        )
                raise UniverseMembershipApplyError(
                    "Membership recovery found no completed target"
                )
            if os.path.lexists(membership_target):
                if not verify_then_complete:
                    raise UniverseMembershipApplyError(
                        "Membership physical target already exists"
                    )
                _verify_membership_target(membership_target, plan.artifacts)
                membership_reused = True
            else:
                _publish_membership_partition(
                    data_root=canonical_root,
                    target=membership_target,
                    artifacts=plan.artifacts,
                    plan_fingerprint=plan.logical_fingerprint,
                )
                membership_published = True
                published_file_count += len(plan.artifacts)
                published_bytes += sum(item.size for item in plan.artifacts)

            try:
                physical_records = ParquetHistoricalResearchRepository(
                    canonical_root
                ).read_universe_membership(membership_target)
            except Exception as exc:
                raise UniverseMembershipApplyError(
                    "canonical Membership physical preread failed"
                ) from exc
            if len(physical_records) != plan.publication.record_count:
                raise UniverseMembershipApplyError(
                    "canonical Membership physical preread count differs"
                )

            # The marker is intentionally the final canonical write.
            if os.path.lexists(publication_target):
                if not verify_then_complete:
                    raise UniverseMembershipApplyError(
                        "Membership publication marker already exists"
                    )
                _verify_publication_target(publication_target, plan)
                marker_reused = True
            else:
                _publish_publication_marker(
                    data_root=canonical_root,
                    target=publication_target,
                    plan=plan,
                )
                marker_published = True
                published_file_count += 1
                published_bytes += plan.publication_manifest_bytes

            try:
                canonical = read_canonical_universe_membership(
                    data_root=canonical_root,
                    methodology_version=plan.publication.methodology_version,
                    session_date=plan.publication.session_date,
                    expected_publication_fingerprint=(
                        plan.publication.logical_fingerprint
                    ),
                )
            except CanonicalUniverseMembershipError as exc:
                raise UniverseMembershipApplyError(
                    "canonical Membership formal reread failed"
                ) from exc
            outside_inventory = _recovery_inventory_fingerprint(
                canonical_root,
                (membership_target, publication_target),
            )
            if outside_inventory != expected_current_state_fingerprint:
                raise UniverseMembershipApplyError(
                    "canonical inventory outside Membership targets changed during Apply"
                )
        post_state = inventory_reader(canonical_root)

    return UniverseMembershipApplyResult(
        status=("verified_then_completed" if verify_then_complete else "applied"),
        plan_sha256=approved_plan_sha256,
        plan_logical_fingerprint=expected_plan_logical_fingerprint,
        expected_current_state_fingerprint=expected_current_state_fingerprint,
        post_state_fingerprint=post_state,
        membership_partition_published=membership_published,
        membership_partition_reused=membership_reused,
        publication_marker_published=marker_published,
        publication_marker_reused=marker_reused,
        published_file_count=published_file_count,
        published_bytes=published_bytes,
        formal_reread_record_count=len(canonical.records),
        publication_fingerprint=canonical.publication.logical_fingerprint,
        publication_sha256=canonical.publication_sha256,
    )


def _read_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    verify_then_complete: bool,
    inventory_reader: InventoryReader,
    recovery_inventory_reader: RecoveryInventoryReader | None,
) -> UniverseMembershipApplyPlanEvidence:
    try:
        return read_universe_membership_apply_plan(
            plan_path=plan_path,
            approved_plan_sha256=approved_plan_sha256,
            verify_then_complete=verify_then_complete,
            inventory_reader=inventory_reader,
            recovery_inventory_reader=recovery_inventory_reader,
        )
    except UniverseMembershipApplyPlanError as exc:
        raise UniverseMembershipApplyError(
            "Membership Apply plan failed formal reread"
        ) from exc


def _validate_execution_binding(
    *,
    evidence: UniverseMembershipApplyPlanEvidence,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_current_state_fingerprint: str,
    data_root: Path,
) -> None:
    plan = evidence.plan
    if (
        evidence.plan_sha256 != approved_plan_sha256
        or plan.logical_fingerprint != expected_plan_logical_fingerprint
        or plan.expected_current_state_fingerprint
        != expected_current_state_fingerprint
        or Path(plan.data_root) != data_root
        or plan.operation != "publish_signal_eligible_universe_membership"
        or plan.inventory_change_file_count != 3
        or plan.apply_authorized is not False
        or plan.historical_coverage_authorized is not False
        or plan.research_performance_authorized is not False
    ):
        raise UniverseMembershipApplyError(
            "Membership Apply execution binding differs"
        )


def _publish_membership_partition(
    *,
    data_root: Path,
    target: Path,
    artifacts: tuple[UniverseMembershipPlanArtifactV1, ...],
    plan_fingerprint: str,
) -> None:
    _reject_symlink_chain(data_root, target)
    _mkdirs_durable(target.parent, data_root)
    staging = _staging_path(target, plan_fingerprint)
    if os.path.lexists(target) or os.path.lexists(staging):
        raise UniverseMembershipApplyError(
            "Membership physical target or staging path already exists"
        )
    staging.mkdir(mode=0o755)
    staging.chmod(0o755)
    try:
        for artifact in artifacts:
            source = Path(artifact.source_path)
            _verify_source(source, artifact)
            destination = staging / artifact.file_name
            shutil.copyfile(source, destination)
            destination.chmod(0o644)
            _fsync_file(destination)
            if (
                destination.stat().st_size != artifact.size
                or _file_sha256(destination) != artifact.sha256
            ):
                raise UniverseMembershipApplyError(
                    "staged Membership artifact differs"
                )
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise
    _verify_membership_target(target, artifacts)


def _publish_publication_marker(
    *,
    data_root: Path,
    target: Path,
    plan: UniverseMembershipApplyPlanV1,
) -> None:
    _reject_symlink_chain(data_root, target)
    _mkdirs_durable(target.parent, data_root)
    staging = _staging_path(target, plan.logical_fingerprint)
    if os.path.lexists(target) or os.path.lexists(staging):
        raise UniverseMembershipApplyError(
            "Membership publication target or staging path already exists"
        )
    staging.mkdir(mode=0o755)
    staging.chmod(0o755)
    try:
        payload = _canonical_json_bytes(plan.publication.model_dump(mode="json"))
        if (
            len(payload) != plan.publication_manifest_bytes
            or _bytes_sha256(payload) != plan.publication_manifest_sha256
        ):
            raise UniverseMembershipApplyError(
                "Membership publication bytes differ from plan"
            )
        destination = staging / canonical_service.PUBLICATION_FILE_NAME
        with destination.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        destination.chmod(0o644)
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise
    _verify_publication_target(target, plan)


def _verify_membership_target(
    target: Path,
    artifacts: tuple[UniverseMembershipPlanArtifactV1, ...],
) -> None:
    if (
        target.is_symlink()
        or not target.is_dir()
        or stat.S_IMODE(target.stat().st_mode) != 0o755
    ):
        raise UniverseMembershipApplyError(
            "completed Membership physical target differs"
        )
    if {item.name for item in target.iterdir()} != {
        item.file_name for item in artifacts
    }:
        raise UniverseMembershipApplyError(
            "completed Membership physical file set differs"
        )
    for artifact in artifacts:
        path = target / artifact.file_name
        _regular_file(path, expected_mode=0o644)
        if (
            path.stat().st_size != artifact.size
            or _file_sha256(path) != artifact.sha256
        ):
            raise UniverseMembershipApplyError(
                "completed Membership physical artifact differs"
            )


def _verify_publication_target(
    target: Path,
    plan: UniverseMembershipApplyPlanV1,
) -> None:
    if (
        target.is_symlink()
        or not target.is_dir()
        or stat.S_IMODE(target.stat().st_mode) != 0o755
    ):
        raise UniverseMembershipApplyError(
            "completed Membership publication target differs"
        )
    if {item.name for item in target.iterdir()} != {
        canonical_service.PUBLICATION_FILE_NAME
    }:
        raise UniverseMembershipApplyError(
            "completed Membership publication file set differs"
        )
    path = target / canonical_service.PUBLICATION_FILE_NAME
    _regular_file(path, expected_mode=0o644)
    payload = path.read_bytes()
    if (
        len(payload) != plan.publication_manifest_bytes
        or _bytes_sha256(payload) != plan.publication_manifest_sha256
        or payload
        != _canonical_json_bytes(plan.publication.model_dump(mode="json"))
    ):
        raise UniverseMembershipApplyError(
            "completed Membership publication marker differs"
        )


def _verify_source(
    path: Path,
    artifact: UniverseMembershipPlanArtifactV1,
) -> None:
    if path.is_symlink() or not path.is_file():
        raise UniverseMembershipApplyError(
            "Membership source artifact is unavailable"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_size != artifact.size
        or _file_sha256(path) != artifact.sha256
    ):
        raise UniverseMembershipApplyError(
            "Membership source artifact differs from plan"
        )


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise UniverseMembershipApplyError(
            "Membership data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise UniverseMembershipApplyError(
            "Membership data root is not the approved Dell root"
        )
    return resolved


def _mkdirs_durable(path: Path, root: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        if current == root or root not in current.parents:
            raise UniverseMembershipApplyError(
                "Membership publication path escapes data root"
            )
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise UniverseMembershipApplyError(
            "Membership publication parent is unsafe"
        )
    for item in reversed(missing):
        item.mkdir(mode=0o755)
        item.chmod(0o755)
        _fsync_directory(item.parent)
    _reject_symlink_chain(root, path)


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise UniverseMembershipApplyError(
            "Membership publication path escapes data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise UniverseMembershipApplyError(
                "Membership publication path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _regular_file(path: Path, *, expected_mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise UniverseMembershipApplyError(
            "Membership artifact is not a regular file"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != expected_mode
    ):
        raise UniverseMembershipApplyError(
            "Membership artifact mode differs"
        )


def _staging_path(target: Path, plan_fingerprint: str) -> Path:
    return target.parent / (
        f".{target.name}.staging.{plan_fingerprint[:16]}"
    )


def _validate_fingerprint(value: str, label: str) -> None:
    if len(value) != _SHA256_LENGTH or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise UniverseMembershipApplyError(f"{label} is malformed")


def _recovery_inventory_fingerprint(
    root: Path,
    targets: tuple[Path, ...],
) -> str:
    return inventory_fingerprint(root, exclude_prefixes=targets)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise UniverseMembershipApplyError(
            "network access is disabled during Membership Apply"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]


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


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
