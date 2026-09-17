"""Outcome-blind U.S. successor hypothesis intake after factor-space review."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from functools import lru_cache
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_discovery_trial_ledger_v5 import (
    quant_research_discovery_trial_ledger_v5,
)


SUCCESSOR_HYPOTHESIS_REGISTRY_CONTRACT_VERSION = (
    "quant-research-successor-hypothesis-registry/1.0"
)
SUCCESSOR_HYPOTHESIS_REGISTRY_VERSION = (
    "whalpha.quant-research.successor-hypotheses/1.0.0"
)
FACTOR_SPACE_REPORT_SHA256 = (
    "2336546e1f48a35748aeb1bc5ffbc89bc69811f40f19b4bd35cb080d0c32757c"
)
FACTOR_SPACE_REPORT_FINGERPRINT = (
    "f2042c0c5e5e020734ab58b0dfb2706a4543fdb664d2f56469e60dbb5fe8dd3f"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SuccessorHypothesisRole(StrEnum):
    CANDIDATE_ALPHA = "candidate_alpha"
    RISK_GUARD = "risk_guard"


class InputAvailability(StrEnum):
    REQUIRES_POINT_IN_TIME_SOURCE_QUALIFICATION = (
        "requires_point_in_time_source_qualification"
    )


class SuccessorHypothesisCardV1(FrozenModel):
    hypothesis_id: str = Field(
        pattern=r"^whalpha\.hypothesis\.successor-one\.[a-z0-9-]+$"
    )
    role: SuccessorHypothesisRole
    economic_family: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    economic_mechanism: str
    countermechanism: str
    exact_formula: str
    orientation: Literal["higher_is_preferred", "true_is_risk_exclusion"]
    information_cutoff: str
    primary_horizon_sessions: Literal[3]
    parameter_neighborhood: tuple[str, ...] = Field(min_length=1)
    required_source_families: tuple[str, ...] = Field(min_length=1)
    point_in_time_requirements: tuple[str, ...] = Field(min_length=1)
    prior_trial_comparison: str
    factor_space_comparison: str
    consumed_trial_links: tuple[str, ...]
    related_input_links: tuple[str, ...]
    input_availability: Literal[
        InputAvailability.REQUIRES_POINT_IN_TIME_SOURCE_QUALIFICATION
    ] = InputAvailability.REQUIRES_POINT_IN_TIME_SOURCE_QUALIFICATION
    prospective_outcome_trial_count: Literal[0] = 0
    contains_forward_outcomes: Literal[False] = False
    development_outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_input_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    duplicate_signature: str = Field(pattern=r"^[0-9a-f]{64}$")
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def card_reconciles(self) -> "SuccessorHypothesisCardV1":
        expected = _CARD_PAYLOAD_BY_ID.get(self.hypothesis_id)
        actual = self.model_dump(
            mode="json", exclude={"duplicate_signature", "logical_fingerprint"}
        )
        if expected is None or _canonical(actual) != _canonical(
            _complete_card_payload(expected)
        ):
            raise ValueError("successor hypothesis card differs")
        if self.duplicate_signature != successor_duplicate_signature(self):
            raise ValueError("successor duplicate signature differs")
        if self.logical_fingerprint != _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        ):
            raise ValueError("successor hypothesis fingerprint differs")
        return self


class SuccessorHypothesisRegistryV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        SUCCESSOR_HYPOTHESIS_REGISTRY_CONTRACT_VERSION
    ] = SUCCESSOR_HYPOTHESIS_REGISTRY_CONTRACT_VERSION
    registry_version: Literal[SUCCESSOR_HYPOTHESIS_REGISTRY_VERSION] = (
        SUCCESSOR_HYPOTHESIS_REGISTRY_VERSION
    )
    frozen_date: Literal[date(2026, 9, 17)] = date(2026, 9, 17)
    stage: Literal["outcome_blind_intake_frozen_source_qualification_pending"] = (
        "outcome_blind_intake_frozen_source_qualification_pending"
    )
    source_completed_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_factor_space_report_sha256: Literal[FACTOR_SPACE_REPORT_SHA256] = (
        FACTOR_SPACE_REPORT_SHA256
    )
    source_factor_space_report_fingerprint: Literal[
        FACTOR_SPACE_REPORT_FINGERPRINT
    ] = FACTOR_SPACE_REPORT_FINGERPRINT
    consumed_formal_trial_count: Literal[17] = 17
    stock_factor_effective_dimension: Literal[9.1370855827] = 9.1370855827
    market_state_effective_dimension: Literal[4.5277176543] = 4.5277176543
    dedup_identity_fields: tuple[str, ...] = Field(min_length=7, max_length=7)
    cards: tuple[SuccessorHypothesisCardV1, ...] = Field(min_length=4, max_length=4)
    card_count: Literal[4] = 4
    candidate_alpha_card_count: Literal[3] = 3
    risk_guard_card_count: Literal[1] = 1
    formal_trial_count_registered: Literal[0] = 0
    development_outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    canonical_data_write_authorized: Literal[False] = False
    production_write_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def registry_reconciles(self) -> "SuccessorHypothesisRegistryV1":
        ledger = quant_research_discovery_trial_ledger_v5()
        if (
            self.source_completed_ledger_fingerprint != ledger.logical_fingerprint
            or self.consumed_formal_trial_count != ledger.cumulative_formal_trial_count
            or self.cards != _cards()
            or len({item.hypothesis_id for item in self.cards}) != 4
            or len({item.duplicate_signature for item in self.cards}) != 4
            or sum(item.role is SuccessorHypothesisRole.CANDIDATE_ALPHA for item in self.cards)
            != self.candidate_alpha_card_count
            or sum(item.role is SuccessorHypothesisRole.RISK_GUARD for item in self.cards)
            != self.risk_guard_card_count
            or successor_registry_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("successor hypothesis registry differs")
        return self


def successor_duplicate_signature(
    value: SuccessorHypothesisCardV1 | Mapping[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return _fingerprint(
        {
            "economic_mechanism": payload["economic_mechanism"],
            "information_cutoff": payload["information_cutoff"],
            "exact_formula": payload["exact_formula"],
            "orientation": payload["orientation"],
            "primary_horizon_sessions": payload["primary_horizon_sessions"],
            "parameter_neighborhood": payload["parameter_neighborhood"],
            "economic_family": payload["economic_family"],
        }
    )


def successor_registry_fingerprint(
    value: BaseModel | Mapping[str, object],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return _fingerprint(payload)


@lru_cache(maxsize=1)
def quant_research_successor_hypothesis_registry_v1() -> (
    SuccessorHypothesisRegistryV1
):
    payload: dict[str, object] = {
        "source_completed_ledger_fingerprint": (
            quant_research_discovery_trial_ledger_v5().logical_fingerprint
        ),
        "dedup_identity_fields": (
            "economic_mechanism",
            "information_cutoff",
            "formula_and_transform",
            "universe_and_eligibility",
            "horizon_and_label",
            "parameter_neighborhood",
            "economic_family",
        ),
        "cards": _cards(),
    }
    provisional = SuccessorHypothesisRegistryV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return SuccessorHypothesisRegistryV1.model_validate(
        {**payload, "logical_fingerprint": successor_registry_fingerprint(provisional)}
    )


@lru_cache(maxsize=1)
def _cards() -> tuple[SuccessorHypothesisCardV1, ...]:
    result = []
    for payload in _CARD_PAYLOADS:
        complete = _complete_card_payload(payload)
        signature = successor_duplicate_signature(complete)
        result.append(
            SuccessorHypothesisCardV1.model_validate(
                {
                    **complete,
                    "duplicate_signature": signature,
                    "logical_fingerprint": _fingerprint(
                        {**complete, "duplicate_signature": signature}
                    ),
                }
            )
        )
    return tuple(result)


def _complete_card_payload(payload: Mapping[str, object]) -> dict[str, object]:
    typed = {
        **payload,
        "role": SuccessorHypothesisRole(str(payload["role"])),
        "input_availability": InputAvailability(str(payload["input_availability"])),
    }
    provisional = SuccessorHypothesisCardV1.model_construct(
        **typed, duplicate_signature="0" * 64, logical_fingerprint="0" * 64
    )
    return provisional.model_dump(
        mode="json", exclude={"duplicate_signature", "logical_fingerprint"}
    )


_COMMON = {
    "information_cutoff": "completed_session_close_using_only_records_public_by_that_cutoff",
    "primary_horizon_sessions": 3,
    "input_availability": InputAvailability.REQUIRES_POINT_IN_TIME_SOURCE_QUALIFICATION.value,
    "prospective_outcome_trial_count": 0,
}
_CARD_PAYLOADS = (
    {
        **_COMMON,
        "hypothesis_id": "whalpha.hypothesis.successor-one.fy1-eps-revision-yield",
        "role": SuccessorHypothesisRole.CANDIDATE_ALPHA.value,
        "economic_family": "analyst_expectation_revision",
        "economic_mechanism": "Upward point-in-time FY1 earnings revisions may contain incremental information beyond price leadership.",
        "countermechanism": "Consensus revisions can lag price, cluster around events, and reflect stale or sparse analyst coverage.",
        "exact_formula": "(fy1_eps_consensus_asof_t-fy1_eps_consensus_asof_t_minus_21_sessions)/split_and_currency_aligned_close_t",
        "orientation": "higher_is_preferred",
        "parameter_neighborhood": ("revision_window_21_sessions", "fy1_consensus", "no_price_momentum_substitute"),
        "required_source_families": ("point_in_time_analyst_consensus", "split_and_currency_history"),
        "point_in_time_requirements": ("estimate_publication_timestamp", "historical_consensus_vintage", "coverage_and_currency_identity"),
        "prior_trial_comparison": "Economically distinct from all 17 price, path, participation, volatility, and Market-State interaction trials.",
        "factor_space_comparison": "Adds expectations information rather than another member of the measured leadership, reversal, path, liquidity, or risk clusters.",
        "consumed_trial_links": (),
        "related_input_links": (),
    },
    {
        **_COMMON,
        "hypothesis_id": "whalpha.hypothesis.successor-one.cash-earnings-quality",
        "role": SuccessorHypothesisRole.CANDIDATE_ALPHA.value,
        "economic_family": "fundamental_quality",
        "economic_mechanism": "Cash generation exceeding accounting earnings may distinguish durable operating quality from accrual-heavy earnings.",
        "countermechanism": "Sector accounting differences, working-capital cycles, and filing lags can dominate the raw relation.",
        "exact_formula": "(operating_cash_flow_ttm_asof_t-net_income_ttm_asof_t)/average_total_assets_ttm_asof_t",
        "orientation": "higher_is_preferred",
        "parameter_neighborhood": ("four_as_filed_quarters", "ttm", "nonfinancial_applicability_declared"),
        "required_source_families": ("point_in_time_as_filed_financial_statements", "stable_instrument_issuer_mapping"),
        "point_in_time_requirements": ("filing_acceptance_timestamp", "original_and_amended_filing_version", "period_and_currency_alignment"),
        "prior_trial_comparison": "No consumed trial used filing-time cash-flow or accrual-quality evidence.",
        "factor_space_comparison": "Targets a fundamental-quality direction absent from both completed diagnostic panels.",
        "consumed_trial_links": (),
        "related_input_links": (),
    },
    {
        **_COMMON,
        "hypothesis_id": "whalpha.hypothesis.successor-one.short-interest-change",
        "role": SuccessorHypothesisRole.CANDIDATE_ALPHA.value,
        "economic_family": "positioning_pressure",
        "economic_mechanism": "A decline in published short interest relative to shares outstanding may indicate easing persistent positioning pressure.",
        "countermechanism": "Publication delay, corporate actions, securities lending, and crowded long unwinds can overwhelm the signal.",
        "exact_formula": "-1*((short_interest_latest_publication/shares_outstanding_asof_latest)-(short_interest_prior_publication/shares_outstanding_asof_prior))",
        "orientation": "higher_is_preferred",
        "parameter_neighborhood": ("two_publications", "publication_date_cutoff", "daily_short_volume_forbidden_as_substitute"),
        "required_source_families": ("point_in_time_short_interest", "point_in_time_shares_outstanding"),
        "point_in_time_requirements": ("public_dissemination_timestamp", "settlement_period_identity", "corporate_action_alignment"),
        "prior_trial_comparison": "No consumed trial measured published short positioning; traded-volume surprise is explicitly not fund flow or short interest.",
        "factor_space_comparison": "Adds positioning evidence rather than another turnover or dollar-volume transformation.",
        "consumed_trial_links": (),
        "related_input_links": ("whalpha.factor.daily-behavior-v1.dollar_volume_surprise_1_to_20",),
    },
    {
        **_COMMON,
        "hypothesis_id": "whalpha.hypothesis.successor-one.scheduled-earnings-event-guard",
        "role": SuccessorHypothesisRole.RISK_GUARD.value,
        "economic_family": "scheduled_event_risk",
        "economic_mechanism": "A scheduled earnings release inside the holding window creates discrete gap and volatility risk not described by trailing daily-price factors.",
        "countermechanism": "Event dates can move, timing can be unconfirmed, and excluding every event may remove genuine opportunity.",
        "exact_formula": "earnings_event_known_at_t_close_occurs_from_next_open_through_third_session_close",
        "orientation": "true_is_risk_exclusion",
        "parameter_neighborhood": ("next_open_through_3_close", "confirmed_vs_estimated_status", "date_revision_history"),
        "required_source_families": ("historical_point_in_time_earnings_calendar",),
        "point_in_time_requirements": ("event_announcement_timestamp", "event_date_revision_history", "before_during_after_market_timing"),
        "prior_trial_comparison": "Distinct from the six trailing-price risk trials because it describes known forward event exposure, not a return forecast.",
        "factor_space_comparison": "A calendar guard is not a latent stock-factor component and must remain outside PCA-derived Alpha.",
        "consumed_trial_links": (),
        "related_input_links": (),
    },
)
_CARD_PAYLOAD_BY_ID = {str(item["hypothesis_id"]): item for item in _CARD_PAYLOADS}


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False, default=str)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
