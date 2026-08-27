from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from tip_api.services.daily_eod_alerting import (
    AlertSeverity,
    DailyEodAlertingError,
    plan_daily_eod_alert,
    validate_daily_eod_alert_intent,
)
from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorResult,
)


TARGET = date(2026, 8, 27)


def result(
    status: CoordinatorStatus,
    *,
    alert_required: bool,
    source_fingerprint: str = "a" * 64,
) -> DailyEodCoordinatorResult:
    next_action = {
        CoordinatorStatus.BLOCKED: "operator_diagnosis",
        CoordinatorStatus.RECOVERY_REQUIRED: "recover_offline_action",
        CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED: (
            "review_fetch_authorization"
        ),
        CoordinatorStatus.WAITING: "wait",
    }[status]
    return DailyEodCoordinatorResult(
        status=status,
        target_session=TARGET.isoformat(),
        next_action=next_action,
        reason_codes=("fixture_reason",),
        automation_plan_fingerprint="b" * 64,
        readiness_plan_fingerprint=None,
        transition_fingerprint=None,
        external_request_count=0,
        production_write_count=0,
        alert_required=alert_required,
        logical_content_fingerprint=source_fingerprint,
    )


@pytest.mark.parametrize(
    ("status", "category", "severity"),
    (
        (CoordinatorStatus.BLOCKED, "pipeline_blocked", AlertSeverity.CRITICAL),
        (
            CoordinatorStatus.RECOVERY_REQUIRED,
            "interrupted_transition",
            AlertSeverity.WARNING,
        ),
        (
            CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED,
            "missed_session_attention",
            AlertSeverity.WARNING,
        ),
    ),
)
def test_builds_channel_neutral_non_delivering_intent(
    status: CoordinatorStatus,
    category: str,
    severity: AlertSeverity,
) -> None:
    intent = plan_daily_eod_alert(
        target_session=TARGET,
        result=result(status, alert_required=True),
    )

    assert intent is not None
    assert intent.category == category
    assert intent.severity is severity
    assert intent.delivery_attempted is False
    assert intent.external_request_count == 0
    assert intent.production_write_count == 0
    assert len(intent.deduplication_key) == 64
    assert intent.as_dict()["severity"] == severity.value


def test_identical_source_has_a_stable_deduplication_key() -> None:
    first = plan_daily_eod_alert(
        target_session=TARGET,
        result=result(CoordinatorStatus.BLOCKED, alert_required=True),
    )
    second = plan_daily_eod_alert(
        target_session=TARGET,
        result=result(CoordinatorStatus.BLOCKED, alert_required=True),
    )
    changed = plan_daily_eod_alert(
        target_session=TARGET,
        result=result(
            CoordinatorStatus.BLOCKED,
            alert_required=True,
            source_fingerprint="c" * 64,
        ),
    )

    assert first is not None and second is not None and changed is not None
    assert first == second
    assert first.deduplication_key != changed.deduplication_key


def test_non_alerting_result_produces_no_intent() -> None:
    assert (
        plan_daily_eod_alert(
            target_session=TARGET,
            result=result(CoordinatorStatus.WAITING, alert_required=False),
        )
        is None
    )


def test_rejects_false_alert_status_and_malformed_source() -> None:
    with pytest.raises(DailyEodAlertingError, match="unsupported"):
        plan_daily_eod_alert(
            target_session=TARGET,
            result=result(CoordinatorStatus.WAITING, alert_required=True),
        )
    with pytest.raises(DailyEodAlertingError, match="malformed"):
        plan_daily_eod_alert(
            target_session=TARGET,
            result=result(
                CoordinatorStatus.BLOCKED,
                alert_required=True,
                source_fingerprint="bad",
            ),
        )


def test_rejects_target_session_mismatch() -> None:
    with pytest.raises(DailyEodAlertingError, match="malformed"):
        plan_daily_eod_alert(
            target_session=date(2026, 8, 28),
            result=result(CoordinatorStatus.BLOCKED, alert_required=True),
        )


def test_formal_intent_validation_rejects_tampering() -> None:
    intent = plan_daily_eod_alert(
        target_session=TARGET,
        result=result(CoordinatorStatus.BLOCKED, alert_required=True),
    )
    assert intent is not None
    validate_daily_eod_alert_intent(intent)

    with pytest.raises(DailyEodAlertingError, match="inconsistent"):
        validate_daily_eod_alert_intent(
            replace(intent, next_action="silently_changed")
        )
