"""Project and custody bounded-cadence evidence in the existing run journal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Mapping

from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorError,
    DailyEodCoordinatorResult,
    verify_daily_eod_coordinator_result,
)
from tip_api.services.daily_eod_executor import DailyEodExecutionResult
from tip_api.services.daily_eod_pipeline_cadence import (
    MAXIMUM_WAKE_LIMIT,
    MAXIMUM_WINDOW_SECONDS,
    MINIMUM_INTERVAL_FLOOR_SECONDS,
    CadenceAction,
    CadenceStatus,
    CadenceWakeEvidence,
    CadenceWakeOutcome,
    DailyEodBoundedCadencePlan,
    DailyEodPipelineCadenceError,
    record_cadence_wake_evidence,
    verify_bounded_pipeline_cadence_plan,
    verify_cadence_wake_evidence,
)
from tip_api.services.daily_eod_pipeline_scheduler import (
    DailyEodPipelineSchedulerError,
    DailyEodPipelineWakePlan,
    PipelineWakeAction,
    PipelineWakeStatus,
    verify_daily_eod_pipeline_wake_plan,
)
from tip_api.services.daily_eod_run_journal import (
    CADENCE_WAKE_RECORDED_EVENT,
    CADENCE_WAKE_RESERVED_EVENT,
    DailyEodRunEvent,
    DailyEodRunJournalError,
    locked_daily_eod_run_journal,
    new_attempt_id,
    verify_daily_eod_run_event,
)


CONTRACT_VERSION = "daily-eod-cadence-evidence-custody/1.1"
READABLE_CONTRACTS = frozenset(
    {"daily-eod-cadence-evidence-custody/1.0", CONTRACT_VERSION}
)
INVOKE_ACTIONS = {
    PipelineWakeAction.INVOKE_ONE_DATA_TRANSITION,
    PipelineWakeAction.INVOKE_ONE_OFFLINE_TRANSITION,
}
DATA_TRANSITION_ACTIONS = {
    "fetch_identity",
    "fetch_eod",
    "apply_identity",
    "apply_eod",
    "recover_acquisition_attempt",
    "recover_canonical_apply",
}


class DailyEodCadenceEvidenceError(RuntimeError):
    """Raised when wake evidence cannot be projected or retained exactly."""


@dataclass(frozen=True, slots=True)
class CadenceWakeJournalState:
    completed: tuple[CadenceWakeEvidence, ...]
    pending_plan: DailyEodBoundedCadencePlan | None
    pending_evidence: CadenceWakeEvidence | None
    pending_event: DailyEodRunEvent | None


def cadence_evidence_from_coordinator_result(
    *,
    sequence: int,
    started_at: datetime,
    completed_at: datetime,
    cadence_plan: DailyEodBoundedCadencePlan,
    pipeline_plan: DailyEodPipelineWakePlan,
    result: DailyEodCoordinatorResult,
) -> CadenceWakeEvidence:
    """Map one formal coordinator return without inferring hidden success."""

    _validate_invocation_plans(
        cadence_plan, pipeline_plan, started_at, sequence=sequence
    )
    try:
        verify_daily_eod_coordinator_result(result)
    except DailyEodCoordinatorError as exc:
        raise DailyEodCadenceEvidenceError(
            "coordinator result content is invalid"
        ) from exc
    if (
        not isinstance(result.status, CoordinatorStatus)
        or result.target_session != pipeline_plan.target_session
        or not result.reason_codes
        or not _is_fingerprint(result.automation_plan_fingerprint)
        or result.publication_authorized
        or result.deployment_authorized
        or result.scheduler_enabled
        or result.external_request_count < 0
        or result.production_write_count < 0
    ):
        raise DailyEodCadenceEvidenceError(
            "coordinator result exceeds cadence evidence boundary"
        )
    if result.status is CoordinatorStatus.TRANSITION_EXECUTED:
        expected_offline_action = (
            pipeline_plan.pipeline_next_action
            if pipeline_plan.next_action
            is PipelineWakeAction.INVOKE_ONE_OFFLINE_TRANSITION
            else None
        )
        if (
            not _is_fingerprint(result.transition_fingerprint)
            or (
                expected_offline_action is not None
                and result.next_action != expected_offline_action
            )
            or (
                expected_offline_action is None
                and result.next_action not in DATA_TRANSITION_ACTIONS
            )
        ):
            raise DailyEodCadenceEvidenceError(
                "executed transition lacks formal transition evidence"
            )
        outcome = CadenceWakeOutcome.ADVANCED
    elif result.status is CoordinatorStatus.WAITING:
        if result.next_action != "wait":
            raise DailyEodCadenceEvidenceError(
                "waiting coordinator result has an invalid next action"
            )
        outcome = CadenceWakeOutcome.NO_CHANGE
    else:
        outcome = CadenceWakeOutcome.FAILED
    return record_cadence_wake_evidence(
        sequence=sequence,
        target_session=pipeline_plan.target_session,
        cadence_started_at=datetime.fromisoformat(cadence_plan.cadence_started_at),
        started_at=started_at,
        completed_at=completed_at,
        cadence_plan_fingerprint=cadence_plan.logical_content_fingerprint,
        pipeline_plan_fingerprint=pipeline_plan.logical_content_fingerprint,
        pipeline_action=pipeline_plan.next_action.value,
        outcome=outcome,
        next_eligible_at=(
            None
            if result.next_check_at is None
            else datetime.fromisoformat(result.next_check_at)
        ),
        result_fingerprint=result.logical_content_fingerprint,
    )


def cadence_evidence_from_offline_result(
    *,
    sequence: int,
    started_at: datetime,
    completed_at: datetime,
    cadence_plan: DailyEodBoundedCadencePlan,
    pipeline_plan: DailyEodPipelineWakePlan,
    result: DailyEodExecutionResult,
) -> CadenceWakeEvidence:
    """Map one formally journaled offline executor result."""

    _validate_invocation_plans(
        cadence_plan,
        pipeline_plan,
        started_at,
        sequence=sequence,
        expected_action=PipelineWakeAction.INVOKE_ONE_OFFLINE_TRANSITION,
    )
    if not isinstance(result, DailyEodExecutionResult):
        raise DailyEodCadenceEvidenceError("offline result contract is invalid")
    try:
        verify_daily_eod_run_event(result.event)
    except DailyEodRunJournalError as exc:
        raise DailyEodCadenceEvidenceError(
            "offline result event is invalid"
        ) from exc
    if (
        result.action.value != pipeline_plan.pipeline_next_action
        or result.pre_plan.target_session != pipeline_plan.target_session
        or result.pre_plan.logical_content_fingerprint
        != pipeline_plan.automation_plan_fingerprint
        or result.event.target_session != pipeline_plan.target_session
        or result.event.attempt_id != result.attempt_id
        or result.outcome not in {"succeeded", "failed"}
        or (
            result.outcome == "succeeded"
            and (
                result.event.event_type != "action_succeeded"
                or result.post_plan is None
                or result.stage_evidence is None
                or result.post_plan.logical_content_fingerprint
                == result.pre_plan.logical_content_fingerprint
            )
        )
        or (
            result.outcome == "failed"
            and result.event.event_type != "action_failed"
        )
    ):
        raise DailyEodCadenceEvidenceError(
            "offline result differs from the pipeline invocation"
        )
    return record_cadence_wake_evidence(
        sequence=sequence,
        target_session=pipeline_plan.target_session,
        cadence_started_at=datetime.fromisoformat(cadence_plan.cadence_started_at),
        started_at=started_at,
        completed_at=completed_at,
        cadence_plan_fingerprint=cadence_plan.logical_content_fingerprint,
        pipeline_plan_fingerprint=pipeline_plan.logical_content_fingerprint,
        pipeline_action=pipeline_plan.next_action.value,
        outcome=(
            CadenceWakeOutcome.ADVANCED
            if result.outcome == "succeeded"
            else CadenceWakeOutcome.FAILED
        ),
        next_eligible_at=None,
        result_fingerprint=result.event.event_fingerprint,
    )


def unknown_cadence_wake_evidence(
    *,
    sequence: int,
    started_at: datetime,
    cadence_plan: DailyEodBoundedCadencePlan,
    pipeline_plan: DailyEodPipelineWakePlan,
) -> CadenceWakeEvidence:
    """Represent process ambiguity in memory; it cannot be persisted as resolved."""

    _validate_invocation_plans(
        cadence_plan, pipeline_plan, started_at, sequence=sequence
    )
    return record_cadence_wake_evidence(
        sequence=sequence,
        target_session=pipeline_plan.target_session,
        cadence_started_at=datetime.fromisoformat(cadence_plan.cadence_started_at),
        started_at=started_at,
        completed_at=None,
        cadence_plan_fingerprint=cadence_plan.logical_content_fingerprint,
        pipeline_plan_fingerprint=pipeline_plan.logical_content_fingerprint,
        pipeline_action=pipeline_plan.next_action.value,
        outcome=CadenceWakeOutcome.UNKNOWN,
        next_eligible_at=None,
        result_fingerprint=None,
    )


def reserve_cadence_wake(
    *,
    run_root: Path,
    target_session: date,
    cadence_plan: DailyEodBoundedCadencePlan,
    pipeline_plan: DailyEodPipelineWakePlan,
    started_at: datetime,
) -> tuple[DailyEodRunEvent, CadenceWakeEvidence]:
    """Durably reserve one invocation before its side effects may begin."""

    try:
        with locked_daily_eod_run_journal(
            run_root=run_root,
            target_session=target_session,
        ) as journal:
            events = journal.read_events()
            state = cadence_wake_state_from_events(
                events,
                target_session=target_session,
            )
            if state.pending_event is not None:
                raise DailyEodCadenceEvidenceError(
                    "a cadence wake already has an unknown outcome"
                )
            sequence = len(state.completed) + 1
            evidence = unknown_cadence_wake_evidence(
                sequence=sequence,
                started_at=started_at,
                cadence_plan=cadence_plan,
                pipeline_plan=pipeline_plan,
            )
            _validate_retention_boundary(state.completed, evidence)
            _validate_retained_cadence_plan(
                cadence_plan,
                evidence=evidence,
                prior_count=len(state.completed),
            )
            event_sequence = len(events) + 1
            event = journal.append(
                event_type=CADENCE_WAKE_RESERVED_EVENT,
                attempt_id=new_attempt_id(
                    target_session=target_session,
                    plan_fingerprint=evidence.logical_content_fingerprint,
                    sequence=event_sequence,
                ),
                details={
                    "custody_contract": CONTRACT_VERSION,
                    "cadence_plan": cadence_plan.as_dict(),
                    "cadence_evidence": evidence.as_dict(),
                },
                observed_at=started_at,
            )
            reread = cadence_wake_state_from_events(
                journal.read_events(),
                target_session=target_session,
            )
            if (
                reread.completed != state.completed
                or reread.pending_event != event
                or reread.pending_evidence != evidence
            ):
                raise DailyEodCadenceEvidenceError(
                    "cadence wake reservation did not formally reread"
                )
            return event, evidence
    except DailyEodRunJournalError as exc:
        raise DailyEodCadenceEvidenceError(
            "daily run journal rejected cadence reservation"
        ) from exc


def resolve_cadence_wake(
    *,
    run_root: Path,
    target_session: date,
    cadence_plan: DailyEodBoundedCadencePlan,
    evidence: CadenceWakeEvidence,
    reservation_event_fingerprint: str,
) -> DailyEodRunEvent:
    """Close one exact reservation with a formally known result."""

    try:
        verify_cadence_wake_evidence(evidence)
    except DailyEodPipelineCadenceError as exc:
        raise DailyEodCadenceEvidenceError(
            "cadence evidence content is invalid"
        ) from exc
    if (
        evidence.target_session != target_session.isoformat()
        or evidence.outcome is CadenceWakeOutcome.UNKNOWN
        or evidence.completed_at is None
        or cadence_plan.logical_content_fingerprint
        != evidence.cadence_plan_fingerprint
        or not _is_fingerprint(reservation_event_fingerprint)
    ):
        raise DailyEodCadenceEvidenceError(
            "only a known result may resolve an exact cadence reservation"
        )
    try:
        with locked_daily_eod_run_journal(
            run_root=run_root,
            target_session=target_session,
        ) as journal:
            state = cadence_wake_state_from_events(
                journal.read_events(),
                target_session=target_session,
            )
            pending = state.pending_event
            pending_evidence = state.pending_evidence
            if (
                pending is None
                or pending_evidence is None
                or pending.event_fingerprint != reservation_event_fingerprint
                or evidence.sequence != pending_evidence.sequence
                or evidence.started_at != pending_evidence.started_at
                or evidence.cadence_started_at != pending_evidence.cadence_started_at
                or evidence.cadence_plan_fingerprint
                != pending_evidence.cadence_plan_fingerprint
                or evidence.pipeline_plan_fingerprint
                != pending_evidence.pipeline_plan_fingerprint
                or evidence.pipeline_action != pending_evidence.pipeline_action
            ):
                raise DailyEodCadenceEvidenceError(
                    "cadence result differs from its unresolved reservation"
                )
            event = journal.append(
                event_type=CADENCE_WAKE_RECORDED_EVENT,
                attempt_id=pending.attempt_id,
                details={
                    "custody_contract": CONTRACT_VERSION,
                    "cadence_plan": cadence_plan.as_dict(),
                    "cadence_evidence": evidence.as_dict(),
                },
                observed_at=datetime.fromisoformat(evidence.completed_at),
            )
            reread = cadence_wake_state_from_events(
                journal.read_events(),
                target_session=target_session,
            )
            if (
                reread.pending_event is not None
                or len(reread.completed) != evidence.sequence
                or reread.completed[-1] != evidence
            ):
                raise DailyEodCadenceEvidenceError(
                    "resolved cadence evidence did not formally reread"
                )
            return event
    except DailyEodRunJournalError as exc:
        raise DailyEodCadenceEvidenceError(
            "daily run journal rejected cadence resolution"
        ) from exc


def append_cadence_wake_evidence(
    *,
    run_root: Path,
    target_session: date,
    cadence_plan: DailyEodBoundedCadencePlan,
    evidence: CadenceWakeEvidence,
) -> DailyEodRunEvent:
    """Append one known wake result to the existing owner-only hash chain."""

    try:
        verify_cadence_wake_evidence(evidence)
    except DailyEodPipelineCadenceError as exc:
        raise DailyEodCadenceEvidenceError(
            "cadence evidence content is invalid"
        ) from exc
    if (
        evidence.target_session != target_session.isoformat()
        or evidence.outcome is CadenceWakeOutcome.UNKNOWN
        or evidence.completed_at is None
        or cadence_plan.logical_content_fingerprint
        != evidence.cadence_plan_fingerprint
    ):
        raise DailyEodCadenceEvidenceError(
            "only known same-session cadence evidence may be persisted"
        )
    try:
        with locked_daily_eod_run_journal(
            run_root=run_root,
            target_session=target_session,
        ) as journal:
            events = journal.read_events()
            state = cadence_wake_state_from_events(
                events,
                target_session=target_session,
            )
            if state.pending_event is not None:
                raise DailyEodCadenceEvidenceError(
                    "cadence evidence cannot bypass an unresolved reservation"
                )
            retained = state.completed
            if evidence.sequence != len(retained) + 1 or any(
                item.result_fingerprint == evidence.result_fingerprint
                for item in retained
            ):
                raise DailyEodCadenceEvidenceError(
                    "cadence evidence sequence or result is duplicated"
                )
            _validate_retention_boundary(retained, evidence)
            _validate_retained_cadence_plan(
                cadence_plan,
                evidence=evidence,
                prior_count=len(retained),
            )
            event_sequence = len(events) + 1
            event = journal.append(
                event_type=CADENCE_WAKE_RECORDED_EVENT,
                attempt_id=new_attempt_id(
                    target_session=target_session,
                    plan_fingerprint=evidence.logical_content_fingerprint,
                    sequence=event_sequence,
                ),
                details={
                    "custody_contract": CONTRACT_VERSION,
                    "cadence_plan": cadence_plan.as_dict(),
                    "cadence_evidence": evidence.as_dict(),
                },
                observed_at=datetime.fromisoformat(evidence.completed_at),
            )
            reread = cadence_evidence_from_events(
                journal.read_events(),
                target_session=target_session,
            )
            if len(reread) != evidence.sequence or reread[-1] != evidence:
                raise DailyEodCadenceEvidenceError(
                    "cadence evidence did not formally reread"
                )
            return event
    except DailyEodRunJournalError as exc:
        raise DailyEodCadenceEvidenceError(
            "daily run journal rejected cadence evidence"
        ) from exc


def cadence_evidence_from_events(
    events: tuple[DailyEodRunEvent, ...],
    *,
    target_session: date,
) -> tuple[CadenceWakeEvidence, ...]:
    """Project only formally retained cadence records from one session journal."""

    return cadence_wake_state_from_events(
        events,
        target_session=target_session,
    ).completed


def cadence_wake_state_from_events(
    events: tuple[DailyEodRunEvent, ...],
    *,
    target_session: date,
) -> CadenceWakeJournalState:
    """Project completed wakes plus at most one unresolved reservation."""

    projected: list[CadenceWakeEvidence] = []
    pending_plan: DailyEodBoundedCadencePlan | None = None
    pending_evidence: CadenceWakeEvidence | None = None
    pending_event: DailyEodRunEvent | None = None
    for event in events:
        if event.event_type not in {
            CADENCE_WAKE_RESERVED_EVENT,
            CADENCE_WAKE_RECORDED_EVENT,
        }:
            continue
        try:
            verify_daily_eod_run_event(event)
            cadence_plan, evidence = _evidence_from_details(event.details)
        except (DailyEodRunJournalError, DailyEodPipelineCadenceError) as exc:
            raise DailyEodCadenceEvidenceError(
                "retained cadence evidence is invalid"
            ) from exc
        is_reservation = event.event_type == CADENCE_WAKE_RESERVED_EVENT
        expected_attempt = (
            new_attempt_id(
                target_session=target_session,
                plan_fingerprint=evidence.logical_content_fingerprint,
                sequence=event.sequence,
                contract_version=event.contract_version,
            )
            if is_reservation or pending_event is None
            else pending_event.attempt_id
        )
        expected_observed_at = (
            evidence.started_at if is_reservation else evidence.completed_at
        )
        if (
            evidence.sequence != len(projected) + 1
            or evidence.target_session != target_session.isoformat()
            or expected_observed_at != event.observed_at
        ):
            raise DailyEodCadenceEvidenceError(
                "retained cadence evidence timing conflicts"
            )
        if (
            (is_reservation and evidence.outcome is not CadenceWakeOutcome.UNKNOWN)
            or (not is_reservation and evidence.outcome is CadenceWakeOutcome.UNKNOWN)
            or event.attempt_id != expected_attempt
            or cadence_plan.logical_content_fingerprint
            != evidence.cadence_plan_fingerprint
            or cadence_plan.transition_wakes_used != evidence.sequence - 1
            or any(
                item.result_fingerprint == evidence.result_fingerprint
                for item in projected
            )
        ):
            raise DailyEodCadenceEvidenceError(
                "retained cadence evidence identity conflicts"
            )
        _validate_retention_boundary(tuple(projected), evidence)
        _validate_retained_cadence_plan(
            cadence_plan,
            evidence=evidence,
            prior_count=len(projected),
        )
        if is_reservation:
            if pending_event is not None:
                raise DailyEodCadenceEvidenceError(
                    "cadence wake reservations overlap"
                )
            pending_plan = cadence_plan
            pending_evidence = evidence
            pending_event = event
            continue
        if pending_event is not None:
            if (
                pending_plan != cadence_plan
                or pending_evidence is None
                or evidence.started_at != pending_evidence.started_at
                or evidence.cadence_started_at != pending_evidence.cadence_started_at
                or evidence.cadence_plan_fingerprint
                != pending_evidence.cadence_plan_fingerprint
                or evidence.pipeline_plan_fingerprint
                != pending_evidence.pipeline_plan_fingerprint
                or evidence.pipeline_action != pending_evidence.pipeline_action
            ):
                raise DailyEodCadenceEvidenceError(
                    "cadence result does not close its reservation"
                )
            pending_plan = None
            pending_evidence = None
            pending_event = None
        projected.append(evidence)
    return CadenceWakeJournalState(
        completed=tuple(projected),
        pending_plan=pending_plan,
        pending_evidence=pending_evidence,
        pending_event=pending_event,
    )


def _evidence_from_details(
    details: Mapping[str, object],
) -> tuple[DailyEodBoundedCadencePlan, CadenceWakeEvidence]:
    if set(details) != {
        "custody_contract",
        "cadence_plan",
        "cadence_evidence",
    } or details.get("custody_contract") not in READABLE_CONTRACTS:
        raise DailyEodCadenceEvidenceError(
            "cadence custody details are malformed"
        )
    plan_payload = details.get("cadence_plan")
    payload = details.get("cadence_evidence")
    plan_keys = set(DailyEodBoundedCadencePlan.__dataclass_fields__)
    expected_keys = set(CadenceWakeEvidence.__dataclass_fields__)
    if (
        not isinstance(plan_payload, dict)
        or set(plan_payload) != plan_keys
        or not isinstance(payload, dict)
        or set(payload) != expected_keys
    ):
        raise DailyEodCadenceEvidenceError(
            "cadence evidence payload is malformed"
        )
    try:
        cadence_plan = DailyEodBoundedCadencePlan(
            **{
                **plan_payload,
                "status": CadenceStatus(str(plan_payload["status"])),
                "next_action": CadenceAction(str(plan_payload["next_action"])),
                "reason_codes": tuple(plan_payload["reason_codes"]),
            }
        )
        evidence = CadenceWakeEvidence(
            **{
                **payload,
                "outcome": CadenceWakeOutcome(str(payload["outcome"])),
            }
        )
    except (TypeError, ValueError) as exc:
        raise DailyEodCadenceEvidenceError(
            "cadence evidence payload fields are malformed"
    ) from exc
    verify_bounded_pipeline_cadence_plan(cadence_plan)
    verify_cadence_wake_evidence(evidence)
    return cadence_plan, evidence


def _validate_invocation_plans(
    cadence_plan: DailyEodBoundedCadencePlan,
    pipeline_plan: DailyEodPipelineWakePlan,
    started_at: datetime,
    *,
    sequence: int,
    expected_action: PipelineWakeAction | None = None,
) -> None:
    try:
        verify_bounded_pipeline_cadence_plan(cadence_plan)
        verify_daily_eod_pipeline_wake_plan(pipeline_plan)
    except (DailyEodPipelineCadenceError, DailyEodPipelineSchedulerError) as exc:
        raise DailyEodCadenceEvidenceError(
            "pipeline invocation plan is invalid"
        ) from exc
    if (
        cadence_plan.status is not CadenceStatus.WAKE_READY
        or cadence_plan.next_action is not CadenceAction.INVOKE_ONE_TRANSITION
        or cadence_plan.pipeline_plan_fingerprint
        != pipeline_plan.logical_content_fingerprint
        or cadence_plan.target_session != pipeline_plan.target_session
        or cadence_plan.pipeline_action != pipeline_plan.next_action.value
        or not cadence_plan.cadence_candidate_enabled
        or not cadence_plan.pipeline_candidate_enabled
        or pipeline_plan.status is not PipelineWakeStatus.READY_FOR_WAKE
        or pipeline_plan.next_action not in INVOKE_ACTIONS
        or not pipeline_plan.scheduler_candidate_enabled
        or sequence != cadence_plan.transition_wakes_used + 1
        or (expected_action is not None and pipeline_plan.next_action is not expected_action)
        or started_at < datetime.fromisoformat(cadence_plan.checked_at)
        or started_at >= datetime.fromisoformat(cadence_plan.cadence_expires_at)
    ):
        raise DailyEodCadenceEvidenceError(
            "pipeline plan does not authorize an enabled invocation candidate"
        )


def _validate_retained_cadence_plan(
    plan: DailyEodBoundedCadencePlan,
    *,
    evidence: CadenceWakeEvidence,
    prior_count: int,
) -> None:
    try:
        verify_bounded_pipeline_cadence_plan(plan)
    except DailyEodPipelineCadenceError as exc:
        raise DailyEodCadenceEvidenceError(
            "retained cadence plan is invalid"
        ) from exc
    if (
        plan.status is not CadenceStatus.WAKE_READY
        or plan.next_action is not CadenceAction.INVOKE_ONE_TRANSITION
        or plan.target_session != evidence.target_session
        or plan.cadence_started_at != evidence.cadence_started_at
        or plan.logical_content_fingerprint != evidence.cadence_plan_fingerprint
        or plan.pipeline_plan_fingerprint != evidence.pipeline_plan_fingerprint
        or plan.pipeline_action != evidence.pipeline_action
        or plan.transition_wakes_used != prior_count
        or plan.transition_wakes_remaining <= 0
    ):
        raise DailyEodCadenceEvidenceError(
            "retained cadence plan differs from wake evidence"
        )


def _validate_retention_boundary(
    retained: tuple[CadenceWakeEvidence, ...],
    evidence: CadenceWakeEvidence,
) -> None:
    cadence_started = datetime.fromisoformat(evidence.cadence_started_at)
    started = datetime.fromisoformat(evidence.started_at)
    if (
        len(retained) >= MAXIMUM_WAKE_LIMIT
        or started
        >= cadence_started + timedelta(seconds=MAXIMUM_WINDOW_SECONDS)
        or (
            retained
            and (
                retained[-1].outcome
                in {CadenceWakeOutcome.FAILED, CadenceWakeOutcome.UNKNOWN}
                or retained[-1].completed_at is None
                or started
                < datetime.fromisoformat(retained[-1].completed_at)
                + timedelta(seconds=MINIMUM_INTERVAL_FLOOR_SECONDS)
                or retained[-1].cadence_started_at != evidence.cadence_started_at
            )
        )
    ):
        raise DailyEodCadenceEvidenceError(
            "cadence evidence exceeds retained timing or terminal boundary"
        )


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
