"""Recoverable physical-first Apply for bounded corporate-action observations."""

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

from tip_api.contracts.market_data.v1 import (
    CorporateActionSourceApplyPlanV1,
    CorporateActionSourcePlanArtifactV1,
    corporate_action_source_publication_bytes,
)
from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.corporate_action_source_canonical import (
    CanonicalCorporateActionSourceError,
    read_canonical_corporate_action_source,
)
from tip_api.services.historical_corporate_action_source_publication_plan import (
    CorporateActionSourcePublicationPlanError,
    CorporateActionSourcePublicationPlanEvidence,
    RecoveryInventoryReader,
    read_corporate_action_source_publication_plan,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
LOCK_ROOT = Path("/tmp")
PUBLICATION_FILE_NAME = "manifest.json"
_SHA256_LENGTH = 64


class CorporateActionSourceApplyError(RuntimeError):
    """Raised when bounded corporate-action publication cannot be applied."""


@dataclass(frozen=True, slots=True)
class CorporateActionSourceApplyResult:
    status: str
    plan_sha256: str
    plan_logical_fingerprint: str
    expected_current_state_fingerprint: str
    post_state_fingerprint: str
    published_partition_count: int
    reused_partition_count: int
    publication_marker_published: bool
    publication_marker_reused: bool
    published_file_count: int
    published_bytes: int
    formal_reread_record_count: int
    publication_fingerprint: str
    publication_sha256: str
    outside_inventory_fingerprint: str
    external_request_count: int = 0
    overwritten_partition_count: int = 0
    deleted_partition_count: int = 0
    canonical_corporate_action_authorized: bool = False
    adjustment_ledger_authorized: bool = False
    historical_coverage_authorized: bool = False
    research_performance_authorized: bool = False


InventoryReader = Callable[[Path], str]


def apply_approved_corporate_action_source_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_current_state_fingerprint: str,
    data_root: Path,
    verify_then_complete: bool = False,
    inventory_reader: InventoryReader = inventory_fingerprint,
    recovery_inventory_reader: RecoveryInventoryReader | None = None,
) -> CorporateActionSourceApplyResult:
    """Apply one exact plan or verify and complete one exact interrupted prefix."""

    root = _validated_data_root(data_root)
    for value, label in (
        (approved_plan_sha256, "approved plan SHA-256"),
        (expected_plan_logical_fingerprint, "expected plan fingerprint"),
        (expected_current_state_fingerprint, "expected current-state fingerprint"),
    ):
        _validate_fingerprint(value, label)
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
        data_root=root,
    )
    lock_path = LOCK_ROOT / (
        "tip-same-day-catchup-"
        + hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
        + ".lock"
    )
    try:
        descriptor = os.open(
            lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
    except OSError as exc:
        raise CorporateActionSourceApplyError(
            "corporate-action publication lock is unavailable"
        ) from exc

    with os.fdopen(descriptor, "r+b") as lock:
        metadata = os.fstat(lock.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise CorporateActionSourceApplyError(
                "corporate-action publication lock custody differs"
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
            raise CorporateActionSourceApplyError(
                "corporate-action plan changed before locked execution"
            )
        _validate_execution_binding(
            evidence=locked,
            approved_plan_sha256=approved_plan_sha256,
            expected_plan_logical_fingerprint=expected_plan_logical_fingerprint,
            expected_current_state_fingerprint=expected_current_state_fingerprint,
            data_root=root,
        )
        plan = locked.plan
        published_partitions = 0
        reused_partitions = 0
        marker_published = False
        marker_reused = False
        published_files = 0
        published_bytes = 0
        with _network_prohibited():
            for partition_path in plan.target_partition_paths:
                target = Path(partition_path)
                artifacts = tuple(
                    item for item in plan.artifacts if Path(item.target_path).parent == target
                )
                if os.path.lexists(target):
                    if not verify_then_complete:
                        raise CorporateActionSourceApplyError(
                            "corporate-action target already exists"
                        )
                    _verify_partition(root, target, artifacts)
                    reused_partitions += 1
                else:
                    _publish_partition(
                        root=root,
                        target=target,
                        artifacts=artifacts,
                        plan_fingerprint=plan.logical_fingerprint,
                    )
                    published_partitions += 1
                    published_files += len(artifacts)
                    published_bytes += sum(item.size for item in artifacts)

            marker_target = Path(plan.target_publication_partition)
            marker_path = marker_target / PUBLICATION_FILE_NAME
            if os.path.lexists(marker_target):
                if not verify_then_complete:
                    raise CorporateActionSourceApplyError(
                        "corporate-action marker target already exists"
                    )
                _verify_marker(marker_target, plan)
                marker_reused = True
            else:
                _publish_marker(root=root, target=marker_target, plan=plan)
                marker_published = True
                published_files += 1
                published_bytes += plan.publication_manifest_bytes
            try:
                canonical = read_canonical_corporate_action_source(
                    data_root=root, publication_path=marker_path
                )
            except CanonicalCorporateActionSourceError as exc:
                raise CorporateActionSourceApplyError(
                    "canonical corporate-action source formal reread failed"
                ) from exc
            exclusions = _target_exclusions(plan)
            outside = inventory_fingerprint(root, exclude_prefixes=exclusions)
            if outside != expected_current_state_fingerprint:
                raise CorporateActionSourceApplyError(
                    "canonical inventory outside corporate-action targets changed"
                )
            post_state = inventory_reader(root)

    return CorporateActionSourceApplyResult(
        status="verified_then_completed" if verify_then_complete else "applied",
        plan_sha256=approved_plan_sha256,
        plan_logical_fingerprint=expected_plan_logical_fingerprint,
        expected_current_state_fingerprint=expected_current_state_fingerprint,
        post_state_fingerprint=post_state,
        published_partition_count=published_partitions,
        reused_partition_count=reused_partitions,
        publication_marker_published=marker_published,
        publication_marker_reused=marker_reused,
        published_file_count=published_files,
        published_bytes=published_bytes,
        formal_reread_record_count=len(canonical.records),
        publication_fingerprint=canonical.publication.logical_fingerprint,
        publication_sha256=canonical.publication_sha256,
        outside_inventory_fingerprint=outside,
    )


def _read_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    verify_then_complete: bool,
    inventory_reader: InventoryReader,
    recovery_inventory_reader: RecoveryInventoryReader | None,
) -> CorporateActionSourcePublicationPlanEvidence:
    try:
        return read_corporate_action_source_publication_plan(
            plan_path=plan_path,
            approved_plan_sha256=approved_plan_sha256,
            verify_then_complete=verify_then_complete,
            inventory_reader=inventory_reader,
            recovery_inventory_reader=recovery_inventory_reader,
        )
    except CorporateActionSourcePublicationPlanError as exc:
        raise CorporateActionSourceApplyError(
            "corporate-action Apply plan failed formal reread"
        ) from exc


def _validate_execution_binding(
    *,
    evidence: CorporateActionSourcePublicationPlanEvidence,
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
        or plan.operation != "publish_bounded_corporate_action_source"
        or plan.apply_authorized is not False
        or plan.canonical_corporate_action_authorized is not False
        or plan.adjustment_ledger_authorized is not False
        or plan.historical_coverage_authorized is not False
        or plan.research_performance_authorized is not False
    ):
        raise CorporateActionSourceApplyError(
            "corporate-action Apply execution binding differs"
        )


def _publish_partition(
    *,
    root: Path,
    target: Path,
    artifacts: tuple[CorporateActionSourcePlanArtifactV1, ...],
    plan_fingerprint: str,
) -> None:
    _reject_symlink_chain(root, target)
    _mkdirs_durable(target.parent, root)
    staging = _staging_path(target, plan_fingerprint)
    if os.path.lexists(target) or os.path.lexists(staging):
        raise CorporateActionSourceApplyError(
            "corporate-action target or staging path already exists"
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
                raise CorporateActionSourceApplyError(
                    "staged corporate-action artifact differs"
                )
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise
    _verify_partition(root, target, artifacts)


def _publish_marker(
    *, root: Path, target: Path, plan: CorporateActionSourceApplyPlanV1
) -> None:
    _reject_symlink_chain(root, target)
    _mkdirs_durable(target.parent, root)
    staging = _staging_path(target, plan.logical_fingerprint)
    if os.path.lexists(target) or os.path.lexists(staging):
        raise CorporateActionSourceApplyError(
            "corporate-action marker target or staging path already exists"
        )
    staging.mkdir(mode=0o755)
    staging.chmod(0o755)
    try:
        payload = corporate_action_source_publication_bytes(plan.publication)
        if (
            len(payload) != plan.publication_manifest_bytes
            or hashlib.sha256(payload).hexdigest()
            != plan.publication_manifest_sha256
        ):
            raise CorporateActionSourceApplyError(
                "corporate-action marker bytes differ from plan"
            )
        destination = staging / PUBLICATION_FILE_NAME
        descriptor = os.open(
            destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o644
        )
        try:
            _write_all(descriptor, payload)
            os.fchmod(descriptor, 0o644)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise
    _verify_marker(target, plan)


def _verify_partition(
    root: Path,
    target: Path,
    artifacts: tuple[CorporateActionSourcePlanArtifactV1, ...],
) -> None:
    if (
        target.is_symlink()
        or not target.is_dir()
        or stat.S_IMODE(target.stat().st_mode) != 0o755
        or {item.name for item in target.iterdir()}
        != {item.file_name for item in artifacts}
    ):
        raise CorporateActionSourceApplyError(
            "completed corporate-action partition differs"
        )
    for artifact in artifacts:
        path = target / artifact.file_name
        _regular_file(path, expected_mode=0o644)
        if path.stat().st_size != artifact.size or _file_sha256(path) != artifact.sha256:
            raise CorporateActionSourceApplyError(
                "completed corporate-action artifact differs"
            )
    try:
        ParquetHistoricalResearchRepository(root).read_corporate_action_observations(
            target
        )
    except Exception as exc:
        raise CorporateActionSourceApplyError(
            "completed corporate-action partition failed formal reread"
        ) from exc


def _verify_marker(target: Path, plan: CorporateActionSourceApplyPlanV1) -> None:
    if (
        target.is_symlink()
        or not target.is_dir()
        or stat.S_IMODE(target.stat().st_mode) != 0o755
        or {item.name for item in target.iterdir()} != {PUBLICATION_FILE_NAME}
    ):
        raise CorporateActionSourceApplyError(
            "completed corporate-action marker target differs"
        )
    path = target / PUBLICATION_FILE_NAME
    _regular_file(path, expected_mode=0o644)
    payload = path.read_bytes()
    if (
        len(payload) != plan.publication_manifest_bytes
        or hashlib.sha256(payload).hexdigest() != plan.publication_manifest_sha256
        or payload != corporate_action_source_publication_bytes(plan.publication)
    ):
        raise CorporateActionSourceApplyError(
            "completed corporate-action publication marker differs"
        )


def _verify_source(path: Path, artifact: CorporateActionSourcePlanArtifactV1) -> None:
    if path.is_symlink() or not path.is_file():
        raise CorporateActionSourceApplyError(
            "corporate-action source artifact is unavailable"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_size != artifact.size
        or _file_sha256(path) != artifact.sha256
    ):
        raise CorporateActionSourceApplyError(
            "corporate-action source artifact differs from plan"
        )


def _target_exclusions(plan: CorporateActionSourceApplyPlanV1) -> tuple[Path, ...]:
    return tuple(Path(item) for item in plan.target_partition_paths) + (
        Path(plan.target_publication_partition),
    )


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CorporateActionSourceApplyError(
            "corporate-action canonical data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CorporateActionSourceApplyError(
            "corporate-action data root is not the approved Dell root"
        )
    return resolved


def _mkdirs_durable(path: Path, root: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        if current == root or root not in current.parents:
            raise CorporateActionSourceApplyError(
                "corporate-action publication path escaped the data root"
            )
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise CorporateActionSourceApplyError(
            "corporate-action publication parent is unsafe"
        )
    for item in reversed(missing):
        item.mkdir(mode=0o755)
        item.chmod(0o755)
        _fsync_directory(item.parent)
    _reject_symlink_chain(root, path)


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise CorporateActionSourceApplyError(
            "corporate-action publication path escaped the data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise CorporateActionSourceApplyError(
                "corporate-action publication path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _regular_file(path: Path, *, expected_mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise CorporateActionSourceApplyError(
            "corporate-action publication artifact is unavailable"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != expected_mode
        or metadata.st_uid != os.getuid()
    ):
        raise CorporateActionSourceApplyError(
            "corporate-action publication artifact custody differs"
        )


def _staging_path(target: Path, plan_fingerprint: str) -> Path:
    return target.parent / f".{target.name}.staging.{plan_fingerprint[:16]}"


def _validate_fingerprint(value: str, label: str) -> None:
    if len(value) != _SHA256_LENGTH or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise CorporateActionSourceApplyError(f"{label} is malformed")


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise CorporateActionSourceApplyError(
                "corporate-action publication write did not progress"
            )
        remaining = remaining[written:]


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise CorporateActionSourceApplyError(
            "network is disabled during corporate-action Apply"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
