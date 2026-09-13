from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from tip_api.services import five_year_research_foundation_census as module

from tip_api.contracts.market_data.v1 import (
    FiveYearFoundationCoverageStatus,
    FiveYearFoundationFamily,
)
from tip_api.services.five_year_research_foundation_census import (
    FiveYearResearchFoundationCensusError,
    _build_family_census,
    _combined_membership_inventory,
    _membership_publication_dates,
    _research_membership_inventory,
)
from tip_api.services.historical_universe_membership_shadow import (
    CANONICAL_SOURCE_HISTORICAL_METHODOLOGY_VERSION,
    CANONICAL_SOURCE_LOCALIZED_COLLISION_METHODOLOGY_VERSION,
)


def _inventory(
    family: FiveYearFoundationFamily,
    **changes: object,
) -> dict[str, object]:
    value: dict[str, object] = {
        "family": family.value,
        "custody_state": "observed_not_coverage_validated",
        "partition_count": 1,
        "record_count": 10,
        "quarantined_record_count": 0,
        "research_ready": False,
    }
    value.update(changes)
    return value


def test_family_census_uses_exact_non_contiguous_session_evidence() -> None:
    sessions = (
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
        date(2026, 1, 7),
    )
    inventories = {
        FiveYearFoundationFamily.EOD_PRICE_BAR.value: _inventory(
            FiveYearFoundationFamily.EOD_PRICE_BAR,
            covered_session_count=4,
            first_session="2026-01-02",
            last_session="2026-01-07",
        ),
        FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY.value: _inventory(
            FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY,
            covered_session_count=3,
            missing_eod_session_dates=("2026-01-05",),
            first_session="2026-01-02",
            last_session="2026-01-07",
        ),
        FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY_SOURCE.value: _inventory(
            FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY_SOURCE,
            covered_session_count=2,
            missing_eod_session_dates=("2026-01-02", "2026-01-06"),
            first_session="2026-01-05",
            last_session="2026-01-07",
        ),
        FiveYearFoundationFamily.UNIVERSE_MEMBERSHIP.value: _inventory(
            FiveYearFoundationFamily.UNIVERSE_MEMBERSHIP,
            covered_session_count=2,
            first_session="2026-01-02",
            last_session="2026-01-06",
        ),
        FiveYearFoundationFamily.CORPORATE_ACTION_SOURCE.value: _inventory(
            FiveYearFoundationFamily.CORPORATE_ACTION_SOURCE,
            quarantined_record_count=2,
        ),
        FiveYearFoundationFamily.CORPORATE_ACTION.value: _inventory(
            FiveYearFoundationFamily.CORPORATE_ACTION
        ),
        FiveYearFoundationFamily.INSTRUMENT_LIFECYCLE.value: _inventory(
            FiveYearFoundationFamily.INSTRUMENT_LIFECYCLE,
            partition_count=0,
            record_count=0,
        ),
        FiveYearFoundationFamily.ADJUSTMENT_LEDGER.value: _inventory(
            FiveYearFoundationFamily.ADJUSTMENT_LEDGER
        ),
        FiveYearFoundationFamily.HISTORICAL_COVERAGE_EVIDENCE.value: _inventory(
            FiveYearFoundationFamily.HISTORICAL_COVERAGE_EVIDENCE,
            partition_count=0,
            record_count=0,
        ),
        FiveYearFoundationFamily.HISTORICAL_COVERAGE.value: _inventory(
            FiveYearFoundationFamily.HISTORICAL_COVERAGE,
            partition_count=0,
            record_count=0,
        ),
    }

    census = _build_family_census(
        target_sessions=sessions,
        eod_sessions=sessions,
        membership_session_dates=(sessions[0], sessions[2]),
        inventories=inventories,
    )
    by_family = {item.family: item for item in census}

    assert by_family[
        FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY
    ].covered_session_count == 3
    assert by_family[
        FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY_SOURCE
    ].covered_session_count == 2
    membership = by_family[FiveYearFoundationFamily.UNIVERSE_MEMBERSHIP]
    assert membership.covered_session_count == 2
    assert membership.missing_session_count == 2
    assert by_family[FiveYearFoundationFamily.EOD_PRICE_BAR].record_count == 10
    assert (
        by_family[FiveYearFoundationFamily.INSTRUMENT_LIFECYCLE].coverage_status
        is FiveYearFoundationCoverageStatus.ABSENT
    )


def test_exact_missing_session_count_must_reconcile() -> None:
    inventories = {
        family.value: _inventory(family)
        for family in FiveYearFoundationFamily
        if family
        not in {
            FiveYearFoundationFamily.POINT_IN_TIME_CLASSIFICATION,
            FiveYearFoundationFamily.POINT_IN_TIME_FUNDAMENTALS,
        }
    }
    inventories[FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY.value].update(
        covered_session_count=1,
        missing_eod_session_dates=(),
    )
    inventories[
        FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY_SOURCE.value
    ].update(covered_session_count=1, missing_eod_session_dates=())

    with pytest.raises(FiveYearResearchFoundationCensusError, match="reconcile"):
        _build_family_census(
            target_sessions=(date(2026, 1, 2), date(2026, 1, 5)),
            eod_sessions=(date(2026, 1, 2), date(2026, 1, 5)),
            membership_session_dates=(),
            inventories=inventories,
        )


def test_membership_dates_are_deduplicated_across_methodologies(
    tmp_path,
) -> None:
    root = (
        tmp_path
        / "market-data/universe-membership-publications/schema_version=1"
        / "policy_id=next-open-v1"
    )
    for methodology in ("a", "b"):
        (root / f"methodology_version={methodology}" / "session_date=2026-01-02").mkdir(
            parents=True
        )

    assert _membership_publication_dates(tmp_path) == (date(2026, 1, 2),)


def test_membership_inventory_keeps_reconstructed_and_signal_tiers_separate() -> None:
    signal = _inventory(
        FiveYearFoundationFamily.UNIVERSE_MEMBERSHIP,
        partition_count=2,
        record_count=40,
        quarantined_record_count=1,
    )
    combined = _combined_membership_inventory(
        signal,
        signal_membership_dates=(date(2026, 1, 5), date(2026, 1, 6)),
        research_membership={
            "partition_count": 2,
            "record_count": 30,
            "quarantined_record_count": 3,
            "session_dates": (date(2026, 1, 2), date(2026, 1, 5)),
        },
    )

    assert combined["partition_count"] == 4
    assert combined["record_count"] == 70
    assert combined["quarantined_record_count"] == 4
    assert combined["covered_session_count"] == 3
    assert combined["five_year_evidence_tier"] == "mixed"
    assert combined["research_ready"] is False
    assert "reconstructed_membership_not_signal_eligible" in combined[
        "five_year_reason_codes"
    ]


def test_research_membership_inventory_reads_approved_methods_without_overlap(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = (
        tmp_path
        / "market-data/research-universe-membership/schema_version=1"
        / "evidence_tier=reconstructed-latest-vintage-v1"
    )
    sessions = {
        CANONICAL_SOURCE_HISTORICAL_METHODOLOGY_VERSION: date(2026, 1, 2),
        CANONICAL_SOURCE_LOCALIZED_COLLISION_METHODOLOGY_VERSION: date(2026, 1, 5),
    }
    for methodology, session in sessions.items():
        (
            base
            / f"methodology_version={methodology}"
            / f"session_date={session.isoformat()}"
        ).mkdir(parents=True)

    monkeypatch.setattr(
        module,
        "read_canonical_research_universe_membership",
        lambda **_: SimpleNamespace(
            membership_manifest=SimpleNamespace(
                record_count=10,
                disposition_summaries=(SimpleNamespace(quarantined_count=2),),
            )
        ),
    )

    result = _research_membership_inventory(tmp_path)

    assert result["partition_count"] == 2
    assert result["record_count"] == 20
    assert result["quarantined_record_count"] == 4
    assert result["session_dates"] == tuple(sorted(sessions.values()))
    assert result["methodology_partition_counts"] == (
        (CANONICAL_SOURCE_HISTORICAL_METHODOLOGY_VERSION, 1),
        (CANONICAL_SOURCE_LOCALIZED_COLLISION_METHODOLOGY_VERSION, 1),
    )
