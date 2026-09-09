"""Pipeline-aware planning above canonical EOD scheduler wake plan 1.1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import StrEnum

from tip_api.services.daily_eod_automation import (
    CONTRACT_VERSION as AUTOMATION_CONTRACT_VERSION,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_executor import OFFLINE_ACTIONS
from tip_api.services.daily_eod_scheduler import (
    SchedulerWakeStatus,
    plan_daily_eod_scheduler_wake,
    verify_daily_eod_scheduler_wake_plan,
)
from tip_api.services.daily_eod_readiness import DailyEodReadinessPolicy
from tip_api.services.daily_universe_membership_sidecar import (
    DailyUniverseMembershipSidecarPlan,
    MembershipSidecarAction,
    MembershipSidecarStatus,
    verify_daily_universe_membership_sidecar_plan,
)


CONTRACT_VERSION = "daily-eod-pipeline-wake-plan/2.1"
MANUAL_REVIEW_ACTIONS = {
    NextAction.REVIEW_PUBLICATION,
    NextAction.REVIEW_SNAPSHOT_PUBLICATION,
    NextAction.REVIEW_BUNDLE_DEPLOYMENT,
}


class DailyEodPipelineSchedulerError(RuntimeError):
    """Raised when one pipeline-aware wake cannot be planned exactly."""


class PipelineWakeStatus(StrEnum):
    WAITING = "waiting"
    READY_FOR_WAKE = "ready_for_wake"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class PipelineWakePhase(StrEnum):
    CANONICAL_DATA = "canonical_data"
    OFFLINE_PIPELINE = "offline_pipeline"
    MANUAL_REVIEW = "manual_review"
    BLOCKED = "blocked"


class PipelineWakeAction(StrEnum):
    WAIT = "wait"
    REVIEW_ONE_DATA_TRANSITION = "review_one_data_transition"
    INVOKE_ONE_DATA_TRANSITION = "invoke_one_data_transition"
    REVIEW_ONE_OFFLINE_TRANSITION = "review_one_offline_transition"
    INVOKE_ONE_OFFLINE_TRANSITION = "invoke_one_offline_transition"
    REVIEW_MANUAL_BOUNDARY = "review_manual_boundary"
    OPERATOR_DIAGNOSIS = "operator_diagnosis"


@dataclass(frozen=True, slots=True)
class DailyEodPipelineWakePlan:
    contract_version: str
    checked_at: str
    status: PipelineWakeStatus
    phase: PipelineWakePhase
    next_action: PipelineWakeAction
    target_session: str
    latest_canonical_session: str
    expected_latest_completed_session: str
    missing_session_count: int
    next_check_at: str | None
    pipeline_next_action: str | None
    reason_codes: tuple[str, ...]
    scheduler_wake_plan_fingerprint: str
    automation_plan_fingerprint: str | None
    research_sidecar_status: str | None
    research_sidecar_next_action: str | None
    research_sidecar_plan_fingerprint: str | None
    research_sidecar_website_pipeline_blocked: bool
    scheduler_candidate_enabled: bool
    scheduler_installation_performed: bool
    coordinator_invocation_scope: str
    coordinator_invocation_limit: int
    coordinator_invocation_count: int
    automatic_retry_enabled: bool
    automatic_recovery_enabled: bool
    publication_authorized: bool
    deployment_authorized: bool
    credential_access_count: int
    external_request_count: int
    filesystem_write_count: int
    production_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))  # type: ignore[return-value]


def plan_daily_eod_pipeline_wake(
    *,
    checked_at: datetime,
    completed_sessions: tuple[date, ...],
    latest_pipeline_plan: DailyEodAutomationPlan | None = None,
    membership_sidecar_plan: DailyUniverseMembershipSidecarPlan | None = None,
    review_enabled_candidate: bool = False,
    policy: DailyEodReadinessPolicy | None = None,
) -> DailyEodPipelineWakePlan:
    """Plan data or offline progress while stopping at every manual boundary."""

    scheduler_plan = plan_daily_eod_scheduler_wake(
        checked_at=checked_at,
        completed_sessions=completed_sessions,
        review_enabled_candidate=False,
        policy=policy,
    )
    verify_daily_eod_scheduler_wake_plan(scheduler_plan)
    canonical_current = scheduler_plan.missing_session_count == 0
    if not canonical_current:
        if latest_pipeline_plan is not None:
            raise DailyEodPipelineSchedulerError(
                "pipeline plan is ambiguous while canonical data is missing"
            )
        ready = scheduler_plan.status is SchedulerWakeStatus.READY_FOR_WAKE
        return _build_plan(
            scheduler_plan=scheduler_plan,
            status=(
                PipelineWakeStatus.READY_FOR_WAKE
                if ready
                else PipelineWakeStatus.WAITING
            ),
            phase=PipelineWakePhase.CANONICAL_DATA,
            next_action=(
                PipelineWakeAction.INVOKE_ONE_DATA_TRANSITION
                if ready and review_enabled_candidate
                else (
                    PipelineWakeAction.REVIEW_ONE_DATA_TRANSITION
                    if ready
                    else PipelineWakeAction.WAIT
                )
            ),
            target_session=scheduler_plan.target_session,
            next_check_at=scheduler_plan.next_check_at,
            pipeline_next_action=None,
            reasons=scheduler_plan.reason_codes,
            automation_plan_fingerprint=None,
            membership_sidecar_plan=membership_sidecar_plan,
            review_enabled_candidate=review_enabled_candidate,
            coordinator_scope="data" if ready else "none",
        )

    if latest_pipeline_plan is None:
        raise DailyEodPipelineSchedulerError(
            "current canonical state requires its exact pipeline plan"
        )
    _verify_automation_plan(
        latest_pipeline_plan,
        expected_session=scheduler_plan.latest_canonical_session,
    )
    if latest_pipeline_plan.status is PlanStatus.READY_FOR_OFFLINE_CALCULATION:
        if latest_pipeline_plan.next_action not in OFFLINE_ACTIONS:
            raise DailyEodPipelineSchedulerError(
                "ready pipeline plan does not select an offline action"
            )
        return _build_plan(
            scheduler_plan=scheduler_plan,
            status=PipelineWakeStatus.READY_FOR_WAKE,
            phase=PipelineWakePhase.OFFLINE_PIPELINE,
            next_action=(
                PipelineWakeAction.INVOKE_ONE_OFFLINE_TRANSITION
                if review_enabled_candidate
                else PipelineWakeAction.REVIEW_ONE_OFFLINE_TRANSITION
            ),
            target_session=scheduler_plan.latest_canonical_session,
            next_check_at=scheduler_plan.checked_at,
            pipeline_next_action=latest_pipeline_plan.next_action.value,
            reasons=("canonical_eod_current", "offline_pipeline_incomplete"),
            automation_plan_fingerprint=(
                latest_pipeline_plan.logical_content_fingerprint
            ),
            membership_sidecar_plan=membership_sidecar_plan,
            review_enabled_candidate=review_enabled_candidate,
            coordinator_scope="offline",
        )
    if latest_pipeline_plan.status is PlanStatus.ANALYTICS_READY:
        if latest_pipeline_plan.next_action not in MANUAL_REVIEW_ACTIONS:
            raise DailyEodPipelineSchedulerError(
                "analytics-ready pipeline plan has no manual review action"
            )
        return _build_plan(
            scheduler_plan=scheduler_plan,
            status=PipelineWakeStatus.REVIEW_REQUIRED,
            phase=PipelineWakePhase.MANUAL_REVIEW,
            next_action=PipelineWakeAction.REVIEW_MANUAL_BOUNDARY,
            target_session=scheduler_plan.latest_canonical_session,
            next_check_at=None,
            pipeline_next_action=latest_pipeline_plan.next_action.value,
            reasons=("canonical_eod_current", "manual_pipeline_review_required"),
            automation_plan_fingerprint=(
                latest_pipeline_plan.logical_content_fingerprint
            ),
            membership_sidecar_plan=membership_sidecar_plan,
            review_enabled_candidate=review_enabled_candidate,
            coordinator_scope="none",
        )
    if latest_pipeline_plan.status in {
        PlanStatus.BLOCKED,
        PlanStatus.WAITING_FOR_AUTHORIZED_INPUT,
    }:
        return _build_plan(
            scheduler_plan=scheduler_plan,
            status=PipelineWakeStatus.BLOCKED,
            phase=PipelineWakePhase.BLOCKED,
            next_action=PipelineWakeAction.OPERATOR_DIAGNOSIS,
            target_session=scheduler_plan.latest_canonical_session,
            next_check_at=None,
            pipeline_next_action=latest_pipeline_plan.next_action.value,
            reasons=(
                "canonical_eod_pipeline_state_conflict",
                *latest_pipeline_plan.reason_codes,
            ),
            automation_plan_fingerprint=(
                latest_pipeline_plan.logical_content_fingerprint
            ),
            membership_sidecar_plan=membership_sidecar_plan,
            review_enabled_candidate=review_enabled_candidate,
            coordinator_scope="none",
        )
    raise DailyEodPipelineSchedulerError("pipeline plan status is unsupported")


def verify_daily_eod_pipeline_wake_plan(plan: DailyEodPipelineWakePlan) -> None:
    if not isinstance(plan, DailyEodPipelineWakePlan):
        raise DailyEodPipelineSchedulerError(
            "pipeline wake plan contract is invalid"
        )
    logical = asdict(plan)
    logical.pop("logical_content_fingerprint")
    if (
        plan.contract_version != CONTRACT_VERSION
        or plan.logical_content_fingerprint != _fingerprint(_jsonable(logical))
    ):
        raise DailyEodPipelineSchedulerError(
            "pipeline wake plan content fingerprint mismatch"
        )
    _verify_plan_semantics(plan)


def _verify_plan_semantics(plan: DailyEodPipelineWakePlan) -> None:
    if (
        not isinstance(plan.status, PipelineWakeStatus)
        or not isinstance(plan.phase, PipelineWakePhase)
        or not isinstance(plan.next_action, PipelineWakeAction)
    ):
        raise DailyEodPipelineSchedulerError(
            "pipeline wake plan enum fields are invalid"
        )
    expected_pairs = {
        PipelineWakeStatus.WAITING: {
            (PipelineWakePhase.CANONICAL_DATA, PipelineWakeAction.WAIT),
        },
        PipelineWakeStatus.READY_FOR_WAKE: {
            (
                PipelineWakePhase.CANONICAL_DATA,
                PipelineWakeAction.REVIEW_ONE_DATA_TRANSITION,
            ),
            (
                PipelineWakePhase.CANONICAL_DATA,
                PipelineWakeAction.INVOKE_ONE_DATA_TRANSITION,
            ),
            (
                PipelineWakePhase.OFFLINE_PIPELINE,
                PipelineWakeAction.REVIEW_ONE_OFFLINE_TRANSITION,
            ),
            (
                PipelineWakePhase.OFFLINE_PIPELINE,
                PipelineWakeAction.INVOKE_ONE_OFFLINE_TRANSITION,
            ),
        },
        PipelineWakeStatus.REVIEW_REQUIRED: {
            (
                PipelineWakePhase.MANUAL_REVIEW,
                PipelineWakeAction.REVIEW_MANUAL_BOUNDARY,
            ),
        },
        PipelineWakeStatus.BLOCKED: {
            (
                PipelineWakePhase.BLOCKED,
                PipelineWakeAction.OPERATOR_DIAGNOSIS,
            ),
        },
    }
    if (plan.phase, plan.next_action) not in expected_pairs[plan.status]:
        raise DailyEodPipelineSchedulerError(
            "pipeline wake plan status and action conflict"
        )
    sidecar_values = (
        plan.research_sidecar_status,
        plan.research_sidecar_next_action,
        plan.research_sidecar_plan_fingerprint,
    )
    if any(value is not None for value in sidecar_values):
        if any(value is None for value in sidecar_values):
            raise DailyEodPipelineSchedulerError(
                "Membership sidecar projection is incomplete"
            )
        try:
            MembershipSidecarStatus(str(plan.research_sidecar_status))
            MembershipSidecarAction(str(plan.research_sidecar_next_action))
        except ValueError as exc:
            raise DailyEodPipelineSchedulerError(
                "Membership sidecar projection is invalid"
            ) from exc
        if not _is_fingerprint(plan.research_sidecar_plan_fingerprint):
            raise DailyEodPipelineSchedulerError(
                "Membership sidecar projection fingerprint is invalid"
            )
    invoke_actions = {
        PipelineWakeAction.INVOKE_ONE_DATA_TRANSITION,
        PipelineWakeAction.INVOKE_ONE_OFFLINE_TRANSITION,
    }
    expected_scope = {
        PipelineWakePhase.CANONICAL_DATA: (
            "none" if plan.status is PipelineWakeStatus.WAITING else "data"
        ),
        PipelineWakePhase.OFFLINE_PIPELINE: "offline",
        PipelineWakePhase.MANUAL_REVIEW: "none",
        PipelineWakePhase.BLOCKED: "none",
    }[plan.phase]
    if (
        plan.coordinator_invocation_scope != expected_scope
        or (
            plan.status is PipelineWakeStatus.READY_FOR_WAKE
            and (plan.next_action in invoke_actions)
            != plan.scheduler_candidate_enabled
        )
        or plan.scheduler_installation_performed
        or plan.coordinator_invocation_limit != 1
        or plan.coordinator_invocation_count != 0
        or plan.automatic_retry_enabled
        or plan.automatic_recovery_enabled
        or plan.publication_authorized
        or plan.deployment_authorized
        or plan.research_sidecar_website_pipeline_blocked
        or plan.credential_access_count != 0
        or plan.external_request_count != 0
        or plan.filesystem_write_count != 0
        or plan.production_write_count != 0
    ):
        raise DailyEodPipelineSchedulerError(
            "pipeline wake plan exceeds planning authority"
        )


def _verify_automation_plan(
    plan: DailyEodAutomationPlan,
    *,
    expected_session: str,
) -> None:
    if not isinstance(plan, DailyEodAutomationPlan):
        raise DailyEodPipelineSchedulerError("automation plan contract is invalid")
    logical = asdict(plan)
    logical.pop("logical_content_fingerprint")
    if (
        plan.contract_version != AUTOMATION_CONTRACT_VERSION
        or plan.target_session != expected_session
        or plan.logical_content_fingerprint != _fingerprint(_jsonable(logical))
        or plan.publication_authorized
        or plan.deployment_authorized
        or plan.scheduler_enabled
        or plan.external_request_count != 0
        or plan.production_write_count != 0
    ):
        raise DailyEodPipelineSchedulerError(
            "automation plan exceeds pipeline wake boundary"
        )


def _build_plan(
    *,
    scheduler_plan,
    status: PipelineWakeStatus,
    phase: PipelineWakePhase,
    next_action: PipelineWakeAction,
    target_session: str,
    next_check_at: str | None,
    pipeline_next_action: str | None,
    reasons: tuple[str, ...],
    automation_plan_fingerprint: str | None,
    membership_sidecar_plan: DailyUniverseMembershipSidecarPlan | None,
    review_enabled_candidate: bool,
    coordinator_scope: str,
) -> DailyEodPipelineWakePlan:
    sidecar_status = None
    sidecar_action = None
    sidecar_fingerprint = None
    sidecar_website_blocked = False
    if membership_sidecar_plan is not None:
        verify_daily_universe_membership_sidecar_plan(membership_sidecar_plan)
        if (
            membership_sidecar_plan.target_session != target_session
            or membership_sidecar_plan.primary_automation_plan_fingerprint
            != automation_plan_fingerprint
        ):
            raise DailyEodPipelineSchedulerError(
                "Membership sidecar differs from the primary pipeline plan"
            )
        sidecar_status = membership_sidecar_plan.status.value
        sidecar_action = membership_sidecar_plan.next_action.value
        sidecar_fingerprint = (
            membership_sidecar_plan.logical_content_fingerprint
        )
        sidecar_website_blocked = (
            membership_sidecar_plan.website_pipeline_blocked
        )
    logical = {
        "contract_version": CONTRACT_VERSION,
        "checked_at": scheduler_plan.checked_at,
        "status": status.value,
        "phase": phase.value,
        "next_action": next_action.value,
        "target_session": target_session,
        "latest_canonical_session": scheduler_plan.latest_canonical_session,
        "expected_latest_completed_session": (
            scheduler_plan.expected_latest_completed_session
        ),
        "missing_session_count": scheduler_plan.missing_session_count,
        "next_check_at": next_check_at,
        "pipeline_next_action": pipeline_next_action,
        "reason_codes": list(reasons),
        "scheduler_wake_plan_fingerprint": (
            scheduler_plan.logical_content_fingerprint
        ),
        "automation_plan_fingerprint": automation_plan_fingerprint,
        "research_sidecar_status": sidecar_status,
        "research_sidecar_next_action": sidecar_action,
        "research_sidecar_plan_fingerprint": sidecar_fingerprint,
        "research_sidecar_website_pipeline_blocked": sidecar_website_blocked,
        "scheduler_candidate_enabled": review_enabled_candidate,
        "scheduler_installation_performed": False,
        "coordinator_invocation_scope": coordinator_scope,
        "coordinator_invocation_limit": 1,
        "coordinator_invocation_count": 0,
        "automatic_retry_enabled": False,
        "automatic_recovery_enabled": False,
        "publication_authorized": False,
        "deployment_authorized": False,
        "credential_access_count": 0,
        "external_request_count": 0,
        "filesystem_write_count": 0,
        "production_write_count": 0,
    }
    result = DailyEodPipelineWakePlan(
        contract_version=CONTRACT_VERSION,
        checked_at=scheduler_plan.checked_at,
        status=status,
        phase=phase,
        next_action=next_action,
        target_session=target_session,
        latest_canonical_session=scheduler_plan.latest_canonical_session,
        expected_latest_completed_session=(
            scheduler_plan.expected_latest_completed_session
        ),
        missing_session_count=scheduler_plan.missing_session_count,
        next_check_at=next_check_at,
        pipeline_next_action=pipeline_next_action,
        reason_codes=reasons,
        scheduler_wake_plan_fingerprint=(
            scheduler_plan.logical_content_fingerprint
        ),
        automation_plan_fingerprint=automation_plan_fingerprint,
        research_sidecar_status=sidecar_status,
        research_sidecar_next_action=sidecar_action,
        research_sidecar_plan_fingerprint=sidecar_fingerprint,
        research_sidecar_website_pipeline_blocked=sidecar_website_blocked,
        scheduler_candidate_enabled=review_enabled_candidate,
        scheduler_installation_performed=False,
        coordinator_invocation_scope=coordinator_scope,
        coordinator_invocation_limit=1,
        coordinator_invocation_count=0,
        automatic_retry_enabled=False,
        automatic_recovery_enabled=False,
        publication_authorized=False,
        deployment_authorized=False,
        credential_access_count=0,
        external_request_count=0,
        filesystem_write_count=0,
        production_write_count=0,
        logical_content_fingerprint=_fingerprint(logical),
    )
    verify_daily_eod_pipeline_wake_plan(result)
    return result


def _jsonable(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
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


def _is_fingerprint(value: str | None) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
