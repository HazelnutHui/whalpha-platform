from __future__ import annotations

from datetime import UTC, date, datetime

from tip_api.contracts.analytics.v1.quant_research_sec_cash_earnings_quality_query_registry import (
    quant_research_sec_cash_quality_query_registry_v1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_occurrence_selection import (
    SecCashQualityEndpointRequestV1,
    SecCashQualityLocalOccurrenceV1,
    SecCashQualityLocalSourceBindingV1,
    occurrence_readiness_fingerprint,
)
from tip_api.services.quant_research_sec_cash_quality_occurrence_selection import (
    assess_sec_cash_quality_local_occurrence_readiness,
)


CIK = "0000000001"
SESSION = date(2025, 8, 4)
CUTOFF = datetime(2025, 8, 4, 20, tzinfo=UTC)
Q1_END = date(2025, 3, 31)
Q2_END = date(2025, 6, 30)
ORIGIN = date(2025, 1, 1)
ACCESSION = "0000000001-25-000002"


def _binding() -> SecCashQualityLocalSourceBindingV1:
    return SecCashQualityLocalSourceBindingV1(
        query_registry_fingerprint=(
            quant_research_sec_cash_quality_query_registry_v1().logical_fingerprint
        ),
        normalized_source_manifest_fingerprint="1" * 64,
        normalized_source_content_fingerprint="2" * 64,
        filing_clock_manifest_fingerprint="3" * 64,
    )


def _request() -> SecCashQualityEndpointRequestV1:
    return SecCashQualityEndpointRequestV1(
        companyfacts_cik=CIK,
        fiscal_year=2025,
        fiscal_year_origin=ORIGIN,
        fiscal_period="Q2",
        period_end=Q2_END,
        evaluated_session=SESSION,
        cutoff_at=CUTOFF,
    )


def _row(
    ordinal: int,
    *,
    concept: str,
    value: str,
    fiscal_period: str = "Q2",
    end: date = Q2_END,
    start: date | None = ORIGIN,
    accession: str = ACCESSION,
    available: datetime = datetime(2025, 8, 1, 12, tzinfo=UTC),
) -> SecCashQualityLocalOccurrenceV1:
    return SecCashQualityLocalOccurrenceV1(
        source_occurrence_id=f"{ordinal:064x}",
        companyfacts_cik=CIK,
        namespace="us-gaap",
        concept_name=concept,
        unit="USD",
        start_date=start,
        end_date=end,
        value_kind="integer",
        value_text=value,
        accession_number=accession,
        fiscal_year=2025,
        fiscal_period=fiscal_period,
        form="10-Q",
        filed_date=available.date(),
        filing_clock_admission_status="admitted",
        source_available_at=available,
        signal_eligible_session=SESSION,
        normalization_status="admitted",
    )


def _ready_rows() -> tuple[SecCashQualityLocalOccurrenceV1, ...]:
    return (
        _row(
            1,
            concept="NetIncomeLoss",
            value="10",
            fiscal_period="Q1",
            end=Q1_END,
            accession="0000000001-25-000001",
        ),
        _row(
            2,
            concept="NetCashProvidedByUsedInOperatingActivities",
            value="15",
            fiscal_period="Q1",
            end=Q1_END,
            accession="0000000001-25-000001",
        ),
        _row(3, concept="NetIncomeLoss", value="25"),
        _row(
            4,
            concept="NetCashProvidedByUsedInOperatingActivities",
            value="40",
        ),
        _row(5, concept="Assets", value="500", start=None),
    )


def test_local_occurrence_readiness_selects_exact_endpoint_without_ttm() -> None:
    result = assess_sec_cash_quality_local_occurrence_readiness(
        rows=_ready_rows(),
        source_binding=_binding(),
        request=_request(),
    )

    assert result.readiness_status == "ready_for_endpoint_occurrence_use_only"
    assert result.duration_pair_accession_coherent is True
    assert result.reason_codes == ()
    assert all(item.selection_status == "selected" for item in result.selections)
    assert result.ttm_derivation_authorized is False
    assert result.factor_materialization_authorized is False
    assert result.outcome_access_authorized is False
    assert result.logical_fingerprint == occurrence_readiness_fingerprint(result)


def test_local_occurrence_readiness_requires_q1_origin_witness() -> None:
    rows = tuple(
        row for row in _ready_rows() if row.fiscal_period != "Q1"
    )

    result = assess_sec_cash_quality_local_occurrence_readiness(
        rows=rows,
        source_binding=_binding(),
        request=_request(),
    )

    assert result.readiness_status == "blocked"
    assert result.duration_pair_accession_coherent is False
    assert (
        "net_income_loss_fiscal_ytd_and_year_v1:"
        "fiscal_year_origin_witness_missing"
    ) in result.reason_codes
    assert (
        "operating_cash_flow_fiscal_ytd_and_year_v1:"
        "fiscal_year_origin_witness_missing"
    ) in result.reason_codes


def test_local_occurrence_readiness_blocks_cross_query_accession_mismatch() -> None:
    rows = tuple(
        row.model_copy(
            update={"accession_number": "0000000001-25-000003"}
        )
        if row.concept_name == "NetIncomeLoss" and row.fiscal_period == "Q2"
        else row
        for row in _ready_rows()
    )

    result = assess_sec_cash_quality_local_occurrence_readiness(
        rows=rows,
        source_binding=_binding(),
        request=_request(),
    )

    assert result.readiness_status == "blocked"
    assert result.duration_pair_accession_coherent is False
    assert result.reason_codes == ("duration_pair_accession_incoherent",)


def test_local_occurrence_readiness_ignores_future_amendment_and_collapses_duplicates() -> None:
    rows = _ready_rows() + (
        _row(6, concept="Assets", value="500", start=None),
        _row(
            7,
            concept="Assets",
            value="550",
            start=None,
            accession="0000000001-25-000004",
            available=datetime(2025, 8, 5, 12, tzinfo=UTC),
        ),
    )

    result = assess_sec_cash_quality_local_occurrence_readiness(
        rows=rows,
        source_binding=_binding(),
        request=_request(),
    )

    assets = result.selections[0]
    assert result.readiness_status == "ready_for_endpoint_occurrence_use_only"
    assert assets.value_text == "500"
    assert assets.exact_duplicate_redundant_occurrence_count == 1


def test_local_occurrence_readiness_quarantines_ambiguous_origin() -> None:
    rows = _ready_rows() + (
        _row(
            8,
            concept="NetIncomeLoss",
            value="10",
            fiscal_period="Q1",
            end=Q1_END,
            start=date(2025, 1, 2),
            accession="0000000001-25-000005",
        ),
    )

    result = assess_sec_cash_quality_local_occurrence_readiness(
        rows=rows,
        source_binding=_binding(),
        request=_request(),
    )

    net_income = result.selections[1]
    assert result.readiness_status == "blocked"
    assert net_income.selection_status == "quarantined"
    assert net_income.reason_codes == ("fiscal_year_origin_ambiguous",)


def test_local_occurrence_readiness_distinguishes_single_origin_mismatch() -> None:
    rows = tuple(
        row.model_copy(update={"start_date": date(2025, 1, 2)})
        if row.concept_name == "NetIncomeLoss" and row.fiscal_period == "Q1"
        else row
        for row in _ready_rows()
    )

    result = assess_sec_cash_quality_local_occurrence_readiness(
        rows=rows,
        source_binding=_binding(),
        request=_request(),
    )

    net_income = result.selections[1]
    assert net_income.selection_status == "quarantined"
    assert net_income.reason_codes == ("fiscal_year_origin_witness_mismatch",)
