"""Vectorized outcome-blind Factor Catalog V2 calculation for Dell research."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
)
from tip_api.services.quant_research_factor_values_v2 import (
    QuantResearchFactorBarV2,
    quant_research_factor_series_issue_v2,
)


FloatArray = NDArray[np.float64]


class QuantResearchFactorMatrixV2Error(ValueError):
    """Raised when a vectorized V2 panel violates the frozen calculation shape."""


@dataclass(frozen=True, slots=True)
class QuantResearchFactorMatrixV2:
    factor_values: dict[str, FloatArray]
    reason_codes: dict[str, tuple[tuple[str, ...], ...]]
    instrument_count: int


def calculate_quant_research_factor_matrix_v2(
    *,
    stock_series: tuple[tuple[QuantResearchFactorBarV2, ...], ...],
    benchmark_series: tuple[QuantResearchFactorBarV2, ...],
) -> QuantResearchFactorMatrixV2:
    """Calculate a complete valid-stock cross-section without any outcomes."""

    benchmark_issue = quant_research_factor_series_issue_v2(
        benchmark_series, label="benchmark"
    )
    if benchmark_issue is not None:
        raise QuantResearchFactorMatrixV2Error(benchmark_issue)
    benchmark_sessions = tuple(item.session for item in benchmark_series)
    for series in stock_series:
        issue = quant_research_factor_series_issue_v2(series, label="stock")
        if issue is not None:
            raise QuantResearchFactorMatrixV2Error(issue)
        if tuple(item.session for item in series) != benchmark_sessions:
            raise QuantResearchFactorMatrixV2Error(
                "stock and benchmark sessions are not exactly aligned"
            )

    count = len(stock_series)
    values = {
        factor_id: np.full(count, np.nan, dtype=np.float64)
        for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
    }
    reasons: dict[str, list[tuple[str, ...]]] = {
        factor_id: [()] * count for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
    }
    if count == 0:
        return QuantResearchFactorMatrixV2(
            factor_values=values,
            reason_codes={key: tuple(item) for key, item in reasons.items()},
            instrument_count=0,
        )

    close = np.asarray(
        [[float(bar.close) for bar in series] for series in stock_series],
        dtype=np.float64,
    )
    open_price = np.asarray(
        [[float(bar.open) for bar in series] for series in stock_series],
        dtype=np.float64,
    )
    volume = np.asarray(
        [[float(bar.volume) for bar in series] for series in stock_series],
        dtype=np.float64,
    )
    benchmark_close = np.asarray(
        [float(bar.close) for bar in benchmark_series], dtype=np.float64
    )
    benchmark_open = np.asarray(
        [float(bar.open) for bar in benchmark_series], dtype=np.float64
    )

    values["medium_term_relative_momentum_126s_skip5"] = (
        np.log(close[:, 121] / close[:, 0])
        - np.log(benchmark_close[121] / benchmark_close[0])
    )
    values["short_term_relative_reversal_5s"] = -(
        np.log(close[:, 126] / close[:, 121])
        - np.log(benchmark_close[126] / benchmark_close[121])
    )
    values["intraday_relative_pressure_reversal_5s"] = -(
        np.log(close[:, 122:127] / open_price[:, 122:127]).sum(axis=1)
        - np.log(benchmark_close[122:127] / benchmark_open[122:127]).sum()
    )
    values["overnight_relative_persistence_5s"] = (
        np.log(open_price[:, 122:127] / close[:, 121:126]).sum(axis=1)
        - np.log(benchmark_open[122:127] / benchmark_close[121:126]).sum()
    )

    stock_returns = np.log(close[:, 67:127] / close[:, 66:126])
    benchmark_returns = np.log(benchmark_close[67:127] / benchmark_close[66:126])
    down_mask = benchmark_returns < 0.0
    if int(down_mask.sum()) >= 12:
        values["down_market_relative_resilience_60s"] = (
            stock_returns[:, down_mask] - benchmark_returns[down_mask]
        ).mean(axis=1)
    else:
        reasons["down_market_relative_resilience_60s"] = [
            ("fewer_than_twelve_negative_benchmark_sessions",)
        ] * count

    dollar_volume = close[:, 107:127] * volume[:, 107:127]
    zero_dollar_volume = np.any(dollar_volume == 0.0, axis=1)
    amihud = (
        1_000_000.0
        * (
            np.abs(np.log(close[:, 107:127] / close[:, 106:126]))
            / np.where(dollar_volume == 0.0, 1.0, dollar_volume)
        ).mean(axis=1)
    )
    amihud[zero_dollar_volume] = np.nan
    values["amihud_illiquidity_20s"] = amihud
    for index in np.flatnonzero(zero_dollar_volume):
        reasons["amihud_illiquidity_20s"][int(index)] = ("zero_dollar_volume",)

    benchmark_mean = benchmark_returns.mean()
    benchmark_centered = benchmark_returns - benchmark_mean
    benchmark_variance_sum = float(np.square(benchmark_centered).sum())
    if benchmark_variance_sum == 0.0:
        reasons["single_index_residual_volatility_60s"] = [
            ("zero_benchmark_return_variance",)
        ] * count
    else:
        stock_mean = stock_returns.mean(axis=1)
        stock_centered = stock_returns - stock_mean[:, None]
        beta = (stock_centered * benchmark_centered).sum(axis=1) / (
            benchmark_variance_sum
        )
        alpha = stock_mean - beta * benchmark_mean
        residual = stock_returns - alpha[:, None] - beta[:, None] * benchmark_returns
        values["single_index_residual_volatility_60s"] = np.sqrt(252.0) * np.sqrt(
            np.square(residual).sum(axis=1) / 58.0
        )

    relative_returns = stock_returns - benchmark_returns
    downside = np.minimum(relative_returns, 0.0)
    values["relative_downside_semideviation_60s"] = np.sqrt(252.0) * np.sqrt(
        np.square(downside).mean(axis=1)
    )

    frozen_reasons = {key: tuple(item) for key, item in reasons.items()}
    for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER:
        factor = values[factor_id]
        if factor.shape != (count,):
            raise QuantResearchFactorMatrixV2Error("factor matrix shape differs")
        for index, value in enumerate(factor):
            has_reason = bool(frozen_reasons[factor_id][index])
            if bool(np.isfinite(value)) == has_reason:
                raise QuantResearchFactorMatrixV2Error(
                    "factor matrix availability and reason differ"
                )
    return QuantResearchFactorMatrixV2(
        factor_values=values,
        reason_codes=frozen_reasons,
        instrument_count=count,
    )
