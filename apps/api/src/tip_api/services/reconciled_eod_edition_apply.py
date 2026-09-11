"""Atomic no-overwrite Apply for one complete reconciled EOD edition."""

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

from tip_api.contracts.market_data.v1 import ReconciledEodEditionApplyArtifactV1
from tip_api.persistence.parquet import reconciled_eod_edition as persistence
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.reconciled_eod_edition_apply_plan import (
    ReconciledEodEditionApplyPlanError,
    ReconciledEodEditionApplyPlanEvidence,
    read_reconciled_eod_edition_apply_plan,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
LOCK_ROOT = Path("/tmp")
_SHA256_LENGTH = 64


class ReconciledEodEditionApplyError(RuntimeError):
    """Fail-closed error for whole-edition canonical publication."""


@dataclass(frozen=True, slots=True)
class ReconciledEodEditionApplyResult:
    status: str
    plan_sha256: str
    plan_logical_fingerprint: str
    edition_id: str
    interval_manifest_fingerprint: str
    pre_apply_outside_inventory_fingerprint: str
    post_apply_outside_inventory_fingerprint: str
    edition_published: bool
    edition_reused: bool
    published_file_count: int
    published_bytes: int
    formal_reread_session_count: int
    formal_reread_record_count: int
    external_request_count: int = 0
    overwritten_partition_count: int = 0
    deleted_partition_count: int = 0
    candidate_authority: bool = False
    production_authority: bool = False
    research_performance_authorized: bool = False


OutsideInventoryReader = Callable[[Path, tuple[Path, ...]], str]


def apply_approved_reconciled_eod_edition_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_current_state_fingerprint: str,
    data_root: Path,
    verify_then_complete: bool = False,
    outside_inventory_reader: OutsideInventoryReader | None = None,
) -> ReconciledEodEditionApplyResult:
    """Apply one exact edition under the global Dell data-writer lock."""

    root = _validated_data_root(data_root)
    for value, label in (
        (approved_plan_sha256, "approved plan SHA-256"),
        (expected_plan_logical_fingerprint, "expected plan fingerprint"),
        (expected_current_state_fingerprint, "expected current-state fingerprint"),
    ):
        _validate_fingerprint(value, label)
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
        raise ReconciledEodEditionApplyError(
            "reconciled EOD publication lock is unavailable"
        ) from exc

    with os.fdopen(descriptor, "r+b") as lock:
        metadata = os.fstat(lock.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise ReconciledEodEditionApplyError(
                "reconciled EOD publication lock custody differs"
            )
        os.fchmod(lock.fileno(), 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        evidence = _read_plan(
            plan_path=plan_path,
            approved_plan_sha256=approved_plan_sha256,
            allow_completed_target=verify_then_complete,
        )
        _validate_execution_binding(
            evidence=evidence,
            approved_plan_sha256=approved_plan_sha256,
            expected_plan_logical_fingerprint=expected_plan_logical_fingerprint,
            expected_current_state_fingerprint=expected_current_state_fingerprint,
            data_root=root,
        )
        plan = evidence.plan
        target = Path(plan.target_edition_path)
        staging = _staging_path(target, plan.logical_fingerprint)
        exclusions = (target, staging)
        outside_reader = outside_inventory_reader or _outside_inventory_fingerprint
        with _network_prohibited():
            before_outside = outside_reader(root, exclusions)
            if before_outside != plan.expected_current_state_fingerprint:
                raise ReconciledEodEditionApplyError(
                    "canonical inventory changed after reconciled EOD planning"
                )
            published = False
            reused = False
            if os.path.lexists(target):
                if not verify_then_complete:
                    raise ReconciledEodEditionApplyError(
                        "reconciled EOD target already exists"
                    )
                completed = _formal_target_read(root=root, evidence=evidence)
                reused = True
            else:
                _publish_edition(
                    root=root,
                    target=target,
                    staging=staging,
                    evidence=evidence,
                )
                completed = _formal_target_read(root=root, evidence=evidence)
                published = True
            after_outside = outside_reader(root, exclusions)
            if after_outside != before_outside:
                raise ReconciledEodEditionApplyError(
                    "canonical inventory outside the edition changed during Apply"
                )

    return ReconciledEodEditionApplyResult(
        status="applied" if published else "verified_then_completed",
        plan_sha256=approved_plan_sha256,
        plan_logical_fingerprint=expected_plan_logical_fingerprint,
        edition_id=plan.edition_id,
        interval_manifest_fingerprint=completed.manifest.logical_fingerprint,
        pre_apply_outside_inventory_fingerprint=before_outside,
        post_apply_outside_inventory_fingerprint=after_outside,
        edition_published=published,
        edition_reused=reused,
        published_file_count=plan.inventory_change_file_count if published else 0,
        published_bytes=plan.inventory_change_bytes if published else 0,
        formal_reread_session_count=len(completed.session_manifests),
        formal_reread_record_count=sum(
            item.diff.rebuilt_record_count for item in completed.session_manifests
        ),
    )


def _read_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    allow_completed_target: bool,
) -> ReconciledEodEditionApplyPlanEvidence:
    try:
        return read_reconciled_eod_edition_apply_plan(
            plan_path=plan_path,
            approved_plan_sha256=approved_plan_sha256,
            allow_completed_target=allow_completed_target,
        )
    except ReconciledEodEditionApplyPlanError as exc:
        raise ReconciledEodEditionApplyError(
            "reconciled EOD Apply plan failed formal reread"
        ) from exc


def _validate_execution_binding(
    *,
    evidence: ReconciledEodEditionApplyPlanEvidence,
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
        or plan.operation != "publish_complete_reconciled_eod_edition"
        or plan.status != "ready_for_separate_apply"
        or plan.candidate_formal_read_complete is not True
        or plan.target_absence_verified is not True
        or plan.current_inventory_bound is not True
        or plan.external_request_count != 0
        or plan.canonical_data_write_count != 0
        or plan.apply_authorized is not False
        or plan.candidate_authority is not False
        or plan.production_authority is not False
        or plan.research_performance_authorized is not False
    ):
        raise ReconciledEodEditionApplyError(
            "reconciled EOD Apply execution binding differs"
        )


def _publish_edition(
    *,
    root: Path,
    target: Path,
    staging: Path,
    evidence: ReconciledEodEditionApplyPlanEvidence,
) -> None:
    _reject_symlink_chain(root, target)
    _mkdirs_durable(target.parent, root)
    if os.path.lexists(target) or os.path.lexists(staging):
        raise ReconciledEodEditionApplyError(
            "reconciled EOD target or staging path already exists"
        )
    staging.mkdir(mode=0o755)
    staging.chmod(0o755)
    staging_metadata = staging.stat()
    try:
        for artifact in evidence.plan.artifacts:
            destination = staging / artifact.relative_path
            if destination.parent != staging:
                if destination.parent.parent != staging:
                    raise ReconciledEodEditionApplyError(
                        "reconciled EOD staging path is unexpectedly nested"
                    )
                if not destination.parent.exists():
                    destination.parent.mkdir(mode=0o755)
                    destination.parent.chmod(0o755)
                elif destination.parent.is_symlink() or not destination.parent.is_dir():
                    raise ReconciledEodEditionApplyError(
                        "reconciled EOD staging directory is unsafe"
                    )
            _copy_verified_artifact(
                source=evidence.candidate.edition_path / artifact.relative_path,
                destination=destination,
                artifact=artifact,
            )
        _verify_staged_inventory(staging=staging, evidence=evidence)
        for directory in sorted(
            (path for path in staging.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        ):
            _fsync_directory(directory)
        _fsync_directory(staging)
        if os.path.lexists(target):
            raise ReconciledEodEditionApplyError(
                "reconciled EOD target appeared during Apply"
            )
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        _remove_owned_staging(
            staging,
            expected_device=staging_metadata.st_dev,
            expected_inode=staging_metadata.st_ino,
        )
        raise


def _copy_verified_artifact(
    *,
    source: Path,
    destination: Path,
    artifact: ReconciledEodEditionApplyArtifactV1,
) -> None:
    try:
        source_descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise ReconciledEodEditionApplyError(
            "reconciled EOD source artifact is unavailable"
        ) from exc
    try:
        source_metadata = os.fstat(source_descriptor)
        if (
            not stat.S_ISREG(source_metadata.st_mode)
            or source_metadata.st_uid != os.getuid()
            or stat.S_IMODE(source_metadata.st_mode) != 0o600
            or source_metadata.st_size != artifact.size
        ):
            raise ReconciledEodEditionApplyError(
                "reconciled EOD source artifact custody differs"
            )
        destination_descriptor = os.open(
            destination,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
            0o644,
        )
        try:
            digest = hashlib.sha256()
            copied = 0
            while True:
                chunk = os.read(source_descriptor, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                copied += len(chunk)
                remaining = memoryview(chunk)
                while remaining:
                    written = os.write(destination_descriptor, remaining)
                    if written <= 0:
                        raise ReconciledEodEditionApplyError(
                            "reconciled EOD artifact copy did not progress"
                        )
                    remaining = remaining[written:]
            if copied != artifact.size or digest.hexdigest() != artifact.sha256:
                raise ReconciledEodEditionApplyError(
                    "reconciled EOD source artifact changed before copy"
                )
            os.fchmod(destination_descriptor, 0o644)
            os.fsync(destination_descriptor)
        finally:
            os.close(destination_descriptor)
    finally:
        os.close(source_descriptor)


def _verify_staged_inventory(
    *,
    staging: Path,
    evidence: ReconciledEodEditionApplyPlanEvidence,
) -> None:
    expected_files = {item.relative_path for item in evidence.plan.artifacts}
    actual_files: set[str] = set()
    for path in staging.rglob("*"):
        if path.is_symlink():
            raise ReconciledEodEditionApplyError(
                "reconciled EOD staged inventory contains a symlink"
            )
        if path.is_file():
            actual_files.add(path.relative_to(staging).as_posix())
            metadata = path.stat()
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o644
            ):
                raise ReconciledEodEditionApplyError(
                    "reconciled EOD staged file custody differs"
                )
        elif path.is_dir():
            metadata = path.stat()
            if (
                metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o755
            ):
                raise ReconciledEodEditionApplyError(
                    "reconciled EOD staged directory custody differs"
                )
        else:
            raise ReconciledEodEditionApplyError(
                "reconciled EOD staged inventory contains an unsupported entry"
            )
    if actual_files != expected_files:
        raise ReconciledEodEditionApplyError(
            "reconciled EOD staged file set differs"
        )


def _formal_target_read(*, root: Path, evidence: ReconciledEodEditionApplyPlanEvidence):
    plan = evidence.plan
    target = Path(plan.target_edition_path)
    for artifact in plan.artifacts:
        destination = target / artifact.relative_path
        if target not in destination.parents:
            raise ReconciledEodEditionApplyError(
                "reconciled EOD target artifact escapes its edition"
            )
        if destination.is_symlink() or not destination.is_file():
            raise ReconciledEodEditionApplyError(
                "reconciled EOD target artifact is unavailable"
            )
        metadata = destination.stat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o644
            or metadata.st_size != artifact.size
        ):
            raise ReconciledEodEditionApplyError(
                "reconciled EOD target artifact custody differs"
            )
        if not artifact.relative_path.endswith(".parquet") and (
            _file_sha256(destination) != artifact.sha256
        ):
            raise ReconciledEodEditionApplyError(
                "reconciled EOD target manifest differs"
            )
    try:
        completed = persistence.validate_reconciled_eod_edition(
            root=root,
            edition_id=plan.edition_id,
        )
    except Exception as exc:
        raise ReconciledEodEditionApplyError(
            "reconciled EOD target failed formal reread"
        ) from exc
    if (
        completed.manifest.logical_fingerprint
        != plan.candidate_interval_manifest_fingerprint
        or len(completed.session_manifests) != plan.candidate_session_count
        or sum(
            item.diff.rebuilt_record_count for item in completed.session_manifests
        )
        != plan.candidate_record_count
    ):
        raise ReconciledEodEditionApplyError(
            "reconciled EOD target summary differs"
        )
    return completed


def _outside_inventory_fingerprint(
    root: Path,
    exclusions: tuple[Path, ...],
) -> str:
    return inventory_fingerprint(root, exclude_prefixes=exclusions)


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ReconciledEodEditionApplyError(
            "canonical data root is unavailable"
        )
    try:
        resolved = path.resolve(strict=True)
        approved = APPROVED_DATA_ROOT.resolve(strict=True)
    except OSError as exc:
        raise ReconciledEodEditionApplyError(
            "canonical data root is unavailable"
        ) from exc
    if resolved != path or resolved != approved:
        raise ReconciledEodEditionApplyError(
            "canonical data root is not the approved Dell root"
        )
    return resolved


def _mkdirs_durable(path: Path, root: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        if current == root or root not in current.parents:
            raise ReconciledEodEditionApplyError(
                "reconciled EOD publication path escapes data root"
            )
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise ReconciledEodEditionApplyError(
            "reconciled EOD publication parent is unsafe"
        )
    for item in reversed(missing):
        item.mkdir(mode=0o755)
        item.chmod(0o755)
        _fsync_directory(item.parent)
    _reject_symlink_chain(root, path)


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise ReconciledEodEditionApplyError(
            "reconciled EOD publication path escapes data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise ReconciledEodEditionApplyError(
                "reconciled EOD publication path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _staging_path(target: Path, plan_fingerprint: str) -> Path:
    return target.parent / f".{target.name}.staging.{plan_fingerprint[:16]}"


def _remove_owned_staging(
    path: Path,
    *,
    expected_device: int,
    expected_inode: int,
) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_dev != expected_device
        or metadata.st_ino != expected_inode
        or metadata.st_uid != os.getuid()
    ):
        return
    shutil.rmtree(path)
    _fsync_directory(path.parent)


def _validate_fingerprint(value: str, label: str) -> None:
    if len(value) != _SHA256_LENGTH or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ReconciledEodEditionApplyError(f"{label} is malformed")


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
        raise ReconciledEodEditionApplyError(
            "network is prohibited during reconciled EOD Apply"
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
