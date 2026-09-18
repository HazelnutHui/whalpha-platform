from __future__ import annotations

from datetime import UTC, date, datetime

import pyarrow as pa

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_ttm_coverage_v2 import build_sec_cash_quality_ttm_coverage_plan_v2
from tip_api.persistence.quant_research_sec_cash_quality_endpoint_selection import SELECTED_ENDPOINT_SCHEMA, _schema_fingerprint
from tip_api.persistence.quant_research_sec_cash_quality_ttm_coverage_v2 import publish_sec_cash_quality_ttm_coverage_v2, read_sec_cash_quality_ttm_coverage_v2
from tip_api.services.quant_research_sec_cash_quality_ttm_coverage_v2 import derive_sec_cash_quality_ttm_coverage_v2, independently_verify_sec_cash_quality_ttm_coverage_v2


def test_ttm_v2_uses_economic_origin_not_reported_fy_and_replays() -> None:
    table = _table()
    plan = _plan(table)
    rows, result, verification = independently_verify_sec_cash_quality_ttm_coverage_v2(
        selected_endpoints=table, plan=plan
    )
    assert rows.num_rows == 1
    assert result.ttm_ready_endpoint_count == 1
    assert dict(result.blocker_counts) == {"insufficient_prior_endpoints": 4}
    assert rows.to_pylist()[0]["ttm_cfo_text"] == "120"
    assert rows.to_pylist()[0]["ttm_net_income_text"] == "60"
    assert rows.to_pylist()[0]["average_assets_text"] == "160"
    assert rows.to_pylist()[0]["fiscal_year_origin"] == date(2025, 1, 1)
    assert verification.status == "byte_identical"


def test_ttm_v2_accepts_proven_fifty_three_week_boundary() -> None:
    coordinates = (
        (date(2023, 12, 31), "FY", date(2025, 1, 4)),
        (date(2025, 1, 5), "Q1", date(2025, 4, 5)),
        (date(2025, 1, 5), "Q2", date(2025, 7, 5)),
        (date(2025, 1, 5), "Q3", date(2025, 10, 5)),
        (date(2025, 1, 5), "FY", date(2026, 1, 3)),
    )
    table = _table(coordinates=coordinates)
    rows, result = derive_sec_cash_quality_ttm_coverage_v2(
        selected_endpoints=table, plan=_plan(table)
    )
    assert rows.num_rows == 1
    assert result.ttm_ready_endpoint_count == 1


def test_ttm_v2_quarantines_multiple_ends_for_one_origin_period() -> None:
    base = _rows()
    duplicate = [dict(row) for row in base[3:6]]
    for row in duplicate:
        row["period_end"] = date(2025, 4, 1)
        row["source_occurrence_ids"] = ["f" * 64]
    table = pa.Table.from_pylist(base + duplicate, schema=SELECTED_ENDPOINT_SCHEMA)
    _, result = derive_sec_cash_quality_ttm_coverage_v2(
        selected_endpoints=table, plan=_plan(table)
    )
    assert dict(result.blocker_counts)["fiscal_period_endpoint_ambiguous"] == 2


def test_ttm_v2_blocks_gap_and_zero_average_assets() -> None:
    rows = _rows()
    without_q2 = [row for row in rows if row["fiscal_period"] != "Q2"]
    gap_table = pa.Table.from_pylist(without_q2, schema=SELECTED_ENDPOINT_SCHEMA)
    _, gap = derive_sec_cash_quality_ttm_coverage_v2(
        selected_endpoints=gap_table, plan=_plan(gap_table)
    )
    assert gap.ttm_ready_endpoint_count == 0

    for row in rows:
        if row["query_id"] == "assets_fiscal_boundary_v1" and row["period_end"] in {
            date(2024, 12, 31), date(2025, 12, 31)
        }:
            row["value_text"] = "0"
    zero_table = pa.Table.from_pylist(rows, schema=SELECTED_ENDPOINT_SCHEMA)
    _, zero = derive_sec_cash_quality_ttm_coverage_v2(
        selected_endpoints=zero_table, plan=_plan(zero_table)
    )
    assert dict(zero.blocker_counts)["zero_average_assets"] == 1


def test_ttm_v2_owner_only_exact_reread(tmp_path) -> None:
    table = _table(); plan = _plan(table)
    rows, result, verification = independently_verify_sec_cash_quality_ttm_coverage_v2(
        selected_endpoints=table, plan=plan
    )
    published = publish_sec_cash_quality_ttm_coverage_v2(
        custody_root=tmp_path / "custody", plan=plan, rows=rows,
        result=result, verification=verification,
    )
    reread = read_sec_cash_quality_ttm_coverage_v2(package_path=published.package_path)
    assert reread.status == "exact_reread_complete"
    assert reread.rows.equals(rows)


def _plan(table):
    return build_sec_cash_quality_ttm_coverage_plan_v2(
        source_selection_verification_fingerprint="1" * 64,
        source_selection_result_fingerprint="2" * 64,
        source_rows_logical_sha256="3" * 64,
        source_rows_physical_sha256="4" * 64,
        source_rows_schema_fingerprint=_schema_fingerprint(SELECTED_ENDPOINT_SCHEMA),
        source_rows_bytes=1,
        input_endpoint_count=table.num_rows // 3,
        input_query_row_count=table.num_rows,
    )


def _table(*, coordinates=None):
    return pa.Table.from_pylist(_rows(coordinates=coordinates), schema=SELECTED_ENDPOINT_SCHEMA)


def _rows(*, coordinates=None):
    coordinates = coordinates or (
        (date(2024, 1, 1), "FY", date(2024, 12, 31)),
        (date(2025, 1, 1), "Q1", date(2025, 3, 31)),
        (date(2025, 1, 1), "Q2", date(2025, 6, 30)),
        (date(2025, 1, 1), "Q3", date(2025, 9, 30)),
        (date(2025, 1, 1), "FY", date(2025, 12, 31)),
    )
    cfo=(80,10,25,45,120); ni=(40,5,12,20,60)
    output=[]
    for ordinal, ((origin,fp,end),cfo_value,ni_value) in enumerate(zip(coordinates,cfo,ni,strict=True),1):
        accession=f"0000000001-25-{ordinal:06d}"
        for query,concept,value in (
            ("assets_fiscal_boundary_v1","Assets",100+ordinal*20),
            ("net_income_loss_fiscal_ytd_and_year_v1","NetIncomeLoss",ni_value),
            ("operating_cash_flow_fiscal_ytd_and_year_v1","NetCashProvidedByUsedInOperatingActivities",cfo_value),
        ):
            output.append({
                "companyfacts_cik":"0000000001","fiscal_year":2025,
                "fiscal_year_origin":origin,"fiscal_period":fp,"period_end":end,
                "query_id":query,"concept_name":concept,"value_kind":"integer",
                "value_text":str(value),"accession_number":accession,
                "source_available_at_utc":datetime(2026,ordinal,1,tzinfo=UTC),
                "signal_eligible_session":date(2026,ordinal,2),
                "source_occurrence_ids":[f"{ordinal:064x}"],
            })
    return output
