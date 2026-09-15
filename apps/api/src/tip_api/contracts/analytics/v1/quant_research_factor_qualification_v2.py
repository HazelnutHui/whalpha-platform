"""Frozen outcome-blind qualification protocol and report for Factor Catalog V2."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from functools import lru_cache
from itertools import combinations
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_discovery_trial_ledger import (
    quant_research_discovery_trial_ledger_v1,
)
from .quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
    QuantResearchFactorRoleV2,
    quant_research_factor_catalog_v2,
)


QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_PROTOCOL_CONTRACT_VERSION = (
    "quant-research-factor-qualification-protocol/2.0"
)
QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_PROTOCOL_VERSION = (
    "quant-research-factor-qualification/2.0.0"
)
QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_REPORT_CONTRACT_VERSION = (
    "quant-research-factor-qualification-report/2.0"
)
QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_EVIDENCE_TIER = (
    "reconstructed_latest_vintage_outcome_blind_only"
)
QUANT_RESEARCH_FACTOR_V2_PAIR_ORDER = tuple(
    combinations(QUANT_RESEARCH_FACTOR_V2_ORDER, 2)
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchFactorQualificationV2Status(StrEnum):
    READY_FOR_SCREENING_PROTOCOL_REVIEW = "ready_for_screening_protocol_review"
    REQUIRES_OUTCOME_BLIND_REDUNDANCY_ADJUDICATION = (
        "requires_outcome_blind_redundancy_adjudication"
    )
    REJECTED_DATA_OR_IMPLEMENTATION = "rejected_data_or_implementation"


class QuantResearchFactorQualificationV2Decision(StrEnum):
    ELIGIBLE_FOR_SCREENING_PROTOCOL_REVIEW = (
        "eligible_for_screening_protocol_review"
    )
    REJECTED_QUALIFICATION = "rejected_qualification"


class QuantResearchFactorConcentrationAxisV2(StrEnum):
    SESSION = "session"
    INSTRUMENT = "instrument"


class QuantResearchFactorQualificationProtocolV2(FrozenModel):
    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[
        QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_PROTOCOL_CONTRACT_VERSION
    ] = QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_PROTOCOL_CONTRACT_VERSION
    protocol_version: Literal[
        QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_PROTOCOL_VERSION
    ] = QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_PROTOCOL_VERSION
    registered_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    prior_discovery_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_signal_session_count: Literal[287] = 287
    expected_signal_path_count: Literal[437402] = 437402
    source_window_sessions: Literal[127] = 127
    signal_membership_rule: Literal[
        "reconstructed_membership_at_signal_session_only"
    ] = "reconstructed_membership_at_signal_session_only"
    pre_signal_membership_projection_prohibited: Literal[True] = True
    benchmark_failure_rule: Literal["exclude_complete_signal_session"] = (
        "exclude_complete_signal_session"
    )
    instrument_failure_rule: Literal[
        "quarantine_only_affected_stable_instrument_id"
    ] = "quarantine_only_affected_stable_instrument_id"
    minimum_factor_availability_rate: Literal["0.9000000000"] = "0.9000000000"
    minimum_factor_eligible_session_count: Literal[250] = 250
    minimum_factor_first_half_session_count: Literal[120] = 120
    minimum_factor_second_half_session_count: Literal[120] = 120
    minimum_instruments_per_eligible_session: Literal[100] = 100
    minimum_distinct_factor_values: Literal[100] = 100
    maximum_same_session_tie_excess_rate: Literal["0.9500000000"] = (
        "0.9500000000"
    )
    minimum_candidate_alpha_factors_after_redundancy: Literal[2] = 2
    pair_minimum_observations_per_session: Literal[100] = 100
    near_duplicate_minimum_sessions: Literal[60] = 60
    near_duplicate_absolute_spearman: Literal["0.9000000000"] = "0.9000000000"
    near_duplicate_session_share: Literal["0.8000000000"] = "0.8000000000"
    near_duplicate_dominant_sign_share: Literal["0.9000000000"] = (
        "0.9000000000"
    )
    near_duplicate_resolution_rule: Literal[
        "within_related_group_keep_lowest_preregistered_redundancy_priority"
    ] = "within_related_group_keep_lowest_preregistered_redundancy_priority"
    cross_group_near_duplicate_rule: Literal[
        "retain_for_review_and_block_outcome_protocol_until_adjudicated"
    ] = "retain_for_review_and_block_outcome_protocol_until_adjudicated"
    distribution_quantiles: tuple[
        Literal["p01"],
        Literal["p05"],
        Literal["p25"],
        Literal["p50"],
        Literal["p75"],
        Literal["p95"],
        Literal["p99"],
    ] = ("p01", "p05", "p25", "p50", "p75", "p95", "p99")
    outlier_rule: Literal["outside_three_interquartile_ranges"] = (
        "outside_three_interquartile_ranges"
    )
    reproducibility_rule: Literal["one_report_plus_one_exact_full_replay"] = (
        "one_report_plus_one_exact_full_replay"
    )
    real_factor_values_not_read_before_protocol: Literal[True] = True
    contains_forward_outcomes: Literal[False] = False
    contains_performance_metrics: Literal[False] = False
    development_outcome_read_authorized: Literal[False] = False
    factor_screening_authorized: Literal[False] = False
    factor_admission_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    strategy_expression_authorized: Literal[False] = False
    validation_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    external_request_authorized: Literal[False] = False
    canonical_data_write_authorized: Literal[False] = False
    production_write_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def protocol_reconciles(self) -> "QuantResearchFactorQualificationProtocolV2":
        if (
            self.catalog_fingerprint
            != quant_research_factor_catalog_v2().logical_fingerprint
            or self.prior_discovery_ledger_fingerprint
            != quant_research_discovery_trial_ledger_v1().logical_fingerprint
            or factor_qualification_v2_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("Factor Catalog V2 qualification protocol differs")
        return self


class QuantResearchFactorReasonCountV2(FrozenModel):
    reason_code: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    count: int = Field(ge=1)


class QuantResearchFactorCoverageV2(FrozenModel):
    factor_id: str
    expected_count: int = Field(ge=0)
    available_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)
    availability_rate: str
    eligible_session_count: int = Field(ge=0)
    first_half_eligible_session_count: int = Field(ge=0)
    second_half_eligible_session_count: int = Field(ge=0)
    unavailable_reason_counts: tuple[QuantResearchFactorReasonCountV2, ...]

    @model_validator(mode="after")
    def coverage_reconciles(self) -> "QuantResearchFactorCoverageV2":
        if (
            self.factor_id not in QUANT_RESEARCH_FACTOR_V2_ORDER
            or self.available_count + self.unavailable_count != self.expected_count
            or self.first_half_eligible_session_count
            + self.second_half_eligible_session_count
            != self.eligible_session_count
            or tuple(item.reason_code for item in self.unavailable_reason_counts)
            != tuple(sorted({item.reason_code for item in self.unavailable_reason_counts}))
        ):
            raise ValueError("Factor Catalog V2 coverage differs")
        _require_ratio(
            self.availability_rate,
            self.available_count,
            self.expected_count,
            "Factor Catalog V2 availability rate",
        )
        return self


class QuantResearchFactorDistributionV2(FrozenModel):
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
    outer_outlier_count: int = Field(ge=0)
    outer_outlier_rate: str

    @model_validator(mode="after")
    def distribution_reconciles(self) -> "QuantResearchFactorDistributionV2":
        ordered = (
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
            self.factor_id not in QUANT_RESEARCH_FACTOR_V2_ORDER
            or self.distinct_value_count > self.observation_count
            or self.same_session_tie_excess_count > self.observation_count
            or self.outer_outlier_count > self.observation_count
        ):
            raise ValueError("Factor Catalog V2 distribution counts differ")
        _require_ratio(
            self.same_session_tie_excess_rate,
            self.same_session_tie_excess_count,
            self.observation_count,
            "Factor Catalog V2 tie rate",
        )
        _require_ratio(
            self.outer_outlier_rate,
            self.outer_outlier_count,
            self.observation_count,
            "Factor Catalog V2 outlier rate",
        )
        if self.observation_count == 0:
            if any(item is not None for item in ordered):
                raise ValueError("empty Factor Catalog V2 distribution carries values")
        elif any(item is None for item in ordered) or tuple(
            _canonical_decimal(item) for item in ordered
        ) != tuple(sorted(_canonical_decimal(item) for item in ordered)):
            raise ValueError("Factor Catalog V2 distribution quantiles differ")
        return self


class QuantResearchFactorConcentrationV2(FrozenModel):
    factor_id: str
    axis: QuantResearchFactorConcentrationAxisV2
    observation_count: int = Field(ge=0)
    group_count: int = Field(ge=0)
    maximum_group_count: int = Field(ge=0)
    maximum_group_share: str
    top_ten_group_share: str
    herfindahl_index: str

    @model_validator(mode="after")
    def concentration_reconciles(self) -> "QuantResearchFactorConcentrationV2":
        if (
            self.factor_id not in QUANT_RESEARCH_FACTOR_V2_ORDER
            or self.group_count > self.observation_count
            or self.maximum_group_count > self.observation_count
        ):
            raise ValueError("Factor Catalog V2 concentration differs")
        for value in (
            self.maximum_group_share,
            self.top_ten_group_share,
            self.herfindahl_index,
        ):
            parsed = _canonical_decimal(value)
            if not Decimal("0") <= parsed <= Decimal("1"):
                raise ValueError("Factor Catalog V2 concentration ratio differs")
        return self


class QuantResearchFactorPairCorrelationV2(FrozenModel):
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
    def pair_reconciles(self) -> "QuantResearchFactorPairCorrelationV2":
        if (
            (self.left_factor_id, self.right_factor_id)
            not in QUANT_RESEARCH_FACTOR_V2_PAIR_ORDER
            or self.high_absolute_correlation_session_count
            > self.eligible_session_count
            or self.positive_session_count
            + self.negative_session_count
            + self.zero_session_count
            != self.eligible_session_count
        ):
            raise ValueError("Factor Catalog V2 pair counts differ")
        for value in (
            self.high_absolute_correlation_session_share,
            self.dominant_sign_session_share,
        ):
            parsed = _canonical_decimal(value)
            if not Decimal("0") <= parsed <= Decimal("1"):
                raise ValueError("Factor Catalog V2 pair share differs")
        values = (
            self.weighted_mean_spearman,
            self.median_session_spearman,
            self.p05_session_spearman,
            self.p95_session_spearman,
        )
        if self.eligible_session_count == 0:
            if any(value is not None for value in values) or self.near_duplicate:
                raise ValueError("empty Factor Catalog V2 pair carries correlation")
        elif any(value is None for value in values):
            raise ValueError("eligible Factor Catalog V2 pair lacks correlation")
        for value in values:
            if value is not None and not Decimal("-1") <= _canonical_decimal(
                value
            ) <= Decimal("1"):
                raise ValueError("Factor Catalog V2 correlation differs")
        return self


class QuantResearchFactorQualificationDecisionV2(FrozenModel):
    factor_id: str
    role: QuantResearchFactorRoleV2
    decision: QuantResearchFactorQualificationV2Decision
    reason_codes: tuple[str, ...]
    lower_priority_near_duplicate_of: str | None = None
    outcome_trial_registered: Literal[False] = False
    factor_admission_authorized: Literal[False] = False

    @model_validator(mode="after")
    def decision_reconciles(self) -> "QuantResearchFactorQualificationDecisionV2":
        catalog = quant_research_factor_catalog_v2()
        definition = next(
            (item for item in catalog.definitions if item.factor_id == self.factor_id),
            None,
        )
        if (
            definition is None
            or self.role is not definition.role
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise ValueError("Factor Catalog V2 qualification decision differs")
        eligible = (
            self.decision
            is QuantResearchFactorQualificationV2Decision.ELIGIBLE_FOR_SCREENING_PROTOCOL_REVIEW
        )
        if eligible != (not self.reason_codes and self.lower_priority_near_duplicate_of is None):
            raise ValueError("Factor Catalog V2 qualification disposition differs")
        return self


class QuantResearchFactorQualificationReportV2(FrozenModel):
    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[
        QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_REPORT_CONTRACT_VERSION
    ] = QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_REPORT_CONTRACT_VERSION
    protocol_version: Literal[
        QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_PROTOCOL_VERSION
    ] = QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_PROTOCOL_VERSION
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_tier: Literal[QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_EVIDENCE_TIER] = (
        QUANT_RESEARCH_FACTOR_QUALIFICATION_V2_EVIDENCE_TIER
    )
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    prior_discovery_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    chronological_plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_population_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_eod_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_action_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calculation_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    diagnostic_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    first_source_session: date
    first_signal_session: date
    last_signal_session: date
    signal_session_count: int = Field(ge=1)
    expected_path_count: int = Field(ge=0)
    complete_factor_vector_count: int = Field(ge=0)
    incomplete_factor_vector_count: int = Field(ge=0)
    expected_factor_cell_count: int = Field(ge=0)
    available_factor_cell_count: int = Field(ge=0)
    unavailable_factor_cell_count: int = Field(ge=0)
    factor_coverage: tuple[QuantResearchFactorCoverageV2, ...] = Field(
        min_length=8, max_length=8
    )
    distributions: tuple[QuantResearchFactorDistributionV2, ...] = Field(
        min_length=8, max_length=8
    )
    concentration: tuple[QuantResearchFactorConcentrationV2, ...] = Field(
        min_length=16, max_length=16
    )
    pairwise_same_session_spearman: tuple[
        QuantResearchFactorPairCorrelationV2, ...
    ] = Field(min_length=28, max_length=28)
    decisions: tuple[QuantResearchFactorQualificationDecisionV2, ...] = Field(
        min_length=8, max_length=8
    )
    eligible_candidate_alpha_count: int = Field(ge=0, le=4)
    eligible_setup_conditioner_count: int = Field(ge=0, le=1)
    eligible_applicability_input_count: int = Field(ge=0, le=1)
    eligible_risk_guard_count: int = Field(ge=0, le=2)
    cross_group_near_duplicate_pairs: tuple[tuple[str, str], ...]
    status: QuantResearchFactorQualificationV2Status
    limitation_codes: tuple[str, ...] = Field(min_length=1)
    contains_forward_outcomes: Literal[False] = False
    contains_performance_metrics: Literal[False] = False
    development_outcome_read_count: Literal[0] = 0
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
    def report_reconciles(self) -> "QuantResearchFactorQualificationReportV2":
        protocol = quant_research_factor_qualification_protocol_v2()
        factor_count = len(QUANT_RESEARCH_FACTOR_V2_ORDER)
        if (
            self.protocol_fingerprint != protocol.logical_fingerprint
            or self.catalog_fingerprint != protocol.catalog_fingerprint
            or self.prior_discovery_ledger_fingerprint
            != protocol.prior_discovery_ledger_fingerprint
            or not self.first_source_session
            < self.first_signal_session
            <= self.last_signal_session
            or self.signal_session_count != protocol.expected_signal_session_count
            or self.expected_path_count != protocol.expected_signal_path_count
            or self.complete_factor_vector_count
            + self.incomplete_factor_vector_count
            != self.expected_path_count
            or self.expected_factor_cell_count != self.expected_path_count * factor_count
            or self.available_factor_cell_count + self.unavailable_factor_cell_count
            != self.expected_factor_cell_count
            or tuple(item.factor_id for item in self.factor_coverage)
            != QUANT_RESEARCH_FACTOR_V2_ORDER
            or tuple(item.factor_id for item in self.distributions)
            != QUANT_RESEARCH_FACTOR_V2_ORDER
            or tuple(item.factor_id for item in self.decisions)
            != QUANT_RESEARCH_FACTOR_V2_ORDER
            or tuple(
                (item.left_factor_id, item.right_factor_id)
                for item in self.pairwise_same_session_spearman
            )
            != QUANT_RESEARCH_FACTOR_V2_PAIR_ORDER
            or self.limitation_codes != tuple(sorted(set(self.limitation_codes)))
            or self.cross_group_near_duplicate_pairs
            != tuple(sorted(set(self.cross_group_near_duplicate_pairs)))
        ):
            raise ValueError("Factor Catalog V2 qualification report differs")
        expected_concentration = tuple(
            (factor_id, axis)
            for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
            for axis in QuantResearchFactorConcentrationAxisV2
        )
        if tuple(
            (item.factor_id, item.axis) for item in self.concentration
        ) != expected_concentration:
            raise ValueError("Factor Catalog V2 concentration order differs")
        if (
            sum(item.available_count for item in self.factor_coverage)
            != self.available_factor_cell_count
            or sum(item.unavailable_count for item in self.factor_coverage)
            != self.unavailable_factor_cell_count
        ):
            raise ValueError("Factor Catalog V2 factor cells do not reconcile")
        role_counts = {
            role: sum(
                item.decision
                is QuantResearchFactorQualificationV2Decision.ELIGIBLE_FOR_SCREENING_PROTOCOL_REVIEW
                and item.role is role
                for item in self.decisions
            )
            for role in QuantResearchFactorRoleV2
        }
        if role_counts != {
            QuantResearchFactorRoleV2.CANDIDATE_ALPHA: self.eligible_candidate_alpha_count,
            QuantResearchFactorRoleV2.SETUP_CONDITIONER: self.eligible_setup_conditioner_count,
            QuantResearchFactorRoleV2.APPLICABILITY_INPUT: self.eligible_applicability_input_count,
            QuantResearchFactorRoleV2.RISK_GUARD: self.eligible_risk_guard_count,
        }:
            raise ValueError("Factor Catalog V2 eligible role counts differ")
        if self.cross_group_near_duplicate_pairs:
            expected_status = (
                QuantResearchFactorQualificationV2Status
                .REQUIRES_OUTCOME_BLIND_REDUNDANCY_ADJUDICATION
            )
        elif (
            self.eligible_candidate_alpha_count
            >= protocol.minimum_candidate_alpha_factors_after_redundancy
        ):
            expected_status = (
                QuantResearchFactorQualificationV2Status
                .READY_FOR_SCREENING_PROTOCOL_REVIEW
            )
        else:
            expected_status = (
                QuantResearchFactorQualificationV2Status
                .REJECTED_DATA_OR_IMPLEMENTATION
            )
        if self.status is not expected_status:
            raise ValueError("Factor Catalog V2 qualification status differs")
        ready = (
            self.eligible_candidate_alpha_count
            >= protocol.minimum_candidate_alpha_factors_after_redundancy
            and not self.cross_group_near_duplicate_pairs
        )
        if ready != (
            expected_status
            is QuantResearchFactorQualificationV2Status
            .READY_FOR_SCREENING_PROTOCOL_REVIEW
        ):
            raise ValueError("Factor Catalog V2 qualification status differs")
        if factor_qualification_v2_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("Factor Catalog V2 qualification fingerprint differs")
        return self


@lru_cache(maxsize=1)
def quant_research_factor_qualification_protocol_v2() -> QuantResearchFactorQualificationProtocolV2:
    payload = {
        "catalog_fingerprint": quant_research_factor_catalog_v2().logical_fingerprint,
        "prior_discovery_ledger_fingerprint": (
            quant_research_discovery_trial_ledger_v1().logical_fingerprint
        ),
    }
    provisional = QuantResearchFactorQualificationProtocolV2.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchFactorQualificationProtocolV2.model_validate(
        {
            **payload,
            "logical_fingerprint": factor_qualification_v2_fingerprint(provisional),
        }
    )


def factor_qualification_v2_fingerprint(value: BaseModel | dict[str, object]) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude={"logical_fingerprint"})
    else:
        payload = {key: item for key, item in value.items() if key != "logical_fingerprint"}
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
        raise ValueError("Factor Catalog V2 diagnostic value must be numeric") from exc
    if not parsed.is_finite() or value != format(
        parsed.quantize(Decimal("0.0000000001")), "f"
    ):
        raise ValueError("Factor Catalog V2 value must use ten decimal places")
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
