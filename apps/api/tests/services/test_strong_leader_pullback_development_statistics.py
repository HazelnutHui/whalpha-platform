from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.analytics.v1 import (
    DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT,
    REPLACEMENT_SELECTION_OUTPUT_DIRECTORY,
    REPLACEMENT_SELECTION_POLICY_FINGERPRINT,
    DevelopmentDispositionCountsV1,
    DevelopmentEndpointScenario,
    DevelopmentSelectionStatus,
    StrategyMembershipMode,
    strong_leader_pullback_replacement_selection_protocol_v1,
)
from tip_api.persistence.strong_leader_pullback_development_statistics import (
    StrongLeaderPullbackDevelopmentStatisticsPersistenceError,
    read_strong_leader_pullback_development_statistics,
    write_strong_leader_pullback_development_statistics,
)
from tip_api.persistence.strong_leader_pullback_replacement_selection import (
    StrongLeaderPullbackReplacementSelectionPersistenceError,
    read_strong_leader_pullback_replacement_selection,
    write_strong_leader_pullback_replacement_selection,
)
from tip_api.services.candidate_strategy_research_execution import (
    build_strong_leader_pullback_observation,
)
from tip_api.services.candidate_strategy_research_statistics_oracle import (
    calculate_block_bootstrap_inference_oracle,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.strong_leader_pullback_development_labels import (
    ReconstructedOutcomeBarV1,
    build_reconstructed_development_label,
)
from tip_api.services.strong_leader_pullback_development_statistics import (
    calculate_development_block_bootstrap,
    evaluate_strong_leader_pullback_development_statistics,
)
from tip_api.services.strong_leader_pullback_replacement_selection import (
    _build_selection_report,
    apply_replacement_selection_policy,
)


def _research_rows(*, unavailable_primary_horizon: bool = False):
    calendar = ExchangeCalendar()
    sessions = [date(2025, 1, 2)]
    while len(sessions) < 25:
        sessions.append(calendar.next_session(sessions[-1]))
    observations = []
    labels = []
    instrument_number = 1
    for session_index, signal_session in enumerate(sessions[:20]):
        paths = {
            horizon: tuple(sessions[session_index + 1 : session_index + 1 + horizon])
            for horizon in (1, 3, 5)
        }
        for role_index in range(6):
            is_signal = role_index < 3
            instrument_id = UUID(int=instrument_number)
            ticker = f"T{instrument_number}"
            source = hashlib.sha256(
                f"{signal_session}:{instrument_number}".encode("utf-8")
            ).hexdigest()
            observation = build_strong_leader_pullback_observation(
                as_of_session=signal_session,
                universe_id="primary",
                instrument_id=instrument_id,
                ticker=ticker,
                membership_mode=StrategyMembershipMode.POINT_IN_TIME,
                membership_session=signal_session,
                membership_included=True,
                relative_strength_20s_percentile="0.9500",
                trend_quality_score="80.0000",
                pullback_depth_atr="1.2500",
                close_above_prior_close=True,
                close_above_prior_high=True,
                pullback_volume_ratio="0.7000" if is_signal else "1.5000",
                market_regime="Balanced",
                source_max_session=signal_session,
                source_fingerprint=source,
            )
            observations.append(observation)
            for horizon, path in paths.items():
                unavailable = (
                    unavailable_primary_horizon
                    and instrument_number == 1
                    and horizon == 3
                )
                close = Decimal("103") if is_signal else Decimal("100")
                instrument_bars = tuple(
                    ReconstructedOutcomeBarV1(
                        session=item,
                        open=Decimal("100"),
                        high=max(Decimal("104"), close),
                        low=Decimal("99"),
                        close=close,
                    )
                    for item in path
                )
                benchmark_bars = tuple(
                    ReconstructedOutcomeBarV1(
                        session=item,
                        open=Decimal("100"),
                        high=Decimal("101"),
                        low=Decimal("99"),
                        close=Decimal("100"),
                    )
                    for item in path
                )
                labels.append(
                    build_reconstructed_development_label(
                        observation_fingerprint=observation.logical_fingerprint,
                        signal_session=signal_session,
                        instrument_id=instrument_id,
                        ticker_locator=ticker,
                        expected_path_sessions=path,
                        split_basis_session=sessions[-1],
                        instrument_bars=instrument_bars,
                        benchmark_bars=benchmark_bars,
                        source_eod_fingerprint=source,
                        source_adjustment_fingerprint="a" * 64,
                        unavailable_reason_codes=(
                            ("fixture_source_gap",) if unavailable else ()
                        ),
                    )
                )
            instrument_number += 1
    return (
        tuple(
            sorted(
                observations,
                key=lambda item: (
                    item.as_of_session,
                    item.universe_id,
                    str(item.instrument_id),
                ),
            )
        ),
        tuple(labels),
    )


def _evaluate(observations, labels):
    return evaluate_strong_leader_pullback_development_statistics(
        observations=observations,
        labels=labels,
        source_dataset_manifest_sha256="b" * 64,
        source_dataset_logical_fingerprint="c" * 64,
        implementation_revision="d" * 40,
        created_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
    )


@pytest.fixture(scope="module")
def complete_report():
    return _evaluate(*_research_rows())


@pytest.fixture(scope="module")
def replacement_report(complete_report):
    return _build_selection_report(
        decision=apply_replacement_selection_policy(complete_report.summaries),
        protocol=strong_leader_pullback_replacement_selection_protocol_v1(),
        implementation_revision="e" * 40,
        created_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
    )


def test_policy_is_frozen_before_real_result_evaluation() -> None:
    assert DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT == (
        "a420675be6c7eb580bc95906f4ef0588eccee0d9640047a57d459423e5708f37"
    )


def test_replacement_protocol_is_frozen_without_outcome_design_values() -> None:
    protocol = strong_leader_pullback_replacement_selection_protocol_v1()

    assert REPLACEMENT_SELECTION_POLICY_FINGERPRINT == (
        "9fa09e0b627aed2c1bb1f108eec2d73bfeb3a5407b3c0850b3605b23ef0991f9"
    )
    assert protocol.logical_fingerprint == (
        "65e2258153e6f5462a440662826a2a20594d9a889aaaa0761b71531251e07a0d"
    )
    assert protocol.outcome_values_used_in_design is False
    assert protocol.prior_protocol_trials == 1
    assert protocol.total_protocol_trials == 2
    assert protocol.replacement_run_budget == 1
    assert protocol.validation_data_accessed is False
    assert protocol.holdout_data_accessed is False


def test_replacement_selection_locks_only_after_all_frozen_gates(
    complete_report,
) -> None:
    decision = apply_replacement_selection_policy(complete_report.summaries)

    assert decision.selection_status.value == "locked"
    assert decision.common_eligible_parameter_count == 24
    assert len(decision.eligibility) == 24
    assert all(item.passed for item in decision.gate_results)
    assert set(decision.endpoint_winner_ids.values()) == {
        decision.selected_parameter_combination_id
    }


def test_replacement_selection_blocks_unavailable_primary_evidence() -> None:
    report = _evaluate(*_research_rows(unavailable_primary_horizon=True))

    decision = apply_replacement_selection_policy(report.summaries)

    assert decision.selection_status.value == "blocked_source_evidence"
    assert decision.selected_parameter_combination_id is None
    assert decision.gate_results == ()


def test_complete_exact_matrix_locks_one_stable_parameter(complete_report) -> None:
    report = complete_report
    primary = [item for item in report.summaries if item.horizon_sessions == 3]

    assert len(report.summaries) == 216
    assert len(primary) == 72
    assert report.selection_status is DevelopmentSelectionStatus.LOCKED
    assert report.parameter_lock is not None
    assert report.selected_parameter_combination_id == min(
        item.parameter_combination_id for item in primary
    )
    assert set(report.endpoint_winner_ids.values()) == {
        report.selected_parameter_combination_id
    }
    assert report.validation_data_accessed is False
    assert report.holdout_data_accessed is False
    assert report.validation_transition_authorized is False
    assert report.performance_claim_authorized is False
    assert report.candidate_activation_authorized is False


def test_event_metrics_are_complete_but_portfolio_metrics_do_not_exist(
    complete_report,
) -> None:
    selected = next(
        item
        for item in complete_report.summaries
        if item.parameter_combination_id
        == complete_report.selected_parameter_combination_id
        and item.horizon_sessions == 3
        and item.endpoint_scenario is DevelopmentEndpointScenario.CONTRAST_ADVERSE
    )

    assert selected.signal_disposition.numeric_count == 60
    assert selected.control_disposition.numeric_count == 60
    assert selected.paired_session_count == 20
    assert selected.signal_mean_underlying_return == "0.0300000000"
    assert selected.signal_win_rate == "1.0000000000"
    assert selected.session_balanced_mean_contrast == "0.0300000000"
    assert selected.contrast_lower_90pct == "0.0300000000"
    assert selected.signal_excursion_count == 60
    assert len(selected.stability_slices) == 6
    assert next(
        item.signal_mean_underlying_return_net
        for item in selected.cost_metrics
        if item.basis_points_per_side == 25
    ) == "0.0250000000"
    assert not hasattr(selected, "sharpe_ratio")
    assert not hasattr(selected, "maximum_drawdown")


def test_unavailable_primary_evidence_blocks_parameter_lock() -> None:
    report = _evaluate(*_research_rows(unavailable_primary_horizon=True))

    assert report.selection_status is (
        DevelopmentSelectionStatus.BLOCKED_UNAVAILABLE_EVIDENCE
    )
    assert report.parameter_lock is None
    assert report.selected_parameter_combination_id is None
    assert "primary_family_contains_unavailable_source_evidence" in (
        report.reason_codes
    )


def test_primary_inference_matches_independent_oracle() -> None:
    values = tuple(
        Decimal(((index * 11) % 17) - 8) / Decimal("1000")
        for index in range(37)
    )
    seed = "development:independent-oracle:3:contrast_adverse"

    actual = calculate_development_block_bootstrap(values, seed_material=seed)
    expected = calculate_block_bootstrap_inference_oracle(
        values,
        seed_material=seed,
    )

    assert actual == (
        expected.lower_90pct,
        expected.upper_90pct,
        expected.one_sided_p_value,
    )


def test_disposition_contract_rejects_silent_omission() -> None:
    with pytest.raises(ValueError, match="counts differ"):
        DevelopmentDispositionCountsV1(
            assigned_count=2,
            observed_eod_exact_count=1,
            terminal_reference_exact_count=0,
            terminal_reference_interval_count=0,
            unavailable_evidence_count=0,
            unexecutable_no_next_open_count=0,
            numeric_count=1,
        )


def test_owner_only_statistics_round_trip_and_immutable_replay(
    tmp_path, complete_report
) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    target = custody / "report=fixture"

    first = write_strong_leader_pullback_development_statistics(
        output_root=target,
        output_custody_root=custody,
        report=complete_report,
    )
    second = write_strong_leader_pullback_development_statistics(
        output_root=target,
        output_custody_root=custody,
        report=complete_report,
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert second.report == complete_report
    assert {item.stat().st_mode & 0o777 for item in target.iterdir()} == {0o400}


def test_statistics_reader_rejects_custody_tampering(
    tmp_path, complete_report
) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    target = custody / "report=fixture"
    write_strong_leader_pullback_development_statistics(
        output_root=target,
        output_custody_root=custody,
        report=complete_report,
    )
    (target / "report.json").chmod(0o600)

    with pytest.raises(
        StrongLeaderPullbackDevelopmentStatisticsPersistenceError,
        match="custody",
    ):
        read_strong_leader_pullback_development_statistics(
            output_root=target,
            output_custody_root=custody,
        )


def test_statistics_cli_retains_only_bounded_summary(
    tmp_path, complete_report, monkeypatch, capsys
) -> None:
    from tip_api.services import strong_leader_pullback_development_statistics_cli

    source = SimpleNamespace(
        manifest=SimpleNamespace(
            validation_observation_count=0,
            validation_label_count=0,
            holdout_observation_count=0,
            holdout_label_count=0,
            development_only=True,
            logical_fingerprint="c" * 64,
        ),
        observations=(),
        labels=(),
        manifest_sha256="b" * 64,
    )
    monkeypatch.setattr(
        strong_leader_pullback_development_statistics_cli,
        "read_strong_leader_pullback_development_dataset",
        lambda **_kwargs: source,
    )
    monkeypatch.setattr(
        strong_leader_pullback_development_statistics_cli,
        "evaluate_strong_leader_pullback_development_statistics",
        lambda **_kwargs: complete_report,
    )
    custody = tmp_path / "statistics"
    custody.mkdir(mode=0o700)
    target = custody / "report=fixture"

    status = strong_leader_pullback_development_statistics_cli.main(
        [
            "--development-dataset-root",
            str(tmp_path / "source"),
            "--development-dataset-custody-root",
            str(tmp_path),
            "--output-root",
            str(target),
            "--output-custody-root",
            str(custody),
            "--created-at",
            "2026-09-15T07:00:00Z",
            "--implementation-revision",
            "d" * 40,
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert status == 0
    assert output["status"] == "published"
    assert output["summary_count"] == 216
    assert "summaries" not in output
    assert output["validation_transition_authorized"] is False
    assert output["publication_authorized"] is False


def test_owner_only_replacement_round_trip_and_immutable_replay(
    tmp_path, replacement_report
) -> None:
    custody = tmp_path / "replacement"
    custody.mkdir(mode=0o700)
    target = custody / REPLACEMENT_SELECTION_OUTPUT_DIRECTORY

    first = write_strong_leader_pullback_replacement_selection(
        output_root=target,
        output_custody_root=custody,
        report=replacement_report,
    )
    second = write_strong_leader_pullback_replacement_selection(
        output_root=target,
        output_custody_root=custody,
        report=replacement_report,
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert second.report == replacement_report
    assert {item.stat().st_mode & 0o777 for item in target.iterdir()} == {0o400}


def test_replacement_reader_rejects_custody_tampering(
    tmp_path, replacement_report
) -> None:
    custody = tmp_path / "replacement"
    custody.mkdir(mode=0o700)
    target = custody / REPLACEMENT_SELECTION_OUTPUT_DIRECTORY
    write_strong_leader_pullback_replacement_selection(
        output_root=target,
        output_custody_root=custody,
        report=replacement_report,
    )
    (target / "report.json").chmod(0o600)

    with pytest.raises(
        StrongLeaderPullbackReplacementSelectionPersistenceError,
        match="custody",
    ):
        read_strong_leader_pullback_replacement_selection(
            output_root=target,
            output_custody_root=custody,
        )


def test_replacement_cli_retains_only_bounded_decision(
    tmp_path, complete_report, replacement_report, monkeypatch, capsys
) -> None:
    from tip_api.services import strong_leader_pullback_replacement_selection_cli

    source = SimpleNamespace(
        report=complete_report,
        report_sha256=(
            "c29f04b5e6da95e2256c137f23d00898"
            "b313325ac09e982a991bb823ce0f7852"
        ),
    )
    monkeypatch.setattr(
        strong_leader_pullback_replacement_selection_cli,
        "read_strong_leader_pullback_development_statistics",
        lambda **_kwargs: source,
    )
    monkeypatch.setattr(
        strong_leader_pullback_replacement_selection_cli,
        "evaluate_strong_leader_pullback_replacement_selection",
        lambda **_kwargs: replacement_report,
    )
    custody = tmp_path / "replacement"
    custody.mkdir(mode=0o700)
    target = custody / REPLACEMENT_SELECTION_OUTPUT_DIRECTORY

    status = strong_leader_pullback_replacement_selection_cli.main(
        [
            "--development-statistics-root",
            str(tmp_path / "source"),
            "--development-statistics-custody-root",
            str(tmp_path),
            "--output-root",
            str(target),
            "--output-custody-root",
            str(custody),
            "--created-at",
            "2026-09-15T08:00:00Z",
            "--implementation-revision",
            "e" * 40,
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert status == 0
    assert output["status"] == "published"
    assert output["selection_status"] == "locked"
    assert len(output["gate_passes"]) == 6
    assert "gate_results" not in output
    assert output["validation_transition_authorized"] is False
    assert output["publication_authorized"] is False
    assert output["network_request_count"] == 0
