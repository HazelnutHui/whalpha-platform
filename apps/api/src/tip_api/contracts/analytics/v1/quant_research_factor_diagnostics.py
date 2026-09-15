"""Outcome-blind diagnostic report contracts for Factor Catalog V1."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from itertools import combinations
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_factor_catalog import (
    QUANT_RESEARCH_FACTOR_ORDER,
    quant_research_factor_catalog_v1,
)


QUANT_RESEARCH_FACTOR_DIAGNOSTICS_CONTRACT_VERSION = (
    "quant-research-factor-diagnostics/1.0"
)
QUANT_RESEARCH_FACTOR_DIAGNOSTICS_PROTOCOL_VERSION = (
    "quant-research-factor-qualification/1.0.0"
)
QUANT_RESEARCH_FACTOR_DIAGNOSTICS_EVIDENCE_TIER = (
    "reconstructed_latest_vintage_outcome_blind_only"
)
QUANT_RESEARCH_FACTOR_DIAGNOSTICS_MINIMUM_PAIR_OBSERVATIONS = 30
QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_MINIMUM_SESSIONS = 60
QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_ABSOLUTE_RHO = "0.9000000000"
QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_SESSION_SHARE = "0.8000000000"
QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_SIGN_SHARE = "0.9000000000"
QUANT_RESEARCH_FACTOR_PAIR_ORDER = tuple(
    combinations(QUANT_RESEARCH_FACTOR_ORDER, 2)
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchFactorConcentrationAxis(StrEnum):
    SESSION = "session"
    INSTRUMENT = "instrument"


class QuantResearchFactorReasonCountV1(FrozenModel):
    reason_code: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    count: int = Field(ge=1)


class QuantResearchFactorCoverageV1(FrozenModel):
    factor_id: str
    expected_count: int = Field(ge=0)
    available_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)
    availability_rate: str
    unavailable_reason_counts: tuple[QuantResearchFactorReasonCountV1, ...]

    @model_validator(mode="after")
    def coverage_reconciles(self) -> "QuantResearchFactorCoverageV1":
        if (
            self.factor_id not in QUANT_RESEARCH_FACTOR_ORDER
            or self.available_count + self.unavailable_count != self.expected_count
            or tuple(item.reason_code for item in self.unavailable_reason_counts)
            != tuple(sorted({item.reason_code for item in self.unavailable_reason_counts}))
        ):
            raise ValueError("factor coverage differs")
        _require_ratio(
            self.availability_rate,
            self.available_count,
            self.expected_count,
            "factor availability rate",
        )
        return self


class QuantResearchFactorSessionAvailabilityV1(FrozenModel):
    as_of_session: date
    factor_id: str
    expected_count: int = Field(ge=0)
    available_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)
    availability_rate: str

    @model_validator(mode="after")
    def session_reconciles(self) -> "QuantResearchFactorSessionAvailabilityV1":
        if (
            self.factor_id not in QUANT_RESEARCH_FACTOR_ORDER
            or self.available_count + self.unavailable_count != self.expected_count
        ):
            raise ValueError("factor session availability differs")
        _require_ratio(
            self.availability_rate,
            self.available_count,
            self.expected_count,
            "factor session availability rate",
        )
        return self


class QuantResearchFactorDistributionV1(FrozenModel):
    factor_id: str
    observation_count: int = Field(ge=0)
    distinct_value_count: int = Field(ge=0)
    same_session_tie_excess_count: int = Field(ge=0)
    same_session_tie_excess_rate: str
    minimum: str | None = None
    p01: str | None = None
    p05: str | None = None
    p25: str | None = None
    median: str | None = None
    p75: str | None = None
    p95: str | None = None
    p99: str | None = None
    maximum: str | None = None
    outer_fence_low: str | None = None
    outer_fence_high: str | None = None
    outer_outlier_count: int = Field(ge=0)
    outer_outlier_rate: str

    @model_validator(mode="after")
    def distribution_reconciles(self) -> "QuantResearchFactorDistributionV1":
        values = (
            self.minimum,
            self.p01,
            self.p05,
            self.p25,
            self.median,
            self.p75,
            self.p95,
            self.p99,
            self.maximum,
        )
        if (
            self.factor_id not in QUANT_RESEARCH_FACTOR_ORDER
            or self.distinct_value_count > self.observation_count
            or self.same_session_tie_excess_count > self.observation_count
            or self.outer_outlier_count > self.observation_count
        ):
            raise ValueError("factor distribution counts differ")
        _require_ratio(
            self.same_session_tie_excess_rate,
            self.same_session_tie_excess_count,
            self.observation_count,
            "factor tie excess rate",
        )
        _require_ratio(
            self.outer_outlier_rate,
            self.outer_outlier_count,
            self.observation_count,
            "factor outlier rate",
        )
        if self.observation_count == 0:
            if any(value is not None for value in values) or any(
                value is not None
                for value in (self.outer_fence_low, self.outer_fence_high)
            ):
                raise ValueError("empty factor distribution carries values")
            return self
        if any(value is None for value in values) or any(
            value is None for value in (self.outer_fence_low, self.outer_fence_high)
        ):
            raise ValueError("populated factor distribution lacks values")
        parsed = tuple(_canonical_decimal(value) for value in values)
        if parsed != tuple(sorted(parsed)):
            raise ValueError("factor distribution quantiles are not monotonic")
        _canonical_decimal(self.outer_fence_low)
        _canonical_decimal(self.outer_fence_high)
        return self


class QuantResearchFactorConcentrationV1(FrozenModel):
    factor_id: str
    axis: QuantResearchFactorConcentrationAxis
    observation_count: int = Field(ge=0)
    group_count: int = Field(ge=0)
    maximum_group_count: int = Field(ge=0)
    maximum_group_share: str
    top_ten_group_share: str
    herfindahl_index: str

    @model_validator(mode="after")
    def concentration_reconciles(self) -> "QuantResearchFactorConcentrationV1":
        if (
            self.factor_id not in QUANT_RESEARCH_FACTOR_ORDER
            or self.group_count > self.observation_count
            or self.maximum_group_count > self.observation_count
            or (self.observation_count > 0 and self.group_count == 0)
        ):
            raise ValueError("factor concentration counts differ")
        for value in (
            self.maximum_group_share,
            self.top_ten_group_share,
            self.herfindahl_index,
        ):
            parsed = _canonical_decimal(value)
            if parsed < 0 or parsed > 1:
                raise ValueError("factor concentration ratio is outside zero to one")
        _require_ratio(
            self.maximum_group_share,
            self.maximum_group_count,
            self.observation_count,
            "maximum group share",
        )
        return self


class QuantResearchFactorPairCorrelationV1(FrozenModel):
    left_factor_id: str
    right_factor_id: str
    eligible_session_count: int = Field(ge=0)
    shared_observation_count: int = Field(ge=0)
    weighted_mean_spearman: str | None = None
    median_session_spearman: str | None = None
    p05_session_spearman: str | None = None
    p95_session_spearman: str | None = None
    high_absolute_correlation_session_count: int = Field(ge=0)
    high_absolute_correlation_session_share: str
    positive_session_count: int = Field(ge=0)
    negative_session_count: int = Field(ge=0)
    zero_session_count: int = Field(ge=0)
    dominant_sign_session_share: str
    near_duplicate: bool

    @model_validator(mode="after")
    def correlation_reconciles(self) -> "QuantResearchFactorPairCorrelationV1":
        if (
            (self.left_factor_id, self.right_factor_id)
            not in QUANT_RESEARCH_FACTOR_PAIR_ORDER
            or self.high_absolute_correlation_session_count
            > self.eligible_session_count
            or self.positive_session_count
            + self.negative_session_count
            + self.zero_session_count
            != self.eligible_session_count
        ):
            raise ValueError("factor pair correlation counts differ")
        _require_ratio(
            self.high_absolute_correlation_session_share,
            self.high_absolute_correlation_session_count,
            self.eligible_session_count,
            "high absolute correlation share",
        )
        nonzero = self.positive_session_count + self.negative_session_count
        _require_ratio(
            self.dominant_sign_session_share,
            max(self.positive_session_count, self.negative_session_count),
            nonzero,
            "dominant sign share",
        )
        values = (
            self.weighted_mean_spearman,
            self.median_session_spearman,
            self.p05_session_spearman,
            self.p95_session_spearman,
        )
        if self.eligible_session_count == 0:
            if any(value is not None for value in values) or self.near_duplicate:
                raise ValueError("empty factor pair carries correlation")
        elif any(value is None for value in values):
            raise ValueError("eligible factor pair lacks correlation")
        for value in values:
            if value is not None and not Decimal("-1") <= _canonical_decimal(value) <= Decimal("1"):
                raise ValueError("factor pair correlation is outside minus one to one")
        return self


class QuantResearchFactorNearDuplicateGroupV1(FrozenModel):
    group_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    factor_ids: tuple[str, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def group_reconciles(self) -> "QuantResearchFactorNearDuplicateGroupV1":
        if self.factor_ids != tuple(sorted(set(self.factor_ids))):
            raise ValueError("near-duplicate group order differs")
        if any(item not in QUANT_RESEARCH_FACTOR_ORDER for item in self.factor_ids):
            raise ValueError("near-duplicate group contains unknown factor")
        expected = hashlib.sha256("\n".join(self.factor_ids).encode("utf-8")).hexdigest()
        if self.group_id != expected:
            raise ValueError("near-duplicate group identity differs")
        return self


class QuantResearchFactorDiagnosticsV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[QUANT_RESEARCH_FACTOR_DIAGNOSTICS_CONTRACT_VERSION] = (
        QUANT_RESEARCH_FACTOR_DIAGNOSTICS_CONTRACT_VERSION
    )
    protocol_version: Literal[QUANT_RESEARCH_FACTOR_DIAGNOSTICS_PROTOCOL_VERSION] = (
        QUANT_RESEARCH_FACTOR_DIAGNOSTICS_PROTOCOL_VERSION
    )
    evidence_tier: Literal[QUANT_RESEARCH_FACTOR_DIAGNOSTICS_EVIDENCE_TIER] = (
        QUANT_RESEARCH_FACTOR_DIAGNOSTICS_EVIDENCE_TIER
    )
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    chronological_plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_population_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_eod_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_action_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calculation_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    diagnostic_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    first_session: date
    last_session: date
    session_count: int = Field(ge=1)
    expected_path_count: int = Field(ge=0)
    complete_factor_vector_count: int = Field(ge=0)
    incomplete_factor_vector_count: int = Field(ge=0)
    expected_factor_cell_count: int = Field(ge=0)
    available_factor_cell_count: int = Field(ge=0)
    unavailable_factor_cell_count: int = Field(ge=0)
    factor_coverage: tuple[QuantResearchFactorCoverageV1, ...]
    session_availability: tuple[QuantResearchFactorSessionAvailabilityV1, ...]
    distributions: tuple[QuantResearchFactorDistributionV1, ...]
    concentration: tuple[QuantResearchFactorConcentrationV1, ...]
    pairwise_same_session_spearman: tuple[QuantResearchFactorPairCorrelationV1, ...]
    near_duplicate_groups: tuple[QuantResearchFactorNearDuplicateGroupV1, ...]
    limitation_codes: tuple[str, ...] = Field(min_length=1)
    contains_forward_outcomes: Literal[False] = False
    contains_performance_metrics: Literal[False] = False
    factor_screening_authorized: Literal[False] = False
    factor_admission_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    strategy_expression_authorized: Literal[False] = False
    validation_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def report_reconciles(self) -> "QuantResearchFactorDiagnosticsV1":
        factor_count = len(QUANT_RESEARCH_FACTOR_ORDER)
        expected_session_rows = self.session_count * factor_count
        if (
            self.catalog_fingerprint
            != quant_research_factor_catalog_v1().logical_fingerprint
            or self.first_session > self.last_session
            or self.complete_factor_vector_count + self.incomplete_factor_vector_count
            != self.expected_path_count
            or self.expected_factor_cell_count != self.expected_path_count * factor_count
            or self.available_factor_cell_count + self.unavailable_factor_cell_count
            != self.expected_factor_cell_count
            or tuple(item.factor_id for item in self.factor_coverage)
            != QUANT_RESEARCH_FACTOR_ORDER
            or tuple(item.factor_id for item in self.distributions)
            != QUANT_RESEARCH_FACTOR_ORDER
            or len(self.session_availability) != expected_session_rows
            or tuple(
                (item.left_factor_id, item.right_factor_id)
                for item in self.pairwise_same_session_spearman
            )
            != QUANT_RESEARCH_FACTOR_PAIR_ORDER
            or self.limitation_codes != tuple(sorted(set(self.limitation_codes)))
        ):
            raise ValueError("factor diagnostic report differs")
        expected_concentration = tuple(
            (factor_id, axis)
            for factor_id in QUANT_RESEARCH_FACTOR_ORDER
            for axis in QuantResearchFactorConcentrationAxis
        )
        if tuple((item.factor_id, item.axis) for item in self.concentration) != expected_concentration:
            raise ValueError("factor concentration order differs")
        if sum(item.available_count for item in self.factor_coverage) != self.available_factor_cell_count:
            raise ValueError("factor available cells do not reconcile")
        if sum(item.unavailable_count for item in self.factor_coverage) != self.unavailable_factor_cell_count:
            raise ValueError("factor unavailable cells do not reconcile")
        session_order = {factor_id: index for index, factor_id in enumerate(QUANT_RESEARCH_FACTOR_ORDER)}
        if self.session_availability != tuple(
            sorted(
                self.session_availability,
                key=lambda item: (item.as_of_session, session_order[item.factor_id]),
            )
        ):
            raise ValueError("factor session availability order differs")
        if factor_diagnostics_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("factor diagnostic fingerprint mismatch")
        return self


def factor_diagnostics_fingerprint(value: BaseModel | dict[str, object]) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude={"logical_fingerprint"})
    else:
        payload = dict(value)
        payload.pop("logical_fingerprint", None)
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _canonical_decimal(value: str | None) -> Decimal:
    try:
        parsed = Decimal(value) if value is not None else Decimal("NaN")
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("diagnostic value must be numeric") from exc
    if (
        not parsed.is_finite()
        or value != format(parsed.quantize(Decimal("0.0000000001")), "f")
    ):
        raise ValueError("diagnostic value must use ten decimal places")
    return parsed


def _require_ratio(
    value: str, numerator: int, denominator: int, label: str
) -> None:
    expected = (
        Decimal("0")
        if denominator == 0
        else Decimal(numerator) / Decimal(denominator)
    ).quantize(Decimal("0.0000000001"))
    if _canonical_decimal(value) != expected:
        raise ValueError(f"{label} differs")
