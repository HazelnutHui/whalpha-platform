from decimal import Decimal

import pytest

from tip_api.services.historical_adjustment_invariants import (
    FactorReconciliationStatus,
    ProviderFactorBasis,
    apply_multiplier,
    calculate_cash_dividend_backward_factor,
    calculate_composed_split_adjustment_multipliers,
    calculate_split_adjustment_multipliers,
    compose_price_multipliers,
    reconcile_provider_factor,
    reverse_multiplier,
)


@pytest.mark.parametrize(
    ("ratio_from", "ratio_to", "price_factor", "volume_factor"),
    [
        ("1", "4", "0.25", "4"),
        ("10", "1", "10", "0.1"),
        ("1", "1.05", "0.952380952380952381", "1.05"),
    ],
)
def test_split_price_and_volume_directions_are_explicit(
    ratio_from: str,
    ratio_to: str,
    price_factor: str,
    volume_factor: str,
) -> None:
    result = calculate_split_adjustment_multipliers(
        split_ratio_from=Decimal(ratio_from),
        split_ratio_to=Decimal(ratio_to),
    )

    assert result.price_multiplier_to_post_event_basis == Decimal(price_factor)
    assert result.volume_multiplier_to_post_event_basis == Decimal(volume_factor)


@pytest.mark.parametrize(
    ("ratio_from", "ratio_to", "raw_price", "raw_volume"),
    [
        ("1", "4", "120", "1000"),
        ("10", "1", "5", "10000"),
    ],
)
def test_split_fixture_adjustment_reverses_to_exact_raw_values(
    ratio_from: str,
    ratio_to: str,
    raw_price: str,
    raw_volume: str,
) -> None:
    factors = calculate_split_adjustment_multipliers(
        split_ratio_from=Decimal(ratio_from),
        split_ratio_to=Decimal(ratio_to),
    )
    price = Decimal(raw_price)
    volume = Decimal(raw_volume)

    adjusted_price = apply_multiplier(
        price,
        factors.price_multiplier_to_post_event_basis,
    )
    adjusted_volume = apply_multiplier(
        volume,
        factors.volume_multiplier_to_post_event_basis,
    )

    assert reverse_multiplier(
        adjusted_price,
        factors.price_multiplier_to_post_event_basis,
    ) == price
    assert reverse_multiplier(
        adjusted_volume,
        factors.volume_multiplier_to_post_event_basis,
    ) == volume


def test_same_day_reciprocal_split_ratios_cancel_before_quantization() -> None:
    result = calculate_composed_split_adjustment_multipliers(
        (
            (Decimal("3000"), Decimal("1")),
            (Decimal("1"), Decimal("3000")),
        )
    )

    assert result.price_multiplier_to_post_event_basis == Decimal(
        "1.000000000000000000"
    )
    assert result.volume_multiplier_to_post_event_basis == Decimal(
        "1.000000000000000000"
    )


def test_composed_split_requires_at_least_one_event() -> None:
    with pytest.raises(ValueError, match="at least one"):
        calculate_composed_split_adjustment_multipliers(())


def test_cash_dividend_factor_removes_the_same_basis_price_gap() -> None:
    factor = calculate_cash_dividend_backward_factor(
        cash_amount_on_reference_share_basis=Decimal("1"),
        pre_ex_close_on_same_share_basis=Decimal("100"),
    )

    assert factor == Decimal("0.99")
    assert apply_multiplier(Decimal("100"), factor) == Decimal("99")
    assert reverse_multiplier(Decimal("99"), factor) == Decimal("100")


def test_split_and_dividend_factors_compose_only_after_basis_alignment() -> None:
    split = calculate_split_adjustment_multipliers(
        split_ratio_from=Decimal("1"),
        split_ratio_to=Decimal("4"),
    )
    dividend = calculate_cash_dividend_backward_factor(
        cash_amount_on_reference_share_basis=Decimal("0.25"),
        pre_ex_close_on_same_share_basis=Decimal("25"),
    )

    combined = compose_price_multipliers(
        (split.price_multiplier_to_post_event_basis, dividend)
    )

    assert combined == Decimal("0.2475")
    assert apply_multiplier(Decimal("100"), combined) == Decimal("24.75")


def test_provider_cumulative_factor_is_not_silently_compared_to_one_event() -> None:
    comparison = reconcile_provider_factor(
        calculated_factor=Decimal("0.25"),
        provider_factor=Decimal("0.125"),
        basis=ProviderFactorBasis.CUMULATIVE_OR_UNVERIFIED,
    )

    assert comparison.status is FactorReconciliationStatus.NOT_COMPARABLE
    assert comparison.absolute_difference is None


@pytest.mark.parametrize(
    ("provider", "status"),
    [
        ("0.25", FactorReconciliationStatus.EXACT),
        ("0.2500004", FactorReconciliationStatus.WITHIN_TOLERANCE),
        ("0.251", FactorReconciliationStatus.MISMATCH),
    ],
)
def test_same_basis_provider_factor_reconciliation_is_bounded(
    provider: str,
    status: FactorReconciliationStatus,
) -> None:
    comparison = reconcile_provider_factor(
        calculated_factor=Decimal("0.25"),
        provider_factor=Decimal(provider),
        basis=ProviderFactorBasis.SAME_EVENT_AND_BASIS,
    )

    assert comparison.status is status


def test_missing_provider_factor_is_explicitly_unavailable() -> None:
    comparison = reconcile_provider_factor(
        calculated_factor=Decimal("0.25"),
        provider_factor=None,
        basis=ProviderFactorBasis.SAME_EVENT_AND_BASIS,
    )

    assert comparison.status is FactorReconciliationStatus.UNAVAILABLE
    assert comparison.absolute_difference is None


@pytest.mark.parametrize(
    "call",
    [
        lambda: calculate_split_adjustment_multipliers(
            split_ratio_from=Decimal("0"),
            split_ratio_to=Decimal("2"),
        ),
        lambda: calculate_split_adjustment_multipliers(
            split_ratio_from=1.0,  # type: ignore[arg-type]
            split_ratio_to=Decimal("2"),
        ),
        lambda: calculate_cash_dividend_backward_factor(
            cash_amount_on_reference_share_basis=Decimal("100"),
            pre_ex_close_on_same_share_basis=Decimal("100"),
        ),
        lambda: apply_multiplier(Decimal("-1"), Decimal("0.5")),
        lambda: reconcile_provider_factor(
            calculated_factor=Decimal("0.25"),
            provider_factor=Decimal("NaN"),
            basis=ProviderFactorBasis.SAME_EVENT_AND_BASIS,
        ),
    ],
)
def test_invalid_or_binary_float_inputs_fail_closed(call) -> None:
    with pytest.raises(ValueError):
        call()
