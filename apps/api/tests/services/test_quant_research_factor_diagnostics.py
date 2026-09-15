from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_factor_catalog import (
    QUANT_RESEARCH_FACTOR_ORDER,
    QuantResearchFactorAvailability,
    QuantResearchFactorValueV1,
    build_quant_research_factor_observation,
    factor_definition_fingerprint,
    quant_research_factor_catalog_v1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_diagnostics import (
    QuantResearchFactorDiagnosticsV1,
    factor_diagnostics_fingerprint,
)
from tip_api.services.quant_research_factor_diagnostics import (
    QuantResearchFactorDiagnosticsAccumulator,
    QuantResearchFactorDiagnosticsError,
)


def _value(factor_id: str, raw: Decimal) -> QuantResearchFactorValueV1:
    return QuantResearchFactorValueV1(
        factor_id=factor_id,
        factor_definition_fingerprint=factor_definition_fingerprint(factor_id),
        availability=QuantResearchFactorAvailability.AVAILABLE,
        value=format(raw.quantize(Decimal("0.0000000001")), "f"),
    )


def _unavailable(factor_id: str) -> QuantResearchFactorValueV1:
    return QuantResearchFactorValueV1(
        factor_id=factor_id,
        factor_definition_fingerprint=factor_definition_fingerprint(factor_id),
        availability=QuantResearchFactorAvailability.UNAVAILABLE,
        reason_codes=("zero_denominator",),
    )


def _observation(
    *,
    session: date,
    index: int,
    unavailable_factor: str | None = None,
) -> object:
    values = tuple(
        _unavailable(factor_id)
        if factor_id == unavailable_factor
        else _value(factor_id, Decimal(index) + Decimal(factor_index) / Decimal(100))
        for factor_index, factor_id in enumerate(QUANT_RESEARCH_FACTOR_ORDER)
    )
    return build_quant_research_factor_observation(
        catalog_fingerprint=quant_research_factor_catalog_v1().logical_fingerprint,
        calculation_version="quant-research-factor-calculation/1.0.0",
        as_of_session=session,
        instrument_id=UUID(f"00000000-0000-4000-8000-{index:012d}"),
        display_ticker=f"T{index}",
        membership_tier="reconstructed_latest_vintage_research_only",
        source_max_session=session,
        source_eod_fingerprint="3" * 64,
        source_adjustment_fingerprint="6" * 64,
        factor_values=values,
        contains_forward_outcomes=False,
        factor_screening_authorized=False,
        model_construction_authorized=False,
        candidate_activation_authorized=False,
    )


def _accumulator() -> QuantResearchFactorDiagnosticsAccumulator:
    return QuantResearchFactorDiagnosticsAccumulator(
        chronological_plan_fingerprint="1" * 64,
        source_population_fingerprint="2" * 64,
        source_eod_fingerprint="3" * 64,
        source_membership_fingerprint="4" * 64,
        source_action_fingerprint="5" * 64,
        source_adjustment_fingerprint="6" * 64,
        calculation_code_sha256="7" * 64,
        diagnostic_code_sha256="8" * 64,
        limitation_codes=(
            "reconstructed_membership_not_as_operated",
            "split_neutral_absence_unproven",
        ),
    )


def test_report_reconciles_coverage_missingness_and_is_deterministic() -> None:
    accumulator = _accumulator()
    first = date(2026, 1, 2)
    accumulator.add_session(
        as_of_session=first,
        observations=tuple(_observation(session=first, index=index) for index in range(30)),
    )
    second = first + timedelta(days=1)
    accumulator.add_session(
        as_of_session=second,
        observations=tuple(
            _observation(
                session=second,
                index=index,
                unavailable_factor=QUANT_RESEARCH_FACTOR_ORDER[0] if index == 0 else None,
            )
            for index in range(30)
        ),
    )

    report = accumulator.build()
    repeated = accumulator.build()
    first_coverage = report.factor_coverage[0]

    assert report == repeated
    assert report.session_count == 2
    assert report.expected_path_count == 60
    assert report.complete_factor_vector_count == 59
    assert report.incomplete_factor_vector_count == 1
    assert first_coverage.available_count == 59
    assert first_coverage.unavailable_count == 1
    assert first_coverage.unavailable_reason_counts[0].reason_code == "zero_denominator"
    assert len(report.session_availability) == 24
    assert len(report.pairwise_same_session_spearman) == 66
    assert report.contains_forward_outcomes is False
    assert report.factor_screening_authorized is False
    assert report.logical_fingerprint == factor_diagnostics_fingerprint(report)


def test_near_duplicate_rule_uses_all_four_frozen_conditions() -> None:
    accumulator = _accumulator()
    first = date(2025, 1, 2)
    for offset in range(60):
        session = first + timedelta(days=offset)
        accumulator.add_session(
            as_of_session=session,
            observations=tuple(
                _observation(session=session, index=index) for index in range(30)
            ),
        )
    report = accumulator.build()
    first_pair = report.pairwise_same_session_spearman[0]

    assert first_pair.eligible_session_count == 60
    assert first_pair.weighted_mean_spearman == "1.0000000000"
    assert first_pair.high_absolute_correlation_session_share == "1.0000000000"
    assert first_pair.dominant_sign_session_share == "1.0000000000"
    assert first_pair.near_duplicate is True
    assert len(report.near_duplicate_groups) == 1
    assert set(report.near_duplicate_groups[0].factor_ids) == set(QUANT_RESEARCH_FACTOR_ORDER)


def test_report_rejects_fingerprint_tampering() -> None:
    accumulator = _accumulator()
    session = date(2026, 1, 2)
    accumulator.add_session(
        as_of_session=session,
        observations=tuple(_observation(session=session, index=index) for index in range(30)),
    )
    payload = accumulator.build().model_dump(mode="json")
    payload["complete_factor_vector_count"] = 29
    payload["incomplete_factor_vector_count"] = 1

    with pytest.raises(ValidationError, match="fingerprint mismatch"):
        QuantResearchFactorDiagnosticsV1.model_validate(payload)


def test_accumulator_rejects_out_of_order_sessions() -> None:
    accumulator = _accumulator()
    session = date(2026, 1, 2)
    accumulator.add_session(as_of_session=session, observations=())

    with pytest.raises(QuantResearchFactorDiagnosticsError, match="strictly ordered"):
        accumulator.add_session(as_of_session=session, observations=())
