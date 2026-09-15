from __future__ import annotations

from math import isclose

import numpy as np

from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
    QuantResearchFactorAvailabilityV2,
)
from tip_api.services.quant_research_factor_matrix_v2 import (
    calculate_quant_research_factor_matrix_v2,
)
from tip_api.services.quant_research_factor_values_v2 import (
    calculate_quant_research_factor_values_v2,
)
from tests.services.test_quant_research_factor_values_v2 import _series


def test_vectorized_v2_matrix_matches_decimal_reference_calculator() -> None:
    stock = _series(stock=True)
    benchmark = _series(stock=False)
    reference = calculate_quant_research_factor_values_v2(
        stock_series=stock,
        benchmark_series=benchmark,
    )
    matrix = calculate_quant_research_factor_matrix_v2(
        stock_series=(stock,),
        benchmark_series=benchmark,
    )

    assert tuple(matrix.factor_values) == QUANT_RESEARCH_FACTOR_V2_ORDER
    for item in reference:
        assert item.availability is QuantResearchFactorAvailabilityV2.AVAILABLE
        assert matrix.reason_codes[item.factor_id] == ((),)
        assert isclose(
            float(matrix.factor_values[item.factor_id][0]),
            float(item.value),
            rel_tol=0.0,
            abs_tol=5e-10,
        )


def test_vectorized_v2_matrix_preserves_factor_specific_unavailability() -> None:
    stock = _series(stock=True, zero_volume_at=120)
    matrix = calculate_quant_research_factor_matrix_v2(
        stock_series=(stock,),
        benchmark_series=_series(stock=False),
    )

    assert np.isnan(matrix.factor_values["amihud_illiquidity_20s"][0])
    assert matrix.reason_codes["amihud_illiquidity_20s"] == (
        ("zero_dollar_volume",),
    )
    assert np.isfinite(matrix.factor_values["short_term_relative_reversal_5s"][0])


def test_vectorized_v2_matrix_handles_an_empty_valid_cross_section() -> None:
    matrix = calculate_quant_research_factor_matrix_v2(
        stock_series=(),
        benchmark_series=_series(stock=False),
    )

    assert matrix.instrument_count == 0
    assert all(values.shape == (0,) for values in matrix.factor_values.values())
