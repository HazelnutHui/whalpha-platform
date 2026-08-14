from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    ProviderInstrumentIdentityV1,
    ResolutionMethod,
    ResolutionStatus,
)

INSTRUMENT_ID = UUID("11111111-1111-4111-8111-111111111111")


def test_resolved_identity_contract_normalizes_fields():
    record = ProviderInstrumentIdentityV1(
        provider=" massive ",
        as_of_date=date(2026, 8, 13),
        provider_ticker=" testa ",
        composite_figi=" figi1 ",
        share_class_figi=" figi2 ",
        cik="000123",
        canonical_instrument_id=INSTRUMENT_ID,
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_method=ResolutionMethod.SHARE_CLASS_FIGI,
        valid_from=date(2026, 8, 13),
        source_updated_at=datetime(2026, 8, 14, 1, tzinfo=UTC),
        ingested_at=datetime(2026, 8, 14, 2, tzinfo=UTC),
        quality_status=QualityStatus.VALID,
        quality_flags=("Needs Review", "needs_review"),
    )
    assert record.provider == "massive"
    assert record.provider_ticker == "TESTA"
    assert record.share_class_figi == "FIGI2"
    assert record.cik == "000123"
    assert record.quality_flags == ("needs_review",)


def test_unresolved_allows_missing_canonical_id():
    record = ProviderInstrumentIdentityV1(
        provider="massive",
        as_of_date=date(2026, 8, 13),
        provider_ticker="TESTA",
        canonical_instrument_id=None,
        resolution_status=ResolutionStatus.UNRESOLVED,
        resolution_method=ResolutionMethod.UNRESOLVED,
        valid_from=date(2026, 8, 13),
        ingested_at=datetime(2026, 8, 14, tzinfo=UTC),
        quality_status=QualityStatus.WARNING,
        quality_flags=("no_stable_security_identifier",),
    )
    assert record.canonical_instrument_id is None


def test_resolved_requires_canonical_id_and_stable_method():
    with pytest.raises(ValidationError):
        ProviderInstrumentIdentityV1(
            provider="massive",
            as_of_date=date(2026, 8, 13),
            provider_ticker="TESTA",
            resolution_status=ResolutionStatus.RESOLVED,
            resolution_method=ResolutionMethod.UNRESOLVED,
            valid_from=date(2026, 8, 13),
            ingested_at=datetime(2026, 8, 14, tzinfo=UTC),
            quality_status=QualityStatus.VALID,
        )


def test_ambiguous_and_rejected_require_quality_flags():
    with pytest.raises(ValidationError):
        ProviderInstrumentIdentityV1(
            provider="massive",
            as_of_date=date(2026, 8, 13),
            provider_ticker="TESTA",
            resolution_status=ResolutionStatus.AMBIGUOUS,
            resolution_method=ResolutionMethod.UNRESOLVED,
            valid_from=date(2026, 8, 13),
            ingested_at=datetime(2026, 8, 14, tzinfo=UTC),
            quality_status=QualityStatus.REJECTED,
        )


def test_naive_datetime_rejected_and_extra_forbidden():
    with pytest.raises(ValidationError):
        ProviderInstrumentIdentityV1(
            provider="massive",
            as_of_date=date(2026, 8, 13),
            provider_ticker="TESTA",
            resolution_status=ResolutionStatus.UNRESOLVED,
            resolution_method=ResolutionMethod.UNRESOLVED,
            valid_from=date(2026, 8, 13),
            ingested_at=datetime(2026, 8, 14),
            quality_status=QualityStatus.WARNING,
            quality_flags=("no_stable_security_identifier",),
            unexpected="nope",
        )

