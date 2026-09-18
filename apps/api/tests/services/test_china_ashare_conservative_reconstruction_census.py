from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from tip_api.contracts.china_ashare.v1.cninfo_event_evidence import (
    ChinaAshareCninfoParseStatus,
    ChinaAshareCninfoRequestKind,
)
from tip_api.contracts.china_ashare.v1.conservative_reconstruction_census import (
    ChinaAshareOfficialEvidenceBudgetFamily,
    build_conservative_partition_census,
    build_conservative_reconstruction_plan,
    candidate_set_fingerprint,
)
from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.china_ashare.v1.population import (
    ChinaAsharePopulationDisposition,
)
from tip_api.services import china_ashare_conservative_reconstruction_census as service


INSTRUMENT_A = UUID("00000000-0000-0000-0000-000000000001")
INSTRUMENT_B = UUID("00000000-0000-0000-0000-000000000002")


def test_candidate_scan_is_security_driven_and_provisional_only() -> None:
    plan = _plan()
    source_partition, normalized = _partition()

    census = service.scan_conservative_reconstruction_partition(
        plan=plan,
        source_partition=source_partition,
        normalized_partition=normalized,
        population_occurrences_by_fingerprint=_occurrences(source_partition),
    )

    assert census.target_count == 3
    assert census.resolved_target_count == 2
    assert census.isolated_target_count == 1
    assert census.state_count == 5
    assert census.provisional_candidate_included_state_count == 1
    assert census.provisional_candidate_excluded_state_count == 1
    assert census.provisional_quarantined_state_count == 3
    assert census.warning_present_state_count == 1
    assert census.warning_unknown_state_count == 0
    assert census.trading_status_unknown_state_count == 0
    assert census.factor_change_candidate_window_count == 1
    assert census.terminal_boundary_candidate_security_count == 1
    assert census.resolved_empty_state_target_count == 0
    assert census.warning_candidate_security_count == 1
    assert census.lifecycle_candidate_security_count == 2
    assert census.listing_stage_candidate_security_count == 1
    assert census.action_candidate_security_count == 1
    assert census.maximum_official_request_count == 10
    assert census.outcome_read_count == 0
    assert census.research_backtest_authorized is False


def test_global_merge_quantifies_avoided_blind_requests() -> None:
    plan = _plan()
    first = service.scan_conservative_reconstruction_partition(
        plan=plan,
        source_partition=_partition()[0],
        normalized_partition=_partition()[1],
        population_occurrences_by_fingerprint=_occurrences(_partition()[0]),
    )
    partitions = [first]
    for index in range(1, 109):
        partitions.append(
            build_conservative_partition_census(
                plan_fingerprint=plan.logical_fingerprint,
                partition_index=index,
                normalized_partition_manifest_fingerprint=(
                    plan.normalized_partition_manifest_fingerprints[index]
                ),
                target_count=1,
                resolved_target_count=1,
                isolated_target_count=0,
                state_count=0,
                provisional_candidate_included_state_count=0,
                provisional_candidate_excluded_state_count=0,
                provisional_quarantined_state_count=0,
                warning_present_state_count=0,
                warning_unknown_state_count=0,
                trading_status_unknown_state_count=0,
                factor_change_candidate_window_count=0,
                terminal_boundary_candidate_security_count=0,
                resolved_empty_state_target_count=0,
                warning_candidate_security_count=0,
                lifecycle_candidate_security_count=0,
                listing_stage_candidate_security_count=0,
                action_candidate_security_count=0,
                candidate_records=(),
                candidate_set_fingerprint=candidate_set_fingerprint(()),
                maximum_official_request_count=0,
                outcome_read_count=0,
                research_backtest_authorized=False,
            )
        )

    census = service.merge_conservative_reconstruction_census(
        plan=plan, partitions=tuple(partitions)
    )
    replay = service.merge_conservative_reconstruction_census(
        plan=plan, partitions=tuple(reversed(partitions))
    )

    assert census.logical_fingerprint == replay.logical_fingerprint
    assert census.target_count == 111
    assert census.maximum_official_request_count == 10
    assert census.blind_baseline_request_count == 555
    assert census.avoided_request_count == 545
    assert [item.family.value for item in census.official_request_budget_by_priority] == [
        "risk_warning",
        "lifecycle",
        "listing_stage",
    ]
    assert [item.maximum_request_count for item in census.official_request_budget_by_priority] == [
        1,
        8,
        1,
    ]
    assert census.official_confirmed_full_family_security_count == 0
    assert census.historical_coverage_authorized is False
    assert census.research_backtest_authorized is False


def test_partition_rows_are_fail_closed_and_reconcile_to_census() -> None:
    plan = _plan()
    source_partition, normalized = _partition()
    census = service.scan_conservative_reconstruction_partition(
        plan=plan,
        source_partition=source_partition,
        normalized_partition=normalized,
        population_occurrences_by_fingerprint=_occurrences(source_partition),
    )

    rows = service.build_conservative_universe_partition_rows(
        plan=plan,
        partition_census=census,
        source_partition=source_partition,
        normalized_partition=normalized,
        population_occurrences_by_fingerprint=_occurrences(source_partition),
    )

    assert [item.disposition.value for item in rows] == [
        "provisional_include",
        "quarantine",
        "quarantine",
        "warning_exclude",
        "quarantine",
    ]
    assert all(item.as_operated is False for item in rows)
    assert all(item.research_authorized is False for item in rows)
    assert all(item.return_construction_authorized is False for item in rows)
    assert all(item.research_backtest_authorized is False for item in rows)
    assert "factor_change_candidate_window" in rows[1].reason_codes
    assert "next_session_knowledge_clock_unavailable" in rows[2].reason_codes
    assert "provider_risk_warning_window_excluded" in rows[3].reason_codes
    assert "terminal_boundary_not_officially_adjudicated" in rows[4].reason_codes


def test_sz000001_smoke_requires_six_parsed_zero_event_captures(
    monkeypatch,
) -> None:
    plan = _plan()
    queries = tuple(
        SimpleNamespace(
            query_id=f"q{index}",
            request_kind=(
                ChinaAshareCninfoRequestKind.SECURITY_MAP
                if index == 0
                else ChinaAshareCninfoRequestKind.ANNOUNCEMENT_QUERY
            ),
        )
        for index in range(6)
    )
    cninfo_plan = SimpleNamespace(logical_fingerprint="7" * 64, queries=queries)
    captures = tuple(
        SimpleNamespace(
            query_id=query.query_id,
            logical_fingerprint=f"{index + 20:064x}",
            parse_status=ChinaAshareCninfoParseStatus.PARSED,
            announcements=(),
        )
        for index, query in enumerate(queries)
    )
    source_partition = SimpleNamespace(
        partition=SimpleNamespace(
            partition_index=47,
            targets=(
                SimpleNamespace(
                    source_security_id="sz.000001",
                    listing_date=date(1991, 4, 3),
                ),
            ),
        )
    )
    normalized = SimpleNamespace(
        manifest=SimpleNamespace(logical_fingerprint="8" * 64),
        normalized=SimpleNamespace(
            bars=(
                SimpleNamespace(
                    source_record_id="sz.000001:2024-01-02",
                    instrument_id=INSTRUMENT_A,
                ),
            ),
            states=(
                _state(INSTRUMENT_A, date(2024, 1, 2)),
                _state(INSTRUMENT_A, date(2024, 1, 3)),
            ),
        ),
    )
    resolver_plan = SimpleNamespace(logical_fingerprint="9" * 64)
    mechanics = SimpleNamespace(trading_rules=())

    def resolved(**values):
        return SimpleNamespace(
            status=SimpleNamespace(value="resolved"),
            model_dump=lambda mode: {
                "instrument_id": str(values["instrument_id"]),
                "session_date": values["session_date"].isoformat(),
            },
        )

    monkeypatch.setattr(service, "resolve_china_ashare_price_limit", resolved)
    smoke = service.build_sz000001_price_limit_smoke(
        plan=plan,
        cninfo_plan=cninfo_plan,
        cninfo_replay_captures=captures,
        source_partition=source_partition,
        normalized_partition=normalized,
        mechanics=mechanics,
        price_limit_resolver_plan=resolver_plan,
    )

    assert smoke.state_count == 2
    assert smoke.resolved_count == 2
    assert smoke.quarantined_count == 0
    assert smoke.official_zero_event_evidence is True
    assert smoke.as_operated is False
    assert smoke.research_backtest_authorized is False


def _plan():
    return build_conservative_reconstruction_plan(
        source_expansion_plan_fingerprint="1" * 64,
        population_package_fingerprint="2" * 64,
        normalized_run_fingerprint="3" * 64,
        normalized_partition_manifest_fingerprints=tuple(
            f"{index + 1000:064x}" for index in range(109)
        ),
        market_mechanics_package_fingerprint="4" * 64,
        price_limit_resolver_plan_fingerprint="5" * 64,
        cninfo_sample_plan_fingerprint="7" * 64,
        cninfo_sample_replay_set_fingerprint="6" * 64,
        interval_start=date(2021, 9, 16),
        interval_end=date(2024, 1, 3),
        target_sessions=(
            date(2021, 9, 16),
            date(2024, 1, 1),
            date(2024, 1, 2),
            date(2024, 1, 3),
        ),
        official_evidence_priority=(
            ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING,
            ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE,
            ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE,
        ),
        official_confirmed_requires_all_families=True,
        provider_provisional_as_operated=False,
        provider_provisional_excludes_warning_windows=True,
        provider_provisional_quarantines_action_windows=True,
        provider_provisional_quarantines_terminal_boundaries=True,
        provider_provisional_quarantines_unknown_states=True,
        provider_provisional_reconstructs_normal_limits_from_official_mechanics=True,
        provider_provisional_personal_research_candidate_only=True,
        maximum_requests_per_warning_candidate=1,
        maximum_requests_per_lifecycle_candidate=4,
        maximum_requests_per_listing_candidate=1,
        maximum_requests_per_action_candidate=0,
        action_candidates_remain_isolated_without_official_requests=True,
        outcome_read_count=0,
        return_construction_authorized=False,
        historical_coverage_authorized=False,
        research_backtest_authorized=False,
        factor_discovery_authorized=False,
        product_publication_authorized=False,
    )


def _partition():
    targets = (
        SimpleNamespace(
            source_security_id="sh.600001",
            listing_date=date(2000, 1, 1),
            disposition=ChinaAsharePopulationDisposition.RESOLVED,
            population_occurrence_fingerprint="a" * 64,
        ),
        SimpleNamespace(
            source_security_id="sh.600002",
            listing_date=date(2000, 1, 1),
            disposition=ChinaAsharePopulationDisposition.RESOLVED,
            population_occurrence_fingerprint="b" * 64,
        ),
        SimpleNamespace(
            source_security_id="sh.600003",
            listing_date=date(2022, 1, 1),
            disposition=ChinaAsharePopulationDisposition.QUARANTINED,
            population_occurrence_fingerprint="c" * 64,
        ),
    )
    states = (
        _state(INSTRUMENT_A, date(2024, 1, 1)),
        _state(INSTRUMENT_A, date(2024, 1, 2)),
        _state(INSTRUMENT_A, date(2024, 1, 3)),
        _state(
            INSTRUMENT_B,
            date(2024, 1, 1),
            risk=ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED,
        ),
        _state(INSTRUMENT_B, date(2024, 1, 2)),
    )
    bars = (
        SimpleNamespace(
            source_record_id="sh.600001:2024-01-01", instrument_id=INSTRUMENT_A
        ),
        SimpleNamespace(
            source_record_id="sh.600002:2024-01-01", instrument_id=INSTRUMENT_B
        ),
    )
    adjustments = (
        _adjustment(INSTRUMENT_A, date(2024, 1, 1), "1"),
        _adjustment(INSTRUMENT_A, date(2024, 1, 2), "2"),
    )
    plan = _plan()
    return (
        SimpleNamespace(
            partition=SimpleNamespace(
                partition_index=0,
                targets=targets,
            )
        ),
        SimpleNamespace(
            manifest=SimpleNamespace(
                partition_index=0,
                logical_fingerprint=plan.normalized_partition_manifest_fingerprints[0],
            ),
            normalized=SimpleNamespace(
                states=states,
                bars=bars,
                adjustments=adjustments,
            ),
        ),
    )


def _state(instrument_id, session_date, risk=ChinaAshareRiskWarningStatus.NONE):
    return SimpleNamespace(
        instrument_id=instrument_id,
        session_date=session_date,
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        risk_warning_status=risk,
        trading_status=ChinaAshareTradingStatus.TRADING,
    )


def _adjustment(instrument_id, session_date, factor):
    value = Decimal(factor)
    return SimpleNamespace(
        instrument_id=instrument_id,
        session_date=session_date,
        provider_factor=value,
        fore_adjust_factor=value,
        back_adjust_factor=value,
    )


def _occurrences(source_partition):
    instruments = {
        "sh.600001": INSTRUMENT_A,
        "sh.600002": INSTRUMENT_B,
        "sh.600003": None,
    }
    return {
        target.population_occurrence_fingerprint: SimpleNamespace(
            source_security_id=target.source_security_id,
            instrument_id=instruments[target.source_security_id],
        )
        for target in source_partition.partition.targets
    }
