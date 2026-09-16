from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_multi_agent_governance import (
    QuantResearchMultiAgentGovernanceV1,
    multi_agent_governance_fingerprint,
    quant_research_multi_agent_governance_v1,
)


def test_multi_agent_pilot_is_stage_isolated_and_outcome_closed() -> None:
    value = quant_research_multi_agent_governance_v1()
    by_role = {item.role_id.value: item for item in value.role_policies}

    assert value.current_pilot_scope == (
        "campaign_three_outcome_blind_qualification_only"
    )
    assert value.campaign_three_registered is False
    assert value.development_outcome_access_authorized is False
    assert by_role["data_evidence"].development_outcome_rows_allowed is False
    assert by_role["evaluation"].development_outcome_rows_allowed is True
    assert by_role["red_team"].development_outcome_rows_allowed is False
    assert by_role["red_team"].maximum_data_access.value == (
        "outcome_blind_source_and_derived"
    )
    assert "evaluation" not in value.active_pilot_roles
    assert value.same_model_agents_are_independent_statistical_evidence is False
    assert value.agent_count_changes_trial_budget is False


def test_multi_agent_pilot_rejects_scope_or_authority_tamper() -> None:
    payload = quant_research_multi_agent_governance_v1().model_dump(mode="python")
    changed = deepcopy(payload)
    changed["development_outcome_access_authorized"] = True
    changed["logical_fingerprint"] = multi_agent_governance_fingerprint(changed)

    with pytest.raises(ValidationError):
        QuantResearchMultiAgentGovernanceV1.model_validate(changed)
