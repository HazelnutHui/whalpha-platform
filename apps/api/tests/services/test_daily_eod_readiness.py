from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from tip_api.services.daily_eod_automation import NextAction
from tip_api.services.daily_eod_readiness import (
    AcquisitionAttempt,
    AcquisitionOperatorReview,
    AttemptOutcome,
    DailyEodReadinessPolicy,
    DailyEodReadinessError,
    OperatorReviewDisposition,
    OperatorReviewEvidenceCode,
    OperatorReviewPurpose,
    ProviderRecencyProfile,
    ReadinessNextAction,
    ReadinessStatus,
    plan_daily_eod_readiness,
)


TARGET = date(2026, 8, 27)
LATEST = date(2026, 8, 26)
ACTION = NextAction.PREPARE_IDENTITY_CATCHUP


def _plan(checked_at: datetime, attempts=()):
    return plan_daily_eod_readiness(
        checked_at=checked_at,
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=ACTION,
        attempts=attempts,
    )


def _attempt(
    sequence: int,
    hour: int,
    minute: int,
    outcome: AttemptOutcome,
    retry_after_seconds: int | None = None,
) -> AcquisitionAttempt:
    return AcquisitionAttempt(
        sequence=sequence,
        observed_at=datetime(2026, 8, 27, hour, minute, tzinfo=UTC),
        outcome=outcome,
        retry_after_seconds=retry_after_seconds,
    )


def test_waits_for_close_then_post_close_stabilization() -> None:
    before = _plan(datetime(2026, 8, 27, 19, 59, tzinfo=UTC))
    assert before.status is ReadinessStatus.WAITING_FOR_CLOSE
    assert before.next_check_at == "2026-08-27T20:00:00+00:00"
    stabilizing = _plan(datetime(2026, 8, 27, 20, 15, tzinfo=UTC))
    assert stabilizing.status is ReadinessStatus.STABILIZING
    assert stabilizing.next_check_at == "2026-08-27T20:30:00+00:00"


def test_first_review_is_due_thirty_minutes_after_close_without_completeness_claim() -> None:
    plan = _plan(datetime(2026, 8, 27, 20, 30, tzinfo=UTC))
    assert plan.status is ReadinessStatus.READY_FOR_FETCH_REVIEW
    assert plan.next_action is ReadinessNextAction.REVIEW_FETCH_AUTHORIZATION
    assert plan.provider_completeness_asserted is False
    assert plan.scheduler_enabled is False
    assert plan.external_request_count == 0
    assert plan.production_write_count == 0


def test_current_basic_eod_requires_explicit_release_review() -> None:
    plan = plan_daily_eod_readiness(
        checked_at=datetime(2026, 8, 27, 20, 30, tzinfo=UTC),
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=NextAction.PREPARE_EOD_CATCHUP,
    )

    assert plan.status is ReadinessStatus.AWAITING_OPERATOR_REVIEW
    assert plan.next_action is ReadinessNextAction.OPERATOR_DIAGNOSIS
    assert plan.operator_review_required is True
    assert plan.provider_recency_profile == "massive_stocks_basic_end_of_day"
    assert plan.provider_completeness_asserted is False


def test_basic_eod_review_waits_for_not_before_then_allows_separate_fetch_review() -> None:
    reviewed_at = datetime(2026, 8, 27, 20, 30, tzinfo=UTC)
    not_before = datetime(2026, 8, 27, 21, 0, tzinfo=UTC)
    review = AcquisitionOperatorReview(
        purpose=OperatorReviewPurpose.INITIAL_EOD_AVAILABILITY,
        acquisition_action=NextAction.PREPARE_EOD_CATCHUP,
        attempt_sequence=0,
        reviewed_at=reviewed_at,
        not_before=not_before,
        disposition=OperatorReviewDisposition.AUTHORIZE_ONE_FETCH_AFTER,
        evidence_code=(
            OperatorReviewEvidenceCode.PROVIDER_PLAN_AND_RELEASE_REVIEWED
        ),
    )
    waiting = plan_daily_eod_readiness(
        checked_at=reviewed_at,
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=NextAction.PREPARE_EOD_CATCHUP,
        operator_reviews=(review,),
    )
    ready = plan_daily_eod_readiness(
        checked_at=not_before,
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=NextAction.PREPARE_EOD_CATCHUP,
        operator_reviews=(review,),
    )

    assert waiting.status is ReadinessStatus.WAITING_TO_RETRY
    assert waiting.next_check_at == not_before.isoformat()
    assert ready.status is ReadinessStatus.READY_FOR_FETCH_REVIEW
    assert ready.next_action is ReadinessNextAction.REVIEW_FETCH_AUTHORIZATION
    assert ready.operator_review_count == 1


def test_delayed_profile_does_not_invent_a_basic_plan_gate() -> None:
    plan = plan_daily_eod_readiness(
        checked_at=datetime(2026, 8, 27, 20, 30, tzinfo=UTC),
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=NextAction.PREPARE_EOD_CATCHUP,
        policy=DailyEodReadinessPolicy(
            provider_recency_profile=(
                ProviderRecencyProfile.MASSIVE_STOCKS_DELAYED_15_MINUTES
            )
        ),
    )

    assert plan.status is ReadinessStatus.READY_FOR_FETCH_REVIEW
    assert plan.operator_review_required is False


def test_not_ready_uses_bounded_backoff_then_allows_review() -> None:
    attempts = (_attempt(1, 20, 31, AttemptOutcome.NOT_READY),)
    waiting = _plan(datetime(2026, 8, 27, 20, 40, tzinfo=UTC), attempts)
    assert waiting.status is ReadinessStatus.WAITING_TO_RETRY
    assert waiting.next_check_at == "2026-08-27T20:46:00+00:00"
    ready = _plan(datetime(2026, 8, 27, 20, 46, tzinfo=UTC), attempts)
    assert ready.status is ReadinessStatus.READY_FOR_FETCH_REVIEW
    assert ready.reason_codes[0] == "bounded_retry_due"


def test_rate_limit_honors_longer_retry_after() -> None:
    attempts = (_attempt(1, 20, 31, AttemptOutcome.RATE_LIMITED, 1800),)
    plan = _plan(datetime(2026, 8, 27, 20, 50, tzinfo=UTC), attempts)
    assert plan.status is ReadinessStatus.WAITING_TO_RETRY
    assert plan.next_check_at == "2026-08-27T21:01:00+00:00"


def test_fetch_package_requires_separate_apply_review() -> None:
    plan = _plan(
        datetime(2026, 8, 27, 20, 32, tzinfo=UTC),
        (_attempt(1, 20, 31, AttemptOutcome.FETCH_PACKAGE_READY),),
    )
    assert plan.status is ReadinessStatus.READY_FOR_APPLY_REVIEW
    assert plan.next_action is ReadinessNextAction.REVIEW_APPLY_AUTHORIZATION


@pytest.mark.parametrize(
    "outcome", [AttemptOutcome.PERMANENT_FAILURE, AttemptOutcome.QUALITY_FAILURE]
)
def test_nontransient_failure_blocks_and_alerts(outcome) -> None:
    plan = _plan(
        datetime(2026, 8, 27, 20, 32, tzinfo=UTC),
        (_attempt(1, 20, 31, outcome),),
    )
    assert plan.status is ReadinessStatus.BLOCKED
    assert plan.next_action is ReadinessNextAction.OPERATOR_DIAGNOSIS
    assert plan.alert_required is True


def test_five_transient_attempts_exhaust_the_policy() -> None:
    attempts = (
        _attempt(1, 20, 30, AttemptOutcome.NOT_READY),
        _attempt(2, 20, 45, AttemptOutcome.TRANSIENT_FAILURE),
        _attempt(3, 21, 15, AttemptOutcome.NOT_READY),
        _attempt(4, 22, 15, AttemptOutcome.TRANSIENT_FAILURE),
        _attempt(5, 0, 15, AttemptOutcome.NOT_READY),
    )
    # The fifth attempt is on the following UTC date.
    attempts = (*attempts[:-1], AcquisitionAttempt(5, datetime(2026, 8, 28, 0, 15, tzinfo=UTC), AttemptOutcome.NOT_READY))
    plan = _plan(datetime(2026, 8, 28, 0, 16, tzinfo=UTC), attempts)
    assert plan.status is ReadinessStatus.BLOCKED
    assert plan.reason_codes == ("bounded_attempts_exhausted",)
    assert plan.alert_required is True


def test_elapsed_deadline_enters_missed_session_recovery() -> None:
    plan = _plan(datetime(2026, 8, 28, 3, 0, tzinfo=UTC))
    assert plan.status is ReadinessStatus.MISSED_SESSION_RECOVERY
    assert plan.next_action is ReadinessNextAction.REVIEW_FETCH_AUTHORIZATION
    assert plan.alert_required is True


def test_backlog_requires_oldest_missing_session_first() -> None:
    plan = plan_daily_eod_readiness(
        checked_at=datetime(2026, 8, 27, 21, tzinfo=UTC),
        target_session=date(2026, 8, 26),
        latest_canonical_session=date(2026, 8, 25),
        acquisition_action=NextAction.PREPARE_EOD_CATCHUP,
    )
    assert plan.status is ReadinessStatus.MISSED_SESSION_RECOVERY
    assert plan.missing_session_count == 2
    with pytest.raises(DailyEodReadinessError, match="oldest"):
        plan_daily_eod_readiness(
            checked_at=datetime(2026, 8, 27, 21, tzinfo=UTC),
            target_session=date(2026, 8, 27),
            latest_canonical_session=date(2026, 8, 25),
            acquisition_action=NextAction.PREPARE_EOD_CATCHUP,
        )


def test_early_close_and_dst_come_from_exchange_schedule() -> None:
    plan = plan_daily_eod_readiness(
        checked_at=datetime(2026, 11, 27, 18, 15, tzinfo=UTC),
        target_session=date(2026, 11, 27),
        latest_canonical_session=date(2026, 11, 25),
        acquisition_action=ACTION,
    )
    assert plan.status is ReadinessStatus.STABILIZING
    assert plan.earliest_fetch_review_at == "2026-11-27T18:30:00+00:00"


def test_attempt_history_rejects_backoff_violation_and_bad_retry_after() -> None:
    too_soon = (
        _attempt(1, 20, 30, AttemptOutcome.NOT_READY),
        _attempt(2, 20, 31, AttemptOutcome.NOT_READY),
    )
    with pytest.raises(DailyEodReadinessError, match="backoff"):
        _plan(datetime(2026, 8, 27, 20, 40, tzinfo=UTC), too_soon)
    with pytest.raises(DailyEodReadinessError, match="retry-after"):
        _plan(
            datetime(2026, 8, 27, 20, 40, tzinfo=UTC),
            (_attempt(1, 20, 31, AttemptOutcome.NOT_READY, 20),),
        )


def test_plan_is_deterministic_and_rejects_naive_time_or_offline_action() -> None:
    checked = datetime(2026, 8, 27, 20, 30, tzinfo=UTC)
    assert _plan(checked).logical_content_fingerprint == _plan(checked).logical_content_fingerprint
    with pytest.raises(DailyEodReadinessError, match="timezone-aware"):
        _plan(datetime(2026, 8, 27, 20, 30))
    with pytest.raises(DailyEodReadinessError, match="acquisition"):
        plan_daily_eod_readiness(
            checked_at=checked,
            target_session=TARGET,
            latest_canonical_session=LATEST,
            acquisition_action=NextAction.CALCULATE_PHASE1A,
        )
