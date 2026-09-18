from __future__ import annotations

import random
from datetime import UTC, date, datetime

import pyarrow as pa

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_direct_origin_selection import (
    build_sec_cash_quality_direct_origin_selection_plan_v2,
)
from tip_api.persistence.quant_research_sec_cash_quality_direct_origin_selection import (
    publish_sec_cash_quality_direct_origin_selection_v2,
    read_sec_cash_quality_direct_origin_selection_v2,
)
from tip_api.persistence.quant_research_sec_cash_quality_endpoint_selection import (
    TARGET_INDEX_SCHEMA,
    _schema_fingerprint,
)
from tip_api.services.quant_research_sec_cash_quality_direct_origin_selection import (
    independently_verify_sec_cash_quality_direct_origin_selection_v2,
    select_sec_cash_quality_direct_origin_endpoints_v2,
)


def test_q2_uses_direct_duration_origin_without_q1_witness() -> None:
    rows = _endpoint(fy=2025, fp="Q2", origin=date(2025, 1, 1), end=date(2025, 6, 30))
    table, plan = _table_plan(rows)

    selected, result, verification = (
        independently_verify_sec_cash_quality_direct_origin_selection_v2(
            target_index=table, plan=plan
        )
    )

    assert selected.num_rows == 3
    assert result.canonical_endpoint_count == 1
    assert dict(result.fiscal_period_canonical_endpoint_counts) == {"Q2": 1}
    assert verification.status == "byte_identical"


def test_multiple_complete_direct_origins_fail_closed() -> None:
    rows = _endpoint(fy=2025, fp="Q2", origin=date(2025, 1, 1), end=date(2025, 6, 30))
    rows.extend(
        row
        for row in _endpoint(
            fy=2025, fp="Q2", origin=date(2025, 1, 2), end=date(2025, 6, 30),
            accession="0000000001-25-000002",
        )
        if row["concept_name"] != "Assets"
    )
    table, plan = _table_plan(rows)

    selected, result = select_sec_cash_quality_direct_origin_endpoints_v2(
        target_index=table, plan=plan
    )

    assert selected.num_rows == 0
    assert dict(result.selector_blocker_counts) == {
        "multiple_complete_duration_origins": 1
    }


def test_comparative_variant_is_componentwise_latest_and_order_independent() -> None:
    rows = _endpoint(fy=2024, fp="FY", origin=date(2024, 1, 1), end=date(2024, 12, 31))
    later = _endpoint(
        fy=2025, fp="FY", origin=date(2024, 1, 1), end=date(2024, 12, 31),
        accession="0000000001-25-000002", available=datetime(2026, 2, 1, tzinfo=UTC),
    )
    rows.extend(later)
    table, plan = _table_plan(rows)
    expected, expected_result = select_sec_cash_quality_direct_origin_endpoints_v2(
        target_index=table, plan=plan
    )
    shuffled = list(rows)
    random.Random(7).shuffle(shuffled)
    replay = pa.Table.from_pylist(shuffled, schema=TARGET_INDEX_SCHEMA)

    actual, actual_result = select_sec_cash_quality_direct_origin_endpoints_v2(
        target_index=replay, plan=plan, traversal_order="reverse"
    )

    assert actual.equals(expected)
    assert actual_result == expected_result
    assert actual_result.selected_endpoint_variant_count == 2
    assert actual_result.canonical_endpoint_count == 1
    assert actual_result.superseded_comparative_variant_count == 1
    assert {row["fiscal_year"] for row in actual.to_pylist()} == {2025}


def test_crossed_comparative_component_clocks_fail_closed() -> None:
    rows = _endpoint(fy=2024, fp="FY", origin=date(2024, 1, 1), end=date(2024, 12, 31))
    later = _endpoint(
        fy=2025, fp="FY", origin=date(2024, 1, 1), end=date(2024, 12, 31),
        accession="0000000001-25-000002",
    )
    rows[0]["source_available_at_utc"] = datetime(2026, 3, 1, tzinfo=UTC)
    later[1]["source_available_at_utc"] = datetime(2026, 3, 1, tzinfo=UTC)
    later[2]["source_available_at_utc"] = datetime(2026, 3, 1, tzinfo=UTC)
    table, plan = _table_plan(rows + later)

    selected, result = select_sec_cash_quality_direct_origin_endpoints_v2(
        target_index=table, plan=plan
    )

    assert selected.num_rows == 0
    assert dict(result.canonicalization_blocker_counts) == {
        "comparative_component_clocks_crossed": 2
    }


def test_equal_latest_accession_values_conflict_fails_closed() -> None:
    rows = _endpoint(
        fy=2025, fp="Q2", origin=date(2025, 1, 1), end=date(2025, 6, 30)
    )
    conflicting = dict(rows[2])
    conflicting["accession_number"] = "0000000001-25-000099"
    conflicting["source_occurrence_id"] = "f" * 64
    conflicting["value_text"] = "31"
    table, plan = _table_plan(rows + [conflicting])

    selected, result = select_sec_cash_quality_direct_origin_endpoints_v2(
        target_index=table, plan=plan
    )

    assert selected.num_rows == 0
    assert dict(result.selector_blocker_counts) == {
        "latest_availability_value_conflict": 1
    }


def test_equal_comparative_clocks_fail_closed_even_when_values_match() -> None:
    rows = _endpoint(
        fy=2024, fp="FY", origin=date(2024, 1, 1), end=date(2024, 12, 31)
    )
    later = _endpoint(
        fy=2025, fp="FY", origin=date(2024, 1, 1), end=date(2024, 12, 31),
        accession="0000000001-25-000002",
    )
    table, plan = _table_plan(rows + later)

    selected, result = select_sec_cash_quality_direct_origin_endpoints_v2(
        target_index=table, plan=plan
    )

    assert selected.num_rows == 0
    assert dict(result.canonicalization_blocker_counts) == {
        "comparative_latest_clock_tie": 2
    }


def test_owner_only_publish_and_exact_reread(tmp_path) -> None:
    table, plan = _table_plan(
        _endpoint(fy=2025, fp="Q3", origin=date(2025, 1, 1), end=date(2025, 9, 30))
    )
    rows, result, verification = (
        independently_verify_sec_cash_quality_direct_origin_selection_v2(
            target_index=table, plan=plan
        )
    )
    published = publish_sec_cash_quality_direct_origin_selection_v2(
        custody_root=tmp_path / "custody", plan=plan, rows=rows,
        result=result, verification=verification,
    )

    reread = read_sec_cash_quality_direct_origin_selection_v2(
        package_path=published.package_path
    )

    assert reread.status == "exact_reread_complete"
    assert reread.rows.equals(rows)


def _table_plan(rows):
    table = pa.Table.from_pylist(rows, schema=TARGET_INDEX_SCHEMA)
    plan = build_sec_cash_quality_direct_origin_selection_plan_v2(
        source_endpoint_package_fingerprint="1" * 64,
        source_selection_plan_fingerprint="2" * 64,
        target_index_physical_sha256="3" * 64,
        target_index_schema_fingerprint=_schema_fingerprint(TARGET_INDEX_SCHEMA),
        target_index_row_count=table.num_rows,
        target_index_bytes=1,
    )
    return table, plan


def _endpoint(
    *, fy: int, fp: str, origin: date, end: date,
    accession: str = "0000000001-25-000001",
    available: datetime = datetime(2026, 1, 1, tzinfo=UTC),
):
    output = []
    for ordinal, (concept, start, value) in enumerate(
        (
            ("Assets", None, "100"),
            ("NetIncomeLoss", origin, "20"),
            ("NetCashProvidedByUsedInOperatingActivities", origin, "30"),
        )
    ):
        output.append(
            {
                "source_occurrence_id": f"{fy:04d}{ordinal:060d}",
                "companyfacts_cik": "0000000001",
                "namespace": "us-gaap",
                "concept_name": concept,
                "unit": "USD",
                "start_date": start,
                "end_date": end,
                "value_kind": "integer",
                "value_text": value,
                "accession_number": accession,
                "fiscal_year": fy,
                "fiscal_period": fp,
                "form": "10-Q" if fp != "FY" else "10-K",
                "filed_date": available.date(),
                "source_available_at_utc": available,
                "signal_eligible_session": available.date(),
                "filing_clock_admission_status": "admitted",
                "normalization_status": "admitted",
                "occurrence_disposition": "query_candidate",
            }
        )
    return output
