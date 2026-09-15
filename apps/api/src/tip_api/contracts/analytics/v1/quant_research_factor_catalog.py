"""Immutable outcome-blind contracts for Quant Research Factor Catalog V1."""

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


QUANT_RESEARCH_FACTOR_CATALOG_CONTRACT_VERSION = (
    "quant-research-factor-catalog/1.0"
)
QUANT_RESEARCH_FACTOR_VALUE_CONTRACT_VERSION = "quant-research-factor-value/1.0"
QUANT_RESEARCH_FACTOR_OBSERVATION_CONTRACT_VERSION = (
    "quant-research-factor-observation/1.0"
)
QUANT_RESEARCH_FACTOR_CALCULATION_VERSION = (
    "quant-research-factor-calculation/1.0.0"
)
QUANT_RESEARCH_FACTOR_CATALOG_ID = "whalpha.factor-catalog.price-volume-v1"
QUANT_RESEARCH_FACTOR_SOURCE_SESSION_COUNT = 21


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchFactorFamily(StrEnum):
    RELATIVE_LEADERSHIP = "relative_leadership"
    TREND_PATH = "trend_path"
    VOLATILITY_STRUCTURE = "volatility_structure"
    PARTICIPATION_EXECUTION = "participation_execution"
    DOWNSIDE_FRAGILITY = "downside_fragility"


class QuantResearchFactorRole(StrEnum):
    CANDIDATE_ALPHA = "candidate_alpha"
    SETUP_CONDITIONER = "setup_conditioner"
    RISK_GUARD = "risk_guard"


class QuantResearchFactorExpectedRelationship(StrEnum):
    POSITIVE_MONOTONIC = "positive_monotonic"
    NEGATIVE_MONOTONIC = "negative_monotonic"
    NO_STANDALONE_ALPHA_CLAIM = "no_standalone_alpha_claim"


class QuantResearchFactorAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class QuantResearchFactorDefinitionV1(FrozenModel):
    factor_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    factor_version: str = Field(pattern=r"^whalpha\.factor\.[a-z0-9_.-]+/1\.0\.0$")
    calculation_code: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    family: QuantResearchFactorFamily
    role: QuantResearchFactorRole
    expected_relationship: QuantResearchFactorExpectedRelationship
    economic_rationale: str
    countermechanism: str
    exact_formula: str
    source_families: tuple[str, ...] = Field(min_length=1)
    source_fields: tuple[str, ...] = Field(min_length=1)
    source_window: str
    calculation_lookback_sessions: int = Field(ge=0, le=504)
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
    contains_forward_outcomes: Literal[False] = False
    standalone_alpha_claim_authorized: Literal[False] = False
    model_input_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def definition_reconciles(self) -> "QuantResearchFactorDefinitionV1":
        expected = _FACTOR_PAYLOAD_BY_ID.get(self.factor_id)
        actual = self.model_dump(mode="json", exclude={"logical_fingerprint"})
        if expected is None or _canonical_json_value(actual) != _canonical_json_value(
            expected
        ):
            raise ValueError("factor definition differs from immutable V1 catalog")
        if self.logical_fingerprint != _fingerprint(expected):
            raise ValueError("factor definition fingerprint mismatch")
        return self


class QuantResearchFactorCatalogV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[QUANT_RESEARCH_FACTOR_CATALOG_CONTRACT_VERSION] = (
        QUANT_RESEARCH_FACTOR_CATALOG_CONTRACT_VERSION
    )
    catalog_id: Literal[QUANT_RESEARCH_FACTOR_CATALOG_ID] = (
        QUANT_RESEARCH_FACTOR_CATALOG_ID
    )
    calculation_version: Literal[QUANT_RESEARCH_FACTOR_CALCULATION_VERSION] = (
        QUANT_RESEARCH_FACTOR_CALCULATION_VERSION
    )
    registered_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    source_session_count: Literal[QUANT_RESEARCH_FACTOR_SOURCE_SESSION_COUNT] = (
        QUANT_RESEARCH_FACTOR_SOURCE_SESSION_COUNT
    )
    definitions: tuple[QuantResearchFactorDefinitionV1, ...] = Field(
        min_length=12, max_length=12
    )
    family_count: Literal[5] = 5
    candidate_alpha_count: Literal[5] = 5
    setup_conditioner_count: Literal[4] = 4
    risk_guard_count: Literal[3] = 3
    outcome_blind_qualification_only: Literal[True] = True
    contains_forward_outcomes: Literal[False] = False
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
    def catalog_reconciles(self) -> "QuantResearchFactorCatalogV1":
        if tuple(item.factor_id for item in self.definitions) != QUANT_RESEARCH_FACTOR_ORDER:
            raise ValueError("factor catalog order differs")
        if len({item.logical_fingerprint for item in self.definitions}) != 12:
            raise ValueError("factor definition fingerprints are not unique")
        role_counts = {
            role: sum(item.role == role for item in self.definitions)
            for role in QuantResearchFactorRole
        }
        if role_counts != {
            QuantResearchFactorRole.CANDIDATE_ALPHA: self.candidate_alpha_count,
            QuantResearchFactorRole.SETUP_CONDITIONER: self.setup_conditioner_count,
            QuantResearchFactorRole.RISK_GUARD: self.risk_guard_count,
        }:
            raise ValueError("factor role counts differ")
        if factor_catalog_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("factor catalog fingerprint mismatch")
        return self


class QuantResearchFactorValueV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[QUANT_RESEARCH_FACTOR_VALUE_CONTRACT_VERSION] = (
        QUANT_RESEARCH_FACTOR_VALUE_CONTRACT_VERSION
    )
    factor_id: str
    factor_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    availability: QuantResearchFactorAvailability
    value: str | None = None
    reason_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def value_reconciles(self) -> "QuantResearchFactorValueV1":
        expected = _FACTOR_PAYLOAD_BY_ID.get(self.factor_id)
        if expected is None or self.factor_definition_fingerprint != _fingerprint(expected):
            raise ValueError("factor value definition identity differs")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("factor value reason codes must be unique and sorted")
        if self.availability == QuantResearchFactorAvailability.AVAILABLE:
            if self.value is None or self.reason_codes:
                raise ValueError("available factor must contain one value and no reasons")
            _finite_canonical_decimal(self.value)
        elif self.value is not None or not self.reason_codes:
            raise ValueError("unavailable factor must contain reasons and no value")
        return self


class QuantResearchFactorObservationV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[QUANT_RESEARCH_FACTOR_OBSERVATION_CONTRACT_VERSION] = (
        QUANT_RESEARCH_FACTOR_OBSERVATION_CONTRACT_VERSION
    )
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calculation_version: Literal[QUANT_RESEARCH_FACTOR_CALCULATION_VERSION] = (
        QUANT_RESEARCH_FACTOR_CALCULATION_VERSION
    )
    as_of_session: date
    instrument_id: UUID
    display_ticker: str | None = None
    membership_tier: Literal["reconstructed_latest_vintage_research_only"] = (
        "reconstructed_latest_vintage_research_only"
    )
    source_max_session: date
    source_eod_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    factor_values: tuple[QuantResearchFactorValueV1, ...] = Field(
        min_length=12, max_length=12
    )
    contains_forward_outcomes: Literal[False] = False
    factor_screening_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def observation_reconciles(self) -> "QuantResearchFactorObservationV1":
        catalog = quant_research_factor_catalog_v1()
        if (
            self.catalog_fingerprint != catalog.logical_fingerprint
            or self.source_max_session > self.as_of_session
            or tuple(item.factor_id for item in self.factor_values)
            != QUANT_RESEARCH_FACTOR_ORDER
            or factor_observation_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("factor observation differs")
        return self


@lru_cache(maxsize=1)
def quant_research_factor_catalog_v1() -> QuantResearchFactorCatalogV1:
    definitions = tuple(
        QuantResearchFactorDefinitionV1.model_validate(
            {**payload, "logical_fingerprint": _fingerprint(payload)}
        )
        for payload in _FACTOR_PAYLOADS
    )
    payload: dict[str, object] = {"definitions": definitions}
    provisional = QuantResearchFactorCatalogV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchFactorCatalogV1.model_validate(
        {
            **payload,
            "logical_fingerprint": factor_catalog_fingerprint(provisional),
        }
    )


def build_quant_research_factor_observation(
    **payload: object,
) -> QuantResearchFactorObservationV1:
    provisional = QuantResearchFactorObservationV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchFactorObservationV1.model_validate(
        {
            **payload,
            "logical_fingerprint": factor_observation_fingerprint(provisional),
        }
    )


def factor_catalog_fingerprint(value: BaseModel | dict[str, object]) -> str:
    return _model_fingerprint(value, excluded={"logical_fingerprint"})


def factor_observation_fingerprint(value: BaseModel | dict[str, object]) -> str:
    return _model_fingerprint(value, excluded={"logical_fingerprint"})


def _factor_payload(
    factor_id: str,
    *,
    family: QuantResearchFactorFamily,
    role: QuantResearchFactorRole,
    relationship: QuantResearchFactorExpectedRelationship,
    rationale: str,
    countermechanism: str,
    formula: str,
    fields: tuple[str, ...],
    window: str,
    lookback: int,
    group: str,
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
        "signal_cutoff": "completed_session_close",
        "earliest_execution": "next_session_open",
        "adjustment_basis": "split_reconciled_to_signal_session",
        "transform": "raw_ratio",
        "unit": "ratio",
        "missingness_rule": "explicit_unavailable_never_zero_fill",
        "related_factor_group": group,
        "contains_forward_outcomes": False,
        "standalone_alpha_claim_authorized": False,
        "model_input_authorized": False,
        "candidate_activation_authorized": False,
    }


_P = QuantResearchFactorExpectedRelationship.POSITIVE_MONOTONIC
_N = QuantResearchFactorExpectedRelationship.NEGATIVE_MONOTONIC
_C = QuantResearchFactorExpectedRelationship.NO_STANDALONE_ALPHA_CLAIM
_A = QuantResearchFactorRole.CANDIDATE_ALPHA
_S = QuantResearchFactorRole.SETUP_CONDITIONER
_R = QuantResearchFactorRole.RISK_GUARD

_FACTOR_PAYLOADS = (
    _factor_payload(
        "relative_return_spy_20s",
        family=QuantResearchFactorFamily.RELATIVE_LEADERSHIP,
        role=_A,
        relationship=_P,
        rationale="Persistent relative demand can distinguish leaders from a broad market move.",
        countermechanism="Crowded leadership can reverse when market breadth or liquidity changes.",
        formula="ln(C[t]/C[t-20]) - ln(B[t]/B[t-20])",
        fields=("close", "spy_close"),
        window="t-20_through_t",
        lookback=20,
        group="relative_return",
    ),
    _factor_payload(
        "relative_return_acceleration_5_vs_prior15",
        family=QuantResearchFactorFamily.RELATIVE_LEADERSHIP,
        role=_A,
        relationship=_P,
        rationale="Recent leadership acceleration may identify strengthening demand before a longer window catches up.",
        countermechanism="Short bursts can be exhaustion, news jumps, or transitory reversal exposure.",
        formula="[ln(C[t]/C[t-5])-ln(B[t]/B[t-5])] - [ln(C[t-5]/C[t-20])-ln(B[t-5]/B[t-20])]/3",
        fields=("close", "spy_close"),
        window="t-20_through_t_with_5_session_recent_leg",
        lookback=20,
        group="relative_return",
    ),
    _factor_payload(
        "signed_path_efficiency_10s",
        family=QuantResearchFactorFamily.TREND_PATH,
        role=_A,
        relationship=_P,
        rationale="A directional path that uses less two-way movement may be more persistent and cheaper to express.",
        countermechanism="Very smooth paths can be mature, illiquid, or vulnerable to abrupt repricing.",
        formula="sum(log(C[i]/C[i-1]),i=t-9..t)/sum(abs(log(C[i]/C[i-1])),i=t-9..t)",
        fields=("close",),
        window="ten_returns_from_t-10_through_t",
        lookback=10,
        group="trend_path_quality",
    ),
    _factor_payload(
        "positive_session_share_10s",
        family=QuantResearchFactorFamily.TREND_PATH,
        role=_A,
        relationship=_P,
        rationale="Repeated positive sessions may separate broad participation from one-day jumps.",
        countermechanism="A high hit rate can coexist with small gains and one dominant negative tail event.",
        formula="count(C[i]/C[i-1]-1>0,i=t-9..t)/10",
        fields=("close",),
        window="ten_returns_from_t-10_through_t",
        lookback=10,
        group="trend_path_quality",
    ),
    _factor_payload(
        "largest_absolute_return_share_10s",
        family=QuantResearchFactorFamily.TREND_PATH,
        role=_R,
        relationship=_N,
        rationale="A path dominated by one move contains less repeatable evidence than a distributed trend.",
        countermechanism="A genuine information shock can create a durable repricing rather than fragility.",
        formula="max(abs(log(C[i]/C[i-1])))/sum(abs(log(C[i]/C[i-1])),i=t-9..t)",
        fields=("close",),
        window="ten_returns_from_t-10_through_t",
        lookback=10,
        group="trend_path_quality",
    ),
    _factor_payload(
        "prior_atr_ratio_5_to_14",
        family=QuantResearchFactorFamily.VOLATILITY_STRUCTURE,
        role=_S,
        relationship=_C,
        rationale="Short volatility relative to its prior baseline can identify compression or expansion state.",
        countermechanism="Compression can precede either direction and expansion can reflect useful information.",
        formula="ATR5[t-1]/ATR14[t-1]",
        fields=("high", "low", "close"),
        window="true_ranges_ending_t-1",
        lookback=14,
        group="volatility_structure",
    ),
    _factor_payload(
        "prior_close_range_10s_atr14",
        family=QuantResearchFactorFamily.VOLATILITY_STRUCTURE,
        role=_S,
        relationship=_C,
        rationale="A prior close range scaled by volatility describes the compactness of the setup.",
        countermechanism="A tight base is not directional and can break against the prevailing trend.",
        formula="(max(C[t-10:t-1])-min(C[t-10:t-1]))/ATR14[t-1]",
        fields=("high", "low", "close"),
        window="prior_ten_closes_and_prior_atr14",
        lookback=14,
        group="volatility_structure",
    ),
    _factor_payload(
        "close_vs_prior_high_20s_atr14",
        family=QuantResearchFactorFamily.VOLATILITY_STRUCTURE,
        role=_S,
        relationship=_C,
        rationale="Distance from a prior closing high locates a security relative to a potential breakout boundary.",
        countermechanism="The same distance can mean breakout, extension, failed breakout, or unresolved resistance.",
        formula="(C[t]-max(C[t-20:t-1]))/ATR14[t-1]",
        fields=("high", "low", "close"),
        window="t_against_prior_twenty_closes_and_prior_atr14",
        lookback=20,
        group="volatility_structure",
    ),
    _factor_payload(
        "dollar_volume_surprise_1_to_20",
        family=QuantResearchFactorFamily.PARTICIPATION_EXECUTION,
        role=_S,
        relationship=_C,
        rationale="Unusual traded dollar volume may confirm attention and improve near-term executability.",
        countermechanism="Volume shocks can mark capitulation, distribution, index events, or temporary news.",
        formula="(C[t]*V[t])/median(C[i]*V[i],i=t-20..t-1)",
        fields=("close", "volume"),
        window="signal_session_against_prior_twenty_sessions",
        lookback=20,
        group="participation",
    ),
    _factor_payload(
        "close_location_value_1s",
        family=QuantResearchFactorFamily.PARTICIPATION_EXECUTION,
        role=_A,
        relationship=_P,
        rationale="A close near the session high can indicate that buyers retained control into the cutoff.",
        countermechanism="Closing location is noisy, auction-sensitive, and can reverse at the next open.",
        formula="(C[t]-L[t])/(H[t]-L[t])",
        fields=("high", "low", "close"),
        window="signal_session",
        lookback=0,
        group="participation",
    ),
    _factor_payload(
        "absolute_overnight_gap_atr14",
        family=QuantResearchFactorFamily.DOWNSIDE_FRAGILITY,
        role=_R,
        relationship=_N,
        rationale="Large overnight repricing increases execution uncertainty and jump-risk exposure.",
        countermechanism="A large information gap can begin a persistent repricing rather than immediate reversal.",
        formula="abs(O[t]-C[t-1])/ATR14[t-1]",
        fields=("open", "high", "low", "close"),
        window="signal_open_and_prior_atr14",
        lookback=14,
        group="downside_fragility",
    ),
    _factor_payload(
        "rolling_maximum_drawdown_10s",
        family=QuantResearchFactorFamily.DOWNSIDE_FRAGILITY,
        role=_R,
        relationship=_P,
        rationale="A less negative recent drawdown indicates lower observed downside path fragility.",
        countermechanism="A calm recent path can underestimate latent jump or event risk.",
        formula="min(C[j]/C[i]-1) for t-10<=i<j<=t",
        fields=("close",),
        window="eleven_closes_from_t-10_through_t",
        lookback=10,
        group="downside_fragility",
    ),
)

QUANT_RESEARCH_FACTOR_ORDER = tuple(
    str(payload["factor_id"]) for payload in _FACTOR_PAYLOADS
)
_FACTOR_PAYLOAD_BY_ID = {
    str(payload["factor_id"]): payload for payload in _FACTOR_PAYLOADS
}


@lru_cache(maxsize=None)
def factor_definition_fingerprint(factor_id: str) -> str:
    try:
        return _fingerprint(_FACTOR_PAYLOAD_BY_ID[factor_id])
    except KeyError as exc:
        raise ValueError(f"unknown factor_id: {factor_id}") from exc


def _finite_canonical_decimal(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("factor value must be numeric") from exc
    if not parsed.is_finite() or value != format(parsed.quantize(Decimal("0.0000000001")), "f"):
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
