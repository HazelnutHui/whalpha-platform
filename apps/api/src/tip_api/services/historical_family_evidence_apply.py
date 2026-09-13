"""Recoverable exact-plan Apply for historical family evidence."""

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
    CurrentHistoricalFamilyEvidencePlanItemV1,
    historical_dataset_coverage_evidence_bytes,
)
from tip_api.persistence.parquet.historical_coverage import (
    HistoricalDatasetEvidenceWriteResult,
    ParquetHistoricalCoverageRepository,
)
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.historical_family_evidence_publication_plan import (
    HistoricalFamilyEvidencePublicationPlanEvidence,
    read_current_historical_family_evidence_publication_plan,
    read_identity_extension_historical_family_evidence_publication_plan,
    read_reconciled_eod_historical_family_evidence_publication_plan,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
LOCK_ROOT = Path("/tmp")
_SHA256_LENGTH = 64


class HistoricalFamilyEvidenceApplyError(RuntimeError):
    """Fail-closed error for exact family-evidence publication."""


@dataclass(frozen=True, slots=True)
class HistoricalFamilyEvidenceApplyResult:
    status: str
    plan_sha256: str
    plan_logical_fingerprint: str
    family_set_fingerprint: str
    pre_apply_outside_inventory_fingerprint: str
    post_apply_outside_inventory_fingerprint: str
    post_state_fingerprint: str
    published_families: tuple[str, ...]
    reused_families: tuple[str, ...]
    published_file_count: int
    published_bytes: int
    formal_reread_family_count: int
    external_request_count: int = 0
    overwritten_partition_count: int = 0
    deleted_partition_count: int = 0
    historical_coverage_authorized: bool = False
    research_development_authorized: bool = False
    research_performance_authorized: bool = False


InventoryReader = Callable[[Path], str]
OutsideInventoryReader = Callable[[Path, tuple[Path, ...]], str]
PlanReader = Callable[..., HistoricalFamilyEvidencePublicationPlanEvidence]


def apply_approved_current_historical_family_evidence_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_family_set_fingerprint: str,
    data_root: Path,
    verify_then_complete: bool = False,
    inventory_reader: InventoryReader = inventory_fingerprint,
    outside_inventory_reader: OutsideInventoryReader | None = None,
) -> HistoricalFamilyEvidenceApplyResult:
    """Apply, recover, or verify one exact rolling-current plan."""

    return _apply_approved_historical_family_evidence_plan(
        plan_path=plan_path,
        approved_plan_sha256=approved_plan_sha256,
        expected_plan_logical_fingerprint=expected_plan_logical_fingerprint,
        expected_family_set_fingerprint=expected_family_set_fingerprint,
        data_root=data_root,
        plan_reader=read_current_historical_family_evidence_publication_plan,
        expected_operation="publish_current_historical_family_evidence",
        expected_family_count=2,
        verify_then_complete=verify_then_complete,
        inventory_reader=inventory_reader,
        outside_inventory_reader=outside_inventory_reader,
    )


def apply_approved_reconciled_eod_historical_family_evidence_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_family_set_fingerprint: str,
    data_root: Path,
    verify_then_complete: bool = False,
    inventory_reader: InventoryReader = inventory_fingerprint,
    outside_inventory_reader: OutsideInventoryReader | None = None,
) -> HistoricalFamilyEvidenceApplyResult:
    """Apply, recover, or verify one exact reconciled-edition plan."""

    return _apply_approved_historical_family_evidence_plan(
        plan_path=plan_path,
        approved_plan_sha256=approved_plan_sha256,
        expected_plan_logical_fingerprint=expected_plan_logical_fingerprint,
        expected_family_set_fingerprint=expected_family_set_fingerprint,
        data_root=data_root,
        plan_reader=(
            read_reconciled_eod_historical_family_evidence_publication_plan
        ),
        expected_operation="publish_reconciled_eod_historical_family_evidence",
        expected_family_count=2,
        verify_then_complete=verify_then_complete,
        inventory_reader=inventory_reader,
        outside_inventory_reader=outside_inventory_reader,
    )


def apply_approved_identity_extension_historical_family_evidence_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_family_set_fingerprint: str,
    data_root: Path,
    verify_then_complete: bool = False,
    inventory_reader: InventoryReader = inventory_fingerprint,
    outside_inventory_reader: OutsideInventoryReader | None = None,
) -> HistoricalFamilyEvidenceApplyResult:
    """Apply, recover, or verify one exact Identity-only extension plan."""

    return _apply_approved_historical_family_evidence_plan(
        plan_path=plan_path,
        approved_plan_sha256=approved_plan_sha256,
        expected_plan_logical_fingerprint=expected_plan_logical_fingerprint,
        expected_family_set_fingerprint=expected_family_set_fingerprint,
        data_root=data_root,
        plan_reader=(
            read_identity_extension_historical_family_evidence_publication_plan
        ),
        expected_operation=(
            "publish_identity_extension_historical_family_evidence"
        ),
        expected_family_count=1,
        verify_then_complete=verify_then_complete,
        inventory_reader=inventory_reader,
        outside_inventory_reader=outside_inventory_reader,
    )


def _apply_approved_historical_family_evidence_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_family_set_fingerprint: str,
    data_root: Path,
    plan_reader: PlanReader,
    expected_operation: str,
    expected_family_count: int,
    verify_then_complete: bool,
    inventory_reader: InventoryReader,
    outside_inventory_reader: OutsideInventoryReader | None,
) -> HistoricalFamilyEvidenceApplyResult:
    """Shared execution mechanics after a source-specific reader is selected."""

    root = _validated_data_root(data_root)
    for value, label in (
        (approved_plan_sha256, "approved plan SHA-256"),
        (expected_plan_logical_fingerprint, "expected plan fingerprint"),
        (expected_family_set_fingerprint, "expected family-set fingerprint"),
    ):
        _validate_fingerprint(value, label)
    evidence = _read_plan(
        plan_path=plan_path,
        approved_plan_sha256=approved_plan_sha256,
        verify_then_complete=verify_then_complete,
        plan_reader=plan_reader,
    )
    _validate_execution_binding(
        evidence=evidence,
        approved_plan_sha256=approved_plan_sha256,
        expected_plan_logical_fingerprint=expected_plan_logical_fingerprint,
        expected_family_set_fingerprint=expected_family_set_fingerprint,
        data_root=root,
        expected_operation=expected_operation,
        expected_family_count=expected_family_count,
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
        raise HistoricalFamilyEvidenceApplyError(
            "family-evidence publication lock is unavailable"
        ) from exc

    with os.fdopen(descriptor, "r+b") as lock:
        lock_metadata = os.fstat(lock.fileno())
        if (
            not stat.S_ISREG(lock_metadata.st_mode)
            or lock_metadata.st_uid != os.getuid()
        ):
            raise HistoricalFamilyEvidenceApplyError(
                "family-evidence publication lock custody differs"
            )
        os.fchmod(lock.fileno(), 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        locked = _read_plan(
            plan_path=plan_path,
            approved_plan_sha256=approved_plan_sha256,
            verify_then_complete=verify_then_complete,
            plan_reader=plan_reader,
        )
        if locked != evidence:
            raise HistoricalFamilyEvidenceApplyError(
                "family-evidence plan changed before locked execution"
            )
        _validate_execution_binding(
            evidence=locked,
            approved_plan_sha256=approved_plan_sha256,
            expected_plan_logical_fingerprint=(
                expected_plan_logical_fingerprint
            ),
            expected_family_set_fingerprint=expected_family_set_fingerprint,
            data_root=root,
            expected_operation=expected_operation,
            expected_family_count=expected_family_count,
        )
        exclusions = _inventory_exclusions(root=root, evidence=locked)
        outside_reader = outside_inventory_reader or _outside_inventory_fingerprint
        with _network_prohibited():
            before_outside = outside_reader(root, exclusions)
            published: list[str] = []
            reused: list[str] = []
            published_bytes = 0
            for item in locked.plan.families:
                target = (root / item.target_path).parent
                if os.path.lexists(target):
                    if not verify_then_complete:
                        raise HistoricalFamilyEvidenceApplyError(
                            "family-evidence target already exists"
                        )
                    _verify_family_target(root=root, item=item)
                    reused.append(item.family.value)
                else:
                    _publish_family_target(
                        root=root,
                        item=item,
                        plan_fingerprint=locked.plan.logical_fingerprint,
                    )
                    published.append(item.family.value)
                    published_bytes += item.evidence_manifest_bytes

            reread = tuple(
                _verify_family_target(root=root, item=item)
                for item in locked.plan.families
            )
            after_outside = outside_reader(root, exclusions)
            if after_outside != before_outside:
                raise HistoricalFamilyEvidenceApplyError(
                    "canonical inventory outside planned targets changed during Apply"
                )
            post_state = inventory_reader(root)

    return HistoricalFamilyEvidenceApplyResult(
        status=(
            "verified_then_completed" if verify_then_complete else "applied"
        ),
        plan_sha256=approved_plan_sha256,
        plan_logical_fingerprint=expected_plan_logical_fingerprint,
        family_set_fingerprint=expected_family_set_fingerprint,
        pre_apply_outside_inventory_fingerprint=before_outside,
        post_apply_outside_inventory_fingerprint=after_outside,
        post_state_fingerprint=post_state,
        published_families=tuple(published),
        reused_families=tuple(reused),
        published_file_count=len(published),
        published_bytes=published_bytes,
        formal_reread_family_count=len(reread),
    )


def _read_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    verify_then_complete: bool,
    plan_reader: PlanReader,
) -> HistoricalFamilyEvidencePublicationPlanEvidence:
    try:
        return plan_reader(
            plan_path=plan_path,
            approved_plan_sha256=approved_plan_sha256,
            verify_then_complete=verify_then_complete,
        )
    except Exception as exc:
        raise HistoricalFamilyEvidenceApplyError(
            "family-evidence Apply plan failed formal reread"
        ) from exc


def _validate_execution_binding(
    *,
    evidence: HistoricalFamilyEvidencePublicationPlanEvidence,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_family_set_fingerprint: str,
    data_root: Path,
    expected_operation: str,
    expected_family_count: int,
) -> None:
    plan = evidence.plan
    if (
        evidence.plan_sha256 != approved_plan_sha256
        or plan.logical_fingerprint != expected_plan_logical_fingerprint
        or plan.family_set_fingerprint != expected_family_set_fingerprint
        or Path(plan.data_root) != data_root
        or plan.operation != expected_operation
        or len(plan.families) != expected_family_count
        or plan.inventory_change_file_count != expected_family_count
        or plan.target_absent_count != expected_family_count
        or plan.source_formal_read_complete is not True
        or plan.target_absence_verified is not True
        or plan.recovery_policy != "verify_exact_then_complete"
        or plan.external_request_count != 0
        or plan.canonical_data_write_count != 0
        or plan.apply_authorized is not False
        or plan.historical_coverage_authorized is not False
        or plan.research_development_authorized is not False
        or plan.research_performance_authorized is not False
    ):
        raise HistoricalFamilyEvidenceApplyError(
            "family-evidence Apply execution binding differs"
        )


def _publish_family_target(
    *,
    root: Path,
    item: CurrentHistoricalFamilyEvidencePlanItemV1,
    plan_fingerprint: str,
) -> None:
    target_file = root / item.target_path
    target = target_file.parent
    _reject_symlink_chain(root, target)
    _mkdirs_durable(target.parent, root)
    staging = _staging_path(target, plan_fingerprint)
    if os.path.lexists(target) or os.path.lexists(staging):
        raise HistoricalFamilyEvidenceApplyError(
            "family-evidence target or staging path already exists"
        )
    staging.mkdir(mode=0o755)
    staging.chmod(0o755)
    staging_metadata = staging.stat()
    try:
        payload = historical_dataset_coverage_evidence_bytes(item.evidence)
        if (
            len(payload) != item.evidence_manifest_bytes
            or hashlib.sha256(payload).hexdigest()
            != item.evidence_manifest_sha256
        ):
            raise HistoricalFamilyEvidenceApplyError(
                "family-evidence planned manifest bytes differ"
            )
        destination = staging / target_file.name
        descriptor = os.open(
            destination,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
            0o644,
        )
        try:
            remaining = memoryview(payload)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise HistoricalFamilyEvidenceApplyError(
                        "family-evidence manifest write did not progress"
                    )
                remaining = remaining[written:]
            os.fchmod(descriptor, 0o644)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        _remove_owned_staging(
            staging,
            expected_device=staging_metadata.st_dev,
            expected_inode=staging_metadata.st_ino,
        )
        raise
    _verify_family_target(root=root, item=item)


def _verify_family_target(
    *,
    root: Path,
    item: CurrentHistoricalFamilyEvidencePlanItemV1,
) -> HistoricalDatasetEvidenceWriteResult:
    target_file = root / item.target_path
    target = target_file.parent
    target_metadata = target.lstat() if os.path.lexists(target) else None
    if (
        target_metadata is None
        or not stat.S_ISDIR(target_metadata.st_mode)
        or target_metadata.st_uid != os.getuid()
        or stat.S_IMODE(target_metadata.st_mode) != 0o755
        or {candidate.name for candidate in target.iterdir()}
        != {target_file.name}
    ):
        raise HistoricalFamilyEvidenceApplyError(
            "completed family-evidence target differs"
        )
    _regular_file(target_file, expected_mode=0o644)
    if (
        target_file.stat().st_size != item.evidence_manifest_bytes
        or _file_sha256(target_file) != item.evidence_manifest_sha256
    ):
        raise HistoricalFamilyEvidenceApplyError(
            "completed family-evidence manifest differs"
        )
    try:
        reread = ParquetHistoricalCoverageRepository(root).read_dataset_evidence(
            target_file
        )
    except Exception as exc:
        raise HistoricalFamilyEvidenceApplyError(
            "completed family-evidence formal reread failed"
        ) from exc
    if (
        reread.evidence != item.evidence
        or reread.evidence_path != target_file
        or reread.physical_sha256 != item.evidence_manifest_sha256
    ):
        raise HistoricalFamilyEvidenceApplyError(
            "completed family-evidence identity differs"
        )
    return reread


def _inventory_exclusions(
    *,
    root: Path,
    evidence: HistoricalFamilyEvidencePublicationPlanEvidence,
) -> tuple[Path, ...]:
    targets = tuple(
        (root / item.target_path).parent for item in evidence.plan.families
    )
    staging = tuple(
        _staging_path(target, evidence.plan.logical_fingerprint)
        for target in targets
    )
    return (*targets, *staging)


def _outside_inventory_fingerprint(
    root: Path,
    exclusions: tuple[Path, ...],
) -> str:
    return inventory_fingerprint(root, exclude_prefixes=exclusions)


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise HistoricalFamilyEvidenceApplyError(
            "family-evidence data root is unavailable"
        )
    try:
        resolved = path.resolve(strict=True)
        approved = APPROVED_DATA_ROOT.resolve(strict=True)
    except OSError as exc:
        raise HistoricalFamilyEvidenceApplyError(
            "family-evidence data root is unavailable"
        ) from exc
    if resolved != path or resolved != approved:
        raise HistoricalFamilyEvidenceApplyError(
            "family-evidence data root is not the approved Dell root"
        )
    return resolved


def _mkdirs_durable(path: Path, root: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        if current == root or root not in current.parents:
            raise HistoricalFamilyEvidenceApplyError(
                "family-evidence publication path escapes data root"
            )
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise HistoricalFamilyEvidenceApplyError(
            "family-evidence publication parent is unsafe"
        )
    for item in reversed(missing):
        item.mkdir(mode=0o755)
        item.chmod(0o755)
        _fsync_directory(item.parent)
    _reject_symlink_chain(root, path)


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise HistoricalFamilyEvidenceApplyError(
            "family-evidence publication path escapes data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise HistoricalFamilyEvidenceApplyError(
                "family-evidence publication path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _regular_file(path: Path, *, expected_mode: int) -> None:
    if not os.path.lexists(path):
        raise HistoricalFamilyEvidenceApplyError(
            "family-evidence artifact is not a regular file"
        )
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != expected_mode
    ):
        raise HistoricalFamilyEvidenceApplyError(
            "family-evidence artifact mode differs"
        )


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


def _staging_path(target: Path, plan_fingerprint: str) -> Path:
    return target.parent / (
        f".{target.name}.staging.{plan_fingerprint[:16]}"
    )


def _validate_fingerprint(value: str, label: str) -> None:
    if len(value) != _SHA256_LENGTH or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise HistoricalFamilyEvidenceApplyError(f"{label} is malformed")


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise HistoricalFamilyEvidenceApplyError(
            "network access is disabled during family-evidence Apply"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    socket.getaddrinfo = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
