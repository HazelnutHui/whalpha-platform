from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.security_classification.v1 import (
    ClassificationStatus, EvidenceGrade, ProviderInstrumentSecurityEvidenceV1,
    ProviderSecurityTypeCatalogV1, SecurityForm, UniverseDisposition,
)
from tip_api.persistence.parquet.security_evidence import ParquetSecurityEvidenceRepository
from tip_api.persistence.security_evidence import SecurityEvidenceConflictError, SecurityEvidenceCorruptionError

NOW=datetime(2026,8,15,tzinfo=UTC); AS_OF=date(2026,8,14); PROVIDER="massive_stocks_basic"


def catalog(description="Common Stock"):
    return (ProviderSecurityTypeCatalogV1(provider=PROVIDER,provider_type_code="CS",provider_type_description=description,provider_asset_class="stocks",provider_locale="us",observed_at=NOW,source_endpoint="/v3/reference/tickers/types",evidence_fingerprint="a"*64),)


def evidence(ticker="TEST"):
    return (ProviderInstrumentSecurityEvidenceV1(as_of_date=AS_OF,instrument_id=UUID("00000000-0000-4000-8000-000000000001"),provider=PROVIDER,provider_ticker=ticker,provider_type_code="CS",provider_type_description="Common Stock",primary_exchange="XNYS",security_form_evidence=SecurityForm.COMMON_SHARE,evidence_source="/v3/reference/tickers",evidence_grade=EvidenceGrade.PROVIDER_EXPLICIT,classification_status=ClassificationStatus.UNKNOWN,universe_disposition=UniverseDisposition.QUARANTINE,decision_flags=("stable_identifier_join",),review_flags=("issuer_structure_unresolved",),observed_at=NOW,ingested_at=NOW),)


def test_parquet_round_trip_atomic_publish_and_identical_rerun(tmp_path: Path) -> None:
    repo=ParquetSecurityEvidenceRepository(tmp_path,created_at=NOW)
    first=repo.publish_catalog(catalog(),observed_date=NOW.date(),provider_id=PROVIDER)
    second=repo.publish_catalog(catalog(),observed_date=NOW.date(),provider_id=PROVIDER)
    ev=repo.publish_instrument_evidence(evidence(),as_of_date=AS_OF,provider_id=PROVIDER,catalog_content_sha256=first.content_sha256,quality_summary={"raw_record_count":1})
    assert first.status=="published" and second.status=="already_present" and ev.record_count==1
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
