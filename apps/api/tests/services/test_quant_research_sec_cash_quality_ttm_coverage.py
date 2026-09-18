from __future__ import annotations

from datetime import UTC, date, datetime

import pyarrow as pa

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_ttm_coverage import (
    build_sec_cash_quality_ttm_coverage_plan_v1,
)
from tip_api.persistence.quant_research_sec_cash_quality_endpoint_selection import (
    SELECTED_ENDPOINT_SCHEMA,
)
from tip_api.services.quant_research_sec_cash_quality_ttm_coverage import (
    canonicalize_comparative_endpoint_variants,
    derive_sec_cash_quality_ttm_coverage,
    independently_verify_sec_cash_quality_ttm_coverage,
)
from tip_api.persistence.quant_research_sec_cash_quality_ttm_coverage import (
    publish_sec_cash_quality_ttm_coverage,
    read_sec_cash_quality_ttm_coverage,
)


def test_ttm_derives_incremental_quarters_and_replays_in_reverse(tmp_path) -> None:
    table = _table()
    plan = build_sec_cash_quality_ttm_coverage_plan_v1(
        endpoint_package_fingerprint="1" * 64,
        endpoint_plan_fingerprint="2" * 64,
        endpoint_count=5,
    )
    forward_rows, forward = derive_sec_cash_quality_ttm_coverage(
        selected_endpoints=table, plan=plan
    )
    reverse_rows, reverse = derive_sec_cash_quality_ttm_coverage(
        selected_endpoints=table, plan=plan, traversal_order="reverse"
    )

    assert forward == reverse
    assert forward_rows.equals(reverse_rows)
    assert forward.ttm_ready_endpoint_count == 1
    assert forward.ttm_blocked_endpoint_count == 4
    assert dict(forward.blocker_counts) == {"insufficient_prior_endpoints": 4}
    row = forward_rows.to_pylist()[0]
    assert row["ttm_cfo_text"] == "120"
    assert row["ttm_net_income_text"] == "60"
    assert row["average_assets_text"] == "160"
    rows, result, verification = independently_verify_sec_cash_quality_ttm_coverage(
        selected_endpoints=table, plan=plan
    )
    published = publish_sec_cash_quality_ttm_coverage(
        custody_root=tmp_path / "custody", plan=plan, rows=rows,
        result=result, verification=verification,
    )
    reread = read_sec_cash_quality_ttm_coverage(package_path=published.package_path)
    assert reread.status == "exact_reread_complete"
    assert reread.rows.equals(rows)


def test_ttm_accepts_negative_and_zero_flows_but_blocks_zero_assets() -> None:
    rows = _rows(cfo=(100, -10, 0, 5, 5), ni=(50, 0, -5, 0, 0))
    for row in rows:
        if row["period_end"] in (date(2024, 12, 31), date(2025, 12, 31)):
            if row["query_id"] == "assets_fiscal_boundary_v1":
                row["value_text"] = "0"
    table = pa.Table.from_pylist(rows, schema=SELECTED_ENDPOINT_SCHEMA)
    plan = build_sec_cash_quality_ttm_coverage_plan_v1(
        endpoint_package_fingerprint="1" * 64,
        endpoint_plan_fingerprint="2" * 64,
        endpoint_count=5,
    )
    output, result = derive_sec_cash_quality_ttm_coverage(
        selected_endpoints=table, plan=plan
    )
    assert output.num_rows == 0
    assert dict(result.blocker_counts)["zero_average_assets"] == 1


def test_ttm_accepts_proven_fifty_three_week_fiscal_year() -> None:
    rows = _rows()
    coordinates = {
        (2024, "FY"): (date(2023, 12, 31), date(2025, 1, 4)),
        (2025, "Q1"): (date(2025, 1, 5), date(2025, 4, 5)),
        (2025, "Q2"): (date(2025, 1, 5), date(2025, 7, 5)),
        (2025, "Q3"): (date(2025, 1, 5), date(2025, 10, 5)),
        (2025, "FY"): (date(2025, 1, 5), date(2026, 1, 3)),
    }
    for row in rows:
        row["fiscal_year_origin"], row["period_end"] = coordinates[
            (row["fiscal_year"], row["fiscal_period"])
        ]
    table = pa.Table.from_pylist(rows, schema=SELECTED_ENDPOINT_SCHEMA)
    plan = build_sec_cash_quality_ttm_coverage_plan_v1(
        endpoint_package_fingerprint="1" * 64,
        endpoint_plan_fingerprint="2" * 64,
        endpoint_count=5,
    )
    output, result = derive_sec_cash_quality_ttm_coverage(
        selected_endpoints=table, plan=plan
    )
    assert output.num_rows == 1
    assert result.ttm_ready_endpoint_count == 1


def test_comparative_facts_reusing_filing_fy_do_not_merge_economic_cycles() -> None:
    rows = _rows()
    for row in rows:
        row["fiscal_year"] = 2025
    table = pa.Table.from_pylist(rows, schema=SELECTED_ENDPOINT_SCHEMA)
    plan = build_sec_cash_quality_ttm_coverage_plan_v1(
        endpoint_package_fingerprint="1" * 64,
        endpoint_plan_fingerprint="2" * 64,
        endpoint_count=5,
    )
    output, result = derive_sec_cash_quality_ttm_coverage(
        selected_endpoints=table, plan=plan
    )
    assert output.num_rows == 1
    assert "fiscal_period_endpoint_ambiguous" not in dict(result.blocker_counts)


def test_exact_economic_endpoint_uses_componentwise_latest_variant() -> None:
    rows = _rows()[:3]
    later = [dict(row) for row in rows]
    for row in later:
        row["fiscal_year"] = 2025
        row["value_text"] = str(int(row["value_text"]) + 1)
        row["source_available_at_utc"] = datetime(2026, 6, 1, tzinfo=UTC)
        row["source_occurrence_ids"] = ["f" * 64]
    table = pa.Table.from_pylist(rows + later, schema=SELECTED_ENDPOINT_SCHEMA)

    canonical, report = canonicalize_comparative_endpoint_variants(
        selected_endpoints=table
    )
    replay, replay_report = canonicalize_comparative_endpoint_variants(
        selected_endpoints=table.take(pa.array(tuple(reversed(range(table.num_rows)))))
    )

    assert report.input_endpoint_variant_count == 2
    assert report.canonical_endpoint_count == 1
    assert report.superseded_endpoint_variant_count == 1
    assert report.incomparable_endpoint_variant_count == 0
    assert {row["fiscal_year"] for row in canonical.to_pylist()} == {2025}
    assert replay_report == report
    assert replay.equals(canonical)


def test_exact_economic_endpoint_fails_closed_when_component_clocks_cross() -> None:
    rows = _rows()[:3]
    later = [dict(row) for row in rows]
    for row in later:
        row["fiscal_year"] = 2025
        row["source_occurrence_ids"] = ["f" * 64]
    rows[0]["source_available_at_utc"] = datetime(2026, 6, 1, tzinfo=UTC)
    later[1]["source_available_at_utc"] = datetime(2026, 6, 1, tzinfo=UTC)
    later[2]["source_available_at_utc"] = datetime(2026, 6, 1, tzinfo=UTC)
    table = pa.Table.from_pylist(rows + later, schema=SELECTED_ENDPOINT_SCHEMA)

    canonical, report = canonicalize_comparative_endpoint_variants(
        selected_endpoints=table
    )

    assert canonical.num_rows == 0
    assert report.canonical_endpoint_count == 0
    assert report.superseded_endpoint_variant_count == 0
    assert report.incomparable_endpoint_variant_count == 2


def _table() -> pa.Table:
    return pa.Table.from_pylist(_rows(), schema=SELECTED_ENDPOINT_SCHEMA)


def _rows(
    *, cfo=(80, 10, 25, 45, 120), ni=(40, 5, 12, 20, 60)
) -> list[dict[str, object]]:
    endpoints = (
        (2024, date(2024, 1, 1), "FY", date(2024, 12, 31)),
        (2025, date(2025, 1, 1), "Q1", date(2025, 3, 31)),
        (2025, date(2025, 1, 1), "Q2", date(2025, 6, 30)),
        (2025, date(2025, 1, 1), "Q3", date(2025, 9, 30)),
        (2025, date(2025, 1, 1), "FY", date(2025, 12, 31)),
    )
    output = []
    for ordinal, ((fy, origin, fp, end), cfo_value, ni_value) in enumerate(
        zip(endpoints, cfo, ni, strict=True), start=1
    ):
        accession = f"0000000001-{fy % 100:02d}-{ordinal:06d}"
        for query, concept, value in (
            ("assets_fiscal_boundary_v1", "Assets", 100 + ordinal * 20),
            ("net_income_loss_fiscal_ytd_and_year_v1", "NetIncomeLoss", ni_value),
            ("operating_cash_flow_fiscal_ytd_and_year_v1", "NetCashProvidedByUsedInOperatingActivities", cfo_value),
        ):
            output.append(
                {
                    "companyfacts_cik": "0000000001",
                    "fiscal_year": fy,
                    "fiscal_year_origin": origin,
                    "fiscal_period": fp,
                    "period_end": end,
                    "query_id": query,
                    "concept_name": concept,
                    "value_kind": "integer",
                    "value_text": str(value),
                    "accession_number": accession,
                    "source_available_at_utc": datetime(2026, ordinal, 1, tzinfo=UTC),
                    "signal_eligible_session": date(2026, ordinal, 2),
                    "source_occurrence_ids": [f"{ordinal:064x}"],
                }
            )
    return output
