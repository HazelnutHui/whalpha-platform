from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import EodPriceBarV1, QualityStatus
from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodDiffDisposition,
    ReconciledEodSourceProvenance,
)
from tip_api.services.reconciled_eod_edition import (
    ReconciledEodEditionError,
    compare_reconciled_eod_records,
    expected_case_sensitive_absences,
    expected_case_sensitive_additions,
)
from tip_api.persistence.parquet.manifest import record_business_key


SESSION = date(2022, 10, 7)
INGESTED = datetime(2022, 10, 8, tzinfo=UTC)
ID1 = UUID("00000000-0000-0000-0000-000000000001")
ID2 = UUID("00000000-0000-0000-0000-000000000002")
ID3 = UUID("00000000-0000-0000-0000-000000000003")


def bar(
    instrument_id: UUID,
    *,
    close: str = "11",
    ingested_at: datetime = INGESTED,
    source_record_id: str | None = None,
) -> EodPriceBarV1:
    return EodPriceBarV1(
        instrument_id=instrument_id,
        session_date=SESSION,
        open=Decimal("10"),
        high=Decimal("12"),
        low=Decimal("9"),
        close=Decimal(close),
        volume=Decimal("1000"),
        vwap=Decimal("10.5"),
        trade_count=25,
        notional=Decimal(close) * Decimal("1000"),
        currency="USD",
        split_adjustment_factor=Decimal("1"),
        dividend_adjustment_factor=Decimal("1"),
        total_return_adjustment_factor=Decimal("1"),
        adjusted_close=Decimal(close),
        source="massive_stocks_basic",
        source_record_id=source_record_id,
        ingested_at=ingested_at,
        revision=1,
        is_latest_revision=True,
        quality_status=QualityStatus.VALID,
    )


def test_expected_case_sensitive_additions_require_an_exact_symbol_pair() -> None:
    expected = expected_case_sensitive_additions(
        exact_provider_tickers=("TPC", "TpC", "ONLY"),
        exact_resolver={"TPC": ID1, "ONLY": ID2},
    )

    assert expected == frozenset({ID1})


def test_retained_source_accepts_only_expected_added_records() -> None:
    summary = compare_reconciled_eod_records(
        base_records=(bar(ID1),),
        rebuilt_records=(bar(ID1), bar(ID2)),
        expected_added_instrument_ids=frozenset({ID2}),
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
    )

    assert summary.disposition == (
        ReconciledEodDiffDisposition.ACCEPTED_CASE_SENSITIVE_ADDITIONS_ONLY
    )
    assert summary.added_record_count == 1


def test_retained_source_accepts_only_fully_proven_legacy_case_misbinding() -> None:
    timestamp = 1_665_100_800_000
    misbound = bar(ID1, source_record_id=f"ALPA:{timestamp}")
    retained = bar(ID2)
    source_payload = {
        "results": [
            {
                "T": "ALpA",
                "o": 10,
                "h": 12,
                "l": 9,
                "c": 11,
                "v": 1000,
                "t": timestamp,
            }
        ]
    }
    expected_absences = expected_case_sensitive_absences(
        base_records=(misbound, retained),
        grouped_daily_payload=source_payload,
        exact_status={"ALPA": "resolved", "ALpA": "excluded"},
        case_colliding_normalized_tickers=frozenset({"ALPA"}),
        canonical_resolver={"ALPA": ID1},
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
        source_observed_at=INGESTED,
    )

    assert expected_absences == frozenset({record_business_key(misbound)})
    summary = compare_reconciled_eod_records(
        base_records=(misbound, retained),
        rebuilt_records=(retained,),
        expected_added_instrument_ids=frozenset(),
        expected_absent_business_keys=expected_absences,
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
    )

    assert summary.disposition == (
        ReconciledEodDiffDisposition.ACCEPTED_CASE_SENSITIVE_RECONCILIATION
    )
    assert summary.absent_record_count == 1
    assert summary.expected_absent_record_count == 1
    assert summary.unexpected_absent_record_count == 0


def test_case_misbinding_absence_rejects_later_or_economically_different_source() -> None:
    timestamp = 1_665_100_800_000
    misbound = bar(ID1, source_record_id=f"ALPA:{timestamp}")
    values = {
        "base_records": (misbound, bar(ID2)),
        "grouped_daily_payload": {
            "results": [
                {
                    "T": "ALpA",
                    "o": 10,
                    "h": 12,
                    "l": 9,
                    "c": 12,
                    "v": 1000,
                    "t": timestamp,
                }
            ]
        },
        "exact_status": {"ALpA": "excluded"},
        "case_colliding_normalized_tickers": frozenset({"ALPA"}),
        "canonical_resolver": {"ALPA": ID1},
        "source_observed_at": INGESTED,
    }

    assert expected_case_sensitive_absences(
        **values,
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
    ) == frozenset()
    assert expected_case_sensitive_absences(
        **values,
        source_provenance=ReconciledEodSourceProvenance.LATER_REACQUISITION,
    ) == frozenset()


def test_unexpected_addition_is_quarantined() -> None:
    summary = compare_reconciled_eod_records(
        base_records=(bar(ID1),),
        rebuilt_records=(bar(ID1), bar(ID3)),
        expected_added_instrument_ids=frozenset({ID2}),
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
    )

    assert summary.disposition == ReconciledEodDiffDisposition.QUARANTINED
    assert summary.quarantine_reasons == ("unexpected_added_records",)


def test_absence_and_economic_change_are_never_auto_accepted() -> None:
    summary = compare_reconciled_eod_records(
        base_records=(bar(ID1), bar(ID2)),
        rebuilt_records=(bar(ID1, close="12"),),
        expected_added_instrument_ids=frozenset(),
        source_provenance=ReconciledEodSourceProvenance.LATER_REACQUISITION,
    )

    assert summary.disposition == ReconciledEodDiffDisposition.QUARANTINED
    assert summary.quarantine_reasons == (
        "base_records_absent",
        "economic_values_changed",
    )


def test_later_reacquisition_may_change_only_provenance() -> None:
    later = datetime(2026, 9, 10, tzinfo=UTC)
    summary = compare_reconciled_eod_records(
        base_records=(bar(ID1),),
        rebuilt_records=(bar(ID1, ingested_at=later),),
        expected_added_instrument_ids=frozenset(),
        source_provenance=ReconciledEodSourceProvenance.LATER_REACQUISITION,
    )

    assert summary.disposition == (
        ReconciledEodDiffDisposition.ACCEPTED_LATER_REACQUISITION
    )
    assert summary.provenance_only_change_count == 1
    assert summary.unexpected_provenance_change_count == 0


def test_retained_source_provenance_change_is_quarantined() -> None:
    later = datetime(2026, 9, 10, tzinfo=UTC)
    summary = compare_reconciled_eod_records(
        base_records=(bar(ID1),),
        rebuilt_records=(bar(ID1, ingested_at=later),),
        expected_added_instrument_ids=frozenset(),
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
    )

    assert summary.disposition == ReconciledEodDiffDisposition.QUARANTINED
    assert summary.quarantine_reasons == (
        "retained_source_provenance_changed",
    )


def test_comparison_rejects_empty_or_cross_session_inputs() -> None:
    with pytest.raises(ReconciledEodEditionError, match="empty"):
        compare_reconciled_eod_records(
            base_records=(),
            rebuilt_records=(bar(ID1),),
            expected_added_instrument_ids=frozenset(),
            source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
        )

    other = bar(ID2).model_copy(update={"session_date": date(2022, 10, 6)})
    with pytest.raises(ReconciledEodEditionError, match="shared session"):
        compare_reconciled_eod_records(
            base_records=(bar(ID1),),
            rebuilt_records=(other,),
            expected_added_instrument_ids=frozenset(),
            source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
        )
