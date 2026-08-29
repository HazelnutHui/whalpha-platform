"""Route exactly one unresolved daily EOD journal event to no-replay recovery."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Callable

from tip_api.services.daily_eod_acquisition_custody import (
    AcquisitionCustodyResult,
    DailyEodAcquisitionConfig,
    recover_acquisition_attempt,
)
from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPlan,
    NextAction,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_canonical_apply_custody import (
    CanonicalApplyCustodyResult,
    DailyEodCanonicalApplyConfig,
    recover_canonical_apply,
)
from tip_api.services.daily_eod_coordinator import (
    RecoveryTransitionContext,
    RecoveryTransitionEvidence,
)
from tip_api.services.daily_eod_dashboard_snapshot_apply_custody import (
    DashboardSnapshotApplyCustodyResult,
    DailyEodDashboardSnapshotApplyConfig,
    recover_dashboard_snapshot_apply,
)
from tip_api.services.daily_eod_executor import (
    OFFLINE_ACTIONS,
    DailyEodExecutionConfig,
    DailyEodRecoveryResult,
    recover_daily_eod_action,
)
from tip_api.services.daily_eod_market_intelligence_apply_custody import (
    DailyEodMarketIntelligenceApplyConfig,
    MarketIntelligenceApplyCustodyResult,
    recover_market_intelligence_apply,
)
from tip_api.services.daily_eod_readiness import ACQUISITION_ACTIONS
from tip_api.services.daily_eod_run_journal import (
    ACQUISITION_START_EVENT,
    CANONICAL_APPLY_START_EVENT,
    DASHBOARD_SNAPSHOT_APPLY_START_EVENT,
    MARKET_INTELLIGENCE_APPLY_START_EVENT,
    START_EVENT,
    DailyEodRunEvent,
    locked_daily_eod_run_journal,
    unresolved_started_event,
)


CONTRACT_VERSION = "daily-eod-one-transition-recovery/1.2"


class DailyEodRecoveryRouterError(RuntimeError):
    """Raised when one unresolved event cannot be routed without ambiguity."""


Clock = Callable[[], datetime]
Planner = Callable[..., DailyEodAutomationPlan]
JournalReader = Callable[[Path, date], tuple[DailyEodRunEvent, ...]]
AcquisitionRecoverer = Callable[..., AcquisitionCustodyResult]
ApplyRecoverer = Callable[..., CanonicalApplyCustodyResult]
MarketIntelligenceApplyRecoverer = Callable[..., MarketIntelligenceApplyCustodyResult]
DashboardSnapshotApplyRecoverer = Callable[..., DashboardSnapshotApplyCustodyResult]
OfflineRecoverer = Callable[..., DailyEodRecoveryResult]


def recover_one_daily_eod_transition(
    context: RecoveryTransitionContext,
    *,
    clock: Clock = lambda: datetime.now(UTC),
    planner: Planner = plan_daily_eod_automation,
    journal_reader: JournalReader | None = None,
    acquisition_recoverer: AcquisitionRecoverer = recover_acquisition_attempt,
    apply_recoverer: ApplyRecoverer = recover_canonical_apply,
    market_intelligence_apply_recoverer: MarketIntelligenceApplyRecoverer = (
        recover_market_intelligence_apply
    ),
    dashboard_snapshot_apply_recoverer: DashboardSnapshotApplyRecoverer = (
        recover_dashboard_snapshot_apply
    ),
    offline_recoverer: OfflineRecoverer = recover_daily_eod_action,
) -> RecoveryTransitionEvidence:
    """Recover one exact pending family; never fetch, apply, or replay an action."""

    if not isinstance(context, RecoveryTransitionContext):
        raise DailyEodRecoveryRouterError("recovery context is invalid")
    pending = context.pending_event
    config = context.coordinator
    if (
        pending.target_session != config.target_session.isoformat()
        or context.automation_plan.target_session != pending.target_session
        or not _is_fingerprint(pending.event_fingerprint)
    ):
        raise DailyEodRecoveryRouterError("pending event identity is inconsistent")
    events = (journal_reader or _read_journal_events)(
        config.run_root,
        config.target_session,
    )
    current = unresolved_started_event(events)
    if current is None or current != pending:
        raise DailyEodRecoveryRouterError(
            "pending event changed before recovery routing"
        )

    if pending.event_type == ACQUISITION_START_EVENT:
        _require_action(context.recovery_action, "recover_acquisition_attempt")
        action = _acquisition_action(pending)
        result = acquisition_recoverer(
            config=DailyEodAcquisitionConfig(
                target_session=config.target_session,
                latest_canonical_session=config.latest_canonical_session,
                acquisition_action=action,
                package_path=config.package_path,
                run_root=config.run_root,
            ),
            clock=clock,
        )
        return _evidence(
            context,
            result=result,
            result_type=AcquisitionCustodyResult,
            outcome_events={
                "recovered_package_ready": "acquisition_recovered_package_ready",
                "recovered_not_completed": "acquisition_recovered_not_completed",
                "recovery_blocked": "acquisition_recovery_blocked",
            },
        )

    if pending.event_type == CANONICAL_APPLY_START_EVENT:
        _require_action(context.recovery_action, "recover_canonical_apply")
        action = _acquisition_action(pending)
        approved_plan_sha256 = _detail_fingerprint(
            pending,
            "approval_plan_sha256",
        )
        expected_state = _detail_fingerprint(
            pending,
            "expected_current_state_fingerprint",
        )
        expected_operation = (
            "apply_identity"
            if action is NextAction.PREPARE_IDENTITY_CATCHUP
            else "apply_eod"
        )
        if pending.details.get("operation") != expected_operation:
            raise DailyEodRecoveryRouterError(
                "pending canonical Apply operation is inconsistent"
            )
        result = apply_recoverer(
            config=DailyEodCanonicalApplyConfig(
                target_session=config.target_session,
                latest_canonical_session=config.latest_canonical_session,
                acquisition_action=action,
                package_path=config.package_path,
                approval_plan_path=config.approval_plan_path,
                approved_plan_sha256=approved_plan_sha256,
                expected_current_state_fingerprint=expected_state,
                data_root=config.paths.data_root,
                run_root=config.run_root,
                automation_paths=config.paths,
            ),
            clock=clock,
            planner=planner,
        )
        return _evidence(
            context,
            result=result,
            result_type=CanonicalApplyCustodyResult,
            outcome_events={
                "recovered_succeeded": "canonical_apply_recovered_succeeded",
                "recovered_not_completed": "canonical_apply_recovered_not_completed",
                "recovery_blocked": "canonical_apply_recovery_blocked",
            },
        )

    if pending.event_type == START_EVENT:
        _require_action(context.recovery_action, "recover_offline_action")
        action = _offline_action(pending)
        result = offline_recoverer(
            config=DailyEodExecutionConfig(
                target_session=config.target_session,
                paths=config.paths,
                run_root=config.run_root,
                panel_cache_root=config.panel_cache_root,
                candidate_work_dir=config.candidate_work_dir,
                publication_created_at=config.publication_created_at,
                publication_expected_current_state_fingerprint=(
                    config.publication_expected_current_state_fingerprint
                ),
                snapshot_generated_at=config.snapshot_generated_at,
                bundle_built_at=config.bundle_built_at,
            ),
            planner=planner,
        )
        if (
            not isinstance(result, DailyEodRecoveryResult)
            or result.action is not action
        ):
            raise DailyEodRecoveryRouterError(
                "offline recovery result action is inconsistent"
            )
        return _evidence(
            context,
            result=result,
            result_type=DailyEodRecoveryResult,
            outcome_events={
                "recovered_succeeded": "action_recovered_succeeded",
                "recovered_not_completed": "action_recovered_not_completed",
                "recovery_blocked": "action_recovery_blocked",
            },
        )

    if pending.event_type == MARKET_INTELLIGENCE_APPLY_START_EVENT:
        _require_action(
            context.recovery_action,
            "recover_market_intelligence_apply",
        )
        if pending.details.get("operation") != "market_intelligence_publication":
            raise DailyEodRecoveryRouterError(
                "pending MI Apply operation is inconsistent"
            )
        result = market_intelligence_apply_recoverer(
            config=DailyEodMarketIntelligenceApplyConfig(
                target_session=config.target_session,
                approval_plan_path=(
                    config.paths.market_intelligence_approval_plan
                ),
                approved_plan_sha256=_detail_fingerprint(
                    pending,
                    "approval_plan_sha256",
                ),
                expected_current_state_fingerprint=_detail_fingerprint(
                    pending,
                    "expected_current_state_fingerprint",
                ),
                review_acknowledgement_sha256=_optional_detail_fingerprint(
                    pending,
                    "review_acknowledgement_sha256",
                ),
                data_root=config.paths.data_root,
                run_root=config.run_root,
                automation_paths=config.paths,
            ),
            clock=clock,
        )
        return _evidence(
            context,
            result=result,
            result_type=MarketIntelligenceApplyCustodyResult,
            outcome_events={
                "recovered_succeeded": (
                    "market_intelligence_apply_recovered_succeeded"
                ),
                "recovered_not_completed": (
                    "market_intelligence_apply_recovered_not_completed"
                ),
                "recovery_blocked": (
                    "market_intelligence_apply_recovery_blocked"
                ),
            },
        )

    if pending.event_type == DASHBOARD_SNAPSHOT_APPLY_START_EVENT:
        _require_action(
            context.recovery_action,
            "recover_dashboard_snapshot_apply",
        )
        if pending.details.get("operation") != "dashboard_snapshot_publication":
            raise DailyEodRecoveryRouterError(
                "pending Snapshot Apply operation is inconsistent"
            )
        result = dashboard_snapshot_apply_recoverer(
            config=DailyEodDashboardSnapshotApplyConfig(
                target_session=config.target_session,
                approval_plan_path=config.paths.snapshot_approval_plan,
                approved_plan_sha256=_detail_fingerprint(
                    pending,
                    "approval_plan_sha256",
                ),
                expected_current_state_fingerprint=_detail_fingerprint(
                    pending,
                    "expected_current_state_fingerprint",
                ),
                review_acknowledgement_sha256=_optional_detail_fingerprint(
                    pending,
                    "review_acknowledgement_sha256",
                ),
                data_root=config.paths.data_root,
                legacy_root=_snapshot_legacy_root(),
                run_root=config.run_root,
                automation_paths=config.paths,
            ),
            clock=clock,
        )
        return _evidence(
            context,
            result=result,
            result_type=DashboardSnapshotApplyCustodyResult,
            outcome_events={
                "recovered_succeeded": (
                    "dashboard_snapshot_apply_recovered_succeeded"
                ),
                "recovered_not_completed": (
                    "dashboard_snapshot_apply_recovered_not_completed"
                ),
                "recovery_blocked": (
                    "dashboard_snapshot_apply_recovery_blocked"
                ),
            },
        )

    raise DailyEodRecoveryRouterError("pending event family is unsupported")


def _read_journal_events(
    run_root: Path,
    target_session: date,
) -> tuple[DailyEodRunEvent, ...]:
    with locked_daily_eod_run_journal(
        run_root=run_root,
        target_session=target_session,
    ) as journal:
        return journal.read_events()


def _snapshot_legacy_root() -> Path:
    return Path(__file__).resolve().parents[5] / "build/private-dashboard"


def _acquisition_action(pending: DailyEodRunEvent) -> NextAction:
    try:
        action = NextAction(str(pending.details["acquisition_action"]))
    except (KeyError, ValueError) as exc:
        raise DailyEodRecoveryRouterError(
            "pending acquisition action is malformed"
        ) from exc
    if action not in ACQUISITION_ACTIONS:
        raise DailyEodRecoveryRouterError(
            "pending acquisition action is unsupported"
        )
    return action


def _detail_fingerprint(pending: DailyEodRunEvent, name: str) -> str:
    value = pending.details.get(name)
    if not _is_fingerprint(value):
        raise DailyEodRecoveryRouterError(
            f"pending Apply {name} is malformed"
        )
    return value


def _optional_detail_fingerprint(
    pending: DailyEodRunEvent,
    name: str,
) -> str | None:
    value = pending.details.get(name)
    if value is not None and not _is_fingerprint(value):
        raise DailyEodRecoveryRouterError(
            f"pending publication Apply {name} is malformed"
        )
    return value


def _offline_action(pending: DailyEodRunEvent) -> NextAction:
    try:
        action = NextAction(str(pending.details["action"]))
    except (KeyError, ValueError) as exc:
        raise DailyEodRecoveryRouterError(
            "pending offline action is malformed"
        ) from exc
    if action not in OFFLINE_ACTIONS:
        raise DailyEodRecoveryRouterError("pending offline action is unsupported")
    return action


def _require_action(actual: str, expected: str) -> None:
    if actual != expected:
        raise DailyEodRecoveryRouterError("recovery action differs from event family")


def _evidence(
    context: RecoveryTransitionContext,
    *,
    result: object,
    result_type: type[object],
    outcome_events: dict[str, str],
) -> RecoveryTransitionEvidence:
    event = getattr(result, "event", None)
    outcome = getattr(result, "outcome", None)
    attempt_id = getattr(result, "attempt_id", None)
    reason_code = getattr(result, "reason_code", None)
    if (
        not isinstance(result, result_type)
        or not isinstance(event, DailyEodRunEvent)
        or outcome not in outcome_events
        or event.event_type != outcome_events[outcome]
        or event.target_session != context.pending_event.target_session
        or attempt_id != context.pending_event.attempt_id
        or event.attempt_id != context.pending_event.attempt_id
        or not _is_fingerprint(event.event_fingerprint)
        or not isinstance(reason_code, str)
        or not reason_code
    ):
        raise DailyEodRecoveryRouterError("recovery result is inconsistent")
    return RecoveryTransitionEvidence(
        recovery_action=context.recovery_action,
        target_session=context.pending_event.target_session,
        pending_event_fingerprint=context.pending_event.event_fingerprint,
        outcome=outcome,
        event_fingerprint=event.event_fingerprint,
        external_request_count=0,
        production_write_count=0,
        action_replayed=False,
        reason_code=reason_code,
    )


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
