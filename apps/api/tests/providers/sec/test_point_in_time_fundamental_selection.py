from __future__ import annotations

from datetime import UTC, date, datetime

from tip_api.providers.sec.fundamental_query_readiness_census import _SelectedRow
from tip_api.providers.sec.fundamental_query_registry import (
    build_first_sec_fundamental_query_registry,
)
from tip_api.providers.sec.point_in_time_fundamental_selection import (
    select_sec_issuer_fundamental,
)


CIK = "0000000001"
SESSION = date(2025, 3, 3)
CUTOFF = datetime(2025, 3, 3, 14, 30, tzinfo=UTC)


def _row(
    ordinal: int,
    *,
    concept: str = "Assets",
    value: str = "100",
    accession: str = "0000000001-25-000001",
    available: datetime = datetime(2025, 3, 1, 12, tzinfo=UTC),
    eligible_session: date = SESSION,
    start: date | None = None,
    end: date = date(2024, 12, 31),
) -> _SelectedRow:
    return _SelectedRow(
        source_occurrence_id=f"{ordinal:064x}",
        source_member_name=f"CIK{CIK}.json",
        companyfacts_cik=CIK,
        namespace="us-gaap",
        concept_name=concept,
        unit="USD",
        ordinal=ordinal,
        start_date=start,
        end_date=end,
        value_kind="integer",
        value_text=value,
        accession_number=accession,
        fiscal_period="FY",
        form="10-K",
        filed_date=available.date(),
        clock_status="admitted",
        source_available_at=available,
        signal_eligible_session=eligible_session,
        normalization_status="admitted",
    )


def _query(query_id: str):
    registry = build_first_sec_fundamental_query_registry()
    return next(item for item in registry.queries if item.query_id == query_id)


def test_selection_collapses_duplicates_and_uses_latest_visible_revision() -> None:
    first = datetime(2025, 2, 20, 12, tzinfo=UTC)
    latest = datetime(2025, 3, 1, 12, tzinfo=UTC)
    rows = (
        _row(0, value="100", available=first),
        _row(1, value="100", available=first),
        _row(
            2,
            value="110",
            accession="0000000001-25-000002",
            available=latest,
        ),
    )

    selected = select_sec_issuer_fundamental(
        rows=rows,
        query=_query("assets_latest_reported_v1"),
        companyfacts_cik=CIK,
        evaluated_session=SESSION,
        cutoff_at=CUTOFF,
    )

    assert selected.selection_status == "selected"
    assert selected.value_text == "110"
    assert selected.accession_numbers == ("0000000001-25-000002",)
    assert selected.visible_revision_state_count == 2
    assert selected.selected_occurrence_count == 1


def test_selection_excludes_future_filing_clock_state() -> None:
    rows = (
        _row(0),
        _row(
            1,
            value="120",
            accession="0000000001-25-000002",
            available=datetime(2025, 3, 3, 14, 29, tzinfo=UTC),
            eligible_session=date(2025, 3, 4),
        ),
    )

    selected = select_sec_issuer_fundamental(
        rows=rows,
        query=_query("assets_latest_reported_v1"),
        companyfacts_cik=CIK,
        evaluated_session=SESSION,
        cutoff_at=CUTOFF,
    )

    assert selected.selection_status == "selected"
    assert selected.value_text == "100"


def test_selection_quarantines_visible_period_end_shape_ambiguity() -> None:
    rows = (
        _row(
            0,
            concept="NetIncomeLoss",
            value="10",
            start=date(2024, 1, 1),
        ),
        _row(
            1,
            concept="NetIncomeLoss",
            value="10",
            accession="0000000001-25-000002",
            start=date(2024, 1, 2),
        ),
    )

    selected = select_sec_issuer_fundamental(
        rows=rows,
        query=_query("net_income_loss_fiscal_year_v1"),
        companyfacts_cik=CIK,
        evaluated_session=SESSION,
        cutoff_at=CUTOFF,
    )

    assert selected.selection_status == "quarantined"
    assert selected.reason_codes == ("same_period_end_multiple_starts",)


def test_selection_quarantines_same_time_value_conflict() -> None:
    rows = (
        _row(0, value="100"),
        _row(
            1,
            value="101",
            accession="0000000001-25-000002",
        ),
    )

    selected = select_sec_issuer_fundamental(
        rows=rows,
        query=_query("assets_latest_reported_v1"),
        companyfacts_cik=CIK,
        evaluated_session=SESSION,
        cutoff_at=CUTOFF,
    )

    assert selected.selection_status == "quarantined"
    assert selected.reason_codes == ("same_availability_value_conflict",)


def test_selection_returns_explicit_not_available() -> None:
    selected = select_sec_issuer_fundamental(
        rows=(),
        query=_query("assets_latest_reported_v1"),
        companyfacts_cik=CIK,
        evaluated_session=SESSION,
        cutoff_at=CUTOFF,
    )

    assert selected.selection_status == "not_available"
    assert selected.reason_codes == ("no_query_eligible_occurrence_at_cutoff",)
