from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tip_api.services.daily_eod_acquisition_custody import (
    DailyEodAcquisitionConfig,
    acquisition_attempts_from_events,
    acquisition_operator_reviews_from_events,
    record_acquisition_outcome,
    reserve_acquisition_attempt,
)
from tip_api.services.daily_eod_acquisition_operator_review import (
    DailyEodAcquisitionOperatorReviewError,
    record_acquisition_operator_review,
)
from tip_api.services.daily_eod_automation import NextAction
from tip_api.services.daily_eod_readiness import (
    AttemptOutcome,
    OperatorReviewDisposition,
    OperatorReviewEvidenceCode,
    OperatorReviewPurpose,
    ReadinessNextAction,
    ReadinessStatus,
    plan_daily_eod_readiness,
)
from tip_api.services.daily_eod_run_journal import locked_daily_eod_run_journal


TARGET = date(2026, 8, 27)
LATEST = date(2026, 8, 26)
READY_AT = datetime(2026, 8, 27, 20, 30, tzinfo=UTC)


def _config(tmp_path: Path, name: str = "eod-fetch") -> DailyEodAcquisitionConfig:
    root = tmp_path / "run-root"
    if not root.exists():
        root.mkdir(mode=0o700)
        root.chmod(0o700)
    return DailyEodAcquisitionConfig(
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=NextAction.PREPARE_EOD_CATCHUP,
        package_path=Path(f"/tmp/{tmp_path.parent.name}-{tmp_path.name}-{name}"),
        run_root=root,
    )


def _history(config: DailyEodAcquisitionConfig):
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=TARGET,
    ) as journal:
        events = journal.read_events()
    attempts = acquisition_attempts_from_events(
        events,
        target_session=TARGET,
        acquisition_action=config.acquisition_action,
    )
    reviews = acquisition_operator_reviews_from_events(
        events,
        target_session=TARGET,
        acquisition_action=config.acquisition_action,
    )
    return events, attempts, reviews


def test_initial_basic_eod_review_is_immutable_bounded_and_nonexecuting(tmp_path) -> None:
    config = _config(tmp_path)
    release_at = datetime(2026, 8, 27, 21, 0, tzinfo=UTC)

    result = record_acquisition_operator_review(
        config=config,
        purpose=OperatorReviewPurpose.INITIAL_EOD_AVAILABILITY,
        disposition=OperatorReviewDisposition.AUTHORIZE_ONE_FETCH_AFTER,
        evidence_code=(
            OperatorReviewEvidenceCode.PROVIDER_PLAN_AND_RELEASE_REVIEWED
        ),
        not_before=release_at,
        clock=lambda: READY_AT,
    )

    assert result.event.event_type == "acquisition_operator_reviewed"
    assert result.readiness_plan.status is ReadinessStatus.WAITING_TO_RETRY
    assert result.readiness_plan.next_check_at == release_at.isoformat()
    assert result.external_request_count == 0
    assert result.production_write_count == 0
    assert result.fetch_authorized_by_review is False
    assert result.scheduler_enabled is False
    _, attempts, reviews = _history(config)
    assert attempts == ()
    assert reviews == (result.review,)


def test_duplicate_initial_review_and_wrong_action_fail_closed(tmp_path) -> None:
    config = _config(tmp_path)
    kwargs = {
        "config": config,
        "purpose": OperatorReviewPurpose.INITIAL_EOD_AVAILABILITY,
        "disposition": OperatorReviewDisposition.AUTHORIZE_ONE_FETCH_AFTER,
        "evidence_code": (
            OperatorReviewEvidenceCode.PROVIDER_PLAN_AND_RELEASE_REVIEWED
        ),
        "not_before": READY_AT,
        "clock": lambda: READY_AT,
    }
    record_acquisition_operator_review(**kwargs)
    with pytest.raises(
        DailyEodAcquisitionOperatorReviewError,
        match="already exists",
    ):
        record_acquisition_operator_review(**kwargs)

    identity = DailyEodAcquisitionConfig(
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=NextAction.PREPARE_IDENTITY_CATCHUP,
        package_path=Path(f"/tmp/{tmp_path.name}-identity"),
        run_root=config.run_root,
    )
    with pytest.raises(
        DailyEodAcquisitionOperatorReviewError,
        match="not applicable",
    ):
        record_acquisition_operator_review(
            config=identity,
            purpose=OperatorReviewPurpose.INITIAL_EOD_AVAILABILITY,
            disposition=OperatorReviewDisposition.AUTHORIZE_ONE_FETCH_AFTER,
            evidence_code=(
                OperatorReviewEvidenceCode.PROVIDER_PLAN_AND_RELEASE_REVIEWED
            ),
            not_before=READY_AT,
            clock=lambda: READY_AT,
        )


def test_exact_terminal_review_releases_only_the_next_bounded_fetch(tmp_path) -> None:
    config = _config(tmp_path)
    initial = record_acquisition_operator_review(
        config=config,
        purpose=OperatorReviewPurpose.INITIAL_EOD_AVAILABILITY,
        disposition=OperatorReviewDisposition.AUTHORIZE_ONE_FETCH_AFTER,
        evidence_code=(
            OperatorReviewEvidenceCode.PROVIDER_PLAN_AND_RELEASE_REVIEWED
        ),
        not_before=READY_AT,
        clock=lambda: READY_AT,
    )
    reserve_acquisition_attempt(
        config=config,
        checked_at=READY_AT,
        expected_readiness_fingerprint=(
            initial.readiness_plan.logical_content_fingerprint
        ),
        clock=lambda: READY_AT,
    )
    failure = record_acquisition_outcome(
        config=config,
        outcome=AttemptOutcome.PERMANENT_FAILURE,
        request_count=1,
        provider_http_status_code=403,
        clock=lambda: datetime(2026, 8, 27, 20, 31, tzinfo=UTC),
    )
    review_at = datetime(2026, 8, 27, 21, 0, tzinfo=UTC)

    with pytest.raises(
        DailyEodAcquisitionOperatorReviewError,
        match="exact latest failure",
    ):
        record_acquisition_operator_review(
            config=config,
            purpose=OperatorReviewPurpose.TERMINAL_FAILURE_RETRY,
            disposition=OperatorReviewDisposition.AUTHORIZE_ONE_FETCH_AFTER,
            evidence_code=OperatorReviewEvidenceCode.LOCAL_CONFIGURATION_CORRECTED,
            not_before=review_at,
            expected_terminal_event_fingerprint="f" * 64,
            clock=lambda: review_at,
        )

    reviewed = record_acquisition_operator_review(
        config=config,
        purpose=OperatorReviewPurpose.TERMINAL_FAILURE_RETRY,
        disposition=OperatorReviewDisposition.AUTHORIZE_ONE_FETCH_AFTER,
        evidence_code=OperatorReviewEvidenceCode.LOCAL_CONFIGURATION_CORRECTED,
        not_before=review_at,
        expected_terminal_event_fingerprint=failure.event.event_fingerprint,
        clock=lambda: review_at,
    )

    assert reviewed.review.source_event_fingerprint == failure.event.event_fingerprint
    assert reviewed.readiness_plan.status is ReadinessStatus.READY_FOR_FETCH_REVIEW
    assert (
        reviewed.readiness_plan.next_action
        is ReadinessNextAction.REVIEW_FETCH_AUTHORIZATION
    )
    assert reviewed.readiness_plan.reason_codes == (
        "operator_diagnosis_authorized_one_fetch",
    )
    second = _config(tmp_path, "eod-fetch-2")
    reserved = reserve_acquisition_attempt(
        config=second,
        checked_at=review_at,
        expected_readiness_fingerprint=(
            reviewed.readiness_plan.logical_content_fingerprint
        ),
        clock=lambda: review_at,
    )
    assert reserved.event.details["attempt_number"] == 2


def test_terminal_failure_without_review_remains_blocked(tmp_path) -> None:
    config = _config(tmp_path)
    initial = record_acquisition_operator_review(
        config=config,
        purpose=OperatorReviewPurpose.INITIAL_EOD_AVAILABILITY,
        disposition=OperatorReviewDisposition.AUTHORIZE_ONE_FETCH_AFTER,
        evidence_code=(
            OperatorReviewEvidenceCode.PROVIDER_PLAN_AND_RELEASE_REVIEWED
        ),
        not_before=READY_AT,
        clock=lambda: READY_AT,
    )
    reserve_acquisition_attempt(
        config=config,
        checked_at=READY_AT,
        expected_readiness_fingerprint=initial.readiness_plan.logical_content_fingerprint,
        clock=lambda: READY_AT,
    )
    failure = record_acquisition_outcome(
        config=config,
        outcome=AttemptOutcome.PERMANENT_FAILURE,
        request_count=1,
        provider_http_status_code=403,
        clock=lambda: datetime(2026, 8, 27, 20, 31, tzinfo=UTC),
    )
    assert failure.readiness_plan is not None
    assert failure.readiness_plan.status is ReadinessStatus.BLOCKED
    assert failure.readiness_plan.operator_review_required is False
