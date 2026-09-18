"""Pure issuer-level four-quarter TTM derivation from ready SEC endpoints."""

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
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_ttm_coverage import (
    SecCashQualityTtmCoveragePlanV1,
    SecCashQualityTtmCoverageResultV1,
    SecCashQualityTtmCoverageVerificationV1,
)


TTM_ARROW_SCHEMA = pa.schema(
    [
        pa.field("companyfacts_cik", pa.string(), nullable=False),
        pa.field("fiscal_year", pa.int32(), nullable=False),
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


class SecCashQualityTtmCoverageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EconomicEndpointCanonicalization:
    """Outcome-blind disposition of repeated comparative endpoint variants."""

    input_endpoint_variant_count: int
    canonical_endpoint_count: int
    superseded_endpoint_variant_count: int
    incomparable_endpoint_variant_count: int

    def __post_init__(self) -> None:
        if self.input_endpoint_variant_count != (
            self.canonical_endpoint_count
            + self.superseded_endpoint_variant_count
            + self.incomparable_endpoint_variant_count
        ):
            raise SecCashQualityTtmCoverageError(
                "economic endpoint canonicalization counts differ"
            )


def canonicalize_comparative_endpoint_variants(
    *, selected_endpoints: pa.Table
) -> tuple[pa.Table, EconomicEndpointCanonicalization]:
    """Select only a uniquely componentwise-latest exact economic endpoint.

    Company Facts ``fy`` describes the filing's fiscal focus.  The same
    economic endpoint can therefore be repeated under later ``fy`` values.
    A variant supersedes another only when every required component is at
    least as recently available.  Incomparable or tied variants fail closed.
    """

    variants: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for row in selected_endpoints.to_pylist():
        key = (
            row["companyfacts_cik"],
            row["fiscal_year_origin"],
            row["fiscal_period"],
            row["period_end"],
            row["fiscal_year"],
        )
        if row["query_id"] in variants[key]:
            raise SecCashQualityTtmCoverageError("duplicate endpoint query row")
        variants[key][row["query_id"]] = row

    by_economic_endpoint: dict[tuple, list[dict[str, dict]]] = defaultdict(list)
    for key, rows in variants.items():
        if set(rows) != {_ASSETS, _NI, _CFO}:
            raise SecCashQualityTtmCoverageError(
                "economic endpoint query membership differs"
            )
        by_economic_endpoint[key[:4]].append(rows)

    canonical_rows: list[dict] = []
    superseded_count = 0
    incomparable_count = 0
    for key in sorted(by_economic_endpoint):
        candidates = by_economic_endpoint[key]
        dominators = [
            candidate
            for candidate in candidates
            if all(
                all(
                    candidate[query_id]["source_available_at_utc"]
                    >= other[query_id]["source_available_at_utc"]
                    for query_id in (_ASSETS, _NI, _CFO)
                )
                for other in candidates
            )
        ]
        if len(dominators) != 1:
            incomparable_count += len(candidates)
            continue
        canonical_rows.extend(dominators[0].values())
        superseded_count += len(candidates) - 1

    canonical_rows.sort(
        key=lambda row: (
            row["companyfacts_cik"],
            row["fiscal_year_origin"],
            row["fiscal_period"],
            row["period_end"],
            row["query_id"],
        )
    )
    report = EconomicEndpointCanonicalization(
        input_endpoint_variant_count=len(variants),
        canonical_endpoint_count=len(canonical_rows) // 3,
        superseded_endpoint_variant_count=superseded_count,
        incomparable_endpoint_variant_count=incomparable_count,
    )
    return pa.Table.from_pylist(canonical_rows, schema=selected_endpoints.schema), report


def derive_sec_cash_quality_ttm_coverage(
    *,
    selected_endpoints: pa.Table,
    plan: SecCashQualityTtmCoveragePlanV1,
    traversal_order: Literal["forward", "reverse"] = "forward",
) -> tuple[pa.Table, SecCashQualityTtmCoverageResultV1]:
    """Derive only provable issuer TTM rows and aggregate all blocked endpoints."""

    grouped: dict[tuple[str, int, str, object, object], dict[str, dict]] = defaultdict(dict)
    for row in selected_endpoints.to_pylist():
        key = (
            row["companyfacts_cik"], row["fiscal_year"],
            row["fiscal_period"], row["fiscal_year_origin"], row["period_end"],
        )
        if row["query_id"] in grouped[key]:
            raise SecCashQualityTtmCoverageError("duplicate endpoint query row")
        grouped[key][row["query_id"]] = row
    if len(grouped) != plan.input_endpoint_count:
        raise SecCashQualityTtmCoverageError("TTM input endpoint denominator differs")
    by_cik: dict[str, list[tuple[tuple, dict[str, dict]]]] = defaultdict(list)
    for key, rows in grouped.items():
        if set(rows) != {_ASSETS, _NI, _CFO}:
            raise SecCashQualityTtmCoverageError("TTM endpoint query membership differs")
        if rows[_NI]["accession_number"] != rows[_CFO]["accession_number"]:
            raise SecCashQualityTtmCoverageError("TTM endpoint duration accession differs")
        by_cik[key[0]].append((key, rows))
    blockers: Counter[str] = Counter()
    output: list[dict[str, object]] = []
    ready_issuers: set[str] = set()
    for cik in sorted(by_cik, reverse=traversal_order == "reverse"):
        endpoints = sorted(by_cik[cik], key=lambda item: item[0][4])
        duplicate_periods = Counter((key[3], key[2]) for key, _ in endpoints)
        iterable = range(len(endpoints))
        if traversal_order == "reverse":
            iterable = reversed(tuple(iterable))
        for index in iterable:
            key, _ = endpoints[index]
            if duplicate_periods[(key[3], key[2])] != 1:
                blockers["fiscal_period_endpoint_ambiguous"] += 1
                continue
            if index < 4:
                blockers["insufficient_prior_endpoints"] += 1
                continue
            window = endpoints[index - 4 : index + 1]
            if not all(_consecutive(window[pos][0], window[pos + 1][0]) for pos in range(4)):
                blockers["quarter_sequence_not_consecutive"] += 1
                continue
            if not _annual_shapes_valid(window, plan):
                blockers["fiscal_year_duration_out_of_bounds"] += 1
                continue
            try:
                discrete = [_discrete(endpoints, pos) for pos in range(index - 3, index + 1)]
                ttm_cfo = sum((item[0] for item in discrete), Decimal(0))
                ttm_ni = sum((item[1] for item in discrete), Decimal(0))
                opening_assets = Decimal(window[0][1][_ASSETS]["value_text"])
                closing_assets = Decimal(window[-1][1][_ASSETS]["value_text"])
            except (InvalidOperation, TypeError, SecCashQualityTtmCoverageError):
                blockers["numeric_or_increment_unprovable"] += 1
                continue
            average_assets = (opening_assets + closing_assets) / Decimal(2)
            if average_assets == 0:
                blockers["zero_average_assets"] += 1
                continue
            component_rows = [row for _, rows in window for row in rows.values()]
            knowledge_at = max(row["source_available_at_utc"] for row in component_rows)
            output.append(
                {
                    "companyfacts_cik": cik,
                    "fiscal_year": key[1],
                    "fiscal_period": key[2],
                    "period_end": key[4],
                    "ttm_cfo_text": _decimal_text(ttm_cfo),
                    "ttm_net_income_text": _decimal_text(ttm_ni),
                    "opening_assets_text": _decimal_text(opening_assets),
                    "closing_assets_text": _decimal_text(closing_assets),
                    "average_assets_text": _decimal_text(average_assets),
                    "knowledge_at_utc": knowledge_at,
                    "component_accessions": sorted({row["accession_number"] for row in component_rows}),
                    "source_occurrence_ids": sorted({value for row in component_rows for value in row["source_occurrence_ids"]}),
                }
            )
            ready_issuers.add(cik)
    output.sort(key=lambda row: (row["companyfacts_cik"], row["period_end"]))
    result = _result(plan, len(by_cik), ready_issuers, blockers, output)
    return pa.Table.from_pylist(output, schema=TTM_ARROW_SCHEMA), result


def independently_verify_sec_cash_quality_ttm_coverage(
    *, selected_endpoints: pa.Table, plan: SecCashQualityTtmCoveragePlanV1
) -> tuple[pa.Table, SecCashQualityTtmCoverageResultV1, SecCashQualityTtmCoverageVerificationV1]:
    primary_rows, primary = derive_sec_cash_quality_ttm_coverage(
        selected_endpoints=selected_endpoints, plan=plan, traversal_order="forward"
    )
    replay_rows, replay = derive_sec_cash_quality_ttm_coverage(
        selected_endpoints=selected_endpoints, plan=plan, traversal_order="reverse"
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
    provisional = SecCashQualityTtmCoverageVerificationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    verification = SecCashQualityTtmCoverageVerificationV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )
    return primary_rows, primary, verification


def _table_bytes(table: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, TTM_ARROW_SCHEMA) as writer:
        writer.write_table(table.combine_chunks())
    return sink.getvalue().to_pybytes()


def _consecutive(left: tuple, right: tuple) -> bool:
    if left[2] in _NEXT:
        return right[2] == _NEXT[left[2]] and right[3] == left[3]
    return (
        left[2] == "FY" and right[2] == "Q1"
        and right[3] == left[4] + timedelta(days=1)
    )


def _annual_shapes_valid(window: list, plan: SecCashQualityTtmCoveragePlanV1) -> bool:
    for key, _ in window:
        if key[2] == "FY":
            days = (key[4] - key[3]).days + 1
            if not plan.annual_duration_days_minimum <= days <= plan.annual_duration_days_maximum:
                return False
    return True


def _discrete(endpoints: list, index: int) -> tuple[Decimal, Decimal]:
    key, rows = endpoints[index]
    current = (Decimal(rows[_CFO]["value_text"]), Decimal(rows[_NI]["value_text"]))
    if key[2] == "Q1":
        return current
    if index == 0:
        raise SecCashQualityTtmCoverageError("duration predecessor missing")
    prior_key, prior_rows = endpoints[index - 1]
    expected = {"Q2": "Q1", "Q3": "Q2", "FY": "Q3"}[key[2]]
    if prior_key[2] != expected or prior_key[3] != key[3]:
        raise SecCashQualityTtmCoverageError("duration predecessor differs")
    return (
        current[0] - Decimal(prior_rows[_CFO]["value_text"]),
        current[1] - Decimal(prior_rows[_NI]["value_text"]),
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
        "ttm_ready_endpoint_count": len(rows),
        "ttm_blocked_endpoint_count": sum(blockers.values()),
        "issuer_count": issuer_count,
        "ttm_ready_issuer_count": len(ready_issuers),
        "blocker_counts": tuple(sorted(blockers.items())),
        "negative_ttm_cfo_count": sum(value < 0 for value in cfo),
        "zero_ttm_cfo_count": sum(value == 0 for value in cfo),
        "negative_ttm_net_income_count": sum(value < 0 for value in ni),
        "zero_ttm_net_income_count": sum(value == 0 for value in ni),
        "negative_average_assets_count": sum(value < 0 for value in assets),
        "earliest_knowledge_at": min(times) if times else None,
        "latest_knowledge_at": max(times) if times else None,
    }
    provisional = SecCashQualityTtmCoverageResultV1.model_construct(**values, logical_fingerprint="0" * 64)
    return SecCashQualityTtmCoverageResultV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )
