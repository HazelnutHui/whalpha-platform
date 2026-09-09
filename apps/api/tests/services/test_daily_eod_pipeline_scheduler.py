from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tip_api.services.daily_eod_automation import (
    CONTRACT_VERSION as AUTOMATION_CONTRACT_VERSION,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services import daily_eod_pipeline_scheduler as scheduler
from tip_api.services import daily_universe_membership_sidecar as sidecar


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


def _sidecar_plan(primary: DailyEodAutomationPlan):
    return sidecar._build_plan(
        checked_at=CHECKED_AT,
        target_session=date(2026, 8, 28),
        primary=primary,
        catalog_as_of_date=date(2026, 8, 14),
        candidate_partition=(
            Path("/tmp/universe-membership-candidate")
            / "market-data/universe-membership/schema_version=1"
            / f"methodology_version={sidecar.METHODOLOGY_VERSION}"
            / "session_date=2026-08-28"
        ),
        status=sidecar.MembershipSidecarStatus.WAITING,
        next_action=sidecar.MembershipSidecarAction.WAIT_FOR_PRIMARY_PIPELINE,
        reasons=("primary_canonical_writes_may_remain",),
        catalog_fingerprint="c" * 64,
        candidate_status="already_present",
        record_count=100,
        membership_fingerprint="a" * 64,
        point_in_time_eligibility="signal_eligible",
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


def test_membership_sidecar_is_projected_without_changing_primary_decision() -> None:
    primary = _automation_plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    without_sidecar = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=CHECKED_AT,
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
        latest_pipeline_plan=primary,
    )
    membership = _sidecar_plan(primary)
    with_sidecar = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=CHECKED_AT,
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
        latest_pipeline_plan=primary,
        membership_sidecar_plan=membership,
    )

    assert with_sidecar.status is without_sidecar.status
    assert with_sidecar.phase is without_sidecar.phase
    assert with_sidecar.next_action is without_sidecar.next_action
    assert with_sidecar.coordinator_invocation_scope == (
        without_sidecar.coordinator_invocation_scope
    )
    assert with_sidecar.research_sidecar_status == "waiting"
    assert with_sidecar.research_sidecar_next_action == "wait_for_primary_pipeline"
    assert with_sidecar.research_sidecar_plan_fingerprint == (
        membership.logical_content_fingerprint
    )
    assert with_sidecar.research_sidecar_website_pipeline_blocked is False


def test_membership_sidecar_must_bind_exact_primary_plan() -> None:
    primary = _automation_plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    different_primary = _automation_plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1B_INCREMENTAL,
    )

    with pytest.raises(scheduler.DailyEodPipelineSchedulerError, match="differs"):
        scheduler.plan_daily_eod_pipeline_wake(
            checked_at=CHECKED_AT,
            completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
            latest_pipeline_plan=primary,
            membership_sidecar_plan=_sidecar_plan(different_primary),
        )


def test_recomputed_website_blocking_projection_is_rejected() -> None:
    primary = _automation_plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    plan = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=CHECKED_AT,
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
        latest_pipeline_plan=primary,
        membership_sidecar_plan=_sidecar_plan(primary),
    )
    tampered = replace(plan, research_sidecar_website_pipeline_blocked=True)
    logical = asdict(tampered)
    logical.pop("logical_content_fingerprint")
    tampered = replace(
        tampered,
        logical_content_fingerprint=scheduler._fingerprint(
            scheduler._jsonable(logical)
        ),
    )

    with pytest.raises(scheduler.DailyEodPipelineSchedulerError, match="authority"):
        scheduler.verify_daily_eod_pipeline_wake_plan(tampered)
