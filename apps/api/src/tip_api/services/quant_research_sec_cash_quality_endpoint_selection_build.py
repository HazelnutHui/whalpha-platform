"""One-scan builder for reusable SEC cash-quality endpoint evidence."""

from __future__ import annotations

from collections import defaultdict
import pyarrow as pa

from tip_api.contracts.analytics.v1.quant_research_sec_cash_earnings_quality_query_registry import (
    quant_research_sec_cash_quality_query_registry_v1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_endpoint_selection_package import (
    SecCashQualityEndpointSelectionPlanV1,
)
from tip_api.persistence.quant_research_sec_cash_quality_endpoint_selection import (
    SELECTED_ENDPOINT_SCHEMA,
    TARGET_INDEX_SCHEMA,
)
from tip_api.services.quant_research_sec_cash_quality_source_readiness_census import (
    _OccurrenceRow,
    _origin_candidates,
    _select_indexed_query,
    SecCashQualityPreparedTargetEvidence,
)


class SecCashQualityEndpointSelectionBuildError(RuntimeError):
    pass


def build_sec_cash_quality_endpoint_selection_tables(
    *,
    plan: SecCashQualityEndpointSelectionPlanV1,
    prepared: SecCashQualityPreparedTargetEvidence,
) -> tuple[pa.Table, pa.Table]:
    """Build reusable tables from the already formally verified target evidence."""

    manifest = prepared.source.manifest
    if (
        manifest.logical_fingerprint != plan.normalized_manifest_fingerprint
        or manifest.content_fingerprint != plan.normalized_content_fingerprint
        or manifest.filing_clock_manifest_fingerprint
        != plan.filing_clock_manifest_fingerprint
        or manifest.occurrence_schema_fingerprint
        != plan.occurrence_schema_fingerprint
        or manifest.occurrence_count != plan.source_occurrence_count
    ):
        raise SecCashQualityEndpointSelectionBuildError(
            "cash-quality selection source binding differs"
        )
    target_rows = [
        _target_row(raw, disposition)
        for raw, disposition in prepared.target_records
    ]
    internal_rows = [
        row for rows in prepared.by_worker.values() for row in rows
    ]
    if len(target_rows) != plan.target_occurrence_count:
        raise SecCashQualityEndpointSelectionBuildError(
            "cash-quality selection denominator differs"
        )
    selected_rows = _select_ready_endpoints(internal_rows)
    if len(selected_rows) != plan.admitted_ready_endpoint_count * 3:
        raise SecCashQualityEndpointSelectionBuildError(
            "cash-quality ready endpoint count differs from verified census"
        )
    return (
        pa.Table.from_pylist(target_rows, schema=TARGET_INDEX_SCHEMA),
        pa.Table.from_pylist(selected_rows, schema=SELECTED_ENDPOINT_SCHEMA),
    )


def _select_ready_endpoints(rows: list[_OccurrenceRow]) -> list[dict[str, object]]:
    registry = quant_research_sec_cash_quality_query_registry_v1()
    by_cik: dict[str, list[_OccurrenceRow]] = defaultdict(list)
    for row in rows:
        by_cik[row.companyfacts_cik].append(row)
    output: list[dict[str, object]] = []
    for cik in sorted(by_cik):
        endpoint_rows: dict[tuple[int, str, object], dict[str, list[_OccurrenceRow]]] = (
            defaultdict(lambda: defaultdict(list))
        )
        q1_rows: dict[tuple[int, str], list[_OccurrenceRow]] = defaultdict(list)
        for row in by_cik[cik]:
            if row.fiscal_year is None:
                continue
            if row.fiscal_period == "Q1":
                q1_rows[(row.fiscal_year, row.concept_name)].append(row)
            if row.fiscal_period in {"FY", "Q1", "Q2", "Q3"} and row.end_date:
                endpoint_rows[
                    (row.fiscal_year, row.fiscal_period, row.end_date)
                ][row.concept_name].append(row)
        for fiscal_year, fiscal_period, period_end in sorted(endpoint_rows):
            indexed = endpoint_rows[(fiscal_year, fiscal_period, period_end)]
            origins = _origin_candidates(
                endpoint_rows=indexed,
                q1_rows=q1_rows,
                fiscal_year=fiscal_year,
                fiscal_period=fiscal_period,
                registry_queries=registry.queries,
            )
            if len(origins) != 1:
                continue
            origin = next(iter(origins))
            if period_end < origin:
                continue
            states = {
                query.query_id: _select_indexed_query(
                    query=query,
                    endpoint_rows=indexed.get(query.concept_name, ()),
                    q1_rows=q1_rows.get((fiscal_year, query.concept_name), ()),
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                    period_end=period_end,
                    fiscal_year_origin=origin,
                )
                for query in registry.queries
            }
            if any(state.status != "selected" for state in states.values()):
                continue
            cfo = states["operating_cash_flow_fiscal_ytd_and_year_v1"]
            net_income = states["net_income_loss_fiscal_ytd_and_year_v1"]
            if cfo.accession_number != net_income.accession_number:
                continue
            for query in registry.queries:
                state = states[query.query_id]
                candidates = [
                    row
                    for row in indexed[query.concept_name]
                    if row.query_candidate
                    and row.accession_number == state.accession_number
                    and (
                        query.period_shape == "instant"
                        or row.start_date == origin
                    )
                ]
                witness = candidates[0]
                output.append(
                    {
                        "companyfacts_cik": cik,
                        "fiscal_year": fiscal_year,
                        "fiscal_year_origin": origin,
                        "fiscal_period": fiscal_period,
                        "period_end": period_end,
                        "query_id": query.query_id,
                        "concept_name": query.concept_name,
                        "value_kind": witness.value_kind,
                        "value_text": witness.value_text,
                        "accession_number": witness.accession_number,
                        "source_available_at_utc": witness.source_available_at,
                        "signal_eligible_session": witness.signal_eligible_session,
                        "source_occurrence_ids": sorted(
                            row.source_occurrence_id for row in candidates
                        ),
                    }
                )
    return output


def _target_row(raw: dict[str, object], disposition: str) -> dict[str, object]:
    return {
        key: raw[key]
        for key in (
            "source_occurrence_id",
            "companyfacts_cik",
            "namespace",
            "concept_name",
            "unit",
            "start_date",
            "end_date",
            "value_kind",
            "value_text",
            "accession_number",
            "fiscal_year",
            "fiscal_period",
            "form",
            "filed_date",
            "source_available_at_utc",
            "signal_eligible_session",
            "filing_clock_admission_status",
            "normalization_status",
        )
    } | {"occurrence_disposition": disposition}
