"""Disconnected exact-plan Apply and recovery for Candidate chain heads."""

from __future__ import annotations

import fcntl
import hashlib
import os
import socket
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Literal, Mapping

from tip_api.services import opportunity_candidate_audit as v1
from tip_api.services import opportunity_candidate_segmented_chain_head as head
from tip_api.services import (
    opportunity_candidate_segmented_chain_head_publication as publication,
)
from tip_api.services import opportunity_candidate_segmented_shadow as shadow


RECOVERY_REVIEW_CONTRACT = (
    "opportunity-candidate-segmented-chain-head-recovery-review/1.0"
)
APPLY_RESULT_CONTRACT = (
    "opportunity-candidate-segmented-chain-head-simulated-apply-result/1.0"
)
RecoveryStatus = Literal[
    "not_started",
    "release_published_pointer_pending",
    "complete",
]


class CandidateSegmentedChainHeadApplyError(RuntimeError):
    """Raised when disconnected Apply or recovery cannot be proven exactly."""


@dataclass(frozen=True, slots=True)
class CandidateSegmentedChainHeadRecoveryReview:
    contract_version: str
    status: RecoveryStatus
    plan_path: Path
    plan_sha256: str
    plan_logical_fingerprint: str
    source_logical_fingerprint: str
    expected_current_family_inventory_fingerprint: str
    expected_current_pointer_state_fingerprint: str
    current_pointer_state_fingerprint: str
    release_present: bool
    pointer_matches_plan: bool
    external_request_count: int = 0
    filesystem_write_count: int = 0
    canonical_write_count: int = 0
    production_write_count: int = 0
    recovery_authorized: bool = False
    production_apply_authorized: bool = False


@dataclass(frozen=True, slots=True)
class CandidateSegmentedChainHeadSimulatedApplyResult:
    contract_version: str
    status: Literal["applied", "verified_then_completed", "already_complete"]
    plan_sha256: str
    plan_logical_fingerprint: str
    expected_current_family_inventory_fingerprint: str
    expected_current_pointer_state_fingerprint: str
    post_family_inventory_fingerprint: str
    post_pointer_state_fingerprint: str
    active_chain_head_logical_fingerprint: str
    release_published: bool
    release_reused: bool
    pointer_published: bool
    pointer_reused: bool
    simulated_write_count: int
    simulated_written_bytes: int
    external_request_count: int = 0
    canonical_write_count: int = 0
    production_write_count: int = 0
    overwritten_immutable_release_count: int = 0
    deleted_release_count: int = 0
    rollback_performed: bool = False
    production_apply_authorized: bool = False


@dataclass(frozen=True, slots=True)
class _ValidatedPlan:
    path: Path
    sha256: str
    plan: Mapping[str, Any]
    canonical_root: Path
    source: head.CandidateSegmentedChainHeadEvidence


def review_candidate_segmented_chain_head_recovery(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_source_logical_fingerprint: str,
    expected_current_family_inventory_fingerprint: str,
    expected_current_pointer_state_fingerprint: str,
    canonical_root: Path,
) -> CandidateSegmentedChainHeadRecoveryReview:
    """Classify exact disconnected state without writing or completing it."""

    validated = _load_static_plan(
        plan_path=plan_path,
        approved_plan_sha256=approved_plan_sha256,
        expected_plan_logical_fingerprint=(
            expected_plan_logical_fingerprint
        ),
        expected_source_logical_fingerprint=(
            expected_source_logical_fingerprint
        ),
        expected_current_family_inventory_fingerprint=(
            expected_current_family_inventory_fingerprint
        ),
        expected_current_pointer_state_fingerprint=(
            expected_current_pointer_state_fingerprint
        ),
        canonical_root=canonical_root,
    )
    plan = validated.plan
    target = _release_target(validated)
    pointer_path = _pointer_path(validated)
    _require_no_staging(validated)
    release_present = os.path.lexists(target)
    if not release_present:
        if os.path.lexists(pointer_path):
            current = _read_current_state(validated.canonical_root)
            if current.pointer == plan["planned_pointer"]:
                raise CandidateSegmentedChainHeadApplyError(
                    "planned pointer exists without its immutable release"
                )
        _read_normal_plan(validated)
        current = _read_current_state(validated.canonical_root)
        return _recovery_review(
            validated=validated,
            status="not_started",
            current_pointer_state_fingerprint=(
                current.current_pointer_state_fingerprint
            ),
            release_present=False,
            pointer_matches_plan=False,
        )

    _verify_release_target(validated)
    try:
        complete = _read_current_state(validated.canonical_root)
    except Exception:
        complete = None
    if complete is not None and complete.pointer == plan["planned_pointer"]:
        return _recovery_review(
            validated=validated,
            status="complete",
            current_pointer_state_fingerprint=(
                complete.current_pointer_state_fingerprint
            ),
            release_present=True,
            pointer_matches_plan=True,
        )

    prestate = publication._read_candidate_segmented_chain_head_current_state(
        canonical_root=validated.canonical_root,
        excluded_release_relative_path=str(
            plan["target"]["release_relative_path"]
        ),
    )
    _require_expected_prestate(validated=validated, actual=prestate)
    return _recovery_review(
        validated=validated,
        status="release_published_pointer_pending",
        current_pointer_state_fingerprint=(
            prestate.current_pointer_state_fingerprint
        ),
        release_present=True,
        pointer_matches_plan=False,
    )


def apply_candidate_segmented_chain_head_plan_disconnected(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_source_logical_fingerprint: str,
    expected_current_family_inventory_fingerprint: str,
    expected_current_pointer_state_fingerprint: str,
    canonical_root: Path,
    verify_then_complete: bool = False,
) -> CandidateSegmentedChainHeadSimulatedApplyResult:
    """Apply one exact plan only beneath an owner-controlled `/tmp` root."""

    review_kwargs = {
        "plan_path": plan_path,
        "approved_plan_sha256": approved_plan_sha256,
        "expected_plan_logical_fingerprint": (
            expected_plan_logical_fingerprint
        ),
        "expected_source_logical_fingerprint": (
            expected_source_logical_fingerprint
        ),
        "expected_current_family_inventory_fingerprint": (
            expected_current_family_inventory_fingerprint
        ),
        "expected_current_pointer_state_fingerprint": (
            expected_current_pointer_state_fingerprint
        ),
        "canonical_root": canonical_root,
    }
    initial = review_candidate_segmented_chain_head_recovery(**review_kwargs)
    lock_path = _lock_path(canonical_root)
    descriptor = _open_lock(lock_path)
    with os.fdopen(descriptor, "r+b") as lock:
        os.fchmod(lock.fileno(), 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        locked = review_candidate_segmented_chain_head_recovery(
            **review_kwargs
        )
        if locked != initial:
            raise CandidateSegmentedChainHeadApplyError(
                "chain-head recovery state changed before locked execution"
            )
        validated = _load_static_plan(**review_kwargs)
        plan = validated.plan
        if locked.status == "complete":
            if not verify_then_complete:
                raise CandidateSegmentedChainHeadApplyError(
                    "chain-head publication is already complete"
                )
            current = _read_current_state(validated.canonical_root)
            return _result(
                validated=validated,
                current=current,
                status="already_complete",
                release_published=False,
                release_reused=True,
                pointer_published=False,
                pointer_reused=True,
                simulated_write_count=0,
                simulated_written_bytes=0,
            )
        if locked.status == "not_started" and verify_then_complete:
            raise CandidateSegmentedChainHeadApplyError(
                "chain-head recovery found no completed immutable release"
            )
        if (
            locked.status == "release_published_pointer_pending"
            and not verify_then_complete
        ):
            raise CandidateSegmentedChainHeadApplyError(
                "chain-head partial publication requires verify-then-complete"
            )

        release_published = False
        release_reused = locked.release_present
        simulated_write_count = 0
        simulated_written_bytes = 0
        with _network_prohibited():
            if locked.status == "not_started":
                _publish_release(validated)
                release_published = True
                release_reused = False
                simulated_write_count += 1
                simulated_written_bytes += int(
                    plan["source"]["manifest_bytes"]
                )
            pending = review_candidate_segmented_chain_head_recovery(
                **review_kwargs
            )
            if pending.status != "release_published_pointer_pending":
                raise CandidateSegmentedChainHeadApplyError(
                    "chain-head release did not reach pointer-pending state"
                )
            _publish_pointer(validated)
            simulated_write_count += 1
            simulated_written_bytes += int(plan["planned_pointer_bytes"])
            completed = review_candidate_segmented_chain_head_recovery(
                **review_kwargs
            )
            if completed.status != "complete":
                raise CandidateSegmentedChainHeadApplyError(
                    "chain-head simulated Apply did not complete formally"
                )
        current = _read_current_state(validated.canonical_root)
        return _result(
            validated=validated,
            current=current,
            status=(
                "verified_then_completed"
                if verify_then_complete
                else "applied"
            ),
            release_published=release_published,
            release_reused=release_reused,
            pointer_published=True,
            pointer_reused=False,
            simulated_write_count=simulated_write_count,
            simulated_written_bytes=simulated_written_bytes,
        )


def _load_static_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_source_logical_fingerprint: str,
    expected_current_family_inventory_fingerprint: str,
    expected_current_pointer_state_fingerprint: str,
    canonical_root: Path,
) -> _ValidatedPlan:
    fingerprints = (
        (approved_plan_sha256, "approved plan SHA-256"),
        (expected_plan_logical_fingerprint, "expected plan logical fingerprint"),
        (expected_source_logical_fingerprint, "expected source fingerprint"),
        (
            expected_current_family_inventory_fingerprint,
            "expected family inventory fingerprint",
        ),
        (
            expected_current_pointer_state_fingerprint,
            "expected pointer state fingerprint",
        ),
    )
    for value, label in fingerprints:
        if not shadow._is_sha256(value):
            raise CandidateSegmentedChainHeadApplyError(f"{label} is malformed")
    if canonical_root == publication.APPROVED_DATA_ROOT:
        raise CandidateSegmentedChainHeadApplyError(
            "disconnected chain-head Apply refuses the production data root"
        )
    root = publication._validated_canonical_root(canonical_root)
    if root == publication.APPROVED_DATA_ROOT:
        raise CandidateSegmentedChainHeadApplyError(
            "disconnected chain-head Apply refuses the production data root"
        )
    try:
        path = publication._validated_plan_file(plan_path)
        plan_sha256 = v1._file_sha256(path)
        if plan_sha256 != approved_plan_sha256:
            raise CandidateSegmentedChainHeadApplyError(
                "approved chain-head plan SHA-256 differs"
            )
        plan = publication._read_canonical_mapping(
            path,
            expected_sha256=plan_sha256,
        )
        logical_fingerprint = plan.pop("logical_content_fingerprint", None)
        if (
            v1._fingerprint(plan) != logical_fingerprint
            or logical_fingerprint != expected_plan_logical_fingerprint
        ):
            raise CandidateSegmentedChainHeadApplyError(
                "approved chain-head plan logical identity differs"
            )
        plan["logical_content_fingerprint"] = logical_fingerprint
        publication._validate_plan_shape(plan)
        if Path(str(plan["canonical_root"])) != root:
            raise CandidateSegmentedChainHeadApplyError(
                "chain-head plan root differs from disconnected Apply root"
            )
        source_section = plan["source"]
        source = publication._read_source(
            base_shadow=Path(str(source_section["base_shadow_path"])),
            source_chain_head=Path(str(source_section["package_path"])),
            expected_source_logical_fingerprint=(
                expected_source_logical_fingerprint
            ),
        )
        if (
            source_section != publication._source_descriptor(source)
            or plan["target"]
            != publication._target_descriptor_for_source(source, root)
        ):
            raise CandidateSegmentedChainHeadApplyError(
                "chain-head source or target changed after planning"
            )
    except CandidateSegmentedChainHeadApplyError:
        raise
    except Exception as exc:
        raise CandidateSegmentedChainHeadApplyError(
            f"chain-head plan static reread failed: {type(exc).__name__}"
        ) from exc
    expected_state = plan["expected_current_state"]
    if (
        expected_state["family_inventory_fingerprint"]
        != expected_current_family_inventory_fingerprint
        or expected_state["current_pointer_state_fingerprint"]
        != expected_current_pointer_state_fingerprint
        or plan["planned_pointer"]["prior_pointer_state_fingerprint"]
        != expected_current_pointer_state_fingerprint
        or plan["apply_authorized"] is not False
        or plan["rollback_authorized"] is not False
        or plan["production_consumer_authorized"] is not False
    ):
        raise CandidateSegmentedChainHeadApplyError(
            "chain-head disconnected execution binding differs"
        )
    pointer_bytes = v1._canonical_bytes(plan["planned_pointer"])
    if (
        len(pointer_bytes) != plan["planned_pointer_bytes"]
        or hashlib.sha256(pointer_bytes).hexdigest()
        != plan["planned_pointer_sha256"]
    ):
        raise CandidateSegmentedChainHeadApplyError(
            "planned chain-head pointer bytes differ"
        )
    return _ValidatedPlan(
        path=path,
        sha256=plan_sha256,
        plan=plan,
        canonical_root=root,
        source=source,
    )


def _read_normal_plan(validated: _ValidatedPlan) -> None:
    try:
        publication.read_candidate_segmented_chain_head_publication_plan(
            plan_path=validated.path,
            expected_plan_sha256=validated.sha256,
            expected_plan_logical_fingerprint=str(
                validated.plan["logical_content_fingerprint"]
            ),
            expected_source_logical_fingerprint=str(
                validated.plan["source"]["logical_content_fingerprint"]
            ),
        )
    except Exception as exc:
        raise CandidateSegmentedChainHeadApplyError(
            f"chain-head plan prestate reread failed: {type(exc).__name__}"
        ) from exc


def _require_expected_prestate(
    *,
    validated: _ValidatedPlan,
    actual: publication.CandidateSegmentedChainHeadCurrentState,
) -> None:
    expected = validated.plan["expected_current_state"]
    actual_descriptor = publication._state_descriptor(actual)
    if actual_descriptor == expected:
        return
    empty_inventory = v1._fingerprint(
        {
            "contract_version": publication.FAMILY_INVENTORY_CONTRACT,
            "entries": [],
        }
    )
    created_parent_inventory = v1._fingerprint(
        {
            "contract_version": publication.FAMILY_INVENTORY_CONTRACT,
            "entries": [
                {
                    "relative_path": publication.RELEASES_DIRECTORY,
                    "type": "directory",
                    "mode": "0700",
                }
            ],
        }
    )
    actual_without_inventory = dict(actual_descriptor)
    expected_without_inventory = dict(expected)
    actual_inventory = actual_without_inventory.pop(
        "family_inventory_fingerprint"
    )
    expected_inventory = expected_without_inventory.pop(
        "family_inventory_fingerprint"
    )
    if not (
        expected["active"] is None
        and expected_inventory == empty_inventory
        and actual_inventory == created_parent_inventory
        and actual_without_inventory == expected_without_inventory
    ):
        raise CandidateSegmentedChainHeadApplyError(
            "chain-head pre-Apply state changed during recovery"
        )


def _publish_release(validated: _ValidatedPlan) -> None:
    target = _release_target(validated)
    publication._reject_symlink_chain(validated.canonical_root, target)
    _mkdirs_durable(target.parent, validated.canonical_root)
    staging = _release_staging(validated)
    if os.path.lexists(target) or os.path.lexists(staging):
        raise CandidateSegmentedChainHeadApplyError(
            "chain-head release target or staging already exists"
        )
    staging.mkdir(mode=0o700)
    staging.chmod(0o700)
    source = validated.source.path / head.CHAIN_HEAD_MANIFEST
    destination = staging / head.CHAIN_HEAD_MANIFEST
    _copy_new(source=source, destination=destination)
    _fsync_directory(staging)
    _verify_release_directory(validated=validated, directory=staging)
    os.rename(staging, target)
    _fsync_directory(target.parent)
    _verify_release_target(validated)


def _publish_pointer(validated: _ValidatedPlan) -> None:
    path = _pointer_path(validated)
    publication._reject_symlink_chain(validated.canonical_root, path)
    _mkdirs_durable(path.parent, validated.canonical_root)
    staging = _pointer_staging(validated)
    if os.path.lexists(staging):
        raise CandidateSegmentedChainHeadApplyError(
            "chain-head pointer staging already exists"
        )
    payload = v1._canonical_bytes(validated.plan["planned_pointer"])
    v1._write_canonical_new(staging, validated.plan["planned_pointer"])
    if (
        staging.stat().st_size != len(payload)
        or v1._file_sha256(staging)
        != validated.plan["planned_pointer_sha256"]
        or staging.read_bytes() != payload
    ):
        raise CandidateSegmentedChainHeadApplyError(
            "staged chain-head pointer differs from plan"
        )
    _fsync_directory(staging.parent)
    os.replace(staging, path)
    _fsync_directory(path.parent)


def _verify_release_target(validated: _ValidatedPlan) -> None:
    _verify_release_directory(
        validated=validated,
        directory=_release_target(validated),
    )


def _verify_release_directory(
    *,
    validated: _ValidatedPlan,
    directory: Path,
) -> None:
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or directory.stat().st_uid != os.geteuid()
        or stat.S_IMODE(directory.stat().st_mode) != 0o700
        or {item.name for item in directory.iterdir()}
        != {head.CHAIN_HEAD_MANIFEST}
    ):
        raise CandidateSegmentedChainHeadApplyError(
            "completed chain-head release custody differs"
        )
    path = directory / head.CHAIN_HEAD_MANIFEST
    if path.is_symlink() or not path.is_file():
        raise CandidateSegmentedChainHeadApplyError(
            "completed chain-head release manifest is unsafe"
        )
    metadata = path.stat()
    source = validated.plan["source"]
    if (
        metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or metadata.st_size != source["manifest_bytes"]
        or v1._file_sha256(path) != source["manifest_sha256"]
        or path.read_bytes()
        != validated.source.path.joinpath(head.CHAIN_HEAD_MANIFEST).read_bytes()
    ):
        raise CandidateSegmentedChainHeadApplyError(
            "completed chain-head release manifest differs"
        )


def _copy_new(*, source: Path, destination: Path) -> None:
    shadow._validate_file_custody(source)
    source_sha256 = v1._file_sha256(source)
    source_size = source.stat().st_size
    descriptor = os.open(
        destination,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o400,
    )
    digest = hashlib.sha256()
    copied = 0
    try:
        with source.open("rb") as source_handle:
            while True:
                chunk = source_handle.read(1024 * 1024)
                if not chunk:
                    break
                view = memoryview(chunk)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise CandidateSegmentedChainHeadApplyError(
                            "chain-head release copy did not progress"
                        )
                    digest.update(view[:written])
                    copied += written
                    view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if copied != source_size or digest.hexdigest() != source_sha256:
        raise CandidateSegmentedChainHeadApplyError(
            "chain-head release copy differs from source"
        )


def _require_no_staging(validated: _ValidatedPlan) -> None:
    for path in (
        _release_staging(validated),
        _pointer_staging(validated),
    ):
        publication._reject_symlink_chain(validated.canonical_root, path)
        if os.path.lexists(path):
            raise CandidateSegmentedChainHeadApplyError(
                "chain-head staging residue requires diagnosis"
            )


def _release_target(validated: _ValidatedPlan) -> Path:
    return publication._resolve_relative(
        validated.canonical_root,
        str(validated.plan["target"]["release_relative_path"]),
    )


def _release_staging(validated: _ValidatedPlan) -> Path:
    target = _release_target(validated)
    return target.with_name(f".{target.name}.staging")


def _pointer_path(validated: _ValidatedPlan) -> Path:
    return (
        validated.canonical_root
        / publication.FAMILY_RELATIVE_PATH
        / publication.CURRENT_POINTER_FILE
    )


def _pointer_staging(validated: _ValidatedPlan) -> Path:
    pointer = _pointer_path(validated)
    return pointer.with_name(
        f".{pointer.name}.staging."
        f"{validated.plan['logical_content_fingerprint'][:16]}"
    )


def _read_current_state(
    root: Path,
) -> publication.CandidateSegmentedChainHeadCurrentState:
    try:
        return publication.read_candidate_segmented_chain_head_current_state(
            canonical_root=root,
        )
    except Exception as exc:
        raise CandidateSegmentedChainHeadApplyError(
            f"chain-head current state is invalid: {type(exc).__name__}"
        ) from exc


def _mkdirs_durable(path: Path, root: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        if current == root or root not in current.parents:
            raise CandidateSegmentedChainHeadApplyError(
                "chain-head publication path escapes simulated root"
            )
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise CandidateSegmentedChainHeadApplyError(
            "chain-head publication parent is unsafe"
        )
    for item in reversed(missing):
        item.mkdir(mode=0o700)
        item.chmod(0o700)
        _fsync_directory(item.parent)
    publication._reject_symlink_chain(root, path)


def _lock_path(root: Path) -> Path:
    resolved = publication._validated_canonical_root(root)
    return Path("/tmp") / (
        "tip-candidate-chain-head-simulation-"
        + hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:16]
        + ".lock"
    )


def _open_lock(path: Path) -> int:
    try:
        descriptor = os.open(
            path,
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
        )
    except OSError as exc:
        raise CandidateSegmentedChainHeadApplyError(
            "chain-head simulation lock is unavailable"
        ) from exc
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
    ):
        os.close(descriptor)
        raise CandidateSegmentedChainHeadApplyError(
            "chain-head simulation lock custody differs"
        )
    return descriptor


def _recovery_review(
    *,
    validated: _ValidatedPlan,
    status: RecoveryStatus,
    current_pointer_state_fingerprint: str,
    release_present: bool,
    pointer_matches_plan: bool,
) -> CandidateSegmentedChainHeadRecoveryReview:
    return CandidateSegmentedChainHeadRecoveryReview(
        contract_version=RECOVERY_REVIEW_CONTRACT,
        status=status,
        plan_path=validated.path,
        plan_sha256=validated.sha256,
        plan_logical_fingerprint=str(
            validated.plan["logical_content_fingerprint"]
        ),
        source_logical_fingerprint=str(
            validated.plan["source"]["logical_content_fingerprint"]
        ),
        expected_current_family_inventory_fingerprint=str(
            validated.plan["expected_current_state"][
                "family_inventory_fingerprint"
            ]
        ),
        expected_current_pointer_state_fingerprint=str(
            validated.plan["expected_current_state"][
                "current_pointer_state_fingerprint"
            ]
        ),
        current_pointer_state_fingerprint=(
            current_pointer_state_fingerprint
        ),
        release_present=release_present,
        pointer_matches_plan=pointer_matches_plan,
    )


def _result(
    *,
    validated: _ValidatedPlan,
    current: publication.CandidateSegmentedChainHeadCurrentState,
    status: Literal["applied", "verified_then_completed", "already_complete"],
    release_published: bool,
    release_reused: bool,
    pointer_published: bool,
    pointer_reused: bool,
    simulated_write_count: int,
    simulated_written_bytes: int,
) -> CandidateSegmentedChainHeadSimulatedApplyResult:
    if current.pointer != validated.plan["planned_pointer"]:
        raise CandidateSegmentedChainHeadApplyError(
            "completed chain-head pointer differs from plan"
        )
    return CandidateSegmentedChainHeadSimulatedApplyResult(
        contract_version=APPLY_RESULT_CONTRACT,
        status=status,
        plan_sha256=validated.sha256,
        plan_logical_fingerprint=str(
            validated.plan["logical_content_fingerprint"]
        ),
        expected_current_family_inventory_fingerprint=str(
            validated.plan["expected_current_state"][
                "family_inventory_fingerprint"
            ]
        ),
        expected_current_pointer_state_fingerprint=str(
            validated.plan["expected_current_state"][
                "current_pointer_state_fingerprint"
            ]
        ),
        post_family_inventory_fingerprint=(
            current.family_inventory_fingerprint
        ),
        post_pointer_state_fingerprint=(
            current.current_pointer_state_fingerprint
        ),
        active_chain_head_logical_fingerprint=str(
            current.pointer["active"][
                "chain_head_logical_content_fingerprint"
            ]
        ),
        release_published=release_published,
        release_reused=release_reused,
        pointer_published=pointer_published,
        pointer_reused=pointer_reused,
        simulated_write_count=simulated_write_count,
        simulated_written_bytes=simulated_written_bytes,
    )


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise CandidateSegmentedChainHeadApplyError(
            "network access is disabled during disconnected chain-head Apply"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
