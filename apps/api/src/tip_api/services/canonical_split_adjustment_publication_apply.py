"""Atomic, inventory-bound Apply for one canonical split-adjustment publication."""

from __future__ import annotations

import fcntl
import hashlib
import os
import shutil
import socket
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from tip_api.contracts.market_data.v1 import CanonicalSplitAdjustmentPublicationV1
from tip_api.persistence.parquet.canonical_split_adjustment import (
    CanonicalSplitAdjustmentPersistenceError,
    CanonicalSplitAdjustmentPublicationRead,
    read_canonical_split_adjustment_publication,
)
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.canonical_split_adjustment_publication_plan import (
    CanonicalSplitAdjustmentPublicationPlanError,
    CanonicalSplitAdjustmentPublicationPlanEvidence,
    read_canonical_split_adjustment_publication_plan,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
LOCK_ROOT = Path("/tmp")
_SHA256_LENGTH = 64


class CanonicalSplitAdjustmentPublicationApplyError(RuntimeError):
    """Raised when canonical split adjustments cannot be published safely."""


@dataclass(frozen=True, slots=True)
class CanonicalSplitAdjustmentPublicationApplyResult:
    status: str
    plan_sha256: str
    plan_logical_fingerprint: str
    expected_current_state_fingerprint: str
    post_state_fingerprint: str
    outside_inventory_fingerprint: str
    publication_fingerprint: str
    record_count: int
    clear_record_count: int
    quarantined_record_count: int
    published_file_count: int
    published_bytes: int
    reused_file_count: int
    external_request_count: int = 0
    overwritten_file_count: int = 0
    deleted_file_count: int = 0
    absent_row_neutrality_authorized: bool = False
    total_return_adjustment_authorized: bool = False
    full_adjustment_coverage_authorized: bool = False
    historical_coverage_authorized: bool = False
    research_performance_authorized: bool = False


InventoryReader = Callable[..., str]


def apply_approved_canonical_split_adjustment_publication_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_current_state_fingerprint: str,
    data_root: Path,
    inventory_reader: InventoryReader = inventory_fingerprint,
) -> CanonicalSplitAdjustmentPublicationApplyResult:
    """Publish one exact candidate directory or verify an exact prior rename."""

    root = _validated_data_root(data_root)
    for value, label in (
        (approved_plan_sha256, "approved plan SHA-256"),
        (expected_plan_logical_fingerprint, "expected plan fingerprint"),
        (expected_current_state_fingerprint, "expected current-state fingerprint"),
    ):
        _validate_fingerprint(value, label)
    evidence = _read_plan(plan_path, approved_plan_sha256)
    _validate_binding(
        evidence=evidence,
        expected_plan_logical_fingerprint=expected_plan_logical_fingerprint,
        expected_current_state_fingerprint=expected_current_state_fingerprint,
        data_root=root,
    )
    lock_path = LOCK_ROOT / (
        "tip-same-day-catchup-"
        + hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
        + ".lock"
    )
    try:
        descriptor = os.open(
            lock_path,
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
        )
    except OSError as exc:
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment publication lock is unavailable"
        ) from exc

    with os.fdopen(descriptor, "r+b") as lock:
        metadata = os.fstat(lock.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise CanonicalSplitAdjustmentPublicationApplyError(
                "canonical split-adjustment publication lock custody differs"
            )
        os.fchmod(lock.fileno(), 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        locked = _read_plan(plan_path, approved_plan_sha256)
        if locked != evidence:
            raise CanonicalSplitAdjustmentPublicationApplyError(
                "canonical split-adjustment plan changed before locked execution"
            )
        _validate_binding(
            evidence=locked,
            expected_plan_logical_fingerprint=expected_plan_logical_fingerprint,
            expected_current_state_fingerprint=expected_current_state_fingerprint,
            data_root=root,
        )
        plan = locked.plan
        target = Path(plan.target_publication_root)
        with _network_prohibited():
            if os.path.lexists(target):
                status = "verified_existing"
                published_file_count = 0
                published_bytes = 0
                reused_file_count = len(plan.artifacts)
                _verify_target(root, target, plan.publication)
                outside = inventory_reader(root, exclude_prefixes=(target,))
                if outside != expected_current_state_fingerprint:
                    raise CanonicalSplitAdjustmentPublicationApplyError(
                        "inventory outside the existing publication changed"
                    )
            else:
                if inventory_reader(root) != expected_current_state_fingerprint:
                    raise CanonicalSplitAdjustmentPublicationApplyError(
                        "canonical inventory changed after plan review"
                    )
                _publish(root=root, target=target, evidence=locked)
                status = "applied"
                published_file_count = len(plan.artifacts)
                published_bytes = sum(item.size for item in plan.artifacts)
                reused_file_count = 0
                outside = inventory_reader(root, exclude_prefixes=(target,))
                if outside != expected_current_state_fingerprint:
                    raise CanonicalSplitAdjustmentPublicationApplyError(
                        "inventory outside the new publication changed"
                    )
            canonical = _verify_target(root, target, plan.publication)
            post_state = inventory_reader(root)

    publication = canonical.publication
    return CanonicalSplitAdjustmentPublicationApplyResult(
        status=status,
        plan_sha256=approved_plan_sha256,
        plan_logical_fingerprint=expected_plan_logical_fingerprint,
        expected_current_state_fingerprint=expected_current_state_fingerprint,
        post_state_fingerprint=post_state,
        outside_inventory_fingerprint=outside,
        publication_fingerprint=publication.logical_fingerprint,
        record_count=publication.record_count,
        clear_record_count=publication.clear_record_count,
        quarantined_record_count=publication.quarantined_record_count,
        published_file_count=published_file_count,
        published_bytes=published_bytes,
        reused_file_count=reused_file_count,
    )


def _read_plan(
    plan_path: Path,
    approved_plan_sha256: str,
) -> CanonicalSplitAdjustmentPublicationPlanEvidence:
    try:
        return read_canonical_split_adjustment_publication_plan(
            plan_path=plan_path,
            approved_plan_sha256=approved_plan_sha256,
        )
    except CanonicalSplitAdjustmentPublicationPlanError as exc:
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment plan failed formal reread"
        ) from exc


def _validate_binding(
    *,
    evidence: CanonicalSplitAdjustmentPublicationPlanEvidence,
    expected_plan_logical_fingerprint: str,
    expected_current_state_fingerprint: str,
    data_root: Path,
) -> None:
    plan = evidence.plan
    if (
        plan.logical_fingerprint != expected_plan_logical_fingerprint
        or plan.expected_current_state_fingerprint
        != expected_current_state_fingerprint
        or Path(plan.data_root) != data_root
        or plan.operation != "publish_canonical_split_adjustment"
        or plan.apply_authorized is not False
        or plan.absent_row_neutrality_authorized is not False
        or plan.total_return_adjustment_authorized is not False
        or plan.full_adjustment_coverage_authorized is not False
        or plan.historical_coverage_authorized is not False
        or plan.research_performance_authorized is not False
    ):
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment Apply binding differs"
        )


def _publish(
    *,
    root: Path,
    target: Path,
    evidence: CanonicalSplitAdjustmentPublicationPlanEvidence,
) -> None:
    _reject_symlink_chain(root, target)
    _mkdirs_durable(target.parent, root)
    staging = target.parent / (
        f".{target.name}.staging.{evidence.plan.logical_fingerprint[:16]}"
    )
    if os.path.lexists(target) or os.path.lexists(staging):
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment target or staging path already exists"
        )
    staging.mkdir(mode=0o755)
    staging.chmod(0o755)
    try:
        for artifact in evidence.plan.artifacts:
            source = Path(artifact.source_path)
            _verify_source(source, artifact.size, artifact.sha256)
            destination = staging / artifact.file_name
            shutil.copyfile(source, destination)
            destination.chmod(0o644)
            _fsync_file(destination)
            if (
                destination.stat().st_size != artifact.size
                or _file_sha256(destination) != artifact.sha256
            ):
                raise CanonicalSplitAdjustmentPublicationApplyError(
                    "staged canonical split-adjustment artifact differs"
                )
        _fsync_directory(staging)
        if os.path.lexists(target):
            raise CanonicalSplitAdjustmentPublicationApplyError(
                "canonical split-adjustment target appeared during staging"
            )
        staging.rename(target)
        _fsync_directory(target.parent)
    except Exception as exc:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        if isinstance(exc, CanonicalSplitAdjustmentPublicationApplyError):
            raise
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment atomic publication failed"
        ) from exc
    _verify_target(root, target, evidence.plan.publication)


def _verify_target(
    root: Path,
    target: Path,
    expected: CanonicalSplitAdjustmentPublicationV1,
) -> CanonicalSplitAdjustmentPublicationRead:
    try:
        canonical = read_canonical_split_adjustment_publication(
            data_root=root,
            publication_root=target,
        )
    except CanonicalSplitAdjustmentPersistenceError as exc:
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment publication failed formal reread"
        ) from exc
    if canonical.publication != expected:
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment publication differs from plan"
        )
    return canonical


def _verify_source(path: Path, size: int, sha256: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment source artifact is unavailable"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or metadata.st_uid != os.getuid()
        or metadata.st_size != size
        or _file_sha256(path) != sha256
    ):
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment source artifact differs from plan"
        )


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment data root is not approved"
        )
    return resolved


def _mkdirs_durable(path: Path, root: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        if current == root or root not in current.parents:
            raise CanonicalSplitAdjustmentPublicationApplyError(
                "canonical split-adjustment path escaped the data root"
            )
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment publication parent is unsafe"
        )
    for item in reversed(missing):
        item.mkdir(mode=0o755)
        item.chmod(0o755)
        _fsync_directory(item.parent)
    _reject_symlink_chain(root, path)


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "canonical split-adjustment path escaped the data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise CanonicalSplitAdjustmentPublicationApplyError(
                "canonical split-adjustment publication path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _validate_fingerprint(value: str, label: str) -> None:
    if len(value) != _SHA256_LENGTH or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise CanonicalSplitAdjustmentPublicationApplyError(f"{label} is malformed")


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise CanonicalSplitAdjustmentPublicationApplyError(
            "network is prohibited during canonical split-adjustment Apply"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
