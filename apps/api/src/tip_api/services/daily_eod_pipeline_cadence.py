"""Bounded, default-off cadence planning for distinct daily pipeline wakes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from tip_api.services.daily_eod_pipeline_scheduler import (
    DailyEodPipelineSchedulerError,
    DailyEodPipelineWakePlan,
    PipelineWakeAction,
    PipelineWakePhase,
    PipelineWakeStatus,
    verify_daily_eod_pipeline_wake_plan,
)


CONTRACT_VERSION = "daily-eod-bounded-cadence-plan/1.0"
EVIDENCE_CONTRACT_VERSION = "daily-eod-cadence-wake-evidence/1.0"
MAXIMUM_WAKE_LIMIT = 16
MAXIMUM_WINDOW_SECONDS = 4 * 60 * 60
MINIMUM_INTERVAL_FLOOR_SECONDS = 5 * 60


class DailyEodPipelineCadenceError(RuntimeError):
    """Raised when distinct wake cadence cannot be bounded exactly."""


class CadenceStatus(StrEnum):
    WAITING = "waiting"
    REVIEW_READY = "review_ready"
    WAKE_READY = "wake_ready"
    STOPPED = "stopped"


class CadenceAction(StrEnum):
    WAIT_FOR_PIPELINE_CHECK = "wait_for_pipeline_check"
    WAIT_FOR_MINIMUM_INTERVAL = "wait_for_minimum_interval"
    REVIEW_ONE_TRANSITION = "review_one_transition"
    INVOKE_ONE_TRANSITION = "invoke_one_transition"
    STOP_FOR_MANUAL_REVIEW = "stop_for_manual_review"
    STOP_FOR_BLOCKED_STATE = "stop_for_blocked_state"
    STOP_AFTER_KNOWN_FAILURE = "stop_after_known_failure"
    STOP_AFTER_UNKNOWN_OUTCOME = "stop_after_unknown_outcome"
    STOP_AT_BUDGET = "stop_at_budget"


class CadenceWakeOutcome(StrEnum):
    ADVANCED = "advanced"
    NO_CHANGE = "no_change"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class BoundedCadencePolicy:
    minimum_interval_seconds: int = MINIMUM_INTERVAL_FLOOR_SECONDS
    maximum_window_seconds: int = MAXIMUM_WINDOW_SECONDS
    maximum_transition_wakes: int = MAXIMUM_WAKE_LIMIT

    @property
    def logical_content_fingerprint(self) -> str:
        _validate_policy(self)
        return _fingerprint(asdict(self))


@dataclass(frozen=True, slots=True)
class CadenceWakeEvidence:
    contract_version: str
    sequence: int
    target_session: str
    started_at: str
    completed_at: str | None
    pipeline_plan_fingerprint: str
    pipeline_action: str
    outcome: CadenceWakeOutcome
    transition_invocation_count: int
    result_fingerprint: str | None
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["outcome"] = self.outcome.value
        return value


@dataclass(frozen=True, slots=True)
class DailyEodBoundedCadencePlan:
    contract_version: str
    checked_at: str
    cadence_started_at: str
    cadence_expires_at: str
    target_session: str
    status: CadenceStatus
    next_action: CadenceAction
    next_wake_at: str | None
    reason_codes: tuple[str, ...]
    pipeline_status: str
    pipeline_phase: str
    pipeline_action: str
    pipeline_plan_fingerprint: str
    evidence_chain_fingerprint: str
    policy_fingerprint: str
    minimum_interval_seconds: int
    maximum_window_seconds: int
    maximum_transition_wakes: int
    transition_wakes_used: int
    transition_wakes_remaining: int
    cadence_candidate_enabled: bool
    pipeline_candidate_enabled: bool
    transition_invocation_limit: int
    transition_invocation_count: int
    automatic_retry_enabled: bool
    automatic_recovery_enabled: bool
    publication_authorized: bool
    deployment_authorized: bool
    credential_access_count: int
    external_request_count: int
    filesystem_write_count: int
    production_write_count: int
    scheduler_installation_performed: bool
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))  # type: ignore[return-value]


def record_cadence_wake_evidence(
    *,
    sequence: int,
    target_session: str,
    started_at: datetime,
    completed_at: datetime | None,
    pipeline_plan_fingerprint: str,
    pipeline_action: str,
    outcome: CadenceWakeOutcome,
    result_fingerprint: str | None,
) -> CadenceWakeEvidence:
    """Build immutable evidence for one already completed distinct wake."""

    started = _aware_utc(started_at)
    completed = None if completed_at is None else _aware_utc(completed_at)
    logical = {
        "contract_version": EVIDENCE_CONTRACT_VERSION,
        "sequence": sequence,
        "target_session": target_session,
        "started_at": started.isoformat(),
        "completed_at": None if completed is None else completed.isoformat(),
        "pipeline_plan_fingerprint": pipeline_plan_fingerprint,
        "pipeline_action": pipeline_action,
        "outcome": outcome.value,
        "transition_invocation_count": 1,
        "result_fingerprint": result_fingerprint,
    }
    result = CadenceWakeEvidence(
        contract_version=EVIDENCE_CONTRACT_VERSION,
        sequence=sequence,
        target_session=target_session,
        started_at=started.isoformat(),
        completed_at=None if completed is None else completed.isoformat(),
        pipeline_plan_fingerprint=pipeline_plan_fingerprint,
        pipeline_action=pipeline_action,
        outcome=outcome,
        transition_invocation_count=1,
        result_fingerprint=result_fingerprint,
        logical_content_fingerprint=_fingerprint(logical),
    )
    verify_cadence_wake_evidence(result)
    return result


def verify_cadence_wake_evidence(evidence: CadenceWakeEvidence) -> None:
    if not isinstance(evidence, CadenceWakeEvidence):
        raise DailyEodPipelineCadenceError("cadence wake evidence is invalid")
    logical = asdict(evidence)
    logical.pop("logical_content_fingerprint")
    if (
        evidence.contract_version != EVIDENCE_CONTRACT_VERSION
        or evidence.logical_content_fingerprint
        != _fingerprint(_jsonable(logical))
    ):
        raise DailyEodPipelineCadenceError(
            "cadence wake evidence fingerprint mismatch"
        )
    started = _parse_utc(evidence.started_at)
    completed = (
        None
        if evidence.completed_at is None
        else _parse_utc(evidence.completed_at)
    )
    known = evidence.outcome is not CadenceWakeOutcome.UNKNOWN
    try:
        date.fromisoformat(evidence.target_session)
        pipeline_action = PipelineWakeAction(evidence.pipeline_action)
    except ValueError as exc:
        raise DailyEodPipelineCadenceError(
            "cadence wake evidence identity is malformed"
        ) from exc
    if (
        evidence.sequence < 1
        or not evidence.target_session
        or not _is_fingerprint(evidence.pipeline_plan_fingerprint)
        or not evidence.pipeline_action
        or pipeline_action
        not in {
            PipelineWakeAction.INVOKE_ONE_DATA_TRANSITION,
            PipelineWakeAction.INVOKE_ONE_OFFLINE_TRANSITION,
        }
        or evidence.transition_invocation_count != 1
        or known != (completed is not None)
        or known != _is_fingerprint(evidence.result_fingerprint)
        or (completed is not None and completed < started)
    ):
        raise DailyEodPipelineCadenceError(
            "cadence wake evidence fields conflict"
        )


def plan_bounded_pipeline_cadence(
    *,
    checked_at: datetime,
    cadence_started_at: datetime,
    pipeline_plan: DailyEodPipelineWakePlan,
    prior_wakes: tuple[CadenceWakeEvidence, ...] = (),
    review_enabled_candidate: bool = False,
    policy: BoundedCadencePolicy | None = None,
) -> DailyEodBoundedCadencePlan:
    """Plan one distinct wake or stop; never invoke or loop."""

    checked = _aware_utc(checked_at)
    started = _aware_utc(cadence_started_at)
    selected_policy = policy or BoundedCadencePolicy()
    _validate_policy(selected_policy)
    try:
        verify_daily_eod_pipeline_wake_plan(pipeline_plan)
    except DailyEodPipelineSchedulerError as exc:
        raise DailyEodPipelineCadenceError(
            "pipeline wake plan is invalid"
        ) from exc
    if pipeline_plan.checked_at != checked.isoformat():
        raise DailyEodPipelineCadenceError(
            "pipeline wake plan observation time differs"
        )
    if started > checked:
        raise DailyEodPipelineCadenceError(
            "cadence start cannot follow observation time"
        )
    _validate_evidence_chain(
        prior_wakes,
        target_session=pipeline_plan.target_session,
        cadence_started_at=started,
        checked_at=checked,
        policy=selected_policy,
    )
    expires = started + timedelta(seconds=selected_policy.maximum_window_seconds)
    used = len(prior_wakes)
    if used > selected_policy.maximum_transition_wakes:
        raise DailyEodPipelineCadenceError(
            "cadence wake evidence exceeds the candidate budget"
        )
    last = None if not prior_wakes else prior_wakes[-1]

    if last is not None and last.outcome is CadenceWakeOutcome.UNKNOWN:
        return _build_plan(
            checked=checked,
            started=started,
            expires=expires,
            pipeline_plan=pipeline_plan,
            prior_wakes=prior_wakes,
            policy=selected_policy,
            status=CadenceStatus.STOPPED,
            action=CadenceAction.STOP_AFTER_UNKNOWN_OUTCOME,
            next_wake_at=None,
            reasons=("prior_wake_outcome_unknown", "automatic_replay_prohibited"),
            review_enabled_candidate=review_enabled_candidate,
        )
    if last is not None and last.outcome is CadenceWakeOutcome.FAILED:
        return _build_plan(
            checked=checked,
            started=started,
            expires=expires,
            pipeline_plan=pipeline_plan,
            prior_wakes=prior_wakes,
            policy=selected_policy,
            status=CadenceStatus.STOPPED,
            action=CadenceAction.STOP_AFTER_KNOWN_FAILURE,
            next_wake_at=None,
            reasons=("prior_wake_failed", "automatic_retry_prohibited"),
            review_enabled_candidate=review_enabled_candidate,
        )
    if pipeline_plan.status is PipelineWakeStatus.REVIEW_REQUIRED:
        return _stop_for_pipeline_state(
            checked=checked,
            started=started,
            expires=expires,
            pipeline_plan=pipeline_plan,
            prior_wakes=prior_wakes,
            policy=selected_policy,
            action=CadenceAction.STOP_FOR_MANUAL_REVIEW,
            reason="manual_pipeline_review_required",
            review_enabled_candidate=review_enabled_candidate,
        )
    if pipeline_plan.status is PipelineWakeStatus.BLOCKED:
        return _stop_for_pipeline_state(
            checked=checked,
            started=started,
            expires=expires,
            pipeline_plan=pipeline_plan,
            prior_wakes=prior_wakes,
            policy=selected_policy,
            action=CadenceAction.STOP_FOR_BLOCKED_STATE,
            reason="pipeline_state_blocked",
            review_enabled_candidate=review_enabled_candidate,
        )
    if used >= selected_policy.maximum_transition_wakes or checked >= expires:
        return _build_plan(
            checked=checked,
            started=started,
            expires=expires,
            pipeline_plan=pipeline_plan,
            prior_wakes=prior_wakes,
            policy=selected_policy,
            status=CadenceStatus.STOPPED,
            action=CadenceAction.STOP_AT_BUDGET,
            next_wake_at=None,
            reasons=("bounded_cadence_budget_exhausted",),
            review_enabled_candidate=review_enabled_candidate,
        )

    interval_at = _interval_boundary(last, selected_policy)
    if pipeline_plan.status is PipelineWakeStatus.WAITING:
        pipeline_at = _parse_utc_required(pipeline_plan.next_check_at)
        next_wake = max(pipeline_at, interval_at or pipeline_at)
        if next_wake >= expires:
            return _build_plan(
                checked=checked,
                started=started,
                expires=expires,
                pipeline_plan=pipeline_plan,
                prior_wakes=prior_wakes,
                policy=selected_policy,
                status=CadenceStatus.STOPPED,
                action=CadenceAction.STOP_AT_BUDGET,
                next_wake_at=None,
                reasons=("next_check_exceeds_cadence_window",),
                review_enabled_candidate=review_enabled_candidate,
            )
        return _build_plan(
            checked=checked,
            started=started,
            expires=expires,
            pipeline_plan=pipeline_plan,
            prior_wakes=prior_wakes,
            policy=selected_policy,
            status=CadenceStatus.WAITING,
            action=CadenceAction.WAIT_FOR_PIPELINE_CHECK,
            next_wake_at=next_wake,
            reasons=("pipeline_waiting", "distinct_wake_required"),
            review_enabled_candidate=review_enabled_candidate,
        )

    if interval_at is not None and checked < interval_at:
        if interval_at >= expires:
            return _build_plan(
                checked=checked,
                started=started,
                expires=expires,
                pipeline_plan=pipeline_plan,
                prior_wakes=prior_wakes,
                policy=selected_policy,
                status=CadenceStatus.STOPPED,
                action=CadenceAction.STOP_AT_BUDGET,
                next_wake_at=None,
                reasons=("minimum_interval_exceeds_cadence_window",),
                review_enabled_candidate=review_enabled_candidate,
            )
        return _build_plan(
            checked=checked,
            started=started,
            expires=expires,
            pipeline_plan=pipeline_plan,
            prior_wakes=prior_wakes,
            policy=selected_policy,
            status=CadenceStatus.WAITING,
            action=CadenceAction.WAIT_FOR_MINIMUM_INTERVAL,
            next_wake_at=interval_at,
            reasons=("minimum_distinct_wake_interval",),
            review_enabled_candidate=review_enabled_candidate,
        )

    pipeline_can_invoke = pipeline_plan.next_action in {
        PipelineWakeAction.INVOKE_ONE_DATA_TRANSITION,
        PipelineWakeAction.INVOKE_ONE_OFFLINE_TRANSITION,
    }
    enabled = review_enabled_candidate and pipeline_can_invoke
    return _build_plan(
        checked=checked,
        started=started,
        expires=expires,
        pipeline_plan=pipeline_plan,
        prior_wakes=prior_wakes,
        policy=selected_policy,
        status=CadenceStatus.WAKE_READY if enabled else CadenceStatus.REVIEW_READY,
        action=(
            CadenceAction.INVOKE_ONE_TRANSITION
            if enabled
            else CadenceAction.REVIEW_ONE_TRANSITION
        ),
        next_wake_at=checked,
        reasons=(
            ("bounded_distinct_wake_candidate_ready",)
            if enabled
            else ("bounded_distinct_wake_review_ready",)
        ),
        review_enabled_candidate=review_enabled_candidate,
    )


def verify_bounded_pipeline_cadence_plan(
    plan: DailyEodBoundedCadencePlan,
) -> None:
    if not isinstance(plan, DailyEodBoundedCadencePlan):
        raise DailyEodPipelineCadenceError("bounded cadence plan is invalid")
    logical = asdict(plan)
    logical.pop("logical_content_fingerprint")
    if (
        plan.contract_version != CONTRACT_VERSION
        or plan.logical_content_fingerprint
        != _fingerprint(_jsonable(logical))
        or plan.minimum_interval_seconds < MINIMUM_INTERVAL_FLOOR_SECONDS
        or plan.maximum_window_seconds > MAXIMUM_WINDOW_SECONDS
        or plan.maximum_transition_wakes > MAXIMUM_WAKE_LIMIT
        or plan.maximum_window_seconds < plan.minimum_interval_seconds
        or plan.maximum_transition_wakes < 1
        or plan.transition_wakes_used < 0
        or plan.transition_wakes_remaining < 0
        or plan.transition_wakes_remaining
        != plan.maximum_transition_wakes - plan.transition_wakes_used
        or plan.policy_fingerprint
        != _fingerprint(
            {
                "minimum_interval_seconds": plan.minimum_interval_seconds,
                "maximum_window_seconds": plan.maximum_window_seconds,
                "maximum_transition_wakes": plan.maximum_transition_wakes,
            }
        )
        or plan.transition_invocation_limit != 1
        or plan.transition_invocation_count != 0
        or plan.automatic_retry_enabled
        or plan.automatic_recovery_enabled
        or plan.publication_authorized
        or plan.deployment_authorized
        or plan.credential_access_count != 0
        or plan.external_request_count != 0
        or plan.filesystem_write_count != 0
        or plan.production_write_count != 0
        or plan.scheduler_installation_performed
    ):
        raise DailyEodPipelineCadenceError(
            "bounded cadence plan content or authority differs"
        )
    _verify_cadence_plan_semantics(plan)


def _verify_cadence_plan_semantics(plan: DailyEodBoundedCadencePlan) -> None:
    if (
        not isinstance(plan.status, CadenceStatus)
        or not isinstance(plan.next_action, CadenceAction)
    ):
        raise DailyEodPipelineCadenceError(
            "bounded cadence plan enum fields are invalid"
        )
    try:
        date.fromisoformat(plan.target_session)
        pipeline_status = PipelineWakeStatus(plan.pipeline_status)
        PipelineWakePhase(plan.pipeline_phase)
        pipeline_action = PipelineWakeAction(plan.pipeline_action)
    except ValueError as exc:
        raise DailyEodPipelineCadenceError(
            "bounded cadence pipeline identity is malformed"
        ) from exc
    expected = {
        CadenceStatus.WAITING: {
            CadenceAction.WAIT_FOR_PIPELINE_CHECK,
            CadenceAction.WAIT_FOR_MINIMUM_INTERVAL,
        },
        CadenceStatus.REVIEW_READY: {CadenceAction.REVIEW_ONE_TRANSITION},
        CadenceStatus.WAKE_READY: {CadenceAction.INVOKE_ONE_TRANSITION},
        CadenceStatus.STOPPED: {
            CadenceAction.STOP_FOR_MANUAL_REVIEW,
            CadenceAction.STOP_FOR_BLOCKED_STATE,
            CadenceAction.STOP_AFTER_KNOWN_FAILURE,
            CadenceAction.STOP_AFTER_UNKNOWN_OUTCOME,
            CadenceAction.STOP_AT_BUDGET,
        },
    }
    if plan.next_action not in expected[plan.status]:
        raise DailyEodPipelineCadenceError(
            "bounded cadence status and action conflict"
        )
    checked = _parse_utc(plan.checked_at)
    next_wake = None if plan.next_wake_at is None else _parse_utc(plan.next_wake_at)
    pipeline_invokes = pipeline_action in {
        PipelineWakeAction.INVOKE_ONE_DATA_TRANSITION,
        PipelineWakeAction.INVOKE_ONE_OFFLINE_TRANSITION,
    }
    if (
        (plan.status is CadenceStatus.STOPPED) != (plan.next_wake_at is None)
        or (next_wake is not None and next_wake < checked)
        or (
            plan.status is CadenceStatus.WAKE_READY
            and not (
                plan.cadence_candidate_enabled
                and plan.pipeline_candidate_enabled
                and pipeline_status is PipelineWakeStatus.READY_FOR_WAKE
                and pipeline_invokes
            )
        )
        or (
            plan.status is CadenceStatus.REVIEW_READY
            and plan.cadence_candidate_enabled
            and plan.pipeline_candidate_enabled
            and pipeline_invokes
        )
        or not _is_fingerprint(plan.pipeline_plan_fingerprint)
        or not _is_fingerprint(plan.evidence_chain_fingerprint)
        or _parse_utc(plan.cadence_expires_at)
        - _parse_utc(plan.cadence_started_at)
        != timedelta(seconds=plan.maximum_window_seconds)
    ):
        raise DailyEodPipelineCadenceError(
            "bounded cadence timing or enablement conflicts"
        )


def _stop_for_pipeline_state(
    *,
    checked: datetime,
    started: datetime,
    expires: datetime,
    pipeline_plan: DailyEodPipelineWakePlan,
    prior_wakes: tuple[CadenceWakeEvidence, ...],
    policy: BoundedCadencePolicy,
    action: CadenceAction,
    reason: str,
    review_enabled_candidate: bool,
) -> DailyEodBoundedCadencePlan:
    return _build_plan(
        checked=checked,
        started=started,
        expires=expires,
        pipeline_plan=pipeline_plan,
        prior_wakes=prior_wakes,
        policy=policy,
        status=CadenceStatus.STOPPED,
        action=action,
        next_wake_at=None,
        reasons=(reason,),
        review_enabled_candidate=review_enabled_candidate,
    )


def _build_plan(
    *,
    checked: datetime,
    started: datetime,
    expires: datetime,
    pipeline_plan: DailyEodPipelineWakePlan,
    prior_wakes: tuple[CadenceWakeEvidence, ...],
    policy: BoundedCadencePolicy,
    status: CadenceStatus,
    action: CadenceAction,
    next_wake_at: datetime | None,
    reasons: tuple[str, ...],
    review_enabled_candidate: bool,
) -> DailyEodBoundedCadencePlan:
    used = len(prior_wakes)
    logical = {
        "contract_version": CONTRACT_VERSION,
        "checked_at": checked.isoformat(),
        "cadence_started_at": started.isoformat(),
        "cadence_expires_at": expires.isoformat(),
        "target_session": pipeline_plan.target_session,
        "status": status.value,
        "next_action": action.value,
        "next_wake_at": None if next_wake_at is None else next_wake_at.isoformat(),
        "reason_codes": list(reasons),
        "pipeline_status": pipeline_plan.status.value,
        "pipeline_phase": pipeline_plan.phase.value,
        "pipeline_action": pipeline_plan.next_action.value,
        "pipeline_plan_fingerprint": pipeline_plan.logical_content_fingerprint,
        "evidence_chain_fingerprint": _fingerprint(
            [item.logical_content_fingerprint for item in prior_wakes]
        ),
        "policy_fingerprint": policy.logical_content_fingerprint,
        "minimum_interval_seconds": policy.minimum_interval_seconds,
        "maximum_window_seconds": policy.maximum_window_seconds,
        "maximum_transition_wakes": policy.maximum_transition_wakes,
        "transition_wakes_used": used,
        "transition_wakes_remaining": policy.maximum_transition_wakes - used,
        "cadence_candidate_enabled": review_enabled_candidate,
        "pipeline_candidate_enabled": pipeline_plan.scheduler_candidate_enabled,
        "transition_invocation_limit": 1,
        "transition_invocation_count": 0,
        "automatic_retry_enabled": False,
        "automatic_recovery_enabled": False,
        "publication_authorized": False,
        "deployment_authorized": False,
        "credential_access_count": 0,
        "external_request_count": 0,
        "filesystem_write_count": 0,
        "production_write_count": 0,
        "scheduler_installation_performed": False,
    }
    result = DailyEodBoundedCadencePlan(
        contract_version=CONTRACT_VERSION,
        checked_at=checked.isoformat(),
        cadence_started_at=started.isoformat(),
        cadence_expires_at=expires.isoformat(),
        target_session=pipeline_plan.target_session,
        status=status,
        next_action=action,
        next_wake_at=(
            None if next_wake_at is None else next_wake_at.isoformat()
        ),
        reason_codes=reasons,
        pipeline_status=pipeline_plan.status.value,
        pipeline_phase=pipeline_plan.phase.value,
        pipeline_action=pipeline_plan.next_action.value,
        pipeline_plan_fingerprint=pipeline_plan.logical_content_fingerprint,
        evidence_chain_fingerprint=logical["evidence_chain_fingerprint"],
        policy_fingerprint=policy.logical_content_fingerprint,
        minimum_interval_seconds=policy.minimum_interval_seconds,
        maximum_window_seconds=policy.maximum_window_seconds,
        maximum_transition_wakes=policy.maximum_transition_wakes,
        transition_wakes_used=used,
        transition_wakes_remaining=policy.maximum_transition_wakes - used,
        cadence_candidate_enabled=review_enabled_candidate,
        pipeline_candidate_enabled=pipeline_plan.scheduler_candidate_enabled,
        transition_invocation_limit=1,
        transition_invocation_count=0,
        automatic_retry_enabled=False,
        automatic_recovery_enabled=False,
        publication_authorized=False,
        deployment_authorized=False,
        credential_access_count=0,
        external_request_count=0,
        filesystem_write_count=0,
        production_write_count=0,
        scheduler_installation_performed=False,
        logical_content_fingerprint=_fingerprint(logical),
    )
    verify_bounded_pipeline_cadence_plan(result)
    return result


def _validate_evidence_chain(
    evidence: tuple[CadenceWakeEvidence, ...],
    *,
    target_session: str,
    cadence_started_at: datetime,
    checked_at: datetime,
    policy: BoundedCadencePolicy,
) -> None:
    previous_completed: datetime | None = None
    for index, item in enumerate(evidence, start=1):
        verify_cadence_wake_evidence(item)
        item_started = _parse_utc(item.started_at)
        item_completed = (
            None if item.completed_at is None else _parse_utc(item.completed_at)
        )
        if (
            item.sequence != index
            or item.target_session != target_session
            or item_started < cadence_started_at
            or item_started > checked_at
            or (item_completed is not None and item_completed > checked_at)
            or (
                previous_completed is not None
                and item_started
                < previous_completed
                + timedelta(seconds=policy.minimum_interval_seconds)
            )
        ):
            raise DailyEodPipelineCadenceError(
                "cadence wake evidence chain is inconsistent"
            )
        previous_completed = item_completed
        if (
            item.outcome
            in {CadenceWakeOutcome.FAILED, CadenceWakeOutcome.UNKNOWN}
            and index != len(evidence)
        ):
            raise DailyEodPipelineCadenceError(
                "failed or unknown wake must terminate the evidence chain"
            )


def _interval_boundary(
    evidence: CadenceWakeEvidence | None,
    policy: BoundedCadencePolicy,
) -> datetime | None:
    if evidence is None or evidence.completed_at is None:
        return None
    return _parse_utc(evidence.completed_at) + timedelta(
        seconds=policy.minimum_interval_seconds
    )


def _validate_policy(policy: BoundedCadencePolicy) -> None:
    if (
        policy.minimum_interval_seconds < MINIMUM_INTERVAL_FLOOR_SECONDS
        or policy.maximum_window_seconds < policy.minimum_interval_seconds
        or policy.maximum_window_seconds > MAXIMUM_WINDOW_SECONDS
        or policy.maximum_transition_wakes < 1
        or policy.maximum_transition_wakes > MAXIMUM_WAKE_LIMIT
    ):
        raise DailyEodPipelineCadenceError(
            "bounded cadence policy exceeds candidate limits"
        )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodPipelineCadenceError("cadence timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise DailyEodPipelineCadenceError(
            "cadence timestamp is malformed"
        ) from exc
    return _aware_utc(parsed)


def _parse_utc_required(value: str | None) -> datetime:
    if value is None:
        raise DailyEodPipelineCadenceError(
            "waiting pipeline plan lacks its next check"
        )
    return _parse_utc(value)


def _is_fingerprint(value: str | None) -> bool:
    return bool(
        value
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


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
