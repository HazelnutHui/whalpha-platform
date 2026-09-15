"""Cumulative, append-only trial accounting for governed factor discovery."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_factor_catalog import (
    QuantResearchFactorRole,
    factor_definition_fingerprint,
    quant_research_factor_catalog_v1,
)
from .quant_research_factor_screening import (
    QuantResearchFactorScreeningTarget,
    quant_research_factor_screening_protocol_v1,
)


QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_CONTRACT_VERSION = (
    "quant-research-discovery-trial-ledger/1.0"
)
QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_VERSION = (
    "whalpha.quant-research.discovery-trial-ledger/1.0.0"
)
FACTOR_SCREENING_V1_REPORT_FINGERPRINT = (
    "5e40cd9ab11dd20a98aabdf0834dc3cfb5c5a173a94929eca73891db8f8f789a"
)
FACTOR_SCREENING_V1_REPORT_SHA256 = (
    "184bc3f92f97809fbc69ea13877857d78a81472d0fbd15fa48bbce0891c62704"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchDiscoveryTrialDisposition(StrEnum):
    REJECTED_SCREEN = "rejected_screen"
    RETAINED_RISK_EVIDENCE = "retained_risk_evidence"


class QuantResearchDiscoveryTrialV1(FrozenModel):
    trial_id: str = Field(pattern=r"^whalpha\.discovery-trial\.[a-z0-9_.-]+$")
    campaign_id: Literal["whalpha.factor-discovery.price-volume-v1"] = (
        "whalpha.factor-discovery.price-volume-v1"
    )
    factor_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    factor_version: str = Field(pattern=r"^whalpha\.factor\.[a-z0-9_.-]+/1\.0\.0$")
    factor_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: QuantResearchFactorRole
    target: QuantResearchFactorScreeningTarget
    related_factor_group: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    primary_horizon_sessions: Literal[3] = 3
    formal_trial_count: Literal[1] = 1
    outcome_partition: Literal["development"] = "development"
    outcome_accessed: Literal[True] = True
    outcome_access_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    disposition: QuantResearchDiscoveryTrialDisposition
    report_fingerprint: Literal[FACTOR_SCREENING_V1_REPORT_FINGERPRINT] = (
        FACTOR_SCREENING_V1_REPORT_FINGERPRINT
    )
    report_sha256: Literal[FACTOR_SCREENING_V1_REPORT_SHA256] = (
        FACTOR_SCREENING_V1_REPORT_SHA256
    )
    validation_accessed: Literal[False] = False
    holdout_accessed: Literal[False] = False
    model_input_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False


class QuantResearchDiscoveryCampaignV1(FrozenModel):
    campaign_id: Literal["whalpha.factor-discovery.price-volume-v1"] = (
        "whalpha.factor-discovery.price-volume-v1"
    )
    registered_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    completed_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    catalog_id: Literal["whalpha.factor-catalog.price-volume-v1"] = (
        "whalpha.factor-catalog.price-volume-v1"
    )
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    screening_protocol_version: Literal["quant-research-factor-screening/1.0.0"] = (
        "quant-research-factor-screening/1.0.0"
    )
    screening_protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_status: Literal["closed_no_candidate_alpha"] = (
        "closed_no_candidate_alpha"
    )
    report_fingerprint: Literal[FACTOR_SCREENING_V1_REPORT_FINGERPRINT] = (
        FACTOR_SCREENING_V1_REPORT_FINGERPRINT
    )
    report_sha256: Literal[FACTOR_SCREENING_V1_REPORT_SHA256] = (
        FACTOR_SCREENING_V1_REPORT_SHA256
    )
    formal_trials: tuple[QuantResearchDiscoveryTrialV1, ...] = Field(
        min_length=8, max_length=8
    )
    formal_trial_count: Literal[8] = 8
    candidate_alpha_trial_count: Literal[5] = 5
    risk_guard_trial_count: Literal[3] = 3
    setup_conditioner_outcome_trial_count: Literal[0] = 0
    candidate_alpha_admitted_count: Literal[0] = 0
    retained_risk_evidence_count: Literal[1] = 1
    model_construction_authorized: Literal[False] = False

    @model_validator(mode="after")
    def campaign_reconciles(self) -> "QuantResearchDiscoveryCampaignV1":
        catalog = quant_research_factor_catalog_v1()
        protocol = quant_research_factor_screening_protocol_v1()
        if (
            self.catalog_fingerprint != catalog.logical_fingerprint
            or self.screening_protocol_fingerprint != protocol.logical_fingerprint
            or self.formal_trials != _factor_screening_v1_trials()
            or sum(item.formal_trial_count for item in self.formal_trials) != 8
            or len({item.trial_id for item in self.formal_trials}) != 8
        ):
            raise ValueError("Factor Discovery V1 campaign ledger differs")
        role_counts = {
            role: sum(item.role is role for item in self.formal_trials)
            for role in QuantResearchFactorRole
        }
        if role_counts != {
            QuantResearchFactorRole.CANDIDATE_ALPHA: 5,
            QuantResearchFactorRole.SETUP_CONDITIONER: 0,
            QuantResearchFactorRole.RISK_GUARD: 3,
        }:
            raise ValueError("Factor Discovery V1 trial role counts differ")
        if sum(
            item.disposition
            is QuantResearchDiscoveryTrialDisposition.RETAINED_RISK_EVIDENCE
            for item in self.formal_trials
        ) != 1:
            raise ValueError("Factor Discovery V1 retained evidence differs")
        return self


class QuantResearchDiscoveryTrialLedgerV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_CONTRACT_VERSION
    ] = QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_CONTRACT_VERSION
    ledger_version: Literal[QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_VERSION] = (
        QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_VERSION
    )
    registered_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    accounting_scope: Literal[
        "factor_and_registered_factor_interaction_outcome_trials"
    ] = "factor_and_registered_factor_interaction_outcome_trials"
    campaign_accounting_rule: Literal[
        "append_new_version_never_rewrite_consumed_campaign"
    ] = "append_new_version_never_rewrite_consumed_campaign"
    development_evidence_rule: Literal[
        "campaign_adjusted_screening_not_global_independent_alpha_claim"
    ] = "campaign_adjusted_screening_not_global_independent_alpha_claim"
    prior_strategy_programs_separate: tuple[
        Literal["whalpha.strong-leader-pullback"]
    ] = ("whalpha.strong-leader-pullback",)
    campaigns: tuple[QuantResearchDiscoveryCampaignV1, ...] = Field(
        min_length=1, max_length=1
    )
    completed_campaign_count: Literal[1] = 1
    cumulative_formal_trial_count: Literal[8] = 8
    cumulative_candidate_alpha_trial_count: Literal[5] = 5
    cumulative_risk_guard_trial_count: Literal[3] = 3
    cumulative_setup_conditioner_interaction_trial_count: Literal[0] = 0
    cumulative_candidate_alpha_admitted_count: Literal[0] = 0
    cumulative_retained_risk_evidence_count: Literal[1] = 1
    next_campaign_requires_new_registered_ledger_version: Literal[True] = True
    next_campaign_is_adaptive_to_consumed_development_evidence: Literal[True] = True
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    strategy_expression_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def ledger_reconciles(self) -> "QuantResearchDiscoveryTrialLedgerV1":
        expected_campaign = _factor_screening_v1_campaign()
        if self.campaigns != (expected_campaign,):
            raise ValueError("cumulative discovery campaign registry differs")
        trials = tuple(trial for campaign in self.campaigns for trial in campaign.formal_trials)
        if (
            len(trials) != self.cumulative_formal_trial_count
            or sum(item.role is QuantResearchFactorRole.CANDIDATE_ALPHA for item in trials)
            != self.cumulative_candidate_alpha_trial_count
            or sum(item.role is QuantResearchFactorRole.RISK_GUARD for item in trials)
            != self.cumulative_risk_guard_trial_count
            or discovery_trial_ledger_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("cumulative discovery trial accounting differs")
        return self


@lru_cache(maxsize=1)
def quant_research_discovery_trial_ledger_v1() -> QuantResearchDiscoveryTrialLedgerV1:
    campaign = _factor_screening_v1_campaign()
    provisional = QuantResearchDiscoveryTrialLedgerV1.model_construct(
        campaigns=(campaign,),
        logical_fingerprint="0" * 64,
    )
    return QuantResearchDiscoveryTrialLedgerV1.model_validate(
        {
            "campaigns": (campaign,),
            "logical_fingerprint": discovery_trial_ledger_fingerprint(provisional),
        }
    )


def discovery_trial_ledger_fingerprint(value: BaseModel | dict[str, object]) -> str:
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
def _factor_screening_v1_campaign() -> QuantResearchDiscoveryCampaignV1:
    catalog = quant_research_factor_catalog_v1()
    protocol = quant_research_factor_screening_protocol_v1()
    return QuantResearchDiscoveryCampaignV1(
        catalog_fingerprint=catalog.logical_fingerprint,
        screening_protocol_fingerprint=protocol.logical_fingerprint,
        formal_trials=_factor_screening_v1_trials(),
    )


@lru_cache(maxsize=1)
def _factor_screening_v1_trials() -> tuple[QuantResearchDiscoveryTrialV1, ...]:
    catalog = quant_research_factor_catalog_v1()
    protocol = quant_research_factor_screening_protocol_v1()
    definitions = {item.factor_id: item for item in catalog.definitions}
    retained = "rolling_maximum_drawdown_10s"
    return tuple(
        QuantResearchDiscoveryTrialV1(
            trial_id=f"whalpha.discovery-trial.price-volume-v1.{item.factor_id}.h3",
            factor_id=item.factor_id,
            factor_version=definitions[item.factor_id].factor_version,
            factor_definition_fingerprint=factor_definition_fingerprint(item.factor_id),
            role=item.role,
            target=item.target,
            related_factor_group=item.related_factor_group,
            disposition=(
                QuantResearchDiscoveryTrialDisposition.RETAINED_RISK_EVIDENCE
                if item.factor_id == retained
                else QuantResearchDiscoveryTrialDisposition.REJECTED_SCREEN
            ),
        )
        for item in protocol.formal_hypotheses
    )
