"""Stage-isolated multi-agent governance for the first bounded pilot."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_discovery_cycle import (
    QuantResearchDiscoveryStageId,
    quant_research_discovery_cycle_v1,
)
from .quant_research_reusable_artifacts import (
    quant_research_reusable_artifact_registry_v1,
)


QUANT_RESEARCH_MULTI_AGENT_GOVERNANCE_CONTRACT_VERSION = (
    "quant-research-multi-agent-governance/1.0"
)
QUANT_RESEARCH_MULTI_AGENT_GOVERNANCE_VERSION = (
    "whalpha.quant-research.multi-agent-governance/1.0.0"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchAgentRoleId(StrEnum):
    RESEARCH_CONTROLLER = "research_controller"
    DATA_EVIDENCE = "data_evidence"
    HYPOTHESIS = "hypothesis"
    IMPLEMENTATION = "implementation"
    EVALUATION = "evaluation"
    RED_TEAM = "red_team"
    APPROVAL_PUBLICATION = "approval_publication"


class QuantResearchAgentDataAccess(StrEnum):
    COMPACT_GOVERNED_SUMMARIES = "compact_governed_summaries"
    OUTCOME_BLIND_SOURCE_AND_DERIVED = "outcome_blind_source_and_derived"
    REGISTERED_DEVELOPMENT_SLICE = "registered_development_slice"
    REVIEWED_REPORTS_ONLY = "reviewed_reports_only"


class QuantResearchAgentRolePolicyV1(FrozenModel):
    role_id: QuantResearchAgentRoleId
    permitted_stages: tuple[QuantResearchDiscoveryStageId, ...] = Field(
        min_length=1
    )
    maximum_data_access: QuantResearchAgentDataAccess
    development_outcome_rows_allowed: bool
    validation_rows_allowed: Literal[False] = False
    holdout_rows_allowed: Literal[False] = False
    may_transition_stage: bool
    deterministic_gate_override_allowed: Literal[False] = False
    required_handoff: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")


class QuantResearchMultiAgentGovernanceV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_MULTI_AGENT_GOVERNANCE_CONTRACT_VERSION
    ] = QUANT_RESEARCH_MULTI_AGENT_GOVERNANCE_CONTRACT_VERSION
    governance_version: Literal[
        QUANT_RESEARCH_MULTI_AGENT_GOVERNANCE_VERSION
    ] = QUANT_RESEARCH_MULTI_AGENT_GOVERNANCE_VERSION
    accepted_date: Literal[date(2026, 9, 16)] = date(2026, 9, 16)
    source_cycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_reusable_artifact_registry_fingerprint: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    implementation_status: Literal[
        "outcome_blind_pilot_ready_campaign_not_registered"
    ] = "outcome_blind_pilot_ready_campaign_not_registered"
    current_pilot_scope: Literal[
        "campaign_three_outcome_blind_qualification_only"
    ] = "campaign_three_outcome_blind_qualification_only"
    role_policies: tuple[QuantResearchAgentRolePolicyV1, ...] = Field(
        min_length=7,
        max_length=7,
    )
    active_pilot_roles: tuple[
        Literal[
            QuantResearchAgentRoleId.RESEARCH_CONTROLLER,
            QuantResearchAgentRoleId.DATA_EVIDENCE,
            QuantResearchAgentRoleId.HYPOTHESIS,
            QuantResearchAgentRoleId.IMPLEMENTATION,
            QuantResearchAgentRoleId.RED_TEAM,
        ],
        ...,
    ]
    shared_accounting_artifacts: tuple[
        Literal[
            "campaign_identity",
            "duplicate_signature",
            "finite_trial_budget",
            "content_addressed_input_registry",
            "append_only_cumulative_trial_ledger",
        ],
        ...,
    ] = Field(min_length=5, max_length=5)
    parallel_work_rule: Literal[
        "same_outcome_access_class_and_disjoint_artifact_writes_only"
    ] = "same_outcome_access_class_and_disjoint_artifact_writes_only"
    serial_gate_order: tuple[
        Literal[
            "protocol_freeze",
            "development_evaluation",
            "independent_replay_and_red_team",
            "ledger_close",
            "human_route_decision",
        ],
        ...,
    ] = Field(min_length=5, max_length=5)
    same_model_agents_are_independent_statistical_evidence: Literal[False] = False
    agent_count_changes_trial_budget: Literal[False] = False
    unattended_agent_service_authorized: Literal[False] = False
    campaign_three_registered: Literal[False] = False
    development_outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    product_activation_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    trading_authorized: Literal[False] = False
    human_approval_required_for_scope_expansion: Literal[True] = True
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def governance_reconciles(self) -> "QuantResearchMultiAgentGovernanceV1":
        cycle = quant_research_discovery_cycle_v1()
        registry = quant_research_reusable_artifact_registry_v1()
        if (
            self.source_cycle_fingerprint != cycle.logical_fingerprint
            or self.source_reusable_artifact_registry_fingerprint
            != registry.logical_fingerprint
            or self.role_policies != _role_policies()
            or tuple(item.role_id for item in self.role_policies)
            != tuple(QuantResearchAgentRoleId)
            or self.active_pilot_roles
            != (
                QuantResearchAgentRoleId.RESEARCH_CONTROLLER,
                QuantResearchAgentRoleId.DATA_EVIDENCE,
                QuantResearchAgentRoleId.HYPOTHESIS,
                QuantResearchAgentRoleId.IMPLEMENTATION,
                QuantResearchAgentRoleId.RED_TEAM,
            )
            or len(set(self.shared_accounting_artifacts)) != 5
            or len(set(self.serial_gate_order)) != 5
            or multi_agent_governance_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("multi-agent research governance differs")
        return self


def multi_agent_governance_fingerprint(
    value: BaseModel | dict[str, object],
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
def quant_research_multi_agent_governance_v1() -> (
    QuantResearchMultiAgentGovernanceV1
):
    cycle = quant_research_discovery_cycle_v1()
    registry = quant_research_reusable_artifact_registry_v1()
    payload = {
        "source_cycle_fingerprint": cycle.logical_fingerprint,
        "source_reusable_artifact_registry_fingerprint": (
            registry.logical_fingerprint
        ),
        "role_policies": _role_policies(),
        "active_pilot_roles": (
            QuantResearchAgentRoleId.RESEARCH_CONTROLLER,
            QuantResearchAgentRoleId.DATA_EVIDENCE,
            QuantResearchAgentRoleId.HYPOTHESIS,
            QuantResearchAgentRoleId.IMPLEMENTATION,
            QuantResearchAgentRoleId.RED_TEAM,
        ),
        "shared_accounting_artifacts": (
            "campaign_identity",
            "duplicate_signature",
            "finite_trial_budget",
            "content_addressed_input_registry",
            "append_only_cumulative_trial_ledger",
        ),
        "serial_gate_order": (
            "protocol_freeze",
            "development_evaluation",
            "independent_replay_and_red_team",
            "ledger_close",
            "human_route_decision",
        ),
    }
    provisional = QuantResearchMultiAgentGovernanceV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchMultiAgentGovernanceV1.model_validate(
        {
            **payload,
            "logical_fingerprint": multi_agent_governance_fingerprint(provisional),
        }
    )


def _role_policies() -> tuple[QuantResearchAgentRolePolicyV1, ...]:
    stage = QuantResearchDiscoveryStageId
    access = QuantResearchAgentDataAccess
    return (
        QuantResearchAgentRolePolicyV1(
            role_id=QuantResearchAgentRoleId.RESEARCH_CONTROLLER,
            permitted_stages=tuple(stage),
            maximum_data_access=access.COMPACT_GOVERNED_SUMMARIES,
            development_outcome_rows_allowed=False,
            may_transition_stage=True,
            required_handoff="stage_decision",
        ),
        QuantResearchAgentRolePolicyV1(
            role_id=QuantResearchAgentRoleId.DATA_EVIDENCE,
            permitted_stages=(stage.DATA_ADMISSION, stage.OUTCOME_BLIND_QUALIFICATION),
            maximum_data_access=access.OUTCOME_BLIND_SOURCE_AND_DERIVED,
            development_outcome_rows_allowed=False,
            may_transition_stage=False,
            required_handoff="data_admission_report",
        ),
        QuantResearchAgentRolePolicyV1(
            role_id=QuantResearchAgentRoleId.HYPOTHESIS,
            permitted_stages=(stage.HYPOTHESIS_INTAKE, stage.DEDUPLICATION),
            maximum_data_access=access.COMPACT_GOVERNED_SUMMARIES,
            development_outcome_rows_allowed=False,
            may_transition_stage=False,
            required_handoff="hypothesis_cards",
        ),
        QuantResearchAgentRolePolicyV1(
            role_id=QuantResearchAgentRoleId.IMPLEMENTATION,
            permitted_stages=(stage.OUTCOME_BLIND_QUALIFICATION,),
            maximum_data_access=access.OUTCOME_BLIND_SOURCE_AND_DERIVED,
            development_outcome_rows_allowed=False,
            may_transition_stage=False,
            required_handoff="implementation_manifest",
        ),
        QuantResearchAgentRolePolicyV1(
            role_id=QuantResearchAgentRoleId.EVALUATION,
            permitted_stages=(stage.DEVELOPMENT_SCREEN,),
            maximum_data_access=access.REGISTERED_DEVELOPMENT_SLICE,
            development_outcome_rows_allowed=True,
            may_transition_stage=False,
            required_handoff="immutable_evaluation_report",
        ),
        QuantResearchAgentRolePolicyV1(
            role_id=QuantResearchAgentRoleId.RED_TEAM,
            permitted_stages=(stage.OUTCOME_BLIND_QUALIFICATION,),
            maximum_data_access=access.OUTCOME_BLIND_SOURCE_AND_DERIVED,
            development_outcome_rows_allowed=False,
            may_transition_stage=False,
            required_handoff="outcome_blind_red_team_report",
        ),
        QuantResearchAgentRolePolicyV1(
            role_id=QuantResearchAgentRoleId.APPROVAL_PUBLICATION,
            permitted_stages=(stage.LEDGER_CLOSE_AND_ROUTE,),
            maximum_data_access=access.REVIEWED_REPORTS_ONLY,
            development_outcome_rows_allowed=False,
            may_transition_stage=False,
            required_handoff="promotion_publication_decision",
        ),
    )
