"""Outcome-blind point-in-time market-state inputs for Factor Discovery."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_discovery_cycle import quant_research_discovery_cycle_v1
from .quant_research_reusable_artifacts import (
    quant_research_reusable_artifact_registry_v1,
)


QUANT_RESEARCH_MARKET_STATE_VECTOR_CONTRACT_VERSION = (
    "quant-research-market-state-vector/1.0"
)
QUANT_RESEARCH_MARKET_STATE_VECTOR_VERSION = (
    "whalpha.quant-research.market-state-vector/1.0.0"
)
QUANT_RESEARCH_MARKET_STATE_SOURCE_SESSION_COUNT = 21
QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER = (
    "spy_log_return_20s",
    "spy_realized_volatility_20s",
    "qqq_spy_relative_log_return_20s",
    "iwm_spy_relative_log_return_20s",
    "dia_spy_relative_log_return_20s",
    "broad_etf_above_sma20_share",
    "reconstructed_member_positive_log_return_5s_share",
    "reconstructed_member_above_sma20_share",
    "reconstructed_member_log_return_dispersion_5s",
    "reconstructed_member_log_return_dispersion_20s",
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchMarketStateEvidenceTier(StrEnum):
    BENCHMARK_EXACT = "benchmark_exact"
    RECONSTRUCTED_RESEARCH_ONLY = "reconstructed_research_only"


class QuantResearchMarketStateAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class QuantResearchMarketStateMetricDefinitionV1(FrozenModel):
    metric_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    evidence_tier: QuantResearchMarketStateEvidenceTier
    exact_formula: str
    source_fields: tuple[str, ...] = Field(min_length=1)
    calculation_lookback_sessions: int = Field(ge=1, le=252)
    minimum_complete_members: int | None = Field(default=None, ge=1)
    minimum_member_coverage: str | None = None
    signal_cutoff: Literal["completed_session_close"] = "completed_session_close"
    earliest_execution: Literal["next_session_open"] = "next_session_open"
    membership_basis: Literal[
        "not_applicable_benchmark_identity",
        "effective_dated_reconstructed_membership_by_stable_instrument_id",
    ]
    missingness_rule: Literal["explicit_unavailable_never_zero_fill"] = (
        "explicit_unavailable_never_zero_fill"
    )
    contains_forward_outcomes: Literal[False] = False
    standalone_alpha_claim_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def definition_reconciles(self) -> "QuantResearchMarketStateMetricDefinitionV1":
        expected = _METRIC_PAYLOAD_BY_ID.get(self.metric_id)
        actual = self.model_dump(mode="json", exclude={"logical_fingerprint"})
        if expected is None or _canonical(actual) != _canonical(expected):
            raise ValueError("market-state metric definition differs")
        if self.logical_fingerprint != _fingerprint(expected):
            raise ValueError("market-state metric definition fingerprint differs")
        return self


class QuantResearchMarketStateVectorDefinitionV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_MARKET_STATE_VECTOR_CONTRACT_VERSION
    ] = QUANT_RESEARCH_MARKET_STATE_VECTOR_CONTRACT_VERSION
    vector_version: Literal[
        QUANT_RESEARCH_MARKET_STATE_VECTOR_VERSION
    ] = QUANT_RESEARCH_MARKET_STATE_VECTOR_VERSION
    accepted_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    source_cycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_reusable_artifact_registry_fingerprint: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    required_benchmark_tickers: tuple[
        Literal["SPY", "QQQ", "IWM", "DIA"], ...
    ] = ("SPY", "QQQ", "IWM", "DIA")
    source_session_count: Literal[21] = 21
    definitions: tuple[QuantResearchMarketStateMetricDefinitionV1, ...] = Field(
        min_length=10, max_length=10
    )
    benchmark_metric_count: Literal[6] = 6
    reconstructed_metric_count: Literal[4] = 4
    emits_continuous_metrics_only: Literal[True] = True
    state_thresholds_selected: Literal[False] = False
    interactions_registered: Literal[False] = False
    campaign_three_registered: Literal[False] = False
    contains_forward_outcomes: Literal[False] = False
    development_outcome_read_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def vector_reconciles(self) -> "QuantResearchMarketStateVectorDefinitionV1":
        cycle = quant_research_discovery_cycle_v1()
        registry = quant_research_reusable_artifact_registry_v1()
        if (
            self.source_cycle_fingerprint != cycle.logical_fingerprint
            or self.source_reusable_artifact_registry_fingerprint
            != registry.logical_fingerprint
            or tuple(item.metric_id for item in self.definitions)
            != QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER
            or len({item.logical_fingerprint for item in self.definitions}) != 10
            or market_state_vector_definition_fingerprint(self)
            != self.logical_fingerprint
        ):
            raise ValueError("market-state vector definition differs")
        return self


class QuantResearchMarketStateMetricValueV1(FrozenModel):
    metric_id: str
    definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    availability: QuantResearchMarketStateAvailability
    value: str | None = None
    actual_observations: int = Field(ge=0)
    expected_observations: int = Field(ge=1)
    coverage_ratio: str
    reason_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def value_reconciles(self) -> "QuantResearchMarketStateMetricValueV1":
        expected = _METRIC_PAYLOAD_BY_ID.get(self.metric_id)
        if expected is None or self.definition_fingerprint != _fingerprint(expected):
            raise ValueError("market-state metric identity differs")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("market-state reason codes must be unique and sorted")
        if self.availability is QuantResearchMarketStateAvailability.AVAILABLE:
            if self.value is None or self.reason_codes:
                raise ValueError("available market-state value differs")
        elif self.value is not None or not self.reason_codes:
            raise ValueError("unavailable market-state value differs")
        coverage = _require_fixed_decimal(self.coverage_ratio, "coverage ratio")
        if coverage < Decimal("0") or coverage > Decimal("1"):
            raise ValueError("market-state coverage ratio is outside [0,1]")
        if self.value is not None:
            _require_fixed_decimal(self.value, "metric value")
        return self


def market_state_metric_definition_fingerprint(metric_id: str) -> str:
    return _fingerprint(_METRIC_PAYLOAD_BY_ID[metric_id])


def market_state_vector_definition_fingerprint(
    value: BaseModel | dict[str, object],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return _fingerprint(payload)


@lru_cache(maxsize=1)
def quant_research_market_state_vector_definition_v1() -> (
    QuantResearchMarketStateVectorDefinitionV1
):
    cycle = quant_research_discovery_cycle_v1()
    registry = quant_research_reusable_artifact_registry_v1()
    payload: dict[str, object] = {
        "source_cycle_fingerprint": cycle.logical_fingerprint,
        "source_reusable_artifact_registry_fingerprint": registry.logical_fingerprint,
        "definitions": tuple(
            QuantResearchMarketStateMetricDefinitionV1(
                **item,
                logical_fingerprint=_fingerprint(item),
            )
            for item in _METRIC_PAYLOADS
        ),
    }
    provisional = QuantResearchMarketStateVectorDefinitionV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchMarketStateVectorDefinitionV1.model_validate(
        {
            **payload,
            "logical_fingerprint": market_state_vector_definition_fingerprint(
                provisional
            ),
        }
    )


def _metric(
    metric_id: str,
    *,
    evidence_tier: QuantResearchMarketStateEvidenceTier,
    formula: str,
    fields: tuple[str, ...],
    lookback: int,
) -> dict[str, object]:
    reconstructed = (
        evidence_tier
        is QuantResearchMarketStateEvidenceTier.RECONSTRUCTED_RESEARCH_ONLY
    )
    return {
        "metric_id": metric_id,
        "evidence_tier": evidence_tier.value,
        "exact_formula": formula,
        "source_fields": fields,
        "calculation_lookback_sessions": lookback,
        "minimum_complete_members": 500 if reconstructed else None,
        "minimum_member_coverage": "0.7500000000" if reconstructed else None,
        "signal_cutoff": "completed_session_close",
        "earliest_execution": "next_session_open",
        "membership_basis": (
            "effective_dated_reconstructed_membership_by_stable_instrument_id"
            if reconstructed
            else "not_applicable_benchmark_identity"
        ),
        "missingness_rule": "explicit_unavailable_never_zero_fill",
        "contains_forward_outcomes": False,
        "standalone_alpha_claim_authorized": False,
    }


_B = QuantResearchMarketStateEvidenceTier.BENCHMARK_EXACT
_R = QuantResearchMarketStateEvidenceTier.RECONSTRUCTED_RESEARCH_ONLY
_METRIC_PAYLOADS = (
    _metric(
        "spy_log_return_20s",
        evidence_tier=_B,
        formula="ln(SPY_C[t]/SPY_C[t-20])",
        fields=("spy_close",),
        lookback=20,
    ),
    _metric(
        "spy_realized_volatility_20s",
        evidence_tier=_B,
        formula=(
            "sqrt(252)*sample_std(ln(SPY_C[i]/SPY_C[i-1]),i=t-19..t)"
        ),
        fields=("spy_close",),
        lookback=20,
    ),
    _metric(
        "qqq_spy_relative_log_return_20s",
        evidence_tier=_B,
        formula=(
            "ln(QQQ_C[t]/QQQ_C[t-20])-ln(SPY_C[t]/SPY_C[t-20])"
        ),
        fields=("qqq_close", "spy_close"),
        lookback=20,
    ),
    _metric(
        "iwm_spy_relative_log_return_20s",
        evidence_tier=_B,
        formula=(
            "ln(IWM_C[t]/IWM_C[t-20])-ln(SPY_C[t]/SPY_C[t-20])"
        ),
        fields=("iwm_close", "spy_close"),
        lookback=20,
    ),
    _metric(
        "dia_spy_relative_log_return_20s",
        evidence_tier=_B,
        formula=(
            "ln(DIA_C[t]/DIA_C[t-20])-ln(SPY_C[t]/SPY_C[t-20])"
        ),
        fields=("dia_close", "spy_close"),
        lookback=20,
    ),
    _metric(
        "broad_etf_above_sma20_share",
        evidence_tier=_B,
        formula=(
            "mean(C_j[t]>mean(C_j[t-19:t]),j in {SPY,QQQ,IWM,DIA})"
        ),
        fields=("spy_close", "qqq_close", "iwm_close", "dia_close"),
        lookback=19,
    ),
    _metric(
        "reconstructed_member_positive_log_return_5s_share",
        evidence_tier=_R,
        formula=(
            "mean(ln(C_k[t]/C_k[t-5])>0,k in reconstructed_members[t])"
        ),
        fields=("member_close", "reconstructed_membership"),
        lookback=5,
    ),
    _metric(
        "reconstructed_member_above_sma20_share",
        evidence_tier=_R,
        formula=(
            "mean(C_k[t]>mean(C_k[t-19:t]),k in reconstructed_members[t])"
        ),
        fields=("member_close", "reconstructed_membership"),
        lookback=19,
    ),
    _metric(
        "reconstructed_member_log_return_dispersion_5s",
        evidence_tier=_R,
        formula=(
            "1.4826*MAD(ln(C_k[t]/C_k[t-5]),k in reconstructed_members[t])"
        ),
        fields=("member_close", "reconstructed_membership"),
        lookback=5,
    ),
    _metric(
        "reconstructed_member_log_return_dispersion_20s",
        evidence_tier=_R,
        formula=(
            "1.4826*MAD(ln(C_k[t]/C_k[t-20]),k in reconstructed_members[t])"
        ),
        fields=("member_close", "reconstructed_membership"),
        lookback=20,
    ),
)
_METRIC_PAYLOAD_BY_ID = {item["metric_id"]: item for item in _METRIC_PAYLOADS}


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def _canonical(value: object) -> object:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _require_fixed_decimal(value: str, label: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"market-state {label} must be numeric") from exc
    if not parsed.is_finite() or Decimal(value).as_tuple().exponent != -10:
        raise ValueError(f"market-state {label} must use ten decimal places")
    return parsed
