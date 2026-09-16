"""Completed cumulative trial accounting through Campaign Three."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from functools import lru_cache
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_campaign_three_hypotheses import CampaignThreeHypothesisRole
from .quant_research_campaign_three_screening import (
    CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT,
    CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256,
    QUANT_RESEARCH_CAMPAIGN_THREE_SCREENING_VERSION,
    CampaignThreeScreeningHypothesisV1,
    quant_research_campaign_three_screening_protocol_v1,
)
from .quant_research_discovery_trial_ledger import QuantResearchDiscoveryCampaignV1
from .quant_research_discovery_trial_ledger_v3 import QuantResearchDiscoveryCampaignV3
from .quant_research_discovery_trial_ledger_v4 import (
    quant_research_discovery_trial_ledger_v4,
)


QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V5_CONTRACT_VERSION = (
    "quant-research-discovery-trial-ledger/5.0"
)
QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V5_VERSION = (
    "whalpha.quant-research.discovery-trial-ledger/5.0.0"
)
CAMPAIGN_THREE_SCREENING_REPORT_FINGERPRINT = (
    "7b4f0e60c7dd3aa4faa01d16e303ed7bec35a4af5a7b992a4941ef01e3a439f9"
)
CAMPAIGN_THREE_SCREENING_REPORT_SHA256 = (
    "8ba525beb7e39e7e9175fd0359b45e17c44c16cd6c1a083fb53c99704c4f13e1"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchDiscoveryTrialDispositionV5(StrEnum):
    REJECTED_SCREEN = "rejected_screen"


class QuantResearchDiscoveryTrialV5(FrozenModel):
    trial_id: str = Field(
        pattern=r"^whalpha\.discovery-trial\.campaign-three\.[a-z0-9-]+\.h3$"
    )
    campaign_id: Literal["whalpha.factor-discovery.market-state-interactions-v1"] = (
        "whalpha.factor-discovery.market-state-interactions-v1"
    )
    hypothesis_id: str = Field(
        pattern=r"^whalpha\.hypothesis\.campaign-three\.[a-z0-9-]+$"
    )
    hypothesis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: CampaignThreeHypothesisRole
    related_hypothesis_family: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    primary_horizon_sessions: Literal[3] = 3
    formal_trial_count: Literal[1] = 1
    outcome_partition: Literal["development"] = "development"
    outcome_accessed: Literal[True] = True
    outcome_access_date: Literal[date(2026, 9, 16)] = date(2026, 9, 16)
    disposition: Literal[QuantResearchDiscoveryTrialDispositionV5.REJECTED_SCREEN] = (
        QuantResearchDiscoveryTrialDispositionV5.REJECTED_SCREEN
    )
    report_fingerprint: Literal[CAMPAIGN_THREE_SCREENING_REPORT_FINGERPRINT] = (
        CAMPAIGN_THREE_SCREENING_REPORT_FINGERPRINT
    )
    report_sha256: Literal[CAMPAIGN_THREE_SCREENING_REPORT_SHA256] = (
        CAMPAIGN_THREE_SCREENING_REPORT_SHA256
    )
    validation_accessed: Literal[False] = False
    holdout_accessed: Literal[False] = False
    model_input_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False

    @model_validator(mode="after")
    def trial_reconciles(self) -> "QuantResearchDiscoveryTrialV5":
        protocol = quant_research_campaign_three_screening_protocol_v1()
        source = next(
            (item for item in protocol.formal_hypotheses if item.trial_id == self.trial_id),
            None,
        )
        if source is None or not _trial_matches_hypothesis(self, source):
            raise ValueError("completed Campaign Three trial differs")
        return self


class QuantResearchDiscoveryCampaignV5(FrozenModel):
    campaign_id: Literal["whalpha.factor-discovery.market-state-interactions-v1"] = (
        "whalpha.factor-discovery.market-state-interactions-v1"
    )
    registered_date: Literal[date(2026, 9, 16)] = date(2026, 9, 16)
    completed_date: Literal[date(2026, 9, 16)] = date(2026, 9, 16)
    status: Literal["closed_no_candidate_alpha"] = "closed_no_candidate_alpha"
    hypothesis_registry_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_qualification_fingerprint: Literal[
        CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT
    ] = CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT
    input_qualification_sha256: Literal[
        CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256
    ] = CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256
    input_qualification_exact_replay_verified: Literal[True] = True
    screening_protocol_version: Literal[
        QUANT_RESEARCH_CAMPAIGN_THREE_SCREENING_VERSION
    ] = QUANT_RESEARCH_CAMPAIGN_THREE_SCREENING_VERSION
    screening_protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_fingerprint: Literal[CAMPAIGN_THREE_SCREENING_REPORT_FINGERPRINT] = (
        CAMPAIGN_THREE_SCREENING_REPORT_FINGERPRINT
    )
    report_sha256: Literal[CAMPAIGN_THREE_SCREENING_REPORT_SHA256] = (
        CAMPAIGN_THREE_SCREENING_REPORT_SHA256
    )
    exact_replay_verified: Literal[True] = True
    formal_trials: tuple[QuantResearchDiscoveryTrialV5, ...] = Field(
        min_length=3, max_length=3
    )
    formal_trial_count: Literal[3] = 3
    candidate_alpha_trial_count: Literal[2] = 2
    risk_guard_trial_count: Literal[1] = 1
    rejected_before_outcomes_count: Literal[2] = 2
    rejected_candidate_alpha_trial_count: Literal[2] = 2
    rejected_risk_guard_trial_count: Literal[1] = 1
    candidate_alpha_admitted_count: Literal[0] = 0
    qualified_risk_evidence_count: Literal[0] = 0
    selected_model_input_count: Literal[0] = 0
    outcomes_read: Literal[True] = True
    formal_execution_count: Literal[1] = 1
    exact_replay_execution_count: Literal[1] = 1
    validation_accessed: Literal[False] = False
    holdout_accessed: Literal[False] = False
    model_construction_authorized: Literal[False] = False

    @model_validator(mode="after")
    def campaign_reconciles(self) -> "QuantResearchDiscoveryCampaignV5":
        protocol = quant_research_campaign_three_screening_protocol_v1()
        if (
            self.hypothesis_registry_fingerprint
            != protocol.source_hypothesis_registry_fingerprint
            or self.screening_protocol_fingerprint != protocol.logical_fingerprint
            or self.formal_trials != _completed_campaign_three_trials()
            or len({item.trial_id for item in self.formal_trials}) != 3
            or sum(item.formal_trial_count for item in self.formal_trials) != 3
        ):
            raise ValueError("completed Campaign Three campaign differs")
        return self


class QuantResearchDiscoveryTrialLedgerV5(FrozenModel):
    schema_version: Literal["5.0"] = "5.0"
    contract_version: Literal[
        QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V5_CONTRACT_VERSION
    ] = QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V5_CONTRACT_VERSION
    ledger_version: Literal[QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V5_VERSION] = (
        QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V5_VERSION
    )
    completed_date: Literal[date(2026, 9, 16)] = date(2026, 9, 16)
    accounting_scope: Literal[
        "factor_and_registered_factor_interaction_outcome_trials"
    ] = "factor_and_registered_factor_interaction_outcome_trials"
    campaign_accounting_rule: Literal[
        "append_new_version_never_rewrite_consumed_campaign"
    ] = "append_new_version_never_rewrite_consumed_campaign"
    development_evidence_rule: Literal[
        "campaign_adjusted_screening_not_global_independent_alpha_claim"
    ] = "campaign_adjusted_screening_not_global_independent_alpha_claim"
    prior_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    prior_strategy_programs_separate: tuple[
        Literal["whalpha.strong-leader-pullback"]
    ] = ("whalpha.strong-leader-pullback",)
    campaigns: tuple[
        QuantResearchDiscoveryCampaignV1,
        QuantResearchDiscoveryCampaignV3,
        QuantResearchDiscoveryCampaignV5,
    ]
    completed_campaign_count: Literal[3] = 3
    registered_unread_campaign_count: Literal[0] = 0
    cumulative_formal_trial_count: Literal[17] = 17
    cumulative_candidate_alpha_trial_count: Literal[11] = 11
    cumulative_risk_guard_trial_count: Literal[6] = 6
    cumulative_candidate_alpha_admitted_count: Literal[0] = 0
    cumulative_qualified_risk_evidence_count: Literal[3] = 3
    cumulative_model_input_authorized_factor_count: Literal[0] = 0
    next_campaign_requires_new_registered_ledger_version: Literal[True] = True
    next_campaign_is_adaptive_to_consumed_development_evidence: Literal[True] = True
    development_screen_execution_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    strategy_expression_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def ledger_reconciles(self) -> "QuantResearchDiscoveryTrialLedgerV5":
        prior = quant_research_discovery_trial_ledger_v4()
        completed = _completed_campaign_three()
        all_trials = tuple(
            trial for campaign in self.campaigns for trial in campaign.formal_trials
        )
        if (
            self.prior_ledger_fingerprint != prior.logical_fingerprint
            or self.campaigns != (*prior.campaigns[:2], completed)
            or len({item.trial_id for item in all_trials}) != 17
            or sum(item.formal_trial_count for item in all_trials) != 17
            or discovery_trial_ledger_v5_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("completed Campaign Three cumulative accounting differs")
        return self


def discovery_trial_ledger_v5_fingerprint(
    value: BaseModel | Mapping[str, object],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
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


@lru_cache(maxsize=1)
def quant_research_discovery_trial_ledger_v5() -> (
    QuantResearchDiscoveryTrialLedgerV5
):
    prior = quant_research_discovery_trial_ledger_v4()
    campaigns = (*prior.campaigns[:2], _completed_campaign_three())
    payload: dict[str, object] = {
        "prior_ledger_fingerprint": prior.logical_fingerprint,
        "campaigns": campaigns,
    }
    provisional = QuantResearchDiscoveryTrialLedgerV5.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return QuantResearchDiscoveryTrialLedgerV5.model_validate(
        {
            **payload,
            "logical_fingerprint": discovery_trial_ledger_v5_fingerprint(provisional),
        }
    )


@lru_cache(maxsize=1)
def _completed_campaign_three() -> QuantResearchDiscoveryCampaignV5:
    protocol = quant_research_campaign_three_screening_protocol_v1()
    return QuantResearchDiscoveryCampaignV5(
        hypothesis_registry_fingerprint=protocol.source_hypothesis_registry_fingerprint,
        screening_protocol_fingerprint=protocol.logical_fingerprint,
        formal_trials=_completed_campaign_three_trials(),
    )


@lru_cache(maxsize=1)
def _completed_campaign_three_trials() -> tuple[QuantResearchDiscoveryTrialV5, ...]:
    return tuple(
        QuantResearchDiscoveryTrialV5(
            trial_id=item.trial_id,
            hypothesis_id=item.hypothesis_id,
            hypothesis_fingerprint=item.hypothesis_fingerprint,
            role=item.role,
            related_hypothesis_family=item.related_hypothesis_family,
        )
        for item in quant_research_campaign_three_screening_protocol_v1().formal_hypotheses
    )


def _trial_matches_hypothesis(
    trial: QuantResearchDiscoveryTrialV5,
    hypothesis: CampaignThreeScreeningHypothesisV1,
) -> bool:
    return (
        trial.hypothesis_id == hypothesis.hypothesis_id
        and trial.hypothesis_fingerprint == hypothesis.hypothesis_fingerprint
        and trial.role is hypothesis.role
        and trial.related_hypothesis_family == hypothesis.related_hypothesis_family
        and trial.primary_horizon_sessions == hypothesis.primary_horizon_sessions
    )
