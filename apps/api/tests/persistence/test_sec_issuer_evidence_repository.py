from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.security_classification.v1 import (
    IssuerStructure,
    ListingScope,
    SecEvidenceGrade,
    SecIssuerStructureEvidenceV1,
    SecurityForm,
    UniverseDisposition,
)
from tip_api.persistence.parquet.sec_issuer_evidence import (
    ParquetSecIssuerEvidenceRepository,
    read_completed_sec_issuer_evidence,
)
from tip_api.persistence.sec_issuer_evidence import (
    SecIssuerEvidenceConflictError,
    SecIssuerEvidenceCorruptionError,
    SecIssuerEvidencePersistenceError,
)

NOW = datetime(2026, 8, 15, tzinfo=UTC)
AS_OF = date(2026, 8, 14)


def record(reason="authoritative_fixture"):
    return SecIssuerStructureEvidenceV1(
        as_of_date=AS_OF,
        instrument_id=UUID("00000000-0000-4000-8000-000000000001"),
        cik="1",
        asserted_security_form=SecurityForm.COMMON_SHARE,
        asserted_issuer_structure=IssuerStructure.OPERATING_COMPANY,
        asserted_listing_scope=ListingScope.US_DOMESTIC_PRIMARY,
        evidence_grade=SecEvidenceGrade.AUTHORITATIVE_EXPLICIT,
        universe_disposition=UniverseDisposition.CANDIDATE_CORE,
        source_observation_ids=("a" * 64,),
        decision_reasons=(reason,),
        quality_status=QualityStatus.VALID,
        quality_flags=(),
        source_observed_at=NOW,
    )


def test_parquet_round_trip_atomic_publish_and_idempotency(tmp_path: Path) -> None:
    repo = ParquetSecIssuerEvidenceRepository(tmp_path, NOW)
    first = repo.publish((record(),), source_datasets=("inline_xbrl_cover",))
    second = repo.publish((record(),), source_datasets=("inline_xbrl_cover",))
    assert first.status == "published" and second.status == "already_present"
    assert read_completed_sec_issuer_evidence(first.partition_path) == (record(),)
    assert not list(first.partition_path.parent.glob("*.staging.*"))


def test_conflicting_rerun_is_rejected(tmp_path: Path) -> None:
    repo = ParquetSecIssuerEvidenceRepository(tmp_path, NOW)
    repo.publish((record(),), source_datasets=("fixture",))
    with pytest.raises(SecIssuerEvidenceConflictError):
        repo.publish((record("changed"),), source_datasets=("fixture",))


def test_incomplete_and_corrupt_partition_are_rejected(tmp_path: Path) -> None:
    repo = ParquetSecIssuerEvidenceRepository(tmp_path, NOW)
    result = repo.publish((record(),), source_datasets=("fixture",))
    (result.partition_path / "manifest.json").unlink()
    with pytest.raises(SecIssuerEvidenceCorruptionError):
        repo.publish((record(),), source_datasets=("fixture",))


def test_symlink_root_is_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(SecIssuerEvidencePersistenceError):
        ParquetSecIssuerEvidenceRepository(link, NOW).publish((record(),), source_datasets=("fixture",))


def test_business_key_conflict_hard_fails(tmp_path: Path) -> None:
    with pytest.raises(SecIssuerEvidenceConflictError):
        ParquetSecIssuerEvidenceRepository(tmp_path, NOW).publish(
            (record(), record("conflict")), source_datasets=("fixture",)
        )
