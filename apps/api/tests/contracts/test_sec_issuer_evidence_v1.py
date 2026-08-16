from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.security_classification.v1 import (
    IssuerStructure,
    SecEvidenceGrade,
    SecEvidenceResolutionStatus,
    SecEvidenceSubject,
    SecIssuerEvidenceObservationV1,
    SecurityForm,
)

NOW = datetime(2026, 8, 15, tzinfo=UTC)
INSTRUMENT_ID = UUID("00000000-0000-4000-8000-000000000001")


def observation(**overrides):
    values = dict(
        observation_id="a" * 64,
        instrument_id=INSTRUMENT_ID,
        cik="1234",
        source_dataset="inline_xbrl_cover",
        source_document_type="inline_xbrl",
        form_type="10-k",
        accession_number="0000000000-26-000001",
        filing_date=date(2026, 8, 14),
        effective_from=date(2026, 8, 14),
        ticker=" test ",
        exchange=" xnys ",
        evidence_subject=SecEvidenceSubject.SECURITY,
        asserted_security_form=SecurityForm.COMMON_SHARE,
        evidence_grade=SecEvidenceGrade.AUTHORITATIVE_FILING_COVER,
        resolution_status=SecEvidenceResolutionStatus.CANONICAL_MAPPED,
        decision_reasons=("cover_page_security_mapping",),
        source_observed_at=NOW,
        quality_status=QualityStatus.VALID,
        quality_flags=(),
    )
    values.update(overrides)
    return SecIssuerEvidenceObservationV1(**values)


def test_sec_observation_is_frozen_normalized_and_extra_forbidden() -> None:
    value = observation()
    assert value.cik == "0000001234"
    assert value.ticker == "TEST" and value.exchange == "XNYS" and value.form_type == "10-K"
    with pytest.raises(ValidationError):
        value.ticker = "OTHER"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        SecIssuerEvidenceObservationV1.model_validate({**value.model_dump(), "extra": True})


def test_point_in_time_interval_and_utc_are_strict() -> None:
    assert observation(effective_to=date(2026, 8, 16)).is_effective_on(date(2026, 8, 15))
    assert not observation(effective_to=date(2026, 8, 16)).is_effective_on(date(2026, 8, 16))
    with pytest.raises(ValidationError, match="later"):
        observation(effective_to=date(2026, 8, 14))
    with pytest.raises(ValidationError, match="before its filing"):
        observation(filing_date=date(2026, 8, 15))
    with pytest.raises(ValidationError, match="timezone-aware"):
        observation(source_observed_at=datetime(2026, 8, 15))


def test_unmapped_observation_cannot_carry_identity() -> None:
    with pytest.raises(ValidationError, match="must not carry"):
        observation(resolution_status=SecEvidenceResolutionStatus.EXPECTED_UNJOINED)


def test_weak_evidence_cannot_assert_positive_classification() -> None:
    with pytest.raises(ValidationError, match="weak evidence"):
        observation(evidence_grade=SecEvidenceGrade.INSUFFICIENT)


def test_enum_values_cover_authoritative_and_state_machine_evidence() -> None:
    assert SecEvidenceGrade.AUTHORITATIVE_EXPLICIT.value == "authoritative_explicit"
    assert SecEvidenceGrade.AUTHORITATIVE_STATE_MACHINE.value == "authoritative_state_machine"
    assert IssuerStructure.BUSINESS_DEVELOPMENT_COMPANY.value == "business_development_company"
