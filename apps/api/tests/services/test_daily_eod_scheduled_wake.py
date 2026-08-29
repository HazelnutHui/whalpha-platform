from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorResult,
    daily_eod_coordinator_result_fingerprint,
)
from tip_api.services.daily_eod_scheduled_wake import (
    DailyEodScheduledWakeError,
    ScheduledWakeStatus,
    run_one_scheduled_wake,
)
from tip_api.services.daily_eod_scheduler import plan_daily_eod_scheduler_wake


def plan(*, enabled: bool = False, current: bool = False):
    return plan_daily_eod_scheduler_wake(
        checked_at=(
            datetime(2026, 8, 29, 12, tzinfo=UTC)
            if current
            else datetime(2026, 8, 28, 21, tzinfo=UTC)
        ),
        completed_sessions=(
            (date(2026, 8, 27), date(2026, 8, 28))
            if current
            else (date(2026, 8, 27),)
        ),
        review_enabled_candidate=enabled,
    )


def coordinator_result(
    *,
    status: CoordinatorStatus = CoordinatorStatus.WAITING,
    target_session: str = "2026-08-28",
    alert_required: bool = False,
) -> DailyEodCoordinatorResult:
    result = DailyEodCoordinatorResult(
        status=status,
        target_session=target_session,
        next_action="wait_for_retry",
        reason_codes=("synthetic",),
        automation_plan_fingerprint="a" * 64,
        readiness_plan_fingerprint="b" * 64,
        transition_fingerprint=None,
        external_request_count=0,
        production_write_count=0,
        alert_required=alert_required,
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        logical_content_fingerprint="",
    )
    return refingerprint(result)


def refingerprint(result: DailyEodCoordinatorResult) -> DailyEodCoordinatorResult:
    return replace(
        result,
        logical_content_fingerprint=daily_eod_coordinator_result_fingerprint(result),
    )


def test_current_wake_does_not_invoke_coordinator() -> None:
    selected = plan(current=True)
    calls = 0

    def coordinator():
        nonlocal calls
        calls += 1
        return coordinator_result()

    result = run_one_scheduled_wake(
        plan=selected,
        expected_plan_fingerprint=selected.logical_content_fingerprint,
        coordinator=coordinator,
    )

    assert result.status is ScheduledWakeStatus.WAITING
    assert result.coordinator_invocation_count == 0
    assert calls == 0


def test_disabled_ready_candidate_stops_at_review() -> None:
    selected = plan()
    result = run_one_scheduled_wake(
        plan=selected,
        expected_plan_fingerprint=selected.logical_content_fingerprint,
    )

    assert result.status is ScheduledWakeStatus.REVIEW_READY
    assert result.coordinator_invocation_count == 0


def test_explicit_invocation_requires_enabled_candidate() -> None:
    selected = plan()
    calls = 0

    def coordinator():
        nonlocal calls
        calls += 1
        return coordinator_result()

    with pytest.raises(DailyEodScheduledWakeError, match="enabled ready-wake"):
        run_one_scheduled_wake(
            plan=selected,
            expected_plan_fingerprint=selected.logical_content_fingerprint,
            invoke_one_transition=True,
            coordinator=coordinator,
        )
    assert calls == 0


def test_enabled_wake_invokes_coordinator_exactly_once() -> None:
    selected = plan(enabled=True)
    calls = 0

    def coordinator():
        nonlocal calls
        calls += 1
        return coordinator_result()

    result = run_one_scheduled_wake(
        plan=selected,
        expected_plan_fingerprint=selected.logical_content_fingerprint,
        invoke_one_transition=True,
        coordinator=coordinator,
    )

    assert result.status is ScheduledWakeStatus.COORDINATOR_INVOKED
    assert result.coordinator_status == "waiting"
    assert result.coordinator_result_fingerprint == (
        daily_eod_coordinator_result_fingerprint(coordinator_result())
    )
    assert result.coordinator_invocation_count == 1
    assert calls == 1
    assert result.automatic_retry_enabled is False


def test_recovery_required_is_reported_without_recovery() -> None:
    selected = plan(enabled=True)
    result = run_one_scheduled_wake(
        plan=selected,
        expected_plan_fingerprint=selected.logical_content_fingerprint,
        invoke_one_transition=True,
        coordinator=lambda: coordinator_result(
            status=CoordinatorStatus.RECOVERY_REQUIRED
        ),
    )

    assert result.coordinator_status == "recovery_required"
    assert result.recovery_attempted is False
    assert result.automatic_recovery_enabled is False


def test_alert_required_is_reported_without_delivery() -> None:
    selected = plan(enabled=True)
    result = run_one_scheduled_wake(
        plan=selected,
        expected_plan_fingerprint=selected.logical_content_fingerprint,
        invoke_one_transition=True,
        coordinator=lambda: coordinator_result(
            status=CoordinatorStatus.BLOCKED,
            alert_required=True,
        ),
    )

    assert result.alert_required is True
    assert result.alert_delivery_attempted is False


def test_coordinator_exception_is_never_retried() -> None:
    selected = plan(enabled=True)
    calls = 0

    def coordinator():
        nonlocal calls
        calls += 1
        raise RuntimeError("interrupted")

    with pytest.raises(DailyEodScheduledWakeError, match="replay is prohibited"):
        run_one_scheduled_wake(
            plan=selected,
            expected_plan_fingerprint=selected.logical_content_fingerprint,
            invoke_one_transition=True,
            coordinator=coordinator,
        )
    assert calls == 1


@pytest.mark.parametrize(
    "result",
    (
        coordinator_result(target_session="2026-08-27"),
        refingerprint(replace(coordinator_result(), scheduler_enabled=True)),
        refingerprint(replace(coordinator_result(), publication_authorized=True)),
        refingerprint(replace(coordinator_result(), deployment_authorized=True)),
        refingerprint(replace(coordinator_result(), external_request_count=-1)),
        refingerprint(replace(coordinator_result(), production_write_count=-1)),
    ),
)
def test_invalid_coordinator_result_fails_closed(result) -> None:
    selected = plan(enabled=True)
    with pytest.raises(DailyEodScheduledWakeError):
        run_one_scheduled_wake(
            plan=selected,
            expected_plan_fingerprint=selected.logical_content_fingerprint,
            invoke_one_transition=True,
            coordinator=lambda: result,
        )


def test_stale_plan_fingerprint_stops_before_coordinator() -> None:
    selected = plan(enabled=True)
    with pytest.raises(DailyEodScheduledWakeError, match="fingerprint mismatch"):
        run_one_scheduled_wake(
            plan=selected,
            expected_plan_fingerprint="d" * 64,
            invoke_one_transition=True,
            coordinator=lambda: pytest.fail("stale plan must stop before call"),
        )


def test_tampered_plan_content_stops_before_coordinator() -> None:
    selected = plan(enabled=True)
    tampered = replace(selected, target_session="2026-08-31")
    with pytest.raises(DailyEodScheduledWakeError, match="content is invalid"):
        run_one_scheduled_wake(
            plan=tampered,
            expected_plan_fingerprint=selected.logical_content_fingerprint,
            invoke_one_transition=True,
            coordinator=lambda: pytest.fail("tampered plan must stop before call"),
        )


def test_tampered_coordinator_content_is_rejected() -> None:
    selected = plan(enabled=True)
    valid = coordinator_result()
    tampered = replace(valid, next_action="different_action")
    with pytest.raises(DailyEodScheduledWakeError, match="content is invalid"):
        run_one_scheduled_wake(
            plan=selected,
            expected_plan_fingerprint=selected.logical_content_fingerprint,
            invoke_one_transition=True,
            coordinator=lambda: tampered,
        )
