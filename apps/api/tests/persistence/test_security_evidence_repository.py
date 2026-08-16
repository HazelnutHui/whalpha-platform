from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.security_classification.v1 import (
    ClassificationStatus, EvidenceGrade, FailedSecurityEvidenceDiagnosticV1,
    ProviderInstrumentSecurityEvidenceV1, ProviderObservationStatus,
    ProviderSecurityObservationV1, ProviderSecurityTypeCatalogV1,
    SecurityForm, UniverseDisposition,
)
from tip_api.persistence.parquet.security_evidence import (
    ParquetSecurityEvidenceRepository,
    read_completed_security_evidence_snapshot,
    write_failed_diagnostic,
)
from tip_api.persistence.security_evidence import SecurityEvidenceConflictError, SecurityEvidenceCorruptionError

NOW=datetime(2026,8,15,tzinfo=UTC); AS_OF=date(2026,8,14); PROVIDER="massive_stocks_basic"


def catalog(description="Common Stock"):
    return (ProviderSecurityTypeCatalogV1(provider=PROVIDER,provider_type_code="CS",provider_type_description=description,provider_asset_class="stocks",provider_locale="us",observed_at=NOW,source_endpoint="/v3/reference/tickers/types",evidence_fingerprint="a"*64),)


def evidence(ticker="TEST"):
    return (ProviderInstrumentSecurityEvidenceV1(as_of_date=AS_OF,instrument_id=UUID("00000000-0000-4000-8000-000000000001"),provider=PROVIDER,provider_ticker=ticker,provider_type_code="CS",provider_type_description="Common Stock",primary_exchange="XNYS",security_form_evidence=SecurityForm.COMMON_SHARE,evidence_source="/v3/reference/tickers",evidence_grade=EvidenceGrade.PROVIDER_EXPLICIT,classification_status=ClassificationStatus.UNKNOWN,universe_disposition=UniverseDisposition.QUARANTINE,decision_flags=("stable_identifier_join",),review_flags=("issuer_structure_unresolved",),provider_observation_ids=("a"*64,),observed_at=NOW,ingested_at=NOW),)


def observations():
    return (ProviderSecurityObservationV1(provider_observation_id="a"*64,as_of_date=AS_OF,instrument_id=UUID("00000000-0000-4000-8000-000000000001"),provider=PROVIDER,provider_ticker="TEST",provider_type_code="CS",provider_type_description="Common Stock",primary_exchange="XNYS",security_form_evidence=SecurityForm.COMMON_SHARE,evidence_source="/v3/reference/tickers",evidence_grade=EvidenceGrade.PROVIDER_EXPLICIT,observation_status=ProviderObservationStatus.CANONICAL_MAPPED,resolution_method="share_class_figi",reason_codes=("share_class_figi_join",),review_flags=(),observed_at=NOW,ingested_at=NOW),)


def test_parquet_round_trip_atomic_publish_and_identical_rerun(tmp_path: Path) -> None:
    repo=ParquetSecurityEvidenceRepository(tmp_path,created_at=NOW)
    first=repo.publish_catalog(catalog(),observed_date=NOW.date(),provider_id=PROVIDER)
    second=repo.publish_catalog(catalog(),observed_date=NOW.date(),provider_id=PROVIDER)
    ev=repo.publish_instrument_evidence(evidence(),as_of_date=AS_OF,provider_id=PROVIDER,catalog_content_sha256=first.content_sha256,quality_summary={"raw_record_count":1})
    obs=repo.publish_observations(observations(),as_of_date=AS_OF,provider_id=PROVIDER,catalog_content_sha256=first.content_sha256,quality_summary={"raw_record_count":1})
    logical=repo.publish_logical_snapshot(
        as_of_date=AS_OF, observed_date=NOW.date(), provider_id=PROVIDER,
        created_at=NOW, request_count=2, catalog=first, observations=obs, evidence=ev,
    )
    repeated=repo.publish_logical_snapshot(
        as_of_date=AS_OF, observed_date=NOW.date(), provider_id=PROVIDER,
        created_at=NOW, request_count=2, catalog=first, observations=obs, evidence=ev,
    )
    assert first.status=="published" and second.status=="already_present" and ev.record_count==1 and obs.record_count==1
    assert logical.status == "published" and repeated.status == "already_present"
    assert logical.manifest_path.is_file()
    completed = read_completed_security_evidence_snapshot(tmp_path, as_of_date=AS_OF)
    assert len(completed.catalog) == len(completed.observations) == len(completed.evidence) == 1
    assert completed.manifest.logical_content_sha256 == logical.logical_content_sha256
    assert (first.partition_path/"part-00000.parquet").is_file()
    assert not list(first.partition_path.parent.glob("*.staging.*"))


def test_conflicting_rerun_rejected(tmp_path: Path) -> None:
    repo=ParquetSecurityEvidenceRepository(tmp_path,created_at=NOW)
    repo.publish_catalog(catalog(),observed_date=NOW.date(),provider_id=PROVIDER)
    with pytest.raises(SecurityEvidenceConflictError):
        repo.publish_catalog(catalog("Changed"),observed_date=NOW.date(),provider_id=PROVIDER)


def test_incomplete_or_corrupt_existing_partition_rejected(tmp_path: Path) -> None:
    repo=ParquetSecurityEvidenceRepository(tmp_path,created_at=NOW)
    result=repo.publish_catalog(catalog(),observed_date=NOW.date(),provider_id=PROVIDER)
    (result.partition_path/"manifest.json").unlink()
    with pytest.raises(SecurityEvidenceCorruptionError):
        repo.publish_catalog(catalog(),observed_date=NOW.date(),provider_id=PROVIDER)


def test_symlink_root_rejected(tmp_path: Path) -> None:
    real=tmp_path/"real"; real.mkdir(); link=tmp_path/"link"; link.symlink_to(real,target_is_directory=True)
    with pytest.raises(Exception):
        ParquetSecurityEvidenceRepository(link).publish_catalog(catalog(),observed_date=NOW.date(),provider_id=PROVIDER)


def test_failed_diagnostic_is_separate_from_completed_datasets(tmp_path: Path) -> None:
    diagnostic = FailedSecurityEvidenceDiagnosticV1(
        run_id="test-run", as_of_date=AS_OF, provider=PROVIDER,
        endpoint_names=("/v3/reference/tickers",), request_count=1,
        ticker_types_request_count=0, all_tickers_request_count=1,
        statistics_complete=True,
        raw_observation_count=1, status_counts={"ambiguous": 1},
        linkage_numerator=0, linkage_denominator=1, linkage_ratio="0.000000",
        exact_duplicate_count=0, ambiguous_count=1, collision_count=0,
        business_key_conflict_count=0, reconciliation_status="passed",
        failure_reasons=("ambiguous_mapping_nonzero",), conflicting_observations=(), created_at=NOW,
    )
    result = write_failed_diagnostic(tmp_path, diagnostic)
    assert result.diagnostic_path.name == "failed.json"
    assert "operation-diagnostics" in result.diagnostic_path.parts
    assert not (tmp_path / "market-data").exists()
    rendered = result.diagnostic_path.read_text(encoding="utf-8")
    assert "api_key" not in rendered and "Authorization" not in rendered


def test_logical_completion_requires_intact_component_partitions(tmp_path: Path) -> None:
    repo=ParquetSecurityEvidenceRepository(tmp_path,created_at=NOW)
    cat=repo.publish_catalog(catalog(),observed_date=NOW.date(),provider_id=PROVIDER)
    obs=repo.publish_observations(observations(),as_of_date=AS_OF,provider_id=PROVIDER,catalog_content_sha256=cat.content_sha256,quality_summary={"raw_record_count":1})
    ev=repo.publish_instrument_evidence(evidence(),as_of_date=AS_OF,provider_id=PROVIDER,catalog_content_sha256=cat.content_sha256,quality_summary={"raw_record_count":1})
    (obs.partition_path / "part-00000.parquet").write_bytes(b"corrupt")
    with pytest.raises(Exception):
        repo.publish_logical_snapshot(
            as_of_date=AS_OF, observed_date=NOW.date(), provider_id=PROVIDER,
            created_at=NOW, request_count=2, catalog=cat, observations=obs, evidence=ev,
        )
    assert not (tmp_path / "market-data/snapshots/provider-security-evidence" / f"as_of_date={AS_OF}").exists()
