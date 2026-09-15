"""Preregistered cumulative trial accounting through Factor Discovery V2."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_discovery_trial_ledger import (
    QuantResearchDiscoveryCampaignV1,
    quant_research_discovery_trial_ledger_v1,
)
from .quant_research_factor_catalog_v2 import (
    QuantResearchFactorRoleV2,
    quant_research_factor_catalog_v2,
)
from .quant_research_factor_screening import QuantResearchFactorScreeningTarget
from .quant_research_factor_screening_v2 import (
    QuantResearchFactorScreeningHypothesisV2,
    quant_research_factor_screening_protocol_v2,
)


QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V2_CONTRACT_VERSION = (
    "quant-research-discovery-trial-ledger/2.0"
)
QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V2_VERSION = (
    "whalpha.quant-research.discovery-trial-ledger/2.0.0"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchDiscoveryTrialDispositionV2(StrEnum):
    REGISTERED_PENDING_DEVELOPMENT_SCREEN = "registered_pending_development_screen"


class QuantResearchDiscoveryTrialV2(FrozenModel):
    trial_id: str = Field(
        pattern=r"^whalpha\.discovery-trial\.daily-behavior-v2\.[a-z0-9_]+\.h3$"
    )
    campaign_id: Literal["whalpha.factor-discovery.daily-behavior-v2"] = (
        "whalpha.factor-discovery.daily-behavior-v2"
    )
    factor_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    factor_version: str = Field(pattern=r"^whalpha\.factor\.[a-z0-9_.-]+/1\.0\.0$")
    factor_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: QuantResearchFactorRoleV2
    target: QuantResearchFactorScreeningTarget
    related_factor_group: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    primary_horizon_sessions: Literal[3] = 3
    formal_trial_count: Literal[1] = 1
    outcome_partition: Literal["development"] = "development"
    outcome_accessed: Literal[False] = False
    outcome_access_date: None = None
    disposition: Literal[
        QuantResearchDiscoveryTrialDispositionV2.REGISTERED_PENDING_DEVELOPMENT_SCREEN
    ] = QuantResearchDiscoveryTrialDispositionV2.REGISTERED_PENDING_DEVELOPMENT_SCREEN
    report_fingerprint: None = None
    report_sha256: None = None
    validation_accessed: Literal[False] = False
    holdout_accessed: Literal[False] = False
    model_input_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False

    @model_validator(mode="after")
    def trial_reconciles(self) -> "QuantResearchDiscoveryTrialV2":
        hypothesis = next(
            (
                item
                for item in quant_research_factor_screening_protocol_v2().formal_hypotheses
                if item.trial_id == self.trial_id
            ),
            None,
        )
        if hypothesis is None or not _trial_matches_hypothesis(self, hypothesis):
            raise ValueError("Factor Discovery V2 preregistered trial differs")
        return self


class QuantResearchDiscoveryCampaignV2(FrozenModel):
    campaign_id: Literal["whalpha.factor-discovery.daily-behavior-v2"] = (
        "whalpha.factor-discovery.daily-behavior-v2"
    )
    registered_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    completed_date: None = None
    catalog_id: Literal["whalpha.factor-catalog.daily-behavior-v2"] = (
        "whalpha.factor-catalog.daily-behavior-v2"
    )
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    screening_protocol_version: Literal["quant-research-factor-screening/2.0.0"] = (
        "quant-research-factor-screening/2.0.0"
    )
    screening_protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_status: Literal["registered_outcomes_unread"] = "registered_outcomes_unread"
    report_fingerprint: None = None
    report_sha256: None = None
    formal_trials: tuple[QuantResearchDiscoveryTrialV2, ...] = Field(
        min_length=6, max_length=6
    )
    formal_trial_count: Literal[6] = 6
    candidate_alpha_trial_count: Literal[4] = 4
    risk_guard_trial_count: Literal[2] = 2
    setup_conditioner_outcome_trial_count: Literal[0] = 0
    applicability_input_outcome_trial_count: Literal[0] = 0
    candidate_alpha_admitted_count: Literal[0] = 0
    retained_risk_evidence_count: Literal[0] = 0
    outcomes_read: Literal[False] = False
    model_construction_authorized: Literal[False] = False

    @model_validator(mode="after")
    def campaign_reconciles(self) -> "QuantResearchDiscoveryCampaignV2":
        catalog = quant_research_factor_catalog_v2()
        protocol = quant_research_factor_screening_protocol_v2()
        if (
            self.catalog_fingerprint != catalog.logical_fingerprint
            or self.qualification_fingerprint
            != protocol.source_qualification_fingerprint
            or self.screening_protocol_fingerprint != protocol.logical_fingerprint
            or self.formal_trials != _factor_screening_v2_trials()
            or len({item.trial_id for item in self.formal_trials}) != 6
            or sum(item.formal_trial_count for item in self.formal_trials) != 6
        ):
            raise ValueError("Factor Discovery V2 campaign ledger differs")
        role_counts = {
            role: sum(item.role is role for item in self.formal_trials)
            for role in QuantResearchFactorRoleV2
        }
        if role_counts != {
            QuantResearchFactorRoleV2.CANDIDATE_ALPHA: 4,
            QuantResearchFactorRoleV2.SETUP_CONDITIONER: 0,
            QuantResearchFactorRoleV2.APPLICABILITY_INPUT: 0,
            QuantResearchFactorRoleV2.RISK_GUARD: 2,
        }:
            raise ValueError("Factor Discovery V2 preregistered role counts differ")
        return self


class QuantResearchDiscoveryTrialLedgerV2(FrozenModel):
    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[
        QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V2_CONTRACT_VERSION
    ] = QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V2_CONTRACT_VERSION
    ledger_version: Literal[QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V2_VERSION] = (
        QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V2_VERSION
    )
    registered_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    accounting_scope: Literal[
        "factor_and_registered_factor_interaction_outcome_trials"
    ] = "factor_and_registered_factor_interaction_outcome_trials"
    campaign_accounting_rule: Literal[
        "append_new_version_never_rewrite_consumed_or_registered_campaign"
    ] = "append_new_version_never_rewrite_consumed_or_registered_campaign"
    development_evidence_rule: Literal[
        "campaign_adjusted_screening_not_global_independent_alpha_claim"
    ] = "campaign_adjusted_screening_not_global_independent_alpha_claim"
    prior_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    prior_strategy_programs_separate: tuple[
        Literal["whalpha.strong-leader-pullback"]
    ] = ("whalpha.strong-leader-pullback",)
    campaigns: tuple[
        QuantResearchDiscoveryCampaignV1,
        QuantResearchDiscoveryCampaignV2,
    ]
    completed_campaign_count: Literal[1] = 1
    registered_unread_campaign_count: Literal[1] = 1
    cumulative_formal_trial_count: Literal[14] = 14
    cumulative_candidate_alpha_trial_count: Literal[9] = 9
    cumulative_risk_guard_trial_count: Literal[5] = 5
    cumulative_setup_conditioner_interaction_trial_count: Literal[0] = 0
    cumulative_applicability_input_outcome_trial_count: Literal[0] = 0
    cumulative_candidate_alpha_admitted_count: Literal[0] = 0
    cumulative_retained_risk_evidence_count: Literal[1] = 1
    current_campaign_is_adaptive_to_consumed_development_evidence: Literal[True] = True
    development_screen_execution_authorized: Literal[True] = True
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    strategy_expression_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def ledger_reconciles(self) -> "QuantResearchDiscoveryTrialLedgerV2":
        prior = quant_research_discovery_trial_ledger_v1()
        current = _factor_screening_v2_campaign()
        all_trials = tuple(
            trial for campaign in self.campaigns for trial in campaign.formal_trials
        )
        if (
            self.prior_ledger_fingerprint != prior.logical_fingerprint
            or self.campaigns != (prior.campaigns[0], current)
            or len({item.trial_id for item in all_trials}) != 14
            or sum(item.formal_trial_count for item in all_trials) != 14
            or sum(item.role.value == "candidate_alpha" for item in all_trials) != 9
            or sum(item.role.value == "risk_guard" for item in all_trials) != 5
            or discovery_trial_ledger_v2_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("cumulative discovery trial accounting V2 differs")
        return self


def discovery_trial_ledger_v2_fingerprint(value: BaseModel | dict[str, object]) -> str:
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


@lru_cache(maxsize=1)
def quant_research_discovery_trial_ledger_v2() -> QuantResearchDiscoveryTrialLedgerV2:
    prior = quant_research_discovery_trial_ledger_v1()
    current = _factor_screening_v2_campaign()
    payload: dict[str, object] = {
        "prior_ledger_fingerprint": prior.logical_fingerprint,
        "campaigns": (prior.campaigns[0], current),
    }
    provisional = QuantResearchDiscoveryTrialLedgerV2.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchDiscoveryTrialLedgerV2.model_validate(
        {
            **payload,
            "logical_fingerprint": discovery_trial_ledger_v2_fingerprint(provisional),
        }
    )


@lru_cache(maxsize=1)
def _factor_screening_v2_campaign() -> QuantResearchDiscoveryCampaignV2:
    catalog = quant_research_factor_catalog_v2()
    protocol = quant_research_factor_screening_protocol_v2()
    return QuantResearchDiscoveryCampaignV2(
        catalog_fingerprint=catalog.logical_fingerprint,
        qualification_fingerprint=protocol.source_qualification_fingerprint,
        screening_protocol_fingerprint=protocol.logical_fingerprint,
        formal_trials=_factor_screening_v2_trials(),
    )


@lru_cache(maxsize=1)
def _factor_screening_v2_trials() -> tuple[QuantResearchDiscoveryTrialV2, ...]:
    return tuple(
        QuantResearchDiscoveryTrialV2(
            trial_id=hypothesis.trial_id,
            factor_id=hypothesis.factor_id,
            factor_version=hypothesis.factor_version,
            factor_definition_fingerprint=(
                hypothesis.factor_definition_fingerprint
            ),
            role=hypothesis.role,
            target=hypothesis.target,
            related_factor_group=hypothesis.related_factor_group,
        )
        for hypothesis in quant_research_factor_screening_protocol_v2().formal_hypotheses
    )


def _trial_matches_hypothesis(
    trial: QuantResearchDiscoveryTrialV2,
    hypothesis: QuantResearchFactorScreeningHypothesisV2,
) -> bool:
    return (
        trial.factor_id == hypothesis.factor_id
        and trial.factor_version == hypothesis.factor_version
        and trial.factor_definition_fingerprint
        == hypothesis.factor_definition_fingerprint
        and trial.role is hypothesis.role
        and trial.target is hypothesis.target
        and trial.related_factor_group == hypothesis.related_factor_group
        and trial.primary_horizon_sessions == hypothesis.primary_horizon_sessions
    )
