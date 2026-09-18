from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import (
    build_sec_cash_quality_source_readiness_plan_v1,
)
from tip_api.providers.sec.companyfacts_normalized_source import (
    CONTRACT_VERSION as NORMALIZED_CONTRACT_VERSION,
    OCCURRENCE_ARROW_SCHEMA,
    NormalizedArtifactV1,
    SecCompanyfactsNormalizedSourceManifestV1,
    SecCompanyfactsNormalizedSourceResult,
)
from tip_api.services.quant_research_sec_cash_quality_source_readiness_census import (
    SecCashQualitySourceReadinessCensusError,
    independently_verify_sec_cash_quality_source_readiness,
    run_sec_cash_quality_source_readiness_census,
)


CIK = "0000000001"
ORIGIN = date(2025, 1, 1)
Q1_END = date(2025, 3, 31)
Q2_END = date(2025, 6, 30)
AVAILABLE = datetime(2025, 8, 1, 12, tzinfo=UTC)


def _filtered_reader(package: Path, source: SecCompanyfactsNormalizedSourceResult):
    def read(**kwargs):
        consumer = kwargs["occurrence_batch_consumer"]
        concepts = kwargs["occurrence_concept_filter"]
        for artifact in source.manifest.artifacts:
            if artifact.artifact_kind != "occurrence":
                continue
            parquet = pq.ParquetFile(package / artifact.relative_path)
            for batch in parquet.iter_batches():
                filtered = batch.filter(
                    pc.is_in(
                        batch.column(batch.schema.get_field_index("concept_name")),
                        value_set=pa.array(sorted(concepts)),
                    )
                )
                if filtered.num_rows:
                    consumer(artifact, filtered)
        return source

    return read


def _raw(
    ordinal: int,
    *,
    concept: str,
    value: str,
    fiscal_period: str,
    end: date,
    start: date | None,
    accession: str,
) -> dict[str, object]:
    return {
        "contract_version": NORMALIZED_CONTRACT_VERSION,
        "source_occurrence_id": f"{ordinal:064x}",
        "raw_fact_fingerprint": f"{ordinal + 100:064x}",
        "companyfacts_cik": CIK,
        "source_member_name": f"CIK{CIK}.json",
        "concept_key": f"{ordinal + 200:064x}",
        "namespace": "us-gaap",
        "concept_name": concept,
        "unit": "USD",
        "unit_occurrence_ordinal": ordinal,
        "start_raw": start.isoformat() if start else None,
        "start_date": start,
        "end_raw": end.isoformat(),
        "end_date": end,
        "value_kind": "integer",
        "value_text": value,
        "accession_number": accession,
        "fiscal_year_raw": "2025",
        "fiscal_year": 2025,
        "fiscal_period": fiscal_period,
        "form": "10-Q",
        "filed_date": AVAILABLE.date(),
        "frame": None,
        "filing_clock_admission_status": "admitted",
        "source_available_at_utc": AVAILABLE,
        "signal_eligible_session": date(2025, 8, 4),
        "clock_reason_codes": [],
        "normalization_status": "admitted",
        "normalization_reason_codes": [],
        "instrument_resolution_status": "unresolved",
        "instrument_id": None,
    }


def _package(tmp_path: Path) -> tuple[Path, SecCompanyfactsNormalizedSourceManifestV1]:
    rows = [
        _raw(
            1,
            concept="NetIncomeLoss",
            value="10",
            fiscal_period="Q1",
            end=Q1_END,
            start=ORIGIN,
            accession="0000000001-25-000001",
        ),
        _raw(
            2,
            concept="NetCashProvidedByUsedInOperatingActivities",
            value="15",
            fiscal_period="Q1",
            end=Q1_END,
            start=ORIGIN,
            accession="0000000001-25-000001",
        ),
        _raw(
            3,
            concept="NetIncomeLoss",
            value="25",
            fiscal_period="Q2",
            end=Q2_END,
            start=ORIGIN,
            accession="0000000001-25-000002",
        ),
        _raw(
            4,
            concept="NetCashProvidedByUsedInOperatingActivities",
            value="40",
            fiscal_period="Q2",
            end=Q2_END,
            start=ORIGIN,
            accession="0000000001-25-000002",
        ),
        _raw(
            5,
            concept="Assets",
            value="500",
            fiscal_period="Q2",
            end=Q2_END,
            start=None,
            accession="0000000001-25-000002",
        ),
    ]
    package = tmp_path / "normalized"
    worker = package / "worker=00"
    worker.mkdir(parents=True)
    relative = "worker=00/occurrences-filed-year=2025.parquet"
    path = package / relative
    pq.write_table(pa.Table.from_pylist(rows, schema=OCCURRENCE_ARROW_SCHEMA), path)
    artifact = NormalizedArtifactV1(
        artifact_kind="occurrence",
        worker_index=0,
        filed_year=2025,
        relative_path=relative,
        row_count=len(rows),
        byte_size=path.stat().st_size,
        physical_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        logical_fingerprint="1" * 64,
        schema_fingerprint="2" * 64,
    )
    manifest = SecCompanyfactsNormalizedSourceManifestV1.model_construct(
        built_at=datetime(2025, 8, 5, tzinfo=UTC),
        range_start=date(2025, 1, 1),
        range_end=date(2025, 8, 4),
        worker_count=1,
        artifacts=(artifact,),
        occurrence_count=len(rows),
        occurrence_schema_fingerprint="3" * 64,
        filing_clock_manifest_fingerprint="4" * 64,
        content_fingerprint="5" * 64,
        logical_fingerprint="6" * 64,
    )
    return package, manifest


def test_bounded_census_counts_observed_endpoints_and_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package, manifest = _package(tmp_path)
    plan = build_sec_cash_quality_source_readiness_plan_v1(manifest)
    source = SecCompanyfactsNormalizedSourceResult(
        package_path=package,
        manifest=manifest,
    )
    monkeypatch.setattr(
        "tip_api.services.quant_research_sec_cash_quality_source_readiness_census."
        "read_sec_companyfacts_normalized_source",
        _filtered_reader(package, source),
    )

    result, verification = independently_verify_sec_cash_quality_source_readiness(
        normalized_package_path=package,
        plan=plan,
    )

    assert result.scanned_occurrence_count == 5
    assert result.target_occurrence_count == 5
    assert result.observed_issuer_count == 1
    assert result.observed_endpoint_count == 2
    assert result.ready_endpoint_count == 1
    assert result.blocked_endpoint_count == 1
    assert result.positive_evidence_denominator_only is True
    assert result.absent_issuer_endpoints_measured is False
    assert result.ttm_derivation_count == 0
    assert result.security_projection_count == 0
    assert verification.verification_status == "byte_identical"
    assert verification.primary_result_fingerprint == result.logical_fingerprint


def test_bounded_census_stops_on_bound_source_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package, manifest = _package(tmp_path)
    plan = build_sec_cash_quality_source_readiness_plan_v1(manifest)
    drifted = manifest.model_copy(update={"content_fingerprint": "f" * 64})
    source = SecCompanyfactsNormalizedSourceResult(
        package_path=package,
        manifest=drifted,
    )
    monkeypatch.setattr(
        "tip_api.services.quant_research_sec_cash_quality_source_readiness_census."
        "read_sec_companyfacts_normalized_source",
        _filtered_reader(package, source),
    )

    with pytest.raises(
        SecCashQualitySourceReadinessCensusError,
        match="source binding differs",
    ):
        run_sec_cash_quality_source_readiness_census(
            normalized_package_path=package,
            plan=plan,
        )
