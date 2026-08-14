"""Shared contract types and validation helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

SCHEMA_VERSION_V1 = "1.0"


class QualityStatus(StrEnum):
    """Shared quality status for canonical market-data contracts."""

    VALID = "valid"
    WARNING = "warning"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"


def normalize_utc_datetime(value: datetime) -> datetime:
    """Require a timezone-aware datetime and normalize it to UTC."""

    if not isinstance(value, datetime):
        raise ValueError("value must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)


def normalize_required_string(value: str, *, field_name: str, uppercase: bool = False) -> str:
    """Trim a required string and reject empty values."""

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized.upper() if uppercase else normalized


def normalize_optional_string(value: str | None, *, field_name: str, uppercase: bool = False) -> str | None:
    """Trim an optional string while keeping missing values as None."""

    if value is None:
        return None
    return normalize_required_string(value, field_name=field_name, uppercase=uppercase)


def ensure_finite_decimal(value: Decimal, *, field_name: str) -> Decimal:
    """Reject NaN and infinity without changing Decimal precision."""

    if not isinstance(value, Decimal):
        raise ValueError(f"{field_name} must be a Decimal")
    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return value


def reject_float_decimal_input(value: Any, *, field_name: str) -> Any:
    """Reject binary-float inputs before Pydantic converts them to Decimal."""

    if isinstance(value, float):
        raise ValueError(f"{field_name} must use Decimal or a decimal string, not float")
    return value
