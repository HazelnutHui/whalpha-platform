from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    InstrumentMasterV1,
    InstrumentStatus,
    InstrumentType,
    ProviderInstrumentIdentityV1,
    ResolutionMethod,
    ResolutionStatus,
)
from tip_api.services.sec_filer_security_link_decision import (
    derive_sec_filer_security_link_decisions,
)


SESSION = date(2025, 8, 1)
OBSERVED = datetime(2026, 9, 10, 16, tzinfo=UTC)


def _instrument(number: int, ticker: str, cik: str | None) -> InstrumentMasterV1:
    return InstrumentMasterV1(
        instrument_id=UUID(int=number),
        instrument_type=InstrumentType.COMMON_STOCK,
        status=InstrumentStatus.ACTIVE,
        ticker=ticker,
        name=f"Issuer {number}",
        primary_exchange="XNYS",
        listing_country="US",
        currency="USD",
        cik=cik,
        valid_from=SESSION,
        as_of_date=SESSION,
        source="massive_stocks_basic",
        source_instrument_id=f"share_class_figi:BBG{number:09d}",
        ingested_at=OBSERVED,
        quality_status=QualityStatus.VALID,
    )


def _identity(
    number: int,
    ticker: str,
    cik: str | None,
    *,
    suffix: int = 0,
) -> ProviderInstrumentIdentityV1:
    return ProviderInstrumentIdentityV1(
        provider="massive_stocks_basic",
        as_of_date=SESSION,
        provider_ticker=ticker,
        share_class_figi=f"BBG{number:08d}{suffix}",
        cik=cik,
        canonical_instrument_id=UUID(int=number),
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_method=ResolutionMethod.SHARE_CLASS_FIGI,
        valid_from=SESSION,
        ingested_at=OBSERVED,
        quality_status=QualityStatus.VALID,
    )


def test_link_decisions_preserve_multi_security_filer_and_missing_cik() -> None:
    instruments = (
        _instrument(1, "AAA", "0000000042"),
        _instrument(2, "AAB", "0000000042"),
        _instrument(3, "BBB", None),
    )
    identities = (
        _identity(1, "AAA", "0000000042"),
        _identity(2, "AAB", "0000000042"),
        _identity(3, "BBB", None),
    )

    rows = derive_sec_filer_security_link_decisions(
        as_of_date=SESSION,
        instruments=instruments,
        identities=identities,
        point_in_time_eligibility="outcome_reconciliation_only",
        source_observed_at=OBSERVED,
    )

    assert tuple(item.instrument_id for item in rows) == tuple(
        sorted(item.instrument_id for item in rows)
    )
    assert rows[0].decision_status == "admitted_unique_cik"
    assert rows[0].cik_instrument_count == 2
    assert rows[1].decision_status == "admitted_unique_cik"
    assert rows[1].cik_instrument_count == 2
    assert rows[2].decision_status == "quarantined_missing_cik"
    assert rows[2].reason_codes == ("cik_missing",)
    assert all(item.issuer_projection_authorized is False for item in rows)


def test_link_decision_quarantines_same_instrument_cik_conflict() -> None:
    rows = derive_sec_filer_security_link_decisions(
        as_of_date=SESSION,
        instruments=(_instrument(1, "AAA", None),),
        identities=(
            _identity(1, "AAA", "0000000042"),
            _identity(1, "AAA", "0000000043", suffix=1),
        ),
        point_in_time_eligibility="eligible_at_source_observed_at",
        source_observed_at=OBSERVED,
    )

    assert rows[0].decision_status == "quarantined_conflicting_cik"
    assert rows[0].reason_codes == ("cik_conflict",)
    assert rows[0].sec_cik is None
    assert rows[0].source_identity_occurrence_count == 2


def test_missing_source_custody_never_admits_otherwise_valid_link() -> None:
    rows = derive_sec_filer_security_link_decisions(
        as_of_date=SESSION,
        instruments=(_instrument(1, "AAA", "0000000042"),),
        identities=(_identity(1, "AAA", "0000000042"),),
        point_in_time_eligibility="source_custody_missing",
        source_observed_at=None,
    )

    assert rows[0].decision_status == "quarantined_source_custody_missing"
    assert rows[0].reason_codes == ("source_custody_missing",)
    assert rows[0].sec_cik is None
