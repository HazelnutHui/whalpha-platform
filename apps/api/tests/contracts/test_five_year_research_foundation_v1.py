from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from tip_api.contracts.market_data.v1 import (
    FIVE_YEAR_FOUNDATION_FAMILY_ORDER,
    FIVE_YEAR_PRICE_STRATEGY_REQUIRED_FAMILIES,
    FIVE_YEAR_PROGRAM_REQUIRED_FAMILIES,
    FiveYearFoundationCensusStatus,
    FiveYearFoundationCoverageStatus,
    FiveYearFoundationEvidenceTier,
    FiveYearFoundationFamily,
    FiveYearFoundationFamilyCensusV1,
    FiveYearResearchFoundationCensusV1,
    build_five_year_research_foundation_census,
)


def _complete_family(
    family: FiveYearFoundationFamily,
) -> FiveYearFoundationFamilyCensusV1:
    return FiveYearFoundationFamilyCensusV1(
        family=family,
        program_required=family in FIVE_YEAR_PROGRAM_REQUIRED_FAMILIES,
        price_strategy_required=(
            family in FIVE_YEAR_PRICE_STRATEGY_REQUIRED_FAMILIES
        ),
        coverage_status=FiveYearFoundationCoverageStatus.COMPLETE,
        evidence_tier=FiveYearFoundationEvidenceTier.DERIVED_CANONICAL,
        custody_state="canonical_formally_validated",
        record_count=1,
        quarantined_record_count=0,
        source_ids=("whalpha",),
        reason_codes=("formal_coverage_complete",),
    )


def test_complete_census_has_fixed_family_policy_and_stable_fingerprint() -> None:
    census = build_five_year_research_foundation_census(
        calendar_version="test-calendar",
        target_anchor_date=date(2021, 9, 9),
        target_sessions=(date(2021, 9, 9), date(2026, 9, 9)),
        families=tuple(
            _complete_family(family)
            for family in FIVE_YEAR_FOUNDATION_FAMILY_ORDER
        ),
    )

    assert census.status is FiveYearFoundationCensusStatus.COMPLETE
    assert census.program_complete is True
    assert census.price_strategy_foundation_complete is True
    assert census.program_blocking_families == ()
    assert census.external_request_count == 0
    assert census.canonical_write_count == 0
    assert len(census.logical_fingerprint) == 64
    assert (
        FiveYearResearchFoundationCensusV1.model_validate(
            census.model_dump(mode="json")
        )
        == census
    )


def test_census_rejects_family_order_or_required_policy_tampering() -> None:
    families = tuple(
        _complete_family(family) for family in FIVE_YEAR_FOUNDATION_FAMILY_ORDER
    )
    with pytest.raises(ValidationError, match="incomplete or unordered"):
        build_five_year_research_foundation_census(
            calendar_version="test-calendar",
            target_anchor_date=date(2021, 9, 9),
            target_sessions=(date(2021, 9, 9),),
            families=tuple(reversed(families)),
        )

    invalid = families[0].model_copy(update={"program_required": False})
    with pytest.raises(ValidationError, match="program-required policy differs"):
        build_five_year_research_foundation_census(
            calendar_version="test-calendar",
            target_anchor_date=date(2021, 9, 9),
            target_sessions=(date(2021, 9, 9),),
            families=(invalid, *families[1:]),
        )


def test_census_rejects_fingerprint_tampering() -> None:
    census = build_five_year_research_foundation_census(
        calendar_version="test-calendar",
        target_anchor_date=date(2021, 9, 9),
        target_sessions=(date(2021, 9, 9),),
        families=tuple(
            _complete_family(family)
            for family in FIVE_YEAR_FOUNDATION_FAMILY_ORDER
        ),
    )
    payload = census.model_dump(mode="json")
    payload["logical_fingerprint"] = "0" * 64

    with pytest.raises(ValidationError, match="fingerprint differs"):
        FiveYearResearchFoundationCensusV1.model_validate(payload)


def test_nullable_unmeasured_record_count_is_distinct_from_zero() -> None:
    family = FiveYearFoundationFamilyCensusV1(
        family=FiveYearFoundationFamily.EOD_PRICE_BAR,
        program_required=True,
        price_strategy_required=True,
        coverage_status=FiveYearFoundationCoverageStatus.PARTIAL,
        evidence_tier=FiveYearFoundationEvidenceTier.MIXED,
        custody_state="canonical_acquired_coverage_unpublished",
        target_session_count=2,
        covered_session_count=1,
        missing_session_count=1,
        record_count=None,
        quarantined_record_count=None,
        source_ids=("massive",),
        reason_codes=("five_year_eod_sessions_missing",),
    )

    assert family.record_count is None
    assert family.quarantined_record_count is None
