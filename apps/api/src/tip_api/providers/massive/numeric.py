"""Massive JSON numeric conversion helpers."""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation


class MissingMassiveNumericValue(Exception):
    """Raised when a required Massive numeric field is missing."""


class InvalidMassiveNumericValue(Exception):
    """Raised when a Massive numeric field cannot be represented safely."""


def parse_massive_decimal(value: object, *, required: bool) -> Decimal | None:
    """Parse a Massive JSON number into Decimal without binary-float propagation."""

    if value is None:
        if required:
            raise MissingMassiveNumericValue()
        return None
    if isinstance(value, bool):
        raise InvalidMassiveNumericValue()
    if isinstance(value, float) and not math.isfinite(value):
        raise InvalidMassiveNumericValue()
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, int | float):
        decimal_value = Decimal(str(value))
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise InvalidMassiveNumericValue()
        try:
            decimal_value = Decimal(stripped)
        except InvalidOperation as exc:
            raise InvalidMassiveNumericValue() from exc
    else:
        raise InvalidMassiveNumericValue()
    if not decimal_value.is_finite():
        raise InvalidMassiveNumericValue()
    return decimal_value


def parse_massive_integral(value: object, *, required: bool, allow_negative: bool = False) -> int | None:
    """Parse an integer-semantic Massive JSON number without truncation."""

    decimal_value = parse_massive_decimal(value, required=required)
    if decimal_value is None:
        return None
    if decimal_value != decimal_value.to_integral_value():
        raise InvalidMassiveNumericValue()
    integer_value = int(decimal_value)
    if integer_value < 0 and not allow_negative:
        raise InvalidMassiveNumericValue()
    return integer_value


def decimal_signature(value: object, *, required: bool) -> str | None:
    decimal_value = parse_massive_decimal(value, required=required)
    if decimal_value is None:
        return None
    return format(decimal_value.normalize(), "f")
