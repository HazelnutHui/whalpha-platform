"""Deterministic equity execution-cost scenario mechanics."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext

from tip_api.contracts.analytics.v1.equity_execution_cost import (
    EquityExecutionCostAssumptionV1,
    EquityExecutionCostEstimateV1,
    EquityExecutionCostInputV1,
    ExecutionCapacityStatus,
    build_equity_execution_cost_estimate,
)


BPS_QUANTUM = Decimal("0.000001")
PARTICIPATION_QUANTUM = Decimal("0.0000000001")
USD_QUANTUM = Decimal("0.01")


def estimate_equity_execution_cost(
    *,
    input_record: EquityExecutionCostInputV1,
    assumption: EquityExecutionCostAssumptionV1,
) -> EquityExecutionCostEstimateV1:
    """Estimate one side; this is a scenario, not realized execution evidence."""

    with localcontext() as context:
        context.prec = 56
        context.rounding = ROUND_HALF_EVEN
        raw_participation = (
            input_record.order_notional_usd
            / input_record.median_dollar_volume_20_usd
        )
        raw_impact_bps = (
            assumption.impact_coefficient
            * input_record.daily_return_volatility_20
            * raw_participation.sqrt()
            * Decimal("10000")
        )
    participation = raw_participation.quantize(PARTICIPATION_QUANTUM)
    market_impact = raw_impact_bps.quantize(BPS_QUANTUM)
    commission = assumption.commission_bps_per_side.quantize(BPS_QUANTUM)
    half_spread = assumption.half_spread_bps_per_side.quantize(BPS_QUANTUM)
    delay = assumption.delay_slippage_bps_per_side.quantize(BPS_QUANTUM)
    total_bps = (commission + half_spread + delay + market_impact).quantize(
        BPS_QUANTUM
    )
    total_usd = (
        input_record.order_notional_usd * total_bps / Decimal("10000")
    ).quantize(USD_QUANTUM)
    capacity = (
        ExecutionCapacityStatus.WITHIN_PARTICIPATION_LIMIT
        if participation <= assumption.maximum_participation_rate
        else ExecutionCapacityStatus.ABOVE_PARTICIPATION_LIMIT
    )
    limitations = set(assumption.limitation_codes)
    limitations.update(
        {
            "daily_dollar_volume_is_capacity_proxy",
            "intraday_volume_profile_unavailable",
            "estimate_is_not_realized_execution",
            "borrow_financing_and_regulatory_fees_excluded",
            "options_execution_excluded",
        }
    )
    if capacity is ExecutionCapacityStatus.ABOVE_PARTICIPATION_LIMIT:
        limitations.add("participation_limit_exceeded")
    return build_equity_execution_cost_estimate(
        input_logical_fingerprint=input_record.logical_fingerprint,
        assumption_logical_fingerprint=assumption.logical_fingerprint,
        instrument_id=input_record.instrument_id,
        session=input_record.session,
        order_notional_usd=input_record.order_notional_usd,
        median_dollar_volume_20_usd=(
            input_record.median_dollar_volume_20_usd
        ),
        daily_return_volatility_20=input_record.daily_return_volatility_20,
        participation_rate=participation,
        maximum_participation_rate=assumption.maximum_participation_rate,
        commission_bps_per_side=commission,
        half_spread_bps_per_side=half_spread,
        delay_slippage_bps_per_side=delay,
        market_impact_bps_per_side=market_impact,
        total_estimated_bps_per_side=total_bps,
        total_estimated_cost_usd_per_side=total_usd,
        capacity_status=capacity,
        evidence_status=assumption.evidence_status,
        limitation_codes=tuple(limitations),
        calculated_at=input_record.calculated_at,
        estimated_not_realized=True,
        equity_execution_only=True,
        research_admission_authorized=False,
        option_execution_cost_authorized=False,
        performance_claim_authorized=False,
    )
