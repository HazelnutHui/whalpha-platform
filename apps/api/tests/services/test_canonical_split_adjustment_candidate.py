from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    CanonicalSplitActionQuarantineImpactV1,
    CanonicalSplitActionV1,
    CorporateActionRecordStatus,
    CorporateActionType,
    HistoricalCoverageArtifactEvidenceV1,
    HistoricalCoverageFileReferenceV1,
    HistoricalDatasetFamily,
    build_historical_dataset_coverage_evidence,
)
from tip_api.services import canonical_split_adjustment_candidate as module
from tip_api.services.canonical_split_adjustment_candidate import (
    CanonicalSplitAdjustmentCandidateError,
    build_canonical_split_adjustment_candidate,
    read_canonical_split_adjustment_candidate,
)


SESSIONS = (
    date(2026, 8, 20),
    date(2026, 8, 21),
    date(2026, 8, 22),
)
BASIS = SESSIONS[-1]
SOURCE_AT = datetime(2026, 9, 2, tzinfo=UTC)
EVIDENCE_AT = datetime(2026, 9, 3, tzinfo=UTC)
CALCULATED_AT = datetime(2026, 9, 4, tzinfo=UTC)
AAA = UUID("11111111-1111-4111-8111-111111111111")
BBB = UUID("22222222-2222-4222-8222-222222222222")
CCC = UUID("33333333-3333-4333-8333-333333333333")


def _action(
    instrument_id: UUID,
    action_id: str,
    *,
    group_size: int = 1,
) -> CanonicalSplitActionV1:
    quarantined = group_size > 1
    flags = {
        "source_available_time_unavailable",
        "outcome_reconciliation_only",
    }
    if quarantined:
        flags.update(
            {"multiple_same_date_split_actions", "ledger_admission_quarantined"}
        )
    return CanonicalSplitActionV1(
        corporate_action_id=uuid4(),
        instrument_id=instrument_id,
        action_type=CorporateActionType.STOCK_SPLIT,
        effective_date=BASIS,
        split_ratio_from=Decimal("1"),
        split_ratio_to=Decimal("2"),
        source="massive_stocks_basic",
        source_action_id=action_id,
        source_revision=1,
        canonical_revision=1,
        source_action_set_fingerprint=("a" if not quarantined else "b") * 64,
        source_publication_fingerprint="c" * 64,
        event_group_size=group_size,
        record_status=(
            CorporateActionRecordStatus.QUARANTINED
            if quarantined
            else CorporateActionRecordStatus.ACTIVE
        ),
        first_observed_at=SOURCE_AT,
        ingested_at=SOURCE_AT,
        quality_status=(
            QualityStatus.PENDING_REVIEW if quarantined else QualityStatus.VALID
        ),
        quality_flags=tuple(flags),
    )


def _fixture(monkeypatch, tmp_path: Path) -> dict[str, object]:
    root = tmp_path / "data"
    root.mkdir(mode=0o755)
    artifacts = []
    for index, session in enumerate(SESSIONS):
        partition = root / "eod" / session.isoformat()
        partition.mkdir(parents=True)
        parquet_path = partition / "part-00000.parquet"
        pq.write_table(
            pa.table(
                {
                    "instrument_id": [str(AAA), str(BBB), str(CCC)],
                    "session_date": pa.array([session] * 3, type=pa.date32()),
                }
            ),
            parquet_path,
        )
        manifest_path = partition / "manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        artifacts.append(
            HistoricalCoverageArtifactEvidenceV1(
                completion_manifest=HistoricalCoverageFileReferenceV1(
                    path=manifest_path.relative_to(root).as_posix(),
                    physical_sha256=(str(index + 1) * 64)[:64],
                ),
                payload_files=(
                    HistoricalCoverageFileReferenceV1(
                        path=parquet_path.relative_to(root).as_posix(),
                        physical_sha256=(str(index + 4) * 64)[:64],
                    ),
                ),
                first_session=session,
                last_session=session,
                record_count=3,
                logical_fingerprint=(str(index + 7) * 64)[:64],
            )
        )
    evidence = build_historical_dataset_coverage_evidence(
        family=HistoricalDatasetFamily.EOD_PRICE_BAR,
        sessions=SESSIONS,
        artifacts=tuple(artifacts),
        record_count=9,
        quarantined_record_count=0,
        created_at=EVIDENCE_AT,
    )
    impact = CanonicalSplitActionQuarantineImpactV1(
        instrument_id=CCC,
        provider_tickers=("OLD",),
        effective_dates=(BASIS,),
        source_action_ids=("unresolved",),
        source_action_set_fingerprint="d" * 64,
        source_publication_fingerprint="c" * 64,
    )
    actions = (
        _action(AAA, "clear"),
        _action(BBB, "conflict-a", group_size=2),
        _action(BBB, "conflict-b", group_size=2),
    )
    publication = SimpleNamespace(
        start_date=SESSIONS[0],
        end_date=BASIS,
        created_at=SOURCE_AT,
        logical_fingerprint="e" * 64,
        source_coverage_status="bounded_query_snapshot_only",
        point_in_time_eligibility="outcome_reconciliation_only",
        adjustment_ledger_authorized=False,
        full_corporate_action_coverage_authorized=False,
        possible_unresolved_impacts=(impact,),
        active_action_record_count=1,
        quarantined_action_record_count=2,
        unresolved_source_action_count=1,
    )
    action_root = root / "market-data" / "canonical-action-test"
    action_root.mkdir(parents=True)
    action_source = SimpleNamespace(
        root=action_root,
        publication=publication,
        actions=actions,
        manifest_sha256="f" * 64,
    )
    evidence_path = root / "market-data" / "evidence" / "manifest.json"
    evidence_path.parent.mkdir(parents=True)
    eod_source = SimpleNamespace(
        evidence=evidence,
        evidence_path=evidence_path,
        physical_sha256="9" * 64,
    )

    class FakeRepository:
        def __init__(self, _root: Path) -> None:
            pass

        def read_dataset_evidence(self, _path: Path):
            return eod_source

    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", root)
    monkeypatch.setattr(
        module,
        "read_canonical_split_action_publication",
        lambda **_kwargs: action_source,
    )
    monkeypatch.setattr(module, "ParquetHistoricalCoverageRepository", FakeRepository)
    return {
        "data_root": root,
        "canonical_action_publication_root": action_root,
        "eod_evidence_path": evidence_path,
        "output_root": tmp_path / "candidate",
        "source_revision": "8" * 40,
        "calculated_at": CALCULATED_AT,
    }


def test_builds_sparse_clear_and_quarantine_projection(
    monkeypatch, tmp_path: Path
) -> None:
    inputs = _fixture(monkeypatch, tmp_path)

    result = build_canonical_split_adjustment_candidate(**inputs)  # type: ignore[arg-type]

    publication = result.publication.publication
    records = result.publication.records
    assert result.status == "published"
    assert publication.selected_instrument_count == 3
    assert publication.selected_eod_row_count == 9
    assert publication.record_count == 6
    assert publication.clear_record_count == 2
    assert publication.quarantined_record_count == 4
    assert publication.absent_row_neutrality_authorized is False
    clear = tuple(item for item in records if item.instrument_id == AAA)
    assert len(clear) == 2
    assert all(item.split_price_multiplier_to_basis == Decimal("0.5") for item in clear)
    assert all(item.split_volume_multiplier_to_basis == Decimal("2") for item in clear)
    assert all(item.total_return_multiplier_to_basis is None for item in records)
    assert all(item.source_session != BASIS for item in records)
    assert read_canonical_split_adjustment_candidate(
        output_root=result.output_root
    ).publication.publication == publication


def test_exact_candidate_rerun_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    inputs = _fixture(monkeypatch, tmp_path)
    first = build_canonical_split_adjustment_candidate(**inputs)  # type: ignore[arg-type]
    second = build_canonical_split_adjustment_candidate(**inputs)  # type: ignore[arg-type]

    assert first.publication.publication == second.publication.publication
    assert second.status == "already_present"


def test_source_range_mismatch_fails_before_output(monkeypatch, tmp_path: Path) -> None:
    inputs = _fixture(monkeypatch, tmp_path)
    source = module.read_canonical_split_action_publication()
    source.publication.end_date = date(2026, 8, 21)

    with pytest.raises(CanonicalSplitAdjustmentCandidateError, match="scope"):
        build_canonical_split_adjustment_candidate(**inputs)  # type: ignore[arg-type]
    assert not Path(inputs["output_root"]).exists()  # type: ignore[arg-type]


def test_candidate_tamper_fails_formal_reread(monkeypatch, tmp_path: Path) -> None:
    inputs = _fixture(monkeypatch, tmp_path)
    result = build_canonical_split_adjustment_candidate(**inputs)  # type: ignore[arg-type]
    parquet = result.output_root / "part-00000.parquet"
    parquet.chmod(0o600)
    parquet.write_bytes(parquet.read_bytes() + b"tamper")
    parquet.chmod(0o400)

    with pytest.raises(CanonicalSplitAdjustmentCandidateError):
        read_canonical_split_adjustment_candidate(output_root=result.output_root)
