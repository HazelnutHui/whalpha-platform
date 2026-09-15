"""Development-only outcome and report contracts for Factor Catalog V1 screening."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .quant_research_factor_catalog import (
    QuantResearchFactorRole,
    quant_research_factor_catalog_v1,
)
from .quant_research_factor_screening import (
    QUANT_RESEARCH_FACTOR_SCREENING_PROTOCOL_VERSION,
    QuantResearchFactorScreeningTarget,
    factor_screening_fingerprint,
    quant_research_factor_screening_protocol_v1,
)


QUANT_RESEARCH_FACTOR_SCREENING_LABEL_CONTRACT_VERSION = (
    "quant-research-factor-screening-label/1.0"
)
QUANT_RESEARCH_FACTOR_SCREENING_REPORT_CONTRACT_VERSION = (
    "quant-research-factor-screening-report/1.0"
)
QUANT_RESEARCH_FACTOR_SCREENING_RESULT_ORDER = (
    (factor.factor_id, horizon, endpoint)
    for factor in quant_research_factor_screening_protocol_v1().formal_hypotheses
    for horizon in (1, 3, 5)
    for endpoint in (
        ("lower", "upper")
        if factor.role is QuantResearchFactorRole.CANDIDATE_ALPHA
        else ("complete_path",)
    )
)
QUANT_RESEARCH_FACTOR_SCREENING_RESULT_ORDER = tuple(
    QUANT_RESEARCH_FACTOR_SCREENING_RESULT_ORDER
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchFactorScreeningLabelState(StrEnum):
    OBSERVED_EOD_EXACT = "observed_eod_exact"
    TERMINAL_REFERENCE_EXACT = "terminal_reference_exact"
    TERMINAL_REFERENCE_INTERVAL = "terminal_reference_interval"
    UNEXECUTABLE_NO_NEXT_OPEN = "unexecutable_no_next_open"
    UNAVAILABLE_EVIDENCE = "unavailable_evidence"


class QuantResearchFactorScreeningEndpoint(StrEnum):
    LOWER = "lower"
    UPPER = "upper"
    COMPLETE_PATH = "complete_path"


class QuantResearchFactorScreeningDecisionStatus(StrEnum):
    SELECTED_MODEL_CANDIDATE = "selected_model_candidate"
    QUALIFIED_NOT_SELECTED_CAP = "qualified_not_selected_cap"
    REJECTED_SCREEN = "rejected_screen"
    INCONCLUSIVE_DATA = "inconclusive_data"


class QuantResearchFactorScreeningReportStatus(StrEnum):
    READY_FOR_MODEL_PROTOCOL_REVIEW = "ready_for_model_protocol_review"
    CLOSED_NO_CANDIDATE_ALPHA = "closed_no_candidate_alpha"
    INCONCLUSIVE_DATA = "inconclusive_data"


class QuantResearchFactorScreeningLabelV1(FrozenModel):
    contract_version: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_LABEL_CONTRACT_VERSION
    ] = QUANT_RESEARCH_FACTOR_SCREENING_LABEL_CONTRACT_VERSION
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    signal_session: date
    instrument_id: UUID
    display_ticker: str | None = None
    horizon_sessions: Literal[1, 3, 5]
    expected_entry_session: date
    expected_exit_session: date
    expected_path_sessions: tuple[date, ...] = Field(min_length=1, max_length=5)
    split_basis_session: date
    state: QuantResearchFactorScreeningLabelState
    entry_price_usd: str | None = None
    exit_price_lower_usd: str | None = None
    exit_price_upper_usd: str | None = None
    underlying_price_return_lower: str | None = None
    underlying_price_return_upper: str | None = None
    benchmark_price_return: str | None = None
    relative_to_benchmark_return_lower: str | None = None
    relative_to_benchmark_return_upper: str | None = None
    maximum_favorable_excursion: str | None = None
    maximum_adverse_excursion: str | None = None
    source_eod_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_reference_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    reason_codes: tuple[str, ...]
    reconstructed_latest_vintage: Literal[True] = True
    development_only: Literal[True] = True
    prior_strategy_outcome_reused: Literal[False] = False
    underlying_stock_result_not_option_return: Literal[True] = True
    transaction_costs_not_applied: Literal[True] = True
    point_imputation_used: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_unique_and_sorted(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("screening-label reasons must be unique and sorted")
        return values

    @model_validator(mode="after")
    def label_reconciles(self) -> "QuantResearchFactorScreeningLabelV1":
        protocol = quant_research_factor_screening_protocol_v1()
        if (
            self.protocol_fingerprint != protocol.logical_fingerprint
            or self.catalog_fingerprint != protocol.catalog_fingerprint
            or len(self.expected_path_sessions) != self.horizon_sessions
            or self.expected_path_sessions
            != tuple(sorted(set(self.expected_path_sessions)))
            or self.expected_path_sessions[0] != self.expected_entry_session
            or self.expected_path_sessions[-1] != self.expected_exit_session
            or not self.signal_session < self.expected_entry_session <= self.expected_exit_session
            or self.split_basis_session < self.expected_exit_session
        ):
            raise ValueError("screening-label identity or sessions differ")
        numeric = (
            self.entry_price_usd,
            self.exit_price_lower_usd,
            self.exit_price_upper_usd,
            self.underlying_price_return_lower,
            self.underlying_price_return_upper,
            self.benchmark_price_return,
            self.relative_to_benchmark_return_lower,
            self.relative_to_benchmark_return_upper,
        )
        nonnumeric = self.state in {
            QuantResearchFactorScreeningLabelState.UNEXECUTABLE_NO_NEXT_OPEN,
            QuantResearchFactorScreeningLabelState.UNAVAILABLE_EVIDENCE,
        }
        if nonnumeric:
            if (
                any(value is not None for value in numeric)
                or self.maximum_favorable_excursion is not None
                or self.maximum_adverse_excursion is not None
                or not self.reason_codes
            ):
                raise ValueError("nonnumeric screening label carries outcomes")
        else:
            if any(value is None for value in numeric):
                raise ValueError("numeric screening label is incomplete")
            entry = _decimal(self.entry_price_usd)
            lower_exit = _decimal(self.exit_price_lower_usd)
            upper_exit = _decimal(self.exit_price_upper_usd)
            lower_return = _decimal(self.underlying_price_return_lower)
            upper_return = _decimal(self.underlying_price_return_upper)
            benchmark = _decimal(self.benchmark_price_return)
            lower_relative = _decimal(self.relative_to_benchmark_return_lower)
            upper_relative = _decimal(self.relative_to_benchmark_return_upper)
            if (
                entry <= 0
                or lower_exit < 0
                or lower_exit > upper_exit
                or lower_return != _return(lower_exit, entry)
                or upper_return != _return(upper_exit, entry)
                or lower_relative != _quantize(lower_return - benchmark)
                or upper_relative != _quantize(upper_return - benchmark)
            ):
                raise ValueError("screening-label arithmetic differs")
            interval = (
                self.state
                is QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_INTERVAL
            )
            terminal = self.state in {
                QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_EXACT,
                QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_INTERVAL,
            }
            if interval != (lower_exit < upper_exit):
                raise ValueError("screening-label interval state differs")
            if terminal != (self.terminal_reference_fingerprint is not None):
                raise ValueError("screening-label terminal binding differs")
            excursions = (
                self.maximum_favorable_excursion,
                self.maximum_adverse_excursion,
            )
            if all(value is not None for value in excursions):
                if _decimal(excursions[0]) < 0 or _decimal(excursions[1]) > 0:
                    raise ValueError("screening-label excursion signs differ")
                if self.reason_codes:
                    raise ValueError("complete screening label carries reasons")
            elif any(value is not None for value in excursions) or not self.reason_codes:
                raise ValueError("unavailable excursions require one reason")
        if factor_screening_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("screening-label fingerprint differs")
        return self


class QuantResearchFactorScreeningCostDiagnosticV1(FrozenModel):
    basis_points_per_side: Literal[0, 10, 25, 50]
    quintile_long_short_spread_net: str

    @field_validator("quintile_long_short_spread_net")
    @classmethod
    def value_is_canonical(cls, value: str) -> str:
        _decimal(value)
        return value


class QuantResearchFactorScreeningHorizonResultV1(FrozenModel):
    factor_id: str
    role: QuantResearchFactorRole
    target: QuantResearchFactorScreeningTarget
    horizon_sessions: Literal[1, 3, 5]
    endpoint: QuantResearchFactorScreeningEndpoint
    assigned_path_count: int = Field(ge=0)
    numeric_path_count: int = Field(ge=0)
    label_state_counts: dict[str, int]
    eligible_session_count: int = Field(ge=0)
    mean_rank_ic: str | None
    rank_ic_lower_90pct: str | None
    rank_ic_upper_90pct: str | None
    one_sided_raw_p_value: str | None
    positive_session_share: str | None
    largest_absolute_session_contribution_share: str | None
    first_half_session_count: int = Field(ge=0)
    first_half_mean_rank_ic: str | None
    second_half_session_count: int = Field(ge=0)
    second_half_mean_rank_ic: str | None
    mean_partial_rank_ic: str | None
    partial_eligible_session_count: int = Field(ge=0)
    partial_rank_ic_lower_90pct: str | None
    partial_rank_ic_upper_90pct: str | None
    partial_one_sided_raw_p_value: str | None
    bucket_session_count: int = Field(ge=0)
    bucket_target_means: tuple[str, ...]
    bucket_monotonic_spearman: str | None
    bucket_top_minus_bottom: str | None
    cost_diagnostics: tuple[QuantResearchFactorScreeningCostDiagnosticV1, ...]
    reason_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def result_reasons_are_unique_and_sorted(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("screening-result reasons must be unique and sorted")
        return values

    @model_validator(mode="after")
    def result_reconciles(self) -> "QuantResearchFactorScreeningHorizonResultV1":
        if (
            self.numeric_path_count > self.assigned_path_count
            or sum(self.label_state_counts.values()) != self.assigned_path_count
            or self.partial_eligible_session_count > self.eligible_session_count
        ):
            raise ValueError("screening-result label counts differ")
        populated = (
            self.mean_rank_ic,
            self.rank_ic_lower_90pct,
            self.rank_ic_upper_90pct,
            self.one_sided_raw_p_value,
            self.positive_session_share,
            self.largest_absolute_session_contribution_share,
            self.first_half_mean_rank_ic,
            self.second_half_mean_rank_ic,
            self.bucket_monotonic_spearman,
            self.bucket_top_minus_bottom,
        )
        if self.eligible_session_count == 0:
            if any(value is not None for value in populated):
                raise ValueError("empty screening result carries statistics")
        elif any(value is None for value in populated):
            raise ValueError("eligible screening result lacks statistics")
        for value in populated:
            if value is not None:
                _decimal(value)
        partial = (
            self.mean_partial_rank_ic,
            self.partial_rank_ic_lower_90pct,
            self.partial_rank_ic_upper_90pct,
            self.partial_one_sided_raw_p_value,
        )
        baseline = self.factor_id == "relative_return_spy_20s"
        partial_absent = all(value is None for value in partial)
        if baseline and (not partial_absent or self.partial_eligible_session_count != 0):
            raise ValueError("baseline screening result carries partial statistics")
        if (
            not baseline
            and self.partial_eligible_session_count > 0
            and partial_absent
        ):
            raise ValueError("screening-result partial statistics differ")
        for value in partial:
            if value is not None:
                _decimal(value)
        if self.bucket_target_means and len(self.bucket_target_means) != 5:
            raise ValueError("screening-result bucket count differs")
        for value in self.bucket_target_means:
            _decimal(value)
        alpha = self.role is QuantResearchFactorRole.CANDIDATE_ALPHA
        expected_costs = (
            (0, 10, 25, 50)
            if alpha and self.eligible_session_count > 0
            else ()
        )
        if tuple(item.basis_points_per_side for item in self.cost_diagnostics) != expected_costs:
            raise ValueError("screening-result cost diagnostics differ")
        if factor_screening_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("screening-result fingerprint differs")
        return self


class QuantResearchFactorScreeningDecisionV1(FrozenModel):
    factor_id: str
    role: QuantResearchFactorRole
    related_factor_group: str
    status: QuantResearchFactorScreeningDecisionStatus
    formal_raw_p_value: str | None
    holm_adjusted_p_value: str | None
    robust_effect: str | None
    robust_lower_bound: str | None
    failed_gate_ids: tuple[str, ...]
    selected_for_model_candidate_set: bool
    reason_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def decision_reconciles(self) -> "QuantResearchFactorScreeningDecisionV1":
        if self.factor_id not in {
            item.factor_id
            for item in quant_research_factor_screening_protocol_v1().formal_hypotheses
        }:
            raise ValueError("screening decision factor differs")
        for value in (
            self.formal_raw_p_value,
            self.holm_adjusted_p_value,
            self.robust_effect,
            self.robust_lower_bound,
        ):
            if value is not None:
                _decimal(value)
        if self.failed_gate_ids != tuple(sorted(set(self.failed_gate_ids))):
            raise ValueError("screening decision failed gates differ")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("screening decision reasons differ")
        selected_status = (
            self.status
            is QuantResearchFactorScreeningDecisionStatus.SELECTED_MODEL_CANDIDATE
        )
        if self.selected_for_model_candidate_set != selected_status:
            raise ValueError("screening selection status differs")
        if factor_screening_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("screening-decision fingerprint differs")
        return self


class QuantResearchFactorScreeningReportV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_REPORT_CONTRACT_VERSION
    ] = QUANT_RESEARCH_FACTOR_SCREENING_REPORT_CONTRACT_VERSION
    protocol_version: Literal[QUANT_RESEARCH_FACTOR_SCREENING_PROTOCOL_VERSION] = (
        QUANT_RESEARCH_FACTOR_SCREENING_PROTOCOL_VERSION
    )
    implementation_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    created_at: datetime
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_diagnostics_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_diagnostics_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_eod_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_action_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    factor_calculation_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    label_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    screening_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    first_signal_session: date
    last_signal_session: date
    signal_session_count: int = Field(ge=1)
    observation_count: int = Field(ge=1)
    label_count: int = Field(ge=3)
    label_state_counts: dict[str, int]
    results: tuple[QuantResearchFactorScreeningHorizonResultV1, ...]
    decisions: tuple[QuantResearchFactorScreeningDecisionV1, ...]
    setup_conditioner_factor_ids: tuple[str, ...]
    selected_factor_ids: tuple[str, ...]
    status: QuantResearchFactorScreeningReportStatus
    reason_codes: tuple[str, ...]
    limitation_codes: tuple[str, ...]
    development_only: Literal[True] = True
    prior_strategy_outcome_reused: Literal[False] = False
    factor_screen_complete: Literal[True] = True
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
    def report_reconciles(self) -> "QuantResearchFactorScreeningReportV1":
        protocol = quant_research_factor_screening_protocol_v1()
        expected_factors = tuple(item.factor_id for item in protocol.formal_hypotheses)
        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
            or self.protocol_fingerprint != protocol.logical_fingerprint
            or self.source_diagnostics_fingerprint
            != protocol.source_diagnostics_fingerprint
            or self.source_diagnostics_sha256 != protocol.source_diagnostics_sha256
            or self.first_signal_session != protocol.first_development_signal_session
            or self.last_signal_session != protocol.last_development_signal_session
            or self.signal_session_count != protocol.development_eligible_session_count
            or self.observation_count != protocol.development_expected_path_count
            or self.label_count != self.observation_count * 3
            or sum(self.label_state_counts.values()) != self.label_count
            or tuple((item.factor_id, item.horizon_sessions, item.endpoint.value) for item in self.results)
            != QUANT_RESEARCH_FACTOR_SCREENING_RESULT_ORDER
            or tuple(item.factor_id for item in self.decisions) != expected_factors
            or self.selected_factor_ids
            != tuple(
                item.factor_id
                for item in self.decisions
                if item.selected_for_model_candidate_set
            )
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
            or self.limitation_codes != tuple(sorted(set(self.limitation_codes)))
        ):
            raise ValueError("screening report population, order, or identity differs")
        if factor_screening_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("screening report fingerprint differs")
        return self


def build_factor_screening_label(**payload: object) -> QuantResearchFactorScreeningLabelV1:
    provisional = QuantResearchFactorScreeningLabelV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return QuantResearchFactorScreeningLabelV1.model_validate(
        {**payload, "logical_fingerprint": factor_screening_fingerprint(provisional)}
    )


def build_factor_screening_horizon_result(
    **payload: object,
) -> QuantResearchFactorScreeningHorizonResultV1:
    provisional = QuantResearchFactorScreeningHorizonResultV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return QuantResearchFactorScreeningHorizonResultV1.model_validate(
        {**payload, "logical_fingerprint": factor_screening_fingerprint(provisional)}
    )


def build_factor_screening_decision(
    **payload: object,
) -> QuantResearchFactorScreeningDecisionV1:
    provisional = QuantResearchFactorScreeningDecisionV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return QuantResearchFactorScreeningDecisionV1.model_validate(
        {**payload, "logical_fingerprint": factor_screening_fingerprint(provisional)}
    )


def build_factor_screening_report(
    **payload: object,
) -> QuantResearchFactorScreeningReportV1:
    provisional = QuantResearchFactorScreeningReportV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return QuantResearchFactorScreeningReportV1.model_validate(
        {**payload, "logical_fingerprint": factor_screening_fingerprint(provisional)}
    )


def _decimal(value: str | None) -> Decimal:
    if value is None:
        raise ValueError("canonical decimal is required")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("value must be a canonical decimal") from exc
    if not parsed.is_finite() or value != format(_quantize(parsed), "f"):
        raise ValueError("value must use ten decimal places")
    return parsed


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0000000001"))


def _return(exit_price: Decimal, entry_price: Decimal) -> Decimal:
    return _quantize(exit_price / entry_price - Decimal("1"))
