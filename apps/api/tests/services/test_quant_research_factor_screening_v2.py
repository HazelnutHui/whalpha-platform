from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.analytics.v1 import (
    quant_research_factor_screening_result_v2 as result_contract,
)
from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
    QuantResearchFactorAvailabilityV2,
    QuantResearchFactorValueV2,
    build_quant_research_factor_observation_v2,
    factor_definition_v2_fingerprint,
    quant_research_factor_catalog_v2,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening import (
    quant_research_factor_screening_protocol_v1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_result import (
    QuantResearchFactorScreeningDecisionStatus,
    QuantResearchFactorScreeningEndpoint,
    QuantResearchFactorScreeningLabelState,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_result_v2 import (
    build_factor_screening_control_v2,
    build_factor_screening_label_v2,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_v2 import (
    quant_research_factor_screening_protocol_v2,
)
from tip_api.services import quant_research_factor_screening_v2 as service


def test_v2_block_bootstrap_is_deterministic() -> None:
    values = tuple(index / 1000 for index in range(1, 41))

    assert service.calculate_block_bootstrap_v2(
        values, seed_material="registered-v2-test"
    ) == service.calculate_block_bootstrap_v2(
        values, seed_material="registered-v2-test"
    )


def test_v2_collection_fingerprint_binds_order_type_and_membership() -> None:
    first = SimpleNamespace(logical_fingerprint="1" * 64)
    second = SimpleNamespace(logical_fingerprint="2" * 64)

    original = service._collection_fingerprint((first, second))

    assert original == service._collection_fingerprint((first, second))
    assert original != service._collection_fingerprint((second, first))
    assert original != service._collection_fingerprint((first,))


def test_v2_horizon_result_keeps_factor_and_control_missingness_separate(
    monkeypatch,
) -> None:
    protocol = quant_research_factor_screening_protocol_v2()
    payload = protocol.model_dump(mode="python")
    payload.update(
        minimum_instruments_per_session=5,
        minimum_primary_sessions=1,
        minimum_chronological_half_sessions=1,
        bootstrap_replicates=100,
        development_declared_path_count=12,
        development_declared_session_count=2,
        formal_hypotheses=protocol.formal_hypotheses,
    )
    monkeypatch.setattr(
        service,
        "quant_research_factor_screening_protocol_v2",
        lambda: SimpleNamespace(**payload),
    )
    monkeypatch.setattr(
        result_contract,
        "quant_research_factor_screening_protocol_v2",
        lambda: SimpleNamespace(**payload),
    )
    hypothesis = protocol.formal_hypotheses[0]
    sessions = (date(2025, 8, 1), date(2025, 8, 4))
    observations = []
    controls = {}
    labels = {}
    for session_index, session in enumerate(sessions):
        for item_index in range(6):
            instrument_id = UUID(int=1 + session_index * 6 + item_index)
            unavailable_factor = session_index == 0 and item_index == 0
            factor_values = tuple(
                QuantResearchFactorValueV2(
                    factor_id=factor_id,
                    factor_definition_fingerprint=(
                        factor_definition_v2_fingerprint(factor_id)
                    ),
                    availability=(
                        QuantResearchFactorAvailabilityV2.UNAVAILABLE
                        if unavailable_factor and factor_id == hypothesis.factor_id
                        else QuantResearchFactorAvailabilityV2.AVAILABLE
                    ),
                    value=(
                        None
                        if unavailable_factor and factor_id == hypothesis.factor_id
                        else f"{(item_index + 1) / 100:.10f}"
                    ),
                    reason_codes=(
                        ("factor_source_unavailable",)
                        if unavailable_factor and factor_id == hypothesis.factor_id
                        else ()
                    ),
                )
                for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
            )
            observation = build_quant_research_factor_observation_v2(
                catalog_fingerprint=quant_research_factor_catalog_v2().logical_fingerprint,
                as_of_session=session,
                instrument_id=instrument_id,
                display_ticker=f"T{session_index}{item_index}",
                source_min_session=session - timedelta(days=180),
                source_max_session=session,
                source_eod_fingerprint="2" * 64,
                source_adjustment_fingerprint="3" * 64,
                factor_values=factor_values,
            )
            observations.append(observation)
            unavailable_control = session_index == 0 and item_index == 1
            control_values = (0.000, 0.020, 0.005, 0.025, 0.010, 0.015)
            controls[observation.logical_fingerprint] = (
                build_factor_screening_control_v2(
                    protocol_fingerprint=protocol.logical_fingerprint,
                    observation_fingerprint=observation.logical_fingerprint,
                    signal_session=session,
                    instrument_id=instrument_id,
                    factor_definition_fingerprint=(
                        protocol.incremental_baseline_definition_fingerprint
                    ),
                    available=not unavailable_control,
                    value=(
                        None
                        if unavailable_control
                        else f"{control_values[item_index]:.10f}"
                    ),
                    reason_codes=(
                        ("control_source_unavailable",)
                        if unavailable_control
                        else ()
                    ),
                    source_min_session=session - timedelta(days=30),
                    source_max_session=session,
                    source_eod_fingerprint="2" * 64,
                    source_action_fingerprint="5" * 64,
                    source_adjustment_fingerprint="3" * 64,
                )
            )
            outcome = (item_index + 1) / 100
            exit_price = 10 * (1 + outcome)
            labels[observation.logical_fingerprint] = {
                3: build_factor_screening_label_v2(
                    protocol_fingerprint=protocol.logical_fingerprint,
                    catalog_fingerprint=protocol.catalog_fingerprint,
                    observation_fingerprint=observation.logical_fingerprint,
                    signal_session=session,
                    instrument_id=instrument_id,
                    display_ticker=observation.display_ticker,
                    horizon_sessions=3,
                    expected_entry_session=session + timedelta(days=1),
                    expected_exit_session=session + timedelta(days=3),
                    expected_path_sessions=tuple(
                        session + timedelta(days=value) for value in (1, 2, 3)
                    ),
                    split_basis_session=session + timedelta(days=3),
                    state=QuantResearchFactorScreeningLabelState.OBSERVED_EOD_EXACT,
                    entry_price_usd="10.0000000000",
                    exit_price_lower_usd=f"{exit_price:.10f}",
                    exit_price_upper_usd=f"{exit_price:.10f}",
                    underlying_price_return_lower=f"{outcome:.10f}",
                    underlying_price_return_upper=f"{outcome:.10f}",
                    benchmark_price_return="0.0000000000",
                    relative_to_benchmark_return_lower=f"{outcome:.10f}",
                    relative_to_benchmark_return_upper=f"{outcome:.10f}",
                    maximum_favorable_excursion=f"{outcome:.10f}",
                    maximum_adverse_excursion="0.0000000000",
                    source_eod_fingerprint="4" * 64,
                    source_action_fingerprint="5" * 64,
                    source_adjustment_fingerprint="3" * 64,
                    reason_codes=(),
                )
            }

    result = service._build_horizon_result(
        hypothesis=hypothesis,
        horizon=3,
        endpoint=QuantResearchFactorScreeningEndpoint.LOWER,
        observations=tuple(observations),
        controls_by_observation=controls,
        labels_by_observation=labels,
    )

    assert result.assigned_path_count == 12
    assert result.factor_available_path_count == 11
    assert result.control_available_path_count == 11
    assert result.numeric_path_count == 11
    assert result.partial_numeric_path_count == 10
    assert result.factor_unavailable_reason_counts == {"factor_source_unavailable": 1}
    assert result.control_unavailable_reason_counts == {"control_source_unavailable": 1}
    assert result.eligible_session_count == 2
    assert result.partial_eligible_session_count == 1


def test_v2_risk_guard_cannot_enter_candidate_set_without_candidate_alpha() -> None:
    protocol = quant_research_factor_screening_protocol_v2()
    results = []
    for hypothesis in protocol.formal_hypotheses:
        endpoints = (
            (
                QuantResearchFactorScreeningEndpoint.LOWER,
                QuantResearchFactorScreeningEndpoint.UPPER,
            )
            if hypothesis.role.value == "candidate_alpha"
            else (QuantResearchFactorScreeningEndpoint.COMPLETE_PATH,)
        )
        for horizon in (1, 3, 5):
            for endpoint in endpoints:
                alpha_primary_failure = (
                    hypothesis.role.value == "candidate_alpha" and horizon == 3
                )
                results.append(
                    SimpleNamespace(
                        factor_id=hypothesis.factor_id,
                        horizon_sessions=horizon,
                        endpoint=endpoint,
                        eligible_session_count=100,
                        first_half_session_count=50,
                        second_half_session_count=50,
                        partial_eligible_session_count=100,
                        one_sided_raw_p_value="0.0010000000",
                        partial_one_sided_raw_p_value="0.0010000000",
                        mean_rank_ic=(
                            "0.0000000000"
                            if alpha_primary_failure
                            else "0.0200000000"
                        ),
                        mean_partial_rank_ic="0.0100000000",
                        rank_ic_lower_90pct="0.0050000000",
                        partial_rank_ic_lower_90pct="0.0050000000",
                        positive_session_share="0.6000000000",
                        largest_absolute_session_contribution_share=(
                            "0.1000000000"
                        ),
                        first_half_mean_rank_ic="0.0100000000",
                        second_half_mean_rank_ic="0.0100000000",
                        bucket_monotonic_spearman="0.9000000000",
                        bucket_top_minus_bottom="0.0100000000",
                    )
                )

    decisions, selected = service._build_decisions(tuple(results))

    assert selected == ()
    assert all(
        item.status is QuantResearchFactorScreeningDecisionStatus.REJECTED_SCREEN
        for item in decisions
        if item.role.value == "candidate_alpha"
    )
    assert all(
        item.status
        is QuantResearchFactorScreeningDecisionStatus.QUALIFIED_NOT_SELECTED_CAP
        and item.reason_codes
        == ("passed_gates_but_candidate_alpha_prerequisite_absent",)
        for item in decisions
        if item.role.value == "risk_guard"
    )


def test_v2_holm_adjustment_preserves_registered_family_sizes_when_results_missing(
    monkeypatch,
) -> None:
    protocol = quant_research_factor_screening_protocol_v2()
    results = []
    for hypothesis in protocol.formal_hypotheses:
        endpoints = (
            (
                QuantResearchFactorScreeningEndpoint.LOWER,
                QuantResearchFactorScreeningEndpoint.UPPER,
            )
            if hypothesis.role.value == "candidate_alpha"
            else (QuantResearchFactorScreeningEndpoint.COMPLETE_PATH,)
        )
        for horizon in (1, 3, 5):
            for endpoint in endpoints:
                results.append(
                    SimpleNamespace(
                        factor_id=hypothesis.factor_id,
                        horizon_sessions=horizon,
                        endpoint=endpoint,
                        eligible_session_count=0,
                        first_half_session_count=0,
                        second_half_session_count=0,
                        partial_eligible_session_count=0,
                        one_sided_raw_p_value=None,
                        partial_one_sided_raw_p_value=None,
                        mean_rank_ic=None,
                        mean_partial_rank_ic=None,
                        rank_ic_lower_90pct=None,
                        partial_rank_ic_lower_90pct=None,
                        positive_session_share=None,
                        largest_absolute_session_contribution_share=None,
                        first_half_mean_rank_ic=None,
                        second_half_mean_rank_ic=None,
                        bucket_monotonic_spearman=None,
                        bucket_top_minus_bottom=None,
                    )
                )

    captured = []

    def capture(values):
        captured.append(dict(values))
        return dict(values)

    monkeypatch.setattr(service, "calculate_holm_adjustment", capture)

    service._build_decisions(tuple(results))

    assert sorted(len(item) for item in captured) == [2, 4]
    assert all(value == 1.0 for family in captured for value in family.values())


def test_v2_report_binds_separate_sources_and_exact_input_collections(
    monkeypatch,
) -> None:
    protocol = quant_research_factor_screening_protocol_v2()
    sessions = (date(2025, 8, 1), date(2025, 8, 4))
    payload = protocol.model_dump(mode="python")
    payload.update(
        minimum_instruments_per_session=5,
        minimum_primary_sessions=1,
        minimum_chronological_half_sessions=1,
        maximum_absolute_session_contribution_share="0.6000000000",
        bootstrap_replicates=1000,
        development_declared_path_count=12,
        development_declared_session_count=2,
        first_development_signal_session=sessions[0],
        last_development_signal_session=sessions[-1],
        formal_hypotheses=protocol.formal_hypotheses,
    )
    patched_protocol = SimpleNamespace(**payload)
    monkeypatch.setattr(
        service,
        "quant_research_factor_screening_protocol_v2",
        lambda: patched_protocol,
    )
    monkeypatch.setattr(
        result_contract,
        "quant_research_factor_screening_protocol_v2",
        lambda: patched_protocol,
    )

    observations = []
    controls = []
    labels = []
    control_values = (0.000, 0.020, 0.005, 0.025, 0.010, 0.015)
    for session_index, session in enumerate(sessions):
        for item_index in range(6):
            instrument_id = UUID(int=1 + session_index * 6 + item_index)
            factor = Decimal(item_index + 1) / Decimal("100")
            observation = build_quant_research_factor_observation_v2(
                catalog_fingerprint=protocol.catalog_fingerprint,
                as_of_session=session,
                instrument_id=instrument_id,
                display_ticker=f"T{session_index}{item_index}",
                source_min_session=session - timedelta(days=180),
                source_max_session=session,
                source_eod_fingerprint="2" * 64,
                source_adjustment_fingerprint="3" * 64,
                factor_values=tuple(
                    QuantResearchFactorValueV2(
                        factor_id=factor_id,
                        factor_definition_fingerprint=(
                            factor_definition_v2_fingerprint(factor_id)
                        ),
                        availability=QuantResearchFactorAvailabilityV2.AVAILABLE,
                        value=f"{factor:.10f}",
                        reason_codes=(),
                    )
                    for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
                ),
            )
            observations.append(observation)
            controls.append(
                build_factor_screening_control_v2(
                    protocol_fingerprint=protocol.logical_fingerprint,
                    observation_fingerprint=observation.logical_fingerprint,
                    signal_session=session,
                    instrument_id=instrument_id,
                    factor_definition_fingerprint=(
                        protocol.incremental_baseline_definition_fingerprint
                    ),
                    available=True,
                    value=f"{control_values[item_index]:.10f}",
                    source_min_session=session - timedelta(days=30),
                    source_max_session=session,
                    source_eod_fingerprint="2" * 64,
                    source_action_fingerprint="5" * 64,
                    source_adjustment_fingerprint="6" * 64,
                )
            )
            outcome = factor
            exit_price = Decimal("10") * (Decimal("1") + outcome)
            for horizon in (1, 3, 5):
                path = tuple(
                    session + timedelta(days=offset)
                    for offset in range(1, horizon + 1)
                )
                labels.append(
                    build_factor_screening_label_v2(
                        protocol_fingerprint=protocol.logical_fingerprint,
                        catalog_fingerprint=protocol.catalog_fingerprint,
                        observation_fingerprint=observation.logical_fingerprint,
                        signal_session=session,
                        instrument_id=instrument_id,
                        display_ticker=observation.display_ticker,
                        horizon_sessions=horizon,
                        expected_entry_session=path[0],
                        expected_exit_session=path[-1],
                        expected_path_sessions=path,
                        split_basis_session=session + timedelta(days=5),
                        state=(
                            QuantResearchFactorScreeningLabelState.OBSERVED_EOD_EXACT
                        ),
                        entry_price_usd="10.0000000000",
                        exit_price_lower_usd=f"{exit_price:.10f}",
                        exit_price_upper_usd=f"{exit_price:.10f}",
                        underlying_price_return_lower=f"{outcome:.10f}",
                        underlying_price_return_upper=f"{outcome:.10f}",
                        benchmark_price_return="0.0000000000",
                        relative_to_benchmark_return_lower=f"{outcome:.10f}",
                        relative_to_benchmark_return_upper=f"{outcome:.10f}",
                        maximum_favorable_excursion=f"{outcome:.10f}",
                        maximum_adverse_excursion="0.0000000000",
                        source_eod_fingerprint="4" * 64,
                        source_action_fingerprint="5" * 64,
                        source_adjustment_fingerprint="6" * 64,
                        reason_codes=(),
                    )
                )

    report = service.build_quant_research_factor_screening_report_v2(
        observations=tuple(observations),
        controls=tuple(controls),
        labels=tuple(labels),
        implementation_revision="a" * 40,
        created_at=datetime(2026, 9, 15, tzinfo=UTC),
        source_eod_fingerprint="2" * 64,
        source_membership_fingerprint="8" * 64,
        source_cohort_diagnostics_fingerprint=(
            quant_research_factor_screening_protocol_v1().source_diagnostics_fingerprint
        ),
        source_cohort_diagnostics_sha256=(
            quant_research_factor_screening_protocol_v1().source_diagnostics_sha256
        ),
        source_cohort_membership_fingerprint="d" * 64,
        factor_source_action_fingerprint="7" * 64,
        factor_source_adjustment_fingerprint="3" * 64,
        control_source_action_fingerprint="5" * 64,
        control_source_adjustment_fingerprint="6" * 64,
        label_source_action_fingerprint="5" * 64,
        label_source_adjustment_fingerprint="6" * 64,
        factor_calculation_code_sha256="9" * 64,
        control_calculation_code_sha256="a" * 64,
        label_code_sha256="b" * 64,
        screening_code_sha256="c" * 64,
    )

    assert report.observation_count == 12
    assert report.control_count == 12
    assert report.label_count == 36
    assert report.factor_source_action_fingerprint == "7" * 64
    assert report.control_source_action_fingerprint == "5" * 64
    assert report.label_source_action_fingerprint == "5" * 64
    assert len(
        {
            report.observation_collection_fingerprint,
            report.control_collection_fingerprint,
            report.label_collection_fingerprint,
        }
    ) == 3
