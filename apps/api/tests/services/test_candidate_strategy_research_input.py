from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.analytics.v1 import (
    MarketRegimeStateRecordV1,
    RegimeInitializationStatus,
    RegimeState,
    RegimeStateAvailability,
    RegimeTransitionStatus,
    strong_stock_pullback_research_experiment_v1,
)
from tip_api.contracts.common import QualityStatus
from tip_api.contracts.data_governance.v1 import PointInTimeEligibility
from tip_api.contracts.market_data.v1 import (
    RESEARCH_REQUIRED_DATASET_FAMILIES,
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
    HistoricalCoverageManifestV1,
    HistoricalDatasetCoverageReferenceV1,
    HistoricalReadinessStatus,
    InstrumentType,
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipDispositionSummaryV1,
    UniverseMembershipOrigin,
    UniverseMembershipPartitionManifestV1,
    build_universe_membership_canonical_publication,
    build_universe_membership_knowledge_time_assessment,
    historical_coverage_manifest_fingerprint,
)
from tip_api.read_models.eod import EodMarketBarReadModel, EodSessionDescriptor
from tip_api.services import candidate_strategy_research_input as service
from tip_api.services.candidate_strategy_research_input import (
    StrongLeaderPullbackResearchInputError,
    build_strong_leader_pullback_research_input,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.strategy_research_readiness import (
    assess_strategy_research_readiness,
    canonical_eod_identity_evidence,
)


MEMBER_IDS = (
    UUID("11111111-1111-4111-8111-111111111111"),
    UUID("22222222-2222-4222-8222-222222222222"),
)
SPY_ID = UUID("99999999-9999-4999-8999-999999999999")


def _sessions(count: int = 252) -> tuple[date, ...]:
    calendar = ExchangeCalendar()
    result = [date(2024, 1, 2)]
    while len(result) < count:
        result.append(calendar.next_session(result[-1]))
    return tuple(result)


def _coverage(sessions: tuple[date, ...]) -> HistoricalCoverageManifestV1:
    references = tuple(
        HistoricalDatasetCoverageReferenceV1(
            family=family,
            dataset_path=f"market-data/{family.value}/schema_version=1",
            record_count=len(sessions),
            first_session=sessions[0],
            last_session=sessions[-1],
            logical_fingerprint=f"{index + 1:x}" * 64,
            physical_sha256=f"{index + 7:x}" * 64,
            completed=True,
            quarantined_record_count=0,
        )
        for index, family in enumerate(
            sorted(RESEARCH_REQUIRED_DATASET_FAMILIES, key=lambda item: item.value)
        )
    )
    values = {
        "coverage_id": "a" * 64,
        "sessions": sessions,
        "feature_warmup_sessions": 20,
        "maximum_outcome_horizon_sessions": 5,
        "matured_signal_session_count": len(sessions) - 25,
        "datasets": references,
        "readiness_status": HistoricalReadinessStatus.RESEARCH_READY,
        "reason_codes": (),
        "created_at": datetime(2025, 1, 10, tzinfo=UTC),
    }
    provisional = HistoricalCoverageManifestV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return HistoricalCoverageManifestV1.model_validate(
        {
            **values,
            "logical_fingerprint": historical_coverage_manifest_fingerprint(
                provisional
            ),
        }
    )


def _readiness(sessions, coverage):
    descriptors = tuple(
        EodSessionDescriptor(
            schema_version="1.0",
            session_date=session,
            record_count=100,
            completion_status="completed",
            identity_as_of_date=session,
            available_at=datetime.combine(session, time(22), tzinfo=UTC),
            quality_warning_count=0,
        )
        for session in sessions
    )
    return assess_strategy_research_readiness(
        experiment=strong_stock_pullback_research_experiment_v1(),
        canonical_evidence=canonical_eod_identity_evidence(descriptors),
        coverage_manifest=coverage,
    )


def _membership(as_of: date):
    source_cutoff = datetime.combine(as_of, time(21, 10), tzinfo=UTC)
    evaluated = source_cutoff + timedelta(minutes=10)
    assessed = evaluated + timedelta(minutes=10)
    created = assessed + timedelta(minutes=1)
    base_fingerprint = service._fingerprint([str(item) for item in MEMBER_IDS])
    records = tuple(
        UniverseMembershipDecisionV1(
            universe_id="primary",
            instrument_id=instrument_id,
            session_date=as_of,
            methodology_version="fixture-v1",
            origin=UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME,
            disposition=UniverseMembershipDisposition.INCLUDED,
            is_member=True,
            reason_codes=("provider_cs",),
            evaluated_base_fingerprint=base_fingerprint,
            source_fingerprints=("b" * 64,),
            source_data_cutoff=source_cutoff,
            evaluated_at=evaluated,
            quality_status=QualityStatus.VALID,
        )
        for instrument_id in MEMBER_IDS
    )
    logical_fingerprint = service._fingerprint(
        [item.model_dump(mode="python") for item in records]
    )
    manifest = UniverseMembershipPartitionManifestV1(
        partition={
            "methodology_version": "fixture-v1",
            "session_date": as_of.isoformat(),
        },
        record_count=2,
        logical_fingerprint=logical_fingerprint,
        physical_sha256="c" * 64,
        created_at=created,
        methodology_version="fixture-v1",
        session_date=as_of,
        origin=UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME,
        universe_ids=("primary",),
        evaluated_base_count=2,
        evaluated_base_fingerprint=base_fingerprint,
        disposition_summaries=(
            UniverseMembershipDispositionSummaryV1(
                universe_id="primary",
                included_count=2,
                excluded_count=0,
                quarantined_count=0,
            ),
        ),
        source_fingerprints=("b" * 64,),
        source_data_cutoff=source_cutoff,
        evaluated_at=evaluated,
    )
    next_session = ExchangeCalendar().next_session(as_of)
    assessment = build_universe_membership_knowledge_time_assessment(
        membership_logical_fingerprint=manifest.logical_fingerprint,
        membership_manifest_sha256="d" * 64,
        membership_parquet_sha256=manifest.physical_sha256,
        identity_source_logical_fingerprint="e" * 64,
        identity_source_contract_version="historical-identity-source-custody/1.1",
        identity_source_point_in_time_eligibility="eligible_at_source_observed_at",
        methodology_version=manifest.methodology_version,
        session_date=as_of,
        market_information_cutoff_at=datetime.combine(as_of, time(21), tzinfo=UTC),
        source_data_cutoff=source_cutoff,
        evaluated_at=evaluated,
        entry_session_date=next_session,
        next_session_open_at=datetime.combine(next_session, time(14, 30), tzinfo=UTC),
        assessed_at=assessed,
        calendar_id="XNYS",
        calendar_version="fixture-v1",
        point_in_time_eligibility=PointInTimeEligibility.SIGNAL_ELIGIBLE,
        reason_codes=("source_and_evaluation_completed_before_next_session_open",),
    )
    publication = build_universe_membership_canonical_publication(
        session_date=as_of,
        methodology_version=manifest.methodology_version,
        membership_partition_path="market-data/universe-membership/fixture",
        record_count=2,
        membership_logical_fingerprint=manifest.logical_fingerprint,
        membership_manifest_sha256="d" * 64,
        membership_parquet_sha256=manifest.physical_sha256,
        knowledge_time_assessment=assessment,
        created_at=created,
    )
    return publication, manifest, records


def _regime(as_of: date, state: RegimeState = RegimeState.STRESS):
    values = {
        "state_parameter_fingerprint": "1" * 64,
        "phase1a_parameter_fingerprint": "2" * 64,
        "as_of_session": as_of,
        "universe_id": "primary",
        "composite": "25.0000" if state is RegimeState.STRESS else "50.0000",
        "instantaneous_candidate_state": state,
        "confirmed_state": state,
        "previous_confirmed_state": state,
        "state_is_provisional": False,
        "transition_status": RegimeTransitionStatus.HELD,
        "transition_rule_id": "fixture_hold",
        "pending_target_state": None,
        "consecutive_confirmation_sessions": 1,
        "required_confirmation_sessions": 1,
        "entry_threshold": None,
        "exit_threshold": None,
        "boundary_operator": None,
        "initialization_status": RegimeInitializationStatus.INITIALIZED,
        "state_availability": RegimeStateAvailability.AVAILABLE,
        "stale_state": False,
        "in_hysteresis_band": False,
        "confirmation_sessions_remaining": 0,
        "threshold_distances": (),
        "supporting_dimension_ids": (),
        "conflicting_dimension_ids": (),
        "reason_codes": ("fixture",),
        "source_composite_fingerprint": "3" * 64,
    }
    provisional = MarketRegimeStateRecordV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return MarketRegimeStateRecordV1.model_validate(
        {**values, "logical_fingerprint": service._model_fingerprint(provisional)}
    )


def _market_inputs(sessions: tuple[date, ...]):
    bars = []
    adjustments = []
    specifications = (
        (MEMBER_IDS[0], "ALPHA", InstrumentType.COMMON_STOCK, Decimal("3")),
        (MEMBER_IDS[1], "BETA", InstrumentType.COMMON_STOCK, Decimal("1")),
        (SPY_ID, "SPY", InstrumentType.ETF, Decimal("0.5")),
    )
    for instrument_id, ticker, instrument_type, step in specifications:
        for index, session in enumerate(sessions):
            close = Decimal("100") + Decimal(index) * step
            volume = Decimal("80") if ticker == "ALPHA" and index == 20 else Decimal("100")
            bars.append(
                EodMarketBarReadModel(
                    instrument_id=instrument_id,
                    ticker=ticker,
                    name=ticker,
                    instrument_type=instrument_type,
                    primary_exchange="ARCX" if ticker == "SPY" else "XNYS",
                    session_date=session,
                    open=close - Decimal("1"),
                    high=close + Decimal("1"),
                    low=close - Decimal("2"),
                    close=close,
                    volume=volume,
                    vwap=None,
                    trade_count=None,
                    currency="USD",
                    source="fixture",
                    quality_status=QualityStatus.VALID,
                    quality_flags=(),
                )
            )
            adjustments.append(
                AdjustmentLedgerEntryV1(
                    instrument_id=instrument_id,
                    source_session=session,
                    basis_session=sessions[-1],
                    split_price_multiplier_to_basis=Decimal("1"),
                    split_volume_multiplier_to_basis=Decimal("1"),
                    split_adjustment_status=AdjustmentAvailabilityStatus.CLEAR,
                    total_return_multiplier_to_basis=Decimal("1"),
                    total_return_adjustment_status=AdjustmentAvailabilityStatus.CLEAR,
                    source_action_set_fingerprint="f" * 64,
                    calculation_methodology_version="fixture-v1",
                    source_data_cutoff=datetime.combine(session, time(22), tzinfo=UTC),
                    calculated_at=datetime.combine(sessions[-1], time(23), tzinfo=UTC),
                    revision=1,
                    quality_status=QualityStatus.VALID,
                    quality_flags=(),
                )
            )
    return tuple(bars), tuple(adjustments)


def _fixture():
    all_sessions = _sessions()
    as_of = all_sessions[-1]
    coverage = _coverage(all_sessions)
    readiness = _readiness(all_sessions, coverage)
    publication, manifest, records = _membership(as_of)
    feature_sessions = all_sessions[-21:]
    bars, adjustments = _market_inputs(feature_sessions)
    return {
        "as_of_session": as_of,
        "benchmark_instrument_id": SPY_ID,
        "readiness": readiness,
        "coverage": coverage,
        "membership_publication": publication,
        "membership_manifest": manifest,
        "membership_records": records,
        "market_regime": _regime(as_of),
        "bars": bars,
        "adjustments": adjustments,
    }


def test_builds_complete_deterministic_stress_batch_and_preserves_new_high_control():
    inputs = _fixture()
    first = build_strong_leader_pullback_research_input(**inputs)
    second = build_strong_leader_pullback_research_input(**inputs)

    assert first == second
    assert first.expected_member_count == first.observation_count == 2
    assert len(first.source_sessions) == 21
    assert first.contains_forward_outcomes is False
    assert first.development_authorized is False
    alpha = first.observations[0]
    assert alpha.market_regime == "Stress"
    assert Decimal(alpha.pullback_depth_atr) < 0
    assert alpha.relative_strength_20s_percentile == "1.0000"
    assert alpha.pullback_volume_ratio == "0.8000"


def test_rejects_entire_cross_section_when_one_member_bar_is_missing():
    inputs = _fixture()
    inputs["bars"] = inputs["bars"][:-1]

    with pytest.raises(
        StrongLeaderPullbackResearchInputError,
        match="exactly cover every admitted member",
    ):
        build_strong_leader_pullback_research_input(**inputs)


def test_rejects_membership_rows_that_do_not_match_partition_fingerprint():
    inputs = _fixture()
    records = inputs["membership_records"]
    inputs["membership_records"] = (
        records[0].model_copy(update={"reason_codes": ("changed",)}),
        records[1],
    )

    with pytest.raises(
        StrongLeaderPullbackResearchInputError,
        match="logical fingerprint differs",
    ):
        build_strong_leader_pullback_research_input(**inputs)


def test_rejects_adjustment_source_evidence_not_known_before_next_open():
    inputs = _fixture()
    next_open = inputs["membership_publication"].knowledge_time_assessment.next_session_open_at
    adjustments = inputs["adjustments"]
    inputs["adjustments"] = (
        adjustments[0].model_copy(
            update={
                "source_data_cutoff": next_open,
                "calculated_at": next_open + timedelta(minutes=1),
            }
        ),
        *adjustments[1:],
    )

    with pytest.raises(
        StrongLeaderPullbackResearchInputError,
        match="not complete and clear",
    ):
        build_strong_leader_pullback_research_input(**inputs)
