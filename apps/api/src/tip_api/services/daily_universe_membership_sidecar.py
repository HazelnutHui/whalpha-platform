"""Read-only planning for daily Universe Membership research continuity."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Callable

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.persistence.parquet.security_evidence import (
    read_completed_security_evidence_snapshot,
)
from tip_api.services.daily_eod_automation import (
    CONTRACT_VERSION as AUTOMATION_CONTRACT_VERSION,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_executor import OFFLINE_ACTIONS
from tip_api.services.daily_universe_membership_continuation import (
    METHODOLOGY_VERSION,
    DailyUniverseMembershipContinuationResult,
    read_daily_universe_membership_candidate,
)
from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    validate_offline_artifact_location,
)
from tip_api.services.universe_membership_apply_plan import (
    UniverseMembershipApplyPlanEvidence,
    read_universe_membership_apply_plan,
)
from tip_api.services.universe_membership_canonical import (
    PUBLICATION_DIRECTORY,
    PUBLICATION_POLICY_ID,
    read_canonical_universe_membership,
)


CONTRACT_VERSION = "daily-universe-membership-sidecar-plan/1.0"
CANDIDATE_ROOT_NAME = "universe-membership-candidate"
APPLY_PLAN_NAME = "universe-membership-plan.json"
MANUAL_REVIEW_ACTIONS = {
    NextAction.REVIEW_PUBLICATION,
    NextAction.REVIEW_SNAPSHOT_PUBLICATION,
    NextAction.REVIEW_BUNDLE_DEPLOYMENT,
}


class DailyUniverseMembershipSidecarError(RuntimeError):
    """Raised when a read-only Membership sidecar plan cannot be trusted."""


class MembershipSidecarStatus(StrEnum):
    WAITING = "waiting"
    READY = "ready"
    REVIEW_REQUIRED = "review_required"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class MembershipSidecarAction(StrEnum):
    WAIT_FOR_CANONICAL_INPUT = "wait_for_canonical_input"
    PREPARE_CANDIDATE = "prepare_candidate"
    WAIT_FOR_PRIMARY_PIPELINE = "wait_for_primary_pipeline"
    PREPARE_APPLY_PLAN = "prepare_apply_plan"
    REVIEW_APPLY = "review_apply"
    NONE = "none"
    OPERATOR_DIAGNOSIS = "operator_diagnosis"


@dataclass(frozen=True, slots=True)
class DailyUniverseMembershipSidecarPlan:
    contract_version: str
    checked_at: str
    target_session: str
    status: MembershipSidecarStatus
    next_action: MembershipSidecarAction
    reason_codes: tuple[str, ...]
    primary_automation_status: str
    primary_automation_next_action: str
    primary_automation_plan_fingerprint: str
    catalog_as_of_date: str
    catalog_snapshot_fingerprint: str | None
    candidate_partition_path: str
    candidate_status: str | None
    record_count: int
    membership_logical_fingerprint: str | None
    point_in_time_eligibility: str | None
    apply_plan_fingerprint: str | None
    canonical_publication_fingerprint: str | None
    website_pipeline_blocked: bool
    apply_authorized: bool
    historical_coverage_authorized: bool
    research_performance_authorized: bool
    scheduler_enabled: bool
    external_request_count: int
    production_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))  # type: ignore[return-value]


CatalogReader = Callable[..., object]
CandidateReader = Callable[..., DailyUniverseMembershipContinuationResult]
ApplyPlanReader = Callable[..., UniverseMembershipApplyPlanEvidence]
CanonicalReader = Callable[..., object]


def plan_daily_universe_membership_sidecar(
    *,
    checked_at: datetime,
    target_session: date,
    data_root: Path,
    catalog_as_of_date: date,
    candidate_root: Path,
    apply_plan_path: Path,
    primary_automation_plan: DailyEodAutomationPlan,
    catalog_reader: CatalogReader = read_completed_security_evidence_snapshot,
    candidate_reader: CandidateReader = read_daily_universe_membership_candidate,
    apply_plan_reader: ApplyPlanReader = read_universe_membership_apply_plan,
    canonical_reader: CanonicalReader = read_canonical_universe_membership,
) -> DailyUniverseMembershipSidecarPlan:
    """Report the next research-side action without executing it."""

    checked_at = normalize_utc_datetime(checked_at)
    _validate_paths(
        target_session=target_session,
        candidate_root=candidate_root,
        apply_plan_path=apply_plan_path,
    )
    _verify_primary_automation_plan(
        primary_automation_plan,
        expected_session=target_session.isoformat(),
    )
    candidate_partition = _candidate_partition(candidate_root, target_session)
    membership_target, publication_target = _canonical_targets(
        data_root,
        target_session,
    )
    membership_exists = os.path.lexists(membership_target)
    publication_exists = os.path.lexists(publication_target)
    if membership_exists or publication_exists:
        if not membership_exists or not publication_exists:
            return _build_plan(
                checked_at=checked_at,
                target_session=target_session,
                primary=primary_automation_plan,
                catalog_as_of_date=catalog_as_of_date,
                candidate_partition=candidate_partition,
                status=MembershipSidecarStatus.BLOCKED,
                next_action=MembershipSidecarAction.OPERATOR_DIAGNOSIS,
                reasons=("canonical_membership_partial_state",),
            )
        try:
            canonical = canonical_reader(
                data_root=data_root,
                methodology_version=METHODOLOGY_VERSION,
                session_date=target_session,
            )
        except Exception:
            return _build_plan(
                checked_at=checked_at,
                target_session=target_session,
                primary=primary_automation_plan,
                catalog_as_of_date=catalog_as_of_date,
                candidate_partition=candidate_partition,
                status=MembershipSidecarStatus.BLOCKED,
                next_action=MembershipSidecarAction.OPERATOR_DIAGNOSIS,
                reasons=("canonical_membership_invalid",),
            )
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.COMPLETE,
            next_action=MembershipSidecarAction.NONE,
            reasons=("canonical_membership_complete",),
            record_count=len(canonical.records),
            membership_fingerprint=(
                canonical.membership_manifest.logical_fingerprint
            ),
            point_in_time_eligibility=(
                canonical.publication.point_in_time_eligibility.value
            ),
            canonical_publication_fingerprint=(
                canonical.publication.logical_fingerprint
            ),
        )

    if primary_automation_plan.status is PlanStatus.BLOCKED:
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.BLOCKED,
            next_action=MembershipSidecarAction.OPERATOR_DIAGNOSIS,
            reasons=(
                "primary_automation_blocked",
                *primary_automation_plan.reason_codes,
            ),
        )
    if primary_automation_plan.status is PlanStatus.WAITING_FOR_AUTHORIZED_INPUT:
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.WAITING,
            next_action=MembershipSidecarAction.WAIT_FOR_CANONICAL_INPUT,
            reasons=("same_session_eod_or_identity_incomplete",),
        )

    try:
        catalog = catalog_reader(data_root, as_of_date=catalog_as_of_date)
        catalog_manifest = catalog.manifest
        if (
            catalog_manifest.as_of_date != catalog_as_of_date
            or catalog_manifest.as_of_date > target_session
            or catalog_manifest.created_at > checked_at
        ):
            raise DailyUniverseMembershipSidecarError(
                "security-evidence catalog time boundary differs"
            )
        catalog_fingerprint = catalog_manifest.logical_content_sha256
    except Exception:
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.BLOCKED,
            next_action=MembershipSidecarAction.OPERATOR_DIAGNOSIS,
            reasons=("security_evidence_catalog_invalid",),
        )

    if not os.path.lexists(candidate_partition):
        if os.path.lexists(apply_plan_path) or os.path.lexists(
            apply_plan_path.with_name(f".{apply_plan_path.name}.staging")
        ):
            return _build_plan(
                checked_at=checked_at,
                target_session=target_session,
                primary=primary_automation_plan,
                catalog_as_of_date=catalog_as_of_date,
                catalog_fingerprint=catalog_fingerprint,
                candidate_partition=candidate_partition,
                status=MembershipSidecarStatus.BLOCKED,
                next_action=MembershipSidecarAction.OPERATOR_DIAGNOSIS,
                reasons=("membership_plan_without_candidate",),
            )
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            catalog_fingerprint=catalog_fingerprint,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.READY,
            next_action=MembershipSidecarAction.PREPARE_CANDIDATE,
            reasons=("daily_membership_candidate_missing",),
        )

    try:
        candidate = candidate_reader(
            data_root=data_root,
            session_date=target_session,
            assessed_at=checked_at,
            candidate_root=candidate_root,
        )
        _verify_candidate(candidate, target_session, candidate_partition)
    except Exception:
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            catalog_fingerprint=catalog_fingerprint,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.BLOCKED,
            next_action=MembershipSidecarAction.OPERATOR_DIAGNOSIS,
            reasons=("daily_membership_candidate_invalid",),
        )
    candidate_values = {
        "candidate_status": candidate.candidate_status,
        "record_count": candidate.record_count,
        "membership_fingerprint": candidate.membership_logical_fingerprint,
        "point_in_time_eligibility": candidate.point_in_time_eligibility,
    }
    if candidate.status == "outcome_only_candidate":
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            catalog_fingerprint=catalog_fingerprint,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.BLOCKED,
            next_action=MembershipSidecarAction.OPERATOR_DIAGNOSIS,
            reasons=("membership_candidate_outcome_only",),
            **candidate_values,
        )

    primary_final = (
        primary_automation_plan.status is PlanStatus.ANALYTICS_READY
        and primary_automation_plan.next_action
        is NextAction.REVIEW_BUNDLE_DEPLOYMENT
    )
    plan_exists = os.path.lexists(apply_plan_path)
    plan_staging_exists = os.path.lexists(
        apply_plan_path.with_name(f".{apply_plan_path.name}.staging")
    )
    if plan_staging_exists:
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            catalog_fingerprint=catalog_fingerprint,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.BLOCKED,
            next_action=MembershipSidecarAction.OPERATOR_DIAGNOSIS,
            reasons=("membership_apply_plan_staging_residue",),
            **candidate_values,
        )
    if plan_exists and not primary_final:
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            catalog_fingerprint=catalog_fingerprint,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.BLOCKED,
            next_action=MembershipSidecarAction.OPERATOR_DIAGNOSIS,
            reasons=("membership_apply_plan_precedes_primary_final_boundary",),
            **candidate_values,
        )
    if not primary_final:
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            catalog_fingerprint=catalog_fingerprint,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.WAITING,
            next_action=MembershipSidecarAction.WAIT_FOR_PRIMARY_PIPELINE,
            reasons=("primary_canonical_writes_may_remain",),
            **candidate_values,
        )
    if not plan_exists:
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            catalog_fingerprint=catalog_fingerprint,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.READY,
            next_action=MembershipSidecarAction.PREPARE_APPLY_PLAN,
            reasons=("membership_apply_plan_missing_at_final_boundary",),
            **candidate_values,
        )
    try:
        plan_evidence = apply_plan_reader(plan_path=apply_plan_path)
        membership_plan = plan_evidence.plan
        if (
            plan_evidence.plan_path != apply_plan_path
            or membership_plan.publication.session_date != target_session
            or Path(membership_plan.data_root) != data_root
            or Path(membership_plan.candidate_root) != candidate_root
            or Path(membership_plan.candidate_membership_partition)
            != candidate_partition
            or membership_plan.publication.membership_logical_fingerprint
            != candidate.membership_logical_fingerprint
        ):
            raise DailyUniverseMembershipSidecarError(
                "Membership Apply plan boundary differs"
            )
    except Exception:
        return _build_plan(
            checked_at=checked_at,
            target_session=target_session,
            primary=primary_automation_plan,
            catalog_as_of_date=catalog_as_of_date,
            catalog_fingerprint=catalog_fingerprint,
            candidate_partition=candidate_partition,
            status=MembershipSidecarStatus.BLOCKED,
            next_action=MembershipSidecarAction.OPERATOR_DIAGNOSIS,
            reasons=("membership_apply_plan_invalid",),
            **candidate_values,
        )
    return _build_plan(
        checked_at=checked_at,
        target_session=target_session,
        primary=primary_automation_plan,
        catalog_as_of_date=catalog_as_of_date,
        catalog_fingerprint=catalog_fingerprint,
        candidate_partition=candidate_partition,
        status=MembershipSidecarStatus.REVIEW_REQUIRED,
        next_action=MembershipSidecarAction.REVIEW_APPLY,
        reasons=("membership_apply_plan_ready_for_review",),
        apply_plan_fingerprint=membership_plan.logical_fingerprint,
        **candidate_values,
    )


def verify_daily_universe_membership_sidecar_plan(
    plan: DailyUniverseMembershipSidecarPlan,
) -> None:
    if not isinstance(plan, DailyUniverseMembershipSidecarPlan):
        raise DailyUniverseMembershipSidecarError(
            "Membership sidecar plan contract is invalid"
        )
    logical = asdict(plan)
    logical.pop("logical_content_fingerprint")
    if (
        plan.contract_version != CONTRACT_VERSION
        or plan.logical_content_fingerprint != _fingerprint(_jsonable(logical))
    ):
        raise DailyUniverseMembershipSidecarError(
            "Membership sidecar plan content fingerprint mismatch"
        )
    expected_pairs = {
        MembershipSidecarStatus.WAITING: {
            MembershipSidecarAction.WAIT_FOR_CANONICAL_INPUT,
            MembershipSidecarAction.WAIT_FOR_PRIMARY_PIPELINE,
        },
        MembershipSidecarStatus.READY: {
            MembershipSidecarAction.PREPARE_CANDIDATE,
            MembershipSidecarAction.PREPARE_APPLY_PLAN,
        },
        MembershipSidecarStatus.REVIEW_REQUIRED: {
            MembershipSidecarAction.REVIEW_APPLY,
        },
        MembershipSidecarStatus.COMPLETE: {MembershipSidecarAction.NONE},
        MembershipSidecarStatus.BLOCKED: {
            MembershipSidecarAction.OPERATOR_DIAGNOSIS,
        },
    }
    try:
        date.fromisoformat(plan.target_session)
        datetime.fromisoformat(plan.checked_at)
        date.fromisoformat(plan.catalog_as_of_date)
    except ValueError as exc:
        raise DailyUniverseMembershipSidecarError(
            "Membership sidecar plan time identity is invalid"
        ) from exc
    if (
        plan.next_action not in expected_pairs[plan.status]
        or not plan.reason_codes
        or plan.record_count < 0
        or plan.website_pipeline_blocked
        or plan.apply_authorized
        or plan.historical_coverage_authorized
        or plan.research_performance_authorized
        or plan.scheduler_enabled
        or plan.external_request_count != 0
        or plan.production_write_count != 0
    ):
        raise DailyUniverseMembershipSidecarError(
            "Membership sidecar plan exceeds planning authority"
        )


def _build_plan(
    *,
    checked_at: datetime,
    target_session: date,
    primary: DailyEodAutomationPlan,
    catalog_as_of_date: date,
    candidate_partition: Path,
    status: MembershipSidecarStatus,
    next_action: MembershipSidecarAction,
    reasons: tuple[str, ...],
    catalog_fingerprint: str | None = None,
    candidate_status: str | None = None,
    record_count: int = 0,
    membership_fingerprint: str | None = None,
    point_in_time_eligibility: str | None = None,
    apply_plan_fingerprint: str | None = None,
    canonical_publication_fingerprint: str | None = None,
) -> DailyUniverseMembershipSidecarPlan:
    logical = {
        "contract_version": CONTRACT_VERSION,
        "checked_at": checked_at.isoformat(),
        "target_session": target_session.isoformat(),
        "status": status.value,
        "next_action": next_action.value,
        "reason_codes": list(reasons),
        "primary_automation_status": primary.status.value,
        "primary_automation_next_action": primary.next_action.value,
        "primary_automation_plan_fingerprint": (
            primary.logical_content_fingerprint
        ),
        "catalog_as_of_date": catalog_as_of_date.isoformat(),
        "catalog_snapshot_fingerprint": catalog_fingerprint,
        "candidate_partition_path": str(candidate_partition),
        "candidate_status": candidate_status,
        "record_count": record_count,
        "membership_logical_fingerprint": membership_fingerprint,
        "point_in_time_eligibility": point_in_time_eligibility,
        "apply_plan_fingerprint": apply_plan_fingerprint,
        "canonical_publication_fingerprint": canonical_publication_fingerprint,
        "website_pipeline_blocked": False,
        "apply_authorized": False,
        "historical_coverage_authorized": False,
        "research_performance_authorized": False,
        "scheduler_enabled": False,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    result = DailyUniverseMembershipSidecarPlan(
        contract_version=CONTRACT_VERSION,
        checked_at=checked_at.isoformat(),
        target_session=target_session.isoformat(),
        status=status,
        next_action=next_action,
        reason_codes=reasons,
        primary_automation_status=primary.status.value,
        primary_automation_next_action=primary.next_action.value,
        primary_automation_plan_fingerprint=(
            primary.logical_content_fingerprint
        ),
        catalog_as_of_date=catalog_as_of_date.isoformat(),
        catalog_snapshot_fingerprint=catalog_fingerprint,
        candidate_partition_path=str(candidate_partition),
        candidate_status=candidate_status,
        record_count=record_count,
        membership_logical_fingerprint=membership_fingerprint,
        point_in_time_eligibility=point_in_time_eligibility,
        apply_plan_fingerprint=apply_plan_fingerprint,
        canonical_publication_fingerprint=canonical_publication_fingerprint,
        website_pipeline_blocked=False,
        apply_authorized=False,
        historical_coverage_authorized=False,
        research_performance_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=_fingerprint(logical),
    )
    verify_daily_universe_membership_sidecar_plan(result)
    return result


def _verify_primary_automation_plan(
    plan: DailyEodAutomationPlan,
    *,
    expected_session: str,
) -> None:
    if not isinstance(plan, DailyEodAutomationPlan):
        raise DailyUniverseMembershipSidecarError(
            "primary automation plan contract is invalid"
        )
    logical = asdict(plan)
    logical.pop("logical_content_fingerprint")
    expected_actions = {
        PlanStatus.WAITING_FOR_AUTHORIZED_INPUT: {
            NextAction.PREPARE_IDENTITY_CATCHUP,
            NextAction.PREPARE_EOD_CATCHUP,
        },
        PlanStatus.READY_FOR_OFFLINE_CALCULATION: set(OFFLINE_ACTIONS),
        PlanStatus.ANALYTICS_READY: MANUAL_REVIEW_ACTIONS,
        PlanStatus.BLOCKED: {NextAction.OPERATOR_DIAGNOSIS},
    }
    if (
        plan.contract_version != AUTOMATION_CONTRACT_VERSION
        or plan.target_session != expected_session
        or plan.next_action not in expected_actions[plan.status]
        or plan.logical_content_fingerprint != _fingerprint(_jsonable(logical))
        or plan.publication_authorized
        or plan.deployment_authorized
        or plan.scheduler_enabled
        or plan.external_request_count != 0
        or plan.production_write_count != 0
    ):
        raise DailyUniverseMembershipSidecarError(
            "primary automation plan exceeds Membership sidecar boundary"
        )


def _validate_paths(
    *,
    target_session: date,
    candidate_root: Path,
    apply_plan_path: Path,
) -> None:
    if (
        candidate_root.name != CANDIDATE_ROOT_NAME
        or apply_plan_path.name != APPLY_PLAN_NAME
        or candidate_root.parent != apply_plan_path.parent
        or candidate_root.parent.name
        != f"session_date={target_session.isoformat()}"
    ):
        raise DailyUniverseMembershipSidecarError(
            "Membership sidecar workspace paths differ"
        )
    try:
        validate_offline_artifact_location(
            candidate_root,
            persistent_names={CANDIDATE_ROOT_NAME},
            allow_tmp_descendants=True,
        )
        validate_offline_artifact_location(
            apply_plan_path,
            persistent_names={APPLY_PLAN_NAME},
            allow_tmp_descendants=True,
        )
    except OfflineArtifactCustodyError as exc:
        raise DailyUniverseMembershipSidecarError(
            "Membership sidecar workspace custody differs"
        ) from exc


def _verify_candidate(
    candidate: DailyUniverseMembershipContinuationResult,
    target_session: date,
    candidate_partition: Path,
) -> None:
    if (
        not isinstance(candidate, DailyUniverseMembershipContinuationResult)
        or candidate.session_date != target_session.isoformat()
        or candidate.methodology_version != METHODOLOGY_VERSION
        or candidate.candidate_partition_path != str(candidate_partition)
        or candidate.status
        not in {
            "candidate_ready_for_publication_plan",
            "outcome_only_candidate",
        }
        or candidate.record_count <= 0
        or candidate.canonical_publication_fingerprint is not None
        or candidate.external_request_count != 0
        or candidate.canonical_data_write_count != 0
        or candidate.publication_authorized
        or candidate.historical_coverage_authorized
        or candidate.research_performance_authorized
        or candidate.scheduler_enabled
        or candidate.website_pipeline_blocked
    ):
        raise DailyUniverseMembershipSidecarError(
            "daily Membership candidate boundary differs"
        )


def _candidate_partition(candidate_root: Path, session_date: date) -> Path:
    return (
        candidate_root
        / "market-data"
        / "universe-membership"
        / "schema_version=1"
        / f"methodology_version={METHODOLOGY_VERSION}"
        / f"session_date={session_date.isoformat()}"
    )


def _canonical_targets(data_root: Path, session_date: date) -> tuple[Path, Path]:
    membership = (
        data_root
        / "market-data"
        / "universe-membership"
        / "schema_version=1"
        / f"methodology_version={METHODOLOGY_VERSION}"
        / f"session_date={session_date.isoformat()}"
    )
    publication = (
        data_root
        / "market-data"
        / PUBLICATION_DIRECTORY
        / "schema_version=1"
        / f"policy_id={PUBLICATION_POLICY_ID}"
        / f"methodology_version={METHODOLOGY_VERSION}"
        / f"session_date={session_date.isoformat()}"
    )
    return membership, publication


def _jsonable(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    return value


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
