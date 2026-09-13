from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.providers.sec.companyfacts_normalized_source import (
    SecCompanyfactsNormalizedSourceManifestV1,
)
from tip_api.providers.sec.fundamental_projection_readiness_census import (
    _Timeline,
    _TimelinePoint,
    _flush_timeline_filer,
    _lookup_timeline,
    _scan_link_projection,
)
from tip_api.providers.sec.fundamental_query_readiness_census import _SelectedRow
from tip_api.providers.sec.fundamental_query_registry import (
    build_first_sec_fundamental_query_registry,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.sec_filer_security_link_decision import (
    CONTRACT_VERSION as LINK_CONTRACT_VERSION,
    LINK_ARROW_SCHEMA,
    PARQUET_FILE as LINK_PARQUET_FILE,
    SecFilerSecurityLinkManifestV1,
    SecFilerSecurityLinkSessionV1,
)


SHA = "a" * 64
CIK = "0000000001"
SIGNAL_SESSION = date(2025, 2, 28)
ENTRY_SESSION = date(2025, 3, 3)
CUTOFF = datetime(2025, 3, 3, 14, 30, tzinfo=UTC)
OBSERVED = datetime(2025, 3, 3, 12, tzinfo=UTC)


def _fact_row(
    ordinal: int,
    *,
    value: str,
    accession: str,
    available: datetime,
    eligible_session: date,
) -> _SelectedRow:
    return _SelectedRow(
        source_occurrence_id=f"{ordinal:064x}",
        source_member_name=f"CIK{CIK}.json",
        companyfacts_cik=CIK,
        namespace="us-gaap",
        concept_name="Assets",
        unit="USD",
        ordinal=ordinal,
        start_date=None,
        end_date=date(2024, 12, 31),
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


def test_timeline_changes_only_when_cutoff_state_changes() -> None:
    registry = build_first_sec_fundamental_query_registry()
    rows = [
        _fact_row(
            0,
            value="100",
            accession="0000000001-25-000001",
            available=datetime(2025, 2, 1, 12, tzinfo=UTC),
            eligible_session=date(2025, 2, 3),
        ),
        _fact_row(
            1,
            value="110",
            accession="0000000001-25-000002",
            available=datetime(2025, 3, 1, 12, tzinfo=UTC),
            eligible_session=ENTRY_SESSION,
        ),
    ]
    timelines: dict[tuple[str, str], _Timeline] = {}

    _flush_timeline_filer(
        CIK,
        {"assets_latest_reported_v1": rows},
        timelines,
        {query.query_id: query for query in registry.queries},
        ExchangeCalendar(),
        {},
    )

    timeline = timelines[(CIK, "assets_latest_reported_v1")]
    assert timeline.sessions == (date(2025, 2, 3),)
    assert _lookup_timeline(timeline, date(2025, 1, 31)).status == "not_available"
    assert _lookup_timeline(timeline, ENTRY_SESSION).status == "selected"


def _link_row(
    number: int,
    *,
    instrument_type: str,
    cik: str | None,
    status: str,
    cik_count: int | None,
) -> dict[str, object]:
    return {
        "contract_version": LINK_CONTRACT_VERSION,
        "as_of_date": SIGNAL_SESSION,
        "instrument_id": f"00000000-0000-0000-0000-{number:012d}",
        "ticker": f"T{number}",
        "instrument_type": instrument_type,
        "sec_cik": cik,
        "sec_filer_key": f"sec-cik:{cik}" if cik else None,
        "decision_status": status,
        "reason_codes": [] if status == "admitted_unique_cik" else ["cik_missing"],
        "source_identity_occurrence_count": 1,
        "cik_instrument_count": cik_count,
        "point_in_time_eligibility": "eligible_at_source_observed_at",
        "source_observed_at": OBSERVED,
        "source_row_set_fingerprint": SHA,
        "issuer_projection_authorized": False,
    }


def test_projection_scan_keeps_structural_and_query_denominators(
    tmp_path: Path,
) -> None:
    session_dir = tmp_path / f"as_of_date={SIGNAL_SESSION.isoformat()}"
    session_dir.mkdir(mode=0o700)
    path = session_dir / LINK_PARQUET_FILE
    rows = [
        _link_row(
            1,
            instrument_type="common_stock",
            cik=CIK,
            status="admitted_unique_cik",
            cik_count=1,
        ),
        _link_row(
            2,
            instrument_type="common_stock",
            cik="0000000002",
            status="admitted_unique_cik",
            cik_count=2,
        ),
        _link_row(
            3,
            instrument_type="common_stock",
            cik="0000000002",
            status="admitted_unique_cik",
            cik_count=2,
        ),
        _link_row(
            4,
            instrument_type="etf",
            cik="0000000003",
            status="admitted_unique_cik",
            cik_count=1,
        ),
        _link_row(
            5,
            instrument_type="common_stock",
            cik=None,
            status="quarantined_missing_cik",
            cik_count=None,
        ),
    ]
    pq.write_table(pa.Table.from_pylist(rows, schema=LINK_ARROW_SCHEMA), path)
    path.chmod(0o400)
    evidence = SecFilerSecurityLinkSessionV1.model_construct(
        as_of_date=SIGNAL_SESSION,
        relative_path=f"as_of_date={SIGNAL_SESSION.isoformat()}/{LINK_PARQUET_FILE}",
        row_count=len(rows),
        byte_size=path.stat().st_size,
        physical_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        point_in_time_eligibility="eligible_at_source_observed_at",
        source_observed_at=OBSERVED,
    )
    link = SecFilerSecurityLinkManifestV1.model_construct(
        sessions=(evidence,),
        range_start=SIGNAL_SESSION,
        range_end=SIGNAL_SESSION,
        calendar_version=ExchangeCalendar().calendar_version,
        session_count=1,
        row_count=len(rows),
        logical_fingerprint=SHA,
        content_fingerprint=SHA,
    )
    registry = build_first_sec_fundamental_query_registry()
    timelines = {
        (CIK, "assets_latest_reported_v1"): _Timeline(
            sessions=(ENTRY_SESSION,),
            points=(
                _TimelinePoint(
                    eligible_session=ENTRY_SESSION,
                    status="selected",
                    reason=None,
                    period_end=date(2024, 12, 31),
                ),
            ),
        ),
        (CIK, "operating_income_loss_fiscal_year_v1"): _Timeline(
            sessions=(ENTRY_SESSION,),
            points=(
                _TimelinePoint(
                    eligible_session=ENTRY_SESSION,
                    status="quarantined",
                    reason="same_period_end_multiple_starts",
                    period_end=None,
                ),
            ),
        ),
    }
    source = SecCompanyfactsNormalizedSourceManifestV1.model_construct(
        logical_fingerprint=SHA,
        content_fingerprint=SHA,
    )

    census = _scan_link_projection(
        link_package_path=tmp_path,
        link=link,
        link_manifest_sha256=SHA,
        timelines=timelines,
        registry=registry,
        readiness_census_sha256=SHA,
        readiness_logical_fingerprint=SHA,
        source=source,
        implementation_revision="b" * 40,
        evaluated_at=CUTOFF,
    )

    assert census.link_row_count == 5
    assert dict(census.link_disposition_counts) == {
        "common_link_not_admitted": 1,
        "common_multi_security_cik": 2,
        "common_single_as_operated_next_open": 1,
        "common_single_reconstructed_latest_vintage": 0,
        "link_source_custody_missing": 0,
        "not_common_stock": 1,
    }
    assert census.query_selection_evaluation_count == 4
    result = {
        (item.query_id, item.evidence_tier): dict(item.selection_status_counts)
        for item in census.query_tier_results
    }
    assert result[("assets_latest_reported_v1", "as_operated_next_open")] == {
        "not_available": 0,
        "quarantined": 0,
        "selected": 1,
    }
    assert result[
        ("operating_income_loss_fiscal_year_v1", "as_operated_next_open")
    ] == {"not_available": 0, "quarantined": 1, "selected": 0}
    assert result[("net_income_loss_fiscal_year_v1", "as_operated_next_open")][
        "not_available"
    ] == 1
    assert census.security_fact_rows_retained is False
    assert census.strategy_outcome_access_count == 0
