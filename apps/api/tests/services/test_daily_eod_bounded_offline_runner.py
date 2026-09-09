from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from tip_api.services import daily_eod_bounded_offline_runner as runner
from tip_api.services import daily_eod_run_journal as journal
from tip_api.services.daily_eod_automation import (
    CONTRACT_VERSION as AUTOMATION_CONTRACT_VERSION,
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_executor import (
    DailyEodExecutionConfig,
    DailyEodExecutionResult,
    StageExecutionEvidence,
)
from tip_api.services.daily_eod_run_journal import JOURNAL_CONTRACT, DailyEodRunEvent


TARGET = date(2026, 9, 8)
STARTED = datetime(2026, 9, 9, 1, tzinfo=UTC)


def _paths() -> DailyEodAutomationPaths:
    root = Path("/fixture-workspace/daily-eod/sessions/session_date=2026-09-08")
    prior = Path("/fixture-workspace/daily-eod/sessions/session_date=2026-09-04")
    return DailyEodAutomationPaths(
        data_root=Path("/fixture-data"),
        phase1a_audit=root / "market-regime-phase1a",
        prior_phase1b_audit=prior / "market-regime-phase1b",
        phase1b_audit=root / "market-regime-phase1b",
        prior_candidate_audit=prior / "opportunity-candidate",
        candidate_audit=root / "opportunity-candidate",
        entry_geometry_audit=root / "entry-geometry",
        phase2_audit=root / "etf-relationships",
        preview_bundle=root / "market-preview",
        strategy_channel_audit=root / "strategy-channels",
        market_intelligence_output_root=root / "market-intelligence",
        market_intelligence_approval_plan=root / "market-intelligence-plan.json",
        snapshot_output_root=root / "dashboard-snapshot",
        snapshot_approval_plan=root / "dashboard-snapshot-plan.json",
        serving_bundle_root=root / "serving-bundle",
    )


def _config(*, publication_fingerprint: str | None = "f" * 64):
    paths = _paths()
    return DailyEodExecutionConfig(
        target_session=TARGET,
        paths=paths,
        run_root=Path("/fixture-runs"),
        panel_cache_root=Path("/fixture-workspace/daily-eod/cache/panels"),
        candidate_work_dir=paths.candidate_audit.with_name("candidate-work"),
        publication_expected_current_state_fingerprint=publication_fingerprint,
    )


def _plan(status: PlanStatus, action: NextAction) -> DailyEodAutomationPlan:
    logical = {
        "contract_version": AUTOMATION_CONTRACT_VERSION,
        "target_session": TARGET.isoformat(),
        "prior_session": "2026-09-04",
        "status": status.value,
        "next_action": action.value,
        "reason_codes": ["fixture"],
        "observations": [],
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_enabled": False,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    return DailyEodAutomationPlan(
        contract_version=AUTOMATION_CONTRACT_VERSION,
        target_session=TARGET.isoformat(),
        prior_session="2026-09-04",
        status=status,
        next_action=action,
        reason_codes=("fixture",),
        observations=(),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=runner._fingerprint(logical),
    )


def _event(
    sequence: int,
    *,
    event_type: str = "action_succeeded",
) -> DailyEodRunEvent:
    observed_at = (STARTED + timedelta(seconds=sequence)).isoformat()
    attempt_id = f"{sequence:x}".rjust(64, "1")
    logical = {
        "contract_version": JOURNAL_CONTRACT,
        "sequence": sequence,
        "event_type": event_type,
        "target_session": TARGET.isoformat(),
        "observed_at": observed_at,
        "attempt_id": attempt_id,
        "previous_event_fingerprint": None,
        "details": {},
    }
    return DailyEodRunEvent(
        sequence=sequence,
        event_type=event_type,
        target_session=TARGET.isoformat(),
        observed_at=observed_at,
        attempt_id=attempt_id,
        previous_event_fingerprint=None,
        details={},
        event_fingerprint=journal._fingerprint(logical),
    )


def _stage(action: NextAction) -> StageExecutionEvidence:
    return StageExecutionEvidence(
        action=action,
        output_path="/fixture-output",
        summary_sha256="e" * 64,
        summary_bytes=1,
    )


class _Clock:
    def __init__(self) -> None:
        self.value = STARTED

    def __call__(self) -> datetime:
        self.value += timedelta(seconds=1)
        return self.value


def test_runner_chains_successful_actions_and_stops_at_manual_boundary() -> None:
    phase1a = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    phase1b = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1B_INCREMENTAL,
    )
    review = _plan(PlanStatus.ANALYTICS_READY, NextAction.REVIEW_PUBLICATION)
    plans = [phase1a, phase1b, review]
    planner_calls = 0

    def planner(**kwargs) -> DailyEodAutomationPlan:
        nonlocal planner_calls
        del kwargs
        plan = plans[min(planner_calls, 2)]
        planner_calls += 1
        return plan

    executor_calls: list[NextAction] = []

    def executor(**kwargs) -> DailyEodExecutionResult:
        planned = kwargs["expected_action"]
        executor_calls.append(planned)
        before = phase1a if len(executor_calls) == 1 else phase1b
        after = phase1b if len(executor_calls) == 1 else review
        assert kwargs["expected_plan_fingerprint"] == before.logical_content_fingerprint
        return DailyEodExecutionResult(
            outcome="succeeded",
            action=planned,
            attempt_id=_event(len(executor_calls)).attempt_id,
            event=_event(len(executor_calls)),
            pre_plan=before,
            post_plan=after,
            stage_evidence=_stage(planned),
            reason_code="offline_action_completed_and_replanned",
        )

    result = runner.run_bounded_daily_eod_offline(
        config=_config(),
        started_at=STARTED,
        execute=True,
        planner=planner,
        executor=executor,
        clock=_Clock(),
    )

    assert result.status is runner.BoundedOfflineRunStatus.BOUNDARY_REACHED
    assert executor_calls == [
        NextAction.CALCULATE_PHASE1A,
        NextAction.CALCULATE_PHASE1B_INCREMENTAL,
    ]
    assert result.action_attempt_count == 2
    assert result.action_success_count == 2
    assert result.final_next_action == NextAction.REVIEW_PUBLICATION.value
    runner.verify_daily_eod_bounded_offline_run_result(result)


def test_default_review_invokes_no_action() -> None:
    plan = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    calls = 0

    def executor(**kwargs):
        nonlocal calls
        del kwargs
        calls += 1

    result = runner.run_bounded_daily_eod_offline(
        config=_config(),
        started_at=STARTED,
        planner=lambda **kwargs: plan,
        executor=executor,
        clock=_Clock(),
    )

    assert result.status is runner.BoundedOfflineRunStatus.REVIEW_READY
    assert result.action_attempt_count == 0
    assert calls == 0


def test_runner_stops_after_known_failure_without_retry() -> None:
    plan = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    calls = 0

    def executor(**kwargs) -> DailyEodExecutionResult:
        nonlocal calls
        calls += 1
        return DailyEodExecutionResult(
            outcome="failed",
            action=plan.next_action,
            attempt_id=_event(1, event_type="action_failed").attempt_id,
            event=_event(1, event_type="action_failed"),
            pre_plan=plan,
            post_plan=None,
            stage_evidence=None,
            reason_code="offline_action_raised",
        )

    result = runner.run_bounded_daily_eod_offline(
        config=_config(),
        started_at=STARTED,
        execute=True,
        planner=lambda **kwargs: plan,
        executor=executor,
        clock=_Clock(),
    )

    assert result.status is runner.BoundedOfflineRunStatus.ACTION_FAILED
    assert result.action_attempt_count == 1
    assert result.action_success_count == 0
    assert calls == 1
    assert "automatic_retry_prohibited" in result.reason_codes


def test_runner_stops_at_action_budget_after_known_progress() -> None:
    first = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    second = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1B_INCREMENTAL,
    )
    planner_calls = 0

    def planner(**kwargs) -> DailyEodAutomationPlan:
        nonlocal planner_calls
        del kwargs
        planner_calls += 1
        return first if planner_calls == 1 else second

    result = runner.run_bounded_daily_eod_offline(
        config=_config(),
        started_at=STARTED,
        execute=True,
        maximum_actions=1,
        planner=planner,
        executor=lambda **kwargs: DailyEodExecutionResult(
            outcome="succeeded",
            action=first.next_action,
            attempt_id=_event(1).attempt_id,
            event=_event(1),
            pre_plan=first,
            post_plan=second,
            stage_evidence=_stage(first.next_action),
            reason_code="offline_action_completed_and_replanned",
        ),
        clock=_Clock(),
    )

    assert result.status is runner.BoundedOfflineRunStatus.BUDGET_EXHAUSTED
    assert result.action_attempt_count == 1
    assert result.final_next_action == second.next_action.value


def test_market_intelligence_plan_requires_explicit_current_state() -> None:
    plan = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN,
    )
    result = runner.run_bounded_daily_eod_offline(
        config=_config(publication_fingerprint=None),
        started_at=STARTED,
        execute=True,
        planner=lambda **kwargs: plan,
        executor=lambda **kwargs: pytest.fail("executor must not be called"),
        clock=_Clock(),
    )

    assert result.status is runner.BoundedOfflineRunStatus.BOUNDARY_REACHED
    assert result.reason_codes == (
        "publication_current_state_fingerprint_required",
    )


def test_executor_exception_never_retries() -> None:
    plan = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    calls = 0

    def executor(**kwargs):
        nonlocal calls
        del kwargs
        calls += 1
        raise RuntimeError("ambiguous")

    with pytest.raises(
        runner.DailyEodBoundedOfflineRunnerError,
        match="continuation is prohibited",
    ):
        runner.run_bounded_daily_eod_offline(
            config=_config(),
            started_at=STARTED,
            execute=True,
            planner=lambda **kwargs: plan,
            executor=executor,
            clock=_Clock(),
        )
    assert calls == 1


def test_fresh_plan_mismatch_stops_before_a_later_action() -> None:
    first = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    expected_second = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1B_INCREMENTAL,
    )
    mismatched_second = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_CANDIDATE_DAILY,
    )
    planner_calls = 0
    executor_calls = 0

    def planner(**kwargs) -> DailyEodAutomationPlan:
        nonlocal planner_calls
        del kwargs
        planner_calls += 1
        if planner_calls == 1:
            return first
        return mismatched_second

    def executor(**kwargs) -> DailyEodExecutionResult:
        nonlocal executor_calls
        del kwargs
        executor_calls += 1
        return DailyEodExecutionResult(
            outcome="succeeded",
            action=first.next_action,
            attempt_id=_event(1).attempt_id,
            event=_event(1),
            pre_plan=first,
            post_plan=expected_second,
            stage_evidence=_stage(first.next_action),
            reason_code="offline_action_completed_and_replanned",
        )

    with pytest.raises(
        runner.DailyEodBoundedOfflineRunnerError,
        match="does not reproduce",
    ):
        runner.run_bounded_daily_eod_offline(
            config=_config(),
            started_at=STARTED,
            execute=True,
            planner=planner,
            executor=executor,
            clock=_Clock(),
        )

    assert executor_calls == 1


def test_result_tampering_is_rejected() -> None:
    plan = _plan(PlanStatus.ANALYTICS_READY, NextAction.REVIEW_PUBLICATION)
    result = runner.run_bounded_daily_eod_offline(
        config=_config(),
        started_at=STARTED,
        planner=lambda **kwargs: plan,
        clock=_Clock(),
    )

    with pytest.raises(
        runner.DailyEodBoundedOfflineRunnerError,
        match="content or authority",
    ):
        runner.verify_daily_eod_bounded_offline_run_result(
            replace(result, publication_authorized=True)
        )


def test_semantically_conflicting_refingerprinted_result_is_rejected() -> None:
    plan = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    result = runner.run_bounded_daily_eod_offline(
        config=_config(),
        started_at=STARTED,
        planner=lambda **kwargs: plan,
        clock=_Clock(),
    )
    tampered = replace(
        result,
        status=runner.BoundedOfflineRunStatus.BLOCKED,
        logical_content_fingerprint="",
    )
    logical = asdict(tampered)
    logical.pop("logical_content_fingerprint")
    tampered = replace(
        tampered,
        logical_content_fingerprint=runner._fingerprint(runner._jsonable(logical)),
    )

    with pytest.raises(
        runner.DailyEodBoundedOfflineRunnerError,
        match="status conflicts",
    ):
        runner.verify_daily_eod_bounded_offline_run_result(tampered)


def test_success_without_stage_evidence_is_rejected() -> None:
    before = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1A,
    )
    after = _plan(
        PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        NextAction.CALCULATE_PHASE1B_INCREMENTAL,
    )

    with pytest.raises(
        runner.DailyEodBoundedOfflineRunnerError,
        match="differs from the bounded plan",
    ):
        runner.run_bounded_daily_eod_offline(
            config=_config(),
            started_at=STARTED,
            execute=True,
            planner=lambda **kwargs: before,
            executor=lambda **kwargs: DailyEodExecutionResult(
                outcome="succeeded",
                action=before.next_action,
                attempt_id=_event(1).attempt_id,
                event=_event(1),
                pre_plan=before,
                post_plan=after,
                stage_evidence=None,
                reason_code="offline_action_completed_and_replanned",
            ),
            clock=_Clock(),
        )


def test_blocked_plan_cannot_be_refingerprinted_as_boundary() -> None:
    plan = _plan(PlanStatus.BLOCKED, NextAction.OPERATOR_DIAGNOSIS)
    result = runner.run_bounded_daily_eod_offline(
        config=_config(),
        started_at=STARTED,
        planner=lambda **kwargs: plan,
        clock=_Clock(),
    )
    tampered = replace(
        result,
        status=runner.BoundedOfflineRunStatus.BOUNDARY_REACHED,
        logical_content_fingerprint="",
    )
    logical = asdict(tampered)
    logical.pop("logical_content_fingerprint")
    tampered = replace(
        tampered,
        logical_content_fingerprint=runner._fingerprint(runner._jsonable(logical)),
    )

    with pytest.raises(
        runner.DailyEodBoundedOfflineRunnerError,
        match="status conflicts",
    ):
        runner.verify_daily_eod_bounded_offline_run_result(tampered)


@pytest.mark.parametrize(
    "maximum_actions",
    (0, runner.MAXIMUM_ACTIONS + 1, True),
)
def test_action_budget_is_bounded(maximum_actions: int) -> None:
    with pytest.raises(
        runner.DailyEodBoundedOfflineRunnerError,
        match="inputs or budget",
    ):
        runner.run_bounded_daily_eod_offline(
            config=_config(),
            started_at=STARTED,
            maximum_actions=maximum_actions,
            planner=lambda **kwargs: pytest.fail("planner must not be called"),
        )
