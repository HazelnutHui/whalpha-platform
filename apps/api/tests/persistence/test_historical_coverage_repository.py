from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from tip_api.contracts.analytics.v1 import (
    strong_stock_pullback_research_experiment_v1,
)
from tip_api.contracts.market_data.v1 import (
    HistoricalCoverageArtifactEvidenceV1,
    HistoricalCoverageFileReferenceV1,
    HistoricalCoverageManifestV1,
    HistoricalDatasetCoverageReferenceV1,
    HistoricalDatasetFamily,
    HistoricalReadinessStatus,
    RESEARCH_REQUIRED_DATASET_FAMILIES,
    build_historical_dataset_coverage_evidence,
    historical_coverage_manifest_fingerprint,
)
from tip_api.persistence.historical_research import (
    HistoricalResearchConflictError,
    HistoricalResearchCorruptionError,
)
from tip_api.persistence.parquet.historical_coverage import (
    ParquetHistoricalCoverageRepository,
)
from tip_api.read_models.eod import EodSessionDescriptor
from tip_api.services.strategy_research_readiness import (
    StrategyResearchReadinessStatus,
    assess_strategy_research_readiness,
    canonical_eod_identity_evidence,
)


CREATED_AT = datetime(2026, 8, 30, 16, 0, tzinfo=UTC)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sessions(count: int = 252) -> tuple[date, ...]:
    start = date(2025, 1, 2)
    return tuple(start + timedelta(days=index) for index in range(count))


def _source_artifact(
    root: Path,
    family: HistoricalDatasetFamily,
    sessions: tuple[date, ...],
    index: int,
) -> HistoricalCoverageArtifactEvidenceV1:
    directory = root / "source" / family.value
    directory.mkdir(parents=True)
    payload_path = directory / "part-00000.parquet"
    payload_path.write_bytes(f"fixture:{family.value}".encode("utf-8"))
    logical = f"{index:x}" * 64
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "completion_status": "completed",
                "record_count": 1,
                "logical_fingerprint": logical,
                "physical_sha256": _sha(payload_path),
                "parquet_file": payload_path.name,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return HistoricalCoverageArtifactEvidenceV1(
        completion_manifest=HistoricalCoverageFileReferenceV1(
            path=manifest_path.relative_to(root).as_posix(),
            physical_sha256=_sha(manifest_path),
        ),
        payload_files=(
            HistoricalCoverageFileReferenceV1(
                path=payload_path.relative_to(root).as_posix(),
                physical_sha256=_sha(payload_path),
            ),
        ),
        first_session=sessions[0],
        last_session=sessions[-1],
        record_count=1,
        logical_fingerprint=logical,
    )


def _publish_all_evidence(
    root: Path,
    sessions: tuple[date, ...],
) -> tuple[HistoricalDatasetCoverageReferenceV1, ...]:
    repository = ParquetHistoricalCoverageRepository(root)
    references = []
    for index, family in enumerate(
        sorted(RESEARCH_REQUIRED_DATASET_FAMILIES, key=lambda item: item.value),
        start=1,
    ):
        artifact = _source_artifact(root, family, sessions, index)
        evidence = build_historical_dataset_coverage_evidence(
            family=family,
            sessions=sessions,
            artifacts=(artifact,),
            record_count=1,
            quarantined_record_count=0,
            created_at=CREATED_AT,
        )
        published = repository.publish_dataset_evidence(evidence)
        references.append(
            HistoricalDatasetCoverageReferenceV1(
                family=family,
                dataset_path=published.evidence_path.relative_to(root).as_posix(),
                record_count=evidence.record_count,
                first_session=sessions[0],
                last_session=sessions[-1],
                logical_fingerprint=evidence.logical_fingerprint,
                physical_sha256=published.physical_sha256,
                completed=True,
                quarantined_record_count=0,
            )
        )
    return tuple(references)


def _coverage(
    references: tuple[HistoricalDatasetCoverageReferenceV1, ...],
    sessions: tuple[date, ...],
) -> HistoricalCoverageManifestV1:
    payload = {
        "coverage_id": "c" * 64,
        "sessions": sessions,
        "feature_warmup_sessions": 20,
        "maximum_outcome_horizon_sessions": 5,
        "matured_signal_session_count": len(sessions) - 25,
        "datasets": references,
        "readiness_status": HistoricalReadinessStatus.RESEARCH_READY,
        "reason_codes": (),
        "created_at": CREATED_AT,
        "logical_fingerprint": "0" * 64,
    }
    provisional = HistoricalCoverageManifestV1.model_validate(payload)
    return HistoricalCoverageManifestV1.model_validate(
        {
            **payload,
            "logical_fingerprint": historical_coverage_manifest_fingerprint(
                provisional
            ),
        }
    )


def _canonical_descriptors(
    sessions: tuple[date, ...],
) -> tuple[EodSessionDescriptor, ...]:
    return tuple(
        EodSessionDescriptor(
            schema_version="1.0",
            session_date=session,
            record_count=10_000,
            completion_status="completed",
            identity_as_of_date=session,
            available_at=datetime.combine(session, datetime.min.time(), tzinfo=UTC),
            quality_warning_count=0,
        )
        for session in sessions
    )


def test_dataset_evidence_round_trip_is_immutable_and_source_bound(tmp_path) -> None:
    sessions = _sessions(3)
    repository = ParquetHistoricalCoverageRepository(tmp_path)
    artifact = _source_artifact(
        tmp_path,
        HistoricalDatasetFamily.INSTRUMENT_LIFECYCLE,
        sessions,
        1,
    )
    evidence = build_historical_dataset_coverage_evidence(
        family=HistoricalDatasetFamily.INSTRUMENT_LIFECYCLE,
        sessions=sessions,
        artifacts=(artifact,),
        record_count=1,
        quarantined_record_count=0,
        created_at=CREATED_AT,
    )

    published = repository.publish_dataset_evidence(evidence)
    reread = repository.read_dataset_evidence(published.evidence_path)
    again = repository.publish_dataset_evidence(evidence)

    assert published.status == "published"
    assert reread.evidence == evidence
    assert reread.physical_sha256 == published.physical_sha256
    assert again.status == "already_present"


def test_dataset_evidence_rejects_payload_tamper(tmp_path) -> None:
    sessions = _sessions(3)
    repository = ParquetHistoricalCoverageRepository(tmp_path)
    artifact = _source_artifact(
        tmp_path,
        HistoricalDatasetFamily.ADJUSTMENT_LEDGER,
        sessions,
        2,
    )
    evidence = build_historical_dataset_coverage_evidence(
        family=HistoricalDatasetFamily.ADJUSTMENT_LEDGER,
        sessions=sessions,
        artifacts=(artifact,),
        record_count=1,
        quarantined_record_count=0,
        created_at=CREATED_AT,
    )
    published = repository.publish_dataset_evidence(evidence)
    payload = tmp_path / artifact.payload_files[0].path
    payload.write_bytes(payload.read_bytes() + b"tamper")

    with pytest.raises(HistoricalResearchCorruptionError, match="file hash"):
        repository.read_dataset_evidence(published.evidence_path)


def test_research_ready_coverage_formally_rereads_into_review_only_state(
    tmp_path,
) -> None:
    sessions = _sessions()
    references = _publish_all_evidence(tmp_path, sessions)
    coverage = _coverage(references, sessions)
    repository = ParquetHistoricalCoverageRepository(tmp_path)

    published = repository.publish_coverage(coverage)
    reread = repository.read_coverage(coverage.coverage_id)
    assessment = assess_strategy_research_readiness(
        experiment=strong_stock_pullback_research_experiment_v1(),
        canonical_evidence=canonical_eod_identity_evidence(
            _canonical_descriptors(sessions)
        ),
        coverage_manifest=reread.coverage,
    )

    assert published.status == "published"
    assert reread.coverage == coverage
    assert assessment.status is StrategyResearchReadinessStatus.READY_FOR_DEVELOPMENT_REVIEW
    assert assessment.development_authorized is False
    assert assessment.performance_claims_authorized is False


def test_coverage_rejects_wrong_logical_fingerprint(tmp_path) -> None:
    sessions = _sessions()
    references = _publish_all_evidence(tmp_path, sessions)
    coverage = _coverage(references, sessions).model_copy(
        update={"logical_fingerprint": "f" * 64}
    )

    with pytest.raises(HistoricalResearchCorruptionError, match="logical fingerprint"):
        ParquetHistoricalCoverageRepository(tmp_path).publish_coverage(coverage)


def test_coverage_reread_rejects_evidence_manifest_tamper(tmp_path) -> None:
    sessions = _sessions()
    references = _publish_all_evidence(tmp_path, sessions)
    coverage = _coverage(references, sessions)
    repository = ParquetHistoricalCoverageRepository(tmp_path)
    repository.publish_coverage(coverage)
    evidence_path = tmp_path / references[0].dataset_path
    evidence_path.write_bytes(evidence_path.read_bytes() + b" ")

    with pytest.raises(HistoricalResearchCorruptionError, match="reference differs"):
        repository.read_coverage(coverage.coverage_id)


def test_conflicting_coverage_rerun_is_rejected(tmp_path) -> None:
    sessions = _sessions()
    references = _publish_all_evidence(tmp_path, sessions)
    coverage = _coverage(references, sessions)
    repository = ParquetHistoricalCoverageRepository(tmp_path)
    repository.publish_coverage(coverage)
    changed = coverage.model_copy(update={"logical_fingerprint": "e" * 64})

    with pytest.raises((HistoricalResearchConflictError, HistoricalResearchCorruptionError)):
        repository.publish_coverage(changed)


def test_read_missing_root_performs_no_creation(tmp_path) -> None:
    root = tmp_path / "missing"
    with pytest.raises(HistoricalResearchCorruptionError, match="root"):
        ParquetHistoricalCoverageRepository(root).read_coverage("a" * 64)
    assert not root.exists()
