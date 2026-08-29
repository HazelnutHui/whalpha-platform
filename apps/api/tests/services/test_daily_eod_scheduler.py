from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from tip_api.services.daily_eod_scheduler import (
    DailyEodSchedulerError,
    SchedulerWakeAction,
    SchedulerWakeStatus,
    plan_daily_eod_scheduler_wake,
)


def test_current_canonical_state_waits_for_next_session_stabilization() -> None:
    plan = plan_daily_eod_scheduler_wake(
        checked_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
        completed_sessions=(date(2026, 8, 27), date(2026, 8, 28)),
    )

    assert plan.status is SchedulerWakeStatus.UP_TO_DATE
    assert plan.next_action is SchedulerWakeAction.WAIT
    assert plan.latest_canonical_session == "2026-08-28"
    assert plan.expected_latest_completed_session == "2026-08-28"
    assert plan.target_session == "2026-08-31"
    assert plan.next_check_at == "2026-08-31T20:30:00+00:00"
    assert plan.missing_session_count == 0
    assert plan.scheduler_candidate_enabled is False
    assert plan.scheduler_installation_performed is False


def test_current_missing_session_waits_through_stabilization() -> None:
    plan = plan_daily_eod_scheduler_wake(
        checked_at=datetime(2026, 8, 28, 20, 10, tzinfo=UTC),
        completed_sessions=(date(2026, 8, 27),),
    )

    assert plan.status is SchedulerWakeStatus.WAITING
    assert plan.next_action is SchedulerWakeAction.WAIT
    assert plan.target_session == "2026-08-28"
    assert plan.next_check_at == "2026-08-28T20:30:00+00:00"
    assert "provider_completeness_not_asserted" in plan.reason_codes


def test_enabled_candidate_can_only_propose_one_coordinator_invocation() -> None:
    plan = plan_daily_eod_scheduler_wake(
        checked_at=datetime(2026, 8, 28, 21, tzinfo=UTC),
        completed_sessions=(date(2026, 8, 27),),
        review_enabled_candidate=True,
    )

    assert plan.status is SchedulerWakeStatus.READY_FOR_WAKE
    assert plan.next_action is SchedulerWakeAction.INVOKE_ONE_TRANSITION
    assert plan.scheduler_candidate_enabled is True
    assert plan.scheduler_installation_performed is False
    assert plan.coordinator_invocation_limit == 1
    assert plan.coordinator_invocation_count == 0
    assert plan.automatic_retry_enabled is False
    assert plan.automatic_recovery_enabled is False
    assert plan.publication_authorized is False
    assert plan.deployment_authorized is False
    assert plan.credential_access_count == 0
    assert plan.external_request_count == 0
    assert plan.filesystem_write_count == 0
    assert plan.production_write_count == 0


def test_oldest_missing_session_is_selected_before_newer_gap() -> None:
    plan = plan_daily_eod_scheduler_wake(
        checked_at=datetime(2026, 8, 31, 21, tzinfo=UTC),
        completed_sessions=(date(2026, 8, 27),),
    )

    assert plan.expected_latest_completed_session == "2026-08-31"
    assert plan.missing_session_count == 2
    assert plan.target_session == "2026-08-28"
    assert plan.status is SchedulerWakeStatus.READY_FOR_WAKE
    assert plan.next_action is SchedulerWakeAction.REVIEW_ONE_TRANSITION_WAKE
    assert plan.next_check_at == "2026-08-31T21:00:00+00:00"


@pytest.mark.parametrize(
    "completed_sessions",
    (
        (),
        (date(2026, 8, 28), date(2026, 8, 27)),
        (date(2026, 8, 26), date(2026, 8, 28)),
        (date(2026, 8, 29),),
    ),
)
def test_invalid_canonical_sequences_fail_closed(
    completed_sessions: tuple[date, ...],
) -> None:
    with pytest.raises(DailyEodSchedulerError):
        plan_daily_eod_scheduler_wake(
            checked_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
            completed_sessions=completed_sessions,
        )


def test_naive_checked_at_is_rejected() -> None:
    with pytest.raises(DailyEodSchedulerError, match="timezone-aware"):
        plan_daily_eod_scheduler_wake(
            checked_at=datetime(2026, 8, 29, 12),
            completed_sessions=(date(2026, 8, 28),),
        )
