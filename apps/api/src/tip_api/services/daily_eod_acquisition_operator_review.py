"""Immutable operator review for one Basic EOD release or terminal fetch failure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from tip_api.services.daily_eod_acquisition_custody import (
    DailyEodAcquisitionConfig,
    acquisition_attempts_from_events,
    acquisition_operator_reviews_from_events,
)
from tip_api.services.daily_eod_automation import NextAction
from tip_api.services.daily_eod_readiness import (
    AcquisitionAttempt,
    AcquisitionOperatorReview,
    AttemptOutcome,
    DailyEodReadinessPlan,
    OperatorReviewDisposition,
    OperatorReviewEvidenceCode,
    OperatorReviewPurpose,
    plan_daily_eod_readiness,
)
from tip_api.services.daily_eod_run_journal import (
    ACQUISITION_REVIEW_EVENT,
    DailyEodRunEvent,
    locked_daily_eod_run_journal,
    new_attempt_id,
    unresolved_started_event,
)


CONTRACT_VERSION = "daily-eod-acquisition-operator-review/1.0"


class DailyEodAcquisitionOperatorReviewError(RuntimeError):
    """Raised when an operator review is not exact, bounded, and non-duplicative."""


@dataclass(frozen=True, slots=True)
class AcquisitionOperatorReviewResult:
    review: AcquisitionOperatorReview
    event: DailyEodRunEvent
    readiness_plan: DailyEodReadinessPlan
    external_request_count: int = 0
    production_write_count: int = 0
    credential_access_count: int = 0
    fetch_authorized_by_review: bool = False
    scheduler_enabled: bool = False
    publication_authorized: bool = False
    deployment_authorized: bool = False
    contract_version: str = CONTRACT_VERSION

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "purpose": self.review.purpose.value,
            "disposition": self.review.disposition.value,
            "attempt_sequence": self.review.attempt_sequence,
            "not_before": self.review.not_before.isoformat(),
            "review_fingerprint": self.review.logical_fingerprint,
            "event_fingerprint": self.event.event_fingerprint,
            "readiness_plan_fingerprint": (
                self.readiness_plan.logical_content_fingerprint
            ),
            "external_request_count": self.external_request_count,
            "production_write_count": self.production_write_count,
            "credential_access_count": self.credential_access_count,
            "fetch_authorized_by_review": self.fetch_authorized_by_review,
            "scheduler_enabled": self.scheduler_enabled,
            "publication_authorized": self.publication_authorized,
            "deployment_authorized": self.deployment_authorized,
        }


Clock = Callable[[], datetime]


def record_acquisition_operator_review(
    *,
    config: DailyEodAcquisitionConfig,
    purpose: OperatorReviewPurpose,
    disposition: OperatorReviewDisposition,
    evidence_code: OperatorReviewEvidenceCode,
    not_before: datetime,
    expected_terminal_event_fingerprint: str | None = None,
    clock: Clock = lambda: datetime.now(UTC),
) -> AcquisitionOperatorReviewResult:
    """Append one review decision; never reserve or execute the resulting fetch."""

    if (
        not isinstance(config, DailyEodAcquisitionConfig)
        or not isinstance(purpose, OperatorReviewPurpose)
        or not isinstance(disposition, OperatorReviewDisposition)
        or not isinstance(evidence_code, OperatorReviewEvidenceCode)
        or not config.package_path.is_absolute()
        or config.package_path.parent != Path("/tmp")
        or config.package_path.name.startswith(".")
    ):
        raise DailyEodAcquisitionOperatorReviewError(
            "operator review inputs are invalid"
        )
    if (
        purpose is OperatorReviewPurpose.INITIAL_EOD_AVAILABILITY
        and disposition is OperatorReviewDisposition.AUTHORIZE_ONE_FETCH_AFTER
        and evidence_code
        is not OperatorReviewEvidenceCode.PROVIDER_PLAN_AND_RELEASE_REVIEWED
    ):
        raise DailyEodAcquisitionOperatorReviewError(
            "initial EOD release requires plan-and-release review evidence"
        )
    observed_at = _aware_utc(clock())
    release_at = _aware_utc(not_before)
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        events = journal.read_events()
        if unresolved_started_event(events) is not None:
            raise DailyEodAcquisitionOperatorReviewError(
                "operator review cannot overlap an unresolved transition"
            )
        attempts = acquisition_attempts_from_events(
            events,
            target_session=config.target_session,
            acquisition_action=config.acquisition_action,
        )
        prior_reviews = acquisition_operator_reviews_from_events(
            events,
            target_session=config.target_session,
            acquisition_action=config.acquisition_action,
        )
        attempt_sequence, source_fingerprint = _review_binding(
            config=config,
            purpose=purpose,
            attempts=attempts,
            expected_terminal_event_fingerprint=(
                expected_terminal_event_fingerprint
            ),
        )
        if any(
            item.purpose is purpose
            and item.attempt_sequence == attempt_sequence
            for item in prior_reviews
        ):
            raise DailyEodAcquisitionOperatorReviewError(
                "operator review already exists for this exact gate"
            )
        review = AcquisitionOperatorReview(
            purpose=purpose,
            acquisition_action=config.acquisition_action,
            attempt_sequence=attempt_sequence,
            reviewed_at=observed_at,
            not_before=release_at,
            disposition=disposition,
            evidence_code=evidence_code,
            source_event_fingerprint=source_fingerprint,
        )
        # Use the pure contract to reject contradictory evidence or timing
        # before the immutable event is appended.
        readiness = plan_daily_eod_readiness(
            checked_at=observed_at,
            target_session=config.target_session,
            latest_canonical_session=config.latest_canonical_session,
            acquisition_action=config.acquisition_action,
            attempts=attempts,
            operator_reviews=(*prior_reviews, review),
        )
        if (
            purpose is OperatorReviewPurpose.INITIAL_EOD_AVAILABILITY
            and readiness.expected_latest_session != config.target_session.isoformat()
        ):
            raise DailyEodAcquisitionOperatorReviewError(
                "initial EOD availability review is limited to the current session"
            )
        review_id = new_attempt_id(
            target_session=config.target_session,
            plan_fingerprint=review.logical_fingerprint,
            sequence=len(events) + 1,
        )
        event = journal.append(
            event_type=ACQUISITION_REVIEW_EVENT,
            attempt_id=review_id,
            observed_at=observed_at,
            details={
                "review_contract": CONTRACT_VERSION,
                "acquisition_action": config.acquisition_action.value,
                "purpose": purpose.value,
                "attempt_sequence": attempt_sequence,
                "disposition": disposition.value,
                "evidence_code": evidence_code.value,
                "not_before": release_at.isoformat(),
                "source_event_fingerprint": source_fingerprint,
                "review_fingerprint": review.logical_fingerprint,
                "external_request_count": 0,
                "production_write_count": 0,
                "fetch_authorized_by_review": False,
                "scheduler_enabled": False,
                "publication_authorized": False,
                "deployment_authorized": False,
            },
        )
        reread_reviews = acquisition_operator_reviews_from_events(
            journal.read_events(),
            target_session=config.target_session,
            acquisition_action=config.acquisition_action,
        )
        if not reread_reviews or reread_reviews[-1] != review:
            raise DailyEodAcquisitionOperatorReviewError(
                "operator review did not formally reread"
            )
        return AcquisitionOperatorReviewResult(
            review=review,
            event=event,
            readiness_plan=readiness,
        )


def _review_binding(
    *,
    config: DailyEodAcquisitionConfig,
    purpose: OperatorReviewPurpose,
    attempts: tuple[AcquisitionAttempt, ...],
    expected_terminal_event_fingerprint: str | None,
) -> tuple[int, str | None]:
    if purpose is OperatorReviewPurpose.INITIAL_EOD_AVAILABILITY:
        if (
            config.acquisition_action is not NextAction.PREPARE_EOD_CATCHUP
            or attempts
            or expected_terminal_event_fingerprint is not None
        ):
            raise DailyEodAcquisitionOperatorReviewError(
                "initial EOD availability review is not applicable"
            )
        return 0, None
    if purpose is not OperatorReviewPurpose.TERMINAL_FAILURE_RETRY or not attempts:
        raise DailyEodAcquisitionOperatorReviewError(
            "terminal failure review is not applicable"
        )
    last = attempts[-1]
    if (
        last.outcome
        not in {AttemptOutcome.PERMANENT_FAILURE, AttemptOutcome.QUALITY_FAILURE}
        or expected_terminal_event_fingerprint != last.terminal_event_fingerprint
    ):
        raise DailyEodAcquisitionOperatorReviewError(
            "terminal failure review does not match the exact latest failure"
        )
    return last.sequence, last.terminal_event_fingerprint


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodAcquisitionOperatorReviewError(
            "operator review timestamps must be timezone-aware"
        )
    return value.astimezone(UTC)
