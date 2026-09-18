"""Pure issuer-level occurrence selection for registered SEC cash queries."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from tip_api.contracts.analytics.v1.quant_research_sec_cash_earnings_quality_query_registry import (
    SecCashQualitySourceQueryV1,
    quant_research_sec_cash_quality_query_registry_v1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_occurrence_selection import (
    SecCashQualityEndpointRequestV1,
    SecCashQualityLocalOccurrenceReadinessV1,
    SecCashQualityLocalOccurrenceV1,
    SecCashQualityLocalSourceBindingV1,
    SecCashQualityQueryOccurrenceSelectionV1,
    occurrence_readiness_fingerprint,
)


class SecCashQualityOccurrenceSelectionError(RuntimeError):
    """Raised when local occurrence selection scope cannot be proven."""


def assess_sec_cash_quality_local_occurrence_readiness(
    *,
    rows: tuple[SecCashQualityLocalOccurrenceV1, ...],
    source_binding: SecCashQualityLocalSourceBindingV1,
    request: SecCashQualityEndpointRequestV1,
) -> SecCashQualityLocalOccurrenceReadinessV1:
    """Assess three exact issuer queries at one endpoint without deriving TTM."""

    registry = quant_research_sec_cash_quality_query_registry_v1()
    concepts = {query.concept_name for query in registry.queries}
    if any(
        row.companyfacts_cik != request.companyfacts_cik
        or row.concept_name not in concepts
        for row in rows
    ):
        raise SecCashQualityOccurrenceSelectionError(
            "cash-quality local occurrence scope differs"
        )
    selections = tuple(
        _select_query(rows=rows, query=query, request=request)
        for query in registry.queries
    )
    by_id = {item.query_id: item for item in selections}
    cash_flow = by_id["operating_cash_flow_fiscal_ytd_and_year_v1"]
    net_income = by_id["net_income_loss_fiscal_ytd_and_year_v1"]
    coherent = (
        cash_flow.selection_status == "selected"
        and net_income.selection_status == "selected"
        and cash_flow.accession_number == net_income.accession_number
    )
    reasons = {
        f"{item.query_id}:{reason}"
        for item in selections
        for reason in item.reason_codes
    }
    if (
        cash_flow.selection_status == "selected"
        and net_income.selection_status == "selected"
        and not coherent
    ):
        reasons.add("duration_pair_accession_incoherent")
    readiness_status = (
        "ready_for_endpoint_occurrence_use_only"
        if all(item.selection_status == "selected" for item in selections)
        and coherent
        else "blocked"
    )
    values = {
        "source_binding": source_binding,
        "request": request,
        "selections": selections,
        "duration_pair_accession_coherent": coherent,
        "readiness_status": readiness_status,
        "reason_codes": tuple(sorted(reasons)),
    }
    provisional = SecCashQualityLocalOccurrenceReadinessV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualityLocalOccurrenceReadinessV1.model_validate(
        {
            **values,
            "logical_fingerprint": occurrence_readiness_fingerprint(provisional),
        }
    )


def _select_query(
    *,
    rows: tuple[SecCashQualityLocalOccurrenceV1, ...],
    query: SecCashQualitySourceQueryV1,
    request: SecCashQualityEndpointRequestV1,
) -> SecCashQualityQueryOccurrenceSelectionV1:
    concept_rows = tuple(row for row in rows if row.concept_name == query.concept_name)
    origin, origin_error = _duration_origin(
        rows=concept_rows,
        query=query,
        request=request,
    )
    if origin_error is not None:
        return _empty(query.query_id, "quarantined", (origin_error,))
    candidates = tuple(
        row
        for row in concept_rows
        if _base_eligible(row=row, query=query, request=request)
        and row.fiscal_year == request.fiscal_year
        and row.fiscal_period == request.fiscal_period
        and row.end_date == request.period_end
        and (query.period_shape == "instant" or row.start_date == origin)
    )
    if not candidates:
        reason = (
            "fiscal_year_origin_witness_missing"
            if query.period_shape == "duration"
            and request.fiscal_period in ("Q2", "Q3")
            and origin is None
            else "no_query_eligible_occurrence_at_endpoint"
        )
        return _empty(query.query_id, "not_available", (reason,))
    by_accession: dict[str, list[SecCashQualityLocalOccurrenceV1]] = defaultdict(list)
    for row in candidates:
        by_accession[row.accession_number].append(row)
    clean: list[tuple[datetime, str, tuple[SecCashQualityLocalOccurrenceV1, ...]]] = []
    for accession, accession_rows in by_accession.items():
        states = {
            (
                row.value_kind,
                row.value_text,
                row.source_available_at,
                row.signal_eligible_session,
                row.form,
                row.filed_date,
                row.start_date,
                row.end_date,
            )
            for row in accession_rows
        }
        if len(states) != 1:
            return _empty(query.query_id, "quarantined", ("within_accession_conflict",))
        available = accession_rows[0].source_available_at
        if available is None:
            raise SecCashQualityOccurrenceSelectionError(
                "eligible cash-quality occurrence lacks availability"
            )
        clean.append((available, accession, tuple(accession_rows)))
    latest_time = max(item[0] for item in clean)
    latest = tuple(item for item in clean if item[0] == latest_time)
    if len(latest) != 1:
        return _empty(
            query.query_id,
            "quarantined",
            ("latest_availability_multiple_accessions",),
        )
    _, accession, selected_rows = latest[0]
    selected = selected_rows[0]
    source_ids = tuple(sorted(row.source_occurrence_id for row in selected_rows))
    if len(source_ids) != len(set(source_ids)):
        raise SecCashQualityOccurrenceSelectionError(
            "cash-quality source occurrence ID is duplicated"
        )
    return SecCashQualityQueryOccurrenceSelectionV1(
        query_id=query.query_id,
        selection_status="selected",
        reason_codes=(),
        value_kind=selected.value_kind,
        value_text=selected.value_text,
        start_date=selected.start_date,
        end_date=selected.end_date,
        source_available_at=selected.source_available_at,
        signal_eligible_session=selected.signal_eligible_session,
        accession_number=accession,
        form=selected.form,
        filed_date=selected.filed_date,
        source_occurrence_ids=source_ids,
        exact_duplicate_redundant_occurrence_count=len(source_ids) - 1,
    )


def _duration_origin(
    *,
    rows: tuple[SecCashQualityLocalOccurrenceV1, ...],
    query: SecCashQualitySourceQueryV1,
    request: SecCashQualityEndpointRequestV1,
) -> tuple[date | None, str | None]:
    if query.period_shape == "instant":
        return None, None
    if request.fiscal_period not in ("Q2", "Q3"):
        return request.fiscal_year_origin, None
    starts = {
        row.start_date
        for row in rows
        if _base_eligible(row=row, query=query, request=request)
        and row.fiscal_year == request.fiscal_year
        and row.fiscal_period == "Q1"
    }
    starts.discard(None)
    if len(starts) > 1:
        return None, "fiscal_year_origin_ambiguous"
    if starts and starts != {request.fiscal_year_origin}:
        return None, "fiscal_year_origin_witness_mismatch"
    return (request.fiscal_year_origin if starts else None), None


def _base_eligible(
    *,
    row: SecCashQualityLocalOccurrenceV1,
    query: SecCashQualitySourceQueryV1,
    request: SecCashQualityEndpointRequestV1,
) -> bool:
    periods_by_form = {
        form: rule.fiscal_periods
        for rule in query.form_period_rules
        for form in rule.forms
    }
    return (
        row.namespace == query.namespace
        and row.unit == query.unit
        and row.form in periods_by_form
        and row.fiscal_period in periods_by_form[row.form]
        and row.end_date is not None
        and (
            (query.period_shape == "instant" and row.start_date is None)
            or (query.period_shape == "duration" and row.start_date is not None)
        )
        and row.normalization_status == "admitted"
        and row.filing_clock_admission_status == "admitted"
        and row.source_available_at is not None
        and row.source_available_at <= request.cutoff_at
        and row.signal_eligible_session is not None
        and row.signal_eligible_session <= request.evaluated_session
        and row.end_date <= request.cutoff_at.date()
        and row.value_kind in query.accepted_value_kinds
        and row.value_text is not None
    )


def _empty(
    query_id: str,
    status: str,
    reasons: tuple[str, ...],
) -> SecCashQualityQueryOccurrenceSelectionV1:
    return SecCashQualityQueryOccurrenceSelectionV1.model_validate(
        {
            "query_id": query_id,
            "selection_status": status,
            "reason_codes": tuple(sorted(set(reasons))),
            "exact_duplicate_redundant_occurrence_count": 0,
        }
    )
