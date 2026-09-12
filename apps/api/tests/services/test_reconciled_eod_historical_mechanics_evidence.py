from __future__ import annotations

from pathlib import Path

import pytest

from tip_api.contracts.market_data.v1 import (
    HistoricalDatasetFamily,
    build_historical_dataset_coverage_evidence,
)
from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodSourceProvenance,
    reconciled_eod_fingerprint,
)
from tip_api.persistence.historical_research import HistoricalResearchCorruptionError
from tip_api.persistence.parquet import reconciled_eod_edition as edition_module
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.manifest import content_fingerprint
from tip_api.persistence.parquet.historical_coverage import (
    ParquetHistoricalCoverageRepository,
)
from tip_api.persistence.parquet.reconciled_eod_edition import (
    ParquetReconciledEodEditionCandidateRepository,
    validate_reconciled_eod_edition,
)
from tip_api.services.reconciled_eod_edition import (
    ReconciledEodSessionCandidate,
    compare_reconciled_eod_records,
)
from tip_api.services.reconciled_eod_historical_mechanics_evidence import (
    ReconciledEodHistoricalMechanicsEvidenceError,
    _build_reconciled_eod_evidence,
    assess_reconciled_eod_historical_mechanics_evidence,
)
from tests.support.eod_read_dataset import CREATED_AT, publish_completed_eod_dataset


EDITION_ID = "coverage-evidence-test"
REVISION = "a" * 40


def _inventory(root: Path) -> tuple[tuple[str, int | None], ...]:
    return tuple(
        sorted(
            (
                path.relative_to(root).as_posix(),
                path.stat().st_size if path.is_file() else None,
            )
            for path in root.rglob("*")
        )
    )


def _publish_edition(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    wrong_identity: bool = False,
):
    fixture = publish_completed_eod_dataset(root)
    (root / "market-data").chmod(0o700)
    monkeypatch.setattr(edition_module, "MASSIVE_PROVIDER_ID", "massive")
    records = CanonicalEodReadRepository(root).read_canonical_records(
        fixture.session_date
    )
    diff = compare_reconciled_eod_records(
        base_records=records,
        rebuilt_records=records,
        expected_added_instrument_ids=frozenset(),
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
    )
    candidate = ReconciledEodSessionCandidate(
        session_date=fixture.session_date,
        rebuilt_records=records,
        diff=diff,
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
        source_observed_at=CREATED_AT,
        source_package_manifest_sha256="1" * 64,
        source_package_content_sha256="2" * 64,
        identity_snapshot_fingerprint=(
            "9" * 64 if wrong_identity else fixture.snapshot_content_sha256
        ),
        identity_source_fingerprint="4" * 64,
        base_eod_fingerprint=content_fingerprint(records),
        rebuilt_eod_fingerprint=content_fingerprint(records),
        quality_summary_fingerprint=reconciled_eod_fingerprint(("valid",)),
        quality_warnings=(),
    )
    repository = ParquetReconciledEodEditionCandidateRepository(
        root=root,
        edition_id=EDITION_ID,
        implementation_revision=REVISION,
        created_at=CREATED_AT,
    )
    repository.publish_session(candidate)
    return repository.publish_interval_manifest(
        session_dates=(fixture.session_date,),
        evaluation_first_session=fixture.session_date,
        evaluation_last_session=fixture.session_date,
    )


def test_exact_edition_and_identity_become_unpublished_family_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    edition = _publish_edition(tmp_path, monkeypatch)
    before = _inventory(tmp_path)

    first = assess_reconciled_eod_historical_mechanics_evidence(
        data_root=tmp_path,
        edition_id=EDITION_ID,
        expected_interval_manifest_fingerprint=(
            edition.manifest.logical_fingerprint
        ),
    )
    second = assess_reconciled_eod_historical_mechanics_evidence(
        data_root=tmp_path,
        edition_id=EDITION_ID,
        expected_interval_manifest_fingerprint=(
            edition.manifest.logical_fingerprint
        ),
    )

    assert first == second
    assert first.status == "price_identity_mechanics_only"
    assert first.observed_session_count == 1
    assert [item.family for item in first.families] == [
        "eod_price_bar",
        "point_in_time_identity",
    ]
    assert first.families[0].artifact_count == 1
    assert first.families[0].record_count == 3
    assert first.families[1].artifact_count == 1
    assert first.families[1].record_count == 3
    assert all(
        item.validation_status == "validated_not_published"
        and item.publication_exists is False
        for item in first.families
    )
    assert first.evidence_publication_performed is False
    assert first.historical_coverage_publication_performed is False
    assert first.external_request_count == 0
    assert first.production_write_count == 0
    assert _inventory(tmp_path) == before


def test_expected_interval_fingerprint_is_mandatory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    edition = _publish_edition(tmp_path, monkeypatch)

    with pytest.raises(
        ReconciledEodHistoricalMechanicsEvidenceError,
        match="differs from the expected value",
    ):
        assess_reconciled_eod_historical_mechanics_evidence(
            data_root=tmp_path,
            edition_id=EDITION_ID,
            expected_interval_manifest_fingerprint="0" * 64,
        )

    assert edition.manifest.logical_fingerprint != "0" * 64


def test_identity_snapshot_must_match_the_edition_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    edition = _publish_edition(tmp_path, monkeypatch, wrong_identity=True)

    with pytest.raises(
        ReconciledEodHistoricalMechanicsEvidenceError,
        match="Identity snapshot binding differs",
    ):
        assess_reconciled_eod_historical_mechanics_evidence(
            data_root=tmp_path,
            edition_id=EDITION_ID,
            expected_interval_manifest_fingerprint=(
                edition.manifest.logical_fingerprint
            ),
        )


def test_reconciled_eod_evidence_cannot_omit_a_session_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = _publish_edition(tmp_path, monkeypatch)
    edition = validate_reconciled_eod_edition(
        root=tmp_path,
        edition_id=EDITION_ID,
    )
    evidence = _build_reconciled_eod_evidence(tmp_path, edition)
    artifact = evidence.artifacts[0].model_copy(
        update={
            "payload_files": tuple(
                item
                for item in evidence.artifacts[0].payload_files
                if not item.path.endswith("/manifest.json")
            )
        }
    )
    incomplete = build_historical_dataset_coverage_evidence(
        family=HistoricalDatasetFamily.EOD_PRICE_BAR,
        sessions=evidence.sessions,
        artifacts=(artifact,),
        record_count=evidence.record_count,
        quarantined_record_count=0,
        created_at=evidence.created_at,
    )

    with pytest.raises(
        HistoricalResearchCorruptionError,
        match="session payload is not evidence-bound",
    ):
        ParquetHistoricalCoverageRepository(tmp_path).validate_dataset_evidence(
            incomplete
        )

    assert completed.manifest.logical_fingerprint == (
        edition.manifest.logical_fingerprint
    )
