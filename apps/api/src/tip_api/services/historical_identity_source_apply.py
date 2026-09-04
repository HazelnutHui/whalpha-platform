"""Atomic Apply and fail-closed recovery for historical Identity source custody."""

from __future__ import annotations

import fcntl
import hashlib
import multiprocessing
import os
import shutil
import socket
import stat
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from tip_api.contracts.market_data.v1.historical_identity_source_apply_plan import (
    HistoricalIdentitySourceApplyPlanV1,
    HistoricalIdentitySourcePlanArtifactV1,
    HistoricalIdentitySourcePlanSessionV1,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services import historical_identity_source_custody as custody_service
from tip_api.services.historical_identity_source_apply_plan import (
    HistoricalIdentitySourceApplyPlanError,
    HistoricalIdentitySourceApplyPlanEvidence,
    RecoveryInventoryReader,
    read_historical_identity_source_apply_plan,
)
from tip_api.services.historical_identity_source_custody import (
    HistoricalIdentitySourceCustodyError,
    read_historical_identity_source_custody,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
LOCK_ROOT = Path("/tmp")
_SHA256_LENGTH = 64


class HistoricalIdentitySourceApplyError(RuntimeError):
    """Fail-closed error for canonical historical source publication."""


@dataclass(frozen=True, slots=True)
class HistoricalIdentitySourceApplyResult:
    status: str
    plan_sha256: str
    plan_logical_fingerprint: str
    expected_current_state_fingerprint: str
    post_state_fingerprint: str
    session_count: int
    published_partition_count: int
    reused_partition_count: int
    published_file_count: int
    published_bytes: int
    formal_reread_session_count: int
    external_request_count: int = 0
    overwritten_partition_count: int = 0
    deleted_partition_count: int = 0
    historical_coverage_authorized: bool = False
    universe_membership_authorized: bool = False
    research_performance_authorized: bool = False


InventoryReader = Callable[[Path], str]


def apply_approved_historical_identity_source_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_current_state_fingerprint: str,
    data_root: Path,
    verify_then_complete: bool = False,
    formal_read_workers: int = 1,
    inventory_reader: InventoryReader = inventory_fingerprint,
    recovery_inventory_reader: RecoveryInventoryReader | None = None,
) -> HistoricalIdentitySourceApplyResult:
    """Publish or recover one exact, inventory-bound historical source plan."""

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
    if not 1 <= formal_read_workers <= 4:
        raise HistoricalIdentitySourceApplyError(
            "formal-read workers must be between one and four"
        )
    evidence = _read_plan(
        plan_path=plan_path,
        approved_plan_sha256=approved_plan_sha256,
        verify_then_complete=verify_then_complete,
        inventory_reader=inventory_reader,
        recovery_inventory_reader=recovery_inventory_reader,
    )
    _validate_execution_binding(
        plan=evidence.plan,
        plan_sha256=evidence.plan_sha256,
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
        raise HistoricalIdentitySourceApplyError(
            "historical source publication lock is unavailable"
        ) from exc
    with os.fdopen(descriptor, "r+b") as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise HistoricalIdentitySourceApplyError(
                "historical source publication lock is not a regular file"
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
            raise HistoricalIdentitySourceApplyError(
                "historical source Apply plan changed before locked execution"
            )
        _validate_execution_binding(
            plan=locked.plan,
            plan_sha256=locked.plan_sha256,
            approved_plan_sha256=approved_plan_sha256,
            expected_plan_logical_fingerprint=(
                expected_plan_logical_fingerprint
            ),
            expected_current_state_fingerprint=(
                expected_current_state_fingerprint
            ),
            data_root=canonical_root,
        )
        published = 0
        reused = 0
        published_files = 0
        published_bytes = 0
        with _network_prohibited():
            for session in locked.plan.sessions:
                target = _target_partition(locked.plan, session)
                refs = _session_artifacts(locked.plan, session)
                if os.path.lexists(target):
                    if not verify_then_complete:
                        raise HistoricalIdentitySourceApplyError(
                            "historical source target already exists"
                        )
                    _verify_completed_target(target, refs)
                    reused += 1
                    continue
                _publish_partition(
                    data_root=canonical_root,
                    target=target,
                    artifacts=refs,
                    plan_fingerprint=locked.plan.logical_fingerprint,
                )
                published += 1
                published_files += len(refs)
                published_bytes += sum(item.size for item in refs)
            reread_count = _formal_reread_all(
                plan=locked.plan,
                data_root=canonical_root,
                workers=formal_read_workers,
            )
            base_reader = (
                recovery_inventory_reader
                if recovery_inventory_reader is not None
                else _recovery_inventory_fingerprint
            )
            targets = tuple(
                _target_partition(locked.plan, session)
                for session in locked.plan.sessions
            )
            if (
                base_reader(canonical_root, targets)
                != expected_current_state_fingerprint
            ):
                raise HistoricalIdentitySourceApplyError(
                    "canonical inventory outside planned targets changed during Apply"
                )
        post_state = inventory_reader(canonical_root)
    return HistoricalIdentitySourceApplyResult(
        status=(
            "verified_then_completed"
            if verify_then_complete
            else "applied"
        ),
        plan_sha256=approved_plan_sha256,
        plan_logical_fingerprint=expected_plan_logical_fingerprint,
        expected_current_state_fingerprint=expected_current_state_fingerprint,
        post_state_fingerprint=post_state,
        session_count=locked.plan.session_count,
        published_partition_count=published,
        reused_partition_count=reused,
        published_file_count=published_files,
        published_bytes=published_bytes,
        formal_reread_session_count=reread_count,
    )


def _read_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    verify_then_complete: bool,
    inventory_reader: InventoryReader,
    recovery_inventory_reader: RecoveryInventoryReader | None,
) -> HistoricalIdentitySourceApplyPlanEvidence:
    try:
        return read_historical_identity_source_apply_plan(
            plan_path=plan_path,
            approved_plan_sha256=approved_plan_sha256,
            verify_then_complete=verify_then_complete,
            inventory_reader=inventory_reader,
            recovery_inventory_reader=recovery_inventory_reader,
        )
    except HistoricalIdentitySourceApplyPlanError as exc:
        raise HistoricalIdentitySourceApplyError(
            "historical source Apply plan failed formal reread"
        ) from exc


def _validate_execution_binding(
    *,
    plan: HistoricalIdentitySourceApplyPlanV1,
    plan_sha256: str,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_current_state_fingerprint: str,
    data_root: Path,
) -> None:
    if (
        plan_sha256 != approved_plan_sha256
        or plan.logical_fingerprint != expected_plan_logical_fingerprint
        or plan.expected_current_state_fingerprint
        != expected_current_state_fingerprint
        or Path(plan.data_root) != data_root
        or plan.operation != "publish_historical_identity_source_custody"
        or plan.provider != MASSIVE_PROVIDER_ID
        or plan.inventory_change_file_count != 2 * plan.session_count
    ):
        raise HistoricalIdentitySourceApplyError(
            "historical source Apply execution binding differs"
        )


def _session_artifacts(
    plan: HistoricalIdentitySourceApplyPlanV1,
    session: HistoricalIdentitySourcePlanSessionV1,
) -> tuple[HistoricalIdentitySourcePlanArtifactV1, ...]:
    refs = tuple(
        item for item in plan.artifacts if item.session_date == session.session_date
    )
    if tuple(item.file_name for item in refs) != (
        "manifest.json",
        "part-00000.parquet",
    ):
        raise HistoricalIdentitySourceApplyError(
            "historical source session artifact set differs"
        )
    return refs


def _target_partition(
    plan: HistoricalIdentitySourceApplyPlanV1,
    session: HistoricalIdentitySourcePlanSessionV1,
) -> Path:
    return Path(plan.target_dataset_root) / (
        f"as_of_date={session.session_date.isoformat()}"
    )


def _publish_partition(
    *,
    data_root: Path,
    target: Path,
    artifacts: tuple[HistoricalIdentitySourcePlanArtifactV1, ...],
    plan_fingerprint: str,
) -> None:
    _reject_symlink_chain(data_root, target)
    _mkdirs_durable(target.parent, data_root)
    staging = target.parent / f".{target.name}.staging.{plan_fingerprint[:16]}"
    if os.path.lexists(target) or os.path.lexists(staging):
        raise HistoricalIdentitySourceApplyError(
            "historical source target or staging path already exists"
        )
    staging.mkdir(mode=0o755)
    staging.chmod(0o755)
    try:
        for artifact in artifacts:
            source = Path(artifact.source_path)
            _regular_file(source, expected_mode=0o400)
            destination = staging / artifact.file_name
            shutil.copyfile(source, destination)
            destination.chmod(0o644)
            _fsync_file(destination)
            if (
                destination.stat().st_size != artifact.size
                or _file_sha256(destination) != artifact.sha256
            ):
                raise HistoricalIdentitySourceApplyError(
                    "staged historical source artifact differs"
                )
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise
    _verify_completed_target(target, artifacts)


def _verify_completed_target(
    target: Path,
    artifacts: tuple[HistoricalIdentitySourcePlanArtifactV1, ...],
) -> None:
    if (
        target.is_symlink()
        or not target.is_dir()
        or stat.S_IMODE(target.stat().st_mode) != 0o755
    ):
        raise HistoricalIdentitySourceApplyError(
            "completed historical source target directory differs"
        )
    if {item.name for item in target.iterdir()} != {
        "manifest.json",
        "part-00000.parquet",
    }:
        raise HistoricalIdentitySourceApplyError(
            "completed historical source target file set differs"
        )
    for artifact in artifacts:
        path = target / artifact.file_name
        _regular_file(path, expected_mode=0o644)
        if (
            path.stat().st_size != artifact.size
            or _file_sha256(path) != artifact.sha256
        ):
            raise HistoricalIdentitySourceApplyError(
                "completed historical source target artifact differs"
            )


def _formal_reread_all(
    *,
    plan: HistoricalIdentitySourceApplyPlanV1,
    data_root: Path,
    workers: int,
) -> int:
    jobs = tuple((data_root, session) for session in plan.sessions)
    try:
        if workers == 1:
            results = [_formal_read_worker(job) for job in jobs]
        else:
            context = multiprocessing.get_context("spawn")
            with ProcessPoolExecutor(
                max_workers=workers,
                mp_context=context,
                initializer=_initialize_formal_read_worker,
                initargs=(data_root,),
            ) as executor:
                results = list(executor.map(_formal_read_worker, jobs))
    except HistoricalIdentitySourceCustodyError as exc:
        raise HistoricalIdentitySourceApplyError(
            "canonical historical source formal reread failed"
        ) from exc
    expected = tuple(
        (
            item.session_date.isoformat(),
            item.record_count,
            item.manifest_sha256,
            item.parquet_sha256,
            item.logical_fingerprint,
        )
        for item in plan.sessions
    )
    if tuple(results) != expected:
        raise HistoricalIdentitySourceApplyError(
            "canonical historical source formal reread differs from plan"
        )
    return len(results)


def _formal_read_worker(
    job: tuple[Path, HistoricalIdentitySourcePlanSessionV1],
) -> tuple[str, int, str, str, str]:
    data_root, session = job
    value = read_historical_identity_source_custody(
        data_root=data_root,
        provider=MASSIVE_PROVIDER_ID,
        session_date=session.session_date,
    )
    return (
        session.session_date.isoformat(),
        value.manifest.record_count,
        value.manifest_sha256,
        value.manifest.parquet_sha256,
        value.manifest.logical_fingerprint,
    )


def _disable_network_in_worker() -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise HistoricalIdentitySourceApplyError(
            "network access is disabled in historical source Apply workers"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]


def _initialize_formal_read_worker(approved_data_root: Path) -> None:
    # The parent already proved this root against its fixed Dell boundary.
    # Rebind the independently spawned reader process to that exact path.
    custody_service.APPROVED_DATA_ROOT = approved_data_root
    _disable_network_in_worker()


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
        raise HistoricalIdentitySourceApplyError(
            "network access is disabled during historical source Apply"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = (  # type: ignore[assignment]
            original_create_connection
        )


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise HistoricalIdentitySourceApplyError(
            "historical source data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise HistoricalIdentitySourceApplyError(
            "historical source data root is not the approved Dell root"
        )
    return resolved


def _mkdirs_durable(path: Path, root: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        if current == root or root not in current.parents:
            raise HistoricalIdentitySourceApplyError(
                "historical source publication path escapes data root"
            )
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise HistoricalIdentitySourceApplyError(
            "historical source publication parent is unsafe"
        )
    for item in reversed(missing):
        item.mkdir(mode=0o755)
        item.chmod(0o755)
        _fsync_directory(item.parent)
    _reject_symlink_chain(root, path)


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise HistoricalIdentitySourceApplyError(
            "historical source publication path escapes data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise HistoricalIdentitySourceApplyError(
                "historical source publication path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _regular_file(path: Path, *, expected_mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise HistoricalIdentitySourceApplyError(
            "historical source artifact is not a regular file"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != expected_mode
    ):
        raise HistoricalIdentitySourceApplyError(
            "historical source artifact mode differs"
        )


def _validate_fingerprint(value: str, label: str) -> None:
    if len(value) != _SHA256_LENGTH or any(
        char not in "0123456789abcdef" for char in value
    ):
        raise HistoricalIdentitySourceApplyError(f"{label} is malformed")


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
