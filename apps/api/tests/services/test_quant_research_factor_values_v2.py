from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, getcontext

from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
    QuantResearchFactorAvailabilityV2,
)
from tip_api.services.quant_research_factor_values_v2 import (
    QuantResearchFactorBarV2,
    calculate_quant_research_factor_values_v2,
)


def _series(*, stock: bool, zero_volume_at: int | None = None):
    result = []
    close = Decimal("100")
    for index in range(127):
        if index:
            cycle = (index % 7) - 3
            increment = Decimal(cycle) / Decimal("1000")
            if stock:
                increment += Decimal("0.0003")
                if index >= 122:
                    increment -= Decimal("0.002")
            close *= Decimal(1) + increment
        open_price = close * (
            Decimal("0.999") if (index + int(stock)) % 2 else Decimal("1.001")
        )
        high = max(open_price, close) * Decimal("1.002")
        low = min(open_price, close) * Decimal("0.998")
        result.append(
            QuantResearchFactorBarV2(
                session=date(2026, 1, 1) + timedelta(days=index),
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=(
                    Decimal(0)
                    if zero_volume_at == index
                    else Decimal("1000000") + Decimal(index * 100)
                ),
            )
        )
    return tuple(result)


def test_v2_calculator_returns_all_factors_in_frozen_order() -> None:
    values = calculate_quant_research_factor_values_v2(
        stock_series=_series(stock=True),
        benchmark_series=_series(stock=False),
    )

    assert tuple(item.factor_id for item in values) == QUANT_RESEARCH_FACTOR_V2_ORDER
    assert all(
        item.availability is QuantResearchFactorAvailabilityV2.AVAILABLE
        for item in values
    )


def test_v2_calculator_quarantines_only_amihud_when_dollar_volume_is_zero() -> None:
    values = calculate_quant_research_factor_values_v2(
        stock_series=_series(stock=True, zero_volume_at=120),
        benchmark_series=_series(stock=False),
    )
    by_id = {item.factor_id: item for item in values}

    assert by_id["amihud_illiquidity_20s"].availability is (
        QuantResearchFactorAvailabilityV2.UNAVAILABLE
    )
    assert by_id["amihud_illiquidity_20s"].reason_codes == ("zero_dollar_volume",)
    assert by_id["short_term_relative_reversal_5s"].availability is (
        QuantResearchFactorAvailabilityV2.AVAILABLE
    )


def test_v2_calculator_refuses_an_extra_future_session() -> None:
    stock = _series(stock=True)
    benchmark = _series(stock=False)
    values = calculate_quant_research_factor_values_v2(
        stock_series=stock + (stock[-1],),
        benchmark_series=benchmark + (benchmark[-1],),
    )

    assert all(
        item.availability is QuantResearchFactorAvailabilityV2.UNAVAILABLE
        and item.reason_codes == ("stock_source_session_count",)
        for item in values
    )


def test_v2_calculator_is_independent_of_ambient_decimal_precision() -> None:
    original = getcontext().prec
    stock = _series(stock=True)
    benchmark = _series(stock=False)
    try:
        getcontext().prec = 12
        low_precision = calculate_quant_research_factor_values_v2(
            stock_series=stock,
            benchmark_series=benchmark,
        )
        getcontext().prec = 42
        high_precision = calculate_quant_research_factor_values_v2(
            stock_series=stock,
            benchmark_series=benchmark,
        )
    finally:
        getcontext().prec = original

    assert low_precision == high_precision
