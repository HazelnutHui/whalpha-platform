"""Transparent, non-authoritative equity execution-cost scenario contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import (
    ensure_finite_decimal,
    normalize_required_string,
    normalize_utc_datetime,
    reject_float_decimal_input,
)


ASSUMPTION_CONTRACT_VERSION = "equity-execution-cost-assumption/1.0"
INPUT_CONTRACT_VERSION = "equity-execution-cost-input/1.0"
ESTIMATE_CONTRACT_VERSION = "equity-execution-cost-estimate/1.0"
METHODOLOGY_VERSION = "equity-square-root-impact-scenario-v1"
_SHA256 = r"^[0-9a-f]{64}$"
_PROVISIONAL_FINGERPRINT_TOKEN = object()


class ExecutionCostEvidenceStatus(StrEnum):
    SCENARIO_ONLY = "scenario_only"
    OBSERVED_SPREAD = "observed_spread"
    OBSERVED_SPREAD_AND_CALIBRATED_IMPACT = (
        "observed_spread_and_calibrated_impact"
    )


class ExecutionCapacityStatus(StrEnum):
    WITHIN_PARTICIPATION_LIMIT = "within_participation_limit"
    ABOVE_PARTICIPATION_LIMIT = "above_participation_limit"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EquityExecutionCostAssumptionV1(FrozenContract):
    contract_version: Literal[
        "equity-execution-cost-assumption/1.0"
    ] = ASSUMPTION_CONTRACT_VERSION
    methodology_version: Literal[
        "equity-square-root-impact-scenario-v1"
    ] = METHODOLOGY_VERSION
    scenario_id: str
    commission_bps_per_side: Decimal = Field(ge=0)
    half_spread_bps_per_side: Decimal = Field(ge=0)
    delay_slippage_bps_per_side: Decimal = Field(ge=0)
    impact_coefficient: Decimal = Field(ge=0)
    maximum_participation_rate: Decimal = Field(gt=0, le=1)
    evidence_status: ExecutionCostEvidenceStatus
    quoted_spread_evidence_fingerprint: str | None = Field(
        default=None,
        pattern=_SHA256,
    )
    impact_calibration_evidence_fingerprint: str | None = Field(
        default=None,
        pattern=_SHA256,
    )
    limitation_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("scenario_id", mode="before")
    @classmethod
    def normalize_scenario_id(cls, value: str) -> str:
        return normalize_required_string(value, field_name="scenario_id")

    @field_validator(
        "commission_bps_per_side",
        "half_spread_bps_per_side",
        "delay_slippage_bps_per_side",
        "impact_coefficient",
        "maximum_participation_rate",
        mode="before",
    )
    @classmethod
    def reject_float_values(cls, value: Any, info: Any) -> Any:
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator(
        "commission_bps_per_side",
        "half_spread_bps_per_side",
        "delay_slippage_bps_per_side",
        "impact_coefficient",
        "maximum_participation_rate",
    )
    @classmethod
    def finite_values(cls, value: Decimal, info: Any) -> Decimal:
        return ensure_finite_decimal(value, field_name=info.field_name)

    @field_validator("limitation_codes", mode="before")
    @classmethod
    def normalize_limitations(cls, value: Any) -> tuple[str, ...]:
        return _normalized_codes(value, "limitation_codes")

    @model_validator(mode="after")
    def assumption_reconciles(
        self,
        info: ValidationInfo,
    ) -> "EquityExecutionCostAssumptionV1":
        limitations = set(self.limitation_codes)
        if self.evidence_status is ExecutionCostEvidenceStatus.SCENARIO_ONLY:
            if (
                self.quoted_spread_evidence_fingerprint is not None
                or self.impact_calibration_evidence_fingerprint is not None
                or not {
                    "quoted_spread_unavailable",
                    "impact_not_calibrated",
                }.issubset(limitations)
            ):
                raise ValueError("scenario-only cost evidence differs")
        elif self.evidence_status is ExecutionCostEvidenceStatus.OBSERVED_SPREAD:
            if (
                self.quoted_spread_evidence_fingerprint is None
                or self.impact_calibration_evidence_fingerprint is not None
                or "quoted_spread_unavailable" in limitations
                or "impact_not_calibrated" not in limitations
            ):
                raise ValueError("observed-spread cost evidence differs")
        elif (
            self.quoted_spread_evidence_fingerprint is None
            or self.impact_calibration_evidence_fingerprint is None
            or "quoted_spread_unavailable" in limitations
            or "impact_not_calibrated" in limitations
        ):
            raise ValueError(
                "observed-spread and calibrated-impact cost evidence is incomplete"
            )
        if (
            not _provisional_fingerprint_allowed(info)
            and execution_cost_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("execution-cost assumption fingerprint differs")
        return self


class EquityExecutionCostInputV1(FrozenContract):
    contract_version: Literal[
        "equity-execution-cost-input/1.0"
    ] = INPUT_CONTRACT_VERSION
    instrument_id: UUID
    session: date
    order_notional_usd: Decimal = Field(gt=0)
    median_dollar_volume_20_usd: Decimal = Field(gt=0)
    daily_return_volatility_20: Decimal = Field(ge=0)
    source_eod_fingerprint: str = Field(pattern=_SHA256)
    source_data_cutoff: datetime
    calculated_at: datetime
    dollar_volume_basis: Literal[
        "unadjusted_close_times_volume_median_20s_proxy"
    ] = "unadjusted_close_times_volume_median_20s_proxy"
    intraday_volume_profile_available: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("session", mode="before")
    @classmethod
    def reject_datetime_session(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("execution-cost session must not receive datetime")
        return value

    @field_validator(
        "order_notional_usd",
        "median_dollar_volume_20_usd",
        "daily_return_volatility_20",
        mode="before",
    )
    @classmethod
    def reject_float_values(cls, value: Any, info: Any) -> Any:
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator(
        "order_notional_usd",
        "median_dollar_volume_20_usd",
        "daily_return_volatility_20",
    )
    @classmethod
    def finite_values(cls, value: Decimal, info: Any) -> Decimal:
        return ensure_finite_decimal(value, field_name=info.field_name)

    @field_validator("source_data_cutoff", "calculated_at")
    @classmethod
    def utc_times(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def input_reconciles(
        self,
        info: ValidationInfo,
    ) -> "EquityExecutionCostInputV1":
        if self.source_data_cutoff > self.calculated_at:
            raise ValueError("execution-cost calculation precedes source cutoff")
        if (
            not _provisional_fingerprint_allowed(info)
            and execution_cost_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("execution-cost input fingerprint differs")
        return self


class EquityExecutionCostEstimateV1(FrozenContract):
    contract_version: Literal[
        "equity-execution-cost-estimate/1.0"
    ] = ESTIMATE_CONTRACT_VERSION
    methodology_version: Literal[
        "equity-square-root-impact-scenario-v1"
    ] = METHODOLOGY_VERSION
    input_logical_fingerprint: str = Field(pattern=_SHA256)
    assumption_logical_fingerprint: str = Field(pattern=_SHA256)
    instrument_id: UUID
    session: date
    order_notional_usd: Decimal = Field(gt=0)
    median_dollar_volume_20_usd: Decimal = Field(gt=0)
    daily_return_volatility_20: Decimal = Field(ge=0)
    participation_rate: Decimal = Field(gt=0)
    maximum_participation_rate: Decimal = Field(gt=0, le=1)
    commission_bps_per_side: Decimal = Field(ge=0)
    half_spread_bps_per_side: Decimal = Field(ge=0)
    delay_slippage_bps_per_side: Decimal = Field(ge=0)
    market_impact_bps_per_side: Decimal = Field(ge=0)
    total_estimated_bps_per_side: Decimal = Field(ge=0)
    total_estimated_cost_usd_per_side: Decimal = Field(ge=0)
    capacity_status: ExecutionCapacityStatus
    evidence_status: ExecutionCostEvidenceStatus
    limitation_codes: tuple[str, ...]
    calculated_at: datetime
    estimated_not_realized: Literal[True] = True
    equity_execution_only: Literal[True] = True
    research_admission_authorized: Literal[False] = False
    option_execution_cost_authorized: Literal[False] = False
    performance_claim_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator(
        "order_notional_usd",
        "median_dollar_volume_20_usd",
        "daily_return_volatility_20",
        "participation_rate",
        "maximum_participation_rate",
        "commission_bps_per_side",
        "half_spread_bps_per_side",
        "delay_slippage_bps_per_side",
        "market_impact_bps_per_side",
        "total_estimated_bps_per_side",
        "total_estimated_cost_usd_per_side",
        mode="before",
    )
    @classmethod
    def reject_float_values(cls, value: Any, info: Any) -> Any:
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator(
        "order_notional_usd",
        "median_dollar_volume_20_usd",
        "daily_return_volatility_20",
        "participation_rate",
        "maximum_participation_rate",
        "commission_bps_per_side",
        "half_spread_bps_per_side",
        "delay_slippage_bps_per_side",
        "market_impact_bps_per_side",
        "total_estimated_bps_per_side",
        "total_estimated_cost_usd_per_side",
    )
    @classmethod
    def finite_values(cls, value: Decimal, info: Any) -> Decimal:
        return ensure_finite_decimal(value, field_name=info.field_name)

    @field_validator("session", mode="before")
    @classmethod
    def reject_datetime_session(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("execution-cost session must not receive datetime")
        return value

    @field_validator("calculated_at")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("limitation_codes", mode="before")
    @classmethod
    def normalize_limitations(cls, value: Any) -> tuple[str, ...]:
        return _normalized_codes(value, "limitation_codes")

    @model_validator(mode="after")
    def estimate_reconciles(
        self,
        info: ValidationInfo,
    ) -> "EquityExecutionCostEstimateV1":
        expected_total = (
            self.commission_bps_per_side
            + self.half_spread_bps_per_side
            + self.delay_slippage_bps_per_side
            + self.market_impact_bps_per_side
        ).quantize(Decimal("0.000001"))
        expected_usd = (
            self.order_notional_usd
            * self.total_estimated_bps_per_side
            / Decimal("10000")
        ).quantize(Decimal("0.01"))
        expected_capacity = (
            ExecutionCapacityStatus.WITHIN_PARTICIPATION_LIMIT
            if self.participation_rate <= self.maximum_participation_rate
            else ExecutionCapacityStatus.ABOVE_PARTICIPATION_LIMIT
        )
        if (
            self.total_estimated_bps_per_side != expected_total
            or self.total_estimated_cost_usd_per_side != expected_usd
            or self.capacity_status is not expected_capacity
        ):
            raise ValueError("execution-cost estimate arithmetic differs")
        if (
            not _provisional_fingerprint_allowed(info)
            and execution_cost_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("execution-cost estimate fingerprint differs")
        return self


def build_equity_execution_cost_assumption(
    **values: object,
) -> EquityExecutionCostAssumptionV1:
    return _build(EquityExecutionCostAssumptionV1, values)


def build_equity_execution_cost_input(
    **values: object,
) -> EquityExecutionCostInputV1:
    return _build(EquityExecutionCostInputV1, values)


def build_equity_execution_cost_estimate(
    **values: object,
) -> EquityExecutionCostEstimateV1:
    return _build(EquityExecutionCostEstimateV1, values)


def execution_cost_fingerprint(value: BaseModel) -> str:
    payload = json.dumps(
        to_jsonable_python(
            value.model_dump(mode="json", exclude={"logical_fingerprint"})
        ),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _build(model: type[BaseModel], values: dict[str, object]) -> Any:
    provisional = model.model_validate(
        {**values, "logical_fingerprint": "0" * 64},
        context={
            "provisional_logical_fingerprint_token": (
                _PROVISIONAL_FINGERPRINT_TOKEN
            )
        },
    )
    normalized_values = provisional.model_dump(
        mode="python",
        exclude={"logical_fingerprint"},
    )
    return model.model_validate(
        {
            **normalized_values,
            "logical_fingerprint": execution_cost_fingerprint(provisional),
        }
    )


def _provisional_fingerprint_allowed(info: ValidationInfo) -> bool:
    return bool(
        info.context
        and info.context.get("provisional_logical_fingerprint_token")
        is _PROVISIONAL_FINGERPRINT_TOKEN
    )


def _normalized_codes(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list, set, frozenset)):
        raise ValueError(f"{field_name} must be a collection")
    normalized = tuple(
        sorted(
            {
                normalize_required_string(item, field_name=field_name)
                .lower()
                .replace("-", "_")
                .replace(" ", "_")
                for item in value
            }
        )
    )
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized
