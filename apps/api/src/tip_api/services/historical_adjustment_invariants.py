"""Exact fixture math for split and cash-dividend adjustment invariants."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from enum import StrEnum
from typing import Iterable

FACTOR_SCALE = 18
FACTOR_QUANTUM = Decimal(1).scaleb(-FACTOR_SCALE)
DEFAULT_RECONCILIATION_TOLERANCE = Decimal("0.0000005")


class ProviderFactorBasis(StrEnum):
    SAME_EVENT_AND_BASIS = "same_event_and_basis"
    CUMULATIVE_OR_UNVERIFIED = "cumulative_or_unverified"


class FactorReconciliationStatus(StrEnum):
    EXACT = "exact"
    WITHIN_TOLERANCE = "within_tolerance"
    MISMATCH = "mismatch"
    NOT_COMPARABLE = "not_comparable"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SplitAdjustmentMultipliers:
    split_ratio_from: Decimal
    split_ratio_to: Decimal
    price_multiplier_to_post_event_basis: Decimal
    volume_multiplier_to_post_event_basis: Decimal


@dataclass(frozen=True)
class FactorReconciliation:
    calculated_factor: Decimal
    provider_factor: Decimal | None
    basis: ProviderFactorBasis
    tolerance: Decimal
    absolute_difference: Decimal | None
    status: FactorReconciliationStatus


def calculate_split_adjustment_multipliers(
    *,
    split_ratio_from: Decimal,
    split_ratio_to: Decimal,
) -> SplitAdjustmentMultipliers:
    """Return old-share price/volume multipliers on the post-event share basis."""

    ratio_from = _positive_decimal(split_ratio_from, "split_ratio_from")
    ratio_to = _positive_decimal(split_ratio_to, "split_ratio_to")
    return SplitAdjustmentMultipliers(
        split_ratio_from=ratio_from,
        split_ratio_to=ratio_to,
        price_multiplier_to_post_event_basis=_divide(ratio_from, ratio_to),
        volume_multiplier_to_post_event_basis=_divide(ratio_to, ratio_from),
    )


def calculate_composed_split_adjustment_multipliers(
    ratios: Iterable[tuple[Decimal, Decimal]],
) -> SplitAdjustmentMultipliers:
    """Compose same-basis split ratios before the single final quantization.

    Multiplying already-quantized per-event factors can turn reciprocal same-day
    events into a value merely close to one. Combining the exact ratio
    numerators and denominators first preserves that cancellation.
    """

    product_from = Decimal("1")
    product_to = Decimal("1")
    count = 0
    with localcontext() as context:
        context.prec = 56
        context.rounding = ROUND_HALF_EVEN
        for index, (raw_from, raw_to) in enumerate(ratios):
            product_from *= _positive_decimal(raw_from, f"ratios[{index}].from")
            product_to *= _positive_decimal(raw_to, f"ratios[{index}].to")
            count += 1
    if count == 0:
        raise ValueError("at least one split ratio is required")
    return SplitAdjustmentMultipliers(
        split_ratio_from=product_from,
        split_ratio_to=product_to,
        price_multiplier_to_post_event_basis=_divide(product_from, product_to),
        volume_multiplier_to_post_event_basis=_divide(product_to, product_from),
    )


def calculate_cash_dividend_backward_factor(
    *,
    cash_amount_on_reference_share_basis: Decimal,
    pre_ex_close_on_same_share_basis: Decimal,
) -> Decimal:
    """Return the backward price factor that removes one cash-dividend gap.

    This is an adjusted-price continuity factor, not the dividend yield, a
    forecast return, or an option return. Both inputs must use the same share
    basis and currency.
    """

    cash_amount = _positive_decimal(
        cash_amount_on_reference_share_basis,
        "cash_amount_on_reference_share_basis",
    )
    pre_ex_close = _positive_decimal(
        pre_ex_close_on_same_share_basis,
        "pre_ex_close_on_same_share_basis",
    )
    if cash_amount >= pre_ex_close:
        raise ValueError("cash dividend must be smaller than the same-basis pre-ex close")
    return _divide(pre_ex_close - cash_amount, pre_ex_close)


def compose_price_multipliers(multipliers: Iterable[Decimal]) -> Decimal:
    """Compose already basis-aligned price multipliers in deterministic Decimal math."""

    result = Decimal("1")
    count = 0
    with localcontext() as context:
        context.prec = 56
        context.rounding = ROUND_HALF_EVEN
        for index, raw_multiplier in enumerate(multipliers):
            multiplier = _positive_decimal(raw_multiplier, f"multipliers[{index}]")
            result *= multiplier
            count += 1
    if count == 0:
        return Decimal("1").quantize(FACTOR_QUANTUM)
    return _quantize_factor(result)


def apply_multiplier(raw_value: Decimal, multiplier: Decimal) -> Decimal:
    value = _non_negative_decimal(raw_value, "raw_value")
    factor = _positive_decimal(multiplier, "multiplier")
    with localcontext() as context:
        context.prec = 56
        context.rounding = ROUND_HALF_EVEN
        return value * factor


def reverse_multiplier(adjusted_value: Decimal, multiplier: Decimal) -> Decimal:
    value = _non_negative_decimal(adjusted_value, "adjusted_value")
    factor = _positive_decimal(multiplier, "multiplier")
    with localcontext() as context:
        context.prec = 56
        context.rounding = ROUND_HALF_EVEN
        return value / factor


def reconcile_provider_factor(
    *,
    calculated_factor: Decimal,
    provider_factor: Decimal | None,
    basis: ProviderFactorBasis,
    tolerance: Decimal = DEFAULT_RECONCILIATION_TOLERANCE,
) -> FactorReconciliation:
    """Compare only factors explicitly known to share an event set and basis."""

    calculated = _positive_decimal(calculated_factor, "calculated_factor")
    allowed_tolerance = _non_negative_decimal(tolerance, "tolerance")
    if provider_factor is None:
        return FactorReconciliation(
            calculated_factor=calculated,
            provider_factor=None,
            basis=basis,
            tolerance=allowed_tolerance,
            absolute_difference=None,
            status=FactorReconciliationStatus.UNAVAILABLE,
        )
    provider = _positive_decimal(provider_factor, "provider_factor")
    if basis is ProviderFactorBasis.CUMULATIVE_OR_UNVERIFIED:
        return FactorReconciliation(
            calculated_factor=calculated,
            provider_factor=provider,
            basis=basis,
            tolerance=allowed_tolerance,
            absolute_difference=None,
            status=FactorReconciliationStatus.NOT_COMPARABLE,
        )
    difference = abs(provider - calculated)
    status = (
        FactorReconciliationStatus.EXACT
        if difference == 0
        else FactorReconciliationStatus.WITHIN_TOLERANCE
        if difference <= allowed_tolerance
        else FactorReconciliationStatus.MISMATCH
    )
    return FactorReconciliation(
        calculated_factor=calculated,
        provider_factor=provider,
        basis=basis,
        tolerance=allowed_tolerance,
        absolute_difference=difference,
        status=status,
    )


def _divide(numerator: Decimal, denominator: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 56
        context.rounding = ROUND_HALF_EVEN
        result = numerator / denominator
    return _quantize_factor(result)


def _quantize_factor(value: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 56
        context.rounding = ROUND_HALF_EVEN
        return value.quantize(FACTOR_QUANTUM)


def _positive_decimal(value: Decimal, field_name: str) -> Decimal:
    value = _decimal(value, field_name)
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value


def _non_negative_decimal(value: Decimal, field_name: str) -> Decimal:
    value = _decimal(value, field_name)
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _decimal(value: Decimal, field_name: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{field_name} must be a finite Decimal")
    return value
