from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.equity_execution_cost import (
    EquityExecutionCostAssumptionV1,
    ExecutionCapacityStatus,
    ExecutionCostEvidenceStatus,
    build_equity_execution_cost_assumption,
    build_equity_execution_cost_input,
)
from tip_api.services.equity_execution_cost import (
    estimate_equity_execution_cost,
)


INSTRUMENT_ID = UUID("11111111-1111-4111-8111-111111111111")
CALCULATED_AT = datetime(2026, 9, 9, 1, 30, tzinfo=UTC)


def _scenario_assumption(
    **overrides: object,
) -> EquityExecutionCostAssumptionV1:
    values: dict[str, object] = {
        "scenario_id": "baseline-liquid-equity-v1",
        "commission_bps_per_side": "1",
        "half_spread_bps_per_side": "5",
        "delay_slippage_bps_per_side": "2",
        "impact_coefficient": "1",
        "maximum_participation_rate": "0.05",
        "evidence_status": ExecutionCostEvidenceStatus.SCENARIO_ONLY,
        "quoted_spread_evidence_fingerprint": None,
        "impact_calibration_evidence_fingerprint": None,
        "limitation_codes": (
            "quoted_spread_unavailable",
            "impact_not_calibrated",
        ),
    }
    values.update(overrides)
    return build_equity_execution_cost_assumption(**values)


def _input(**overrides: object):
    values: dict[str, object] = {
        "instrument_id": INSTRUMENT_ID,
        "session": date(2026, 9, 4),
        "order_notional_usd": "1000000",
        "median_dollar_volume_20_usd": "100000000",
        "daily_return_volatility_20": "0.02",
        "source_eod_fingerprint": "a" * 64,
        "source_data_cutoff": datetime(2026, 9, 4, 21, tzinfo=UTC),
        "calculated_at": CALCULATED_AT,
    }
    values.update(overrides)
    return build_equity_execution_cost_input(**values)


def test_scenario_cost_arithmetic_is_deterministic_and_non_authoritative() -> None:
    assumption = _scenario_assumption()
    input_record = _input()

    first = estimate_equity_execution_cost(
        input_record=input_record,
        assumption=assumption,
    )
    second = estimate_equity_execution_cost(
        input_record=input_record,
        assumption=assumption,
    )

    assert first == second
    assert first.participation_rate == Decimal("0.0100000000")
    assert first.market_impact_bps_per_side == Decimal("20.000000")
    assert first.total_estimated_bps_per_side == Decimal("28.000000")
    assert first.total_estimated_cost_usd_per_side == Decimal("2800.00")
    assert (
        first.capacity_status
        is ExecutionCapacityStatus.WITHIN_PARTICIPATION_LIMIT
    )
    assert first.evidence_status is ExecutionCostEvidenceStatus.SCENARIO_ONLY
    assert first.estimated_not_realized is True
    assert first.equity_execution_only is True
    assert first.research_admission_authorized is False
    assert first.option_execution_cost_authorized is False
    assert first.performance_claim_authorized is False


def test_cost_and_capacity_increase_with_order_participation() -> None:
    assumption = _scenario_assumption(maximum_participation_rate="0.01")
    smaller = estimate_equity_execution_cost(
        input_record=_input(order_notional_usd="250000"),
        assumption=assumption,
    )
    larger = estimate_equity_execution_cost(
        input_record=_input(order_notional_usd="2000000"),
        assumption=assumption,
    )

    assert larger.market_impact_bps_per_side > smaller.market_impact_bps_per_side
    assert (
        larger.total_estimated_cost_usd_per_side
        > smaller.total_estimated_cost_usd_per_side
    )
    assert (
        smaller.capacity_status
        is ExecutionCapacityStatus.WITHIN_PARTICIPATION_LIMIT
    )
    assert (
        larger.capacity_status
        is ExecutionCapacityStatus.ABOVE_PARTICIPATION_LIMIT
    )
    assert "participation_limit_exceeded" in larger.limitation_codes
    assert "participation_limit_exceeded" not in smaller.limitation_codes


@pytest.mark.parametrize(
    ("status", "quoted", "calibration", "limitations"),
    (
        (
            ExecutionCostEvidenceStatus.SCENARIO_ONLY,
            "b" * 64,
            None,
            ("quoted_spread_unavailable", "impact_not_calibrated"),
        ),
        (
            ExecutionCostEvidenceStatus.OBSERVED_SPREAD,
            None,
            None,
            ("impact_not_calibrated",),
        ),
        (
            ExecutionCostEvidenceStatus.OBSERVED_SPREAD_AND_CALIBRATED_IMPACT,
            "b" * 64,
            "c" * 64,
            ("impact_not_calibrated",),
        ),
    ),
)
def test_evidence_status_cannot_overstate_available_evidence(
    status: ExecutionCostEvidenceStatus,
    quoted: str | None,
    calibration: str | None,
    limitations: tuple[str, ...],
) -> None:
    with pytest.raises(ValidationError, match="cost evidence"):
        _scenario_assumption(
            evidence_status=status,
            quoted_spread_evidence_fingerprint=quoted,
            impact_calibration_evidence_fingerprint=calibration,
            limitation_codes=limitations,
        )


def test_observed_and_calibrated_states_require_exact_evidence_bindings() -> None:
    observed = _scenario_assumption(
        evidence_status=ExecutionCostEvidenceStatus.OBSERVED_SPREAD,
        quoted_spread_evidence_fingerprint="b" * 64,
        limitation_codes=("impact_not_calibrated",),
    )
    calibrated = _scenario_assumption(
        evidence_status=(
            ExecutionCostEvidenceStatus.OBSERVED_SPREAD_AND_CALIBRATED_IMPACT
        ),
        quoted_spread_evidence_fingerprint="b" * 64,
        impact_calibration_evidence_fingerprint="c" * 64,
        limitation_codes=("historical_execution_sample_bounded",),
    )

    assert observed.evidence_status is ExecutionCostEvidenceStatus.OBSERVED_SPREAD
    assert calibrated.evidence_status is (
        ExecutionCostEvidenceStatus.OBSERVED_SPREAD_AND_CALIBRATED_IMPACT
    )


@pytest.mark.parametrize(
    ("factory", "field_name"),
    (
        (
            lambda: _scenario_assumption(commission_bps_per_side=1.0),
            "commission_bps_per_side",
        ),
        (
            lambda: _input(order_notional_usd=1_000_000.0),
            "order_notional_usd",
        ),
    ),
)
def test_binary_floats_are_rejected(factory, field_name: str) -> None:
    with pytest.raises(ValidationError, match=field_name):
        factory()


def test_input_rejects_future_source_cutoff() -> None:
    with pytest.raises(ValidationError, match="precedes source cutoff"):
        _input(source_data_cutoff=datetime(2026, 9, 9, 2, tzinfo=UTC))


def test_tampered_fingerprint_fails_closed() -> None:
    assumption = _scenario_assumption()
    payload = assumption.model_dump(mode="json")
    payload["commission_bps_per_side"] = "2"

    with pytest.raises(ValidationError, match="fingerprint differs"):
        EquityExecutionCostAssumptionV1.model_validate(payload)
