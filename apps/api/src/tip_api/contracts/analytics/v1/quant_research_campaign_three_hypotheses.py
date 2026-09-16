"""Outcome-blind Campaign Three hypothesis intake and deduplication."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from functools import lru_cache
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_discovery_trial_ledger_v3 import (
    quant_research_discovery_trial_ledger_v3,
)
from .quant_research_factor_catalog import quant_research_factor_catalog_v1
from .quant_research_factor_catalog_v2 import quant_research_factor_catalog_v2
from .quant_research_market_state_vector import (
    quant_research_market_state_vector_definition_v1,
)
from .quant_research_multi_agent_governance import (
    quant_research_multi_agent_governance_v1,
)
from .quant_research_reusable_artifacts_v2 import (
    MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT,
    MARKET_STATE_QUALIFICATION_REPORT_SHA256,
    quant_research_reusable_artifact_registry_v2,
)


QUANT_RESEARCH_CAMPAIGN_THREE_HYPOTHESIS_REGISTRY_CONTRACT_VERSION = (
    "quant-research-campaign-hypothesis-registry/1.0"
)
QUANT_RESEARCH_CAMPAIGN_THREE_HYPOTHESIS_REGISTRY_VERSION = (
    "whalpha.quant-research.campaign-three-hypotheses/1.0.0"
)
MARKET_STATE_ARTIFACT_IDENTITY_FINGERPRINT = (
    "7d900990ab1a65bf7520658704c83257a96e808f6b996f827f12a80eecda3e4c"
)
MARKET_STATE_ARTIFACT_CONTENT_SHA256 = (
    "a670fb106b559a3b363da8aae0d3c85a8076fd8b0b5952c52537a859e0b1e537"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CampaignThreeHypothesisRole(StrEnum):
    CANDIDATE_ALPHA_INTERACTION = "candidate_alpha_interaction"
    RISK_GUARD_INTERACTION = "risk_guard_interaction"


class CampaignThreeNoveltyDisposition(StrEnum):
    ACCEPTED_FOR_OUTCOME_BLIND_QUALIFICATION = (
        "accepted_for_outcome_blind_qualification"
    )
    REJECTED_NEAR_DUPLICATE = "rejected_near_duplicate"


class CampaignThreeHypothesisCardV1(FrozenModel):
    hypothesis_id: str = Field(
        pattern=r"^whalpha\.hypothesis\.campaign-three\.[a-z0-9-]+$"
    )
    role: CampaignThreeHypothesisRole
    source_factor_catalog: Literal["v1", "v2"]
    source_factor_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    source_factor_version: str
    source_factor_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_factor_formula: str
    source_factor_orientation: Literal["as_defined", "sign_reversed_lower_is_safer"]
    state_metric_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    state_metric_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    state_metric_formula: str
    state_transform: str
    economic_mechanism: str
    countermechanism: str
    falsifiable_expectation: str
    information_set_and_cutoff: Literal[
        "completed_session_close_point_in_time_earliest_next_open"
    ] = "completed_session_close_point_in_time_earliest_next_open"
    universe_and_eligibility: Literal[
        "frozen_development_primary_reconstructed_membership_complete_factor_and_state_only"
    ] = "frozen_development_primary_reconstructed_membership_complete_factor_and_state_only"
    target_and_horizon: Literal[
        "spy_relative_next_open_to_horizon_3_close",
        "maximum_adverse_excursion_from_next_open_through_horizon_3_close",
    ]
    primary_horizon_sessions: Literal[3] = 3
    diagnostic_horizon_sessions: tuple[Literal[1], Literal[5]] = (1, 5)
    interaction_estimand: Literal[
        "session_rank_ic_q_t_equals_alpha_plus_beta_times_state_s_t_plus_error"
    ] = "session_rank_ic_q_t_equals_alpha_plus_beta_times_state_s_t_plus_error"
    expected_interaction_slope: Literal["beta_greater_than_zero"] = (
        "beta_greater_than_zero"
    )
    parameter_neighborhood: tuple[str, ...] = Field(min_length=1)
    related_hypothesis_family: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    consumed_trial_links: tuple[str, ...]
    adaptive_to_consumed_development_evidence: Literal[True] = True
    volume_activity_proxy_not_fund_flow: bool
    novelty_disposition: CampaignThreeNoveltyDisposition
    rejection_reason: str | None
    prospective_trial_count: Literal[0, 1]
    contains_forward_outcomes: Literal[False] = False
    outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_input_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    duplicate_signature: str = Field(pattern=r"^[0-9a-f]{64}$")
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def card_reconciles(self) -> "CampaignThreeHypothesisCardV1":
        expected = _HYPOTHESIS_PAYLOAD_BY_ID.get(self.hypothesis_id)
        actual = self.model_dump(
            mode="json", exclude={"duplicate_signature", "logical_fingerprint"}
        )
        if expected is None or _canonical(actual) != _canonical(
            _complete_card_payload(expected)
        ):
            raise ValueError("Campaign Three hypothesis card differs")
        if self.duplicate_signature != hypothesis_duplicate_signature(self):
            raise ValueError("Campaign Three duplicate signature differs")
        if self.logical_fingerprint != _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        ):
            raise ValueError("Campaign Three hypothesis fingerprint differs")
        accepted = (
            self.novelty_disposition
            is CampaignThreeNoveltyDisposition.ACCEPTED_FOR_OUTCOME_BLIND_QUALIFICATION
        )
        if accepted != (self.prospective_trial_count == 1):
            raise ValueError("Campaign Three prospective trial accounting differs")
        if accepted != (self.rejection_reason is None):
            raise ValueError("Campaign Three rejection evidence differs")
        return self


class CampaignThreeHypothesisRegistryV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_CAMPAIGN_THREE_HYPOTHESIS_REGISTRY_CONTRACT_VERSION
    ] = QUANT_RESEARCH_CAMPAIGN_THREE_HYPOTHESIS_REGISTRY_CONTRACT_VERSION
    registry_version: Literal[
        QUANT_RESEARCH_CAMPAIGN_THREE_HYPOTHESIS_REGISTRY_VERSION
    ] = QUANT_RESEARCH_CAMPAIGN_THREE_HYPOTHESIS_REGISTRY_VERSION
    frozen_date: Literal[date(2026, 9, 16)] = date(2026, 9, 16)
    stage: Literal["hypothesis_intake_and_deduplication_complete"] = (
        "hypothesis_intake_and_deduplication_complete"
    )
    source_completed_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_multi_agent_governance_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_reusable_artifact_registry_fingerprint: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    source_market_state_qualification_report_fingerprint: Literal[
        MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
    ] = MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
    source_market_state_qualification_report_sha256: Literal[
        MARKET_STATE_QUALIFICATION_REPORT_SHA256
    ] = MARKET_STATE_QUALIFICATION_REPORT_SHA256
    source_market_state_artifact_identity_fingerprint: Literal[
        MARKET_STATE_ARTIFACT_IDENTITY_FINGERPRINT
    ] = MARKET_STATE_ARTIFACT_IDENTITY_FINGERPRINT
    source_market_state_artifact_content_sha256: Literal[
        MARKET_STATE_ARTIFACT_CONTENT_SHA256
    ] = MARKET_STATE_ARTIFACT_CONTENT_SHA256
    dedup_identity_fields: tuple[
        Literal[
            "economic_mechanism",
            "information_set_and_cutoff",
            "formula_and_transform",
            "universe_and_eligibility",
            "horizon_and_label",
            "parameter_neighborhood",
            "related_hypothesis_family",
        ],
        ...,
    ] = Field(min_length=7, max_length=7)
    proposals: tuple[CampaignThreeHypothesisCardV1, ...] = Field(
        min_length=5, max_length=5
    )
    proposal_count: Literal[5] = 5
    accepted_for_qualification_count: Literal[4] = 4
    rejected_near_duplicate_count: Literal[1] = 1
    prospective_candidate_alpha_trial_count: Literal[3] = 3
    prospective_risk_guard_trial_count: Literal[1] = 1
    prospective_total_trial_count: Literal[4] = 4
    formal_trial_count_registered: Literal[0] = 0
    cumulative_consumed_formal_trial_count: Literal[14] = 14
    campaign_three_registered: Literal[False] = False
    interaction_input_qualified: Literal[False] = False
    development_outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    canonical_data_write_authorized: Literal[False] = False
    production_write_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def registry_reconciles(self) -> "CampaignThreeHypothesisRegistryV1":
        ledger = quant_research_discovery_trial_ledger_v3()
        governance = quant_research_multi_agent_governance_v1()
        reusable = quant_research_reusable_artifact_registry_v2()
        expected = _campaign_three_cards()
        accepted = tuple(
            item
            for item in self.proposals
            if item.novelty_disposition
            is CampaignThreeNoveltyDisposition.ACCEPTED_FOR_OUTCOME_BLIND_QUALIFICATION
        )
        rejected = tuple(item for item in self.proposals if item not in accepted)
        if (
            self.source_completed_ledger_fingerprint != ledger.logical_fingerprint
            or self.source_multi_agent_governance_fingerprint
            != governance.logical_fingerprint
            or self.source_reusable_artifact_registry_fingerprint
            != reusable.logical_fingerprint
            or self.proposals != expected
            or len({item.hypothesis_id for item in self.proposals}) != 5
            or len({item.duplicate_signature for item in accepted}) != 4
            or len(accepted) != self.accepted_for_qualification_count
            or len(rejected) != self.rejected_near_duplicate_count
            or sum(
                item.role
                is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
                for item in accepted
            )
            != self.prospective_candidate_alpha_trial_count
            or sum(
                item.role is CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION
                for item in accepted
            )
            != self.prospective_risk_guard_trial_count
            or sum(item.prospective_trial_count for item in accepted)
            != self.prospective_total_trial_count
            or self.cumulative_consumed_formal_trial_count
            != ledger.cumulative_formal_trial_count
            or campaign_three_hypothesis_registry_fingerprint(self)
            != self.logical_fingerprint
        ):
            raise ValueError("Campaign Three hypothesis registry differs")
        return self


def campaign_three_hypothesis_registry_fingerprint(
    value: BaseModel | Mapping[str, object],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return _fingerprint(payload)


def hypothesis_duplicate_signature(
    value: CampaignThreeHypothesisCardV1 | Mapping[str, object],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    identity = {
        "economic_mechanism": payload["economic_mechanism"],
        "information_set_and_cutoff": payload["information_set_and_cutoff"],
        "formula_and_transform": {
            "source_factor_formula": payload["source_factor_formula"],
            "source_factor_orientation": payload["source_factor_orientation"],
            "state_metric_formula": payload["state_metric_formula"],
            "state_transform": payload["state_transform"],
            "interaction_estimand": payload["interaction_estimand"],
        },
        "universe_and_eligibility": payload["universe_and_eligibility"],
        "horizon_and_label": payload["target_and_horizon"],
        "parameter_neighborhood": payload["parameter_neighborhood"],
        "related_hypothesis_family": payload["related_hypothesis_family"],
    }
    return _fingerprint(identity)


@lru_cache(maxsize=1)
def quant_research_campaign_three_hypothesis_registry_v1() -> (
    CampaignThreeHypothesisRegistryV1
):
    payload: dict[str, object] = {
        "source_completed_ledger_fingerprint": (
            quant_research_discovery_trial_ledger_v3().logical_fingerprint
        ),
        "source_multi_agent_governance_fingerprint": (
            quant_research_multi_agent_governance_v1().logical_fingerprint
        ),
        "source_reusable_artifact_registry_fingerprint": (
            quant_research_reusable_artifact_registry_v2().logical_fingerprint
        ),
        "dedup_identity_fields": (
            "economic_mechanism",
            "information_set_and_cutoff",
            "formula_and_transform",
            "universe_and_eligibility",
            "horizon_and_label",
            "parameter_neighborhood",
            "related_hypothesis_family",
        ),
        "proposals": _campaign_three_cards(),
    }
    provisional = CampaignThreeHypothesisRegistryV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return CampaignThreeHypothesisRegistryV1.model_validate(
        {
            **payload,
            "logical_fingerprint": campaign_three_hypothesis_registry_fingerprint(
                provisional
            ),
        }
    )


@lru_cache(maxsize=1)
def _campaign_three_cards() -> tuple[CampaignThreeHypothesisCardV1, ...]:
    cards: list[CampaignThreeHypothesisCardV1] = []
    for payload in _HYPOTHESIS_PAYLOADS:
        complete = _complete_card_payload(payload)
        duplicate_signature = hypothesis_duplicate_signature(complete)
        logical_fingerprint = _fingerprint(
            {**complete, "duplicate_signature": duplicate_signature}
        )
        cards.append(
            CampaignThreeHypothesisCardV1.model_validate(
                {
                    **complete,
                    "duplicate_signature": duplicate_signature,
                    "logical_fingerprint": logical_fingerprint,
                }
            )
        )
    return tuple(cards)


def _complete_card_payload(payload: Mapping[str, object]) -> dict[str, object]:
    typed = {
        **payload,
        "role": CampaignThreeHypothesisRole(str(payload["role"])),
        "novelty_disposition": CampaignThreeNoveltyDisposition(
            str(payload["novelty_disposition"])
        ),
    }
    provisional = CampaignThreeHypothesisCardV1.model_construct(
        **typed,
        duplicate_signature="0" * 64,
        logical_fingerprint="0" * 64,
    )
    return provisional.model_dump(
        mode="json", exclude={"duplicate_signature", "logical_fingerprint"}
    )


def _factor_payload(catalog: str, factor_id: str) -> dict[str, object]:
    source = (
        quant_research_factor_catalog_v1()
        if catalog == "v1"
        else quant_research_factor_catalog_v2()
    )
    definition = next(item for item in source.definitions if item.factor_id == factor_id)
    return {
        "source_factor_catalog": catalog,
        "source_factor_id": factor_id,
        "source_factor_version": definition.factor_version,
        "source_factor_definition_fingerprint": definition.logical_fingerprint,
        "source_factor_formula": definition.exact_formula,
    }


def _state_payload(metric_id: str, transform: str) -> dict[str, object]:
    vector = quant_research_market_state_vector_definition_v1()
    definition = next(item for item in vector.definitions if item.metric_id == metric_id)
    return {
        "state_metric_id": metric_id,
        "state_metric_definition_fingerprint": definition.logical_fingerprint,
        "state_metric_formula": definition.exact_formula,
        "state_transform": transform,
    }


_COMMON_ALPHA = {
    "role": CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION.value,
    "source_factor_orientation": "as_defined",
    "target_and_horizon": "spy_relative_next_open_to_horizon_3_close",
    "volume_activity_proxy_not_fund_flow": False,
    "prospective_trial_count": 1,
    "novelty_disposition": (
        CampaignThreeNoveltyDisposition.ACCEPTED_FOR_OUTCOME_BLIND_QUALIFICATION.value
    ),
    "rejection_reason": None,
}
_HYPOTHESIS_PAYLOADS = (
    {
        **_COMMON_ALPHA,
        "hypothesis_id": "whalpha.hypothesis.campaign-three.breakout-breadth",
        **_factor_payload("v1", "close_vs_prior_high_20s_atr14"),
        **_state_payload(
            "reconstructed_member_above_sma20_share", "2*(share-0.5)"
        ),
        "economic_mechanism": (
            "Breakout location should carry more continuation information when broad "
            "member participation is healthy."
        ),
        "countermechanism": (
            "High breadth can mark late-cycle crowding, while weak breadth can still "
            "contain isolated durable leaders."
        ),
        "falsifiable_expectation": (
            "The session-level breakout rank IC interaction slope is positive, and "
            "the favorable natural-state mean rank IC remains positive."
        ),
        "parameter_neighborhood": (
            "prior_high_20_sessions",
            "atr_14_sessions_lagged_one_session",
            "state_transform_center_0_5_scale_2",
        ),
        "related_hypothesis_family": "breakout_position_by_market_breadth",
        "consumed_trial_links": (),
    },
    {
        **_COMMON_ALPHA,
        "hypothesis_id": "whalpha.hypothesis.campaign-three.volume-participation",
        **_factor_payload("v1", "dollar_volume_surprise_1_to_20"),
        **_state_payload(
            "reconstructed_member_positive_log_return_5s_share", "2*(share-0.5)"
        ),
        "economic_mechanism": (
            "Unusual traded dollar volume should be more informative when medium-short "
            "breadth confirms market participation."
        ),
        "countermechanism": (
            "Volume shocks can reflect distribution, index activity, or temporary news "
            "rather than persistent demand."
        ),
        "falsifiable_expectation": (
            "The session-level dollar-volume-surprise rank IC interaction slope is "
            "positive without describing the activity proxy as fund flow."
        ),
        "parameter_neighborhood": (
            "signal_dollar_volume_over_prior_20_session_median",
            "state_transform_center_0_5_scale_2",
        ),
        "related_hypothesis_family": "volume_activity_by_market_participation",
        "consumed_trial_links": (),
        "volume_activity_proxy_not_fund_flow": True,
    },
    {
        **_COMMON_ALPHA,
        "hypothesis_id": "whalpha.hypothesis.campaign-three.defensive-resilience",
        **_factor_payload("v2", "down_market_relative_resilience_60s"),
        **_state_payload("spy_log_return_20s", "-1*spy_log_return_20s"),
        "economic_mechanism": (
            "Securities that historically held up on benchmark-down sessions should "
            "be relatively more useful when the broad market is currently weak."
        ),
        "countermechanism": (
            "Defensive resilience can lag during abrupt risk-on rebounds and may encode "
            "low beta rather than independent alpha."
        ),
        "falsifiable_expectation": (
            "The resilience rank IC interaction slope rises with market weakness and "
            "the favorable weakness-state mean rank IC is positive."
        ),
        "parameter_neighborhood": (
            "60_session_conditioning_window",
            "minimum_12_negative_spy_sessions",
            "state_sign_reversed_no_hindsight_threshold",
        ),
        "related_hypothesis_family": "defensive_resilience_by_market_weakness",
        "consumed_trial_links": (),
    },
    {
        "hypothesis_id": "whalpha.hypothesis.campaign-three.residual-risk-volatility",
        "role": CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION.value,
        **_factor_payload("v2", "single_index_residual_volatility_60s"),
        "source_factor_orientation": "sign_reversed_lower_is_safer",
        **_state_payload("spy_realized_volatility_20s", "as_defined"),
        "economic_mechanism": (
            "Lower security-specific residual volatility should become more protective "
            "against adverse excursion as broad-market volatility rises."
        ),
        "countermechanism": (
            "Backward-looking residual volatility can miss jumps and can be unstable "
            "when benchmark variance changes abruptly."
        ),
        "falsifiable_expectation": (
            "The safer-oriented residual-volatility rank IC interaction slope is "
            "positive for the registered three-session adverse-excursion label."
        ),
        "target_and_horizon": (
            "maximum_adverse_excursion_from_next_open_through_horizon_3_close"
        ),
        "parameter_neighborhood": (
            "60_session_single_index_residual_window",
            "20_session_spy_realized_volatility_state",
            "source_factor_sign_reversed_lower_is_safer",
        ),
        "related_hypothesis_family": "residual_risk_by_market_volatility",
        "consumed_trial_links": (
            "whalpha.discovery-trial.daily-behavior-v2.single_index_residual_volatility_60s.h3",
        ),
        "adaptive_to_consumed_development_evidence": True,
        "volume_activity_proxy_not_fund_flow": False,
        "novelty_disposition": (
            CampaignThreeNoveltyDisposition.ACCEPTED_FOR_OUTCOME_BLIND_QUALIFICATION.value
        ),
        "rejection_reason": None,
        "prospective_trial_count": 1,
    },
    {
        **_COMMON_ALPHA,
        "hypothesis_id": "whalpha.hypothesis.campaign-three.rejected-compression-trend",
        **_factor_payload("v1", "prior_atr_ratio_5_to_14"),
        **_state_payload("broad_etf_mean_log_distance_to_sma20", "as_defined"),
        "economic_mechanism": (
            "Prior volatility compression might resolve more favorably when broad ETF "
            "trend state is positive."
        ),
        "countermechanism": (
            "Compression is nondirectional and this pairing repackages the earlier "
            "pullback and ATR-compression research family."
        ),
        "falsifiable_expectation": (
            "Not evaluated because the seven-dimensional review classifies the idea "
            "as a near duplicate before outcomes."
        ),
        "parameter_neighborhood": (
            "atr_5_over_atr_14_lagged_one_session",
            "broad_etf_distance_to_sma20_state",
        ),
        "related_hypothesis_family": "pullback_atr_compression",
        "consumed_trial_links": ("whalpha.strong-leader-pullback",),
        "novelty_disposition": (
            CampaignThreeNoveltyDisposition.REJECTED_NEAR_DUPLICATE.value
        ),
        "rejection_reason": (
            "Near-duplicate of the consumed pullback and ATR-compression family; "
            "retained to prevent rediscovery but excluded from the trial budget."
        ),
        "prospective_trial_count": 0,
    },
)
_HYPOTHESIS_PAYLOAD_BY_ID = {
    str(item["hypothesis_id"]): item for item in _HYPOTHESIS_PAYLOADS
}


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=str,
    )


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
