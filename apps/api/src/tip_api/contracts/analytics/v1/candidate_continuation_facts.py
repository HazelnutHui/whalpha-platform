"""Typed descriptive facts for future trend-continuation research."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.parameters.market_regime.candidate_continuation_facts_v1_0_0 import (
    CONTINUATION_FACTS_CALCULATION_VERSION,
    CONTINUATION_FACTS_CONTRACT_VERSION,
    CONTINUATION_FACTS_PARAMETER_FINGERPRINT,
    CONTINUATION_FACTS_PARAMETER_SET_ID,
)


class ContinuationFactAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class CandidateContinuationMetricsV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    availability: ContinuationFactAvailability
    net_return_10: str | None
    information_discreteness_10: str | None
    return_path_efficiency_10: str | None
    largest_absolute_return_share_10: str | None
    positive_return_share_10: str | None
    above_sma10_share_10: str | None
    sma10_slope_5_atr: str | None
    atr_5_to_14: str | None
    close_drawdown_from_high_20_atr: str | None
    recent_close_low_vs_prior_5_atr: str | None
    recent_close_high_vs_prior_5_atr: str | None
    recent_volume_median_ratio_5_to_prior_15: str | None
    missing_reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def availability_reconciles(self) -> "CandidateContinuationMetricsV1":
        names = (
            "net_return_10",
            "information_discreteness_10",
            "return_path_efficiency_10",
            "largest_absolute_return_share_10",
            "positive_return_share_10",
            "above_sma10_share_10",
            "sma10_slope_5_atr",
            "atr_5_to_14",
            "close_drawdown_from_high_20_atr",
            "recent_close_low_vs_prior_5_atr",
            "recent_close_high_vs_prior_5_atr",
            "recent_volume_median_ratio_5_to_prior_15",
        )
        if self.availability is ContinuationFactAvailability.AVAILABLE:
            if (
                any(getattr(self, name) is None for name in names)
                or self.missing_reason_codes
            ):
                raise ValueError("available continuation facts require every frozen metric")
            values = {name: _scale_ten(getattr(self, name), name) for name in names}
            for name in (
                "information_discreteness_10",
                "return_path_efficiency_10",
                "largest_absolute_return_share_10",
                "positive_return_share_10",
                "above_sma10_share_10",
            ):
                lower = (
                    Decimal("-1")
                    if name == "information_discreteness_10"
                    else Decimal("0")
                )
                if not lower <= values[name] <= Decimal("1"):
                    raise ValueError(f"{name} must remain inside its unit interval")
            if values["atr_5_to_14"] <= 0:
                raise ValueError("continuation ATR ratio must be positive")
            if values["close_drawdown_from_high_20_atr"] < 0:
                raise ValueError("continuation high drawdown cannot be negative")
            if values["recent_volume_median_ratio_5_to_prior_15"] < 0:
                raise ValueError("continuation volume ratio cannot be negative")
        elif (
            any(getattr(self, name) is not None for name in names)
            or not self.missing_reason_codes
        ):
            raise ValueError("unavailable continuation facts must be null with a reason")
        return self


class CandidateContinuationFactsV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[CONTINUATION_FACTS_CONTRACT_VERSION] = (
        CONTINUATION_FACTS_CONTRACT_VERSION
    )
    calculation_version: Literal[CONTINUATION_FACTS_CALCULATION_VERSION] = (
        CONTINUATION_FACTS_CALCULATION_VERSION
    )
    parameter_set_id: Literal[CONTINUATION_FACTS_PARAMETER_SET_ID] = (
        CONTINUATION_FACTS_PARAMETER_SET_ID
    )
    parameter_fingerprint: Literal[CONTINUATION_FACTS_PARAMETER_FINGERPRINT] = (
        CONTINUATION_FACTS_PARAMETER_FINGERPRINT
    )
    as_of_session: date
    universe_id: str
    instrument_id: UUID
    ticker: str
    security_type: Literal["CS", "ADRC"]
    source_candidate_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_entry_geometry_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    metrics: CandidateContinuationMetricsV1
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def fingerprint_reconciles(self) -> "CandidateContinuationFactsV1":
        if continuation_facts_fingerprint(
            self, exclude={"logical_fingerprint"}
        ) != self.logical_fingerprint:
            raise ValueError("continuation fact record fingerprint mismatch")
        return self


class CandidateContinuationFactsBatchV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[CONTINUATION_FACTS_CONTRACT_VERSION] = (
        CONTINUATION_FACTS_CONTRACT_VERSION
    )
    calculation_version: Literal[CONTINUATION_FACTS_CALCULATION_VERSION] = (
        CONTINUATION_FACTS_CALCULATION_VERSION
    )
    parameter_set_id: Literal[CONTINUATION_FACTS_PARAMETER_SET_ID] = (
        CONTINUATION_FACTS_PARAMETER_SET_ID
    )
    parameter_fingerprint: Literal[CONTINUATION_FACTS_PARAMETER_FINGERPRINT] = (
        CONTINUATION_FACTS_PARAMETER_FINGERPRINT
    )
    as_of_session: date
    universe_id: str
    source_candidate_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_entry_geometry_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessed_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)
    availability_counts: dict[str, int]
    records: tuple[CandidateContinuationFactsV1, ...]
    strategy_score_input: Literal[False] = False
    outcome_or_performance_claim: Literal[False] = False
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def batch_reconciles(self) -> "CandidateContinuationFactsBatchV1":
        keys = tuple(str(item.instrument_id) for item in self.records)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("continuation fact records must be unique and stable-ID ordered")
        assessed = sum(
            item.metrics.availability is ContinuationFactAvailability.AVAILABLE
            for item in self.records
        )
        if (
            self.assessed_count != assessed
            or self.unavailable_count != len(self.records) - assessed
        ):
            raise ValueError("continuation fact availability totals differ")
        if self.availability_counts != dict(
            Counter(item.metrics.availability.value for item in self.records)
        ):
            raise ValueError("continuation fact availability counts differ")
        if any(
            item.as_of_session != self.as_of_session or item.universe_id != self.universe_id
            for item in self.records
        ):
            raise ValueError("continuation fact record identity differs from its batch")
        if continuation_facts_fingerprint(
            self, exclude={"logical_fingerprint"}
        ) != self.logical_fingerprint:
            raise ValueError("continuation fact batch fingerprint mismatch")
        return self


def continuation_facts_fingerprint(
    value: BaseModel | dict[str, object], *, exclude: set[str] | None = None
) -> str:
    payload = (
        value.model_dump(mode="json", exclude=exclude or set())
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key not in (exclude or set())}
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _scale_ten(value: str | None, label: str) -> Decimal:
    if value is None:
        raise ValueError(f"{label} is required")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} must be a Decimal string") from exc
    if not parsed.is_finite() or value != format(
        parsed.quantize(Decimal("0.0000000001")), "f"
    ):
        raise ValueError(f"{label} must be finite and use scale 10")
    return parsed
