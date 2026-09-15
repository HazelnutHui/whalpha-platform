"""Completed cumulative trial accounting through Factor Discovery V2."""

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
from .quant_research_discovery_trial_ledger_v2 import (
    quant_research_discovery_trial_ledger_v2,
)
from .quant_research_factor_catalog_v2 import QuantResearchFactorRoleV2
from .quant_research_factor_screening import QuantResearchFactorScreeningTarget
from .quant_research_factor_screening_v2 import (
    QuantResearchFactorScreeningHypothesisV2,
    quant_research_factor_screening_protocol_v2,
)


QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V3_CONTRACT_VERSION = (
    "quant-research-discovery-trial-ledger/3.0"
)
QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V3_VERSION = (
    "whalpha.quant-research.discovery-trial-ledger/3.0.0"
)
FACTOR_SCREENING_V2_REPORT_FINGERPRINT = (
    "caf88beb14434f60d4cf018dc6bc5c33b2c788b6504b1db93107faecdd313f42"
)
FACTOR_SCREENING_V2_REPORT_SHA256 = (
    "c900ce46f1685e140e3ef9f309bf0d1cda34b1838df7f4741678b9170d4f0733"
)
_V2_ALPHA_FACTOR_IDS = frozenset(
    {
        "medium_term_relative_momentum_126s_skip5",
        "short_term_relative_reversal_5s",
        "intraday_relative_pressure_reversal_5s",
        "overnight_relative_persistence_5s",
    }
)
_V2_QUALIFIED_RISK_FACTOR_IDS = frozenset(
    {
        "single_index_residual_volatility_60s",
        "relative_downside_semideviation_60s",
    }
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchDiscoveryTrialDispositionV3(StrEnum):
    REJECTED_SCREEN = "rejected_screen"
    QUALIFIED_RISK_NOT_SELECTED_NO_ALPHA = (
        "qualified_risk_evidence_not_selected_no_candidate_alpha"
    )


class QuantResearchDiscoveryTrialV3(FrozenModel):
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
    outcome_accessed: Literal[True] = True
    outcome_access_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    disposition: QuantResearchDiscoveryTrialDispositionV3
    report_fingerprint: Literal[FACTOR_SCREENING_V2_REPORT_FINGERPRINT] = (
        FACTOR_SCREENING_V2_REPORT_FINGERPRINT
    )
    report_sha256: Literal[FACTOR_SCREENING_V2_REPORT_SHA256] = (
        FACTOR_SCREENING_V2_REPORT_SHA256
    )
    validation_accessed: Literal[False] = False
    holdout_accessed: Literal[False] = False
    model_input_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False

    @model_validator(mode="after")
    def trial_reconciles(self) -> "QuantResearchDiscoveryTrialV3":
        hypothesis = next(
            (
                item
                for item in quant_research_factor_screening_protocol_v2().formal_hypotheses
                if item.trial_id == self.trial_id
            ),
            None,
        )
        if hypothesis is None or not _trial_matches_hypothesis(self, hypothesis):
            raise ValueError("completed Factor Discovery V2 trial differs")
        expected = (
            QuantResearchDiscoveryTrialDispositionV3.REJECTED_SCREEN
            if self.factor_id in _V2_ALPHA_FACTOR_IDS
            else QuantResearchDiscoveryTrialDispositionV3.QUALIFIED_RISK_NOT_SELECTED_NO_ALPHA
        )
        if self.disposition is not expected:
            raise ValueError("completed Factor Discovery V2 disposition differs")
        return self


class QuantResearchDiscoveryCampaignV3(FrozenModel):
    campaign_id: Literal["whalpha.factor-discovery.daily-behavior-v2"] = (
        "whalpha.factor-discovery.daily-behavior-v2"
    )
    registered_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    completed_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    catalog_id: Literal["whalpha.factor-catalog.daily-behavior-v2"] = (
        "whalpha.factor-catalog.daily-behavior-v2"
    )
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    screening_protocol_version: Literal["quant-research-factor-screening/2.0.0"] = (
        "quant-research-factor-screening/2.0.0"
    )
    screening_protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_status: Literal["closed_no_candidate_alpha"] = "closed_no_candidate_alpha"
    report_fingerprint: Literal[FACTOR_SCREENING_V2_REPORT_FINGERPRINT] = (
        FACTOR_SCREENING_V2_REPORT_FINGERPRINT
    )
    report_sha256: Literal[FACTOR_SCREENING_V2_REPORT_SHA256] = (
        FACTOR_SCREENING_V2_REPORT_SHA256
    )
    exact_replay_verified: Literal[True] = True
    formal_trials: tuple[QuantResearchDiscoveryTrialV3, ...] = Field(
        min_length=6, max_length=6
    )
    formal_trial_count: Literal[6] = 6
    candidate_alpha_trial_count: Literal[4] = 4
    risk_guard_trial_count: Literal[2] = 2
    setup_conditioner_outcome_trial_count: Literal[0] = 0
    applicability_input_outcome_trial_count: Literal[0] = 0
    candidate_alpha_admitted_count: Literal[0] = 0
    qualified_risk_evidence_count: Literal[2] = 2
    selected_model_input_count: Literal[0] = 0
    outcomes_read: Literal[True] = True
    model_construction_authorized: Literal[False] = False

    @model_validator(mode="after")
    def campaign_reconciles(self) -> "QuantResearchDiscoveryCampaignV3":
        protocol = quant_research_factor_screening_protocol_v2()
        if (
            self.catalog_fingerprint != protocol.catalog_fingerprint
            or self.qualification_fingerprint != protocol.source_qualification_fingerprint
            or self.screening_protocol_fingerprint != protocol.logical_fingerprint
            or self.formal_trials != _completed_factor_screening_v2_trials()
            or len({item.trial_id for item in self.formal_trials}) != 6
            or sum(item.formal_trial_count for item in self.formal_trials) != 6
        ):
            raise ValueError("completed Factor Discovery V2 campaign differs")
        if (
            sum(
                item.disposition
                is QuantResearchDiscoveryTrialDispositionV3.REJECTED_SCREEN
                for item in self.formal_trials
            )
            != 4
            or sum(
                item.disposition
                is QuantResearchDiscoveryTrialDispositionV3.QUALIFIED_RISK_NOT_SELECTED_NO_ALPHA
                for item in self.formal_trials
            )
            != 2
        ):
            raise ValueError("completed Factor Discovery V2 decision counts differ")
        return self


class QuantResearchDiscoveryTrialLedgerV3(FrozenModel):
    schema_version: Literal["3.0"] = "3.0"
    contract_version: Literal[
        QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V3_CONTRACT_VERSION
    ] = QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V3_CONTRACT_VERSION
    ledger_version: Literal[QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V3_VERSION] = (
        QUANT_RESEARCH_DISCOVERY_TRIAL_LEDGER_V3_VERSION
    )
    completed_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
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
    ]
    completed_campaign_count: Literal[2] = 2
    registered_unread_campaign_count: Literal[0] = 0
    cumulative_formal_trial_count: Literal[14] = 14
    cumulative_candidate_alpha_trial_count: Literal[9] = 9
    cumulative_risk_guard_trial_count: Literal[5] = 5
    cumulative_setup_conditioner_interaction_trial_count: Literal[0] = 0
    cumulative_applicability_input_outcome_trial_count: Literal[0] = 0
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
    def ledger_reconciles(self) -> "QuantResearchDiscoveryTrialLedgerV3":
        prior = quant_research_discovery_trial_ledger_v2()
        v1 = quant_research_discovery_trial_ledger_v1().campaigns[0]
        v2 = _completed_factor_screening_v2_campaign()
        all_trials = tuple(
            trial for campaign in self.campaigns for trial in campaign.formal_trials
        )
        if (
            self.prior_ledger_fingerprint != prior.logical_fingerprint
            or self.campaigns != (v1, v2)
            or len({item.trial_id for item in all_trials}) != 14
            or sum(item.formal_trial_count for item in all_trials) != 14
            or discovery_trial_ledger_v3_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("completed cumulative discovery trial accounting differs")
        return self


def discovery_trial_ledger_v3_fingerprint(value: BaseModel | dict[str, object]) -> str:
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
def quant_research_discovery_trial_ledger_v3() -> QuantResearchDiscoveryTrialLedgerV3:
    prior = quant_research_discovery_trial_ledger_v2()
    campaigns = (
        quant_research_discovery_trial_ledger_v1().campaigns[0],
        _completed_factor_screening_v2_campaign(),
    )
    payload: dict[str, object] = {
        "prior_ledger_fingerprint": prior.logical_fingerprint,
        "campaigns": campaigns,
    }
    provisional = QuantResearchDiscoveryTrialLedgerV3.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchDiscoveryTrialLedgerV3.model_validate(
        {
            **payload,
            "logical_fingerprint": discovery_trial_ledger_v3_fingerprint(provisional),
        }
    )


@lru_cache(maxsize=1)
def _completed_factor_screening_v2_campaign() -> QuantResearchDiscoveryCampaignV3:
    protocol = quant_research_factor_screening_protocol_v2()
    return QuantResearchDiscoveryCampaignV3(
        catalog_fingerprint=protocol.catalog_fingerprint,
        qualification_fingerprint=protocol.source_qualification_fingerprint,
        screening_protocol_fingerprint=protocol.logical_fingerprint,
        formal_trials=_completed_factor_screening_v2_trials(),
    )


@lru_cache(maxsize=1)
def _completed_factor_screening_v2_trials() -> tuple[QuantResearchDiscoveryTrialV3, ...]:
    trials: list[QuantResearchDiscoveryTrialV3] = []
    for hypothesis in quant_research_factor_screening_protocol_v2().formal_hypotheses:
        if hypothesis.factor_id in _V2_ALPHA_FACTOR_IDS:
            disposition = QuantResearchDiscoveryTrialDispositionV3.REJECTED_SCREEN
        elif hypothesis.factor_id in _V2_QUALIFIED_RISK_FACTOR_IDS:
            disposition = (
                QuantResearchDiscoveryTrialDispositionV3.QUALIFIED_RISK_NOT_SELECTED_NO_ALPHA
            )
        else:
            raise ValueError("unrecognized completed Factor Discovery V2 trial")
        trials.append(
            QuantResearchDiscoveryTrialV3(
                trial_id=hypothesis.trial_id,
                factor_id=hypothesis.factor_id,
                factor_version=hypothesis.factor_version,
                factor_definition_fingerprint=hypothesis.factor_definition_fingerprint,
                role=hypothesis.role,
                target=hypothesis.target,
                related_factor_group=hypothesis.related_factor_group,
                disposition=disposition,
            )
        )
    return tuple(trials)


def _trial_matches_hypothesis(
    trial: QuantResearchDiscoveryTrialV3,
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
