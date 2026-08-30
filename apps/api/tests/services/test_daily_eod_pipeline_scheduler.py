from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, date, datetime

import pytest

from tip_api.services.daily_eod_automation import (
    CONTRACT_VERSION as AUTOMATION_CONTRACT_VERSION,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services import daily_eod_pipeline_scheduler as scheduler


CHECKED_AT = datetime(2026, 8, 29, 12, tzinfo=UTC)


def _automation_plan(
    status: PlanStatus,
    action: NextAction,
    *,
    reasons: tuple[str, ...] = ("test_reason",),
) -> DailyEodAutomationPlan:
    plan = DailyEodAutomationPlan(
        contract_version=AUTOMATION_CONTRACT_VERSION,
        target_session="2026-08-28",
        prior_session="2026-08-27",
        status=status,
        next_action=action,
        reason_codes=reasons,
        observations=(),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint="",
    )
    logical = asdict(plan)
    logical.pop("logical_content_fingerprint")
    return replace(
        plan,
        logical_content_fingerprint=scheduler._fingerprint(
            scheduler._jsonable(logical)
        ),
    )


def test_missing_canonical_session_keeps_data_stabilization_wait() -> None:
    plan = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=datetime(2026, 8, 28, 20, 10, tzinfo=UTC),
        completed_sessions=(date(2026, 8, 27),),
    )

    assert plan.status is scheduler.PipelineWakeStatus.WAITING
    assert plan.phase is scheduler.PipelineWakePhase.CANONICAL_DATA
    assert plan.next_action is scheduler.PipelineWakeAction.WAIT
    assert plan.target_session == "2026-08-28"
    assert plan.next_check_at == "2026-08-28T20:30:00+00:00"


def test_missing_canonical_session_proposes_only_one_data_transition() -> None:
    plan = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=datetime(2026, 8, 28, 21, tzinfo=UTC),
        completed_sessions=(date(2026, 8, 27),),
        review_enabled_candidate=True,
    )

    assert plan.status is scheduler.PipelineWakeStatus.READY_FOR_WAKE
    assert plan.next_action is scheduler.PipelineWakeAction.INVOKE_ONE_DATA_TRANSITION
    assert plan.coordinator_invocation_scope == "data"
    assert plan.coordinator_invocation_limit == 1
    assert plan.coordinator_invocation_count == 0


def test_current_eod_continues_latest_offline_pipeline() -> None:
    plan = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=CHECKED_AT,
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
        latest_pipeline_plan=_automation_plan(
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_PHASE1A,
        ),
    )

    assert plan.status is scheduler.PipelineWakeStatus.READY_FOR_WAKE
    assert plan.phase is scheduler.PipelineWakePhase.OFFLINE_PIPELINE
    assert plan.target_session == "2026-08-28"
    assert plan.pipeline_next_action == "calculate_phase1a"
    assert plan.next_action is scheduler.PipelineWakeAction.REVIEW_ONE_OFFLINE_TRANSITION
    assert plan.next_check_at == CHECKED_AT.isoformat()


def test_enabled_candidate_changes_only_offline_proposal() -> None:
    plan = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=CHECKED_AT,
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
        latest_pipeline_plan=_automation_plan(
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_STRATEGY_CHANNELS,
        ),
        review_enabled_candidate=True,
    )

    assert plan.next_action is scheduler.PipelineWakeAction.INVOKE_ONE_OFFLINE_TRANSITION
    assert plan.scheduler_candidate_enabled is True
    assert plan.scheduler_installation_performed is False
    assert plan.external_request_count == 0
    assert plan.filesystem_write_count == 0
    assert plan.production_write_count == 0


@pytest.mark.parametrize(
    "action",
    (
        NextAction.REVIEW_PUBLICATION,
        NextAction.REVIEW_SNAPSHOT_PUBLICATION,
        NextAction.REVIEW_BUNDLE_DEPLOYMENT,
    ),
)
def test_manual_boundaries_never_become_invocations(action: NextAction) -> None:
    plan = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=CHECKED_AT,
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
        latest_pipeline_plan=_automation_plan(PlanStatus.ANALYTICS_READY, action),
        review_enabled_candidate=True,
    )

    assert plan.status is scheduler.PipelineWakeStatus.REVIEW_REQUIRED
    assert plan.phase is scheduler.PipelineWakePhase.MANUAL_REVIEW
    assert plan.next_action is scheduler.PipelineWakeAction.REVIEW_MANUAL_BOUNDARY
    assert plan.coordinator_invocation_scope == "none"


def test_current_canonical_input_conflict_blocks() -> None:
    plan = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=CHECKED_AT,
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
        latest_pipeline_plan=_automation_plan(
            PlanStatus.WAITING_FOR_AUTHORIZED_INPUT,
            NextAction.PREPARE_IDENTITY_CATCHUP,
            reasons=("identity_missing",),
        ),
    )

    assert plan.status is scheduler.PipelineWakeStatus.BLOCKED
    assert plan.next_action is scheduler.PipelineWakeAction.OPERATOR_DIAGNOSIS
    assert "canonical_eod_pipeline_state_conflict" in plan.reason_codes


def test_current_canonical_state_requires_exact_pipeline_plan() -> None:
    with pytest.raises(scheduler.DailyEodPipelineSchedulerError, match="requires"):
        scheduler.plan_daily_eod_pipeline_wake(
            checked_at=CHECKED_AT,
            completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
        )


def test_tampered_automation_plan_is_rejected() -> None:
    plan = _automation_plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    with pytest.raises(scheduler.DailyEodPipelineSchedulerError, match="boundary"):
        scheduler.plan_daily_eod_pipeline_wake(
            checked_at=CHECKED_AT,
            completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
            latest_pipeline_plan=replace(
                plan,
                next_action=NextAction.CALCULATE_CANDIDATE_DAILY,
            ),
        )


def test_pipeline_plan_fingerprint_tamper_is_rejected() -> None:
    plan = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=CHECKED_AT,
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
        latest_pipeline_plan=_automation_plan(
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_PHASE1A,
        ),
    )

    with pytest.raises(scheduler.DailyEodPipelineSchedulerError, match="fingerprint"):
        scheduler.verify_daily_eod_pipeline_wake_plan(
            replace(plan, target_session="2026-08-27")
        )
