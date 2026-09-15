from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from tip_api.contracts.analytics.v1.quant_research_market_state_vector import (
    QuantResearchMarketStateAvailability,
)
from tip_api.services.quant_research_market_state_vector import (
    QuantResearchMarketStateBarV1,
    QuantResearchMarketStateCalculationError,
    QuantResearchMarketStateMemberSeriesV1,
    calculate_quant_research_market_state_vector_v1,
)


SESSIONS = tuple(date(2026, 1, 1) + timedelta(days=index) for index in range(21))


def _bars(start: str, step: str):
    first = Decimal(start)
    increment = Decimal(step)
    return tuple(
        QuantResearchMarketStateBarV1(
            session=session,
            close=first + increment * index,
        )
        for index, session in enumerate(SESSIONS)
    )


def _benchmarks():
    return {
        "SPY": _bars("100", "1"),
        "QQQ": _bars("100", "2"),
        "IWM": _bars("100", "0.5"),
        "DIA": _bars("100", "0.8"),
    }


def _members(count: int):
    return tuple(
        QuantResearchMarketStateMemberSeriesV1(
            instrument_id=f"instrument-{index:04d}",
            bars=_bars("100", "1" if index < (count * 2 // 3) else "-0.5"),
        )
        for index in range(count)
    )


def test_market_state_calculator_emits_ten_outcome_blind_values() -> None:
    result = calculate_quant_research_market_state_vector_v1(
        benchmark_series=_benchmarks(),
        member_series=_members(600),
        declared_member_count=600,
    )
    by_id = {item.metric_id: item for item in result}

    assert len(result) == 10
    assert all(
        item.availability is QuantResearchMarketStateAvailability.AVAILABLE
        for item in result
    )
    assert by_id["broad_etf_above_sma20_share"].value == "1.0000000000"
    assert (
        by_id["reconstructed_member_positive_log_return_5s_share"].value
        == "0.6666666667"
    )
    assert by_id["reconstructed_member_log_return_dispersion_5s"].value is not None


def test_market_state_calculator_keeps_low_coverage_cross_section_unavailable() -> None:
    result = calculate_quant_research_market_state_vector_v1(
        benchmark_series=_benchmarks(),
        member_series=_members(400),
        declared_member_count=600,
    )

    assert all(
        item.availability is QuantResearchMarketStateAvailability.AVAILABLE
        for item in result[:6]
    )
    assert all(
        item.availability is QuantResearchMarketStateAvailability.UNAVAILABLE
        and "complete_member_count_below_floor" in item.reason_codes
        and "complete_member_coverage_below_floor" in item.reason_codes
        for item in result[6:]
    )


def test_market_state_calculator_rejects_misaligned_or_unsorted_inputs() -> None:
    benchmarks = _benchmarks()
    benchmarks["QQQ"] = tuple(reversed(benchmarks["QQQ"]))
    with pytest.raises(QuantResearchMarketStateCalculationError):
        calculate_quant_research_market_state_vector_v1(
            benchmark_series=benchmarks,
            member_series=_members(600),
            declared_member_count=600,
        )
