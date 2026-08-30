from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from tip_api.services import daily_eod_pipeline_cadence as cadence
from tip_api.services import daily_eod_pipeline_runtime as runtime
from tip_api.services import daily_eod_pipeline_scheduler as scheduler
from tip_api.services import daily_eod_run_journal as journal
from tip_api.services.daily_eod_cadence_evidence import cadence_wake_state_from_events
from tip_api.services.daily_eod_coordinator import (
    CONTRACT_VERSION as COORDINATOR_CONTRACT_VERSION,
    CoordinatorStatus,
    DailyEodCoordinatorResult,
    daily_eod_coordinator_result_fingerprint,
)


TARGET = date(2026, 8, 28)
PRIOR = date(2026, 8, 27)
CHECKED = datetime(2026, 8, 29, 12, tzinfo=UTC)
STARTED = CHECKED + timedelta(seconds=1)
COMPLETED = STARTED + timedelta(seconds=30)


def _root(tmp_path):
    root = tmp_path / "daily-runs"
    root.mkdir(parents=True, mode=0o700)
    root.chmod(0o700)
    return root


def _plans(*, enabled: bool = True):
    pipeline = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=CHECKED,
        completed_sessions=(PRIOR,),
        review_enabled_candidate=enabled,
    )
    bounded = cadence.plan_bounded_pipeline_cadence(
        checked_at=CHECKED,
        cadence_started_at=CHECKED - timedelta(minutes=15),
        pipeline_plan=pipeline,
        review_enabled_candidate=enabled,
    )
    return pipeline, bounded


def _coordinator_result(
    status: CoordinatorStatus = CoordinatorStatus.TRANSITION_EXECUTED,
) -> DailyEodCoordinatorResult:
    result = DailyEodCoordinatorResult(
        status=status,
        target_session=TARGET.isoformat(),
        next_action=(
            "fetch_eod"
            if status is CoordinatorStatus.TRANSITION_EXECUTED
            else "operator_diagnosis"
        ),
        reason_codes=("test",),
        automation_plan_fingerprint="a" * 64,
        readiness_plan_fingerprint="b" * 64,
        transition_fingerprint="c" * 64,
        external_request_count=1,
        production_write_count=0,
        contract_version=COORDINATOR_CONTRACT_VERSION,
    )
    return replace(
        result,
        logical_content_fingerprint=daily_eod_coordinator_result_fingerprint(result),
    )


def _run(root, pipeline, bounded, **kwargs):
    return runtime.run_one_pipeline_cadence_wake(
        run_root=root,
        pipeline_plan=pipeline,
        cadence_plan=bounded,
        expected_pipeline_plan_fingerprint=pipeline.logical_content_fingerprint,
        expected_cadence_plan_fingerprint=bounded.logical_content_fingerprint,
        started_at=STARTED,
        clock=lambda: COMPLETED,
        **kwargs,
    )


def test_default_off_review_does_not_touch_the_run_root(tmp_path) -> None:
    pipeline, bounded = _plans(enabled=False)
    missing_root = tmp_path / "absent"

    result = _run(missing_root, pipeline, bounded)

    assert result.status is runtime.PipelineRuntimeStatus.REVIEW_READY
    assert result.transition_invocation_count == 0
    assert not missing_root.exists()


def test_one_data_transition_is_reserved_invoked_and_resolved(tmp_path) -> None:
    root = _root(tmp_path)
    pipeline, bounded = _plans()
    calls = 0

    def transition():
        nonlocal calls
        calls += 1
        with journal.locked_daily_eod_run_journal(
            run_root=root,
            target_session=TARGET,
        ) as locked:
            attempt_id = journal.new_attempt_id(
                target_session=TARGET,
                plan_fingerprint="d" * 64,
                sequence=len(locked.read_events()) + 1,
            )
            locked.append(
                event_type=journal.ACQUISITION_START_EVENT,
                attempt_id=attempt_id,
                details={"operation": "fetch_eod"},
                observed_at=STARTED + timedelta(seconds=1),
            )
            locked.append(
                event_type="acquisition_package_ready",
                attempt_id=attempt_id,
                details={"reason_code": "test"},
                observed_at=STARTED + timedelta(seconds=2),
            )
        return _coordinator_result()

    result = _run(
        root,
        pipeline,
        bounded,
        invoke_one_transition=True,
        data_transition=transition,
    )

    with journal.locked_daily_eod_run_journal(
        run_root=root,
        target_session=TARGET,
    ) as locked:
        state = cadence_wake_state_from_events(
            locked.read_events(),
            target_session=TARGET,
        )
    assert calls == 1
    assert result.status is runtime.PipelineRuntimeStatus.TRANSITION_RECORDED
    assert result.transition_invocation_count == 1
    assert result.wake_outcome == cadence.CadenceWakeOutcome.ADVANCED.value
    assert len(state.completed) == 1
    assert state.pending_event is None


def test_exception_leaves_unknown_reservation_and_blocks_replay(tmp_path) -> None:
    root = _root(tmp_path)
    pipeline, bounded = _plans()
    calls = 0

    def transition():
        nonlocal calls
        calls += 1
        raise RuntimeError("ambiguous")

    with pytest.raises(runtime.DailyEodPipelineRuntimeError, match="unknown"):
        _run(
            root,
            pipeline,
            bounded,
            invoke_one_transition=True,
            data_transition=transition,
        )
    with pytest.raises(runtime.DailyEodPipelineRuntimeError, match="reservation"):
        _run(
            root,
            pipeline,
            bounded,
            invoke_one_transition=True,
            data_transition=transition,
        )

    with journal.locked_daily_eod_run_journal(
        run_root=root,
        target_session=TARGET,
    ) as locked:
        state = cadence_wake_state_from_events(
            locked.read_events(),
            target_session=TARGET,
        )
    assert calls == 1
    assert state.completed == ()
    assert state.pending_evidence is not None
    assert state.pending_evidence.outcome is cadence.CadenceWakeOutcome.UNKNOWN
    with pytest.raises(journal.DailyEodRunJournalError, match="earlier"):
        with journal.locked_daily_eod_run_journal(
            run_root=root,
            target_session=TARGET + timedelta(days=1),
        ):
            pass


def test_invalid_return_contract_also_blocks_automatic_replay(tmp_path) -> None:
    root = _root(tmp_path)
    pipeline, bounded = _plans()

    with pytest.raises(runtime.DailyEodPipelineRuntimeError, match="unknown"):
        _run(
            root,
            pipeline,
            bounded,
            invoke_one_transition=True,
            data_transition=lambda: replace(
                _coordinator_result(),
                target_session=PRIOR.isoformat(),
            ),
        )

    with journal.locked_daily_eod_run_journal(
        run_root=root,
        target_session=TARGET,
    ) as locked:
        assert cadence_wake_state_from_events(
            locked.read_events(),
            target_session=TARGET,
        ).pending_event is not None


def test_capability_scope_and_exact_plan_are_checked_before_reservation(tmp_path) -> None:
    root = _root(tmp_path)
    pipeline, bounded = _plans()

    with pytest.raises(runtime.DailyEodPipelineRuntimeError, match="matching"):
        _run(
            root,
            pipeline,
            bounded,
            invoke_one_transition=True,
            offline_transition=lambda: None,  # type: ignore[return-value]
        )
    with pytest.raises(runtime.DailyEodPipelineRuntimeError, match="identity"):
        runtime.run_one_pipeline_cadence_wake(
            run_root=root,
            pipeline_plan=pipeline,
            cadence_plan=bounded,
            expected_pipeline_plan_fingerprint="0" * 64,
            expected_cadence_plan_fingerprint=bounded.logical_content_fingerprint,
            started_at=STARTED,
        )
    assert tuple(root.iterdir()) == ()


def test_known_blocked_result_is_retained_as_failure(tmp_path) -> None:
    root = _root(tmp_path)
    pipeline, bounded = _plans()

    result = _run(
        root,
        pipeline,
        bounded,
        invoke_one_transition=True,
        data_transition=lambda: _coordinator_result(CoordinatorStatus.BLOCKED),
    )

    assert result.wake_outcome == cadence.CadenceWakeOutcome.FAILED.value


def test_runtime_result_tampering_is_rejected(tmp_path) -> None:
    pipeline, bounded = _plans(enabled=False)
    result = _run(tmp_path / "absent", pipeline, bounded)

    with pytest.raises(runtime.DailyEodPipelineRuntimeError, match="fingerprint"):
        runtime.verify_daily_eod_pipeline_runtime_result(
            replace(result, cadence_plan_fingerprint="0" * 64)
        )
