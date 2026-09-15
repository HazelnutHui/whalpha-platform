"""Renewable governance contract for successive bounded factor campaigns."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_discovery_trial_ledger_v3 import (
    quant_research_discovery_trial_ledger_v3,
)


QUANT_RESEARCH_DISCOVERY_CYCLE_CONTRACT_VERSION = (
    "quant-research-discovery-cycle/1.0"
)
QUANT_RESEARCH_DISCOVERY_CYCLE_VERSION = "whalpha.factor-discovery-cycle/1.0.0"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchDiscoveryStageId(StrEnum):
    HYPOTHESIS_INTAKE = "hypothesis_intake"
    DEDUPLICATION = "deduplication"
    DATA_ADMISSION = "data_admission"
    OUTCOME_BLIND_QUALIFICATION = "outcome_blind_qualification"
    PROTOCOL_PREREGISTRATION = "protocol_preregistration"
    DEVELOPMENT_SCREEN = "development_screen"
    INDEPENDENT_REPLAY_AND_RED_TEAM = "independent_replay_and_red_team"
    LEDGER_CLOSE_AND_ROUTE = "ledger_close_and_route"


class QuantResearchDiscoveryCycleStage(FrozenModel):
    order: int = Field(ge=1, le=8)
    stage_id: QuantResearchDiscoveryStageId
    outcome_access_allowed: bool
    required_exit_evidence: tuple[str, ...] = Field(min_length=1)


class QuantResearchDiscoveryCycleV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_DISCOVERY_CYCLE_CONTRACT_VERSION
    ] = QUANT_RESEARCH_DISCOVERY_CYCLE_CONTRACT_VERSION
    cycle_version: Literal[QUANT_RESEARCH_DISCOVERY_CYCLE_VERSION] = (
        QUANT_RESEARCH_DISCOVERY_CYCLE_VERSION
    )
    operating_mode: Literal["continuous_sequence_of_finite_campaigns"] = (
        "continuous_sequence_of_finite_campaigns"
    )
    current_status: Literal["ready_for_next_campaign_design"] = (
        "ready_for_next_campaign_design"
    )
    current_stage: Literal[QuantResearchDiscoveryStageId.HYPOTHESIS_INTAKE] = (
        QuantResearchDiscoveryStageId.HYPOTHESIS_INTAKE
    )
    completed_campaign_count: Literal[2] = 2
    cumulative_formal_trial_count: Literal[14] = 14
    source_completed_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    active_campaign_id: None = None
    next_campaign_registered: Literal[False] = False
    program_campaign_limit: None = None
    stages: tuple[QuantResearchDiscoveryCycleStage, ...] = Field(
        min_length=8, max_length=8
    )
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
    dedup_rule: Literal[
        "reject_exact_duplicates_group_near_duplicates_register_distinct_trials"
    ] = "reject_exact_duplicates_group_near_duplicates_register_distinct_trials"
    preregistration_budget_fields: tuple[
        Literal[
            "factor_and_interaction_count",
            "parameter_variant_count",
            "outcome_horizons",
            "related_hypothesis_families",
            "multiplicity_method",
            "selection_cap",
            "stopping_rule",
        ],
        ...,
    ] = Field(min_length=7, max_length=7)
    failed_campaign_reopen_authorized: Literal[False] = False
    next_design_after_close_authorized: Literal[True] = True
    outcome_access_requires_new_registered_campaign: Literal[True] = True
    model_construction_requires_admitted_alpha: Literal[True] = True
    validation_and_holdout_remain_separate: Literal[True] = True
    activation_remains_human_reviewed: Literal[True] = True
    pause_reason_codes: tuple[
        Literal[
            "data_lineage_mismatch",
            "stage_isolation_breach",
            "trial_budget_breach",
            "exact_replay_failure",
            "sealed_partition_breach",
        ],
        ...,
    ] = Field(min_length=5, max_length=5)
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def cycle_reconciles(self) -> "QuantResearchDiscoveryCycleV1":
        ledger = quant_research_discovery_trial_ledger_v3()
        if (
            self.source_completed_ledger_fingerprint != ledger.logical_fingerprint
            or self.completed_campaign_count != ledger.completed_campaign_count
            or self.cumulative_formal_trial_count
            != ledger.cumulative_formal_trial_count
            or tuple(item.order for item in self.stages) != tuple(range(1, 9))
            or tuple(item.stage_id for item in self.stages)
            != tuple(QuantResearchDiscoveryStageId)
            or tuple(item.outcome_access_allowed for item in self.stages)
            != (False, False, False, False, False, True, True, False)
            or len(set(self.dedup_identity_fields)) != 7
            or len(set(self.preregistration_budget_fields)) != 7
            or len(set(self.pause_reason_codes)) != 5
            or discovery_cycle_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("factor discovery cycle differs from governed state")
        return self


def discovery_cycle_fingerprint(value: BaseModel | dict[str, object]) -> str:
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
def quant_research_discovery_cycle_v1() -> QuantResearchDiscoveryCycleV1:
    ledger = quant_research_discovery_trial_ledger_v3()
    payload: dict[str, object] = {
        "source_completed_ledger_fingerprint": ledger.logical_fingerprint,
        "stages": _discovery_cycle_stages(),
        "dedup_identity_fields": (
            "economic_mechanism",
            "information_set_and_cutoff",
            "formula_and_transform",
            "universe_and_eligibility",
            "horizon_and_label",
            "parameter_neighborhood",
            "related_hypothesis_family",
        ),
        "preregistration_budget_fields": (
            "factor_and_interaction_count",
            "parameter_variant_count",
            "outcome_horizons",
            "related_hypothesis_families",
            "multiplicity_method",
            "selection_cap",
            "stopping_rule",
        ),
        "pause_reason_codes": (
            "data_lineage_mismatch",
            "stage_isolation_breach",
            "trial_budget_breach",
            "exact_replay_failure",
            "sealed_partition_breach",
        ),
    }
    provisional = QuantResearchDiscoveryCycleV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchDiscoveryCycleV1.model_validate(
        {
            **payload,
            "logical_fingerprint": discovery_cycle_fingerprint(provisional),
        }
    )


def _discovery_cycle_stages() -> tuple[QuantResearchDiscoveryCycleStage, ...]:
    definitions = (
        (
            QuantResearchDiscoveryStageId.HYPOTHESIS_INTAKE,
            False,
            ("economic_mechanism", "falsifiable_expectation", "data_clock"),
        ),
        (
            QuantResearchDiscoveryStageId.DEDUPLICATION,
            False,
            ("identity_signature", "related_family", "novelty_disposition"),
        ),
        (
            QuantResearchDiscoveryStageId.DATA_ADMISSION,
            False,
            ("source_lineage", "point_in_time_availability", "missingness_policy"),
        ),
        (
            QuantResearchDiscoveryStageId.OUTCOME_BLIND_QUALIFICATION,
            False,
            ("coverage", "timing", "variation", "redundancy", "exact_replay"),
        ),
        (
            QuantResearchDiscoveryStageId.PROTOCOL_PREREGISTRATION,
            False,
            ("finite_trial_budget", "gates", "multiplicity", "stopping_rule"),
        ),
        (
            QuantResearchDiscoveryStageId.DEVELOPMENT_SCREEN,
            True,
            ("immutable_report", "all_failures_retained", "selection_cap"),
        ),
        (
            QuantResearchDiscoveryStageId.INDEPENDENT_REPLAY_AND_RED_TEAM,
            True,
            ("exact_replay", "leakage_attack", "stability_attack"),
        ),
        (
            QuantResearchDiscoveryStageId.LEDGER_CLOSE_AND_ROUTE,
            False,
            ("append_only_ledger", "authority_decision", "next_design_return"),
        ),
    )
    return tuple(
        QuantResearchDiscoveryCycleStage(
            order=index,
            stage_id=stage_id,
            outcome_access_allowed=outcome_access_allowed,
            required_exit_evidence=required_exit_evidence,
        )
        for index, (stage_id, outcome_access_allowed, required_exit_evidence) in enumerate(
            definitions,
            start=1,
        )
    )

