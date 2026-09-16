"""Current renewable-cycle state after Campaign Three closure."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_discovery_cycle import (
    QuantResearchDiscoveryStageId,
    quant_research_discovery_cycle_v1,
)
from .quant_research_discovery_trial_ledger_v5 import (
    quant_research_discovery_trial_ledger_v5,
)


QUANT_RESEARCH_DISCOVERY_CYCLE_STATE_V2_CONTRACT_VERSION = (
    "quant-research-discovery-cycle-state/2.0"
)
QUANT_RESEARCH_DISCOVERY_CYCLE_STATE_V2_VERSION = (
    "whalpha.factor-discovery-cycle-state/2.0.0"
)


class QuantResearchDiscoveryCycleStateV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[
        QUANT_RESEARCH_DISCOVERY_CYCLE_STATE_V2_CONTRACT_VERSION
    ] = QUANT_RESEARCH_DISCOVERY_CYCLE_STATE_V2_CONTRACT_VERSION
    state_version: Literal[QUANT_RESEARCH_DISCOVERY_CYCLE_STATE_V2_VERSION] = (
        QUANT_RESEARCH_DISCOVERY_CYCLE_STATE_V2_VERSION
    )
    source_cycle_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_completed_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_status: Literal["ready_for_next_campaign_design"] = (
        "ready_for_next_campaign_design"
    )
    current_stage: Literal[QuantResearchDiscoveryStageId.HYPOTHESIS_INTAKE] = (
        QuantResearchDiscoveryStageId.HYPOTHESIS_INTAKE
    )
    completed_campaign_count: Literal[3] = 3
    cumulative_formal_trial_count: Literal[17] = 17
    active_campaign_id: Literal[None] = None
    next_campaign_registered: Literal[False] = False
    admitted_alpha_count: Literal[0] = 0
    active_model_count: Literal[0] = 0
    active_strategy_count: Literal[0] = 0
    next_outcome_access_requires_new_registered_campaign: Literal[True] = True
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def state_reconciles(self) -> "QuantResearchDiscoveryCycleStateV2":
        cycle = quant_research_discovery_cycle_v1()
        ledger = quant_research_discovery_trial_ledger_v5()
        if (
            self.source_cycle_policy_fingerprint != cycle.logical_fingerprint
            or self.source_completed_ledger_fingerprint != ledger.logical_fingerprint
            or self.completed_campaign_count != ledger.completed_campaign_count
            or self.cumulative_formal_trial_count
            != ledger.cumulative_formal_trial_count
            or discovery_cycle_state_v2_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("renewable discovery-cycle state differs")
        return self


def discovery_cycle_state_v2_fingerprint(
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
def quant_research_discovery_cycle_state_v2() -> QuantResearchDiscoveryCycleStateV2:
    cycle = quant_research_discovery_cycle_v1()
    ledger = quant_research_discovery_trial_ledger_v5()
    payload: dict[str, object] = {
        "source_cycle_policy_fingerprint": cycle.logical_fingerprint,
        "source_completed_ledger_fingerprint": ledger.logical_fingerprint,
    }
    provisional = QuantResearchDiscoveryCycleStateV2.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return QuantResearchDiscoveryCycleStateV2.model_validate(
        {
            **payload,
            "logical_fingerprint": discovery_cycle_state_v2_fingerprint(provisional),
        }
    )
