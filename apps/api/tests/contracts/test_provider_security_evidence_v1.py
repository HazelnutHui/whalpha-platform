from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.security_classification.v1 import (
    ClassificationStatus,
    EvidenceGrade,
    ProviderInstrumentSecurityEvidenceV1,
    ProviderObservationStatus,
    ProviderSecurityObservationV1,
    ProviderSecurityTypeCatalogV1,
    SecurityForm,
    UniverseDisposition,
)

NOW = datetime(2026, 8, 15, tzinfo=UTC)


def test_catalog_contract_is_frozen_normalized_and_extra_forbidden() -> None:
    value = ProviderSecurityTypeCatalogV1(
        provider=" massive ", provider_type_code="cs", provider_type_description="Common Stock",
        provider_asset_class="stocks", provider_locale="us", observed_at=NOW,
        source_endpoint="/v3/reference/tickers/types", evidence_fingerprint="a" * 64,
    )
    assert value.provider_type_code == "CS"
    with pytest.raises(ValidationError):
        value.provider = "other"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ProviderSecurityTypeCatalogV1.model_validate({**value.model_dump(), "extra": True})


def test_instrument_evidence_preserves_provider_code_and_rejects_datetime_date() -> None:
    value = ProviderInstrumentSecurityEvidenceV1(
        as_of_date=date(2026, 8, 14), instrument_id=UUID("00000000-0000-4000-8000-000000000001"),
        provider="massive", provider_ticker=" test ", provider_type_code="newx",
        provider_type_description="New Type", primary_exchange="xnys", security_form_evidence=SecurityForm.UNKNOWN,
        evidence_source="/v3/reference/tickers", evidence_grade=EvidenceGrade.INSUFFICIENT,
        classification_status=ClassificationStatus.UNKNOWN, universe_disposition=UniverseDisposition.QUARANTINE,
        decision_flags=["b", "a", "a"], review_flags=[], provider_observation_ids=("a" * 64,),
        observed_at=NOW, ingested_at=NOW,
    )
    assert value.provider_ticker == "TEST"
    assert value.provider_type_code == "NEWX"
    assert value.decision_flags == ("a", "b")
    with pytest.raises(ValidationError):
        ProviderInstrumentSecurityEvidenceV1.model_validate({**value.model_dump(), "as_of_date": NOW})


def test_observation_allows_unjoined_without_instrument_and_rejects_invalid_mapping() -> None:
    value = ProviderSecurityObservationV1(
        provider_observation_id="b" * 64, as_of_date=date(2026, 8, 14), instrument_id=None,
        provider="massive", provider_ticker="test", provider_type_code="pfd",
        provider_type_description="Preferred Stock", primary_exchange="xnys",
        security_form_evidence=SecurityForm.PREFERRED_SHARE, evidence_source="/v3/reference/tickers",
        evidence_grade=EvidenceGrade.PROVIDER_EXPLICIT,
        observation_status=ProviderObservationStatus.EXPECTED_UNJOINED,
        resolution_method="unresolved", reason_codes=("identity_not_canonical_eligible",),
        review_flags=(), observed_at=NOW, ingested_at=NOW,
    )
    assert value.provider_ticker == "TEST"
    assert value.instrument_id is None
    with pytest.raises(ValidationError, match="requires instrument_id"):
        ProviderSecurityObservationV1.model_validate(
            {**value.model_dump(), "observation_status": "canonical_mapped"}
        )
