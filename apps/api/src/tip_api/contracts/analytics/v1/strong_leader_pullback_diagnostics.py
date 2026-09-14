"""Outcome-blind feature and signal diagnostics for Strong-Leader Pullback."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_strategy_research import STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
from .strong_leader_pullback_method import (
    STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT,
    STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT,
    STRONG_LEADER_PULLBACK_METHOD_VERSION,
    strong_leader_pullback_method_v1,
)


STRONG_LEADER_PULLBACK_DIAGNOSTICS_CONTRACT_VERSION = (
    "strong-leader-pullback-method-diagnostics/1.0"
)
STRONG_LEADER_PULLBACK_DIAGNOSTICS_EVIDENCE_TIER = (
    "reconstructed_latest_vintage_method_engineering_only"
)
STRONG_LEADER_PULLBACK_NUMERIC_DIAGNOSTIC_ORDER = (
    "relative_leadership_20s",
    "trend_quality",
    "atr_pullback_depth",
    "volume_contraction",
)
STRONG_LEADER_PULLBACK_BOOLEAN_DIAGNOSTIC_ORDER = (
    "close_above_prior_close",
    "close_above_prior_high",
)
_STRONG_LEADER_PULLBACK_METHOD_FEATURE_IDS = tuple(
    item.feature_id for item in strong_leader_pullback_method_v1().features
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DiagnosticConcentrationAxis(StrEnum):
    SESSION = "session"
    INSTRUMENT = "instrument"


class StrongLeaderPullbackDiagnosticReasonCountV1(FrozenModel):
    reason_code: str = Field(pattern=r"^[a-z0-9][a-z0-9_.:-]*$")
    count: int = Field(ge=1)


class StrongLeaderPullbackDiagnosticUnavailableFeatureV1(FrozenModel):
    feature_id: str
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unavailable_feature_reconciles(
        self,
    ) -> "StrongLeaderPullbackDiagnosticUnavailableFeatureV1":
        if (
            self.feature_id not in _STRONG_LEADER_PULLBACK_METHOD_FEATURE_IDS
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise ValueError("diagnostic unavailable feature differs")
        return self


class StrongLeaderPullbackDiagnosticExcludedPathV1(FrozenModel):
    as_of_session: date
    instrument_id: UUID
    unavailable_features: tuple[
        StrongLeaderPullbackDiagnosticUnavailableFeatureV1, ...
    ] = Field(min_length=1)
    source_max_session: date
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def path_reconciles(self) -> "StrongLeaderPullbackDiagnosticExcludedPathV1":
        feature_ids = tuple(item.feature_id for item in self.unavailable_features)
        if (
            self.source_max_session > self.as_of_session
            or feature_ids != tuple(sorted(set(feature_ids)))
        ):
            raise ValueError("diagnostic excluded path differs")
        return self


class StrongLeaderPullbackFeatureCoverageV1(FrozenModel):
    feature_id: str
    source_available_count: int = Field(ge=0)
    source_unavailable_count: int = Field(ge=0)
    complete_distribution_observation_count: int = Field(ge=0)
    availability_rate: str
    unavailable_reason_counts: tuple[
        StrongLeaderPullbackDiagnosticReasonCountV1, ...
    ]

    @model_validator(mode="after")
    def reasons_reconcile(self) -> "StrongLeaderPullbackFeatureCoverageV1":
        reason_codes = tuple(item.reason_code for item in self.unavailable_reason_counts)
        if reason_codes != tuple(sorted(set(reason_codes))):
            raise ValueError("feature coverage reason order differs")
        return self


class StrongLeaderPullbackNumericDiagnosticV1(FrozenModel):
    feature_id: str
    observation_count: int = Field(ge=0)
    distinct_value_count: int = Field(ge=0)
    duplicate_excess_count: int = Field(ge=0)
    duplicate_excess_rate: str
    minimum: str | None = None
    p05: str | None = None
    p25: str | None = None
    median: str | None = None
    p75: str | None = None
    p95: str | None = None
    maximum: str | None = None

    @model_validator(mode="after")
    def distribution_reconciles(self) -> "StrongLeaderPullbackNumericDiagnosticV1":
        values = (
            self.minimum,
            self.p05,
            self.p25,
            self.median,
            self.p75,
            self.p95,
            self.maximum,
        )
        if self.distinct_value_count > self.observation_count or (
            self.duplicate_excess_count
            != self.observation_count - self.distinct_value_count
        ):
            raise ValueError("numeric diagnostic counts differ")
        _require_ratio(
            self.duplicate_excess_rate,
            self.duplicate_excess_count,
            self.observation_count,
            "numeric duplicate rate",
        )
        if self.observation_count == 0:
            if any(item is not None for item in values):
                raise ValueError("empty numeric diagnostic cannot carry values")
            return self
        if any(item is None for item in values):
            raise ValueError("populated numeric diagnostic lacks quantiles")
        decimals = tuple(_finite_decimal(item, "numeric diagnostic") for item in values)
        if decimals != tuple(sorted(decimals)):
            raise ValueError("numeric diagnostic quantiles are not monotonic")
        return self


class StrongLeaderPullbackBooleanDiagnosticV1(FrozenModel):
    feature_id: str
    observation_count: int = Field(ge=0)
    true_count: int = Field(ge=0)
    false_count: int = Field(ge=0)
    true_rate: str

    @model_validator(mode="after")
    def boolean_reconciles(self) -> "StrongLeaderPullbackBooleanDiagnosticV1":
        if self.true_count + self.false_count != self.observation_count:
            raise ValueError("boolean diagnostic counts differ")
        _require_ratio(
            self.true_rate,
            self.true_count,
            self.observation_count,
            "boolean true rate",
        )
        return self


class StrongLeaderPullbackCategoryCountV1(FrozenModel):
    category: str
    count: int = Field(ge=1)


class StrongLeaderPullbackThresholdProximityV1(FrozenModel):
    feature_id: str
    tolerance: str
    thresholds: tuple[str, ...] = Field(min_length=1)
    observation_count: int = Field(ge=0)
    near_threshold_count: int = Field(ge=0)
    near_threshold_rate: str

    @model_validator(mode="after")
    def proximity_reconciles(self) -> "StrongLeaderPullbackThresholdProximityV1":
        if (
            self.near_threshold_count > self.observation_count
            or self.thresholds != tuple(sorted(set(self.thresholds), key=Decimal))
            or _finite_decimal(self.tolerance, "threshold tolerance") <= 0
        ):
            raise ValueError("threshold proximity differs")
        _require_ratio(
            self.near_threshold_rate,
            self.near_threshold_count,
            self.observation_count,
            "near-threshold rate",
        )
        return self


class StrongLeaderPullbackConcentrationV1(FrozenModel):
    axis: DiagnosticConcentrationAxis
    observation_count: int = Field(ge=0)
    group_count: int = Field(ge=0)
    maximum_group_count: int = Field(ge=0)
    maximum_group_share: str
    top_ten_group_share: str
    herfindahl_index: str

    @model_validator(mode="after")
    def concentration_reconciles(self) -> "StrongLeaderPullbackConcentrationV1":
        if (
            self.group_count > self.observation_count
            or self.maximum_group_count > self.observation_count
            or (self.observation_count > 0 and self.group_count == 0)
            or (
                self.observation_count == 0
                and (self.group_count != 0 or self.maximum_group_count != 0)
            )
        ):
            raise ValueError("diagnostic concentration counts differ")
        for value in (
            self.maximum_group_share,
            self.top_ten_group_share,
            self.herfindahl_index,
        ):
            parsed = _finite_decimal(value, "diagnostic concentration")
            if parsed < 0 or parsed > 1:
                raise ValueError("diagnostic concentration is outside zero to one")
        maximum_share = _finite_decimal(
            self.maximum_group_share, "maximum group share"
        )
        top_ten_share = _finite_decimal(
            self.top_ten_group_share, "top ten group share"
        )
        expected_maximum_share = (
            Decimal("0")
            if self.observation_count == 0
            else (
                Decimal(self.maximum_group_count) / Decimal(self.observation_count)
            ).quantize(Decimal("0.0001"))
        )
        if (
            maximum_share != expected_maximum_share
            or self.maximum_group_share != format(expected_maximum_share, "f")
            or top_ten_share < maximum_share
        ):
            raise ValueError("diagnostic concentration shares differ")
        return self


class StrongLeaderPullbackCombinationDiagnosticV1(FrozenModel):
    parameter_combination_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    signal_count: int = Field(ge=0)
    eligible_leader_control_count: int = Field(ge=0)
    excluded_chronological_boundary_count: int = Field(ge=0)
    excluded_membership_count: int = Field(ge=0)
    excluded_not_leader_count: int = Field(ge=0)
    unavailable_input_count: int = Field(ge=0)
    signal_rate_among_eligible_leaders: str
    distinct_signal_session_count: int = Field(ge=0)
    distinct_signal_instrument_count: int = Field(ge=0)

    @model_validator(mode="after")
    def signal_distinct_counts_reconcile(
        self,
    ) -> "StrongLeaderPullbackCombinationDiagnosticV1":
        if (
            self.distinct_signal_session_count > self.signal_count
            or self.distinct_signal_instrument_count > self.signal_count
        ):
            raise ValueError("combination signal distinct counts differ")
        return self


class StrongLeaderPullbackMethodDiagnosticsV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        STRONG_LEADER_PULLBACK_DIAGNOSTICS_CONTRACT_VERSION
    ] = STRONG_LEADER_PULLBACK_DIAGNOSTICS_CONTRACT_VERSION
    method_version: Literal[STRONG_LEADER_PULLBACK_METHOD_VERSION] = (
        STRONG_LEADER_PULLBACK_METHOD_VERSION
    )
    method_fingerprint: Literal[STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT] = (
        STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT
    )
    experiment_fingerprint: Literal[STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT] = (
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    )
    input_feature_fingerprint: Literal[
        STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT
    ] = STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT
    evidence_tier: Literal[
        STRONG_LEADER_PULLBACK_DIAGNOSTICS_EVIDENCE_TIER
    ] = STRONG_LEADER_PULLBACK_DIAGNOSTICS_EVIDENCE_TIER
    as_operated: Literal[False] = False
    chronological_plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_population_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    first_session: date
    last_session: date
    session_count: int = Field(ge=1)
    expected_path_count: int = Field(ge=0)
    complete_observation_count: int = Field(ge=0)
    excluded_path_count: int = Field(ge=0)
    feature_coverage: tuple[StrongLeaderPullbackFeatureCoverageV1, ...]
    numeric_diagnostics: tuple[StrongLeaderPullbackNumericDiagnosticV1, ...]
    boolean_diagnostics: tuple[StrongLeaderPullbackBooleanDiagnosticV1, ...]
    market_regime_counts: tuple[StrongLeaderPullbackCategoryCountV1, ...]
    threshold_proximity: tuple[StrongLeaderPullbackThresholdProximityV1, ...]
    observation_concentration: tuple[
        StrongLeaderPullbackConcentrationV1,
        StrongLeaderPullbackConcentrationV1,
    ]
    parameter_combinations: tuple[StrongLeaderPullbackCombinationDiagnosticV1, ...]
    limitation_codes: tuple[str, ...] = Field(min_length=1)
    contains_outcome_blind_trigger_counts: Literal[True] = True
    contains_forward_outcomes: Literal[False] = False
    contains_performance_metrics: Literal[False] = False
    trigger_counts_reusable_for_parameter_selection: Literal[False] = False
    parameter_selection_authorized: Literal[False] = False
    formal_development_authorized: Literal[False] = False
    validation_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def report_reconciles(self) -> "StrongLeaderPullbackMethodDiagnosticsV1":
        if (
            self.first_session > self.last_session
            or self.expected_path_count
            != self.complete_observation_count + self.excluded_path_count
            or tuple(item.feature_id for item in self.feature_coverage)
            != _STRONG_LEADER_PULLBACK_METHOD_FEATURE_IDS
            or tuple(item.feature_id for item in self.numeric_diagnostics)
            != STRONG_LEADER_PULLBACK_NUMERIC_DIAGNOSTIC_ORDER
            or tuple(item.feature_id for item in self.boolean_diagnostics)
            != STRONG_LEADER_PULLBACK_BOOLEAN_DIAGNOSTIC_ORDER
            or tuple(item.feature_id for item in self.threshold_proximity)
            != STRONG_LEADER_PULLBACK_NUMERIC_DIAGNOSTIC_ORDER
            or tuple(item.axis for item in self.observation_concentration)
            != (
                DiagnosticConcentrationAxis.SESSION,
                DiagnosticConcentrationAxis.INSTRUMENT,
            )
            or len(self.parameter_combinations) != 24
            or tuple(
                item.parameter_combination_id for item in self.parameter_combinations
            )
            != tuple(
                sorted(
                    {
                        item.parameter_combination_id
                        for item in self.parameter_combinations
                    }
                )
            )
            or tuple(item.category for item in self.market_regime_counts)
            != tuple(sorted({item.category for item in self.market_regime_counts}))
            or self.limitation_codes != tuple(sorted(set(self.limitation_codes)))
        ):
            raise ValueError("Strong-Leader Pullback diagnostics differ")
        for item in self.feature_coverage:
            if (
                item.source_available_count + item.source_unavailable_count
                != self.expected_path_count
                or item.complete_distribution_observation_count
                != self.complete_observation_count
            ):
                raise ValueError("diagnostic feature coverage counts differ")
            _require_ratio(
                item.availability_rate,
                item.source_available_count,
                self.expected_path_count,
                "feature availability rate",
            )
        if any(
            item.observation_count != self.complete_observation_count
            for item in (*self.numeric_diagnostics, *self.boolean_diagnostics)
        ) or any(
            item.observation_count != self.complete_observation_count
            for item in (*self.observation_concentration, *self.threshold_proximity)
        ):
            raise ValueError("diagnostic observation counts differ")
        if sum(item.count for item in self.market_regime_counts) != (
            self.complete_observation_count
        ):
            raise ValueError("diagnostic Regime counts differ")
        for item in self.parameter_combinations:
            classified_count = (
                item.signal_count
                + item.eligible_leader_control_count
                + item.excluded_chronological_boundary_count
                + item.excluded_membership_count
                + item.excluded_not_leader_count
                + item.unavailable_input_count
            )
            if classified_count != self.expected_path_count:
                raise ValueError("diagnostic combination counts differ")
            _require_ratio(
                item.signal_rate_among_eligible_leaders,
                item.signal_count,
                item.signal_count + item.eligible_leader_control_count,
                "combination signal rate",
            )
        if strong_leader_pullback_diagnostics_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("Strong-Leader Pullback diagnostics fingerprint mismatch")
        return self


def strong_leader_pullback_diagnostics_fingerprint(
    value: BaseModel | dict[str, object],
) -> str:
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
        ).encode("utf-8")
    ).hexdigest()


def _finite_decimal(value: str | None, label: str) -> Decimal:
    try:
        parsed = Decimal(value) if value is not None else Decimal("NaN")
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not parsed.is_finite():
        raise ValueError(f"{label} must be finite")
    return parsed


def _require_ratio(value: str, numerator: int, denominator: int, label: str) -> None:
    expected = (
        Decimal("0")
        if denominator == 0
        else (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0001"))
    )
    if _finite_decimal(value, label) != expected or value != format(expected, "f"):
        raise ValueError(f"{label} differs")
