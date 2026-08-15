from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.security_classification.v1 import (
    ClassificationMethod,
    ClassificationStatus,
    EvidenceGrade,
    IssuerStructure,
    ListingScope,
    SecurityClassificationV1,
    SecurityForm,
    UniverseDisposition,
    validate_non_overlapping_classifications,
)

ID = UUID("00000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 14, 20, tzinfo=UTC)


def record(**changes: object) -> SecurityClassificationV1:
    values = {
        "taxonomy_version": "v1",
        "ruleset_version": "r1",
        "instrument_id": ID,
        "provider": "fictional",
        "as_of_date": date(2026, 8, 14),
        "effective_from": date(2026, 8, 1),
        "security_form": SecurityForm.COMMON_SHARE,
        "issuer_structure": IssuerStructure.OPERATING_COMPANY,
        "listing_scope": ListingScope.US_DOMESTIC_PRIMARY,
        "primary_exchange": " xnys ",
        "listing_country": "us",
        "issuer_domicile_country": "us",
        "incorporation_country": "us",
        "is_us_listed": True,
        "is_us_domiciled": True,
        "classification_status": ClassificationStatus.RESOLVED,
        "universe_disposition": UniverseDisposition.CANDIDATE_CORE,
        "decision_reason_codes": ["z", "a", "a"],
        "classification_method": ClassificationMethod.AUTHORITATIVE_OVERRIDE,
        "evidence_grade": EvidenceGrade.AUTHORITATIVE,
        "evidence_ids": ["doc:b", "doc:a"],
        "quality_flags": [],
        "observed_at": NOW,
        "reviewed_at": NOW,
        "ingested_at": NOW,
    }
    values.update(changes)
    return SecurityClassificationV1.model_validate(values)


def test_contract_is_frozen_and_forbids_extra() -> None:
    value = record()
    with pytest.raises(ValidationError):
        value.primary_exchange = "XNAS"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        record(extra_field=True)


def test_normalizes_enums_text_utc_and_deterministic_sets() -> None:
    value = record(security_form="common_share", reviewed_at=NOW.astimezone())
    assert value.security_form is SecurityForm.COMMON_SHARE
    assert value.primary_exchange == "XNYS"
    assert value.listing_country == "US"
    assert value.decision_reason_codes == ("a", "z")
    assert value.evidence_ids == ("doc:a", "doc:b")
    assert value.reviewed_at.tzinfo is UTC


@pytest.mark.parametrize("field", ["as_of_date", "effective_from", "effective_to"])
def test_date_fields_reject_datetime(field: str) -> None:
    with pytest.raises(ValidationError):
        record(**{field: NOW})


def test_effective_interval_is_half_open_and_ordered() -> None:
    value = record(effective_to=date(2026, 8, 15))
    assert value.is_effective_on(date(2026, 8, 14))
    assert not value.is_effective_on(date(2026, 8, 15))
    with pytest.raises(ValidationError):
        record(effective_to=date(2026, 8, 1))


@pytest.mark.parametrize(
    "status",
    [ClassificationStatus.UNKNOWN, ClassificationStatus.AMBIGUOUS, ClassificationStatus.MALFORMED],
)
def test_unresolved_statuses_must_be_quarantined(status: ClassificationStatus) -> None:
    with pytest.raises(ValidationError):
        record(classification_status=status)


@pytest.mark.parametrize("grade", [EvidenceGrade.HEURISTIC_FLAG_ONLY, EvidenceGrade.INSUFFICIENT])
def test_weak_evidence_cannot_create_positive_candidate(grade: EvidenceGrade) -> None:
    with pytest.raises(ValidationError):
        record(evidence_grade=grade)


def test_core_and_international_candidate_semantics_are_distinct() -> None:
    international = record(
        security_form=SecurityForm.ORDINARY_SHARE,
        listing_scope=ListingScope.US_LISTED_FOREIGN,
        issuer_domicile_country="CA",
        incorporation_country="CA",
        is_us_domiciled=False,
        universe_disposition=UniverseDisposition.CANDIDATE_US_LISTED_INTERNATIONAL,
    )
    assert international.listing_scope is ListingScope.US_LISTED_FOREIGN
    with pytest.raises(ValidationError):
        record(is_us_domiciled=False)


def test_overlapping_periods_hard_fail_but_ticker_independent_identity_survives() -> None:
    first = record(effective_to=date(2026, 8, 20))
    overlap = record(as_of_date=date(2026, 8, 20), effective_from=date(2026, 8, 19))
    with pytest.raises(ValueError, match="overlap"):
        validate_non_overlapping_classifications((first, overlap))

    successor = record(as_of_date=date(2026, 8, 20), effective_from=date(2026, 8, 20))
    validate_non_overlapping_classifications((first, successor))
    assert first.instrument_id == successor.instrument_id


def test_datetime_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        record(observed_at=datetime(2026, 8, 14, 20))
