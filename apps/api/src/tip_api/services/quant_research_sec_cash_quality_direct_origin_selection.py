"""Pure V2 direct-origin selection from the closed local target index."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Literal

import pyarrow as pa

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_direct_origin_selection import (
    SecCashQualityDirectOriginSelectionPlanV2,
    SecCashQualityDirectOriginSelectionResultV2,
    SecCashQualityDirectOriginSelectionVerificationV2,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import (
    census_fingerprint,
)
from tip_api.persistence.quant_research_sec_cash_quality_endpoint_selection import (
    SELECTED_ENDPOINT_SCHEMA,
    TARGET_INDEX_SCHEMA,
    _schema_fingerprint,
)


_ASSETS = "Assets"
_NI = "NetIncomeLoss"
_CFO = "NetCashProvidedByUsedInOperatingActivities"
_QUERY_BY_CONCEPT = {
    _ASSETS: "assets_fiscal_boundary_v1",
    _NI: "net_income_loss_fiscal_ytd_and_year_v1",
    _CFO: "operating_cash_flow_fiscal_ytd_and_year_v1",
}
_DURATION_CONCEPTS = (_NI, _CFO)
_PERIODS = frozenset(("FY", "Q1", "Q2", "Q3"))


class SecCashQualityDirectOriginSelectionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _Selected:
    row: dict
    source_occurrence_ids: tuple[str, ...]


def select_sec_cash_quality_direct_origin_endpoints_v2(
    *,
    target_index: pa.Table,
    plan: SecCashQualityDirectOriginSelectionPlanV2,
    traversal_order: Literal["forward", "reverse"] = "forward",
) -> tuple[pa.Table, SecCashQualityDirectOriginSelectionResultV2]:
    """Select and canonicalize endpoints without source or outcome access."""

    if (
        not target_index.schema.equals(TARGET_INDEX_SCHEMA, check_metadata=False)
        or _schema_fingerprint(target_index.schema)
        != plan.target_index_schema_fingerprint
        or target_index.num_rows != plan.target_index_row_count
    ):
        raise SecCashQualityDirectOriginSelectionError(
            "direct-origin target index binding differs"
        )
    candidates = [
        row
        for row in target_index.to_pylist()
        if row["occurrence_disposition"] == "query_candidate"
    ]
    by_coordinate: dict[tuple, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    issuer_ids: set[str] = set()
    for row in candidates:
        if (
            row["concept_name"] not in _QUERY_BY_CONCEPT
            or row["fiscal_year"] is None
            or row["fiscal_period"] not in _PERIODS
            or row["end_date"] is None
        ):
            raise SecCashQualityDirectOriginSelectionError(
                "query candidate coordinate is incomplete"
            )
        key = (
            row["companyfacts_cik"],
            row["fiscal_year"],
            row["fiscal_period"],
            row["end_date"],
        )
        by_coordinate[key][row["concept_name"]].append(row)
        issuer_ids.add(row["companyfacts_cik"])
    if len(by_coordinate) > plan.maximum_endpoint_coordinate_count:
        raise SecCashQualityDirectOriginSelectionError(
            "direct-origin endpoint budget exceeded"
        )

    selector_blockers: Counter[str] = Counter()
    selected_variants: list[dict] = []
    keys = sorted(by_coordinate, reverse=traversal_order == "reverse")
    for cik, fiscal_year, fiscal_period, period_end in keys:
        concept_rows = by_coordinate[(cik, fiscal_year, fiscal_period, period_end)]
        origins = {
            row["start_date"]
            for concept in _DURATION_CONCEPTS
            for row in concept_rows.get(concept, ())
            if row["start_date"] is not None
        }
        complete: list[tuple[object, dict[str, _Selected]]] = []
        failed_reasons: Counter[str] = Counter()
        for origin in sorted(origins):
            states: dict[str, _Selected] = {}
            for concept in (_ASSETS, _NI, _CFO):
                rows = concept_rows.get(concept, ())
                if concept != _ASSETS:
                    rows = tuple(row for row in rows if row["start_date"] == origin)
                selected, reason = _select_latest(rows)
                if selected is None:
                    failed_reasons[reason] += 1
                    break
                states[concept] = selected
            if len(states) != 3:
                continue
            if states[_NI].row["accession_number"] != states[_CFO].row["accession_number"]:
                failed_reasons["duration_pair_accession_incoherent"] += 1
                continue
            complete.append((origin, states))
        if len(complete) != 1:
            if len(complete) > 1:
                selector_blockers["multiple_complete_duration_origins"] += 1
            elif not origins:
                selector_blockers["duration_origin_missing"] += 1
            else:
                selector_blockers[_priority_reason(failed_reasons)] += 1
            continue
        origin, states = complete[0]
        for concept in (_ASSETS, _NI, _CFO):
            selected = states[concept]
            row = selected.row
            selected_variants.append(
                {
                    "companyfacts_cik": cik,
                    "fiscal_year": fiscal_year,
                    "fiscal_year_origin": origin,
                    "fiscal_period": fiscal_period,
                    "period_end": period_end,
                    "query_id": _QUERY_BY_CONCEPT[concept],
                    "concept_name": concept,
                    "value_kind": row["value_kind"],
                    "value_text": row["value_text"],
                    "accession_number": row["accession_number"],
                    "source_available_at_utc": row["source_available_at_utc"],
                    "signal_eligible_session": row["signal_eligible_session"],
                    "source_occurrence_ids": list(selected.source_occurrence_ids),
                }
            )
    variant_table = pa.Table.from_pylist(
        selected_variants, schema=SELECTED_ENDPOINT_SCHEMA
    )
    canonical, canonical_blockers, superseded = _canonicalize(variant_table)
    result = _result(
        plan=plan,
        query_candidate_occurrence_count=len(candidates),
        observed_issuer_count=len(issuer_ids),
        observed_endpoint_coordinate_count=len(by_coordinate),
        selected_endpoint_variant_count=variant_table.num_rows // 3,
        selector_blockers=selector_blockers,
        canonical=canonical,
        canonical_blockers=canonical_blockers,
        superseded=superseded,
    )
    return canonical, result


def independently_verify_sec_cash_quality_direct_origin_selection_v2(
    *, target_index: pa.Table, plan: SecCashQualityDirectOriginSelectionPlanV2
) -> tuple[
    pa.Table,
    SecCashQualityDirectOriginSelectionResultV2,
    SecCashQualityDirectOriginSelectionVerificationV2,
]:
    primary_rows, primary = select_sec_cash_quality_direct_origin_endpoints_v2(
        target_index=target_index, plan=plan
    )
    replay_rows, replay = select_sec_cash_quality_direct_origin_endpoints_v2(
        target_index=target_index, plan=plan, traversal_order="reverse"
    )
    primary_sha = hashlib.sha256(_table_bytes(primary_rows)).hexdigest()
    replay_sha = hashlib.sha256(_table_bytes(replay_rows)).hexdigest()
    values = {
        "plan_fingerprint": plan.logical_fingerprint,
        "primary_result_fingerprint": primary.logical_fingerprint,
        "replay_result_fingerprint": replay.logical_fingerprint,
        "primary_rows_sha256": primary_sha,
        "replay_rows_sha256": replay_sha,
    }
    provisional = SecCashQualityDirectOriginSelectionVerificationV2.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    verification = SecCashQualityDirectOriginSelectionVerificationV2.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )
    return primary_rows, primary, verification


def _select_latest(rows) -> tuple[_Selected | None, str]:
    if not rows:
        return None, "query_occurrence_missing"
    by_accession: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_accession[row["accession_number"]].append(row)
    clean: list[tuple[object, str, list[dict]]] = []
    for accession, accession_rows in by_accession.items():
        states = {
            (
                row["value_kind"], row["value_text"],
                row["source_available_at_utc"], row["signal_eligible_session"],
                row["form"], row["filed_date"], row["start_date"], row["end_date"],
            )
            for row in accession_rows
        }
        if len(states) != 1:
            return None, "within_accession_value_or_clock_conflict"
        clean.append((accession_rows[0]["source_available_at_utc"], accession, accession_rows))
    latest_time = max(item[0] for item in clean)
    latest = [item for item in clean if item[0] == latest_time]
    if len(latest) != 1:
        state_count = len(
            {
                (item[2][0]["value_kind"], item[2][0]["value_text"])
                for item in latest
            }
        )
        return (
            None,
            "latest_availability_value_conflict"
            if state_count > 1
            else "latest_availability_accession_tie",
        )
    _, _, selected_rows = latest[0]
    source_ids = tuple(sorted(row["source_occurrence_id"] for row in selected_rows))
    if len(source_ids) != len(set(source_ids)):
        raise SecCashQualityDirectOriginSelectionError(
            "source occurrence ID is duplicated"
        )
    return _Selected(selected_rows[0], source_ids), ""


def _priority_reason(reasons: Counter[str]) -> str:
    for reason in (
        "within_accession_value_or_clock_conflict",
        "latest_availability_value_conflict",
        "latest_availability_accession_tie",
        "duration_pair_accession_incoherent",
        "query_occurrence_missing",
    ):
        if reasons[reason]:
            return reason
    return "complete_origin_unprovable"


def _canonicalize(table: pa.Table) -> tuple[pa.Table, Counter[str], int]:
    variants: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for row in table.to_pylist():
        key = (
            row["companyfacts_cik"], row["fiscal_year_origin"],
            row["fiscal_period"], row["period_end"], row["fiscal_year"],
        )
        variants[key][row["query_id"]] = row
    economic: dict[tuple, list[dict[str, dict]]] = defaultdict(list)
    for key, rows in variants.items():
        if len(rows) != 3:
            raise SecCashQualityDirectOriginSelectionError(
                "selected endpoint query membership differs"
            )
        economic[key[:4]].append(rows)
    output: list[dict] = []
    blockers: Counter[str] = Counter()
    superseded = 0
    query_ids = tuple(sorted(_QUERY_BY_CONCEPT.values()))
    for key in sorted(economic):
        candidates = economic[key]
        dominators = [
            candidate
            for candidate in candidates
            if all(
                all(
                    candidate[query_id]["source_available_at_utc"]
                    >= other[query_id]["source_available_at_utc"]
                    for query_id in query_ids
                )
                for other in candidates
            )
        ]
        if len(dominators) == 1:
            output.extend(dominators[0].values())
            superseded += len(candidates) - 1
            continue
        if not dominators:
            blockers["comparative_component_clocks_crossed"] += len(candidates)
            continue
        states = {
            tuple(
                (
                    candidate[query_id]["value_kind"],
                    candidate[query_id]["value_text"],
                )
                for query_id in query_ids
            )
            for candidate in dominators
        }
        reason = (
            "comparative_latest_clock_value_conflict"
            if len(states) > 1
            else "comparative_latest_clock_tie"
        )
        blockers[reason] += len(candidates)
    output.sort(
        key=lambda row: (
            row["companyfacts_cik"], row["fiscal_year_origin"],
            row["fiscal_period"], row["period_end"], row["query_id"],
        )
    )
    return (
        pa.Table.from_pylist(output, schema=SELECTED_ENDPOINT_SCHEMA),
        blockers,
        superseded,
    )


def _result(
    *, plan, query_candidate_occurrence_count, observed_issuer_count,
    observed_endpoint_coordinate_count, selected_endpoint_variant_count,
    selector_blockers, canonical, canonical_blockers, superseded,
):
    rows = canonical.to_pylist()
    periods = Counter()
    for index in range(0, len(rows), 3):
        periods[rows[index]["fiscal_period"]] += 1
    times = [row["source_available_at_utc"] for row in rows]
    values = {
        "plan_fingerprint": plan.logical_fingerprint,
        "target_index_row_count": plan.target_index_row_count,
        "query_candidate_occurrence_count": query_candidate_occurrence_count,
        "observed_issuer_count": observed_issuer_count,
        "observed_endpoint_coordinate_count": observed_endpoint_coordinate_count,
        "selected_endpoint_variant_count": selected_endpoint_variant_count,
        "selector_blocked_endpoint_coordinate_count": sum(selector_blockers.values()),
        "selector_blocker_counts": tuple(sorted(selector_blockers.items())),
        "canonical_endpoint_count": canonical.num_rows // 3,
        "superseded_comparative_variant_count": superseded,
        "canonicalization_blocked_variant_count": sum(canonical_blockers.values()),
        "canonicalization_blocker_counts": tuple(sorted(canonical_blockers.items())),
        "fiscal_period_canonical_endpoint_counts": tuple(sorted(periods.items())),
        "earliest_source_available_at": min(times) if times else None,
        "latest_source_available_at": max(times) if times else None,
        "output_query_row_count": canonical.num_rows,
    }
    provisional = SecCashQualityDirectOriginSelectionResultV2.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualityDirectOriginSelectionResultV2.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )


def _table_bytes(table: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, SELECTED_ENDPOINT_SCHEMA) as writer:
        writer.write_table(table.combine_chunks())
    return sink.getvalue().to_pybytes()
