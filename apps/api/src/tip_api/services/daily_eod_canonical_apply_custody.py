"""Durable reservation and no-write recovery for canonical daily data apply."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Callable

from tip_api.providers.massive.same_day_catchup import (
    CatchupApprovalPlanEvidenceV1,
    SameDayCatchupError,
    inventory_fingerprint,
    read_catchup_approval_plan_evidence,
)
from tip_api.services.daily_eod_acquisition_custody import (
    EVENT_OUTCOME,
    acquisition_attempts_from_events,
    acquisition_operator_reviews_from_events,
)
from tip_api.services.daily_eod_automation import (
    ArtifactStatus,
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_readiness import (
    DailyEodReadinessPolicy,
    ReadinessNextAction,
    plan_daily_eod_readiness,
)
from tip_api.services.daily_eod_run_journal import (
    ACQUISITION_START_EVENT,
    CANONICAL_APPLY_START_EVENT,
    DailyEodRunEvent,
    locked_daily_eod_run_journal,
    new_attempt_id,
    unresolved_started_event,
)
from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    validate_daily_eod_data_artifact_pair,
)


CONTRACT_VERSION = "daily-eod-canonical-apply-custody/1.1"
MAXIMUM_PLAN_AGE = timedelta(minutes=5)


class DailyEodCanonicalApplyCustodyError(RuntimeError):
    """Raised when canonical apply custody cannot prove a safe transition."""


@dataclass(frozen=True, slots=True)
class DailyEodCanonicalApplyConfig:
    target_session: date
    latest_canonical_session: date
    acquisition_action: NextAction
    package_path: Path
    approval_plan_path: Path
    approved_plan_sha256: str
    expected_current_state_fingerprint: str
    data_root: Path
    run_root: Path
    automation_paths: DailyEodAutomationPaths
    readiness_policy: DailyEodReadinessPolicy = field(
        default_factory=DailyEodReadinessPolicy
    )


@dataclass(frozen=True, slots=True)
class CanonicalApplyCustodyResult:
    outcome: str
    attempt_id: str
    event: DailyEodRunEvent
    plan_evidence: CatchupApprovalPlanEvidenceV1 | None
    automation_plan: DailyEodAutomationPlan | None
    reason_code: str

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": CONTRACT_VERSION,
            "outcome": self.outcome,
            "attempt_id": self.attempt_id,
            "event_fingerprint": self.event.event_fingerprint,
            "approval_plan_sha256": (
                None
                if self.plan_evidence is None
                else self.plan_evidence.plan_file_sha256
            ),
            "automation_plan_fingerprint": (
                None
                if self.automation_plan is None
                else self.automation_plan.logical_content_fingerprint
            ),
            "reason_code": self.reason_code,
            "apply_executed_by_custody": False,
            "provider_request_count": 0,
            "production_write_count": 0,
            "publication_authorized": False,
            "deployment_authorized": False,
            "scheduler_enabled": False,
        }


Clock = Callable[[], datetime]
Planner = Callable[..., DailyEodAutomationPlan]
PlanReader = Callable[..., CatchupApprovalPlanEvidenceV1]
InventoryReader = Callable[[Path], str]


def reserve_canonical_apply(
    *,
    config: DailyEodCanonicalApplyConfig,
    checked_at: datetime,
    expected_readiness_fingerprint: str,
    authorization_file_sha256: str | None = None,
    authorization_content_sha256: str | None = None,
    clock: Clock = lambda: datetime.now(UTC),
    plan_reader: PlanReader = read_catchup_approval_plan_evidence,
    inventory_reader: InventoryReader = inventory_fingerprint,
) -> CanonicalApplyCustodyResult:
    """Reserve one separately authorized canonical apply without executing it."""

    _validate_config(config)
    checked = _aware_utc(checked_at)
    observed = _aware_utc(clock())
    if observed < checked or observed - checked > MAXIMUM_PLAN_AGE:
        raise DailyEodCanonicalApplyCustodyError(
            "apply readiness is outside the reservation age window"
        )
    if not _is_fingerprint(expected_readiness_fingerprint):
        raise DailyEodCanonicalApplyCustodyError("readiness fingerprint is malformed")
    _validate_authorization_binding(
        authorization_file_sha256,
        authorization_content_sha256,
    )
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        events = journal.read_events()
        if unresolved_started_event(events) is not None:
            raise DailyEodCanonicalApplyCustodyError("daily run has an unresolved attempt")
        readiness = plan_daily_eod_readiness(
            checked_at=checked,
            target_session=config.target_session,
            latest_canonical_session=config.latest_canonical_session,
            acquisition_action=config.acquisition_action,
            attempts=acquisition_attempts_from_events(
                events,
                target_session=config.target_session,
                acquisition_action=config.acquisition_action,
            ),
            operator_reviews=acquisition_operator_reviews_from_events(
                events,
                target_session=config.target_session,
                acquisition_action=config.acquisition_action,
            ),
            policy=config.readiness_policy,
        )
        if (
            readiness.logical_content_fingerprint != expected_readiness_fingerprint
            or readiness.next_action is not ReadinessNextAction.REVIEW_APPLY_AUTHORIZATION
        ):
            raise DailyEodCanonicalApplyCustodyError(
                "readiness plan is stale or not apply-reviewable"
            )
        acquisition_start, acquisition_terminal = _completed_acquisition(
            events,
            config.acquisition_action,
        )
        evidence = _read_plan(config, plan_reader)
        _validate_plan_and_acquisition(
            config,
            evidence,
            acquisition_start,
            acquisition_terminal,
        )
        if inventory_reader(config.data_root) != config.expected_current_state_fingerprint:
            raise DailyEodCanonicalApplyCustodyError(
                "canonical inventory changed before apply reservation"
            )
        if any(os.path.lexists(path) for path in map(Path, evidence.publication_order)):
            raise DailyEodCanonicalApplyCustodyError(
                "canonical apply target is no longer absent"
            )
        input_fingerprint = _execution_input_fingerprint(config)
        attempt_id = new_attempt_id(
            target_session=config.target_session,
            plan_fingerprint=_fingerprint(
                {
                    "readiness": readiness.logical_content_fingerprint,
                    "inputs": input_fingerprint,
                }
            ),
            sequence=len(events) + 1,
        )
        event = journal.append(
            event_type=CANONICAL_APPLY_START_EVENT,
            attempt_id=attempt_id,
            observed_at=observed,
            details={
                "custody_contract": CONTRACT_VERSION,
                "acquisition_action": config.acquisition_action.value,
                "operation": evidence.operation,
                "readiness_plan_fingerprint": readiness.logical_content_fingerprint,
                "acquisition_event_fingerprint": acquisition_terminal.event_fingerprint,
                "approval_plan_sha256": evidence.plan_file_sha256,
                "approval_plan_content_sha256": evidence.plan_content_sha256,
                "expected_current_state_fingerprint": evidence.expected_current_state_fingerprint,
                "execution_input_fingerprint": input_fingerprint,
                "authorization_file_sha256": authorization_file_sha256,
                "authorization_content_sha256": authorization_content_sha256,
            },
        )
        return CanonicalApplyCustodyResult(
            outcome="reserved",
            attempt_id=attempt_id,
            event=event,
            plan_evidence=evidence,
            automation_plan=None,
            reason_code="canonical_apply_reserved_but_not_executed",
        )


def record_canonical_apply_success(
    *,
    config: DailyEodCanonicalApplyConfig,
    authorization_decision_fingerprint: str | None = None,
    clock: Clock = lambda: datetime.now(UTC),
    planner: Planner = plan_daily_eod_automation,
) -> CanonicalApplyCustodyResult:
    """Record success only after formal canonical state proves plan advancement."""

    _validate_config(config)
    if authorization_decision_fingerprint is not None and not _is_fingerprint(
        authorization_decision_fingerprint
    ):
        raise DailyEodCanonicalApplyCustodyError(
            "authorization decision fingerprint is malformed"
        )
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        pending = _pending_apply(journal.read_events(), config)
        current = planner(
            target_session=config.target_session,
            paths=config.automation_paths,
        )
        _validate_automation_plan(current, config)
        if not _canonical_stage_completed(current, config.acquisition_action):
            raise DailyEodCanonicalApplyCustodyError(
                "canonical apply success is not formally proven; recovery required"
            )
        event = journal.append(
            event_type="canonical_apply_succeeded",
            attempt_id=pending.attempt_id,
            observed_at=_aware_utc(clock()),
            details={
                "acquisition_action": config.acquisition_action.value,
                "automation_plan_fingerprint": current.logical_content_fingerprint,
                "automation_status": current.status.value,
                "automation_next_action": current.next_action.value,
                "reason_code": "canonical_stage_completed_and_replanned",
                "authorization_decision_fingerprint": authorization_decision_fingerprint,
            },
        )
        return CanonicalApplyCustodyResult(
            outcome="succeeded",
            attempt_id=pending.attempt_id,
            event=event,
            plan_evidence=None,
            automation_plan=current,
            reason_code="canonical_stage_completed_and_replanned",
        )


def recover_canonical_apply(
    *,
    config: DailyEodCanonicalApplyConfig,
    clock: Clock = lambda: datetime.now(UTC),
    planner: Planner = plan_daily_eod_automation,
    plan_reader: PlanReader = read_catchup_approval_plan_evidence,
    inventory_reader: InventoryReader = inventory_fingerprint,
) -> CanonicalApplyCustodyResult:
    """Classify interrupted canonical apply without executing or completing it."""

    _validate_config(config)
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        pending = _pending_apply(journal.read_events(), config)
        current = planner(
            target_session=config.target_session,
            paths=config.automation_paths,
        )
        _validate_automation_plan(current, config)
        evidence: CatchupApprovalPlanEvidenceV1 | None = None
        if _canonical_stage_completed(current, config.acquisition_action):
            event_type = "canonical_apply_recovered_succeeded"
            outcome = "recovered_succeeded"
            reason = "canonical_stage_formally_reconciled"
        else:
            try:
                evidence = _read_plan(config, plan_reader)
                targets_absent = all(
                    not os.path.lexists(path)
                    for path in map(Path, evidence.publication_order)
                )
                inventory_unchanged = (
                    inventory_reader(config.data_root)
                    == config.expected_current_state_fingerprint
                )
            except (OSError, SameDayCatchupError, DailyEodCanonicalApplyCustodyError):
                targets_absent = False
                inventory_unchanged = False
            if targets_absent and inventory_unchanged:
                event_type = "canonical_apply_recovered_not_completed"
                outcome = "recovered_not_completed"
                reason = "no_canonical_write_detected"
            else:
                event_type = "canonical_apply_recovery_blocked"
                outcome = "recovery_blocked"
                reason = "canonical_apply_state_is_partial_changed_or_ambiguous"
        event = journal.append(
            event_type=event_type,
            attempt_id=pending.attempt_id,
            observed_at=_aware_utc(clock()),
            details={
                "acquisition_action": config.acquisition_action.value,
                "automation_plan_fingerprint": current.logical_content_fingerprint,
                "automation_status": current.status.value,
                "automation_next_action": current.next_action.value,
                "reason_code": reason,
                "apply_executed_by_recovery": False,
            },
        )
        return CanonicalApplyCustodyResult(
            outcome=outcome,
            attempt_id=pending.attempt_id,
            event=event,
            plan_evidence=evidence,
            automation_plan=current,
            reason_code=reason,
        )


def _read_plan(
    config: DailyEodCanonicalApplyConfig,
    reader: PlanReader,
) -> CatchupApprovalPlanEvidenceV1:
    operation = _operation(config.acquisition_action)
    try:
        evidence = reader(
            plan_path=config.approval_plan_path,
            approved_plan_sha256=config.approved_plan_sha256,
            expected_operation=operation,
            expected_session=config.target_session,
            expected_data_root=config.data_root,
        )
    except (OSError, SameDayCatchupError, ValueError) as exc:
        raise DailyEodCanonicalApplyCustodyError(
            "canonical apply plan failed formal reread"
        ) from exc
    if (
        evidence.operation != operation
        or evidence.session_date != config.target_session
        or evidence.plan_path != str(config.approval_plan_path)
        or evidence.plan_file_sha256 != config.approved_plan_sha256
        or evidence.data_root != str(config.data_root)
        or evidence.fetch_package_path != str(config.package_path)
        or evidence.expected_current_state_fingerprint
        != config.expected_current_state_fingerprint
    ):
        raise DailyEodCanonicalApplyCustodyError(
            "canonical apply plan identity mismatch"
        )
    return evidence


def _validate_plan_and_acquisition(
    config: DailyEodCanonicalApplyConfig,
    evidence: CatchupApprovalPlanEvidenceV1,
    acquisition_start: DailyEodRunEvent,
    acquisition_terminal: DailyEodRunEvent,
) -> None:
    if (
        acquisition_start.details.get("package_path") != str(config.package_path)
        or acquisition_terminal.details.get("package_manifest_sha256")
        != evidence.fetch_package_manifest_sha256
        or acquisition_terminal.details.get("package_content_sha256")
        != evidence.fetch_package_content_sha256
    ):
        raise DailyEodCanonicalApplyCustodyError(
            "canonical apply plan differs from acquisition custody"
        )


def _completed_acquisition(
    events: tuple[DailyEodRunEvent, ...],
    action: NextAction,
) -> tuple[DailyEodRunEvent, DailyEodRunEvent]:
    pending: DailyEodRunEvent | None = None
    latest: tuple[DailyEodRunEvent, DailyEodRunEvent] | None = None
    for event in events:
        if event.event_type == ACQUISITION_START_EVENT:
            pending = event
            continue
        if event.event_type in EVENT_OUTCOME:
            if pending is None or pending.attempt_id != event.attempt_id:
                raise DailyEodCanonicalApplyCustodyError(
                    "acquisition journal pairing is invalid"
                )
            if pending.details.get("acquisition_action") == action.value:
                latest = (pending, event)
            pending = None
    if latest is None or latest[1].event_type not in {
        "acquisition_package_ready",
        "acquisition_recovered_package_ready",
    }:
        raise DailyEodCanonicalApplyCustodyError(
            "completed acquisition package is unavailable"
        )
    return latest


def _pending_apply(
    events: tuple[DailyEodRunEvent, ...],
    config: DailyEodCanonicalApplyConfig,
) -> DailyEodRunEvent:
    pending = unresolved_started_event(events)
    if pending is None or pending.event_type != CANONICAL_APPLY_START_EVENT:
        raise DailyEodCanonicalApplyCustodyError(
            "no unresolved canonical apply exists"
        )
    if pending.details.get("execution_input_fingerprint") != _execution_input_fingerprint(
        config
    ):
        raise DailyEodCanonicalApplyCustodyError(
            "canonical apply inputs differ from reservation"
        )
    return pending


def _canonical_stage_completed(
    plan: DailyEodAutomationPlan,
    action: NextAction,
) -> bool:
    stage = "identity" if action is NextAction.PREPARE_IDENTITY_CATCHUP else "eod"
    return any(
        observation.stage == stage
        and observation.status is ArtifactStatus.COMPLETED
        and observation.as_of_session == plan.target_session
        for observation in plan.observations
    ) and plan.next_action is not action


def _validate_automation_plan(
    plan: DailyEodAutomationPlan,
    config: DailyEodCanonicalApplyConfig,
) -> None:
    if (
        not isinstance(plan, DailyEodAutomationPlan)
        or plan.target_session != config.target_session.isoformat()
        or not _is_fingerprint(plan.logical_content_fingerprint)
        or plan.publication_authorized
        or plan.deployment_authorized
        or plan.scheduler_enabled
        or plan.external_request_count != 0
        or plan.production_write_count != 0
    ):
        raise DailyEodCanonicalApplyCustodyError(
            "canonical automation plan differs from apply custody"
        )


def _validate_config(config: DailyEodCanonicalApplyConfig) -> None:
    if not isinstance(config.readiness_policy, DailyEodReadinessPolicy):
        raise DailyEodCanonicalApplyCustodyError("readiness policy is invalid")
    if config.acquisition_action not in {
        NextAction.PREPARE_IDENTITY_CATCHUP,
        NextAction.PREPARE_EOD_CATCHUP,
    }:
        raise DailyEodCanonicalApplyCustodyError("canonical apply action is invalid")
    if (
        not config.data_root.is_absolute()
        or not config.run_root.is_absolute()
        or _is_within(config.run_root, config.data_root)
        or _is_within(config.run_root, Path("/data"))
    ):
        raise DailyEodCanonicalApplyCustodyError("canonical apply roots are invalid")
    try:
        validate_daily_eod_data_artifact_pair(
            package_path=config.package_path,
            plan_path=config.approval_plan_path,
            expected_session=config.target_session,
        )
    except OfflineArtifactCustodyError as exc:
        raise DailyEodCanonicalApplyCustodyError(
            "canonical apply custody path is invalid"
        ) from exc
    if not _is_fingerprint(config.approved_plan_sha256) or not _is_fingerprint(
        config.expected_current_state_fingerprint
    ):
        raise DailyEodCanonicalApplyCustodyError(
            "canonical apply fingerprints are malformed"
        )


def _validate_authorization_binding(
    file_sha256: str | None,
    content_sha256: str | None,
) -> None:
    if (file_sha256 is None) != (content_sha256 is None) or (
        file_sha256 is not None
        and (not _is_fingerprint(file_sha256) or not _is_fingerprint(content_sha256))
    ):
        raise DailyEodCanonicalApplyCustodyError(
            "authorization artifact binding is malformed"
        )


def _execution_input_fingerprint(config: DailyEodCanonicalApplyConfig) -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "target_session": config.target_session.isoformat(),
            "latest_canonical_session": config.latest_canonical_session.isoformat(),
            "acquisition_action": config.acquisition_action.value,
            "package_path": str(config.package_path),
            "approval_plan_path": str(config.approval_plan_path),
            "approved_plan_sha256": config.approved_plan_sha256,
            "expected_current_state_fingerprint": config.expected_current_state_fingerprint,
            "data_root": str(config.data_root),
            "run_root": str(config.run_root),
            "automation_paths": {
                key: str(value)
                for key, value in asdict(config.automation_paths).items()
            },
            "readiness_policy_fingerprint": (
                config.readiness_policy.logical_fingerprint
            ),
        }
    )


def _operation(action: NextAction) -> str:
    return "identity" if action is NextAction.PREPARE_IDENTITY_CATCHUP else "eod"


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodCanonicalApplyCustodyError(
            "canonical apply timestamps must be timezone-aware"
        )
    return value.astimezone(UTC)


def _fingerprint(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.absolute().relative_to(root.absolute())
        return True
    except ValueError:
        return False
