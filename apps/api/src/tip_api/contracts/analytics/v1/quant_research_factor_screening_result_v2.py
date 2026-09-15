"""Development-only result contracts for the registered Factor Catalog V2 screen."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .quant_research_discovery_trial_ledger_v2 import (
    quant_research_discovery_trial_ledger_v2,
)
from .quant_research_factor_catalog_v2 import (
    QuantResearchFactorRoleV2,
    quant_research_factor_catalog_v2,
)
from .quant_research_factor_screening import (
    QuantResearchFactorScreeningTarget,
    quant_research_factor_screening_protocol_v1,
)
from .quant_research_factor_screening_result import (
    QuantResearchFactorScreeningDecisionStatus,
    QuantResearchFactorScreeningEndpoint,
    QuantResearchFactorScreeningLabelState,
    QuantResearchFactorScreeningReportStatus,
)
from .quant_research_factor_screening_v2 import (
    QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID,
    QUANT_RESEARCH_FACTOR_SCREENING_V2_VERSION,
    quant_research_factor_screening_protocol_v2,
)


QUANT_RESEARCH_FACTOR_SCREENING_LABEL_V2_CONTRACT_VERSION = (
    "quant-research-factor-screening-label/2.0"
)
QUANT_RESEARCH_FACTOR_SCREENING_CONTROL_V2_CONTRACT_VERSION = (
    "quant-research-factor-screening-control/2.0"
)
QUANT_RESEARCH_FACTOR_SCREENING_REPORT_V2_CONTRACT_VERSION = (
    "quant-research-factor-screening-report/2.0"
)
QUANT_RESEARCH_FACTOR_SCREENING_V2_EVIDENCE_SOURCE_POLICY = (
    "cohort_uses_frozen_v1_diagnostics_"
    "factor_replays_registered_qualification_private_extension_"
    "control_and_labels_use_canonical_split_evidence_only"
)
QUANT_RESEARCH_FACTOR_SCREENING_V2_RESULT_ORDER = tuple(
    (hypothesis.factor_id, horizon, endpoint)
    for hypothesis in quant_research_factor_screening_protocol_v2().formal_hypotheses
    for horizon in (1, 3, 5)
    for endpoint in (
        ("lower", "upper")
        if hypothesis.role is QuantResearchFactorRoleV2.CANDIDATE_ALPHA
        else ("complete_path",)
    )
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchFactorScreeningLabelV2(FrozenModel):
    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_LABEL_V2_CONTRACT_VERSION
    ] = QUANT_RESEARCH_FACTOR_SCREENING_LABEL_V2_CONTRACT_VERSION
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
    source_action_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
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
            raise ValueError("V2 screening-label reasons must be unique and sorted")
        return values

    @model_validator(mode="after")
    def label_reconciles(self) -> "QuantResearchFactorScreeningLabelV2":
        protocol = quant_research_factor_screening_protocol_v2()
        if (
            self.protocol_fingerprint != protocol.logical_fingerprint
            or self.catalog_fingerprint != protocol.catalog_fingerprint
            or len(self.expected_path_sessions) != self.horizon_sessions
            or self.expected_path_sessions
            != tuple(sorted(set(self.expected_path_sessions)))
            or self.expected_path_sessions[0] != self.expected_entry_session
            or self.expected_path_sessions[-1] != self.expected_exit_session
            or not self.signal_session
            < self.expected_entry_session
            <= self.expected_exit_session
            or self.split_basis_session < self.expected_exit_session
        ):
            raise ValueError("V2 screening-label identity or sessions differ")
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
                raise ValueError("nonnumeric V2 screening label carries outcomes")
        else:
            if any(value is None for value in numeric):
                raise ValueError("numeric V2 screening label is incomplete")
            entry = _decimal(self.entry_price_usd)
            lower_exit = _decimal(self.exit_price_lower_usd)
            upper_exit = _decimal(self.exit_price_upper_usd)
            lower_return = _decimal(self.underlying_price_return_lower)
            upper_return = _decimal(self.underlying_price_return_upper)
            benchmark = _decimal(self.benchmark_price_return)
            if (
                entry <= 0
                or lower_exit < 0
                or lower_exit > upper_exit
                or lower_return != _return(lower_exit, entry)
                or upper_return != _return(upper_exit, entry)
                or _decimal(self.relative_to_benchmark_return_lower)
                != _quantize(lower_return - benchmark)
                or _decimal(self.relative_to_benchmark_return_upper)
                != _quantize(upper_return - benchmark)
            ):
                raise ValueError("V2 screening-label arithmetic differs")
            interval = (
                self.state
                is QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_INTERVAL
            )
            terminal = self.state in {
                QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_EXACT,
                QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_INTERVAL,
            }
            if interval != (lower_exit < upper_exit):
                raise ValueError("V2 screening-label interval state differs")
            if terminal != (self.terminal_reference_fingerprint is not None):
                raise ValueError("V2 screening-label terminal binding differs")
            excursions = (
                self.maximum_favorable_excursion,
                self.maximum_adverse_excursion,
            )
            if all(value is not None for value in excursions):
                if _decimal(excursions[0]) < 0 or _decimal(excursions[1]) > 0:
                    raise ValueError("V2 screening-label excursion signs differ")
                if self.reason_codes:
                    raise ValueError("complete V2 screening label carries reasons")
            elif any(value is not None for value in excursions) or not self.reason_codes:
                raise ValueError("unavailable V2 excursions require one reason")
        if factor_screening_v2_result_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("V2 screening-label fingerprint differs")
        return self


class QuantResearchFactorScreeningControlV2(FrozenModel):
    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_CONTROL_V2_CONTRACT_VERSION
    ] = QUANT_RESEARCH_FACTOR_SCREENING_CONTROL_V2_CONTRACT_VERSION
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    signal_session: date
    instrument_id: UUID
    factor_id: Literal[QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID] = (
        QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID
    )
    factor_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    available: bool
    value: str | None = None
    reason_codes: tuple[str, ...] = ()
    source_min_session: date
    source_max_session: date
    source_eod_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_action_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    contains_forward_outcomes: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def control_reconciles(self) -> "QuantResearchFactorScreeningControlV2":
        protocol = quant_research_factor_screening_protocol_v2()
        if (
            self.protocol_fingerprint != protocol.logical_fingerprint
            or self.factor_definition_fingerprint
            != protocol.incremental_baseline_definition_fingerprint
            or self.source_min_session >= self.source_max_session
            or self.source_max_session != self.signal_session
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
            or (self.available and (self.value is None or self.reason_codes))
            or (not self.available and (self.value is not None or not self.reason_codes))
        ):
            raise ValueError("V2 screening control differs")
        if self.value is not None:
            _decimal(self.value)
        if factor_screening_v2_result_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("V2 screening-control fingerprint differs")
        return self


class QuantResearchFactorScreeningCostDiagnosticV2(FrozenModel):
    basis_points_per_side: Literal[0, 10, 25, 50]
    quintile_long_short_spread_net: str

    @field_validator("quintile_long_short_spread_net")
    @classmethod
    def value_is_canonical(cls, value: str) -> str:
        _decimal(value)
        return value


class QuantResearchFactorScreeningHorizonResultV2(FrozenModel):
    factor_id: str
    role: QuantResearchFactorRoleV2
    target: QuantResearchFactorScreeningTarget
    horizon_sessions: Literal[1, 3, 5]
    endpoint: QuantResearchFactorScreeningEndpoint
    assigned_path_count: int = Field(ge=0)
    factor_available_path_count: int = Field(ge=0)
    control_available_path_count: int = Field(ge=0)
    numeric_path_count: int = Field(ge=0)
    partial_numeric_path_count: int = Field(ge=0)
    factor_unavailable_reason_counts: dict[str, int]
    control_unavailable_reason_counts: dict[str, int]
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
    cost_diagnostics: tuple[QuantResearchFactorScreeningCostDiagnosticV2, ...]
    reason_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def result_reconciles(self) -> "QuantResearchFactorScreeningHorizonResultV2":
        protocol = quant_research_factor_screening_protocol_v2()
        hypothesis = next(
            (
                item
                for item in protocol.formal_hypotheses
                if item.factor_id == self.factor_id
            ),
            None,
        )
        expected_endpoints = (
            {
                QuantResearchFactorScreeningEndpoint.LOWER,
                QuantResearchFactorScreeningEndpoint.UPPER,
            }
            if self.role is QuantResearchFactorRoleV2.CANDIDATE_ALPHA
            else {QuantResearchFactorScreeningEndpoint.COMPLETE_PATH}
        )
        counts = (
            self.factor_available_path_count,
            self.control_available_path_count,
            self.numeric_path_count,
            self.partial_numeric_path_count,
        )
        expected_label_states = {
            state.value for state in QuantResearchFactorScreeningLabelState
        }
        factor_missing = self.assigned_path_count - self.factor_available_path_count
        control_missing = self.assigned_path_count - self.control_available_path_count
        if (
            hypothesis is None
            or self.role is not hypothesis.role
            or self.target is not hypothesis.target
            or self.endpoint not in expected_endpoints
            or self.assigned_path_count
            != protocol.development_declared_path_count
            or any(value > self.assigned_path_count for value in counts)
            or self.numeric_path_count > self.factor_available_path_count
            or self.partial_numeric_path_count
            > min(
                self.factor_available_path_count,
                self.control_available_path_count,
                self.numeric_path_count,
            )
            or set(self.label_state_counts) != expected_label_states
            or any(value < 0 for value in self.label_state_counts.values())
            or sum(self.label_state_counts.values()) != self.assigned_path_count
            or self.partial_eligible_session_count > self.eligible_session_count
            or self.eligible_session_count
            > protocol.development_declared_session_count
            or self.first_half_session_count + self.second_half_session_count
            != self.eligible_session_count
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
            or not _reason_counts_reconcile(
                self.factor_unavailable_reason_counts, factor_missing
            )
            or not _reason_counts_reconcile(
                self.control_unavailable_reason_counts, control_missing
            )
        ):
            raise ValueError("V2 screening-result counts differ")
        main_statistics = (
            self.mean_rank_ic,
            self.rank_ic_lower_90pct,
            self.rank_ic_upper_90pct,
            self.one_sided_raw_p_value,
            self.positive_session_share,
            self.largest_absolute_session_contribution_share,
            self.first_half_mean_rank_ic,
            self.second_half_mean_rank_ic,
        )
        if self.eligible_session_count == 0:
            if any(value is not None for value in main_statistics):
                raise ValueError("empty V2 screening result carries statistics")
        elif any(value is None for value in main_statistics):
            raise ValueError("eligible V2 screening result lacks statistics")
        partial = (
            self.mean_partial_rank_ic,
            self.partial_rank_ic_lower_90pct,
            self.partial_rank_ic_upper_90pct,
            self.partial_one_sided_raw_p_value,
        )
        if self.partial_eligible_session_count > 0 and any(
            value is None for value in partial
        ):
            raise ValueError("V2 partial statistics differ")
        if self.partial_eligible_session_count == 0 and any(
            value is not None for value in partial
        ):
            raise ValueError("empty V2 partial result carries statistics")
        bucket_statistics = (
            self.bucket_monotonic_spearman,
            self.bucket_top_minus_bottom,
        )
        if (
            self.bucket_session_count > self.eligible_session_count
            or (
                self.bucket_session_count == 0
                and (
                    self.bucket_target_means
                    or any(value is not None for value in bucket_statistics)
                )
            )
            or (
                self.bucket_session_count > 0
                and (
                    len(self.bucket_target_means) != 5
                    or any(value is None for value in bucket_statistics)
                )
            )
        ):
            raise ValueError("V2 screening-result bucket statistics differ")
        for value in (
            *main_statistics,
            *partial,
            *bucket_statistics,
            *self.bucket_target_means,
        ):
            if value is not None:
                _decimal(value)
        for value in (
            self.mean_rank_ic,
            self.rank_ic_lower_90pct,
            self.rank_ic_upper_90pct,
            self.positive_session_share,
            self.largest_absolute_session_contribution_share,
            self.first_half_mean_rank_ic,
            self.second_half_mean_rank_ic,
            self.mean_partial_rank_ic,
            self.partial_rank_ic_lower_90pct,
            self.partial_rank_ic_upper_90pct,
            self.bucket_monotonic_spearman,
        ):
            if value is not None and not Decimal("-1") <= _decimal(value) <= Decimal("1"):
                raise ValueError("V2 screening statistic leaves its valid range")
        for value in (
            self.one_sided_raw_p_value,
            self.partial_one_sided_raw_p_value,
            self.positive_session_share,
            self.largest_absolute_session_contribution_share,
        ):
            if value is not None and not Decimal("0") <= _decimal(value) <= Decimal("1"):
                raise ValueError("V2 screening probability or share differs")
        expected_costs = (
            (0, 10, 25, 50)
            if self.role is QuantResearchFactorRoleV2.CANDIDATE_ALPHA
            and self.bucket_session_count > 0
            else ()
        )
        if (
            tuple(item.basis_points_per_side for item in self.cost_diagnostics)
            != expected_costs
        ):
            raise ValueError("V2 screening cost diagnostics differ")
        if self.cost_diagnostics and any(
            _decimal(item.quintile_long_short_spread_net)
            != _quantize(
                _decimal(self.bucket_top_minus_bottom)
                - Decimal(4 * item.basis_points_per_side) / Decimal("10000")
            )
            for item in self.cost_diagnostics
        ):
            raise ValueError("V2 screening cost arithmetic differs")
        if factor_screening_v2_result_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("V2 screening-result fingerprint differs")
        return self


class QuantResearchFactorScreeningDecisionV2(FrozenModel):
    trial_id: str
    factor_id: str
    factor_version: str
    factor_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: QuantResearchFactorRoleV2
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
    def decision_reconciles(self) -> "QuantResearchFactorScreeningDecisionV2":
        hypothesis = next(
            (
                item
                for item in quant_research_factor_screening_protocol_v2().formal_hypotheses
                if item.trial_id == self.trial_id
            ),
            None,
        )
        if (
            hypothesis is None
            or self.factor_id != hypothesis.factor_id
            or self.factor_version != hypothesis.factor_version
            or self.factor_definition_fingerprint
            != hypothesis.factor_definition_fingerprint
            or self.role is not hypothesis.role
            or self.related_factor_group != hypothesis.related_factor_group
            or self.failed_gate_ids != tuple(sorted(set(self.failed_gate_ids)))
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
            or self.selected_for_model_candidate_set
            != (
                self.status
                is QuantResearchFactorScreeningDecisionStatus.SELECTED_MODEL_CANDIDATE
            )
        ):
            raise ValueError("V2 screening decision differs")
        for value in (
            self.formal_raw_p_value,
            self.holm_adjusted_p_value,
            self.robust_effect,
            self.robust_lower_bound,
        ):
            if value is not None:
                _decimal(value)
        for value in (self.formal_raw_p_value, self.holm_adjusted_p_value):
            if value is not None and not Decimal("0") <= _decimal(value) <= Decimal("1"):
                raise ValueError("V2 screening decision probability differs")
        if (
            self.formal_raw_p_value is not None
            and self.holm_adjusted_p_value is not None
            and _decimal(self.holm_adjusted_p_value) < _decimal(self.formal_raw_p_value)
        ):
            raise ValueError("V2 Holm probability is below the raw probability")
        if self.status in {
            QuantResearchFactorScreeningDecisionStatus.SELECTED_MODEL_CANDIDATE,
            QuantResearchFactorScreeningDecisionStatus.QUALIFIED_NOT_SELECTED_CAP,
        }:
            if self.failed_gate_ids or any(
                value is None
                for value in (
                    self.formal_raw_p_value,
                    self.holm_adjusted_p_value,
                    self.robust_effect,
                    self.robust_lower_bound,
                )
            ):
                raise ValueError("qualified V2 screening decision differs")
        if (
            self.status is QuantResearchFactorScreeningDecisionStatus.REJECTED_SCREEN
            and not self.failed_gate_ids
        ):
            raise ValueError("rejected V2 screening decision lacks failed gates")
        if factor_screening_v2_result_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("V2 screening-decision fingerprint differs")
        return self


class QuantResearchFactorScreeningReportV2(FrozenModel):
    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_REPORT_V2_CONTRACT_VERSION
    ] = QUANT_RESEARCH_FACTOR_SCREENING_REPORT_V2_CONTRACT_VERSION
    protocol_version: Literal[QUANT_RESEARCH_FACTOR_SCREENING_V2_VERSION] = (
        QUANT_RESEARCH_FACTOR_SCREENING_V2_VERSION
    )
    implementation_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    created_at: datetime
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_qualification_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_qualification_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    registered_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_cohort_diagnostics_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_cohort_diagnostics_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_cohort_membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_source_policy: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_V2_EVIDENCE_SOURCE_POLICY
    ] = QUANT_RESEARCH_FACTOR_SCREENING_V2_EVIDENCE_SOURCE_POLICY
    source_eod_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    factor_source_action_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    factor_source_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_source_action_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_source_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    label_source_action_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    label_source_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    factor_calculation_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_calculation_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    label_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    screening_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_collection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_collection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    label_collection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    first_signal_session: date
    last_signal_session: date
    signal_session_count: int = Field(ge=1)
    observation_count: int = Field(ge=1)
    control_count: int = Field(ge=1)
    label_count: int = Field(ge=3)
    label_state_counts: dict[str, int]
    formal_trial_count: Literal[6] = 6
    prior_consumed_trial_count: Literal[8] = 8
    cumulative_trial_count: Literal[14] = 14
    results: tuple[QuantResearchFactorScreeningHorizonResultV2, ...]
    decisions: tuple[QuantResearchFactorScreeningDecisionV2, ...]
    setup_conditioner_factor_ids: tuple[str, ...]
    applicability_input_factor_ids: tuple[str, ...]
    selected_factor_ids: tuple[str, ...]
    status: QuantResearchFactorScreeningReportStatus
    reason_codes: tuple[str, ...]
    limitation_codes: tuple[str, ...]
    development_only: Literal[True] = True
    development_outcomes_read: Literal[True] = True
    prior_strategy_outcome_reused: Literal[False] = False
    exact_report_count: Literal[1] = 1
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
    def report_reconciles(self) -> "QuantResearchFactorScreeningReportV2":
        protocol = quant_research_factor_screening_protocol_v2()
        cohort_protocol = quant_research_factor_screening_protocol_v1()
        ledger = quant_research_discovery_trial_ledger_v2()
        hypotheses = protocol.formal_hypotheses
        catalog = quant_research_factor_catalog_v2()
        conditioner_ids = tuple(
            item.factor_id
            for item in catalog.definitions
            if item.role is QuantResearchFactorRoleV2.SETUP_CONDITIONER
        )
        applicability_ids = tuple(
            item.factor_id
            for item in catalog.definitions
            if item.role is QuantResearchFactorRoleV2.APPLICABILITY_INPUT
        )
        selected = tuple(
            item for item in self.decisions if item.selected_for_model_candidate_set
        )
        selected_alpha = tuple(
            item for item in selected if item.role is QuantResearchFactorRoleV2.CANDIDATE_ALPHA
        )
        selected_risk = tuple(
            item for item in selected if item.role is QuantResearchFactorRoleV2.RISK_GUARD
        )
        has_inconclusive_alpha = any(
            item.role is QuantResearchFactorRoleV2.CANDIDATE_ALPHA
            and item.status is QuantResearchFactorScreeningDecisionStatus.INCONCLUSIVE_DATA
            for item in self.decisions
        )
        expected_status = (
            QuantResearchFactorScreeningReportStatus.READY_FOR_MODEL_PROTOCOL_REVIEW
            if selected_alpha
            else QuantResearchFactorScreeningReportStatus.INCONCLUSIVE_DATA
            if has_inconclusive_alpha
            else QuantResearchFactorScreeningReportStatus.CLOSED_NO_CANDIDATE_ALPHA
        )
        expected_reasons = (
            ("at_least_one_candidate_alpha_selected",)
            if selected_alpha
            else ("candidate_alpha_screen_has_inconclusive_data",)
            if has_inconclusive_alpha
            else ("no_candidate_alpha_passed_frozen_screen",)
        )
        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
            or self.protocol_fingerprint != protocol.logical_fingerprint
            or self.source_qualification_fingerprint
            != protocol.source_qualification_fingerprint
            or self.source_qualification_sha256 != protocol.source_qualification_sha256
            or self.registered_ledger_fingerprint != ledger.logical_fingerprint
            or self.source_cohort_diagnostics_fingerprint
            != cohort_protocol.source_diagnostics_fingerprint
            or self.source_cohort_diagnostics_sha256
            != cohort_protocol.source_diagnostics_sha256
            or self.first_signal_session != protocol.first_development_signal_session
            or self.last_signal_session != protocol.last_development_signal_session
            or self.signal_session_count != protocol.development_declared_session_count
            or self.observation_count != protocol.development_declared_path_count
            or self.control_count != self.observation_count
            or self.label_count != self.observation_count * 3
            or set(self.label_state_counts)
            != {state.value for state in QuantResearchFactorScreeningLabelState}
            or any(value < 0 for value in self.label_state_counts.values())
            or sum(self.label_state_counts.values()) != self.label_count
            or tuple(
                (item.factor_id, item.horizon_sessions, item.endpoint.value)
                for item in self.results
            )
            != QUANT_RESEARCH_FACTOR_SCREENING_V2_RESULT_ORDER
            or tuple(item.trial_id for item in self.decisions)
            != tuple(item.trial_id for item in hypotheses)
            or self.selected_factor_ids
            != tuple(
                item.factor_id
                for item in self.decisions
                if item.selected_for_model_candidate_set
            )
            or self.setup_conditioner_factor_ids != conditioner_ids
            or self.applicability_input_factor_ids != applicability_ids
            or len(selected) > protocol.maximum_model_candidate_factors
            or len(selected_alpha) > protocol.maximum_model_candidate_alpha_factors
            or len(selected_risk) > protocol.maximum_model_risk_guard_factors
            or (selected_risk and not selected_alpha)
            or len({item.related_factor_group for item in selected}) != len(selected)
            or self.status is not expected_status
            or self.reason_codes != expected_reasons
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
            or self.limitation_codes != tuple(sorted(set(self.limitation_codes)))
        ):
            raise ValueError("V2 screening report population, order, or identity differs")
        if factor_screening_v2_result_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("V2 screening report fingerprint differs")
        return self


def build_factor_screening_label_v2(
    **payload: object,
) -> QuantResearchFactorScreeningLabelV2:
    return _build(QuantResearchFactorScreeningLabelV2, payload)


def build_factor_screening_control_v2(
    **payload: object,
) -> QuantResearchFactorScreeningControlV2:
    return _build(QuantResearchFactorScreeningControlV2, payload)


def build_factor_screening_horizon_result_v2(
    **payload: object,
) -> QuantResearchFactorScreeningHorizonResultV2:
    return _build(QuantResearchFactorScreeningHorizonResultV2, payload)


def build_factor_screening_decision_v2(
    **payload: object,
) -> QuantResearchFactorScreeningDecisionV2:
    return _build(QuantResearchFactorScreeningDecisionV2, payload)


def build_factor_screening_report_v2(
    **payload: object,
) -> QuantResearchFactorScreeningReportV2:
    return _build(QuantResearchFactorScreeningReportV2, payload)


def factor_screening_v2_result_fingerprint(
    value: BaseModel | dict[str, object],
) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude={"logical_fingerprint"})
    else:
        payload = {
            key: item for key, item in value.items() if key != "logical_fingerprint"
        }
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


def _build(model, payload):
    provisional = model.model_construct(**payload, logical_fingerprint="0" * 64)
    return model.model_validate(
        {
            **payload,
            "logical_fingerprint": factor_screening_v2_result_fingerprint(
                provisional
            ),
        }
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


def _reason_counts_reconcile(counts: dict[str, int], missing_count: int) -> bool:
    if missing_count == 0:
        return not counts
    return bool(counts) and all(0 < value <= missing_count for value in counts.values())
