"""Pure TTM V2 derivation from canonical economic SEC endpoints."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal

import pyarrow as pa

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import (
    census_fingerprint,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_ttm_coverage_v2 import (
    SecCashQualityTtmCoveragePlanV2,
    SecCashQualityTtmCoverageResultV2,
    SecCashQualityTtmCoverageVerificationV2,
)
from tip_api.persistence.quant_research_sec_cash_quality_endpoint_selection import (
    SELECTED_ENDPOINT_SCHEMA,
)


TTM_V2_ARROW_SCHEMA = pa.schema(
    [
        pa.field("companyfacts_cik", pa.string(), nullable=False),
        pa.field("fiscal_year", pa.int32(), nullable=False),
        pa.field("fiscal_year_origin", pa.date32(), nullable=False),
        pa.field("fiscal_period", pa.string(), nullable=False),
        pa.field("period_end", pa.date32(), nullable=False),
        pa.field("ttm_cfo_text", pa.string(), nullable=False),
        pa.field("ttm_net_income_text", pa.string(), nullable=False),
        pa.field("opening_assets_text", pa.string(), nullable=False),
        pa.field("closing_assets_text", pa.string(), nullable=False),
        pa.field("average_assets_text", pa.string(), nullable=False),
        pa.field("knowledge_at_utc", pa.timestamp("ms", tz="UTC"), nullable=False),
        pa.field("component_accessions", pa.list_(pa.string()), nullable=False),
        pa.field("source_occurrence_ids", pa.list_(pa.string()), nullable=False),
    ]
)


_ASSETS = "assets_fiscal_boundary_v1"
_NI = "net_income_loss_fiscal_ytd_and_year_v1"
_CFO = "operating_cash_flow_fiscal_ytd_and_year_v1"
_NEXT = {"Q1": "Q2", "Q2": "Q3", "Q3": "FY"}


class SecCashQualityTtmCoverageV2Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _Endpoint:
    key: tuple
    fiscal_year: int
    rows: dict[str, dict]


def derive_sec_cash_quality_ttm_coverage_v2(
    *, selected_endpoints: pa.Table, plan: SecCashQualityTtmCoveragePlanV2,
    traversal_order: Literal["forward", "reverse"] = "forward",
) -> tuple[pa.Table, SecCashQualityTtmCoverageResultV2]:
    if (
        not selected_endpoints.schema.equals(
            SELECTED_ENDPOINT_SCHEMA, check_metadata=False
        )
        or selected_endpoints.num_rows != plan.input_query_row_count
    ):
        raise SecCashQualityTtmCoverageV2Error("TTM V2 input binding differs")
    grouped: dict[tuple, dict[str, dict]] = defaultdict(dict)
    fiscal_years: dict[tuple, set[int]] = defaultdict(set)
    for row in selected_endpoints.to_pylist():
        key = (
            row["companyfacts_cik"], row["fiscal_year_origin"],
            row["fiscal_period"], row["period_end"],
        )
        if row["query_id"] in grouped[key]:
            raise SecCashQualityTtmCoverageV2Error("duplicate TTM V2 query row")
        grouped[key][row["query_id"]] = row
        fiscal_years[key].add(row["fiscal_year"])
    if len(grouped) != plan.input_endpoint_count:
        raise SecCashQualityTtmCoverageV2Error("TTM V2 endpoint count differs")
    by_cik: dict[str, list[_Endpoint]] = defaultdict(list)
    for key, rows in grouped.items():
        if (
            set(rows) != {_ASSETS, _NI, _CFO}
            or len(fiscal_years[key]) != 1
            or rows[_NI]["accession_number"] != rows[_CFO]["accession_number"]
        ):
            raise SecCashQualityTtmCoverageV2Error(
                "TTM V2 endpoint membership or coherence differs"
            )
        by_cik[key[0]].append(
            _Endpoint(key, next(iter(fiscal_years[key])), rows)
        )
    blockers: Counter[str] = Counter()
    output: list[dict] = []
    ready_issuers: set[str] = set()
    cik_order = sorted(by_cik, reverse=traversal_order == "reverse")
    for cik in cik_order:
        endpoints = sorted(by_cik[cik], key=lambda item: item.key[3])
        period_counts = Counter((item.key[1], item.key[2]) for item in endpoints)
        ambiguous = {
            item.key for item in endpoints
            if period_counts[(item.key[1], item.key[2])] != 1
        }
        clean = [item for item in endpoints if item.key not in ambiguous]
        positions = {item.key: index for index, item in enumerate(clean)}
        iterable = endpoints if traversal_order == "forward" else reversed(endpoints)
        for endpoint in iterable:
            if endpoint.key in ambiguous:
                blockers["fiscal_period_endpoint_ambiguous"] += 1
                continue
            index = positions[endpoint.key]
            if index < 4:
                blockers["insufficient_prior_endpoints"] += 1
                continue
            window = clean[index - 4 : index + 1]
            if not all(
                _consecutive(window[pos], window[pos + 1]) for pos in range(4)
            ):
                blockers["quarter_sequence_not_consecutive"] += 1
                continue
            if not _annual_shapes_valid(window, plan):
                blockers["fiscal_year_duration_out_of_bounds"] += 1
                continue
            try:
                discrete = [
                    _discrete(clean, position)
                    for position in range(index - 3, index + 1)
                ]
                ttm_cfo = sum((item[0] for item in discrete), Decimal(0))
                ttm_ni = sum((item[1] for item in discrete), Decimal(0))
                opening_assets = Decimal(window[0].rows[_ASSETS]["value_text"])
                closing_assets = Decimal(window[-1].rows[_ASSETS]["value_text"])
            except (InvalidOperation, TypeError, SecCashQualityTtmCoverageV2Error):
                blockers["numeric_or_increment_unprovable"] += 1
                continue
            average_assets = (opening_assets + closing_assets) / Decimal(2)
            if average_assets == 0:
                blockers["zero_average_assets"] += 1
                continue
            component_rows = [
                row for item in window for row in item.rows.values()
            ]
            output.append(
                {
                    "companyfacts_cik": cik,
                    "fiscal_year": endpoint.fiscal_year,
                    "fiscal_year_origin": endpoint.key[1],
                    "fiscal_period": endpoint.key[2],
                    "period_end": endpoint.key[3],
                    "ttm_cfo_text": _decimal_text(ttm_cfo),
                    "ttm_net_income_text": _decimal_text(ttm_ni),
                    "opening_assets_text": _decimal_text(opening_assets),
                    "closing_assets_text": _decimal_text(closing_assets),
                    "average_assets_text": _decimal_text(average_assets),
                    "knowledge_at_utc": max(
                        row["source_available_at_utc"] for row in component_rows
                    ),
                    "component_accessions": sorted(
                        {row["accession_number"] for row in component_rows}
                    ),
                    "source_occurrence_ids": sorted(
                        {
                            source_id
                            for row in component_rows
                            for source_id in row["source_occurrence_ids"]
                        }
                    ),
                }
            )
            ready_issuers.add(cik)
    output.sort(
        key=lambda row: (
            row["companyfacts_cik"], row["fiscal_year_origin"],
            row["period_end"], row["fiscal_period"],
        )
    )
    rows = pa.Table.from_pylist(output, schema=TTM_V2_ARROW_SCHEMA)
    return rows, _result(plan, len(by_cik), ready_issuers, blockers, output)


def independently_verify_sec_cash_quality_ttm_coverage_v2(
    *, selected_endpoints: pa.Table, plan: SecCashQualityTtmCoveragePlanV2,
) -> tuple[
    pa.Table, SecCashQualityTtmCoverageResultV2,
    SecCashQualityTtmCoverageVerificationV2,
]:
    rows, result = derive_sec_cash_quality_ttm_coverage_v2(
        selected_endpoints=selected_endpoints, plan=plan
    )
    replay_rows, replay_result = derive_sec_cash_quality_ttm_coverage_v2(
        selected_endpoints=selected_endpoints, plan=plan, traversal_order="reverse"
    )
    row_sha = hashlib.sha256(_table_bytes(rows)).hexdigest()
    replay_sha = hashlib.sha256(_table_bytes(replay_rows)).hexdigest()
    values = {
        "plan_fingerprint": plan.logical_fingerprint,
        "primary_result_fingerprint": result.logical_fingerprint,
        "replay_result_fingerprint": replay_result.logical_fingerprint,
        "primary_rows_sha256": row_sha,
        "replay_rows_sha256": replay_sha,
    }
    provisional = SecCashQualityTtmCoverageVerificationV2.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    verification = SecCashQualityTtmCoverageVerificationV2.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )
    return rows, result, verification


def _consecutive(left: _Endpoint, right: _Endpoint) -> bool:
    if left.key[2] in _NEXT:
        return right.key[2] == _NEXT[left.key[2]] and right.key[1] == left.key[1]
    return (
        left.key[2] == "FY" and right.key[2] == "Q1"
        and right.key[1] == left.key[3] + timedelta(days=1)
    )


def _annual_shapes_valid(window, plan) -> bool:
    return all(
        plan.annual_duration_days_minimum
        <= (item.key[3] - item.key[1]).days + 1
        <= plan.annual_duration_days_maximum
        for item in window if item.key[2] == "FY"
    )


def _discrete(endpoints: list[_Endpoint], index: int) -> tuple[Decimal, Decimal]:
    endpoint = endpoints[index]
    current = (
        Decimal(endpoint.rows[_CFO]["value_text"]),
        Decimal(endpoint.rows[_NI]["value_text"]),
    )
    if endpoint.key[2] == "Q1":
        return current
    if index == 0:
        raise SecCashQualityTtmCoverageV2Error("duration predecessor missing")
    prior = endpoints[index - 1]
    expected = {"Q2": "Q1", "Q3": "Q2", "FY": "Q3"}[endpoint.key[2]]
    if prior.key[2] != expected or prior.key[1] != endpoint.key[1]:
        raise SecCashQualityTtmCoverageV2Error("duration predecessor differs")
    return (
        current[0] - Decimal(prior.rows[_CFO]["value_text"]),
        current[1] - Decimal(prior.rows[_NI]["value_text"]),
    )


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _result(plan, issuer_count, ready_issuers, blockers, rows):
    cfo = [Decimal(row["ttm_cfo_text"]) for row in rows]
    ni = [Decimal(row["ttm_net_income_text"]) for row in rows]
    assets = [Decimal(row["average_assets_text"]) for row in rows]
    times = [row["knowledge_at_utc"] for row in rows]
    values = {
        "plan_fingerprint": plan.logical_fingerprint,
        "input_endpoint_count": plan.input_endpoint_count,
        "input_query_row_count": plan.input_query_row_count,
        "issuer_count": issuer_count,
        "ttm_ready_endpoint_count": len(rows),
        "ttm_ready_issuer_count": len(ready_issuers),
        "ttm_blocked_endpoint_count": sum(blockers.values()),
        "blocker_counts": tuple(sorted(blockers.items())),
        "negative_ttm_cfo_count": sum(value < 0 for value in cfo),
        "zero_ttm_cfo_count": sum(value == 0 for value in cfo),
        "negative_ttm_net_income_count": sum(value < 0 for value in ni),
        "zero_ttm_net_income_count": sum(value == 0 for value in ni),
        "negative_average_assets_count": sum(value < 0 for value in assets),
        "earliest_knowledge_at": min(times) if times else None,
        "latest_knowledge_at": max(times) if times else None,
    }
    provisional = SecCashQualityTtmCoverageResultV2.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualityTtmCoverageResultV2.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )


def _table_bytes(table: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, TTM_V2_ARROW_SCHEMA) as writer:
        writer.write_table(table.combine_chunks())
    return sink.getvalue().to_pybytes()
