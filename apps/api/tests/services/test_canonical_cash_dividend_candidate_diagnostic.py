from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    CorporateActionRecordStatus,
    CorporateActionSourceObservationV1,
    CorporateActionType,
    HistoricalCoverageArtifactEvidenceV1,
    HistoricalCoverageFileReferenceV1,
    HistoricalDatasetFamily,
    KnowledgeTimeStatus,
    ResolutionStatus,
    build_historical_dataset_coverage_evidence,
)
from tip_api.services import canonical_cash_dividend_candidate_diagnostic as module
from tip_api.services.canonical_cash_dividend_candidate_diagnostic import (
    CanonicalCashDividendCandidateDiagnosticError,
    diagnose_canonical_cash_dividend_candidates,
    verify_canonical_cash_dividend_candidate_diagnostic,
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


def _dividend(
    instrument_id: UUID | None,
    action_id: str,
    *,
    ticker: str,
    amount: str,
    currency: str = "USD",
    effective_date: date = SESSIONS[1],
    pay_date: date = SESSIONS[2],
) -> CorporateActionSourceObservationV1:
    resolved = instrument_id is not None
    return CorporateActionSourceObservationV1(
        provider="massive_stocks_basic",
        source_action_id=action_id,
        source_revision=1,
        record_status=(
            CorporateActionRecordStatus.ACTIVE
            if resolved
            else CorporateActionRecordStatus.QUARANTINED
        ),
        action_type=CorporateActionType.CASH_DIVIDEND,
        provider_ticker=ticker,
        instrument_resolution_status=(
            ResolutionStatus.RESOLVED
            if resolved
            else ResolutionStatus.UNRESOLVED
        ),
        instrument_id=instrument_id,
        ex_date=effective_date,
        record_date=effective_date,
        pay_date=pay_date,
        effective_date=effective_date,
        cash_amount=Decimal(amount),
        currency=currency,
        distribution_type="unknown",
        frequency=0,
        knowledge_time_status=KnowledgeTimeStatus.FIRST_OBSERVED_ONLY,
        first_observed_at=SOURCE_AT,
        ingested_at=SOURCE_AT,
        quality_status=(
            QualityStatus.VALID if resolved else QualityStatus.PENDING_REVIEW
        ),
        quality_flags=(
            ("source_available_time_unavailable",)
            if resolved
            else ("unresolved_ticker",)
        ),
    )


def _split(instrument_id: UUID) -> CorporateActionSourceObservationV1:
    return CorporateActionSourceObservationV1(
        provider="massive_stocks_basic",
        source_action_id="split-c",
        source_revision=1,
        record_status=CorporateActionRecordStatus.ACTIVE,
        action_type=CorporateActionType.STOCK_SPLIT,
        provider_ticker="CCC",
        instrument_resolution_status=ResolutionStatus.RESOLVED,
        instrument_id=instrument_id,
        effective_date=SESSIONS[1],
        split_ratio_from=Decimal("1"),
        split_ratio_to=Decimal("2"),
        knowledge_time_status=KnowledgeTimeStatus.FIRST_OBSERVED_ONLY,
        first_observed_at=SOURCE_AT,
        ingested_at=SOURCE_AT,
        quality_status=QualityStatus.VALID,
        quality_flags=("source_available_time_unavailable",),
    )


def _fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, object]:
    root = tmp_path / "data"
    root.mkdir(mode=0o755)
    session_rows = {
        SESSIONS[0]: tuple((item, "100", "100") for item in (AAA, BBB, CCC, DDD, EEE, FFF)),
        SESSIONS[1]: tuple((item, "99", "99") for item in (AAA, BBB, CCC, DDD, FFF)),
        SESSIONS[2]: tuple((item, "99", "99") for item in (AAA, BBB, CCC, DDD, FFF)),
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
                    "open": pa.array([Decimal(item[1]) for item in rows], type=price_type),
                    "close": pa.array([Decimal(item[2]) for item in rows], type=price_type),
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
    records = (
        _dividend(AAA, "ordinary", ticker="AAA", amount="1"),
        _dividend(BBB, "large", ticker="BBB", amount="30"),
        _dividend(CCC, "split-day", ticker="CCC", amount="1"),
        _split(CCC),
        _dividend(DDD, "cad", ticker="DDD", amount="1", currency="CAD"),
        _dividend(EEE, "missing", ticker="EEE", amount="1"),
        _dividend(FFF, "multi-a", ticker="FFF", amount="0.5"),
        _dividend(FFF, "multi-b", ticker="FFF", amount="0.5"),
        _dividend(None, "unresolved", ticker="OLD", amount="1"),
    )
    publication = SimpleNamespace(
        start_date=SESSIONS[0],
        end_date=SESSIONS[-1],
        created_at=SOURCE_AT,
        logical_fingerprint="a" * 64,
        point_in_time_eligibility="outcome_reconciliation_only",
        canonical_corporate_action_authorized=False,
        adjustment_ledger_authorized=False,
    )
    publication_path = root / "market-data" / "source" / "manifest.json"
    publication_path.parent.mkdir(parents=True)
    source = SimpleNamespace(
        publication=publication,
        publication_path=publication_path,
        publication_sha256="b" * 64,
        records=records,
    )
    evidence_path = root / "market-data" / "evidence" / "manifest.json"
    evidence_path.parent.mkdir(parents=True)
    eod_source = SimpleNamespace(
        evidence=evidence,
        evidence_path=evidence_path,
        physical_sha256="c" * 64,
    )

    class FakeRepository:
        def __init__(self, _root: Path) -> None:
            pass

        def read_dataset_evidence(self, _path: Path):
            return eod_source

    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", root)
    monkeypatch.setattr(
        module,
        "read_canonical_corporate_action_source",
        lambda **_kwargs: source,
    )
    monkeypatch.setattr(module, "ParquetHistoricalCoverageRepository", FakeRepository)
    return {
        "data_root": root,
        "source_publication_path": publication_path,
        "eod_evidence_path": evidence_path,
        "source_revision": "8" * 40,
        "calculated_at": CALCULATED_AT,
    }


def test_diagnostic_quarantines_ambiguous_dividend_groups(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    report = diagnose_canonical_cash_dividend_candidates(  # type: ignore[arg-type]
        **_fixture(monkeypatch, tmp_path)
    )

    assert report.source_dividend_record_count == 8
    assert report.resolved_dividend_record_count == 7
    assert report.unresolved_dividend_record_count == 1
    assert report.resolved_dividend_group_count == 6
    assert report.bounded_arithmetic_candidate_group_count == 1
    assert report.review_group_count == 5
    assert report.large_distribution_review_group_count == 1
    assert report.large_distribution_date_order_review_group_count == 1
    assert report.multiple_same_date_dividend_group_count == 1
    assert report.same_date_split_group_count == 1
    assert report.non_usd_group_count == 1
    assert report.adjacent_eod_unavailable_group_count == 1
    large = next(item for item in report.review_flags if item.instrument_id == str(BBB))
    assert "large_cash_distribution_date_order_review" in large.review_reasons
    assert large.cash_to_prior_close_ratio == "0.300000000000"
    assert large.raw_open_to_prior_close_ratio == "0.990000000000"
    assert report.canonical_dividend_authorized is False
    assert report.total_return_adjustment_authorized is False
    assert report.historical_coverage_authorized is False
    assert report.research_performance_authorized is False


def test_report_authority_tampering_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    report = diagnose_canonical_cash_dividend_candidates(  # type: ignore[arg-type]
        **_fixture(monkeypatch, tmp_path)
    )

    with pytest.raises(CanonicalCashDividendCandidateDiagnosticError):
        verify_canonical_cash_dividend_candidate_diagnostic(
            replace(report, total_return_adjustment_authorized=True)
        )
