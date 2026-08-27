from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from tip_api.services import daily_eod_executor as executor
from tip_api.services.daily_eod_automation import (
    ArtifactObservation,
    ArtifactStatus,
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_run_journal import locked_daily_eod_run_journal


SESSION = date(2026, 8, 27)
PRE_FP = "a" * 64
POST_FP = "b" * 64


def _paths(tmp_path: Path) -> DailyEodAutomationPaths:
    suffix = tmp_path.name
    return DailyEodAutomationPaths(
        data_root=tmp_path / "data",
        phase1a_audit=Path(f"/tmp/{suffix}-phase1a"),
        prior_phase1b_audit=Path(f"/tmp/{suffix}-prior-phase1b"),
        phase1b_audit=Path(f"/tmp/{suffix}-phase1b"),
        prior_candidate_audit=Path(f"/tmp/{suffix}-prior-candidate"),
        candidate_audit=Path(f"/tmp/{suffix}-candidate"),
        entry_geometry_audit=Path(f"/tmp/{suffix}-entry"),
    )


def _config(tmp_path: Path) -> executor.DailyEodExecutionConfig:
    run_root = tmp_path / "run-root"
    run_root.mkdir(mode=0o700)
    run_root.chmod(0o700)
    return executor.DailyEodExecutionConfig(
        target_session=SESSION,
        paths=_paths(tmp_path),
        run_root=run_root,
        panel_cache_root=tmp_path / "panel-cache",
        candidate_work_dir=Path(f"/tmp/{tmp_path.name}-candidate-work"),
    )


def _plan(
    *,
    fingerprint: str,
    status: PlanStatus,
    action: NextAction,
    stage: str,
    stage_status: ArtifactStatus,
) -> DailyEodAutomationPlan:
    return DailyEodAutomationPlan(
        contract_version="daily-eod-automation-plan/1.0",
        target_session=SESSION.isoformat(),
        prior_session="2026-08-26",
        status=status,
        next_action=action,
        reason_codes=("test",),
        observations=(
            ArtifactObservation(
                stage=stage,
                status=stage_status,
                path=f"/tmp/{stage}",
                as_of_session=(
                    SESSION.isoformat()
                    if stage_status is ArtifactStatus.COMPLETED
                    else None
                ),
                logical_fingerprint=("c" * 64 if stage_status is ArtifactStatus.COMPLETED else None),
            ),
        ),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=fingerprint,
    )


def _evidence(
    action: NextAction, config: executor.DailyEodExecutionConfig
) -> executor.StageExecutionEvidence:
    return executor.StageExecutionEvidence(
        action=action,
        output_path=str(executor._action_output_path(action, config)),
        summary_sha256="d" * 64,
        summary_bytes=100,
    )


def test_executes_one_exact_action_and_replans_under_hash_chain(tmp_path) -> None:
    config = _config(tmp_path)
    action = NextAction.CALCULATE_PHASE1A
    pre = _plan(
        fingerprint=PRE_FP,
        status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        action=action,
        stage="phase1a",
        stage_status=ArtifactStatus.MISSING,
    )
    post = _plan(
        fingerprint=POST_FP,
        status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        action=NextAction.CALCULATE_PHASE1B_INCREMENTAL,
        stage="phase1a",
        stage_status=ArtifactStatus.COMPLETED,
    )
    calls = []

    def planner(**kwargs):
        calls.append(kwargs)
        return pre if len(calls) == 1 else post

    result = executor.execute_daily_eod_action(
        config=config,
        expected_plan_fingerprint=PRE_FP,
        expected_action=action,
        planner=planner,
        runner=lambda selected, cfg: _evidence(selected, cfg),
    )
    assert result.outcome == "succeeded"
    assert result.post_plan == post
    assert len(calls) == 2
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=SESSION,
    ) as journal:
        events = journal.read_events()
    assert [item.event_type for item in events] == ["action_started", "action_succeeded"]
    assert events[1].previous_event_fingerprint == events[0].event_fingerprint


@pytest.mark.parametrize(
    ("expected_fingerprint", "expected_action"),
    [
        ("f" * 64, NextAction.CALCULATE_PHASE1A),
        (PRE_FP, NextAction.CALCULATE_CANDIDATE_DAILY),
    ],
)
def test_stale_fingerprint_or_different_action_writes_no_attempt(
    tmp_path, expected_fingerprint, expected_action
) -> None:
    config = _config(tmp_path)
    pre = _plan(
        fingerprint=PRE_FP,
        status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        action=NextAction.CALCULATE_PHASE1A,
        stage="phase1a",
        stage_status=ArtifactStatus.MISSING,
    )
    with pytest.raises(executor.DailyEodExecutorError, match="stale"):
        executor.execute_daily_eod_action(
            config=config,
            expected_plan_fingerprint=expected_fingerprint,
            expected_action=expected_action,
            planner=lambda **kwargs: pre,
            runner=lambda selected, cfg: pytest.fail("runner must not execute"),
        )
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=SESSION,
    ) as journal:
        assert journal.read_events() == ()


def test_runner_failure_is_terminal_and_retryable(tmp_path) -> None:
    config = _config(tmp_path)
    action = NextAction.CALCULATE_PHASE1A
    pre = _plan(
        fingerprint=PRE_FP,
        status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        action=action,
        stage="phase1a",
        stage_status=ArtifactStatus.MISSING,
    )
    result = executor.execute_daily_eod_action(
        config=config,
        expected_plan_fingerprint=PRE_FP,
        expected_action=action,
        planner=lambda **kwargs: pre,
        runner=lambda selected, cfg: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert result.outcome == "failed"
    assert result.reason_code == "offline_action_raised"
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=SESSION,
    ) as journal:
        assert [item.event_type for item in journal.read_events()] == [
            "action_started",
            "action_failed",
        ]


def test_mismatched_runner_evidence_cannot_be_recorded_as_success(tmp_path) -> None:
    config = _config(tmp_path)
    action = NextAction.CALCULATE_PHASE1A
    pre = _plan(
        fingerprint=PRE_FP,
        status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        action=action,
        stage="phase1a",
        stage_status=ArtifactStatus.MISSING,
    )
    result = executor.execute_daily_eod_action(
        config=config,
        expected_plan_fingerprint=PRE_FP,
        expected_action=action,
        planner=lambda **kwargs: pre,
        runner=lambda selected, cfg: executor.StageExecutionEvidence(
            action=selected,
            output_path="/tmp/unrelated-output",
            summary_sha256="d" * 64,
            summary_bytes=100,
        ),
    )
    assert result.outcome == "failed"
    assert result.reason_code == "offline_action_raised"
    assert result.stage_evidence is None
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=SESSION,
    ) as journal:
        assert [item.event_type for item in journal.read_events()] == [
            "action_started",
            "action_failed",
        ]


def test_abrupt_interrupt_leaves_started_event_and_requires_recovery(tmp_path) -> None:
    config = _config(tmp_path)
    action = NextAction.CALCULATE_PHASE1A
    pre = _plan(
        fingerprint=PRE_FP,
        status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        action=action,
        stage="phase1a",
        stage_status=ArtifactStatus.MISSING,
    )
    with pytest.raises(KeyboardInterrupt):
        executor.execute_daily_eod_action(
            config=config,
            expected_plan_fingerprint=PRE_FP,
            expected_action=action,
            planner=lambda **kwargs: pre,
            runner=lambda selected, cfg: (_ for _ in ()).throw(KeyboardInterrupt()),
        )
    with pytest.raises(executor.DailyEodExecutorError, match="recover"):
        executor.execute_daily_eod_action(
            config=config,
            expected_plan_fingerprint=PRE_FP,
            expected_action=action,
            planner=lambda **kwargs: pre,
            runner=lambda selected, cfg: pytest.fail("runner must not execute"),
        )
    recovered = executor.recover_daily_eod_action(
        config=config,
        planner=lambda **kwargs: pre,
    )
    assert recovered.outcome == "recovered_not_completed"
    assert recovered.reason_code == "no_completed_artifact_detected"


def test_recovery_recognizes_completed_artifact_without_reexecution(tmp_path) -> None:
    config = _config(tmp_path)
    action = NextAction.CALCULATE_ENTRY_GEOMETRY
    before = _plan(
        fingerprint=PRE_FP,
        status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        action=action,
        stage="entry_geometry",
        stage_status=ArtifactStatus.MISSING,
    )
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=SESSION,
    ) as journal:
        attempt = executor.new_attempt_id(
            target_session=SESSION,
            plan_fingerprint=PRE_FP,
            sequence=1,
        )
        journal.append(
            event_type="action_started",
            attempt_id=attempt,
            details={
                "action": action.value,
                "plan_fingerprint": PRE_FP,
                "execution_input_fingerprint": executor._execution_input_fingerprint(config),
            },
        )
    current = _plan(
        fingerprint=POST_FP,
        status=PlanStatus.ANALYTICS_READY,
        action=NextAction.REVIEW_PUBLICATION,
        stage="entry_geometry",
        stage_status=ArtifactStatus.COMPLETED,
    )
    recovered = executor.recover_daily_eod_action(
        config=config,
        planner=lambda **kwargs: current,
    )
    assert recovered.outcome == "recovered_succeeded"
    assert recovered.current_plan == current
    assert recovered.as_dict()["action_executed"] is False


def test_recovery_blocks_ambiguous_or_corrupt_current_state(tmp_path) -> None:
    config = _config(tmp_path)
    action = NextAction.CALCULATE_PHASE1A
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=SESSION,
    ) as journal:
        attempt = executor.new_attempt_id(
            target_session=SESSION,
            plan_fingerprint=PRE_FP,
            sequence=1,
        )
        journal.append(
            event_type="action_started",
            attempt_id=attempt,
            details={
                "action": action.value,
                "plan_fingerprint": PRE_FP,
                "execution_input_fingerprint": executor._execution_input_fingerprint(config),
            },
        )
    blocked = _plan(
        fingerprint=POST_FP,
        status=PlanStatus.BLOCKED,
        action=NextAction.OPERATOR_DIAGNOSIS,
        stage="phase1a",
        stage_status=ArtifactStatus.INVALID,
    )
    recovered = executor.recover_daily_eod_action(
        config=config,
        planner=lambda **kwargs: blocked,
    )
    assert recovered.outcome == "recovery_blocked"
    assert recovered.reason_code == "current_state_cannot_prove_completion_or_safe_retry"


def test_recovery_rejects_paths_that_differ_from_started_attempt(tmp_path) -> None:
    config = _config(tmp_path)
    action = NextAction.CALCULATE_PHASE1A
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=SESSION,
    ) as journal:
        attempt = executor.new_attempt_id(
            target_session=SESSION,
            plan_fingerprint=PRE_FP,
            sequence=1,
        )
        journal.append(
            event_type="action_started",
            attempt_id=attempt,
            details={
                "action": action.value,
                "plan_fingerprint": PRE_FP,
                "execution_input_fingerprint": executor._execution_input_fingerprint(config),
            },
        )
    changed_paths = DailyEodAutomationPaths(
        data_root=config.paths.data_root,
        phase1a_audit=Path("/tmp/different-phase1a"),
        prior_phase1b_audit=config.paths.prior_phase1b_audit,
        phase1b_audit=config.paths.phase1b_audit,
        prior_candidate_audit=config.paths.prior_candidate_audit,
        candidate_audit=config.paths.candidate_audit,
        entry_geometry_audit=config.paths.entry_geometry_audit,
    )
    changed = executor.DailyEodExecutionConfig(
        target_session=config.target_session,
        paths=changed_paths,
        run_root=config.run_root,
        panel_cache_root=config.panel_cache_root,
        candidate_work_dir=config.candidate_work_dir,
    )
    with pytest.raises(executor.DailyEodExecutorError, match="differ"):
        executor.recover_daily_eod_action(
            config=changed,
            planner=lambda **kwargs: pytest.fail("planner must not run"),
        )


def test_postcondition_requires_formally_completed_action_stage(tmp_path) -> None:
    config = _config(tmp_path)
    action = NextAction.CALCULATE_PHASE1A
    pre = _plan(
        fingerprint=PRE_FP,
        status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
        action=action,
        stage="phase1a",
        stage_status=ArtifactStatus.MISSING,
    )
    calls = 0

    def planner(**kwargs):
        nonlocal calls
        calls += 1
        return pre

    result = executor.execute_daily_eod_action(
        config=config,
        expected_plan_fingerprint=PRE_FP,
        expected_action=action,
        planner=planner,
        runner=lambda selected, cfg: _evidence(selected, cfg),
    )
    assert result.outcome == "failed"
    assert result.reason_code == "offline_action_postcondition_failed"


def test_journal_cannot_be_inside_data_root(tmp_path) -> None:
    config = _config(tmp_path)
    unsafe = executor.DailyEodExecutionConfig(
        target_session=config.target_session,
        paths=config.paths,
        run_root=config.paths.data_root / "daily-runs",
    )
    with pytest.raises(executor.DailyEodExecutorError, match="outside"):
        executor.execute_daily_eod_action(
            config=unsafe,
            expected_plan_fingerprint=PRE_FP,
            expected_action=NextAction.CALCULATE_PHASE1A,
            planner=lambda **kwargs: pytest.fail("planner must not run"),
        )


def test_panel_cache_cannot_be_inside_data_root(tmp_path) -> None:
    config = _config(tmp_path)
    unsafe = executor.DailyEodExecutionConfig(
        target_session=config.target_session,
        paths=config.paths,
        run_root=config.run_root,
        panel_cache_root=config.paths.data_root / "panel-cache",
    )
    with pytest.raises(executor.DailyEodExecutorError, match="panel cache"):
        executor.execute_daily_eod_action(
            config=unsafe,
            expected_plan_fingerprint=PRE_FP,
            expected_action=NextAction.CALCULATE_PHASE1A,
            planner=lambda **kwargs: pytest.fail("planner must not run"),
        )


@pytest.mark.parametrize(
    ("action", "module_name", "required_arguments"),
    [
        (
            NextAction.CALCULATE_PHASE1A,
            "market_regime_cli",
            ("--panel-cache-root", "--output-dir"),
        ),
        (
            NextAction.CALCULATE_PHASE1B_INCREMENTAL,
            "market_regime_state_cli",
            ("--phase1a-audit", "--prior-state-audit"),
        ),
        (
            NextAction.CALCULATE_CANDIDATE_DAILY,
            "opportunity_candidate_cli",
            ("--validation-tier", "daily", "--max-workers", "1", "--audit-work-dir"),
        ),
        (
            NextAction.CALCULATE_ENTRY_GEOMETRY,
            "candidate_entry_geometry_cli",
            ("--candidate-audit", "--output-dir"),
        ),
    ],
)
def test_default_runner_invokes_only_the_selected_offline_administrator(
    monkeypatch, tmp_path, action, module_name, required_arguments
) -> None:
    config = _config(tmp_path)
    calls = []

    def selected_main(argv):
        calls.append(tuple(argv))
        print('{"status":"completed"}')
        return 0

    for name in (
        "market_regime_cli",
        "market_regime_state_cli",
        "opportunity_candidate_cli",
        "candidate_entry_geometry_cli",
    ):
        module = getattr(executor, name)
        monkeypatch.setattr(
            module,
            "main",
            selected_main if name == module_name else lambda argv: pytest.fail("wrong action ran"),
        )
    evidence = executor.run_offline_action(action, config)
    assert evidence.action is action
    assert len(calls) == 1
    argv = calls[0]
    for value in required_arguments:
        assert value in argv
    assert evidence.summary_bytes > 0
    assert len(evidence.summary_sha256) == 64
