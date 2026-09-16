from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_campaign_three_hypotheses import (
    CampaignThreeHypothesisRole,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_screening import (
    CAMPAIGN_THREE_QUALIFIED_HYPOTHESIS_IDS,
    CAMPAIGN_THREE_REJECTED_INPUT_HYPOTHESIS_ID,
    CampaignThreeScreeningProtocolV1,
    campaign_three_screening_fingerprint,
    quant_research_campaign_three_screening_protocol_v1,
)


def test_campaign_three_protocol_is_finite_registered_and_outcomes_closed() -> None:
    first = quant_research_campaign_three_screening_protocol_v1()
    second = quant_research_campaign_three_screening_protocol_v1()

    assert first == second
    assert tuple(item.hypothesis_id for item in first.formal_hypotheses) == (
        CAMPAIGN_THREE_QUALIFIED_HYPOTHESIS_IDS
    )
    assert CAMPAIGN_THREE_REJECTED_INPUT_HYPOTHESIS_ID not in {
        item.hypothesis_id for item in first.formal_hypotheses
    }
    assert first.formal_trial_count == 3
    assert first.prior_consumed_trial_count == 14
    assert first.cumulative_trial_count_after_registration == 17
    assert sum(
        item.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
        for item in first.formal_hypotheses
    ) == 2
    assert sum(
        item.role is CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION
        for item in first.formal_hypotheses
    ) == 1
    assert first.primary_bootstrap_block_sessions == 10
    assert first.sensitivity_bootstrap_block_sessions == 20
    assert first.bootstrap_replicates == 10_000
    assert first.maximum_selected_candidate_alpha == 1
    assert first.maximum_selected_risk_guard == 1
    assert first.development_access_requires_separate_typed_grant is True
    assert first.development_outcome_read_authorized is False
    assert first.validation_authorized is False
    assert first.holdout_access_authorized is False
    assert first.logical_fingerprint == campaign_three_screening_fingerprint(first)


def test_campaign_three_protocol_rejects_gate_drift() -> None:
    payload = quant_research_campaign_three_screening_protocol_v1().model_dump(
        mode="python"
    )
    payload["primary_bootstrap_block_sessions"] = 5
    payload["logical_fingerprint"] = campaign_three_screening_fingerprint(payload)

    with pytest.raises(ValidationError):
        CampaignThreeScreeningProtocolV1.model_validate(payload)


def test_campaign_three_protocol_rejects_reintroducing_failed_design() -> None:
    payload = quant_research_campaign_three_screening_protocol_v1().model_dump(
        mode="python"
    )
    hypotheses = deepcopy(payload["formal_hypotheses"])
    hypotheses[0]["hypothesis_id"] = CAMPAIGN_THREE_REJECTED_INPUT_HYPOTHESIS_ID
    payload["formal_hypotheses"] = hypotheses
    payload["logical_fingerprint"] = campaign_three_screening_fingerprint(payload)

    with pytest.raises(ValidationError, match="Campaign Three screening"):
        CampaignThreeScreeningProtocolV1.model_validate(payload)
