"""Durable reservation and no-write recovery for Market Intelligence Apply."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Callable

from tip_api.contracts.analytics.v1 import MarketIntelligenceApprovalPlanV1
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.market_intelligence_active import (
    CompletedMarketIntelligence,
    MarketIntelligencePublicationError,
    consumer_state_fingerprint,
    read_active_market_intelligence,
    read_market_intelligence_approval_plan,
    pointer_path,
    target_path,
)
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_run_journal import (
    MARKET_INTELLIGENCE_APPLY_START_EVENT,
    DailyEodRunEvent,
    locked_daily_eod_run_journal,
    new_attempt_id,
    unresolved_started_event,
)
from tip_api.services.market_calendar import (
    ExchangeCalendar,
    evaluate_market_data_freshness,
)


CONTRACT_VERSION = "daily-eod-market-intelligence-apply-custody/1.0"
MAXIMUM_PLAN_AGE = timedelta(minutes=5)


class DailyEodMarketIntelligenceApplyCustodyError(RuntimeError):
    """Raised when MI Apply custody cannot prove a safe transition."""


@dataclass(frozen=True, slots=True)
class DailyEodMarketIntelligenceApplyConfig:
    target_session: date
    approval_plan_path: Path
    approved_plan_sha256: str
    expected_current_state_fingerprint: str
    review_acknowledgement_sha256: str | None
    data_root: Path
    run_root: Path
    automation_paths: DailyEodAutomationPaths


@dataclass(frozen=True, slots=True)
class MarketIntelligenceApplyCustodyResult:
    outcome: str
    attempt_id: str
    event: DailyEodRunEvent
    approval_plan: MarketIntelligenceApprovalPlanV1 | None
    active_publication: CompletedMarketIntelligence | None
    reason_code: str

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": CONTRACT_VERSION,
            "outcome": self.outcome,
            "attempt_id": self.attempt_id,
            "event_fingerprint": self.event.event_fingerprint,
            "publication_id": (
                None
                if self.approval_plan is None
                else self.approval_plan.publication_id
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
PlanReader = Callable[[Path], MarketIntelligenceApprovalPlanV1]
InventoryReader = Callable[[Path], str]
ConsumerStateReader = Callable[[Path], str]
ActiveReader = Callable[..., CompletedMarketIntelligence]


def reserve_market_intelligence_apply(
    *,
    config: DailyEodMarketIntelligenceApplyConfig,
    checked_at: datetime,
    expected_automation_plan_fingerprint: str,
    review_acknowledgement: str | None = None,
    clock: Clock = lambda: datetime.now(UTC),
    planner: Planner = plan_daily_eod_automation,
    plan_reader: PlanReader = read_market_intelligence_approval_plan,
    inventory_reader: InventoryReader = inventory_fingerprint,
    consumer_reader: ConsumerStateReader = consumer_state_fingerprint,
) -> MarketIntelligenceApplyCustodyResult:
    """Reserve one explicitly invoked MI Apply without executing it."""

    _validate_config(config)
    checked = _aware_utc(checked_at)
    observed = _aware_utc(clock())
    if observed < checked or observed - checked > MAXIMUM_PLAN_AGE:
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI Apply review is outside the reservation age window"
        )
    if not _is_fingerprint(expected_automation_plan_fingerprint):
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI Apply automation fingerprint is malformed"
        )
    _validate_review_acknowledgement(config, review_acknowledgement)
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        events = journal.read_events()
        if unresolved_started_event(events) is not None:
            raise DailyEodMarketIntelligenceApplyCustodyError(
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
        validate_approved_market_intelligence_freshness(
            root=config.data_root,
            plan=approval,
            checked_at=observed,
            review_acknowledgement=review_acknowledgement,
        )
        if inventory_reader(config.data_root) != config.expected_current_state_fingerprint:
            raise DailyEodMarketIntelligenceApplyCustodyError(
                "Production inventory changed before MI Apply reservation"
            )
        if consumer_reader(config.data_root) != approval.expected_consumer_state_fingerprint:
            raise DailyEodMarketIntelligenceApplyCustodyError(
                "Market Intelligence consumer changed before Apply reservation"
            )
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
            event_type=MARKET_INTELLIGENCE_APPLY_START_EVENT,
            attempt_id=attempt_id,
            observed_at=observed,
            details={
                "custody_contract": CONTRACT_VERSION,
                "operation": "market_intelligence_publication",
                "automation_plan_fingerprint": automation.logical_content_fingerprint,
                "approval_plan_sha256": config.approved_plan_sha256,
                "approval_plan_content_fingerprint": approval.plan_content_fingerprint,
                "publication_id": approval.publication_id,
                "expected_current_state_fingerprint": config.expected_current_state_fingerprint,
                "expected_consumer_state_fingerprint": approval.expected_consumer_state_fingerprint,
                "planned_pointer_fingerprint": approval.planned_pointer_fingerprint,
                "review_acknowledgement_sha256": config.review_acknowledgement_sha256,
                "execution_input_fingerprint": input_fingerprint,
            },
        )
        return MarketIntelligenceApplyCustodyResult(
            outcome="reserved",
            attempt_id=attempt_id,
            event=event,
            approval_plan=approval,
            active_publication=None,
            reason_code="market_intelligence_apply_reserved_but_not_executed",
        )


def record_market_intelligence_apply_success(
    *,
    config: DailyEodMarketIntelligenceApplyConfig,
    clock: Clock = lambda: datetime.now(UTC),
    plan_reader: PlanReader = read_market_intelligence_approval_plan,
    active_reader: ActiveReader = read_active_market_intelligence,
) -> MarketIntelligenceApplyCustodyResult:
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
            event_type="market_intelligence_apply_succeeded",
            attempt_id=pending.attempt_id,
            observed_at=_aware_utc(clock()),
            details={
                "publication_id": approval.publication_id,
                "planned_pointer_fingerprint": approval.planned_pointer_fingerprint,
                "active_pointer_fingerprint": active.pointer.pointer_content_fingerprint,
                "inventory_change_file_count": approval.inventory_change_file_count,
                "reason_code": "market_intelligence_active_state_formally_proven",
            },
        )
        return MarketIntelligenceApplyCustodyResult(
            outcome="succeeded",
            attempt_id=pending.attempt_id,
            event=event,
            approval_plan=approval,
            active_publication=active,
            reason_code="market_intelligence_active_state_formally_proven",
        )


def recover_market_intelligence_apply(
    *,
    config: DailyEodMarketIntelligenceApplyConfig,
    clock: Clock = lambda: datetime.now(UTC),
    plan_reader: PlanReader = read_market_intelligence_approval_plan,
    active_reader: ActiveReader = read_active_market_intelligence,
    inventory_reader: InventoryReader = inventory_fingerprint,
    consumer_reader: ConsumerStateReader = consumer_state_fingerprint,
) -> MarketIntelligenceApplyCustodyResult:
    """Classify an interrupted MI Apply without publishing or linking it."""

    _validate_config(config)
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        pending = _pending_apply(journal.read_events(), config)
        approval: MarketIntelligenceApprovalPlanV1 | None = None
        active: CompletedMarketIntelligence | None = None
        try:
            approval = _read_plan(config, plan_reader)
            active = _read_exact_active(config, approval, active_reader)
        except (
            OSError,
            MarketIntelligencePublicationError,
            DailyEodMarketIntelligenceApplyCustodyError,
        ):
            active = None
        if approval is not None and active is not None:
            event_type = "market_intelligence_apply_recovered_succeeded"
            outcome = "recovered_succeeded"
            reason = "market_intelligence_active_state_formally_reconciled"
        else:
            try:
                approval = approval or _read_plan(config, plan_reader)
                target_absent = not os.path.lexists(Path(approval.target_path))
                inventory_unchanged = (
                    inventory_reader(config.data_root)
                    == config.expected_current_state_fingerprint
                )
                consumer_unchanged = (
                    consumer_reader(config.data_root)
                    == approval.expected_consumer_state_fingerprint
                )
            except (
                OSError,
                MarketIntelligencePublicationError,
                DailyEodMarketIntelligenceApplyCustodyError,
            ):
                target_absent = False
                inventory_unchanged = False
                consumer_unchanged = False
            if target_absent and inventory_unchanged and consumer_unchanged:
                event_type = "market_intelligence_apply_recovered_not_completed"
                outcome = "recovered_not_completed"
                reason = "no_market_intelligence_production_write_detected"
            else:
                event_type = "market_intelligence_apply_recovery_blocked"
                outcome = "recovery_blocked"
                reason = "market_intelligence_apply_state_is_partial_changed_or_ambiguous"
        event = journal.append(
            event_type=event_type,
            attempt_id=pending.attempt_id,
            observed_at=_aware_utc(clock()),
            details={
                "publication_id": pending.details.get("publication_id"),
                "reason_code": reason,
                "apply_executed_by_recovery": False,
            },
        )
        return MarketIntelligenceApplyCustodyResult(
            outcome=outcome,
            attempt_id=pending.attempt_id,
            event=event,
            approval_plan=approval,
            active_publication=active,
            reason_code=reason,
        )


def validate_approved_market_intelligence_freshness(
    *,
    root: Path,
    plan: MarketIntelligenceApprovalPlanV1,
    checked_at: datetime,
    review_acknowledgement: str | None,
) -> None:
    """Recompute the exact normal or review freshness promised by a plan."""

    session_dates = CanonicalEodReadRepository(root).list_session_index()
    if not session_dates:
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "no completed EOD session exists for MI Apply"
        )
    freshness = evaluate_market_data_freshness(
        calendar=ExchangeCalendar(),
        actual_latest_completed_session=session_dates[-1],
        checked_at=_aware_utc(checked_at),
    )
    if plan.activation_allowed:
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
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "current freshness differs from the approved MI plan"
        )


def _read_plan(
    config: DailyEodMarketIntelligenceApplyConfig,
    reader: PlanReader,
) -> MarketIntelligenceApprovalPlanV1:
    try:
        plan = reader(config.approval_plan_path)
        raw = config.approval_plan_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != config.approved_plan_sha256:
            raise DailyEodMarketIntelligenceApplyCustodyError(
                "MI approval plan full-file SHA-256 mismatch"
            )
    except DailyEodMarketIntelligenceApplyCustodyError:
        raise
    except (OSError, MarketIntelligencePublicationError, ValueError) as exc:
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI approval plan failed formal reread"
        ) from exc
    if (
        plan.operation != "market_intelligence_publication"
        or plan.analysis_session != config.target_session
        or Path(plan.data_root) != config.data_root
        or plan.expected_current_state_fingerprint
        != config.expected_current_state_fingerprint
        or Path(plan.target_path)
        != target_path(
            config.data_root,
            config.target_session,
            plan.publication_id,
        )
        or Path(plan.pointer_path) != pointer_path(config.data_root)
    ):
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI approval plan identity mismatch"
        )
    return plan


def _read_exact_active(
    config: DailyEodMarketIntelligenceApplyConfig,
    approval: MarketIntelligenceApprovalPlanV1,
    reader: ActiveReader,
) -> CompletedMarketIntelligence:
    try:
        active = reader(config.data_root, validate_sources=True)
    except (OSError, MarketIntelligencePublicationError) as exc:
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "active MI publication is not formally readable"
        ) from exc
    if (
        active.pointer is None
        or active.pointer.pointer_content_fingerprint
        != approval.planned_pointer_fingerprint
        or active.payload.publication_id != approval.publication_id
        or active.payload.analysis_session != config.target_session
        or active.path != Path(approval.target_path)
        or active.reference.aggregate_sha256 != approval.aggregate_sha256
        or active.reference.payload_sha256 != approval.payload_sha256
    ):
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "active MI publication differs from the approved plan"
        )
    return active


def _require_new_target(plan: MarketIntelligenceApprovalPlanV1) -> None:
    target = Path(plan.target_path)
    if os.path.lexists(target):
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI Apply target is no longer absent"
        )
    if target.parent.exists() and any(
        item.name.startswith(f".{target.name}.staging-")
        for item in target.parent.iterdir()
    ):
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI Apply staging state is already present"
        )


def _pending_apply(
    events: tuple[DailyEodRunEvent, ...],
    config: DailyEodMarketIntelligenceApplyConfig,
) -> DailyEodRunEvent:
    pending = unresolved_started_event(events)
    if (
        pending is None
        or pending.event_type != MARKET_INTELLIGENCE_APPLY_START_EVENT
    ):
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "no unresolved MI Apply exists"
        )
    if pending.details.get("execution_input_fingerprint") != _execution_input_fingerprint(config):
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI Apply inputs differ from reservation"
        )
    return pending


def _validate_reviewable_automation(
    plan: DailyEodAutomationPlan,
    config: DailyEodMarketIntelligenceApplyConfig,
    expected_fingerprint: str,
) -> None:
    if (
        not isinstance(plan, DailyEodAutomationPlan)
        or plan.target_session != config.target_session.isoformat()
        or plan.status is not PlanStatus.ANALYTICS_READY
        or plan.next_action is not NextAction.REVIEW_PUBLICATION
        or plan.logical_content_fingerprint != expected_fingerprint
        or plan.publication_authorized
        or plan.deployment_authorized
        or plan.scheduler_enabled
        or plan.external_request_count != 0
        or plan.production_write_count != 0
    ):
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "automation plan is stale or not MI Apply-reviewable"
        )


def _validate_review_acknowledgement(
    config: DailyEodMarketIntelligenceApplyConfig,
    acknowledgement: str | None,
) -> None:
    actual = (
        None
        if acknowledgement is None
        else hashlib.sha256(acknowledgement.encode("utf-8")).hexdigest()
    )
    if actual != config.review_acknowledgement_sha256:
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI review acknowledgement differs from the approved invocation"
        )


def _validate_config(config: DailyEodMarketIntelligenceApplyConfig) -> None:
    if (
        not config.data_root.is_absolute()
        or not config.run_root.is_absolute()
        or _is_within(config.run_root, config.data_root)
        or _is_within(config.run_root, Path("/data"))
    ):
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI Apply roots are invalid"
        )
    if (
        not config.approval_plan_path.is_absolute()
        or config.approval_plan_path.parent != Path("/tmp")
        or config.approval_plan_path.name.startswith(".")
    ):
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI Apply approval path is invalid"
        )
    if (
        not _is_fingerprint(config.approved_plan_sha256)
        or not _is_fingerprint(config.expected_current_state_fingerprint)
        or (
            config.review_acknowledgement_sha256 is not None
            and not _is_fingerprint(config.review_acknowledgement_sha256)
        )
    ):
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI Apply fingerprints are malformed"
        )


def _execution_input_fingerprint(
    config: DailyEodMarketIntelligenceApplyConfig,
) -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "target_session": config.target_session.isoformat(),
            "approval_plan_path": str(config.approval_plan_path),
            "approved_plan_sha256": config.approved_plan_sha256,
            "expected_current_state_fingerprint": config.expected_current_state_fingerprint,
            "review_acknowledgement_sha256": config.review_acknowledgement_sha256,
            "data_root": str(config.data_root),
            "run_root": str(config.run_root),
            "automation_paths": {
                key: str(value)
                for key, value in asdict(config.automation_paths).items()
            },
        }
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodMarketIntelligenceApplyCustodyError(
            "MI Apply timestamps must be timezone-aware"
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
