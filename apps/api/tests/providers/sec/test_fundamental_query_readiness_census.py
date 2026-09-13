from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.providers.sec.companyfacts_normalized_source import (
    CONTRACT_VERSION as NORMALIZED_CONTRACT_VERSION,
    OCCURRENCE_ARROW_SCHEMA,
    NormalizedArtifactV1,
    SecCompanyfactsNormalizedSourceManifestV1,
)
from tip_api.providers.sec.companyfacts_semantic_census import (
    SecCompanyfactsSemanticCensusV1,
)
from tip_api.providers.sec.fundamental_query_readiness_census import (
    _census_worker,
    _combine_results,
)
from tip_api.providers.sec.fundamental_query_registry import (
    build_first_sec_fundamental_query_registry,
)


CIK = "0000000001"
NOW = datetime(2025, 3, 1, 21, tzinfo=UTC)
SHA = "a" * 64


def _row(
    concept: str,
    ordinal: int,
    *,
    value: str,
    accession: str,
    end: date,
    start: date | None = None,
    unit: str = "USD",
    fiscal_period: str = "FY",
    form: str = "10-K",
    available: datetime = NOW,
) -> dict[str, object]:
    member = f"CIK{CIK}.json"
    return {
        "contract_version": NORMALIZED_CONTRACT_VERSION,
        "source_occurrence_id": hashlib.sha256(
            f"{concept}:{unit}:{ordinal}".encode()
        ).hexdigest(),
        "raw_fact_fingerprint": hashlib.sha256(
            f"raw:{concept}:{unit}:{ordinal}".encode()
        ).hexdigest(),
        "companyfacts_cik": CIK,
        "source_member_name": member,
        "concept_key": hashlib.sha256(f"{CIK}:us-gaap:{concept}".encode()).hexdigest(),
        "namespace": "us-gaap",
        "concept_name": concept,
        "unit": unit,
        "unit_occurrence_ordinal": ordinal,
        "start_raw": start.isoformat() if start else None,
        "start_date": start,
        "end_raw": end.isoformat(),
        "end_date": end,
        "value_kind": "integer",
        "value_text": value,
        "accession_number": accession,
        "fiscal_year_raw": "2024",
        "fiscal_year": 2024,
        "fiscal_period": fiscal_period,
        "form": form,
        "filed_date": date(2025, 2, 28),
        "frame": None,
        "filing_clock_admission_status": "admitted",
        "source_available_at_utc": available,
        "signal_eligible_session": date(2025, 3, 3),
        "clock_reason_codes": [],
        "normalization_status": "admitted",
        "normalization_reason_codes": [],
        "instrument_resolution_status": "unresolved",
        "instrument_id": None,
    }


def _artifact(root: Path) -> NormalizedArtifactV1:
    rows = [
        _row(
            "Assets",
            0,
            value="100",
            accession="0000000001-25-000001",
            end=date(2024, 12, 31),
        ),
        _row(
            "Assets",
            1,
            value="100",
            accession="0000000001-25-000001",
            end=date(2024, 12, 31),
        ),
        _row(
            "Assets",
            0,
            unit="shares",
            value="100",
            accession="0000000001-25-000001",
            end=date(2024, 12, 31),
        ),
        _row(
            "NetIncomeLoss",
            0,
            value="10",
            accession="0000000001-25-000002",
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        ),
        _row(
            "NetIncomeLoss",
            1,
            value="10",
            accession="0000000001-25-000003",
            start=date(2024, 1, 2),
            end=date(2024, 12, 31),
        ),
        _row(
            "NetIncomeLoss",
            2,
            value="5",
            accession="0000000001-24-000004",
            start=date(2024, 7, 1),
            end=date(2024, 12, 31),
        ),
        _row(
            "OperatingIncomeLoss",
            0,
            value="20",
            accession="0000000001-25-000005",
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        ),
        _row(
            "OperatingIncomeLoss",
            1,
            value="21",
            accession="0000000001-25-000005",
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        ),
        _row(
            "Revenue",
            0,
            value="30",
            accession="0000000001-25-000006",
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        ),
        _row(
            "StockholdersEquity",
            0,
            value="40",
            accession="0000000001-25-000007",
            end=date(2024, 12, 31),
        ),
        _row(
            "StockholdersEquity",
            1,
            value="41",
            accession="0000000001-25-000008",
            end=date(2024, 12, 31),
        ),
    ]
    rows.sort(
        key=lambda item: (
            item["source_member_name"],
            item["namespace"],
            item["concept_name"],
            item["unit"],
            item["unit_occurrence_ordinal"],
        )
    )
    worker = root / "worker=00"
    worker.mkdir()
    relative_path = "worker=00/occurrences-filed-year=2025.parquet"
    path = root / relative_path
    pq.write_table(pa.Table.from_pylist(rows, schema=OCCURRENCE_ARROW_SCHEMA), path)
    return NormalizedArtifactV1(
        artifact_kind="occurrence",
        worker_index=0,
        filed_year=2025,
        relative_path=relative_path,
        row_count=len(rows),
        byte_size=path.stat().st_size,
        physical_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        logical_fingerprint=SHA,
        schema_fingerprint=hashlib.sha256(
            OCCURRENCE_ARROW_SCHEMA.serialize().to_pybytes()
        ).hexdigest(),
    )


def test_worker_applies_query_filters_and_quarantines_ambiguity(
    tmp_path: Path,
) -> None:
    artifact = _artifact(tmp_path)
    registry = build_first_sec_fundamental_query_registry()

    result = _census_worker((str(tmp_path), 0, (artifact,), registry))

    assert result.scanned_occurrence_count == 11
    assets = result.queries["assets_latest_reported_v1"]
    assert assets.concept_occurrences == 3
    assert assets.dispositions == {"query_eligible": 2, "unit_not_allowed": 1}
    assert assets.semantic_period_keys == 1
    assert assets.clean_semantic_period_keys == 1
    assert assets.exact_duplicate_groups == 1
    assert assets.exact_duplicate_redundant_occurrences == 1
    assert assets.selectable_filers == {CIK}

    net_income = result.queries["net_income_loss_fiscal_year_v1"]
    assert net_income.concept_occurrences == 3
    assert net_income.dispositions == {
        "query_eligible": 2,
        "year_duration_out_of_range": 1,
    }
    assert net_income.semantic_period_keys == 2
    assert net_income.clean_semantic_period_keys == 0
    assert net_income.quarantined_semantic_period_keys == 2
    assert net_income.same_period_end_conflict_groups == 1
    assert net_income.selectable_filers == set()

    operating_income = result.queries["operating_income_loss_fiscal_year_v1"]
    assert operating_income.within_accession_conflict_groups == 1
    assert operating_income.quarantined_semantic_period_keys == 1
    assert operating_income.selectable_filers == set()

    equity = result.queries["stockholders_equity_latest_reported_v1"]
    assert equity.same_availability_conflict_groups == 1
    assert equity.quarantined_semantic_period_keys == 1
    assert equity.selectable_filers == set()


def test_combined_report_reconciles_denominators_and_zero_authority(
    tmp_path: Path,
) -> None:
    artifact = _artifact(tmp_path)
    registry = build_first_sec_fundamental_query_registry()
    worker = _census_worker((str(tmp_path), 0, (artifact,), registry))
    source = SecCompanyfactsNormalizedSourceManifestV1.model_construct(
        range_start=date(2021, 9, 13),
        range_end=date(2026, 9, 11),
        companyfacts_snapshot_date=date(2026, 9, 10),
        worker_count=1,
        occurrence_count=11,
        content_fingerprint=SHA,
        logical_fingerprint=SHA,
    )
    semantic = SecCompanyfactsSemanticCensusV1.model_construct(
        logical_fingerprint=SHA
    )

    census = _combine_results(
        results=(worker,),
        registry=registry,
        semantic=semantic,
        semantic_census_sha256=SHA,
        source=source,
        source_manifest_sha256=SHA,
        process_count=1,
        implementation_revision="b" * 40,
        evaluated_at=NOW,
    )

    assert census.source_occurrence_count == 11
    assert census.scanned_occurrence_count == 11
    assert census.targeted_concept_occurrence_count == 10
    assert census.unregistered_concept_occurrence_count == 1
    assert census.strategy_outcome_access_count == 0
    assert census.canonical_data_write_count == 0
    assert census.publication_count == 0
    assert census.deployment_count == 0
