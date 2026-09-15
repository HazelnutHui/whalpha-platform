from __future__ import annotations

from decimal import Decimal

import pytest

from tip_api.services.quant_research_factor_screening import (
    QuantResearchFactorScreeningError,
    calculate_average_ranks,
    calculate_block_bootstrap,
    calculate_holm_adjustment,
    calculate_partial_spearman,
    calculate_spearman,
)


def test_average_ranks_and_spearman_preserve_ties_and_direction() -> None:
    assert calculate_average_ranks((2.0, 1.0, 2.0, 4.0)) == (
        2.5,
        1.0,
        2.5,
        4.0,
    )
    assert calculate_spearman((1.0, 2.0, 3.0), (3.0, 2.0, 1.0)) == pytest.approx(-1)


def test_partial_spearman_removes_linear_rank_baseline() -> None:
    factor = (1.0, 2.0, 3.0, 4.0, 5.0)
    baseline = (1.0, 3.0, 2.0, 5.0, 4.0)
    target = (2.0, 1.0, 4.0, 3.0, 5.0)

    result = calculate_partial_spearman(factor, target, baseline)

    assert -1 <= result <= 1
    with pytest.raises(QuantResearchFactorScreeningError):
        calculate_partial_spearman(factor, target, (1.0,) * 5)


def test_holm_adjustment_is_ordered_monotone_and_capped() -> None:
    result = calculate_holm_adjustment({"a": 0.01, "b": 0.03, "c": 0.2})

    assert result == pytest.approx({"a": 0.03, "b": 0.06, "c": 0.2})


def test_block_bootstrap_is_deterministic_and_directional() -> None:
    values = tuple(float(Decimal(index) / Decimal("1000")) for index in range(1, 81))

    first = calculate_block_bootstrap(values, seed_material="registered-test")
    second = calculate_block_bootstrap(values, seed_material="registered-test")

    assert first == second
    assert first[0] > 0
    assert 0 <= first[2] <= 1
