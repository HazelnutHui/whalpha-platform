from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.candidate_strategy_development_coverage import (
    STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT,
    StrongLeaderPullbackDevelopmentCoverageCensusV1,
)
from tip_api.contracts.analytics.v1.candidate_strategy_development_admission import (
    DevelopmentAdmissionDecisionStatus,
    StrongLeaderPullbackDevelopmentAdmissionDecisionV1,
)
from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
    CanonicalSplitActionV1,
    CanonicalSplitActionPublicationV1,
    CanonicalSplitAdjustmentPublicationV1,
    CorporateActionRecordStatus,
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipDispositionSummaryV1,
    UniverseMembershipOrigin,
    UniverseMembershipPartitionManifestV1,
)
from tip_api.persistence.development_coverage_census import (
    REPORT_FILE,
    read_development_coverage_census,
    write_development_coverage_census,
)
from tip_api.persistence.development_admission_decision import (
    DECISION_FILE,
    read_development_admission_decision,
    write_development_admission_decision,
)
from tip_api.services.candidate_strategy_development_admission import (
    decide_strong_leader_pullback_development_admission,
)
from tip_api.services.candidate_strategy_development_coverage import (
    ReconstructedMembershipSessionEvidence,
    StrongLeaderPullbackDevelopmentCoverageError,
    build_strong_leader_pullback_development_coverage_census,
)
from tip_api.services.market_calendar import ExchangeCalendar


NOW = datetime(2026, 9, 10, 12, tzinfo=UTC)
INSTRUMENT_ID = UUID("00000000-0000-0000-0000-000000000001")
PRIMARY = "provider_classified_common_shares_v1"
SECONDARY = "provider_classified_common_shares_plus_adrs_v1"
UNIVERSES = tuple(sorted((PRIMARY, SECONDARY)))
METHODOLOGY = "provider-form-complete-base-point-in-time-v3"
BASE_SHA = "a" * 64
IDENTITY_SHA = "b" * 64
ACTION_SHA = "c" * 64
ACTION_MANIFEST_SHA = "d" * 64
ADJUSTMENT_SHA = "e" * 64
ADJUSTMENT_MANIFEST_SHA = "f" * 64


@pytest.fixture(scope="module")
def calendar() -> ExchangeCalendar:
    return ExchangeCalendar()


@pytest.fixture(scope="module")
def session_dates(calendar: ExchangeCalendar) -> tuple[date, ...]:
    values = [STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION]
    while len(values) < STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT:
        values.append(calendar.next_session(values[-1]))
    assert values[-1] == STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION
    return tuple(values)


def _sha(index: int) -> str:
    return f"{index:064x}"[-64:]


def _session_evidence(
    session_date: date,
    index: int,
    *,
    included_reasons: tuple[str, ...] = (
        "full_base_trailing_liquidity_passed",
        "provisional_provider_security_form_policy",
        "source_disposition:included",
    ),
) -> ReconstructedMembershipSessionEvidence:
    records = tuple(
        UniverseMembershipDecisionV1(
            universe_id=universe_id,
            instrument_id=INSTRUMENT_ID,
            session_date=session_date,
            methodology_version=METHODOLOGY,
            origin=UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME,
            disposition=UniverseMembershipDisposition.INCLUDED,
            is_member=True,
            reason_codes=included_reasons,
            evaluated_base_fingerprint=BASE_SHA,
            source_fingerprints=(IDENTITY_SHA,),
            source_data_cutoff=NOW - timedelta(days=1),
            evaluated_at=NOW,
            quality_status=QualityStatus.WARNING,
        )
        for universe_id in UNIVERSES
    )
    manifest = UniverseMembershipPartitionManifestV1(
        partition={
            "methodology_version": METHODOLOGY,
            "session_date": session_date.isoformat(),
        },
        record_count=2,
        logical_fingerprint=_sha(1_000 + index),
        physical_sha256=_sha(2_000 + index),
        created_at=NOW,
        methodology_version=METHODOLOGY,
        session_date=session_date,
        origin=UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME,
        universe_ids=UNIVERSES,
        evaluated_base_count=1,
        evaluated_base_fingerprint=BASE_SHA,
        disposition_summaries=tuple(
            UniverseMembershipDispositionSummaryV1(
                universe_id=universe_id,
                included_count=1,
                excluded_count=0,
                quarantined_count=0,
            )
            for universe_id in UNIVERSES
        ),
        source_fingerprints=(IDENTITY_SHA,),
        source_data_cutoff=NOW - timedelta(days=1),
        evaluated_at=NOW,
    )
    return ReconstructedMembershipSessionEvidence(
        manifest=manifest,
        manifest_sha256=_sha(3_000 + index),
        records=records,
        identity_source_logical_fingerprint=IDENTITY_SHA,
        identity_source_record_count=1,
        identity_source_content_fingerprint=_sha(4_000 + index),
        identity_source_manifest_sha256=_sha(5_000 + index),
        identity_source_parquet_sha256=_sha(6_000 + index),
        identity_source_materialized_at=NOW - timedelta(days=1),
    )


def _actions(
    calendar: ExchangeCalendar,
    actions: tuple[CanonicalSplitActionV1, ...] = (),
) -> CanonicalSplitActionPublicationV1:
    return CanonicalSplitActionPublicationV1.model_construct(
        action_record_count=len(actions),
        active_action_record_count=sum(
            item.record_status.value == "active" for item in actions
        ),
        quarantined_action_record_count=0,
        start_date=calendar.sessions_before(
            STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION, 20
        )[0],
        end_date=STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
        point_in_time_eligibility="outcome_reconciliation_only",
        neutral_factor_inference_authorized=False,
        historical_coverage_authorized=False,
        research_performance_authorized=False,
        created_at=NOW - timedelta(hours=1),
        possible_unresolved_impacts=(),
        logical_fingerprint=ACTION_SHA,
    )


def _adjustments(
    calendar: ExchangeCalendar,
    *,
    record_count: int = 0,
    clear_record_count: int = 0,
) -> CanonicalSplitAdjustmentPublicationV1:
    return CanonicalSplitAdjustmentPublicationV1.model_construct(
        source_session_count=STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT + 20,
        record_count=record_count,
        clear_record_count=clear_record_count,
        quarantined_record_count=record_count - clear_record_count,
        first_source_session=calendar.sessions_before(
            STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION, 20
        )[0],
        basis_session=STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
        canonical_action_publication_fingerprint=ACTION_SHA,
        canonical_action_publication_sha256=ACTION_MANIFEST_SHA,
        point_in_time_eligibility="outcome_reconciliation_only",
        absent_row_neutrality_authorized=False,
        full_adjustment_coverage_authorized=False,
        historical_coverage_authorized=False,
        research_performance_authorized=False,
        calculated_at=NOW - timedelta(hours=1),
        logical_fingerprint=ADJUSTMENT_SHA,
    )


def _build(
    *,
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
    evidence: tuple[ReconstructedMembershipSessionEvidence, ...] | None = None,
    actions: tuple[CanonicalSplitActionV1, ...] = (),
    adjustments: tuple[AdjustmentLedgerEntryV1, ...] = (),
) -> StrongLeaderPullbackDevelopmentCoverageCensusV1:
    rows = evidence or tuple(
        _session_evidence(session_date, index)
        for index, session_date in enumerate(session_dates)
    )
    return build_strong_leader_pullback_development_coverage_census(
        membership_sessions=rows,
        split_action_publication=_actions(calendar, actions),
        split_actions=actions,
        split_action_manifest_sha256=ACTION_MANIFEST_SHA,
        split_adjustment_publication=_adjustments(
            calendar,
            record_count=len(adjustments),
            clear_record_count=sum(
                item.split_adjustment_status
                is AdjustmentAvailabilityStatus.CLEAR
                for item in adjustments
            ),
        ),
        split_adjustments=adjustments,
        split_adjustment_manifest_sha256=ADJUSTMENT_MANIFEST_SHA,
        source_revision="1" * 40,
        calculated_at=NOW,
        calendar=calendar,
    )


def test_census_is_deterministic_outcome_blind_and_not_research_ready(
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
) -> None:
    first = _build(calendar=calendar, session_dates=session_dates)
    second = _build(calendar=calendar, session_dates=session_dates)

    assert first == second
    assert first.session_count == 287
    assert first.instrument_count == 1
    assert first.primary_decision_count == 287
    assert first.primary_included_count == 287
    assert first.raw_feature_path_complete_count == 287
    assert first.absent_row_neutrality_unproven_path_count == 287
    assert first.lifecycle_unavailable_path_count == 287
    assert first.all_required_evidence_complete_count == 0
    assert first.contains_strategy_triggers is False
    assert first.contains_forward_outcomes is False
    assert first.contains_performance_metrics is False
    assert first.parameter_selection_authorized is False
    assert first.coverage_threshold_selected is False
    assert first.admitted_cohort_selected is False
    assert first.development_authorized is False
    assert first.validation_authorized is False
    assert first.holdout_access_authorized is False
    assert first.candidate_activation_authorized is False
    assert "outcomes" not in type(first).model_fields
    assert "signals" not in type(first).model_fields
    assert tuple(item.family for item in first.dataset_evidence) == (
        "adjustment_ledger",
        "corporate_action",
        "eod_price_bar",
        "instrument_lifecycle",
        "point_in_time_identity",
        "universe_membership",
    )


def test_census_rejects_incomplete_fixed_interval(
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
) -> None:
    evidence = tuple(
        _session_evidence(session_date, index)
        for index, session_date in enumerate(session_dates[:-1])
    )
    with pytest.raises(
        StrongLeaderPullbackDevelopmentCoverageError,
        match="fixed census interval",
    ):
        _build(
            calendar=calendar,
            session_dates=session_dates,
            evidence=evidence,
        )


def test_census_rejects_included_row_without_feature_window_proof(
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
) -> None:
    rows = [
        _session_evidence(session_date, index)
        for index, session_date in enumerate(session_dates)
    ]
    rows[10] = _session_evidence(
        session_dates[10],
        10,
        included_reasons=("source_disposition:included",),
    )
    with pytest.raises(
        StrongLeaderPullbackDevelopmentCoverageError,
        match="raw feature window",
    ):
        _build(
            calendar=calendar,
            session_dates=session_dates,
            evidence=tuple(rows),
        )


def test_census_counts_sparse_clear_split_exposure_without_authorizing_neutrality(
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
) -> None:
    adjustment = AdjustmentLedgerEntryV1.model_construct(
        instrument_id=INSTRUMENT_ID,
        source_session=session_dates[20],
        split_adjustment_status=AdjustmentAvailabilityStatus.CLEAR,
    )
    action = CanonicalSplitActionV1.model_construct(
        instrument_id=INSTRUMENT_ID,
        effective_date=session_dates[20],
        record_status=CorporateActionRecordStatus.ACTIVE,
    )
    report = _build(
        calendar=calendar,
        session_dates=session_dates,
        actions=(action,),
        adjustments=(adjustment,),
    )

    assert report.sparse_clear_split_exposure_count > 0
    assert report.absent_row_neutrality_unproven_path_count == 287
    assert report.all_required_evidence_complete_count == 0


def test_contract_rejects_tampered_aggregate(
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
) -> None:
    report = _build(calendar=calendar, session_dates=session_dates)
    payload = report.model_dump(mode="json")
    payload["primary_included_count"] += 1

    with pytest.raises(ValidationError, match="aggregates differ"):
        StrongLeaderPullbackDevelopmentCoverageCensusV1.model_validate(payload)


def test_owner_only_report_round_trip(
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
) -> None:
    report = _build(calendar=calendar, session_dates=session_dates)
    output_root = Path(
        "/tmp/whalpha-strong-leader-pullback-development-census-"
        f"pytest-{uuid4().hex}"
    )
    try:
        path = write_development_coverage_census(
            output_root=output_root,
            report=report,
        )
        assert path == output_root / REPORT_FILE
        assert read_development_coverage_census(output_root=output_root) == report
        assert output_root.stat().st_mode & 0o777 == 0o700
        assert path.stat().st_mode & 0o777 == 0o400
    finally:
        path = output_root / REPORT_FILE
        if path.exists() and not path.is_symlink():
            path.unlink()
        if output_root.exists() and not output_root.is_symlink():
            output_root.rmdir()


def test_admission_decision_freezes_full_session_rule_and_rejects_current_evidence(
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
) -> None:
    census = _build(calendar=calendar, session_dates=session_dates)
    decision = decide_strong_leader_pullback_development_admission(
        census=census,
        census_physical_sha256="2" * 64,
        decision_revision="3" * 40,
        decided_at=NOW,
    )

    assert (
        decision.decision_status
        is DevelopmentAdmissionDecisionStatus.REJECTED_CURRENT_EVIDENCE
    )
    assert decision.completeness_threshold_bps == 10_000
    assert decision.minimum_admitted_session_count == 252
    assert decision.raw_candidate_session_count == 287
    assert decision.complete_cross_section_session_count == 0
    assert decision.incomplete_cross_section_session_count == 287
    assert decision.absent_row_neutrality_unproven_path_count == 287
    assert decision.lifecycle_unavailable_path_count == 287
    assert decision.incomplete_required_dataset_families == (
        "adjustment_ledger",
        "corporate_action",
        "instrument_lifecycle",
    )
    assert decision.coverage_threshold_selected is True
    assert decision.admitted_cohort_selected is False
    assert decision.development_authorized is False
    assert "minimum_complete_session_count_not_met" in decision.blocker_codes
    assert "absent_row_neutrality_unproven" in decision.blocker_codes
    assert "instrument_lifecycle_unavailable" in decision.blocker_codes
    assert "outcomes" not in type(decision).model_fields
    assert "signals" not in type(decision).model_fields


def test_admission_decision_rejects_tampered_session_totals(
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
) -> None:
    census = _build(calendar=calendar, session_dates=session_dates)
    decision = decide_strong_leader_pullback_development_admission(
        census=census,
        census_physical_sha256="2" * 64,
        decision_revision="3" * 40,
        decided_at=NOW,
    )
    payload = decision.model_dump(mode="json")
    payload["raw_candidate_session_count"] -= 1

    with pytest.raises(ValidationError, match="observed sessions differ"):
        StrongLeaderPullbackDevelopmentAdmissionDecisionV1.model_validate(payload)


def test_admission_decision_rejects_tampered_blocker_evidence(
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
) -> None:
    census = _build(calendar=calendar, session_dates=session_dates)
    decision = decide_strong_leader_pullback_development_admission(
        census=census,
        census_physical_sha256="2" * 64,
        decision_revision="3" * 40,
        decided_at=NOW,
    )
    payload = decision.model_dump(mode="json")
    payload["blocker_codes"].remove("instrument_lifecycle_unavailable")

    with pytest.raises(ValidationError, match="blocker evidence differs"):
        StrongLeaderPullbackDevelopmentAdmissionDecisionV1.model_validate(payload)


def test_admission_decision_cannot_predate_census(
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
) -> None:
    census = _build(calendar=calendar, session_dates=session_dates)

    with pytest.raises(
        RuntimeError,
        match="cannot predate its census",
    ):
        decide_strong_leader_pullback_development_admission(
            census=census,
            census_physical_sha256="2" * 64,
            decision_revision="3" * 40,
            decided_at=NOW - timedelta(seconds=1),
        )


def test_owner_only_admission_decision_round_trip(
    calendar: ExchangeCalendar,
    session_dates: tuple[date, ...],
) -> None:
    census = _build(calendar=calendar, session_dates=session_dates)
    decision = decide_strong_leader_pullback_development_admission(
        census=census,
        census_physical_sha256="2" * 64,
        decision_revision="3" * 40,
        decided_at=NOW,
    )
    output_root = Path(
        "/tmp/whalpha-strong-leader-pullback-development-admission-"
        f"pytest-{uuid4().hex}"
    )
    try:
        path = write_development_admission_decision(
            output_root=output_root,
            decision=decision,
        )
        assert path == output_root / DECISION_FILE
        assert (
            read_development_admission_decision(output_root=output_root)
            == decision
        )
        assert output_root.stat().st_mode & 0o777 == 0o700
        assert path.stat().st_mode & 0o777 == 0o400
    finally:
        path = output_root / DECISION_FILE
        if path.exists() and not path.is_symlink():
            path.unlink()
        if output_root.exists() and not output_root.is_symlink():
            output_root.rmdir()
