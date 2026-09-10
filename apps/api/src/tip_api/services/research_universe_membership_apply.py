"""Atomic no-overwrite Apply for reconstructed research Membership custody."""

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
from typing import Iterator

from tip_api.contracts.market_data.v1 import (
    ResearchUniverseMembershipPlanArtifactV1,
)
from tip_api.services.research_universe_membership_apply_plan import (
    ResearchUniverseMembershipApplyPlanError,
    ResearchUniverseMembershipApplyPlanEvidence,
    read_research_universe_membership_apply_plan,
)
from tip_api.services.research_universe_membership_canonical import (
    CUSTODY_FILE_NAME,
    CanonicalResearchUniverseMembershipError,
    read_canonical_research_universe_membership,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
LOCK_ROOT = Path("/tmp")
_SHA256_LENGTH = 64


class ResearchUniverseMembershipApplyError(RuntimeError):
    """Fail-closed error for research Membership canonical custody."""


@dataclass(frozen=True, slots=True)
class ResearchUniverseMembershipApplyResult:
    status: str
    plan_sha256: str
    plan_logical_fingerprint: str
    custody_logical_fingerprint: str
    membership_partition_published: bool
    membership_partition_reused: bool
    published_file_count: int
    published_bytes: int
    formal_reread_record_count: int
    external_request_count: int = 0
    overwritten_partition_count: int = 0
    deleted_partition_count: int = 0
    performance_authorized: bool = False
    production_authorized: bool = False


def apply_research_universe_membership_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    data_root: Path,
) -> ResearchUniverseMembershipApplyResult:
    """Apply one exact research Membership plan, or prove exact prior completion."""

    root = _validated_data_root(data_root)
    _validate_fingerprint(approved_plan_sha256, "approved plan SHA-256")
    _validate_fingerprint(
        expected_plan_logical_fingerprint,
        "expected plan logical fingerprint",
    )
    evidence = _read_plan(
        plan_path=plan_path,
        approved_plan_sha256=approved_plan_sha256,
        allow_completed_target=True,
    )
    _validate_execution_binding(
        evidence=evidence,
        approved_plan_sha256=approved_plan_sha256,
        expected_plan_logical_fingerprint=expected_plan_logical_fingerprint,
        data_root=root,
    )
    target = Path(evidence.plan.target_membership_partition)
    lock_path = LOCK_ROOT / (
        "tip-research-membership-"
        + hashlib.sha256(str(target).encode("utf-8")).hexdigest()[:20]
        + ".lock"
    )
    try:
        descriptor = os.open(
            lock_path,
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
        )
    except OSError as exc:
        raise ResearchUniverseMembershipApplyError(
            "research Membership lock is unavailable"
        ) from exc
    with os.fdopen(descriptor, "r+b") as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise ResearchUniverseMembershipApplyError(
                "research Membership lock is not regular"
            )
        os.fchmod(lock.fileno(), 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        locked = _read_plan(
            plan_path=plan_path,
            approved_plan_sha256=approved_plan_sha256,
            allow_completed_target=True,
        )
        if locked != evidence:
            raise ResearchUniverseMembershipApplyError(
                "research Membership Apply plan changed before execution"
            )
        _validate_execution_binding(
            evidence=locked,
            approved_plan_sha256=approved_plan_sha256,
            expected_plan_logical_fingerprint=expected_plan_logical_fingerprint,
            data_root=root,
        )
        plan = locked.plan
        target = Path(plan.target_membership_partition)
        published = False
        reused = False
        with _network_prohibited():
            if os.path.lexists(target):
                canonical = _formal_read(root, plan)
                reused = True
            else:
                _publish_partition(
                    data_root=root,
                    target=target,
                    artifacts=plan.artifacts,
                    custody_payload=_canonical_json_bytes(
                        plan.custody.model_dump(mode="json")
                    ),
                    custody_sha256=plan.custody_sha256,
                    plan_fingerprint=plan.logical_fingerprint,
                )
                canonical = _formal_read(root, plan)
                published = True
    return ResearchUniverseMembershipApplyResult(
        status="applied" if published else "already_present",
        plan_sha256=approved_plan_sha256,
        plan_logical_fingerprint=expected_plan_logical_fingerprint,
        custody_logical_fingerprint=evidence.plan.custody.logical_fingerprint,
        membership_partition_published=published,
        membership_partition_reused=reused,
        published_file_count=evidence.plan.inventory_change_file_count if published else 0,
        published_bytes=evidence.plan.inventory_change_bytes if published else 0,
        formal_reread_record_count=len(canonical.records),
    )


def _read_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    allow_completed_target: bool,
) -> ResearchUniverseMembershipApplyPlanEvidence:
    try:
        return read_research_universe_membership_apply_plan(
            plan_path=plan_path,
            approved_plan_sha256=approved_plan_sha256,
            allow_completed_target=allow_completed_target,
        )
    except ResearchUniverseMembershipApplyPlanError as exc:
        raise ResearchUniverseMembershipApplyError(
            "research Membership Apply plan failed formal reread"
        ) from exc


def _validate_execution_binding(
    *,
    evidence: ResearchUniverseMembershipApplyPlanEvidence,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    data_root: Path,
) -> None:
    plan = evidence.plan
    if (
        evidence.plan_sha256 != approved_plan_sha256
        or plan.logical_fingerprint != expected_plan_logical_fingerprint
        or Path(plan.data_root) != data_root
        or plan.operation != "publish_research_universe_membership"
        or plan.overwritten_partition_count != 0
        or plan.deleted_partition_count != 0
        or plan.performance_authorized is not False
        or plan.production_authorized is not False
    ):
        raise ResearchUniverseMembershipApplyError(
            "research Membership Apply execution binding differs"
        )


def _publish_partition(
    *,
    data_root: Path,
    target: Path,
    artifacts: tuple[ResearchUniverseMembershipPlanArtifactV1, ...],
    custody_payload: bytes,
    custody_sha256: str,
    plan_fingerprint: str,
) -> None:
    _reject_symlink_chain(data_root, target)
    _mkdirs_durable(target.parent, data_root)
    staging = target.parent / f".{target.name}.staging.{plan_fingerprint[:16]}"
    if os.path.lexists(target):
        raise ResearchUniverseMembershipApplyError(
            "research Membership target appeared during Apply"
        )
    if os.path.lexists(staging):
        raise ResearchUniverseMembershipApplyError(
            "research Membership staging residue requires diagnosis"
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
                raise ResearchUniverseMembershipApplyError(
                    "staged research Membership artifact differs"
                )
        marker = staging / CUSTODY_FILE_NAME
        with marker.open("xb") as handle:
            handle.write(custody_payload)
            handle.flush()
            os.fsync(handle.fileno())
        marker.chmod(0o644)
        if _bytes_sha256(marker.read_bytes()) != custody_sha256:
            raise ResearchUniverseMembershipApplyError(
                "staged research Membership custody differs"
            )
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise


def _formal_read(root: Path, plan):
    try:
        canonical = read_canonical_research_universe_membership(
            data_root=root,
            methodology_version=plan.custody.methodology_version,
            session_date=plan.custody.session_date,
            expected_custody_fingerprint=plan.custody.logical_fingerprint,
        )
    except CanonicalResearchUniverseMembershipError as exc:
        raise ResearchUniverseMembershipApplyError(
            "research Membership formal reread failed"
        ) from exc
    if canonical.custody_sha256 != plan.custody_sha256:
        raise ResearchUniverseMembershipApplyError(
            "research Membership custody SHA-256 differs after Apply"
        )
    return canonical


def _verify_source(
    path: Path,
    artifact: ResearchUniverseMembershipPlanArtifactV1,
) -> None:
    if path.is_symlink() or not path.is_file():
        raise ResearchUniverseMembershipApplyError(
            "research Membership source artifact is unavailable"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_size != artifact.size
        or _file_sha256(path) != artifact.sha256
    ):
        raise ResearchUniverseMembershipApplyError(
            "research Membership source artifact differs from plan"
        )


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ResearchUniverseMembershipApplyError(
            "research Membership data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise ResearchUniverseMembershipApplyError(
            "research Membership data root is not approved"
        )
    return resolved


def _mkdirs_durable(path: Path, root: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        if current == root or root not in current.parents:
            raise ResearchUniverseMembershipApplyError(
                "research Membership path escapes data root"
            )
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise ResearchUniverseMembershipApplyError(
            "research Membership parent is unsafe"
        )
    for item in reversed(missing):
        item.mkdir(mode=0o755)
        item.chmod(0o755)
        _fsync_directory(item.parent)
    _reject_symlink_chain(root, path)


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise ResearchUniverseMembershipApplyError(
            "research Membership path escapes data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise ResearchUniverseMembershipApplyError(
                "research Membership path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _validate_fingerprint(value: str, label: str) -> None:
    if len(value) != _SHA256_LENGTH or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ResearchUniverseMembershipApplyError(f"{label} is malformed")


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise ResearchUniverseMembershipApplyError(
            "network is disabled during research Membership Apply"
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
