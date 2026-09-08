from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    ClassificationAssignmentBasis,
    ClassificationCoverageDecisionV1,
    ClassificationCoverageStatus,
    ClassificationDefinitionStatus,
    ClassificationDefinitionV1,
    ClassificationEligibilityScope,
    ClassificationIdentityEvidenceKind,
    ClassificationMembershipRole,
    ClassificationMembershipV1,
    ClassificationObservationStatus,
    ClassificationReviewStatus,
    ClassificationSourceObservationV1,
    ClassificationType,
    ExternalClassificationPathNodeV1,
    KnowledgeTimeStatus,
    ResolutionStatus,
)


INSTRUMENT_ID = UUID("11111111-1111-4111-8111-111111111111")
SECTOR_ID = UUID("22222222-2222-4222-8222-222222222222")
INDUSTRY_GROUP_ID = UUID("33333333-3333-4333-8333-333333333333")
OBSERVED_AT = datetime(2026, 9, 8, 20, 0, tzinfo=UTC)
AVAILABLE_AT = OBSERVED_AT - timedelta(hours=1)


def path() -> tuple[ExternalClassificationPathNodeV1, ...]:
    return (
        ExternalClassificationPathNodeV1(level=1, code="45", name="Information Technology"),
        ExternalClassificationPathNodeV1(level=2, code="4510", name="Software & Services"),
    )


def observation(**updates: object) -> ClassificationSourceObservationV1:
    payload: dict[str, object] = {
        "source_observation_id": "gics-company-1-revision-7",
        "provider": "sp-global",
        "as_of_date": date(2026, 9, 4),
        "source_entity_id": "company-1",
        "source_security_id": "security-1",
        "instrument_id": INSTRUMENT_ID,
        "identity_resolution_status": ResolutionStatus.RESOLVED,
        "identity_evidence": (ClassificationIdentityEvidenceKind.SHARE_CLASS_FIGI,),
        "assignment_basis": ClassificationAssignmentBasis.DIRECT_SECURITY,
        "external_taxonomy": "GICS",
        "external_taxonomy_version": "2026",
        "external_classification_code": "4510",
        "external_classification_path": path(),
        "valid_from": date(2024, 1, 1),
        "knowledge_time_status": KnowledgeTimeStatus.SOURCE_TIMESTAMP,
        "source_available_at": AVAILABLE_AT,
        "provider_updated_at": AVAILABLE_AT,
        "observed_at": OBSERVED_AT,
        "revision_id": "7",
        "correction_status": ClassificationObservationStatus.ACTIVE,
        "permission_review_fingerprint": "a" * 64,
        "eligibility_scope": ClassificationEligibilityScope.HISTORICAL_RESEARCH,
        "quality_status": QualityStatus.VALID,
    }
    payload.update(updates)
    return ClassificationSourceObservationV1.model_validate(payload)


def membership(**updates: object) -> ClassificationMembershipV1:
    payload: dict[str, object] = {
        "instrument_id": INSTRUMENT_ID,
        "classification_id": INDUSTRY_GROUP_ID,
        "valid_from": date(2024, 1, 1),
        "membership_role": ClassificationMembershipRole.PRIMARY,
        "confidence": Decimal("1"),
        "source": "sp-global",
        "source_observation_id": "gics-company-1-revision-7",
        "assignment_basis": ClassificationAssignmentBasis.DIRECT_SECURITY,
        "source_available_at": AVAILABLE_AT,
        "eligibility_scope": ClassificationEligibilityScope.HISTORICAL_RESEARCH,
        "assigned_at": OBSERVED_AT,
        "review_status": ClassificationReviewStatus.AUTO_RESOLVED,
        "methodology_version": "whalpha-traditional-v1",
        "quality_status": QualityStatus.VALID,
    }
    payload.update(updates)
    return ClassificationMembershipV1.model_validate(payload)


def test_historical_observation_preserves_validity_knowledge_and_stable_identity() -> None:
    record = observation()

    assert record.instrument_id == INSTRUMENT_ID
    assert record.valid_from == date(2024, 1, 1)
    assert record.source_available_at == AVAILABLE_AT
    assert record.eligibility_scope is ClassificationEligibilityScope.HISTORICAL_RESEARCH


def test_current_display_observation_can_keep_unknown_knowledge_time() -> None:
    record = observation(
        knowledge_time_status=KnowledgeTimeStatus.UNAVAILABLE,
        source_available_at=None,
        eligibility_scope=ClassificationEligibilityScope.CURRENT_DISPLAY_ONLY,
    )

    assert record.source_available_at is None


def test_historical_observation_rejects_missing_source_availability() -> None:
    with pytest.raises(ValidationError, match="historical eligibility requires"):
        observation(
            knowledge_time_status=KnowledgeTimeStatus.UNAVAILABLE,
            source_available_at=None,
        )


def test_direct_security_observation_requires_stable_security_evidence() -> None:
    with pytest.raises(ValidationError, match="stable security evidence"):
        observation(
            identity_evidence=(ClassificationIdentityEvidenceKind.REVIEWED_ISSUER_PROJECTION,),
        )


def test_issuer_projection_requires_reviewed_projection_evidence() -> None:
    with pytest.raises(ValidationError, match="reviewed projection evidence"):
        observation(
            assignment_basis=ClassificationAssignmentBasis.ISSUER_PROJECTED,
            identity_evidence=(ClassificationIdentityEvidenceKind.COMPOSITE_FIGI,),
        )


def test_unresolved_observation_is_quarantined_without_instrument_authority() -> None:
    record = observation(
        source_security_id=None,
        instrument_id=None,
        identity_resolution_status=ResolutionStatus.AMBIGUOUS,
        identity_evidence=(),
        assignment_basis=ClassificationAssignmentBasis.UNRESOLVED,
        correction_status=ClassificationObservationStatus.QUARANTINED,
        eligibility_scope=ClassificationEligibilityScope.INELIGIBLE,
        quality_status=QualityStatus.PENDING_REVIEW,
        quality_flags=("multiple stable-id candidates",),
    )

    assert record.instrument_id is None
    assert record.quality_flags == ("multiple_stable_id_candidates",)


def test_external_path_must_be_contiguous_and_end_at_assigned_code() -> None:
    with pytest.raises(ValidationError, match="terminal path node"):
        observation(external_classification_code="451030")
    with pytest.raises(ValidationError, match="contiguous"):
        observation(
            external_classification_path=(
                ExternalClassificationPathNodeV1(level=2, code="4510", name="Software"),
            )
        )


def test_provider_or_source_time_cannot_arrive_after_observation() -> None:
    with pytest.raises(ValidationError, match="provider_updated_at"):
        observation(provider_updated_at=OBSERVED_AT + timedelta(seconds=1))
    with pytest.raises(ValidationError, match="source_available_at"):
        observation(source_available_at=OBSERVED_AT + timedelta(seconds=1))


def test_cancelled_observation_cannot_be_eligible() -> None:
    with pytest.raises(ValidationError, match="cancelled or quarantined"):
        observation(
            correction_status=ClassificationObservationStatus.CANCELLED,
            supersedes_source_observation_id="gics-company-1-revision-6",
            quality_flags=("provider_cancelled",),
        )


def test_corrected_observation_requires_explicit_superseded_record() -> None:
    with pytest.raises(ValidationError, match="superseded ID"):
        observation(correction_status=ClassificationObservationStatus.CORRECTED)


def test_active_observation_cannot_claim_to_supersede_another_record() -> None:
    with pytest.raises(ValidationError, match="only corrected or cancelled"):
        observation(
            supersedes_source_observation_id="gics-company-1-revision-6",
        )


def test_traditional_definition_enforces_parent_shape() -> None:
    sector = ClassificationDefinitionV1(
        classification_id=SECTOR_ID,
        classification_type=ClassificationType.SECTOR,
        name="Information Technology",
        methodology_version="whalpha-traditional-v1",
        status=ClassificationDefinitionStatus.ACTIVE,
        valid_from=date(2024, 1, 1),
        source="whalpha",
    )
    group = ClassificationDefinitionV1(
        classification_id=INDUSTRY_GROUP_ID,
        classification_type=ClassificationType.INDUSTRY_GROUP,
        name="Software & Services",
        parent_classification_id=SECTOR_ID,
        methodology_version="whalpha-traditional-v1",
        status=ClassificationDefinitionStatus.ACTIVE,
        valid_from=date(2024, 1, 1),
        source="whalpha",
    )

    assert sector.parent_classification_id is None
    assert group.parent_classification_id == SECTOR_ID
    with pytest.raises(ValidationError, match="requires a parent"):
        group.model_copy(update={"parent_classification_id": None}).model_validate(
            group.model_dump() | {"parent_classification_id": None}
        )


def test_membership_rejects_future_source_time_and_float_confidence() -> None:
    with pytest.raises(ValidationError, match="must not follow assigned_at"):
        membership(source_available_at=OBSERVED_AT + timedelta(seconds=1))
    with pytest.raises(ValidationError, match="not float"):
        membership(confidence=0.9)


def test_historical_membership_requires_source_availability() -> None:
    with pytest.raises(ValidationError, match="requires source_available_at"):
        membership(source_available_at=None)


def test_coverage_decision_keeps_unknown_bucket_explicit() -> None:
    classified = ClassificationCoverageDecisionV1(
        instrument_id=INSTRUMENT_ID,
        as_of_date=date(2026, 9, 4),
        status=ClassificationCoverageStatus.CLASSIFIED,
        source_observation_ids=("gics-company-1-revision-7",),
        classification_ids=(INDUSTRY_GROUP_ID,),
        eligibility_scope=ClassificationEligibilityScope.CURRENT_DISPLAY_ONLY,
        evaluated_at=OBSERVED_AT,
        quality_status=QualityStatus.VALID,
    )
    missing = ClassificationCoverageDecisionV1(
        instrument_id=UUID("44444444-4444-4444-8444-444444444444"),
        as_of_date=date(2026, 9, 4),
        status=ClassificationCoverageStatus.NOT_COVERED,
        eligibility_scope=ClassificationEligibilityScope.INELIGIBLE,
        reason_codes=("source_not_covered",),
        evaluated_at=OBSERVED_AT,
        quality_status=QualityStatus.PENDING_REVIEW,
    )

    assert classified.classification_ids == (INDUSTRY_GROUP_ID,)
    assert missing.source_observation_ids == ()


def test_contracts_are_frozen_and_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        observation(unknown_field="forbidden")
