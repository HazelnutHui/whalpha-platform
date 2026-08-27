"""Durable immutable Dashboard Snapshot V2 publication boundary."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4

from tip_api.contracts.market_data.v2.dashboard_snapshot import (
    DashboardSnapshotActivePointerV2, DashboardSnapshotApprovalPlanV2,
    DashboardSnapshotApprovalPlanV2_1,
    DashboardSnapshotApprovalPlanV2_2,
    DashboardSnapshotApprovalPlanV2_3,
    DashboardSnapshotFileReferenceV2, DashboardSnapshotTargetReferenceV2,
)
from tip_api.contracts.analytics.v1.review_deployment import (
    REVIEW_ACKNOWLEDGEMENT,
    ReviewDeploymentAuthorizationV1,
)
from tip_api.persistence.parquet.dashboard_universe_activation_active import (
    _fsync_directory, _mkdir_parents_durable, _reject_symlink_chain, _validated_root,
    read_dashboard_universe_activation_pointer,
)
from tip_api.services.private_dashboard_snapshot import (
    DashboardSnapshotError, DashboardSnapshotManifest, deterministic_json_bytes,
    sha256_file, validate_snapshot_release,
)

SNAPSHOT_V2_BASE = "market-data/snapshots/private-dashboard-v2"
SNAPSHOT_POINTER = "market-data/snapshots/private-dashboard-active/active.json"
REVISION_ID = "universe-funnel-v2"
LEGACY_RELEASE_ID = "2026-08-19T083341Z-7ed7fdc21686"
ABSENT_POINTER = "absent"


class DashboardSnapshotPublicationError(DashboardSnapshotError):
    pass


class DashboardSnapshotPublicationConflict(DashboardSnapshotPublicationError):
    pass


@dataclass(frozen=True, slots=True)
class ActiveDashboardSnapshot:
    reference: DashboardSnapshotTargetReferenceV2
    release_path: Path
    manifest: DashboardSnapshotManifest
    pointer: DashboardSnapshotActivePointerV2 | None


def target_path(root: Path, release_id: str) -> Path:
    return root / SNAPSHOT_V2_BASE / f"revision={REVISION_ID}" / f"release_id={release_id}"


def pointer_path(root: Path) -> Path:
    return root / SNAPSHOT_POINTER


def canonical_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def file_references(release: Path) -> tuple[DashboardSnapshotFileReferenceV2, ...]:
    if release.is_symlink() or not release.is_dir():
        raise DashboardSnapshotPublicationError("snapshot release is unavailable")
    output=[]
    for path in sorted(release.rglob("*")):
        if path.is_symlink():
            raise DashboardSnapshotPublicationError("snapshot release contains a symlink")
        if path.is_file():
            output.append(DashboardSnapshotFileReferenceV2(
                relative_path=path.relative_to(release).as_posix(), size=path.stat().st_size,
                sha256=sha256_file(path),
            ))
    return tuple(output)


def aggregate_sha(files: tuple[DashboardSnapshotFileReferenceV2, ...]) -> str:
    return canonical_sha([item.model_dump(mode="json") for item in files])


def _reference(release: Path, *, storage_kind: str, logical_path: str) -> DashboardSnapshotTargetReferenceV2:
    manifest=validate_snapshot_release(release); files=file_references(release)
    return DashboardSnapshotTargetReferenceV2(
        storage_kind=storage_kind, release_id=manifest.release_id, logical_path=logical_path,
        snapshot_contract_version=manifest.snapshot_contract_version,
        dashboard_contract_version=manifest.dashboard_contract_version,
        aggregate_sha256=aggregate_sha(files), manifest_sha256=sha256_file(release/"private-data/v1/manifest.json"),
    )


def _read_pointer(root: Path) -> DashboardSnapshotActivePointerV2 | None:
    root=_validated_root(root); path=pointer_path(root); _reject_symlink_chain(root,path)
    if not path.exists(): return None
    if path.is_symlink() or not path.is_file(): raise DashboardSnapshotPublicationError("snapshot pointer is unsafe")
    try: pointer=DashboardSnapshotActivePointerV2.model_validate_json(path.read_text())
    except Exception as exc: raise DashboardSnapshotPublicationError("snapshot pointer is malformed") from exc
    payload=pointer.model_dump(mode="json",exclude={"pointer_content_fingerprint"})
    if canonical_sha(payload)!=pointer.pointer_content_fingerprint:
        raise DashboardSnapshotPublicationError("snapshot pointer fingerprint mismatch")
    return pointer


def read_dashboard_snapshot_pointer(root: Path) -> DashboardSnapshotActivePointerV2 | None:
    """Read and fully validate the active snapshot pointer without changing state."""
    return _read_pointer(root)


def _resolve_reference(root: Path, legacy_root: Path, reference: DashboardSnapshotTargetReferenceV2) -> ActiveDashboardSnapshot:
    if reference.storage_kind=="data_root":
        expected_prefix = Path(SNAPSHOT_V2_BASE) / f"revision={REVISION_ID}"
        if not Path(reference.logical_path).is_relative_to(expected_prefix):
            raise DashboardSnapshotPublicationError("snapshot target reference is outside the approved namespace")
        release=root/reference.logical_path; _reject_symlink_chain(root,release)
    else:
        if reference.logical_path != LEGACY_RELEASE_ID:
            raise DashboardSnapshotPublicationError("legacy snapshot reference is not the approved fallback")
        if legacy_root.is_symlink():
            raise DashboardSnapshotPublicationError("legacy snapshot root is unsafe")
        safe_legacy=legacy_root.resolve(strict=True)
        if safe_legacy.is_symlink() or not safe_legacy.is_dir(): raise DashboardSnapshotPublicationError("legacy snapshot root is unsafe")
        release=safe_legacy/reference.logical_path
        if not release.resolve(strict=True).is_relative_to(safe_legacy): raise DashboardSnapshotPublicationError("legacy snapshot path escapes root")
    manifest=validate_snapshot_release(release); actual=_reference(release,storage_kind=reference.storage_kind,logical_path=reference.logical_path)
    if actual!=reference: raise DashboardSnapshotPublicationError("snapshot target reference mismatch")
    return ActiveDashboardSnapshot(reference,release,manifest,None)


def read_active_dashboard_snapshot(root: Path, legacy_root: Path) -> ActiveDashboardSnapshot:
    root=_validated_root(root); pointer=_read_pointer(root)
    if pointer is None:
        release=legacy_root/LEGACY_RELEASE_ID
        reference=_reference(release,storage_kind="legacy_repo_build",logical_path=LEGACY_RELEASE_ID)
        return ActiveDashboardSnapshot(reference,release,validate_snapshot_release(release),None)
    active=_resolve_reference(root,legacy_root,pointer.active)
    return ActiveDashboardSnapshot(active.reference,active.release_path,active.manifest,pointer)


def current_state_fingerprint(root: Path, legacy_root: Path) -> str:
    active=read_active_dashboard_snapshot(root,legacy_root)
    if active.pointer is not None: return active.pointer.pointer_content_fingerprint
    return canonical_sha({"mode":"legacy_fallback","reference":active.reference.model_dump(mode="json")})


def build_approval_plan(*, root: Path, legacy_root: Path, candidate: Path,
                        activation_logical_fingerprint: str, generated_at: datetime) -> DashboardSnapshotApprovalPlanV2 | DashboardSnapshotApprovalPlanV2_1 | DashboardSnapshotApprovalPlanV2_2 | DashboardSnapshotApprovalPlanV2_3:
    root=_validated_root(root); manifest=validate_snapshot_release(candidate)
    if (manifest.snapshot_contract_version, manifest.dashboard_contract_version) not in {
        ("1.4", "2.1"), ("1.5", "2.2"), ("1.6", "2.3"), ("1.7", "2.4"), ("1.8", "2.5")
    }:
        raise DashboardSnapshotPublicationError("candidate snapshot contract is not V2")
    normal_freshness = (
        manifest.freshness_status == "fresh"
        and manifest.session_lag == 0
        and manifest.expected_latest_completed_session
        == manifest.actual_latest_completed_session
    )
    review = None
    if manifest.review_mode:
        review = ReviewDeploymentAuthorizationV1(
            approved_as_of_session=manifest.review_approved_as_of_session,
            expected_latest_session=manifest.review_expected_latest_session,
            expected_lag_sessions=manifest.review_expected_lag_sessions,
            explicit_user_acknowledgement=REVIEW_ACKNOWLEDGEMENT,
        )
    review_allowed = review is not None and (
        manifest.current_session_date == review.approved_as_of_session.isoformat()
        and manifest.actual_latest_completed_session == review.approved_as_of_session.isoformat()
        and manifest.expected_latest_completed_session == review.expected_latest_session.isoformat()
        and manifest.session_lag == review.expected_lag_sessions
        and manifest.freshness_status == "stale"
    )
    if not (normal_freshness or review_allowed):
        raise DashboardSnapshotPublicationError(
            f"stale snapshot cannot produce an approval plan: expected={manifest.expected_latest_completed_session} actual={manifest.actual_latest_completed_session} lag={manifest.session_lag}"
        )
    activation_pointer=read_dashboard_universe_activation_pointer(root)
    if activation_pointer is None:
        raise DashboardSnapshotPublicationError("Activation V2 pointer is required")
    if activation_logical_fingerprint != manifest.activation_fingerprint:
        raise DashboardSnapshotPublicationError("candidate Activation fingerprint mismatch")
    files=file_references(candidate); aggregate=aggregate_sha(files)
    target=target_path(root,manifest.release_id); pointer=pointer_path(root)
    _reject_symlink_chain(root,target); _reject_symlink_chain(root,pointer)
    if target.exists() or target.is_symlink(): raise DashboardSnapshotPublicationConflict("snapshot target already exists")
    if target.parent.exists() and tuple(target.parent.glob(f".{target.name}.staging-*")):
        raise DashboardSnapshotPublicationConflict("snapshot staging residue exists")
    current=read_active_dashboard_snapshot(root,legacy_root)
    rollback=current.reference
    active_ref=DashboardSnapshotTargetReferenceV2(
        storage_kind="data_root",release_id=manifest.release_id,
        logical_path=target.relative_to(root).as_posix(),snapshot_contract_version=manifest.snapshot_contract_version,
        dashboard_contract_version=manifest.dashboard_contract_version,aggregate_sha256=aggregate,
        manifest_sha256=sha256_file(candidate/"private-data/v1/manifest.json"),
    )
    pointer_payload={
        "pointer_version":"2.0","status":"active","active":active_ref.model_dump(mode="json"),
        "rollback":rollback.model_dump(mode="json"),"switched_at":generated_at.astimezone(UTC).isoformat().replace("+00:00","Z"),
        "activation_pointer_fingerprint":activation_pointer.pointer_content_fingerprint,
    }
    pointer_fp=canonical_sha(pointer_payload); pointer_payload["pointer_content_fingerprint"]=pointer_fp
    pointer_bytes=deterministic_json_bytes(pointer_payload)
    payload={
        "plan_version":(
            "2.3" if manifest.snapshot_contract_version == "1.8"
            else "2.2" if manifest.snapshot_contract_version == "1.7"
            else "2.1" if manifest.snapshot_contract_version == "1.6"
            else "2.0"
        ),
        "revision_id":REVISION_ID,"release_id":manifest.release_id,
        "snapshot_contract_version":manifest.snapshot_contract_version,
        "dashboard_contract_version":manifest.dashboard_contract_version,
        "generated_at":generated_at.astimezone(UTC).isoformat().replace("+00:00","Z"),
        "analysis_session":manifest.current_session_date,"expected_latest_completed_session":manifest.expected_latest_completed_session,
        "actual_latest_completed_session":manifest.actual_latest_completed_session,
        "freshness_status":manifest.freshness_status,"session_lag":manifest.session_lag,
        "review_mode":review is not None,
        "normal_freshness":normal_freshness,
        "activation_allowed_by_review_authorization":review_allowed,
        "review_deployment":review.model_dump(mode="json") if review is not None else None,
        "activation_pointer_fingerprint":activation_pointer.pointer_content_fingerprint,
        "activation_logical_fingerprint":activation_logical_fingerprint,
        "expected_current_state_fingerprint":current_state_fingerprint(root,legacy_root),
        "target_path":str(target),"target_logical_path":target.relative_to(root).as_posix(),
        "pointer_path":str(pointer),
        "candidate_path":str(candidate),"files":[item.model_dump(mode="json") for item in files],
        "aggregate_sha256":aggregate,"manifest_sha256":active_ref.manifest_sha256,
        "planned_pointer_sha256":hashlib.sha256(pointer_bytes).hexdigest(),"planned_pointer_fingerprint":pointer_fp,
        "rollback":rollback.model_dump(mode="json"),
        "market_intelligence_publication_id":manifest.market_intelligence_publication_id,
        "market_intelligence_payload_sha256":manifest.market_intelligence_payload_sha256,
        "market_intelligence_logical_fingerprint":manifest.market_intelligence_logical_fingerprint,
    }
    if manifest.snapshot_contract_version in {"1.6", "1.7", "1.8"}:
        payload.update(
            candidate_contract_version=manifest.candidate_contract_version,
            candidate_analytics_logical_fingerprint=manifest.candidate_analytics_logical_fingerprint,
            candidate_audit_logical_fingerprint=manifest.candidate_audit_logical_fingerprint,
            candidate_parameter_fingerprint=manifest.candidate_parameter_fingerprint,
            candidate_state_parameter_fingerprint=manifest.candidate_state_parameter_fingerprint,
        )
    if manifest.snapshot_contract_version in {"1.7", "1.8"}:
        payload.update(
            candidate_publication_contract_version=manifest.candidate_publication_contract_version,
            entry_geometry_contract_version=manifest.entry_geometry_contract_version,
            entry_geometry_audit_logical_fingerprint=manifest.entry_geometry_audit_logical_fingerprint,
            entry_geometry_parameter_fingerprint=manifest.entry_geometry_parameter_fingerprint,
            entry_lane_consumer_parameter_fingerprint=manifest.entry_lane_consumer_parameter_fingerprint,
        )
    if manifest.snapshot_contract_version == "1.8":
        payload.update(
            candidate_summary_contract_version=manifest.candidate_summary_contract_version,
            candidate_summary_logical_fingerprint=manifest.candidate_summary_logical_fingerprint,
            candidate_detail_contract_version=manifest.candidate_detail_contract_version,
            candidate_detail_files=manifest.candidate_detail_files,
        )
    plan_type = (
        DashboardSnapshotApprovalPlanV2_3
        if manifest.snapshot_contract_version == "1.8"
        else DashboardSnapshotApprovalPlanV2_2
        if manifest.snapshot_contract_version == "1.7"
        else DashboardSnapshotApprovalPlanV2_1
        if manifest.snapshot_contract_version == "1.6"
        else DashboardSnapshotApprovalPlanV2
    )
    return plan_type(**payload,plan_content_fingerprint=canonical_sha(payload))


def validate_plan(plan: DashboardSnapshotApprovalPlanV2 | DashboardSnapshotApprovalPlanV2_1 | DashboardSnapshotApprovalPlanV2_2 | DashboardSnapshotApprovalPlanV2_3) -> None:
    payload=plan.model_dump(mode="json",exclude={"plan_content_fingerprint"})
    if canonical_sha(payload)!=plan.plan_content_fingerprint: raise DashboardSnapshotPublicationError("snapshot approval plan fingerprint mismatch")
    candidate=Path(plan.candidate_path); manifest=validate_snapshot_release(candidate); files=file_references(candidate)
    if files!=plan.files or aggregate_sha(files)!=plan.aggregate_sha256 or sha256_file(candidate/"private-data/v1/manifest.json")!=plan.manifest_sha256:
        raise DashboardSnapshotPublicationError("snapshot approval candidate changed")
    if manifest.generated_at!=plan.generated_at.astimezone(UTC).isoformat().replace("+00:00","Z"):
        raise DashboardSnapshotPublicationError("snapshot approval timestamp mismatch")
    if (
        manifest.snapshot_contract_version != plan.snapshot_contract_version
        or manifest.dashboard_contract_version != plan.dashboard_contract_version
        or manifest.market_intelligence_publication_id != plan.market_intelligence_publication_id
        or manifest.market_intelligence_payload_sha256 != plan.market_intelligence_payload_sha256
        or manifest.market_intelligence_logical_fingerprint
        != plan.market_intelligence_logical_fingerprint
    ):
        raise DashboardSnapshotPublicationError("snapshot approval consumer binding changed")
    if isinstance(plan, DashboardSnapshotApprovalPlanV2_1) and (
        manifest.candidate_contract_version != plan.candidate_contract_version
        or manifest.candidate_analytics_logical_fingerprint
        != plan.candidate_analytics_logical_fingerprint
        or manifest.candidate_audit_logical_fingerprint
        != plan.candidate_audit_logical_fingerprint
        or manifest.candidate_parameter_fingerprint != plan.candidate_parameter_fingerprint
        or manifest.candidate_state_parameter_fingerprint
        != plan.candidate_state_parameter_fingerprint
    ):
        raise DashboardSnapshotPublicationError("snapshot approval Candidate binding changed")
    if isinstance(plan, DashboardSnapshotApprovalPlanV2_2) and (
        manifest.candidate_publication_contract_version
        != plan.candidate_publication_contract_version
        or manifest.entry_geometry_contract_version != plan.entry_geometry_contract_version
        or manifest.entry_geometry_audit_logical_fingerprint
        != plan.entry_geometry_audit_logical_fingerprint
        or manifest.entry_geometry_parameter_fingerprint
        != plan.entry_geometry_parameter_fingerprint
        or manifest.entry_lane_consumer_parameter_fingerprint
        != plan.entry_lane_consumer_parameter_fingerprint
    ):
        raise DashboardSnapshotPublicationError(
            "snapshot approval entry-geometry binding changed"
        )
    if isinstance(plan, DashboardSnapshotApprovalPlanV2_3) and (
        manifest.candidate_summary_contract_version
        != plan.candidate_summary_contract_version
        or manifest.candidate_summary_logical_fingerprint
        != plan.candidate_summary_logical_fingerprint
        or manifest.candidate_detail_contract_version
        != plan.candidate_detail_contract_version
        or manifest.candidate_detail_files != plan.candidate_detail_files
    ):
        raise DashboardSnapshotPublicationError(
            "snapshot approval split Candidate binding changed"
        )
    review = plan.review_deployment
    if manifest.review_mode != (review is not None):
        raise DashboardSnapshotPublicationError("snapshot approval review mode changed")
    if review is not None and (
        manifest.review_contract_version != review.contract_version
        or manifest.review_approved_as_of_session != review.approved_as_of_session.isoformat()
        or manifest.review_expected_latest_session != review.expected_latest_session.isoformat()
        or manifest.review_expected_lag_sessions != review.expected_lag_sessions
    ):
        raise DashboardSnapshotPublicationError("snapshot approval review binding changed")


def _planned_pointer(plan: DashboardSnapshotApprovalPlanV2) -> DashboardSnapshotActivePointerV2:
    active=DashboardSnapshotTargetReferenceV2(
        storage_kind="data_root",release_id=plan.release_id,logical_path=plan.target_logical_path,
        snapshot_contract_version=plan.snapshot_contract_version,
        dashboard_contract_version=plan.dashboard_contract_version,
        aggregate_sha256=plan.aggregate_sha256,manifest_sha256=plan.manifest_sha256,
    )
    payload={"pointer_version":"2.0","status":"active","active":active.model_dump(mode="json"),
             "rollback":plan.rollback.model_dump(mode="json"),
             "switched_at":plan.generated_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
             "activation_pointer_fingerprint":plan.activation_pointer_fingerprint}
    return DashboardSnapshotActivePointerV2(**payload,pointer_content_fingerprint=canonical_sha(payload))


def _write_pointer(root: Path, pointer: DashboardSnapshotActivePointerV2) -> None:
    path=pointer_path(root); _mkdir_parents_durable(root,path.parent); _reject_symlink_chain(root,path)
    staging=path.parent/f".{path.name}.staging-{uuid4().hex}"
    try:
        data=deterministic_json_bytes(pointer.model_dump(mode="json"))
        with staging.open("xb") as handle: handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(staging,path); _fsync_directory(path.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink(): staging.unlink()
        raise


@contextmanager
def _lock(root: Path):
    fd=os.open(root,os.O_RDONLY)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc: raise DashboardSnapshotPublicationConflict("snapshot publication is locked") from exc
        yield
    finally: fcntl.flock(fd,fcntl.LOCK_UN); os.close(fd)


def publish_and_activate(*, root: Path, legacy_root: Path, plan: DashboardSnapshotApprovalPlanV2,
                         expected_current_state_fingerprint: str, failpoint: str|None=None,
                         freshness_validator: Callable[[], None] | None = None) -> ActiveDashboardSnapshot:
    root=_validated_root(root); validate_plan(plan)
    if not (plan.normal_freshness or plan.activation_allowed_by_review_authorization):
        raise DashboardSnapshotPublicationConflict("snapshot plan is not freshness-authorized")
    if expected_current_state_fingerprint!=plan.expected_current_state_fingerprint:
        raise DashboardSnapshotPublicationConflict("approved current snapshot state mismatch")
    with _lock(root):
        if freshness_validator is not None:
            freshness_validator()
        if current_state_fingerprint(root,legacy_root)!=expected_current_state_fingerprint:
            raise DashboardSnapshotPublicationConflict("snapshot state changed after approval")
        activation=read_dashboard_universe_activation_pointer(root)
        if activation is None or activation.pointer_content_fingerprint!=plan.activation_pointer_fingerprint:
            raise DashboardSnapshotPublicationConflict("Activation pointer changed after approval")
        validate_plan(plan)
        target=Path(plan.target_path)
        if target != target_path(root, plan.release_id) or Path(plan.pointer_path) != pointer_path(root):
            raise DashboardSnapshotPublicationError("approved publication path mismatch")
        _reject_symlink_chain(root,target)
        if target.exists() or target.is_symlink(): raise DashboardSnapshotPublicationConflict("snapshot target exists")
        if target.parent.exists() and tuple(target.parent.glob(f".{target.name}.staging-*")):
            raise DashboardSnapshotPublicationConflict("snapshot staging residue exists")
        _mkdir_parents_durable(root,target.parent)
        staging=target.parent/f".{target.name}.staging-{uuid4().hex}"; staging.mkdir(); _fsync_directory(staging); _fsync_directory(staging.parent)
        renamed=False
        try:
            for item in plan.files:
                source=Path(plan.candidate_path)/item.relative_path; destination=staging/item.relative_path
                _mkdir_parents_durable(staging,destination.parent)
                with source.open("rb") as src,destination.open("xb") as dst:
                    shutil.copyfileobj(src,dst); dst.flush(); os.fsync(dst.fileno())
            _fsync_directory(staging)
            validate_snapshot_release(staging)
            copied_files = file_references(staging)
            if copied_files != plan.files or aggregate_sha(copied_files) != plan.aggregate_sha256:
                raise DashboardSnapshotPublicationError("staged snapshot artifacts do not match approval")
            if failpoint=="before_target_rename": raise DashboardSnapshotPublicationError("injected failure before target rename")
            os.replace(staging,target);renamed=True;_fsync_directory(target.parent)
            completed = _reference(
                target, storage_kind="data_root", logical_path=plan.target_logical_path
            )
            if completed.aggregate_sha256 != plan.aggregate_sha256 or completed.manifest_sha256 != plan.manifest_sha256:
                raise DashboardSnapshotPublicationError("completed snapshot target does not match approval")
            if failpoint=="after_target_rename": raise DashboardSnapshotPublicationError("injected failure after target rename")
            pointer=_planned_pointer(plan); pointer_bytes=deterministic_json_bytes(pointer.model_dump(mode="json"))
            if hashlib.sha256(pointer_bytes).hexdigest()!=plan.planned_pointer_sha256 or pointer.pointer_content_fingerprint!=plan.planned_pointer_fingerprint:
                raise DashboardSnapshotPublicationError("planned pointer artifact mismatch")
            _write_pointer(root,pointer)
            if failpoint=="after_pointer_write": raise DashboardSnapshotPublicationError("injected failure after pointer write")
        except Exception:
            if staging.exists() and not staging.is_symlink(): shutil.rmtree(staging)
            # Completed immutable targets survive a crash after rename for verify-then-link recovery.
            raise
    return read_active_dashboard_snapshot(root,legacy_root)


def verify_then_link(*, root: Path, legacy_root: Path, plan: DashboardSnapshotApprovalPlanV2,
                     expected_current_state_fingerprint: str,
                     freshness_validator: Callable[[], None] | None = None) -> ActiveDashboardSnapshot:
    root=_validated_root(root);validate_plan(plan)
    if not (plan.normal_freshness or plan.activation_allowed_by_review_authorization):
        raise DashboardSnapshotPublicationConflict("snapshot plan is not freshness-authorized")
    with _lock(root):
        if freshness_validator is not None:
            freshness_validator()
        if current_state_fingerprint(root,legacy_root)!=expected_current_state_fingerprint:
            raise DashboardSnapshotPublicationConflict("snapshot state changed before link recovery")
        target=Path(plan.target_path)
        if target != target_path(root, plan.release_id) or Path(plan.pointer_path) != pointer_path(root):
            raise DashboardSnapshotPublicationError("approved publication path mismatch")
        actual=_reference(target,storage_kind="data_root",logical_path=plan.target_logical_path)
        if actual.aggregate_sha256!=plan.aggregate_sha256 or actual.manifest_sha256!=plan.manifest_sha256:
            raise DashboardSnapshotPublicationError("completed snapshot target does not match approval")
        _write_pointer(root,_planned_pointer(plan))
    return read_active_dashboard_snapshot(root,legacy_root)


def rollback(*, root: Path, legacy_root: Path, expected_pointer_fingerprint: str, apply: bool=False):
    root=_validated_root(root);pointer=_read_pointer(root)
    if pointer is None: raise DashboardSnapshotPublicationError("snapshot pointer does not exist")
    if pointer.pointer_content_fingerprint!=expected_pointer_fingerprint:
        raise DashboardSnapshotPublicationConflict("rollback approval digest mismatch")
    target=_resolve_reference(root,legacy_root,pointer.rollback)
    if not apply: return target
    with _lock(root):
        current=_read_pointer(root)
        if current is None or current.pointer_content_fingerprint!=expected_pointer_fingerprint:
            raise DashboardSnapshotPublicationConflict("snapshot pointer changed after rollback approval")
        payload={"pointer_version":"2.0","status":"active","active":current.rollback.model_dump(mode="json"),
                 "rollback":current.active.model_dump(mode="json"),
                 "switched_at":datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                 "activation_pointer_fingerprint":current.activation_pointer_fingerprint}
        new=DashboardSnapshotActivePointerV2(**payload,pointer_content_fingerprint=canonical_sha(payload))
        _write_pointer(root,new)
    return read_active_dashboard_snapshot(root,legacy_root)
