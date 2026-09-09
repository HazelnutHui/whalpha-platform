from __future__ import annotations

from dataclasses import replace
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
from tip_api.services import canonical_split_coverage_diagnostic as module
from tip_api.services.canonical_split_coverage_diagnostic import (
    CanonicalSplitCoverageDiagnosticError,
    diagnose_canonical_split_coverage,
    verify_canonical_split_coverage_diagnostic,
)


SESSIONS = (
    date(2026, 8, 20),
    date(2026, 8, 21),
    date(2026, 8, 24),
)
SOURCE_AT = datetime(2026, 9, 2, tzinfo=UTC)
EVIDENCE_AT = datetime(2026, 9, 3, tzinfo=UTC)
CALCULATED_AT = datetime(2026, 9, 4, tzinfo=UTC)
AAA = UUID("11111111-1111-4111-8111-111111111111")
BBB = UUID("22222222-2222-4222-8222-222222222222")
CCC = UUID("33333333-3333-4333-8333-333333333333")
DDD = UUID("44444444-4444-4444-8444-444444444444")
EEE = UUID("55555555-5555-4555-8555-555555555555")
FFF = UUID("66666666-6666-4666-8666-666666666666")


def _action(
    instrument_id: UUID,
    effective_date: date,
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
        effective_date=effective_date,
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


def _fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, object]:
    root = tmp_path / "data"
    root.mkdir(mode=0o755)
    session_rows = {
        SESSIONS[0]: (
            (AAA, "100", "100"),
            (BBB, "100", "100"),
            (CCC, "100", "100"),
            (DDD, "100", "100"),
            (FFF, "100", "100"),
        ),
        SESSIONS[1]: (
            (AAA, "50", "50"),
            (BBB, "250", "250"),
            (CCC, "50", "50"),
            (DDD, "100", "100"),
            (FFF, "100", "100"),
        ),
        SESSIONS[2]: (
            (AAA, "50", "50"),
            (BBB, "250", "250"),
            (CCC, "50", "50"),
            (DDD, "40", "40"),
            (EEE, "50", "50"),
        ),
    }
    artifacts = []
    total_records = 0
    for index, session in enumerate(SESSIONS):
        rows = session_rows[session]
        total_records += len(rows)
        partition = root / "eod" / session.isoformat()
        partition.mkdir(parents=True)
        parquet_path = partition / "part-00000.parquet"
        price_type = pa.decimal128(38, 10)
        pq.write_table(
            pa.table(
                {
                    "instrument_id": [str(item[0]) for item in rows],
                    "session_date": pa.array([session] * len(rows), type=pa.date32()),
                    "open": pa.array(
                        [Decimal(item[1]) for item in rows], type=price_type
                    ),
                    "close": pa.array(
                        [Decimal(item[2]) for item in rows], type=price_type
                    ),
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
                record_count=len(rows),
                logical_fingerprint=(str(index + 7) * 64)[:64],
            )
        )
    evidence = build_historical_dataset_coverage_evidence(
        family=HistoricalDatasetFamily.EOD_PRICE_BAR,
        sessions=SESSIONS,
        artifacts=tuple(artifacts),
        record_count=total_records,
        quarantined_record_count=0,
        created_at=EVIDENCE_AT,
    )
    impact = CanonicalSplitActionQuarantineImpactV1(
        instrument_id=DDD,
        provider_tickers=("OLD",),
        effective_dates=(SESSIONS[2],),
        source_action_ids=("unresolved",),
        source_action_set_fingerprint="d" * 64,
        source_publication_fingerprint="c" * 64,
    )
    actions = (
        _action(AAA, SESSIONS[1], "clear"),
        _action(CCC, SESSIONS[1], "conflict-a", group_size=2),
        _action(CCC, SESSIONS[1], "conflict-b", group_size=2),
        _action(EEE, SESSIONS[2], "no-prior"),
        _action(FFF, SESSIONS[2], "no-current"),
    )
    publication = SimpleNamespace(
        start_date=SESSIONS[0],
        end_date=SESSIONS[-1],
        created_at=SOURCE_AT,
        logical_fingerprint="e" * 64,
        source_coverage_status="bounded_query_snapshot_only",
        point_in_time_eligibility="outcome_reconciliation_only",
        full_corporate_action_coverage_authorized=False,
        possible_unresolved_impacts=(impact,),
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
        "source_revision": "8" * 40,
        "calculated_at": CALCULATED_AT,
    }


def test_diagnostic_classifies_known_events_and_unexplained_gaps(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inputs = _fixture(monkeypatch, tmp_path)

    report = diagnose_canonical_split_coverage(**inputs)  # type: ignore[arg-type]

    assert report.source_session_count == 3
    assert report.source_eod_record_count == 15
    assert report.adjacent_transition_count == 9
    assert report.known_event_group_count == 5
    assert report.known_event_comparable_count == 3
    assert report.known_event_current_bar_missing_count == 1
    assert report.known_event_adjacent_transition_missing_count == 1
    assert report.active_split_residual_bounded_count == 1
    assert report.active_split_residual_extreme_count == 0
    assert report.canonical_action_quarantined_count == 1
    assert report.unresolved_impact_quarantined_count == 1
    assert report.unexplained_price_discontinuity_count == 1
    assert report.unexplained_price_discontinuity_instrument_count == 1
    assert report.flag_count == 6
    unexplained = next(
        item
        for item in report.flags
        if item.classification == "unexplained_price_discontinuity"
    )
    assert unexplained.instrument_id == str(BBB)
    assert unexplained.raw_open_to_prior_close_ratio == "2.500000000000"
    assert report.external_request_count == 0
    assert report.filesystem_write_count == 0
    assert report.canonical_data_write_count == 0
    assert report.price_inference_promoted_to_action is False
    assert report.absent_row_neutrality_authorized is False
    assert report.full_corporate_action_coverage_authorized is False
    assert report.total_return_adjustment_authorized is False
    assert report.historical_coverage_authorized is False
    assert report.research_performance_authorized is False


def test_report_tampering_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    report = diagnose_canonical_split_coverage(  # type: ignore[arg-type]
        **_fixture(monkeypatch, tmp_path)
    )

    with pytest.raises(CanonicalSplitCoverageDiagnosticError):
        verify_canonical_split_coverage_diagnostic(
            replace(report, absent_row_neutrality_authorized=True)
        )


def test_source_range_mismatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inputs = _fixture(monkeypatch, tmp_path)
    source = module.read_canonical_split_action_publication()
    source.publication.end_date = SESSIONS[1]

    with pytest.raises(CanonicalSplitCoverageDiagnosticError):
        diagnose_canonical_split_coverage(**inputs)  # type: ignore[arg-type]
