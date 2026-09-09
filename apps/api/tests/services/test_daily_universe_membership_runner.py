from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import daily_universe_membership_runner as runner
from tip_api.services import daily_universe_membership_sidecar as sidecar
from tip_api.services.daily_eod_automation import (
    CONTRACT_VERSION as AUTOMATION_CONTRACT_VERSION,
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_universe_membership_continuation import (
    DailyUniverseMembershipContinuationResult,
)
from tip_api.services.universe_membership_apply_plan import (
    UniverseMembershipApplyPlanEvidence,
)


SESSION = date(2026, 9, 8)
CATALOG = date(2026, 8, 14)
STARTED = datetime(2026, 9, 9, 8, 30, tzinfo=UTC)


def _primary_paths(root: Path) -> DailyEodAutomationPaths:
    current = root / "sessions" / "session_date=2026-09-08"
    prior = root / "sessions" / "session_date=2026-09-04"
    return DailyEodAutomationPaths(
        data_root=root / "canonical",
        phase1a_audit=current / "market-regime-phase1a",
        prior_phase1b_audit=prior / "market-regime-phase1b",
        phase1b_audit=current / "market-regime-phase1b",
        prior_candidate_audit=prior / "opportunity-candidate",
        candidate_audit=current / "opportunity-candidate",
        entry_geometry_audit=current / "entry-geometry",
        phase2_audit=current / "etf-relationships",
        preview_bundle=current / "market-preview",
        strategy_channel_audit=current / "strategy-channels",
        market_intelligence_output_root=current / "market-intelligence",
        market_intelligence_approval_plan=current / "market-intelligence-plan.json",
        snapshot_output_root=current / "dashboard-snapshot",
        snapshot_approval_plan=current / "dashboard-snapshot-plan.json",
        serving_bundle_root=current / "serving-bundle",
    )


def _config(tmp_path: Path) -> runner.DailyUniverseMembershipRunConfig:
    paths = _primary_paths(tmp_path)
    session_root = paths.phase1a_audit.parent
    session_root.mkdir(parents=True, mode=0o700)
    session_root.chmod(0o700)
    paths.data_root.mkdir()
    return runner.DailyUniverseMembershipRunConfig(
        target_session=SESSION,
        data_root=paths.data_root,
        catalog_as_of_date=CATALOG,
        candidate_root=session_root / sidecar.CANDIDATE_ROOT_NAME,
        apply_plan_path=session_root / sidecar.APPLY_PLAN_NAME,
        primary_automation_paths=paths,
    )


def _primary_plan() -> DailyEodAutomationPlan:
    plan = DailyEodAutomationPlan(
        contract_version=AUTOMATION_CONTRACT_VERSION,
        target_session=SESSION.isoformat(),
        prior_session="2026-09-04",
        status=PlanStatus.ANALYTICS_READY,
        next_action=NextAction.REVIEW_BUNDLE_DEPLOYMENT,
        reason_codes=("fixture",),
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
        logical_content_fingerprint=sidecar._fingerprint(
            sidecar._jsonable(logical)
        ),
    )


def _plan(
    config: runner.DailyUniverseMembershipRunConfig,
    *,
    status: sidecar.MembershipSidecarStatus,
    action: sidecar.MembershipSidecarAction,
) -> sidecar.DailyUniverseMembershipSidecarPlan:
    candidate_values = {}
    if action in {
        sidecar.MembershipSidecarAction.WAIT_FOR_PRIMARY_PIPELINE,
        sidecar.MembershipSidecarAction.PREPARE_APPLY_PLAN,
        sidecar.MembershipSidecarAction.REVIEW_APPLY,
    }:
        candidate_values = {
            "catalog_fingerprint": "c" * 64,
            "candidate_status": "already_present",
            "record_count": 19_964,
            "membership_fingerprint": "a" * 64,
            "point_in_time_eligibility": "signal_eligible",
        }
    if action is sidecar.MembershipSidecarAction.PREPARE_CANDIDATE:
        candidate_values = {"catalog_fingerprint": "c" * 64}
    if action is sidecar.MembershipSidecarAction.REVIEW_APPLY:
        candidate_values["apply_plan_fingerprint"] = "d" * 64
    return sidecar._build_plan(
        checked_at=STARTED,
        target_session=SESSION,
        primary=_primary_plan(),
        catalog_as_of_date=CATALOG,
        candidate_partition=Path(runner._candidate_partition(config)),
        status=status,
        next_action=action,
        reasons=("fixture",),
        **candidate_values,
    )


def _planner(*plans: sidecar.DailyUniverseMembershipSidecarPlan):
    remaining = list(plans)

    def plan(**_: object) -> sidecar.DailyUniverseMembershipSidecarPlan:
        if not remaining:
            pytest.fail("runner requested an unexpected extra plan")
        return remaining.pop(0)

    return plan


def _candidate(
    config: runner.DailyUniverseMembershipRunConfig,
) -> DailyUniverseMembershipContinuationResult:
    return DailyUniverseMembershipContinuationResult(
        status="candidate_ready_for_publication_plan",
        session_date=SESSION.isoformat(),
        methodology_version=runner.METHODOLOGY_VERSION,
        candidate_partition_path=runner._candidate_partition(config),
        candidate_status="published",
        record_count=19_964,
        membership_logical_fingerprint="a" * 64,
        point_in_time_eligibility="signal_eligible",
        knowledge_time_assessment_fingerprint="b" * 64,
        canonical_publication_fingerprint=None,
    )


def _apply_evidence(
    config: runner.DailyUniverseMembershipRunConfig,
) -> UniverseMembershipApplyPlanEvidence:
    plan = SimpleNamespace(
        publication=SimpleNamespace(session_date=SESSION),
        data_root=str(config.data_root),
        candidate_root=str(config.candidate_root),
        candidate_membership_partition=runner._candidate_partition(config),
        logical_fingerprint="d" * 64,
        external_request_count=0,
        canonical_data_write_count=0,
        apply_authorized=False,
        historical_coverage_authorized=False,
        research_performance_authorized=False,
    )
    return UniverseMembershipApplyPlanEvidence(
        plan=plan,  # type: ignore[arg-type]
        plan_path=config.apply_plan_path,
        plan_sha256="e" * 64,
    )


def test_defaults_to_review_only_without_running_candidate(tmp_path: Path) -> None:
    config = _config(tmp_path)
    ready = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.READY,
        action=sidecar.MembershipSidecarAction.PREPARE_CANDIDATE,
    )

    result = runner.run_bounded_daily_universe_membership(
        config=config,
        started_at=STARTED,
        planner=_planner(ready),
        candidate_preparer=lambda **_: pytest.fail("review must not execute"),
        clock=lambda: STARTED,
    )

    assert result.status is runner.MembershipRunStatus.REVIEW_READY
    assert result.action_attempt_count == 0
    assert result.execution_enabled is False
    assert result.exclusive_process_lock is False


def test_executes_candidate_then_stops_for_primary_pipeline(tmp_path: Path) -> None:
    config = _config(tmp_path)
    ready = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.READY,
        action=sidecar.MembershipSidecarAction.PREPARE_CANDIDATE,
    )
    waiting = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.WAITING,
        action=sidecar.MembershipSidecarAction.WAIT_FOR_PRIMARY_PIPELINE,
    )

    result = runner.run_bounded_daily_universe_membership(
        config=config,
        started_at=STARTED,
        execute=True,
        planner=_planner(ready, waiting),
        candidate_preparer=lambda **_: _candidate(config),
        clock=lambda: STARTED,
    )

    assert result.status is runner.MembershipRunStatus.BOUNDARY_REACHED
    assert result.action_success_count == 1
    assert result.action_evidence[0].action == "prepare_candidate"
    assert result.final_next_action == "wait_for_primary_pipeline"
    assert result.website_pipeline_blocked is False
    assert result.canonical_membership_apply_performed is False


def test_executes_apply_plan_then_stops_before_apply(tmp_path: Path) -> None:
    config = _config(tmp_path)
    ready = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.READY,
        action=sidecar.MembershipSidecarAction.PREPARE_APPLY_PLAN,
    )
    review = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.REVIEW_REQUIRED,
        action=sidecar.MembershipSidecarAction.REVIEW_APPLY,
    )
    result = runner.run_bounded_daily_universe_membership(
        config=config,
        started_at=STARTED,
        execute=True,
        planner=_planner(ready, review),
        apply_plan_builder=lambda **_: _apply_evidence(config),
        clock=lambda: STARTED,
    )

    assert result.status is runner.MembershipRunStatus.BOUNDARY_REACHED
    assert result.action_success_count == 1
    assert result.action_evidence[0].action == "prepare_apply_plan"
    assert result.final_next_action == "review_apply"
    assert result.production_write_count == 0
    assert result.canonical_membership_apply_performed is False


def test_runs_both_workspace_actions_when_both_are_ready(tmp_path: Path) -> None:
    config = _config(tmp_path)
    candidate_ready = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.READY,
        action=sidecar.MembershipSidecarAction.PREPARE_CANDIDATE,
    )
    apply_plan_ready = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.READY,
        action=sidecar.MembershipSidecarAction.PREPARE_APPLY_PLAN,
    )
    review = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.REVIEW_REQUIRED,
        action=sidecar.MembershipSidecarAction.REVIEW_APPLY,
    )

    result = runner.run_bounded_daily_universe_membership(
        config=config,
        started_at=STARTED,
        execute=True,
        planner=_planner(candidate_ready, apply_plan_ready, review),
        candidate_preparer=lambda **_: _candidate(config),
        apply_plan_builder=lambda **_: _apply_evidence(config),
        clock=lambda: STARTED,
    )

    assert result.status is runner.MembershipRunStatus.BOUNDARY_REACHED
    assert result.action_success_count == 2
    assert [item.action for item in result.action_evidence] == [
        "prepare_candidate",
        "prepare_apply_plan",
    ]
    assert result.final_next_action == "review_apply"


def test_action_failure_never_retries_or_advances(tmp_path: Path) -> None:
    config = _config(tmp_path)
    ready = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.READY,
        action=sidecar.MembershipSidecarAction.PREPARE_CANDIDATE,
    )
    calls = 0

    def fail(**_: object):
        nonlocal calls
        calls += 1
        raise RuntimeError("fixture failure")

    result = runner.run_bounded_daily_universe_membership(
        config=config,
        started_at=STARTED,
        execute=True,
        planner=_planner(ready),
        candidate_preparer=fail,
        clock=lambda: STARTED,
    )

    assert calls == 1
    assert result.status is runner.MembershipRunStatus.ACTION_FAILED
    assert result.automatic_retry_enabled is False
    assert result.automatic_recovery_enabled is False
    assert result.action_evidence[0].failure_type == "RuntimeError"


def test_one_action_budget_stops_before_second_workspace_action(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    candidate_ready = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.READY,
        action=sidecar.MembershipSidecarAction.PREPARE_CANDIDATE,
    )
    apply_plan_ready = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.READY,
        action=sidecar.MembershipSidecarAction.PREPARE_APPLY_PLAN,
    )

    result = runner.run_bounded_daily_universe_membership(
        config=config,
        started_at=STARTED,
        execute=True,
        maximum_actions=1,
        planner=_planner(candidate_ready, apply_plan_ready),
        candidate_preparer=lambda **_: _candidate(config),
        apply_plan_builder=lambda **_: pytest.fail("budget must stop the plan"),
        clock=lambda: STARTED,
    )

    assert result.status is runner.MembershipRunStatus.BUDGET_EXHAUSTED
    assert result.action_attempt_count == 1
    assert result.final_next_action == "prepare_apply_plan"


def test_result_fingerprint_tampering_is_rejected(tmp_path: Path) -> None:
    config = _config(tmp_path)
    waiting = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.WAITING,
        action=sidecar.MembershipSidecarAction.WAIT_FOR_PRIMARY_PIPELINE,
    )
    result = runner.run_bounded_daily_universe_membership(
        config=config,
        started_at=STARTED,
        execute=True,
        planner=_planner(waiting),
        clock=lambda: STARTED,
    )

    with pytest.raises(
        runner.DailyUniverseMembershipRunnerError,
        match="exceeds its authority",
    ):
        runner.verify_daily_universe_membership_run_result(
            replace(result, production_write_count=1)
        )


def test_execute_rejects_a_concurrent_session_runner(tmp_path: Path) -> None:
    config = _config(tmp_path)
    ready = _plan(
        config,
        status=sidecar.MembershipSidecarStatus.READY,
        action=sidecar.MembershipSidecarAction.PREPARE_CANDIDATE,
    )

    with runner._exclusive_session_lock(config.candidate_root.parent), pytest.raises(
        runner.DailyUniverseMembershipRunnerError,
        match="another Membership sidecar runner",
    ):
        runner.run_bounded_daily_universe_membership(
            config=config,
            started_at=STARTED,
            execute=True,
            planner=_planner(ready),
            clock=lambda: STARTED,
        )
