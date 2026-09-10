"""Resumable archive of reconstructed Membership into research-only custody."""

from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from tip_api.contracts.market_data.v1 import UniverseMembershipPartitionManifestV1
from tip_api.services.historical_backfill_batch_runner import (
    prepare_historical_backfill_session_workspace,
    prepare_historical_backfill_workspace,
)
from tip_api.services.research_universe_membership_apply import (
    ResearchUniverseMembershipApplyError,
    apply_research_universe_membership_plan,
)
from tip_api.services.research_universe_membership_apply_plan import (
    PLAN_FILE_NAME,
    ResearchUniverseMembershipApplyPlanError,
    build_research_universe_membership_apply_plan,
    read_research_universe_membership_apply_plan,
)
from tip_api.services.research_universe_membership_canonical import (
    CanonicalResearchUniverseMembershipError,
    read_canonical_research_universe_membership,
    research_membership_partition,
)


class ResearchUniverseMembershipArchiveError(RuntimeError):
    """Raised when an archive input or workspace boundary is unsafe."""


@dataclass(frozen=True, slots=True)
class ResearchUniverseMembershipArchiveSession:
    session_date: str
    methodology_version: str
    status: str
    record_count: int | None
    custody_fingerprint: str | None
    failure_code: str | None


@dataclass(frozen=True, slots=True)
class ResearchUniverseMembershipArchiveResult:
    candidate_session_count: int
    applied_session_count: int
    reused_session_count: int
    failed_session_count: int
    planned_only_session_count: int
    record_count: int
    status: str
    sessions: tuple[ResearchUniverseMembershipArchiveSession, ...]
    external_request_count: int = 0
    overwritten_partition_count: int = 0
    deleted_partition_count: int = 0
    performance_authorized: bool = False
    production_authorized: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def archive_research_universe_membership_candidates(
    *,
    data_root: Path,
    candidate_root: Path,
    workspace_root: Path,
    created_at: datetime,
    execute: bool,
) -> ResearchUniverseMembershipArchiveResult:
    """Inspect or archive every unique completed candidate; isolate row failures."""

    candidate = _validated_candidate_root(candidate_root)
    workspace = prepare_historical_backfill_workspace(workspace_root)
    candidates = _discover_candidates(candidate)
    results: list[ResearchUniverseMembershipArchiveSession] = []
    for manifest, partition in candidates:
        target = research_membership_partition(
            data_root,
            methodology_version=manifest.methodology_version,
            session_date=manifest.session_date,
        )
        try:
            if os.path.lexists(target):
                existing = read_canonical_research_universe_membership(
                    data_root=data_root,
                    methodology_version=manifest.methodology_version,
                    session_date=manifest.session_date,
                )
                if (
                    existing.membership_manifest.logical_fingerprint
                    != manifest.logical_fingerprint
                    or existing.membership_manifest.physical_sha256
                    != manifest.physical_sha256
                ):
                    raise ResearchUniverseMembershipArchiveError(
                        "existing_target_conflicts_with_candidate"
                    )
                results.append(
                    _session_result(
                        manifest,
                        status="already_present",
                        custody_fingerprint=existing.custody.logical_fingerprint,
                    )
                )
                continue
            if not execute:
                results.append(_session_result(manifest, status="plan_required"))
                continue
            session_workspace = prepare_historical_backfill_session_workspace(
                workspace,
                manifest.session_date,
            )
            plan_path = session_workspace / PLAN_FILE_NAME
            if plan_path.exists():
                plan_sha = _file_sha256(plan_path)
                evidence = read_research_universe_membership_apply_plan(
                    plan_path=plan_path,
                    approved_plan_sha256=plan_sha,
                )
                if Path(evidence.plan.candidate_membership_partition) != partition:
                    raise ResearchUniverseMembershipArchiveError(
                        "existing_plan_candidate_path_differs"
                    )
            else:
                evidence = build_research_universe_membership_apply_plan(
                    data_root=data_root,
                    candidate_membership_partition=partition,
                    created_at=created_at,
                    plan_path=plan_path,
                )
            applied = apply_research_universe_membership_plan(
                plan_path=evidence.plan_path,
                approved_plan_sha256=evidence.plan_sha256,
                expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
                data_root=data_root,
            )
            results.append(
                _session_result(
                    manifest,
                    status=applied.status,
                    custody_fingerprint=applied.custody_logical_fingerprint,
                )
            )
        except (
            CanonicalResearchUniverseMembershipError,
            ResearchUniverseMembershipApplyPlanError,
            ResearchUniverseMembershipApplyError,
            ResearchUniverseMembershipArchiveError,
            OSError,
            ValueError,
        ) as exc:
            results.append(
                _session_result(
                    manifest,
                    status="failed",
                    failure_code=_failure_code(exc),
                )
            )

    sessions = tuple(results)
    failed = sum(item.status == "failed" for item in sessions)
    planned = sum(item.status == "plan_required" for item in sessions)
    applied = sum(item.status == "applied" for item in sessions)
    reused = sum(item.status == "already_present" for item in sessions)
    return ResearchUniverseMembershipArchiveResult(
        candidate_session_count=len(sessions),
        applied_session_count=applied,
        reused_session_count=reused,
        failed_session_count=failed,
        planned_only_session_count=planned,
        record_count=sum(
            item.record_count or 0
            for item in sessions
            if item.status in {"applied", "already_present"}
        ),
        status=(
            "completed_with_failures"
            if failed
            else "inspection_complete"
            if planned
            else "completed"
        ),
        sessions=sessions,
    )


def _validated_candidate_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ResearchUniverseMembershipArchiveError(
            "candidate root is unavailable or unsafe"
        )
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise ResearchUniverseMembershipArchiveError(
            "candidate root must be normalized"
        )
    if resolved != Path("/tmp") and Path("/tmp") not in resolved.parents:
        raise ResearchUniverseMembershipArchiveError(
            "bulk candidate root must remain in temporary research custody"
        )
    for item in resolved.rglob("*"):
        if item.is_symlink():
            raise ResearchUniverseMembershipArchiveError(
                "candidate tree contains a symlink"
            )
    return resolved


def _discover_candidates(
    root: Path,
) -> tuple[tuple[UniverseMembershipPartitionManifestV1, Path], ...]:
    found: list[tuple[UniverseMembershipPartitionManifestV1, Path]] = []
    business_keys: set[tuple[str, str]] = set()
    for path in sorted(root.rglob("manifest.json")):
        try:
            manifest = UniverseMembershipPartitionManifestV1.model_validate_json(
                path.read_bytes()
            )
        except Exception:
            continue
        key = (manifest.methodology_version, manifest.session_date.isoformat())
        if key in business_keys:
            raise ResearchUniverseMembershipArchiveError(
                "candidate tree contains duplicate Membership business keys"
            )
        business_keys.add(key)
        found.append((manifest, path.parent))
    if not found:
        raise ResearchUniverseMembershipArchiveError(
            "candidate tree has no completed Membership partitions"
        )
    return tuple(
        sorted(
            found,
            key=lambda item: (item[0].session_date, item[0].methodology_version),
        )
    )


def _session_result(
    manifest: UniverseMembershipPartitionManifestV1,
    *,
    status: str,
    custody_fingerprint: str | None = None,
    failure_code: str | None = None,
) -> ResearchUniverseMembershipArchiveSession:
    return ResearchUniverseMembershipArchiveSession(
        session_date=manifest.session_date.isoformat(),
        methodology_version=manifest.methodology_version,
        status=status,
        record_count=manifest.record_count if failure_code is None else None,
        custody_fingerprint=custody_fingerprint,
        failure_code=failure_code,
    )


def _failure_code(exc: Exception) -> str:
    text = str(exc)
    if text and all(character.islower() or character == "_" for character in text):
        return text
    return type(exc).__name__


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
