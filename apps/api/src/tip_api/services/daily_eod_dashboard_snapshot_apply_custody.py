"""Durable reservation and no-write recovery for Dashboard Snapshot Apply."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Callable

from tip_api.contracts.market_data.v2.dashboard_snapshot import (
    DashboardSnapshotApprovalPlanV2_4,
)
from tip_api.persistence.parquet.dashboard_snapshot_active import (
    ActiveDashboardSnapshot,
    DashboardSnapshotPublicationError,
    current_state_fingerprint,
    pointer_path,
    read_active_dashboard_snapshot,
    read_dashboard_snapshot_approval_plan,
    target_path,
)
from tip_api.persistence.parquet.dashboard_universe_activation_active import (
    read_dashboard_universe_activation_pointer,
)
from tip_api.persistence.parquet.dashboard_universe_activation import (
    DashboardUniverseActivationError,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_run_journal import (
    DASHBOARD_SNAPSHOT_APPLY_START_EVENT,
    DailyEodRunEvent,
    locked_daily_eod_run_journal,
    new_attempt_id,
    unresolved_started_event,
)
from tip_api.services.market_calendar import (
    ExchangeCalendar,
    evaluate_market_data_freshness,
)


CONTRACT_VERSION = "daily-eod-dashboard-snapshot-apply-custody/1.0"
MAXIMUM_PLAN_AGE = timedelta(minutes=5)


class DailyEodDashboardSnapshotApplyCustodyError(RuntimeError):
    """Raised when Snapshot Apply custody cannot prove a safe transition."""


@dataclass(frozen=True, slots=True)
class DailyEodDashboardSnapshotApplyConfig:
    target_session: date
    approval_plan_path: Path
    approved_plan_sha256: str
    expected_current_state_fingerprint: str
    review_acknowledgement_sha256: str | None
    data_root: Path
    legacy_root: Path
    run_root: Path
    automation_paths: DailyEodAutomationPaths


@dataclass(frozen=True, slots=True)
class DashboardSnapshotApplyCustodyResult:
    outcome: str
    attempt_id: str
    event: DailyEodRunEvent
    approval_plan: DashboardSnapshotApprovalPlanV2_4 | None
    active_snapshot: ActiveDashboardSnapshot | None
    reason_code: str

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": CONTRACT_VERSION,
            "outcome": self.outcome,
            "attempt_id": self.attempt_id,
            "event_fingerprint": self.event.event_fingerprint,
            "release_id": (
                None if self.approval_plan is None else self.approval_plan.release_id
            ),
            "reason_code": self.reason_code,
            "apply_executed_by_custody": False,
            "external_request_count": 0,
            "production_write_count_by_custody": 0,
            "publication_authorized": False,
            "deployment_authorized": False,
            "scheduler_enabled": False,
        }


Clock = Callable[[], datetime]
Planner = Callable[..., DailyEodAutomationPlan]
PlanReader = Callable[[Path], object]
StateReader = Callable[[Path, Path], str]
ActivationReader = Callable[[Path], object]
ActiveReader = Callable[[Path, Path], ActiveDashboardSnapshot]


def reserve_dashboard_snapshot_apply(
    *,
    config: DailyEodDashboardSnapshotApplyConfig,
    checked_at: datetime,
    expected_automation_plan_fingerprint: str,
    review_acknowledgement: str | None = None,
    clock: Clock = lambda: datetime.now(UTC),
    planner: Planner = plan_daily_eod_automation,
    plan_reader: PlanReader = read_dashboard_snapshot_approval_plan,
    state_reader: StateReader = current_state_fingerprint,
    activation_reader: ActivationReader = read_dashboard_universe_activation_pointer,
) -> DashboardSnapshotApplyCustodyResult:
    """Reserve one explicitly invoked Snapshot Apply without executing it."""

    _validate_config(config)
    checked = _aware_utc(checked_at)
    observed = _aware_utc(clock())
    if observed < checked or observed - checked > MAXIMUM_PLAN_AGE:
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot Apply review is outside the reservation age window"
        )
    if not _is_fingerprint(expected_automation_plan_fingerprint):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot Apply automation fingerprint is malformed"
        )
    _validate_review_acknowledgement(config, review_acknowledgement)
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        events = journal.read_events()
        if unresolved_started_event(events) is not None:
            raise DailyEodDashboardSnapshotApplyCustodyError(
                "daily run has an unresolved attempt"
            )
        automation = planner(
            target_session=config.target_session,
            paths=config.automation_paths,
        )
        _validate_reviewable_automation(
            automation,
            config,
            expected_automation_plan_fingerprint,
        )
        approval = _read_plan(config, plan_reader)
        validate_approved_dashboard_snapshot_freshness(
            root=config.data_root,
            plan=approval,
            checked_at=observed,
            review_acknowledgement=review_acknowledgement,
        )
        if (
            state_reader(config.data_root, config.legacy_root)
            != config.expected_current_state_fingerprint
        ):
            raise DailyEodDashboardSnapshotApplyCustodyError(
                "active Snapshot state changed before Apply reservation"
            )
        _require_activation_pointer(config, approval, activation_reader)
        _require_new_target(approval)
        input_fingerprint = _execution_input_fingerprint(config)
        attempt_id = new_attempt_id(
            target_session=config.target_session,
            plan_fingerprint=_fingerprint(
                {
                    "automation": automation.logical_content_fingerprint,
                    "inputs": input_fingerprint,
                }
            ),
            sequence=len(events) + 1,
        )
        event = journal.append(
            event_type=DASHBOARD_SNAPSHOT_APPLY_START_EVENT,
            attempt_id=attempt_id,
            observed_at=observed,
            details={
                "custody_contract": CONTRACT_VERSION,
                "operation": "dashboard_snapshot_publication",
                "automation_plan_fingerprint": automation.logical_content_fingerprint,
                "approval_plan_sha256": config.approved_plan_sha256,
                "approval_plan_content_fingerprint": approval.plan_content_fingerprint,
                "release_id": approval.release_id,
                "expected_current_state_fingerprint": (
                    config.expected_current_state_fingerprint
                ),
                "activation_pointer_fingerprint": (
                    approval.activation_pointer_fingerprint
                ),
                "planned_pointer_fingerprint": approval.planned_pointer_fingerprint,
                "review_acknowledgement_sha256": (
                    config.review_acknowledgement_sha256
                ),
                "execution_input_fingerprint": input_fingerprint,
            },
        )
        return DashboardSnapshotApplyCustodyResult(
            outcome="reserved",
            attempt_id=attempt_id,
            event=event,
            approval_plan=approval,
            active_snapshot=None,
            reason_code="dashboard_snapshot_apply_reserved_but_not_executed",
        )


def record_dashboard_snapshot_apply_success(
    *,
    config: DailyEodDashboardSnapshotApplyConfig,
    clock: Clock = lambda: datetime.now(UTC),
    plan_reader: PlanReader = read_dashboard_snapshot_approval_plan,
    active_reader: ActiveReader = read_active_dashboard_snapshot,
) -> DashboardSnapshotApplyCustodyResult:
    """Record success only after the active pointer proves the exact plan."""

    _validate_config(config)
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        pending = _pending_apply(journal.read_events(), config)
        approval = _read_plan(config, plan_reader)
        active = _read_exact_active(config, approval, active_reader)
        event = journal.append(
            event_type="dashboard_snapshot_apply_succeeded",
            attempt_id=pending.attempt_id,
            observed_at=_aware_utc(clock()),
            details={
                "release_id": approval.release_id,
                "planned_pointer_fingerprint": approval.planned_pointer_fingerprint,
                "active_pointer_fingerprint": (
                    active.pointer.pointer_content_fingerprint
                ),
                "inventory_change_file_count": len(approval.files) + 1,
                "reason_code": "dashboard_snapshot_active_state_formally_proven",
            },
        )
        return DashboardSnapshotApplyCustodyResult(
            outcome="succeeded",
            attempt_id=pending.attempt_id,
            event=event,
            approval_plan=approval,
            active_snapshot=active,
            reason_code="dashboard_snapshot_active_state_formally_proven",
        )


def recover_dashboard_snapshot_apply(
    *,
    config: DailyEodDashboardSnapshotApplyConfig,
    clock: Clock = lambda: datetime.now(UTC),
    plan_reader: PlanReader = read_dashboard_snapshot_approval_plan,
    active_reader: ActiveReader = read_active_dashboard_snapshot,
    state_reader: StateReader = current_state_fingerprint,
    activation_reader: ActivationReader = read_dashboard_universe_activation_pointer,
) -> DashboardSnapshotApplyCustodyResult:
    """Classify interrupted Snapshot Apply without publishing or linking it."""

    _validate_config(config)
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        pending = _pending_apply(journal.read_events(), config)
        approval: DashboardSnapshotApprovalPlanV2_4 | None = None
        active: ActiveDashboardSnapshot | None = None
        try:
            approval = _read_plan(config, plan_reader)
            active = _read_exact_active(config, approval, active_reader)
        except (
            OSError,
            DashboardSnapshotPublicationError,
            DashboardUniverseActivationError,
            DailyEodDashboardSnapshotApplyCustodyError,
            ValueError,
        ):
            active = None
        if approval is not None and active is not None:
            event_type = "dashboard_snapshot_apply_recovered_succeeded"
            outcome = "recovered_succeeded"
            reason = "dashboard_snapshot_active_state_formally_reconciled"
        else:
            try:
                approval = approval or _read_plan(config, plan_reader)
                untouched = (
                    not os.path.lexists(Path(approval.target_path))
                    and not _matching_staging_exists(approval)
                    and state_reader(config.data_root, config.legacy_root)
                    == config.expected_current_state_fingerprint
                    and _activation_matches(
                        config,
                        approval,
                        activation_reader,
                    )
                )
            except (
                OSError,
                DashboardSnapshotPublicationError,
                DashboardUniverseActivationError,
                DailyEodDashboardSnapshotApplyCustodyError,
                ValueError,
            ):
                untouched = False
            if untouched:
                event_type = "dashboard_snapshot_apply_recovered_not_completed"
                outcome = "recovered_not_completed"
                reason = "no_dashboard_snapshot_production_write_detected"
            else:
                event_type = "dashboard_snapshot_apply_recovery_blocked"
                outcome = "recovery_blocked"
                reason = "dashboard_snapshot_apply_state_is_partial_changed_or_ambiguous"
        event = journal.append(
            event_type=event_type,
            attempt_id=pending.attempt_id,
            observed_at=_aware_utc(clock()),
            details={
                "release_id": pending.details.get("release_id"),
                "reason_code": reason,
                "apply_executed_by_recovery": False,
            },
        )
        return DashboardSnapshotApplyCustodyResult(
            outcome=outcome,
            attempt_id=pending.attempt_id,
            event=event,
            approval_plan=approval,
            active_snapshot=active,
            reason_code=reason,
        )


def validate_approved_dashboard_snapshot_freshness(
    *,
    root: Path,
    plan: DashboardSnapshotApprovalPlanV2_4,
    checked_at: datetime,
    review_acknowledgement: str | None,
) -> None:
    """Recompute the exact normal or review freshness promised by a plan."""

    sessions = CanonicalEodReadRepository(root).list_sessions()
    if not sessions:
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "no completed EOD session exists for Snapshot Apply"
        )
    freshness = evaluate_market_data_freshness(
        calendar=ExchangeCalendar(),
        actual_latest_completed_session=max(item.session_date for item in sessions),
        checked_at=_aware_utc(checked_at),
    )
    if plan.normal_freshness:
        valid = (
            review_acknowledgement is None
            and freshness.freshness_status.value == "fresh"
            and freshness.session_lag == 0
            and freshness.actual_latest_completed_session
            == plan.actual_latest_completed_session
            and freshness.expected_latest_completed_session
            == plan.expected_latest_completed_session
        )
    else:
        review = plan.review_deployment
        valid = (
            plan.activation_allowed_by_review_authorization
            and review is not None
            and review_acknowledgement == review.explicit_user_acknowledgement
            and plan.analysis_session == review.approved_as_of_session
            and freshness.actual_latest_completed_session
            == review.approved_as_of_session
            and freshness.expected_latest_completed_session
            == review.expected_latest_session
            and freshness.session_lag == review.expected_lag_sessions
            and freshness.freshness_status.value == "stale"
        )
    if not valid:
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "current freshness differs from the approved Snapshot plan"
        )


def _read_plan(
    config: DailyEodDashboardSnapshotApplyConfig,
    reader: PlanReader,
) -> DashboardSnapshotApprovalPlanV2_4:
    try:
        value = reader(config.approval_plan_path)
        if not isinstance(value, DashboardSnapshotApprovalPlanV2_4):
            raise DailyEodDashboardSnapshotApplyCustodyError(
                "daily Snapshot Apply requires current Approval Plan 2.4"
            )
        raw = config.approval_plan_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != config.approved_plan_sha256:
            raise DailyEodDashboardSnapshotApplyCustodyError(
                "Snapshot approval plan full-file SHA-256 mismatch"
            )
        plan = value
    except DailyEodDashboardSnapshotApplyCustodyError:
        raise
    except (OSError, DashboardSnapshotPublicationError, ValueError) as exc:
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot approval plan failed formal reread"
        ) from exc
    if (
        plan.analysis_session != config.target_session
        or plan.expected_current_state_fingerprint
        != config.expected_current_state_fingerprint
        or Path(plan.target_path) != target_path(config.data_root, plan.release_id)
        or Path(plan.target_logical_path)
        != target_path(config.data_root, plan.release_id).relative_to(config.data_root)
        or Path(plan.pointer_path) != pointer_path(config.data_root)
        or Path(plan.candidate_path).parent
        != config.automation_paths.snapshot_output_root
        or config.approval_plan_path
        != config.automation_paths.snapshot_approval_plan
    ):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot approval plan identity mismatch"
        )
    return plan


def _read_exact_active(
    config: DailyEodDashboardSnapshotApplyConfig,
    approval: DashboardSnapshotApprovalPlanV2_4,
    reader: ActiveReader,
) -> ActiveDashboardSnapshot:
    try:
        active = reader(config.data_root, config.legacy_root)
    except (OSError, DashboardSnapshotPublicationError, ValueError) as exc:
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "active Dashboard Snapshot is not formally readable"
        ) from exc
    if (
        active.pointer is None
        or active.pointer.pointer_content_fingerprint
        != approval.planned_pointer_fingerprint
        or active.manifest.release_id != approval.release_id
        or active.manifest.current_session_date
        != config.target_session.isoformat()
        or active.release_path != Path(approval.target_path)
        or active.reference.aggregate_sha256 != approval.aggregate_sha256
        or active.reference.release_id != approval.release_id
        or active.reference.manifest_sha256 != approval.manifest_sha256
        or active.reference.snapshot_contract_version
        != approval.snapshot_contract_version
        or active.reference.dashboard_contract_version
        != approval.dashboard_contract_version
    ):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "active Dashboard Snapshot differs from the approved plan"
        )
    return active


def _require_activation_pointer(
    config: DailyEodDashboardSnapshotApplyConfig,
    approval: DashboardSnapshotApprovalPlanV2_4,
    reader: ActivationReader,
) -> None:
    if not _activation_matches(config, approval, reader):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Dashboard Universe Activation changed before Snapshot Apply"
        )


def _activation_matches(
    config: DailyEodDashboardSnapshotApplyConfig,
    approval: DashboardSnapshotApprovalPlanV2_4,
    reader: ActivationReader,
) -> bool:
    pointer = reader(config.data_root)
    return (
        pointer is not None
        and getattr(pointer, "pointer_content_fingerprint", None)
        == approval.activation_pointer_fingerprint
    )


def _require_new_target(plan: DashboardSnapshotApprovalPlanV2_4) -> None:
    target = Path(plan.target_path)
    if os.path.lexists(target):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot Apply target is no longer absent"
        )
    if _matching_staging_exists(plan):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot Apply staging state is already present"
        )


def _matching_staging_exists(plan: DashboardSnapshotApprovalPlanV2_4) -> bool:
    target = Path(plan.target_path)
    return target.parent.exists() and any(
        item.name.startswith(f".{target.name}.staging-")
        for item in target.parent.iterdir()
    )


def _pending_apply(
    events: tuple[DailyEodRunEvent, ...],
    config: DailyEodDashboardSnapshotApplyConfig,
) -> DailyEodRunEvent:
    pending = unresolved_started_event(events)
    if (
        pending is None
        or pending.event_type != DASHBOARD_SNAPSHOT_APPLY_START_EVENT
    ):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "no unresolved Snapshot Apply exists"
        )
    if (
        pending.details.get("execution_input_fingerprint")
        != _execution_input_fingerprint(config)
    ):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot Apply inputs differ from reservation"
        )
    return pending


def _validate_reviewable_automation(
    plan: DailyEodAutomationPlan,
    config: DailyEodDashboardSnapshotApplyConfig,
    expected_fingerprint: str,
) -> None:
    if (
        not isinstance(plan, DailyEodAutomationPlan)
        or plan.target_session != config.target_session.isoformat()
        or plan.status is not PlanStatus.ANALYTICS_READY
        or plan.next_action is not NextAction.REVIEW_SNAPSHOT_PUBLICATION
        or plan.logical_content_fingerprint != expected_fingerprint
        or plan.publication_authorized
        or plan.deployment_authorized
        or plan.scheduler_enabled
        or plan.external_request_count != 0
        or plan.production_write_count != 0
    ):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "automation plan is stale or not Snapshot Apply-reviewable"
        )


def _validate_review_acknowledgement(
    config: DailyEodDashboardSnapshotApplyConfig,
    acknowledgement: str | None,
) -> None:
    actual = (
        None
        if acknowledgement is None
        else hashlib.sha256(acknowledgement.encode("utf-8")).hexdigest()
    )
    if actual != config.review_acknowledgement_sha256:
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot review acknowledgement differs from the approved invocation"
        )


def _validate_config(config: DailyEodDashboardSnapshotApplyConfig) -> None:
    if (
        not config.data_root.is_absolute()
        or not config.legacy_root.is_absolute()
        or not config.run_root.is_absolute()
        or _paths_overlap(config.run_root, config.data_root)
        or _is_within(config.run_root, Path("/data"))
        or _paths_overlap(config.legacy_root, config.data_root)
        or _paths_overlap(config.legacy_root, config.run_root)
    ):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot Apply roots are invalid"
        )
    if (
        not config.approval_plan_path.is_absolute()
        or config.approval_plan_path.parent != Path("/tmp")
        or config.approval_plan_path.name.startswith(".")
    ):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot Apply approval path is invalid"
        )
    if (
        not _is_fingerprint(config.approved_plan_sha256)
        or not _is_fingerprint(config.expected_current_state_fingerprint)
        or (
            config.review_acknowledgement_sha256 is not None
            and not _is_fingerprint(config.review_acknowledgement_sha256)
        )
    ):
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot Apply fingerprints are malformed"
        )


def _execution_input_fingerprint(
    config: DailyEodDashboardSnapshotApplyConfig,
) -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "target_session": config.target_session.isoformat(),
            "approval_plan_path": str(config.approval_plan_path),
            "approved_plan_sha256": config.approved_plan_sha256,
            "expected_current_state_fingerprint": (
                config.expected_current_state_fingerprint
            ),
            "review_acknowledgement_sha256": (
                config.review_acknowledgement_sha256
            ),
            "data_root": str(config.data_root),
            "legacy_root": str(config.legacy_root),
            "run_root": str(config.run_root),
            "automation_paths": {
                key: str(value)
                for key, value in asdict(config.automation_paths).items()
            },
        }
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot Apply timestamps must be timezone-aware"
        )
    if value.utcoffset().total_seconds() != 0:
        raise DailyEodDashboardSnapshotApplyCustodyError(
            "Snapshot Apply timestamps must be UTC"
        )
    return value.astimezone(UTC)


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.absolute().relative_to(root.absolute())
        return True
    except ValueError:
        return False


def _paths_overlap(left: Path, right: Path) -> bool:
    return _is_within(left, right) or _is_within(right, left)
