from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from tip_api.contracts.analytics.v1.quant_research_factor_catalog import (
    QUANT_RESEARCH_FACTOR_ORDER,
    QuantResearchFactorAvailability,
)
from tip_api.services.quant_research_factor_values import (
    QuantResearchFactorBar,
    QuantResearchFactorCalculationError,
    calculate_quant_research_factor_values,
)


def _series(
    *,
    daily_step: str,
    spread: str = "2",
    volume_step: str = "0",
) -> tuple[QuantResearchFactorBar, ...]:
    start = date(2026, 1, 2)
    step = Decimal(daily_step)
    half_spread = Decimal(spread) / Decimal(2)
    return tuple(
        QuantResearchFactorBar(
            session=start + timedelta(days=index),
            open=Decimal("100") + step * Decimal(index),
            high=Decimal("100") + step * Decimal(index) + half_spread,
            low=Decimal("100") + step * Decimal(index) - half_spread,
            close=Decimal("100") + step * Decimal(index),
            volume=Decimal("1000000") + Decimal(volume_step) * Decimal(index),
        )
        for index in range(21)
    )


def test_calculates_all_registered_factors_in_exact_order() -> None:
    values = calculate_quant_research_factor_values(
        stock_series=_series(daily_step="1", volume_step="10000"),
        benchmark_series=_series(daily_step="0.25"),
    )
    by_id = {item.factor_id: item for item in values}

    assert tuple(item.factor_id for item in values) == QUANT_RESEARCH_FACTOR_ORDER
    assert all(item.availability == QuantResearchFactorAvailability.AVAILABLE for item in values)
    assert Decimal(by_id["relative_return_spy_20s"].value) > 0
    assert by_id["positive_session_share_10s"].value == "1.0000000000"
    assert by_id["signed_path_efficiency_10s"].value == "1.0000000000"
    assert by_id["rolling_maximum_drawdown_10s"].value == "0.0000000000"
    assert by_id["close_location_value_1s"].value == "0.5000000000"


def test_prior_atr_ends_at_t_minus_one_and_excludes_signal_range() -> None:
    stock = list(_series(daily_step="0", spread="2"))
    current = stock[-1]
    stock[-1] = QuantResearchFactorBar(
        session=current.session,
        open=current.open,
        high=Decimal("150"),
        low=Decimal("50"),
        close=current.close,
        volume=current.volume,
    )
    values = calculate_quant_research_factor_values(
        stock_series=tuple(stock),
        benchmark_series=_series(daily_step="0.25"),
    )
    by_id = {item.factor_id: item for item in values}

    assert by_id["prior_atr_ratio_5_to_14"].value == "1.0000000000"
    assert by_id["absolute_overnight_gap_atr14"].value == "0.0000000000"
    assert by_id["close_location_value_1s"].value == "0.5000000000"


def test_denominator_failures_are_explicit_and_do_not_zero_fill_other_factors() -> None:
    flat = _series(daily_step="0", spread="0")
    values = calculate_quant_research_factor_values(
        stock_series=flat,
        benchmark_series=_series(daily_step="0.25"),
    )
    by_id = {item.factor_id: item for item in values}

    assert by_id["signed_path_efficiency_10s"].availability == QuantResearchFactorAvailability.UNAVAILABLE
    assert by_id["signed_path_efficiency_10s"].reason_codes == ("zero_absolute_return_sum",)
    assert by_id["prior_atr_ratio_5_to_14"].reason_codes == ("zero_prior_atr14",)
    assert by_id["close_location_value_1s"].reason_codes == ("zero_signal_session_range",)
    assert by_id["positive_session_share_10s"].value == "0.0000000000"
    assert by_id["rolling_maximum_drawdown_10s"].value == "0.0000000000"


def test_rejects_misaligned_stock_and_benchmark_sessions() -> None:
    benchmark = tuple(
        QuantResearchFactorBar(
            session=item.session + timedelta(days=1),
            open=item.open,
            high=item.high,
            low=item.low,
            close=item.close,
            volume=item.volume,
        )
        for item in _series(daily_step="0.25")
    )

    with pytest.raises(QuantResearchFactorCalculationError, match="not exactly aligned"):
        calculate_quant_research_factor_values(
            stock_series=_series(daily_step="1"),
            benchmark_series=benchmark,
        )


def test_benchmark_failure_only_quarantines_relative_factors() -> None:
    values = calculate_quant_research_factor_values(
        stock_series=_series(daily_step="1"),
        benchmark_series=_series(daily_step="0.25")[:-1],
    )
    by_id = {item.factor_id: item for item in values}

    assert by_id["relative_return_spy_20s"].reason_codes == (
        "benchmark_source_session_count",
    )
    assert by_id["relative_return_acceleration_5_vs_prior15"].availability == (
        QuantResearchFactorAvailability.UNAVAILABLE
    )
    assert by_id["positive_session_share_10s"].availability == (
        QuantResearchFactorAvailability.AVAILABLE
    )
