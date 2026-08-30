"""Default-off, one-invocation runtime bridge for one bounded pipeline wake."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Callable

from tip_api.services.daily_eod_cadence_evidence import (
    DailyEodCadenceEvidenceError,
    cadence_evidence_from_coordinator_result,
    cadence_evidence_from_offline_result,
    reserve_cadence_wake,
    resolve_cadence_wake,
)
from tip_api.services.daily_eod_coordinator import DailyEodCoordinatorResult
from tip_api.services.daily_eod_executor import DailyEodExecutionResult
from tip_api.services.daily_eod_pipeline_cadence import (
    CadenceAction,
    CadenceStatus,
    CadenceWakeOutcome,
    DailyEodBoundedCadencePlan,
    DailyEodPipelineCadenceError,
    verify_bounded_pipeline_cadence_plan,
)
from tip_api.services.daily_eod_pipeline_scheduler import (
    DailyEodPipelineSchedulerError,
    DailyEodPipelineWakePlan,
    PipelineWakeAction,
    verify_daily_eod_pipeline_wake_plan,
)


CONTRACT_VERSION = "daily-eod-pipeline-runtime/1.0"


class DailyEodPipelineRuntimeError(RuntimeError):
    """Raised when one pipeline wake cannot remain exact and fail closed."""


class PipelineRuntimeStatus(StrEnum):
    WAITING = "waiting"
    REVIEW_READY = "review_ready"
    STOPPED = "stopped"
    TRANSITION_RECORDED = "transition_recorded"


@dataclass(frozen=True, slots=True)
class DailyEodPipelineRuntimeResult:
    contract_version: str
    status: PipelineRuntimeStatus
    target_session: str
    pipeline_action: str
    cadence_plan_fingerprint: str
    pipeline_plan_fingerprint: str
    cadence_sequence: int | None
    wake_outcome: str | None
    transition_result_fingerprint: str | None
    reservation_event_fingerprint: str | None
    evidence_event_fingerprint: str | None
    transition_invocation_count: int
    automatic_retry_enabled: bool
    automatic_recovery_enabled: bool
    publication_authorized: bool
    deployment_authorized: bool
    scheduler_installation_performed: bool
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


DataTransition = Callable[[], DailyEodCoordinatorResult]
OfflineTransition = Callable[[], DailyEodExecutionResult]
Clock = Callable[[], datetime]


def run_one_pipeline_cadence_wake(
    *,
    run_root: Path,
    pipeline_plan: DailyEodPipelineWakePlan,
    cadence_plan: DailyEodBoundedCadencePlan,
    expected_pipeline_plan_fingerprint: str,
    expected_cadence_plan_fingerprint: str,
    started_at: datetime,
    invoke_one_transition: bool = False,
    data_transition: DataTransition | None = None,
    offline_transition: OfflineTransition | None = None,
    clock: Clock = lambda: datetime.now(UTC),
) -> DailyEodPipelineRuntimeResult:
    """Review or invoke exactly one reserved transition; never loop or retry."""

    target_session = _validate_plans(
        pipeline_plan=pipeline_plan,
        cadence_plan=cadence_plan,
        expected_pipeline_plan_fingerprint=expected_pipeline_plan_fingerprint,
        expected_cadence_plan_fingerprint=expected_cadence_plan_fingerprint,
    )
    started = _aware_utc(started_at)
    if not invoke_one_transition:
        return _result(
            status={
                CadenceStatus.WAITING: PipelineRuntimeStatus.WAITING,
                CadenceStatus.REVIEW_READY: PipelineRuntimeStatus.REVIEW_READY,
                CadenceStatus.STOPPED: PipelineRuntimeStatus.STOPPED,
                CadenceStatus.WAKE_READY: PipelineRuntimeStatus.REVIEW_READY,
            }[cadence_plan.status],
            pipeline_plan=pipeline_plan,
            cadence_plan=cadence_plan,
        )
    _validate_invocation_capability(
        pipeline_plan=pipeline_plan,
        cadence_plan=cadence_plan,
        data_transition=data_transition,
        offline_transition=offline_transition,
    )
    try:
        reservation, pending = reserve_cadence_wake(
            run_root=run_root,
            target_session=target_session,
            cadence_plan=cadence_plan,
            pipeline_plan=pipeline_plan,
            started_at=started,
        )
    except DailyEodCadenceEvidenceError as exc:
        raise DailyEodPipelineRuntimeError(
            "cadence wake was not invoked because reservation failed"
        ) from exc

    try:
        if pipeline_plan.next_action is PipelineWakeAction.INVOKE_ONE_DATA_TRANSITION:
            if data_transition is None:
                raise DailyEodPipelineRuntimeError(
                    "validated data capability disappeared before invocation"
                )
            transition_result = data_transition()
            completed = _aware_utc(clock())
            evidence = cadence_evidence_from_coordinator_result(
                sequence=pending.sequence,
                started_at=started,
                completed_at=completed,
                cadence_plan=cadence_plan,
                pipeline_plan=pipeline_plan,
                result=transition_result,
            )
        else:
            if offline_transition is None:
                raise DailyEodPipelineRuntimeError(
                    "validated offline capability disappeared before invocation"
                )
            transition_result = offline_transition()
            completed = _aware_utc(clock())
            evidence = cadence_evidence_from_offline_result(
                sequence=pending.sequence,
                started_at=started,
                completed_at=completed,
                cadence_plan=cadence_plan,
                pipeline_plan=pipeline_plan,
                result=transition_result,
            )
    except Exception as exc:
        raise DailyEodPipelineRuntimeError(
            "transition outcome is unknown; reservation remains open and replay is prohibited"
        ) from exc

    try:
        retained = resolve_cadence_wake(
            run_root=run_root,
            target_session=target_session,
            cadence_plan=cadence_plan,
            evidence=evidence,
            reservation_event_fingerprint=reservation.event_fingerprint,
        )
    except DailyEodCadenceEvidenceError as exc:
        raise DailyEodPipelineRuntimeError(
            "known transition result was not retained; reservation remains open "
            "and continuation is prohibited"
        ) from exc
    return _result(
        status=PipelineRuntimeStatus.TRANSITION_RECORDED,
        pipeline_plan=pipeline_plan,
        cadence_plan=cadence_plan,
        sequence=evidence.sequence,
        wake_outcome=evidence.outcome.value,
        transition_result_fingerprint=evidence.result_fingerprint,
        reservation_event_fingerprint=reservation.event_fingerprint,
        evidence_event_fingerprint=retained.event_fingerprint,
    )


def verify_daily_eod_pipeline_runtime_result(
    result: DailyEodPipelineRuntimeResult,
) -> None:
    if not isinstance(result, DailyEodPipelineRuntimeResult):
        raise DailyEodPipelineRuntimeError("pipeline runtime result is invalid")
    logical = asdict(result)
    logical.pop("logical_content_fingerprint")
    if (
        result.contract_version != CONTRACT_VERSION
        or result.logical_content_fingerprint != _fingerprint(_jsonable(logical))
    ):
        raise DailyEodPipelineRuntimeError(
            "pipeline runtime result fingerprint mismatch"
        )
    try:
        date.fromisoformat(result.target_session)
        PipelineWakeAction(result.pipeline_action)
        if result.wake_outcome is not None:
            CadenceWakeOutcome(result.wake_outcome)
    except ValueError as exc:
        raise DailyEodPipelineRuntimeError(
            "pipeline runtime result identity is malformed"
        ) from exc
    invoked = result.status is PipelineRuntimeStatus.TRANSITION_RECORDED
    if (
        not isinstance(result.status, PipelineRuntimeStatus)
        or not _is_fingerprint(result.cadence_plan_fingerprint)
        or not _is_fingerprint(result.pipeline_plan_fingerprint)
        or invoked != (result.transition_invocation_count == 1)
        or invoked != (result.cadence_sequence is not None)
        or (
            result.cadence_sequence is not None
            and (
                type(result.cadence_sequence) is not int
                or result.cadence_sequence < 1
            )
        )
        or invoked != (result.wake_outcome is not None)
        or invoked != _is_fingerprint(result.transition_result_fingerprint)
        or invoked != _is_fingerprint(result.reservation_event_fingerprint)
        or invoked != _is_fingerprint(result.evidence_event_fingerprint)
        or result.automatic_retry_enabled
        or result.automatic_recovery_enabled
        or result.publication_authorized
        or result.deployment_authorized
        or result.scheduler_installation_performed
    ):
        raise DailyEodPipelineRuntimeError(
            "pipeline runtime result authority or evidence conflicts"
        )


def _validate_plans(
    *,
    pipeline_plan: DailyEodPipelineWakePlan,
    cadence_plan: DailyEodBoundedCadencePlan,
    expected_pipeline_plan_fingerprint: str,
    expected_cadence_plan_fingerprint: str,
) -> date:
    try:
        verify_daily_eod_pipeline_wake_plan(pipeline_plan)
        verify_bounded_pipeline_cadence_plan(cadence_plan)
        target_session = date.fromisoformat(pipeline_plan.target_session)
    except (
        DailyEodPipelineSchedulerError,
        DailyEodPipelineCadenceError,
        ValueError,
    ) as exc:
        raise DailyEodPipelineRuntimeError("pipeline runtime plans are invalid") from exc
    if (
        pipeline_plan.logical_content_fingerprint
        != expected_pipeline_plan_fingerprint
        or cadence_plan.logical_content_fingerprint
        != expected_cadence_plan_fingerprint
        or cadence_plan.pipeline_plan_fingerprint
        != pipeline_plan.logical_content_fingerprint
        or cadence_plan.target_session != pipeline_plan.target_session
    ):
        raise DailyEodPipelineRuntimeError("pipeline runtime plan identity differs")
    return target_session


def _validate_invocation_capability(
    *,
    pipeline_plan: DailyEodPipelineWakePlan,
    cadence_plan: DailyEodBoundedCadencePlan,
    data_transition: DataTransition | None,
    offline_transition: OfflineTransition | None,
) -> None:
    data_action = (
        pipeline_plan.next_action is PipelineWakeAction.INVOKE_ONE_DATA_TRANSITION
    )
    if (
        cadence_plan.status is not CadenceStatus.WAKE_READY
        or cadence_plan.next_action is not CadenceAction.INVOKE_ONE_TRANSITION
        or not cadence_plan.cadence_candidate_enabled
        or not cadence_plan.pipeline_candidate_enabled
        or (data_transition is not None) == (offline_transition is not None)
        or data_action != (data_transition is not None)
    ):
        raise DailyEodPipelineRuntimeError(
            "one transition requires exactly one matching enabled capability"
        )


def _result(
    *,
    status: PipelineRuntimeStatus,
    pipeline_plan: DailyEodPipelineWakePlan,
    cadence_plan: DailyEodBoundedCadencePlan,
    sequence: int | None = None,
    wake_outcome: str | None = None,
    transition_result_fingerprint: str | None = None,
    reservation_event_fingerprint: str | None = None,
    evidence_event_fingerprint: str | None = None,
) -> DailyEodPipelineRuntimeResult:
    logical = {
        "contract_version": CONTRACT_VERSION,
        "status": status.value,
        "target_session": pipeline_plan.target_session,
        "pipeline_action": pipeline_plan.next_action.value,
        "cadence_plan_fingerprint": cadence_plan.logical_content_fingerprint,
        "pipeline_plan_fingerprint": pipeline_plan.logical_content_fingerprint,
        "cadence_sequence": sequence,
        "wake_outcome": wake_outcome,
        "transition_result_fingerprint": transition_result_fingerprint,
        "reservation_event_fingerprint": reservation_event_fingerprint,
        "evidence_event_fingerprint": evidence_event_fingerprint,
        "transition_invocation_count": 0 if sequence is None else 1,
        "automatic_retry_enabled": False,
        "automatic_recovery_enabled": False,
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_installation_performed": False,
    }
    result = DailyEodPipelineRuntimeResult(
        contract_version=CONTRACT_VERSION,
        status=status,
        target_session=pipeline_plan.target_session,
        pipeline_action=pipeline_plan.next_action.value,
        cadence_plan_fingerprint=cadence_plan.logical_content_fingerprint,
        pipeline_plan_fingerprint=pipeline_plan.logical_content_fingerprint,
        cadence_sequence=sequence,
        wake_outcome=wake_outcome,
        transition_result_fingerprint=transition_result_fingerprint,
        reservation_event_fingerprint=reservation_event_fingerprint,
        evidence_event_fingerprint=evidence_event_fingerprint,
        transition_invocation_count=0 if sequence is None else 1,
        automatic_retry_enabled=False,
        automatic_recovery_enabled=False,
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_installation_performed=False,
        logical_content_fingerprint=_fingerprint(logical),
    )
    verify_daily_eod_pipeline_runtime_result(result)
    return result


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodPipelineRuntimeError("pipeline runtime time must be aware")
    return value.astimezone(UTC)


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
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
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
