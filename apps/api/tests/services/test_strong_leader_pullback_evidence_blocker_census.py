from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import (
    ResolutionStatus,
    UniverseMembershipDisposition,
)
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    InactiveLifecycleDisposition,
)
from tip_api.services import strong_leader_pullback_evidence_blocker_census as module
from tip_api.services.market_calendar import ExchangeCalendar


IID = UUID("11111111-1111-4111-8111-111111111111")
OTHER_ID = UUID("22222222-2222-4222-8222-222222222222")
NOW = datetime(2026, 9, 13, tzinfo=UTC)
SHA = "a" * 64


def _action(
    *,
    action_id: str,
    effective_date: date,
    ticker: str,
    status: ResolutionStatus,
    instrument_id: UUID | None,
    action_type: str = "cash_dividend",
) -> SimpleNamespace:
    return SimpleNamespace(
        source_action_id=action_id,
        source_revision=1,
        provider_ticker=ticker,
        effective_date=effective_date,
        action_type=SimpleNamespace(value=action_type),
        instrument_resolution_status=status,
        instrument_id=instrument_id,
    )


def test_unassigned_action_candidate_preserves_identity_boundary() -> None:
    event_date = date(2026, 1, 6)
    candidate = SimpleNamespace(instrument_id=IID)
    unresolved = SimpleNamespace(
        provider_ticker="AAA",
        classification="one_historical_candidate",
        unresolved_source_record_count=1,
        candidates=(candidate,),
    )
    residual = SimpleNamespace(
        source_action_id="event-1",
        source_revision=1,
        exact_date_failure_reason="unresolved_ticker",
        inactive_source_state="no_ticker_match",
        inactive_source_type_codes=(),
        finra_exact_date_symbol_occurrence_count=0,
        finra_exact_numeric_occurrence_count=0,
        finra_flag_codes=(),
    )
    records, stats = module._action_exposures(
        source_rows=(
            _action(
                action_id="event-1",
                effective_date=event_date,
                ticker="AAA",
                status=ResolutionStatus.UNRESOLVED,
                instrument_id=None,
            ),
        ),
        unresolved_records=(unresolved,),
        residual_records=(residual,),
        signals={IID: (19, 20, 21)},
        session_index={event_date: 20},
        scoped_sessions=frozenset({event_date}),
        scoped_first=event_date,
        scoped_last=event_date,
    )
    assert len(records) == 1
    assert records[0].identity_evidence_kind == "history_candidate_unassigned"
    assert records[0].stable_identity_assignment_authorized is False
    assert records[0].feature_path_count == 2
    assert records[0].horizon_1_path_count == 1
    assert records[0].horizon_3_path_count == 1
    assert records[0].horizon_5_path_count == 1
    assert stats["unassigned_action_candidate_exposure_record_count"] == 1


def test_primary_membership_projection_validates_only_declared_universe(
    tmp_path: Path,
) -> None:
    session = date(2026, 1, 5)
    partition = tmp_path / "membership"
    partition.mkdir()
    common = {
        "schema_version": "1.0",
        "session_date": session,
        "methodology_version": module.STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY,
        "origin": "reconstructed_point_in_time",
        "reason_codes": ["fixture"],
        "evaluated_base_fingerprint": SHA,
        "source_fingerprints": [SHA],
        "source_data_cutoff": NOW,
        "evaluated_at": NOW,
        "quality_status": "warning",
    }
    table = module.pa.Table.from_pylist(
        [
            {
                **common,
                "universe_id": module.STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE,
                "instrument_id": str(IID),
                "disposition": "included",
                "is_member": True,
            },
            {
                **common,
                "universe_id": "provider_classified_common_shares_plus_adrs_v1",
                "instrument_id": str(OTHER_ID),
                "disposition": "excluded",
                "is_member": False,
            },
        ],
        schema=module.UNIVERSE_MEMBERSHIP_ARROW_SCHEMA,
    )
    module.pq.write_table(table, partition / module.PARQUET_FILE_NAME)
    current = SimpleNamespace(
        membership_partition_path=partition,
        records=(),
        membership_manifest=SimpleNamespace(
            record_count=2,
            disposition_summaries=(
                SimpleNamespace(
                    universe_id=module.STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE,
                    included_count=1,
                    excluded_count=0,
                    quarantined_count=0,
                    evaluated_count=1,
                ),
            ),
        ),
    )
    records = module._read_primary_membership_records(
        current=current,
        session=session,
    )
    assert len(records) == 1
    assert records[0].instrument_id == IID
    assert records[0].disposition is UniverseMembershipDisposition.INCLUDED


def test_lifecycle_candidate_may_equal_last_observed_session() -> None:
    record = module.LifecycleExposureV1(
        instrument_id=IID,
        source_anchor_dates=(date(2026, 9, 3),),
        canonical_first_observed_date=date(2025, 1, 2),
        canonical_last_observed_date=date(2026, 1, 5),
        provider_delist_date_candidate=date(2026, 1, 5),
        included_path_count=1,
        feature_window_outside_observed_span_path_count=0,
        horizon_1_crosses_last_observed_path_count=1,
        horizon_3_crosses_last_observed_path_count=1,
        horizon_5_crosses_last_observed_path_count=1,
        horizon_1_contains_delist_candidate_path_count=0,
        horizon_3_contains_delist_candidate_path_count=0,
        horizon_5_contains_delist_candidate_path_count=0,
    )
    assert record.provider_delist_date_candidate == record.canonical_last_observed_date


def test_build_persists_and_rereads_outcome_blind_package(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calendar = ExchangeCalendar()
    sessions = calendar.sessions_in_range(
        module.STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION,
        module.STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
    )
    assert len(sessions) == 287
    development_root = tmp_path / "development"
    admission_root = tmp_path / "admission"
    development_root.mkdir()
    admission_root.mkdir()
    (development_root / module.REPORT_FILE).write_bytes(b"development\n")
    development_sha = hashlib.sha256(b"development\n").hexdigest()
    (admission_root / module.DECISION_FILE).write_bytes(b"admission\n")
    report_sessions = tuple(
        SimpleNamespace(
            session_date=session,
            membership_logical_fingerprint=f"{index + 1:064x}",
            membership_physical_sha256=f"{index + 1000:064x}",
            membership_manifest_sha256=f"{index + 2000:064x}",
            primary_included_count=1,
        )
        for index, session in enumerate(sessions)
    )
    development = SimpleNamespace(
        logical_fingerprint="b" * 64,
        contains_forward_outcomes=False,
        contains_performance_metrics=False,
        contains_strategy_triggers=False,
        admitted_cohort_selected=False,
        development_authorized=False,
        sessions=report_sessions,
        instruments=(SimpleNamespace(raw_feature_path_complete_count=287),),
        raw_feature_path_complete_count=287,
        primary_decision_count=287,
    )
    admission = SimpleNamespace(
        decision_status=SimpleNamespace(value="rejected_current_evidence"),
        census_logical_fingerprint=development.logical_fingerprint,
        census_physical_sha256=development_sha,
        admitted_cohort_selected=False,
        development_authorized=False,
        logical_fingerprint="c" * 64,
    )
    monkeypatch.setattr(module, "read_development_coverage_census", lambda **_: development)
    monkeypatch.setattr(module, "read_development_admission_decision", lambda **_: admission)

    by_date = {item.session_date: item for item in report_sessions}

    def membership(*, session_date: date, **_: object) -> SimpleNamespace:
        evidence = by_date[session_date]
        return SimpleNamespace(
            membership_manifest=SimpleNamespace(
                logical_fingerprint=evidence.membership_logical_fingerprint,
                physical_sha256=evidence.membership_physical_sha256,
                record_count=2,
            ),
            custody=SimpleNamespace(
                membership_manifest_sha256=evidence.membership_manifest_sha256,
            ),
            custody_sha256=SHA,
            records=(
                SimpleNamespace(
                    universe_id=module.STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE,
                    disposition=UniverseMembershipDisposition.INCLUDED,
                    instrument_id=IID,
                ),
            ),
        )

    monkeypatch.setattr(module, "read_canonical_research_universe_membership", membership)
    action = _action(
        action_id="resolved-1",
        effective_date=sessions[0],
        ticker="AAA",
        status=ResolutionStatus.RESOLVED,
        instrument_id=IID,
    )
    unresolved_action = _action(
        action_id="unresolved-1",
        effective_date=sessions[0],
        ticker="ZZZ",
        status=ResolutionStatus.UNRESOLVED,
        instrument_id=None,
    )
    shadow = SimpleNamespace(
        manifest_sha256="d" * 64,
        manifest=SimpleNamespace(
            logical_fingerprint="e" * 64,
            mapped_record_count=2,
        ),
        records=(action, unresolved_action),
    )
    unresolved = SimpleNamespace(
        manifest_sha256="f" * 64,
        manifest=SimpleNamespace(
            logical_fingerprint="1" * 64,
            resolution_shadow_manifest_sha256=shadow.manifest_sha256,
            resolution_shadow_logical_fingerprint=shadow.manifest.logical_fingerprint,
            unresolved_typed_record_count=1,
        ),
        records=(
            SimpleNamespace(
                provider_ticker="ZZZ",
                classification="zero_historical_candidates",
                unresolved_source_record_count=1,
                candidates=(),
            ),
        ),
    )
    residual = SimpleNamespace(
        manifest_sha256="2" * 64,
        manifest=SimpleNamespace(
            logical_fingerprint="3" * 64,
            resolution_shadow_manifest_sha256=shadow.manifest_sha256,
            resolution_shadow_logical_fingerprint=shadow.manifest.logical_fingerprint,
            unresolved_census_manifest_sha256=unresolved.manifest_sha256,
            unresolved_census_logical_fingerprint=unresolved.manifest.logical_fingerprint,
            residual_record_count=1,
        ),
        records=(
            SimpleNamespace(
                source_action_id="unresolved-1",
                source_revision=1,
                exact_date_failure_reason="unresolved_ticker",
                inactive_source_state="no_ticker_match",
                inactive_source_type_codes=(),
                finra_exact_date_symbol_occurrence_count=0,
                finra_exact_numeric_occurrence_count=0,
                finra_flag_codes=(),
            ),
        ),
    )
    monkeypatch.setattr(
        module, "read_historical_corporate_action_resolution_shadow", lambda **_: shadow
    )
    monkeypatch.setattr(
        module, "read_historical_corporate_action_unresolved_census_output", lambda **_: unresolved
    )
    monkeypatch.setattr(
        module, "read_historical_corporate_action_residual_evidence_census", lambda **_: residual
    )
    lifecycle = SimpleNamespace(
        manifest_sha256="4" * 64,
        manifest=SimpleNamespace(
            anchor_date=date(2026, 9, 3),
            logical_fingerprint="5" * 64,
            decision_artifact=SimpleNamespace(record_count=1),
        ),
        decisions=(
            SimpleNamespace(
                disposition=InactiveLifecycleDisposition.REVIEW_CANDIDATE,
                canonical_instrument_id=IID,
                canonical_first_observed_date=calendar.sessions_before(sessions[0], 20)[0],
                canonical_last_observed_date=sessions[-1],
                effective_date_candidate=calendar.next_session(sessions[-1]),
            ),
        ),
    )
    monkeypatch.setattr(
        module, "read_historical_inactive_lifecycle_resolution_shadow", lambda **_: lifecycle
    )
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", tmp_path)
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    result = module.build_strong_leader_pullback_evidence_blocker_census(
        data_root=tmp_path,
        development_census_root=development_root,
        admission_decision_root=admission_root,
        resolution_shadow_output_root=tmp_path,
        resolution_shadow_custody_root=tmp_path,
        unresolved_census_output_root=tmp_path,
        unresolved_census_custody_root=tmp_path,
        residual_census_output_root=tmp_path,
        residual_census_custody_root=tmp_path,
        lifecycle_shadow_root=tmp_path,
        lifecycle_shadow_custody_root=tmp_path,
        lifecycle_anchor_dates=(date(2026, 9, 3),),
        output_root=custody / "build=fixture",
        output_custody_root=custody,
        implementation_revision="6" * 40,
        evaluated_at=NOW,
    )
    assert result.status == "published"
    assert result.manifest.included_path_count == 287
    assert result.manifest.action_exposure_record_count == 1
    assert result.manifest.feature_action_unique_path_count == 20
    assert result.manifest.global_zero_candidate_source_record_count == 1
    assert result.manifest.lifecycle_instrument_count == 1
    assert result.manifest.horizon_5_lifecycle_crossing_path_count == 5
    assert result.manifest.forward_outcome_count == 0
    assert result.manifest.research_admission_count == 0
    assert result.output_root.stat().st_mode & 0o777 == 0o700
    assert all(item.stat().st_mode & 0o777 == 0o400 for item in result.output_root.iterdir())
    reread = module.read_strong_leader_pullback_evidence_blocker_census(
        output_root=result.output_root,
        output_custody_root=custody,
    )
    assert reread.manifest == result.manifest
    assert reread.action_records == result.action_records

    action_path = result.output_root / module.ACTION_FILE
    action_path.chmod(0o600)
    action_path.write_bytes(action_path.read_bytes() + b"tamper")
    action_path.chmod(0o400)
    with pytest.raises(module.StrongLeaderPullbackEvidenceBlockerCensusError):
        module.read_strong_leader_pullback_evidence_blocker_census(
            output_root=result.output_root,
            output_custody_root=custody,
        )
