from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
    CorporateActionRecordStatus,
    CorporateActionSourceObservationV1,
    CorporateActionType,
    HistoricalCoverageManifestV1,
    HistoricalDatasetCoverageReferenceV1,
    HistoricalDatasetFamily,
    HistoricalReadinessStatus,
    InstrumentLifecycleObservationV1,
    InstrumentLifecycleStatus,
    KnowledgeTimeStatus,
    LineageEvidenceStatus,
    RESEARCH_REQUIRED_DATASET_FAMILIES,
    ResolutionStatus,
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipOrigin,
)


INSTRUMENT_ID = UUID("11111111-1111-4111-8111-111111111111")
SUCCESSOR_ID = UUID("22222222-2222-4222-8222-222222222222")
OBSERVED_AT = datetime(2026, 8, 27, 20, 0, tzinfo=UTC)
INGESTED_AT = OBSERVED_AT + timedelta(minutes=2)


def action_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "provider": " massive ",
        "source_action_id": " split-1 ",
        "source_revision": 1,
        "record_status": CorporateActionRecordStatus.ACTIVE,
        "action_type": CorporateActionType.STOCK_SPLIT,
        "provider_ticker": " test.a ",
        "instrument_resolution_status": ResolutionStatus.RESOLVED,
        "instrument_id": INSTRUMENT_ID,
        "effective_date": date(2026, 8, 27),
        "split_ratio_from": Decimal("1"),
        "split_ratio_to": Decimal("2"),
        "knowledge_time_status": KnowledgeTimeStatus.SOURCE_TIMESTAMP,
        "source_available_at": OBSERVED_AT - timedelta(hours=1),
        "first_observed_at": OBSERVED_AT,
        "ingested_at": INGESTED_AT,
        "quality_status": QualityStatus.VALID,
        "quality_flags": (),
    }
    payload.update(overrides)
    return payload


def lifecycle_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "instrument_id": INSTRUMENT_ID,
        "as_of_date": date(2026, 8, 27),
        "valid_from": date(2020, 1, 2),
        "valid_to": None,
        "lifecycle_status": InstrumentLifecycleStatus.ACTIVE,
        "ticker": " test ",
        "primary_exchange": " xnys ",
        "first_tradable_date": date(2020, 1, 2),
        "last_tradable_date": None,
        "predecessor_instrument_id": None,
        "successor_instrument_id": None,
        "lineage_evidence_status": LineageEvidenceStatus.PROVIDER_EXPLICIT,
        "terminal_cash_amount": None,
        "terminal_currency": None,
        "source": " massive ",
        "source_record_id": "ticker-test",
        "source_revision": 1,
        "knowledge_time_status": KnowledgeTimeStatus.SOURCE_TIMESTAMP,
        "source_available_at": OBSERVED_AT,
        "first_observed_at": OBSERVED_AT,
        "ingested_at": INGESTED_AT,
        "quality_status": QualityStatus.VALID,
        "quality_flags": (),
    }
    payload.update(overrides)
    return payload


def membership_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "universe_id": " primary ",
        "instrument_id": INSTRUMENT_ID,
        "session_date": date(2026, 8, 27),
        "methodology_version": "provider-form-primary-v1",
        "origin": UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME,
        "disposition": UniverseMembershipDisposition.INCLUDED,
        "is_member": True,
        "reason_codes": (" Provider CS ",),
        "evaluated_base_fingerprint": "a" * 64,
        "source_fingerprints": ("b" * 64, "c" * 64),
        "source_data_cutoff": OBSERVED_AT,
        "evaluated_at": INGESTED_AT,
        "quality_status": QualityStatus.VALID,
    }
    payload.update(overrides)
    return payload


def adjustment_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "instrument_id": INSTRUMENT_ID,
        "source_session": date(2026, 8, 26),
        "basis_session": date(2026, 8, 27),
        "split_price_multiplier_to_basis": Decimal("0.5"),
        "split_volume_multiplier_to_basis": Decimal("2"),
        "split_adjustment_status": AdjustmentAvailabilityStatus.CLEAR,
        "total_return_multiplier_to_basis": Decimal("0.49"),
        "total_return_adjustment_status": AdjustmentAvailabilityStatus.CLEAR,
        "source_action_set_fingerprint": "d" * 64,
        "calculation_methodology_version": "adjustment-ledger-v1",
        "source_data_cutoff": OBSERVED_AT,
        "calculated_at": INGESTED_AT,
        "revision": 1,
        "quality_status": QualityStatus.VALID,
        "quality_flags": (),
    }
    payload.update(overrides)
    return payload


def coverage_reference(family: HistoricalDatasetFamily, index: int) -> HistoricalDatasetCoverageReferenceV1:
    char = "0123456789abcdef"[index]
    return HistoricalDatasetCoverageReferenceV1(
        family=family,
        dataset_path=f"market-data/{family.value}/schema_version=1",
        record_count=10,
        first_session=date(2026, 8, 24),
        last_session=date(2026, 8, 26),
        logical_fingerprint=char * 64,
        physical_sha256=("f" if char != "f" else "e") * 64,
        completed=True,
        quarantined_record_count=0,
    )


def test_split_action_normalizes_and_preserves_three_clocks() -> None:
    record = CorporateActionSourceObservationV1.model_validate(action_payload())

    assert record.provider == "massive"
    assert record.provider_ticker == "TEST.A"
    assert record.split_ratio_to == Decimal("2")
    assert record.source_available_at < record.first_observed_at < record.ingested_at


def test_active_split_requires_both_ratios_but_quarantine_can_preserve_partial_source() -> None:
    with pytest.raises(ValidationError):
        CorporateActionSourceObservationV1.model_validate(action_payload(split_ratio_to=None))

    record = CorporateActionSourceObservationV1.model_validate(
        action_payload(
            record_status=CorporateActionRecordStatus.QUARANTINED,
            split_ratio_to=None,
            quality_status=QualityStatus.PENDING_REVIEW,
            quality_flags=("missing split ratio",),
        )
    )
    assert record.quality_flags == ("missing_split_ratio",)


def test_cash_dividend_requires_amount_currency_and_ex_date() -> None:
    record = CorporateActionSourceObservationV1.model_validate(
        action_payload(
            action_type=CorporateActionType.CASH_DIVIDEND,
            split_ratio_from=None,
            split_ratio_to=None,
            ex_date=date(2026, 8, 26),
            cash_amount=Decimal("0.25"),
            currency="usd",
        )
    )
    assert record.currency == "USD"

    with pytest.raises(ValidationError):
        CorporateActionSourceObservationV1.model_validate(
            action_payload(
                action_type=CorporateActionType.CASH_DIVIDEND,
                split_ratio_from=None,
                split_ratio_to=None,
                ex_date=date(2026, 8, 26),
                cash_amount=0.25,
                currency="USD",
            )
        )


def test_provider_adjustment_evidence_stays_separate_and_decimal_only() -> None:
    dividend = CorporateActionSourceObservationV1.model_validate(
        action_payload(
            action_type=CorporateActionType.CASH_DIVIDEND,
            split_ratio_from=None,
            split_ratio_to=None,
            ex_date=date(2026, 8, 27),
            cash_amount=Decimal("0.25"),
            currency="USD",
            provider_historical_adjustment_factor=Decimal("0.9975"),
            provider_split_adjusted_cash_amount=Decimal("0.25"),
            distribution_type="recurring",
            frequency=4,
        )
    )
    assert dividend.provider_historical_adjustment_factor == Decimal("0.9975")

    with pytest.raises(ValidationError):
        CorporateActionSourceObservationV1.model_validate(
            action_payload(provider_historical_adjustment_factor=0.5)
        )
    with pytest.raises(ValidationError):
        CorporateActionSourceObservationV1.model_validate(
            action_payload(distribution_type="recurring", frequency=4)
        )


def test_unresolved_action_cannot_carry_stable_id_and_requires_flags() -> None:
    with pytest.raises(ValidationError):
        CorporateActionSourceObservationV1.model_validate(
            action_payload(
                instrument_resolution_status=ResolutionStatus.UNRESOLVED,
                quality_status=QualityStatus.WARNING,
            )
        )

    record = CorporateActionSourceObservationV1.model_validate(
        action_payload(
            instrument_resolution_status=ResolutionStatus.UNRESOLVED,
            instrument_id=None,
            quality_status=QualityStatus.PENDING_REVIEW,
            quality_flags=("no stable id",),
        )
    )
    assert record.instrument_id is None


def test_source_available_time_cannot_be_invented_for_first_observed_only() -> None:
    with pytest.raises(ValidationError):
        CorporateActionSourceObservationV1.model_validate(
            action_payload(knowledge_time_status=KnowledgeTimeStatus.FIRST_OBSERVED_ONLY)
        )


def test_corrected_action_requires_superseded_source_id() -> None:
    with pytest.raises(ValidationError):
        CorporateActionSourceObservationV1.model_validate(
            action_payload(record_status=CorporateActionRecordStatus.CORRECTED)
        )


def test_lifecycle_normalizes_identity_without_using_ticker_as_key() -> None:
    record = InstrumentLifecycleObservationV1.model_validate(lifecycle_payload())

    assert record.instrument_id == INSTRUMENT_ID
    assert record.ticker == "TEST"
    assert record.primary_exchange == "XNYS"


def test_lifecycle_enforces_three_clock_ordering() -> None:
    with pytest.raises(ValidationError):
        InstrumentLifecycleObservationV1.model_validate(
            lifecycle_payload(
                source_available_at=OBSERVED_AT + timedelta(minutes=1),
            )
        )
    with pytest.raises(ValidationError):
        InstrumentLifecycleObservationV1.model_validate(
            lifecycle_payload(
                ingested_at=OBSERVED_AT - timedelta(minutes=1),
            )
        )


def test_unknown_lifecycle_is_explicitly_quarantined() -> None:
    record = InstrumentLifecycleObservationV1.model_validate(
        lifecycle_payload(
            lifecycle_status=InstrumentLifecycleStatus.UNKNOWN,
            lineage_evidence_status=LineageEvidenceStatus.UNRESOLVED,
            quality_status=QualityStatus.PENDING_REVIEW,
            quality_flags=("disappearance cause unknown",),
        )
    )
    assert record.quality_flags == ("disappearance_cause_unknown",)

    with pytest.raises(ValidationError):
        InstrumentLifecycleObservationV1.model_validate(
            lifecycle_payload(lifecycle_status=InstrumentLifecycleStatus.UNKNOWN)
        )


def test_lifecycle_rejects_self_lineage_and_partial_terminal_cash() -> None:
    with pytest.raises(ValidationError):
        InstrumentLifecycleObservationV1.model_validate(
            lifecycle_payload(successor_instrument_id=INSTRUMENT_ID)
        )
    with pytest.raises(ValidationError):
        InstrumentLifecycleObservationV1.model_validate(
            lifecycle_payload(terminal_cash_amount=Decimal("10"))
        )


def test_lifecycle_accepts_distinct_successor_and_terminal_cash() -> None:
    record = InstrumentLifecycleObservationV1.model_validate(
        lifecycle_payload(
            lifecycle_status=InstrumentLifecycleStatus.ACQUIRED,
            successor_instrument_id=SUCCESSOR_ID,
            last_tradable_date=date(2026, 8, 26),
            terminal_cash_amount=Decimal("10"),
            terminal_currency="usd",
        )
    )
    assert record.successor_instrument_id == SUCCESSOR_ID
    assert record.terminal_currency == "USD"


@pytest.mark.parametrize(
    ("disposition", "is_member"),
    [
        (UniverseMembershipDisposition.INCLUDED, True),
        (UniverseMembershipDisposition.EXCLUDED, False),
        (UniverseMembershipDisposition.QUARANTINED, None),
    ],
)
def test_membership_uses_explicit_three_state_disposition(
    disposition: UniverseMembershipDisposition,
    is_member: bool | None,
) -> None:
    quality = QualityStatus.PENDING_REVIEW if disposition is UniverseMembershipDisposition.QUARANTINED else QualityStatus.VALID
    record = UniverseMembershipDecisionV1.model_validate(
        membership_payload(disposition=disposition, is_member=is_member, quality_status=quality)
    )
    assert record.is_member is is_member


def test_membership_cannot_turn_quarantine_into_false_or_use_future_cutoff() -> None:
    with pytest.raises(ValidationError):
        UniverseMembershipDecisionV1.model_validate(
            membership_payload(
                disposition=UniverseMembershipDisposition.QUARANTINED,
                is_member=False,
                quality_status=QualityStatus.PENDING_REVIEW,
            )
        )
    with pytest.raises(ValidationError):
        UniverseMembershipDecisionV1.model_validate(
            membership_payload(source_data_cutoff=INGESTED_AT + timedelta(seconds=1))
        )


def test_membership_requires_reason_and_unique_source_fingerprints() -> None:
    with pytest.raises(ValidationError):
        UniverseMembershipDecisionV1.model_validate(membership_payload(reason_codes=()))
    with pytest.raises(ValidationError):
        UniverseMembershipDecisionV1.model_validate(
            membership_payload(source_fingerprints=("b" * 64, "b" * 64))
        )


def test_clear_adjustment_keeps_price_and_total_return_distinct() -> None:
    record = AdjustmentLedgerEntryV1.model_validate(adjustment_payload())

    assert record.factor_direction == "multiply_raw_value_to_basis"
    assert record.split_price_multiplier_to_basis == Decimal("0.5")
    assert record.total_return_multiplier_to_basis == Decimal("0.49")


def test_unavailable_adjustment_cannot_carry_neutral_placeholder_factors() -> None:
    record = AdjustmentLedgerEntryV1.model_validate(
        adjustment_payload(
            split_price_multiplier_to_basis=None,
            split_volume_multiplier_to_basis=None,
            split_adjustment_status=AdjustmentAvailabilityStatus.UNAVAILABLE,
            total_return_multiplier_to_basis=None,
            total_return_adjustment_status=AdjustmentAvailabilityStatus.UNAVAILABLE,
            quality_status=QualityStatus.PENDING_REVIEW,
            quality_flags=("action coverage missing",),
        )
    )
    assert record.split_price_multiplier_to_basis is None

    with pytest.raises(ValidationError):
        AdjustmentLedgerEntryV1.model_validate(
            adjustment_payload(
                split_adjustment_status=AdjustmentAvailabilityStatus.UNAVAILABLE,
                total_return_multiplier_to_basis=None,
                total_return_adjustment_status=AdjustmentAvailabilityStatus.UNAVAILABLE,
                quality_status=QualityStatus.PENDING_REVIEW,
                quality_flags=("action coverage missing",),
            )
        )


def test_adjustment_rejects_future_basis_direction_and_binary_float() -> None:
    with pytest.raises(ValidationError):
        AdjustmentLedgerEntryV1.model_validate(
            adjustment_payload(basis_session=date(2026, 8, 25))
        )
    with pytest.raises(ValidationError):
        AdjustmentLedgerEntryV1.model_validate(
            adjustment_payload(split_price_multiplier_to_basis=0.5)
        )


def test_coverage_reference_rejects_absolute_path_and_bad_counts() -> None:
    with pytest.raises(ValidationError):
        HistoricalDatasetCoverageReferenceV1(
            family=HistoricalDatasetFamily.EOD_PRICE_BAR,
            dataset_path="/data/secret",
            record_count=1,
            first_session=date(2026, 8, 26),
            last_session=date(2026, 8, 26),
            logical_fingerprint="a" * 64,
            physical_sha256="b" * 64,
            completed=True,
            quarantined_record_count=0,
        )

    with pytest.raises(ValidationError):
        HistoricalDatasetCoverageReferenceV1(
            family=HistoricalDatasetFamily.EOD_PRICE_BAR,
            dataset_path="market-data/eod",
            record_count=1,
            first_session=date(2026, 8, 26),
            last_session=date(2026, 8, 26),
            logical_fingerprint="a" * 64,
            physical_sha256="b" * 64,
            completed=True,
            quarantined_record_count=2,
        )


def test_research_ready_coverage_requires_every_completed_family() -> None:
    sessions = tuple(
        date(2026, 8, 26) - timedelta(days=index)
        for index in reversed(range(252))
    )
    datasets = tuple(
        coverage_reference(family, index).model_copy(
            update={"first_session": sessions[0]}
        )
        for index, family in enumerate(
            sorted(RESEARCH_REQUIRED_DATASET_FAMILIES, key=lambda item: item.value),
            start=1,
        )
    )
    manifest = HistoricalCoverageManifestV1(
        coverage_id="a" * 64,
        sessions=sessions,
        feature_warmup_sessions=26,
        maximum_outcome_horizon_sessions=5,
        matured_signal_session_count=221,
        datasets=datasets,
        readiness_status=HistoricalReadinessStatus.RESEARCH_READY,
        reason_codes=(),
        created_at=INGESTED_AT,
        logical_fingerprint="b" * 64,
    )
    assert manifest.readiness_status is HistoricalReadinessStatus.RESEARCH_READY

    with pytest.raises(ValidationError):
        HistoricalCoverageManifestV1(
            **{
                **manifest.model_dump(),
                "datasets": datasets[:-1],
            }
        )


def test_research_ready_coverage_rejects_short_or_undercovered_history() -> None:
    short_sessions = tuple(
        date(2026, 8, 26) - timedelta(days=index)
        for index in reversed(range(30))
    )
    datasets = tuple(
        coverage_reference(family, index).model_copy(
            update={"first_session": short_sessions[0]}
        )
        for index, family in enumerate(
            sorted(RESEARCH_REQUIRED_DATASET_FAMILIES, key=lambda item: item.value),
            start=1,
        )
    )
    with pytest.raises(ValidationError):
        HistoricalCoverageManifestV1(
            coverage_id="a" * 64,
            sessions=short_sessions,
            feature_warmup_sessions=26,
            maximum_outcome_horizon_sessions=3,
            matured_signal_session_count=1,
            datasets=datasets,
            readiness_status=HistoricalReadinessStatus.RESEARCH_READY,
            reason_codes=(),
            created_at=INGESTED_AT,
            logical_fingerprint="b" * 64,
        )

    sessions = tuple(
        date(2026, 8, 26) - timedelta(days=index)
        for index in reversed(range(252))
    )
    undercovered = tuple(
        reference.model_copy(update={"first_session": sessions[0]})
        for reference in datasets
    )
    undercovered = (
        undercovered[0].model_copy(
            update={"first_session": sessions[0] + timedelta(days=1)}
        ),
        *undercovered[1:],
    )
    with pytest.raises(ValidationError):
        HistoricalCoverageManifestV1(
            coverage_id="a" * 64,
            sessions=sessions,
            feature_warmup_sessions=26,
            maximum_outcome_horizon_sessions=5,
            matured_signal_session_count=221,
            datasets=undercovered,
            readiness_status=HistoricalReadinessStatus.RESEARCH_READY,
            reason_codes=(),
            created_at=INGESTED_AT,
            logical_fingerprint="b" * 64,
        )


def test_source_observations_do_not_replace_canonical_corporate_actions() -> None:
    sessions = tuple(
        date(2026, 8, 26) - timedelta(days=index)
        for index in reversed(range(252))
    )
    incomplete_families = (
        RESEARCH_REQUIRED_DATASET_FAMILIES
        - {HistoricalDatasetFamily.CORPORATE_ACTION}
        | {HistoricalDatasetFamily.CORPORATE_ACTION_SOURCE_OBSERVATION}
    )
    datasets = tuple(
        coverage_reference(family, index).model_copy(
            update={"first_session": sessions[0]}
        )
        for index, family in enumerate(
            sorted(incomplete_families, key=lambda item: item.value),
            start=1,
        )
    )
    with pytest.raises(ValidationError):
        HistoricalCoverageManifestV1(
            coverage_id="a" * 64,
            sessions=sessions,
            feature_warmup_sessions=26,
            maximum_outcome_horizon_sessions=5,
            matured_signal_session_count=221,
            datasets=datasets,
            readiness_status=HistoricalReadinessStatus.RESEARCH_READY,
            reason_codes=(),
            created_at=INGESTED_AT,
            logical_fingerprint="b" * 64,
        )

    complete_required = tuple(
        coverage_reference(family, index).model_copy(
            update={"first_session": sessions[0]}
        )
        for index, family in enumerate(
            sorted(RESEARCH_REQUIRED_DATASET_FAMILIES, key=lambda item: item.value),
            start=1,
        )
    )
    incomplete_observation = coverage_reference(
        HistoricalDatasetFamily.CORPORATE_ACTION_SOURCE_OBSERVATION,
        7,
    ).model_copy(update={"first_session": sessions[0], "completed": False})
    with pytest.raises(ValidationError):
        HistoricalCoverageManifestV1(
            coverage_id="a" * 64,
            sessions=sessions,
            feature_warmup_sessions=26,
            maximum_outcome_horizon_sessions=5,
            matured_signal_session_count=221,
            datasets=(*complete_required, incomplete_observation),
            readiness_status=HistoricalReadinessStatus.RESEARCH_READY,
            reason_codes=(),
            created_at=INGESTED_AT,
            logical_fingerprint="b" * 64,
        )


def test_non_ready_coverage_requires_reasons_and_unique_families() -> None:
    reference = coverage_reference(HistoricalDatasetFamily.EOD_PRICE_BAR, 1)
    with pytest.raises(ValidationError):
        HistoricalCoverageManifestV1(
            coverage_id="a" * 64,
            sessions=(date(2026, 8, 26),),
            feature_warmup_sessions=26,
            maximum_outcome_horizon_sessions=5,
            matured_signal_session_count=0,
            datasets=(reference,),
            readiness_status=HistoricalReadinessStatus.SOURCE_INCOMPLETE,
            reason_codes=(),
            created_at=INGESTED_AT,
            logical_fingerprint="b" * 64,
        )
    with pytest.raises(ValidationError):
        HistoricalCoverageManifestV1(
            coverage_id="a" * 64,
            sessions=(date(2026, 8, 26),),
            feature_warmup_sessions=26,
            maximum_outcome_horizon_sessions=5,
            matured_signal_session_count=0,
            datasets=(reference, reference),
            readiness_status=HistoricalReadinessStatus.SOURCE_INCOMPLETE,
            reason_codes=("missing families",),
            created_at=INGESTED_AT,
            logical_fingerprint="b" * 64,
        )
