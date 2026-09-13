from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.providers.sec.companyfacts_normalized_source import (
    CONCEPT_ARROW_SCHEMA,
    CONTRACT_VERSION as NORMALIZED_CONTRACT_VERSION,
    ENTITY_ARROW_SCHEMA,
    OCCURRENCE_ARROW_SCHEMA,
    NormalizedArtifactV1,
    SecCompanyfactsNormalizedSourceManifestV1,
    WorkerMemberPartitionV1,
)
from tip_api.providers.sec.companyfacts_semantic_census import (
    CONTRACT_VERSION,
    _LinkPopulation,
    _census_worker,
    _combine_results,
    _fingerprint,
)


REVISION = "a" * 40
SHA = "b" * 64
NOW = datetime(2026, 9, 13, 12, tzinfo=UTC)
CIK = "0000000001"


def _row(
    ordinal: int,
    *,
    end: date | None,
    accession: str,
    value: str | None,
    available: datetime | None,
    filed: date = date(2024, 12, 31),
    normalization_status: str = "admitted",
    clock_status: str = "admitted",
) -> dict[str, object]:
    member = f"CIK{CIK}.json"
    namespace = "us-gaap"
    concept = "Revenue"
    unit = "USD"
    key = (member, namespace, concept, unit, ordinal)
    reasons = [] if normalization_status == "admitted" else ["missing_filing_clock"]
    return {
        "contract_version": NORMALIZED_CONTRACT_VERSION,
        "source_occurrence_id": _fingerprint(key),
        "raw_fact_fingerprint": _fingerprint(("raw", ordinal)),
        "companyfacts_cik": CIK,
        "source_member_name": member,
        "concept_key": _fingerprint((CIK, namespace, concept)),
        "namespace": namespace,
        "concept_name": concept,
        "unit": unit,
        "unit_occurrence_ordinal": ordinal,
        "start_raw": None,
        "start_date": None,
        "end_raw": end.isoformat() if end else None,
        "end_date": end,
        "value_kind": "integer" if value is not None else "invalid",
        "value_text": value,
        "accession_number": accession,
        "fiscal_year_raw": "2024",
        "fiscal_year": 2024,
        "fiscal_period": "FY",
        "form": "10-K",
        "filed_date": filed,
        "frame": None,
        "filing_clock_admission_status": clock_status,
        "source_available_at_utc": available,
        "signal_eligible_session": date(2025, 1, 2) if available else None,
        "clock_reason_codes": reasons,
        "normalization_status": normalization_status,
        "normalization_reason_codes": reasons,
        "instrument_resolution_status": "unresolved",
        "instrument_id": None,
    }


def _artifact(root: Path) -> NormalizedArtifactV1:
    rows = [
        _row(0, end=date(2024, 12, 31), accession="0000000001-24-000001", value="10", available=NOW),
        _row(1, end=date(2024, 12, 31), accession="0000000001-24-000001", value="10", available=NOW),
        _row(2, end=date(2024, 12, 31), accession="0000000001-24-000002", value="12", available=NOW.replace(day=14)),
        _row(3, end=date(2024, 9, 30), accession="0000000001-24-000003", value="5", available=NOW),
        _row(4, end=date(2024, 9, 30), accession="0000000001-24-000003", value="6", available=NOW),
        _row(5, end=date(2024, 6, 30), accession="0000000001-24-000004", value="7", available=NOW),
        _row(6, end=date(2024, 6, 30), accession="0000000001-24-000005", value="8", available=NOW),
        _row(
            7,
            end=None,
            accession="0000000001-24-000006",
            value=None,
            available=None,
            normalization_status="quarantined",
            clock_status="quarantined",
        ),
    ]
    worker = root / "worker=00"
    worker.mkdir()
    path = worker / "occurrences-filed-year=2024.parquet"
    table = pa.Table.from_pylist(rows, schema=OCCURRENCE_ARROW_SCHEMA)
    pq.write_table(table, path)
    return NormalizedArtifactV1(
        artifact_kind="occurrence",
        worker_index=0,
        filed_year=2024,
        relative_path="worker=00/occurrences-filed-year=2024.parquet",
        row_count=len(rows),
        byte_size=path.stat().st_size,
        physical_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        logical_fingerprint=SHA,
        schema_fingerprint=hashlib.sha256(
            OCCURRENCE_ARROW_SCHEMA.serialize().to_pybytes()
        ).hexdigest(),
    )


def _year_artifact(
    root: Path,
    year: int,
    rows: list[dict[str, object]],
) -> NormalizedArtifactV1:
    worker = root / "worker=00"
    worker.mkdir(exist_ok=True)
    relative = f"worker=00/occurrences-filed-year={year}.parquet"
    path = root / relative
    table = pa.Table.from_pylist(rows, schema=OCCURRENCE_ARROW_SCHEMA)
    pq.write_table(table, path)
    return NormalizedArtifactV1(
        artifact_kind="occurrence",
        worker_index=0,
        filed_year=year,
        relative_path=relative,
        row_count=len(rows),
        byte_size=path.stat().st_size,
        physical_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        logical_fingerprint=SHA,
        schema_fingerprint=hashlib.sha256(
            OCCURRENCE_ARROW_SCHEMA.serialize().to_pybytes()
        ).hexdigest(),
    )


def _source_manifest(occurrence: NormalizedArtifactV1) -> SecCompanyfactsNormalizedSourceManifestV1:
    entity = NormalizedArtifactV1(
        artifact_kind="entity",
        worker_index=0,
        relative_path="worker=00/entities.parquet",
        row_count=1,
        byte_size=1,
        physical_sha256=SHA,
        logical_fingerprint=SHA,
        schema_fingerprint=hashlib.sha256(ENTITY_ARROW_SCHEMA.serialize().to_pybytes()).hexdigest(),
    )
    concept = NormalizedArtifactV1(
        artifact_kind="concept",
        worker_index=0,
        relative_path="worker=00/concepts.parquet",
        row_count=1,
        byte_size=1,
        physical_sha256=SHA,
        logical_fingerprint=SHA,
        schema_fingerprint=hashlib.sha256(CONCEPT_ARROW_SCHEMA.serialize().to_pybytes()).hexdigest(),
    )
    artifacts = tuple(sorted((entity, concept, occurrence), key=lambda item: item.relative_path))
    values = {
        "contract_version": NORMALIZED_CONTRACT_VERSION,
        "completion_status": "completed",
        "provider_id": "sec_edgar",
        "implementation_revision": REVISION,
        "built_at": NOW,
        "range_start": date(2024, 1, 1),
        "range_end": date(2024, 12, 31),
        "companyfacts_snapshot_date": date(2026, 9, 10),
        "companyfacts_source_fingerprint": SHA,
        "companyfacts_source_manifest_sha256": SHA,
        "companyfacts_payload_census_fingerprint": SHA,
        "companyfacts_payload_census_sha256": SHA,
        "filing_clock_manifest_sha256": SHA,
        "filing_clock_manifest_fingerprint": SHA,
        "filing_clock_content_fingerprint": SHA,
        "worker_count": 1,
        "worker_partitions": (
            WorkerMemberPartitionV1(
                worker_index=0,
                member_count=1,
                member_name_fingerprint=SHA,
            ),
        ),
        "artifacts": artifacts,
        "entity_count": 1,
        "concept_count": 1,
        "occurrence_count": 8,
        "clock_admitted_occurrence_count": 7,
        "clock_quarantined_occurrence_count": 1,
        "normalization_admitted_occurrence_count": 7,
        "normalization_quarantined_occurrence_count": 1,
        "invalid_normalized_field_occurrence_count": 0,
        "value_kind_counts": (("integer", 7), ("invalid", 1)),
        "namespace_occurrence_counts": (("us-gaap", 8),),
        "form_occurrence_counts": (("10-K", 8),),
        "filed_year_occurrence_counts": (("2024", 8),),
        "entity_schema_fingerprint": entity.schema_fingerprint,
        "concept_schema_fingerprint": concept.schema_fingerprint,
        "occurrence_schema_fingerprint": occurrence.schema_fingerprint,
        "content_fingerprint": _fingerprint(
            tuple((item.relative_path, item.logical_fingerprint) for item in artifacts)
        ),
        "stable_instrument_resolution_count": 0,
        "canonical_data_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    return SecCompanyfactsNormalizedSourceManifestV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def test_worker_counts_duplicates_conflicts_and_clean_revisions(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    result = _census_worker((str(tmp_path), 0, (artifact,), frozenset({CIK})))

    assert result.occurrence_count == 8
    assert result.distinct_filer_count == 1
    assert result.admitted_fact_filer_count == 1
    assert result.observed_concept_key_count == 1
    assert result.semantic_key_count == 4
    assert result.accession_semantic_group_count == 6
    assert result.exact_duplicate_group_count == 1
    assert result.exact_duplicate_redundant_occurrence_count == 1
    assert result.within_accession_conflict_group_count == 1
    assert result.within_accession_conflict_occurrence_count == 2
    assert result.same_availability_conflict_group_count == 1
    assert result.revision_eligible_semantic_key_count == 1
    assert result.revision_quarantined_semantic_key_count == 3
    assert result.semantic_key_with_later_accession_count == 1
    assert result.later_accession_revision_count == 1
    assert result.later_revision_state_count == 1
    assert result.later_revision_value_change_count == 1
    assert result.linked_cik_with_facts_count == 1
    assert Counter(item.conflict_class for item in result.conflict_samples) == {
        "within_accession_value_conflict": 1,
        "same_availability_value_conflict": 1,
    }


def test_combined_census_binds_denominators_and_zero_authority(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    worker = _census_worker((str(tmp_path), 0, (artifact,), frozenset({CIK, "0000000002"})))
    source = _source_manifest(artifact)
    link = _LinkPopulation(
        manifest_sha256=SHA,
        logical_fingerprint=SHA,
        session=date(2023, 11, 9),
        point_in_time_eligibility="eligible_at_source_observed_at",
        source_observed_at=NOW,
        common_stock_instrument_count=3,
        admitted_common_stock_instrument_count=2,
        quarantined_common_stock_instrument_count=1,
        ciks=frozenset({CIK, "0000000002"}),
    )

    census = _combine_results(
        results=(worker,),
        source=source,
        source_manifest_sha256=SHA,
        link=link,
        process_count=1,
        implementation_revision=REVISION,
        evaluated_at=NOW,
    )

    assert census.contract_version == CONTRACT_VERSION
    assert census.link_cik_with_source_facts_count == 1
    assert census.link_cik_without_source_facts_count == 1
    assert census.period_shape_occurrence_counts == (
        ("instant", 7),
        ("invalid_or_incomplete", 1),
    )
    assert census.top_standard_concepts[0].concept_name == "Revenue"
    assert census.top_standard_concepts[0].distinct_filer_count == 1
    assert census.top_standard_concepts[0].linked_common_stock_filer_count == 1
    assert census.registered_feature_count == 0
    assert census.issuer_projection_authorized is False
    assert census.research_performance_authorized is False


def test_worker_merges_filed_year_streams_by_original_occurrence_order(tmp_path: Path) -> None:
    first = _row(
        0,
        end=date(2023, 12, 31),
        accession="0000000001-23-000001",
        value="10",
        available=NOW,
        filed=date(2023, 12, 31),
    )
    second = _row(
        1,
        end=date(2023, 12, 31),
        accession="0000000001-24-000001",
        value="11",
        available=NOW.replace(day=14),
    )
    third = _row(
        2,
        end=date(2023, 12, 31),
        accession="0000000001-23-000002",
        value="10",
        available=NOW.replace(day=15),
        filed=date(2023, 12, 31),
    )
    artifacts = (
        _year_artifact(tmp_path, 2023, [first, third]),
        _year_artifact(tmp_path, 2024, [second]),
    )

    result = _census_worker((str(tmp_path), 0, artifacts, frozenset({CIK})))

    assert result.occurrence_count == 3
    assert result.semantic_key_count == 1
    assert result.semantic_key_with_later_accession_count == 1
    assert result.later_accession_revision_count == 2
    assert result.later_revision_state_count == 2
    assert result.later_revision_value_change_count == 2
