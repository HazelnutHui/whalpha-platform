"""Immutable outcome-blind contracts for Quant Research Factor Catalog V2."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_discovery_trial_ledger import (
    quant_research_discovery_trial_ledger_v1,
)


QUANT_RESEARCH_FACTOR_CATALOG_V2_CONTRACT_VERSION = (
    "quant-research-factor-catalog/2.0"
)
QUANT_RESEARCH_FACTOR_VALUE_V2_CONTRACT_VERSION = (
    "quant-research-factor-value/2.0"
)
QUANT_RESEARCH_FACTOR_OBSERVATION_V2_CONTRACT_VERSION = (
    "quant-research-factor-observation/2.0"
)
QUANT_RESEARCH_FACTOR_CALCULATION_V2_VERSION = (
    "quant-research-factor-calculation/2.0.0"
)
QUANT_RESEARCH_FACTOR_CATALOG_V2_ID = (
    "whalpha.factor-catalog.daily-behavior-v2"
)
QUANT_RESEARCH_FACTOR_V2_SOURCE_SESSION_COUNT = 127


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchFactorFamilyV2(StrEnum):
    MEDIUM_HORIZON_CONTINUATION = "medium_horizon_continuation"
    SHORT_HORIZON_REVERSAL = "short_horizon_reversal"
    RETURN_TIMING = "return_timing"
    MARKET_STATE = "market_state"
    LIQUIDITY_CAPACITY = "liquidity_capacity"
    DOWNSIDE_RISK = "downside_risk"


class QuantResearchFactorRoleV2(StrEnum):
    CANDIDATE_ALPHA = "candidate_alpha"
    SETUP_CONDITIONER = "setup_conditioner"
    APPLICABILITY_INPUT = "applicability_input"
    RISK_GUARD = "risk_guard"


class QuantResearchFactorExpectedRelationshipV2(StrEnum):
    POSITIVE_MONOTONIC = "positive_monotonic"
    NEGATIVE_MONOTONIC = "negative_monotonic"
    NO_STANDALONE_ALPHA_CLAIM = "no_standalone_alpha_claim"


class QuantResearchFactorAvailabilityV2(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class QuantResearchFactorDefinitionV2(FrozenModel):
    factor_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    factor_version: str = Field(pattern=r"^whalpha\.factor\.[a-z0-9_.-]+/1\.0\.0$")
    calculation_code: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    family: QuantResearchFactorFamilyV2
    role: QuantResearchFactorRoleV2
    expected_relationship: QuantResearchFactorExpectedRelationshipV2
    economic_rationale: str
    countermechanism: str
    exact_formula: str
    source_families: tuple[str, ...] = Field(min_length=1)
    source_fields: tuple[str, ...] = Field(min_length=1)
    source_window: str
    calculation_lookback_sessions: int = Field(ge=0, le=504)
    minimum_eligible_observations: int = Field(ge=1, le=126)
    signal_cutoff: Literal["completed_session_close"] = "completed_session_close"
    earliest_execution: Literal["next_session_open"] = "next_session_open"
    adjustment_basis: Literal["split_reconciled_to_signal_session"] = (
        "split_reconciled_to_signal_session"
    )
    transform: str
    unit: str
    missingness_rule: Literal["explicit_unavailable_never_zero_fill"] = (
        "explicit_unavailable_never_zero_fill"
    )
    related_factor_group: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    redundancy_priority: int = Field(ge=1, le=8)
    relationship_to_consumed_trials: str
    consumed_trial_links: tuple[str, ...]
    primary_research_references: tuple[str, ...] = Field(min_length=1)
    price_volume_is_behavior_proxy_not_fund_flow: Literal[True] = True
    contains_forward_outcomes: Literal[False] = False
    standalone_alpha_claim_authorized: Literal[False] = False
    model_input_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def definition_reconciles(self) -> "QuantResearchFactorDefinitionV2":
        expected = _FACTOR_V2_PAYLOAD_BY_ID.get(self.factor_id)
        actual = self.model_dump(mode="json", exclude={"logical_fingerprint"})
        if expected is None or _canonical_json_value(actual) != _canonical_json_value(
            expected
        ):
            raise ValueError("factor definition differs from immutable V2 catalog")
        if self.logical_fingerprint != _fingerprint(expected):
            raise ValueError("factor definition fingerprint mismatch")
        return self


class QuantResearchFactorCatalogV2(FrozenModel):
    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[QUANT_RESEARCH_FACTOR_CATALOG_V2_CONTRACT_VERSION] = (
        QUANT_RESEARCH_FACTOR_CATALOG_V2_CONTRACT_VERSION
    )
    catalog_id: Literal[QUANT_RESEARCH_FACTOR_CATALOG_V2_ID] = (
        QUANT_RESEARCH_FACTOR_CATALOG_V2_ID
    )
    calculation_version: Literal[QUANT_RESEARCH_FACTOR_CALCULATION_V2_VERSION] = (
        QUANT_RESEARCH_FACTOR_CALCULATION_V2_VERSION
    )
    registered_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    source_session_count: Literal[QUANT_RESEARCH_FACTOR_V2_SOURCE_SESSION_COUNT] = (
        QUANT_RESEARCH_FACTOR_V2_SOURCE_SESSION_COUNT
    )
    prior_discovery_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    adaptive_to_consumed_development_evidence: Literal[True] = True
    definitions: tuple[QuantResearchFactorDefinitionV2, ...] = Field(
        min_length=8, max_length=8
    )
    family_count: Literal[6] = 6
    candidate_alpha_count: Literal[4] = 4
    setup_conditioner_count: Literal[1] = 1
    applicability_input_count: Literal[1] = 1
    risk_guard_count: Literal[2] = 2
    outcome_blind_qualification_only: Literal[True] = True
    contains_forward_outcomes: Literal[False] = False
    development_outcome_read_authorized: Literal[False] = False
    factor_screening_authorized: Literal[False] = False
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
    def catalog_reconciles(self) -> "QuantResearchFactorCatalogV2":
        ledger = quant_research_discovery_trial_ledger_v1()
        if (
            self.prior_discovery_ledger_fingerprint != ledger.logical_fingerprint
            or tuple(item.factor_id for item in self.definitions)
            != QUANT_RESEARCH_FACTOR_V2_ORDER
            or len({item.logical_fingerprint for item in self.definitions}) != 8
        ):
            raise ValueError("Factor Catalog V2 lineage differs")
        role_counts = {
            role: sum(item.role is role for item in self.definitions)
            for role in QuantResearchFactorRoleV2
        }
        if role_counts != {
            QuantResearchFactorRoleV2.CANDIDATE_ALPHA: 4,
            QuantResearchFactorRoleV2.SETUP_CONDITIONER: 1,
            QuantResearchFactorRoleV2.APPLICABILITY_INPUT: 1,
            QuantResearchFactorRoleV2.RISK_GUARD: 2,
        }:
            raise ValueError("Factor Catalog V2 role counts differ")
        priorities_by_group: dict[str, list[int]] = {}
        for item in self.definitions:
            priorities_by_group.setdefault(item.related_factor_group, []).append(
                item.redundancy_priority
            )
        if any(
            len(priorities) != len(set(priorities))
            for priorities in priorities_by_group.values()
        ):
            raise ValueError("Factor Catalog V2 redundancy priorities differ")
        if factor_catalog_v2_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("Factor Catalog V2 fingerprint mismatch")
        return self


class QuantResearchFactorValueV2(FrozenModel):
    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[QUANT_RESEARCH_FACTOR_VALUE_V2_CONTRACT_VERSION] = (
        QUANT_RESEARCH_FACTOR_VALUE_V2_CONTRACT_VERSION
    )
    factor_id: str
    factor_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    availability: QuantResearchFactorAvailabilityV2
    value: str | None = None
    reason_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def value_reconciles(self) -> "QuantResearchFactorValueV2":
        expected = _FACTOR_V2_PAYLOAD_BY_ID.get(self.factor_id)
        if expected is None or self.factor_definition_fingerprint != _fingerprint(expected):
            raise ValueError("factor value definition identity differs")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("factor value reason codes must be unique and sorted")
        if self.availability is QuantResearchFactorAvailabilityV2.AVAILABLE:
            if self.value is None or self.reason_codes:
                raise ValueError("available factor must contain one value and no reasons")
            _finite_canonical_decimal(self.value)
        elif self.value is not None or not self.reason_codes:
            raise ValueError("unavailable factor must contain reasons and no value")
        return self


class QuantResearchFactorObservationV2(FrozenModel):
    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[
        QUANT_RESEARCH_FACTOR_OBSERVATION_V2_CONTRACT_VERSION
    ] = QUANT_RESEARCH_FACTOR_OBSERVATION_V2_CONTRACT_VERSION
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calculation_version: Literal[QUANT_RESEARCH_FACTOR_CALCULATION_V2_VERSION] = (
        QUANT_RESEARCH_FACTOR_CALCULATION_V2_VERSION
    )
    as_of_session: date
    instrument_id: UUID
    display_ticker: str | None = None
    membership_tier: Literal["reconstructed_latest_vintage_research_only"] = (
        "reconstructed_latest_vintage_research_only"
    )
    source_min_session: date
    source_max_session: date
    source_eod_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    factor_values: tuple[QuantResearchFactorValueV2, ...] = Field(
        min_length=8, max_length=8
    )
    contains_forward_outcomes: Literal[False] = False
    factor_screening_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def observation_reconciles(self) -> "QuantResearchFactorObservationV2":
        catalog = quant_research_factor_catalog_v2()
        if (
            self.catalog_fingerprint != catalog.logical_fingerprint
            or self.source_min_session > self.source_max_session
            or self.source_max_session != self.as_of_session
            or tuple(item.factor_id for item in self.factor_values)
            != QUANT_RESEARCH_FACTOR_V2_ORDER
            or factor_observation_v2_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("Factor Catalog V2 observation differs")
        return self


@lru_cache(maxsize=1)
def quant_research_factor_catalog_v2() -> QuantResearchFactorCatalogV2:
    definitions = tuple(
        QuantResearchFactorDefinitionV2.model_validate(
            {**payload, "logical_fingerprint": _fingerprint(payload)}
        )
        for payload in _FACTOR_V2_PAYLOADS
    )
    payload: dict[str, object] = {
        "prior_discovery_ledger_fingerprint": (
            quant_research_discovery_trial_ledger_v1().logical_fingerprint
        ),
        "definitions": definitions,
    }
    provisional = QuantResearchFactorCatalogV2.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchFactorCatalogV2.model_validate(
        {
            **payload,
            "logical_fingerprint": factor_catalog_v2_fingerprint(provisional),
        }
    )


def build_quant_research_factor_observation_v2(
    **payload: object,
) -> QuantResearchFactorObservationV2:
    provisional = QuantResearchFactorObservationV2.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchFactorObservationV2.model_validate(
        {
            **payload,
            "logical_fingerprint": factor_observation_v2_fingerprint(provisional),
        }
    )


def factor_catalog_v2_fingerprint(value: BaseModel | dict[str, object]) -> str:
    return _model_fingerprint(value, excluded={"logical_fingerprint"})


def factor_observation_v2_fingerprint(value: BaseModel | dict[str, object]) -> str:
    return _model_fingerprint(value, excluded={"logical_fingerprint"})


def _factor_payload(
    factor_id: str,
    *,
    family: QuantResearchFactorFamilyV2,
    role: QuantResearchFactorRoleV2,
    relationship: QuantResearchFactorExpectedRelationshipV2,
    rationale: str,
    countermechanism: str,
    formula: str,
    fields: tuple[str, ...],
    window: str,
    lookback: int,
    minimum_observations: int,
    transform: str,
    unit: str,
    group: str,
    redundancy_priority: int,
    consumed_relationship: str,
    consumed_links: tuple[str, ...],
    references: tuple[str, ...],
) -> dict[str, object]:
    return {
        "factor_id": factor_id,
        "factor_version": f"whalpha.factor.{factor_id}/1.0.0",
        "calculation_code": factor_id,
        "family": family.value,
        "role": role.value,
        "expected_relationship": relationship.value,
        "economic_rationale": rationale,
        "countermechanism": countermechanism,
        "exact_formula": formula,
        "source_families": (
            "historical-eod-price-bars-v1",
            "historical-research-adjustment-ledger-v1",
        ),
        "source_fields": fields,
        "source_window": window,
        "calculation_lookback_sessions": lookback,
        "minimum_eligible_observations": minimum_observations,
        "signal_cutoff": "completed_session_close",
        "earliest_execution": "next_session_open",
        "adjustment_basis": "split_reconciled_to_signal_session",
        "transform": transform,
        "unit": unit,
        "missingness_rule": "explicit_unavailable_never_zero_fill",
        "related_factor_group": group,
        "redundancy_priority": redundancy_priority,
        "relationship_to_consumed_trials": consumed_relationship,
        "consumed_trial_links": consumed_links,
        "primary_research_references": references,
        "price_volume_is_behavior_proxy_not_fund_flow": True,
        "contains_forward_outcomes": False,
        "standalone_alpha_claim_authorized": False,
        "model_input_authorized": False,
        "candidate_activation_authorized": False,
    }


_P = QuantResearchFactorExpectedRelationshipV2.POSITIVE_MONOTONIC
_N = QuantResearchFactorExpectedRelationshipV2.NEGATIVE_MONOTONIC
_C = QuantResearchFactorExpectedRelationshipV2.NO_STANDALONE_ALPHA_CLAIM
_A = QuantResearchFactorRoleV2.CANDIDATE_ALPHA
_S = QuantResearchFactorRoleV2.SETUP_CONDITIONER
_X = QuantResearchFactorRoleV2.APPLICABILITY_INPUT
_R = QuantResearchFactorRoleV2.RISK_GUARD

_MOMENTUM_REFERENCE = (
    "Jegadeesh_Titman_1993_DOI_10.1111/j.1540-6261.1993.tb04702.x",
)
_REVERSAL_REFERENCE = (
    "Jegadeesh_1990_DOI_10.1111/j.1540-6261.1990.tb05110.x",
)
_INTRADAY_REFERENCE = (
    "Miwa_2019_DOI_10.1142/S2010139219500022",
)
_ILLIQUIDITY_REFERENCE = (
    "Amihud_2002_DOI_10.1016/S1386-4181(01)00024-6",
)
_IDIOSYNCRATIC_VOLATILITY_REFERENCE = (
    "Ang_Hodrick_Xing_Zhang_2006_DOI_10.1111/j.1540-6261.2006.00836.x",
)
_DOWNSIDE_RISK_REFERENCE = (
    "Ang_Chen_Xing_2006_DOI_10.1093/rfs/hhj035",
)

_FACTOR_V2_PAYLOADS = (
    _factor_payload(
        "medium_term_relative_momentum_126s_skip5",
        family=QuantResearchFactorFamilyV2.MEDIUM_HORIZON_CONTINUATION,
        role=_A,
        relationship=_P,
        rationale=(
            "Medium-horizon relative continuation may persist after excluding "
            "the most recent reversal-prone week."
        ),
        countermechanism=(
            "Crowding, momentum crashes, fast regime changes, and a short "
            "three-session label can erase a medium-horizon premium."
        ),
        formula="ln(C[t-5]/C[t-126]) - ln(B[t-5]/B[t-126])",
        fields=("close", "spy_close"),
        window="t-126_through_t-5",
        lookback=126,
        minimum_observations=121,
        transform="raw_log_relative_return",
        unit="log_return",
        group="medium_horizon_relative_continuation",
        redundancy_priority=1,
        consumed_relationship=(
            "related_horizon_extension_not_independent_of_v1_relative_return_trials"
        ),
        consumed_links=(
            "whalpha.discovery-trial.price-volume-v1.relative_return_spy_20s.h3",
            "whalpha.discovery-trial.price-volume-v1.relative_return_acceleration_5_vs_prior15.h3",
        ),
        references=_MOMENTUM_REFERENCE,
    ),
    _factor_payload(
        "short_term_relative_reversal_5s",
        family=QuantResearchFactorFamilyV2.SHORT_HORIZON_REVERSAL,
        role=_A,
        relationship=_P,
        rationale=(
            "Recent market-relative price pressure may partially reverse when "
            "it reflects temporary liquidity demand rather than new information."
        ),
        countermechanism=(
            "Fundamental repricing, distressed continuation, spreads, and "
            "delayed execution can make recent losers continue falling."
        ),
        formula="-[ln(C[t]/C[t-5]) - ln(B[t]/B[t-5])]",
        fields=("close", "spy_close"),
        window="t-5_through_t",
        lookback=5,
        minimum_observations=5,
        transform="sign_reversed_raw_log_relative_return",
        unit="log_return",
        group="short_horizon_relative_reversal",
        redundancy_priority=1,
        consumed_relationship=(
            "economically_opposite_horizon_to_consumed_relative_continuation_trials"
        ),
        consumed_links=(
            "whalpha.discovery-trial.price-volume-v1.relative_return_spy_20s.h3",
        ),
        references=_REVERSAL_REFERENCE,
    ),
    _factor_payload(
        "intraday_relative_pressure_reversal_5s",
        family=QuantResearchFactorFamilyV2.RETURN_TIMING,
        role=_A,
        relationship=_P,
        rationale=(
            "Market-adjusted open-to-close pressure can isolate a daily "
            "liquidity-concession component that may reverse after the signal close."
        ),
        countermechanism=(
            "Persistent informed trading, close-auction effects, bid-ask "
            "bounce, and unobserved spreads can invalidate a daily-bar proxy."
        ),
        formula="-sum([ln(C[i]/O[i])-ln(Bc[i]/Bo[i])],i=t-4..t)",
        fields=("open", "close", "spy_open", "spy_close"),
        window="five_signal_inclusive_intraday_sessions_t-4_through_t",
        lookback=4,
        minimum_observations=5,
        transform="sign_reversed_market_adjusted_log_intraday_return_sum",
        unit="log_return",
        group="short_horizon_relative_reversal",
        redundancy_priority=2,
        consumed_relationship=(
            "new_return_timing_decomposition_related_to_v1_relative_return_family"
        ),
        consumed_links=(
            "whalpha.discovery-trial.price-volume-v1.relative_return_spy_20s.h3",
        ),
        references=_INTRADAY_REFERENCE,
    ),
    _factor_payload(
        "overnight_relative_persistence_5s",
        family=QuantResearchFactorFamilyV2.RETURN_TIMING,
        role=_A,
        relationship=_P,
        rationale=(
            "Market-adjusted close-to-open repricing may carry different "
            "information from intraday pressure and can persist if it reflects "
            "durable news assimilation."
        ),
        countermechanism=(
            "Overnight jumps can overreact, reflect stale closes, or be fully "
            "consumed before next-open execution."
        ),
        formula="sum([ln(O[i]/C[i-1])-ln(Bo[i]/Bc[i-1])],i=t-4..t)",
        fields=("open", "close", "spy_open", "spy_close"),
        window="five_signal_inclusive_overnight_sessions_t-4_through_t",
        lookback=5,
        minimum_observations=5,
        transform="market_adjusted_log_overnight_return_sum",
        unit="log_return",
        group="overnight_information_timing",
        redundancy_priority=1,
        consumed_relationship="new_return_timing_decomposition_related_to_v1_gap_risk_trial",
        consumed_links=(
            "whalpha.discovery-trial.price-volume-v1.absolute_overnight_gap_atr14.h3",
        ),
        references=_INTRADAY_REFERENCE,
    ),
    _factor_payload(
        "down_market_relative_resilience_60s",
        family=QuantResearchFactorFamilyV2.MARKET_STATE,
        role=_S,
        relationship=_C,
        rationale=(
            "Relative behavior on benchmark-down sessions can describe "
            "defensive resilience for a later preregistered market-state interaction."
        ),
        countermechanism=(
            "A defensive history can lag in risk-on rebounds and the available "
            "sample does not prove diverse historical regimes."
        ),
        formula="mean(ln(C[i]/C[i-1])-ln(B[i]/B[i-1]) | benchmark_return[i]<0,i=t-59..t)",
        fields=("close", "spy_close"),
        window="sixty_returns_t-59_through_t_conditioned_on_negative_spy_return",
        lookback=60,
        minimum_observations=12,
        transform="conditional_mean_log_relative_return",
        unit="mean_daily_log_return",
        group="defensive_market_applicability",
        redundancy_priority=1,
        consumed_relationship="new_market_state_conditioner_no_consumed_standalone_trial",
        consumed_links=(),
        references=_DOWNSIDE_RISK_REFERENCE,
    ),
    _factor_payload(
        "amihud_illiquidity_20s",
        family=QuantResearchFactorFamilyV2.LIQUIDITY_CAPACITY,
        role=_X,
        relationship=_C,
        rationale=(
            "Absolute return per dollar traded is a coarse daily-bar proxy for "
            "price impact and can bound applicability and capacity."
        ),
        countermechanism=(
            "The proxy is not a spread, order-flow, or executable-impact "
            "observation and can confound information shocks with illiquidity."
        ),
        formula="1e6*mean(abs(ln(C[i]/C[i-1]))/(C[i]*V[i]),i=t-19..t)",
        fields=("close", "volume"),
        window="twenty_returns_and_signal_session_dollar_volume_t-19_through_t",
        lookback=20,
        minimum_observations=20,
        transform="mean_absolute_log_return_per_dollar_volume_scaled_one_million",
        unit="absolute_log_return_per_usd_million",
        group="liquidity_capacity",
        redundancy_priority=1,
        consumed_relationship="new_applicability_role_related_to_v1_participation_measurement_only",
        consumed_links=(),
        references=_ILLIQUIDITY_REFERENCE,
    ),
    _factor_payload(
        "single_index_residual_volatility_60s",
        family=QuantResearchFactorFamilyV2.DOWNSIDE_RISK,
        role=_R,
        relationship=_N,
        rationale=(
            "Volatility unexplained by the broad benchmark can identify "
            "security-specific path fragility relevant to adverse excursion."
        ),
        countermechanism=(
            "Backward-looking residual volatility misses jump risk and is "
            "unstable when benchmark variance or observations are weak."
        ),
        formula="sqrt(252)*sample_sd(rs[i]-alpha-beta*rb[i],i=t-59..t),OLS_with_intercept",
        fields=("close", "spy_close"),
        window="sixty_daily_returns_t-59_through_t",
        lookback=60,
        minimum_observations=60,
        transform="annualized_single_index_ols_residual_standard_deviation",
        unit="annualized_log_return_volatility",
        group="residual_downside_risk",
        redundancy_priority=1,
        consumed_relationship="new_risk_measure_related_to_retained_v1_drawdown_guard",
        consumed_links=(
            "whalpha.discovery-trial.price-volume-v1.rolling_maximum_drawdown_10s.h3",
        ),
        references=_IDIOSYNCRATIC_VOLATILITY_REFERENCE,
    ),
    _factor_payload(
        "relative_downside_semideviation_60s",
        family=QuantResearchFactorFamilyV2.DOWNSIDE_RISK,
        role=_R,
        relationship=_N,
        rationale=(
            "The downside-only dispersion of benchmark-relative returns "
            "directly measures recent asymmetric adverse variation."
        ),
        countermechanism=(
            "Quiet histories can conceal jump risk and downside semideviation "
            "may duplicate recent drawdown information."
        ),
        formula="sqrt(252)*sqrt(mean(min(ln(C[i]/C[i-1])-ln(B[i]/B[i-1]),0)^2,i=t-59..t))",
        fields=("close", "spy_close"),
        window="sixty_daily_returns_t-59_through_t",
        lookback=60,
        minimum_observations=60,
        transform="annualized_relative_downside_semideviation",
        unit="annualized_log_return_volatility",
        group="residual_downside_risk",
        redundancy_priority=2,
        consumed_relationship="new_risk_measure_related_to_retained_v1_drawdown_guard",
        consumed_links=(
            "whalpha.discovery-trial.price-volume-v1.rolling_maximum_drawdown_10s.h3",
        ),
        references=_DOWNSIDE_RISK_REFERENCE,
    ),
)

QUANT_RESEARCH_FACTOR_V2_ORDER = tuple(
    str(payload["factor_id"]) for payload in _FACTOR_V2_PAYLOADS
)
_FACTOR_V2_PAYLOAD_BY_ID = {
    str(payload["factor_id"]): payload for payload in _FACTOR_V2_PAYLOADS
}


@lru_cache(maxsize=None)
def factor_definition_v2_fingerprint(factor_id: str) -> str:
    try:
        return _fingerprint(_FACTOR_V2_PAYLOAD_BY_ID[factor_id])
    except KeyError as exc:
        raise ValueError(f"unknown V2 factor_id: {factor_id}") from exc


def _finite_canonical_decimal(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("factor value must be numeric") from exc
    if not parsed.is_finite() or value != format(
        parsed.quantize(Decimal("0.0000000001")), "f"
    ):
        raise ValueError("factor value must be finite with ten decimal places")
    return parsed


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _canonical_json_value(value: object) -> object:
    return json.loads(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=str,
        )
    )


def _model_fingerprint(
    value: BaseModel | dict[str, object], *, excluded: set[str]
) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude=excluded)
    else:
        payload = {key: item for key, item in value.items() if key not in excluded}
    return _fingerprint(payload)
