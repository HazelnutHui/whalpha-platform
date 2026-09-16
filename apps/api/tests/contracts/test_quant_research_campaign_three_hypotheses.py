from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_campaign_three_hypotheses import (
    CampaignThreeHypothesisCardV1,
    CampaignThreeHypothesisRegistryV1,
    CampaignThreeNoveltyDisposition,
    campaign_three_hypothesis_registry_fingerprint,
    hypothesis_duplicate_signature,
    quant_research_campaign_three_hypothesis_registry_v1,
)


def test_campaign_three_hypotheses_are_finite_outcome_blind_and_deduplicated() -> None:
    registry = quant_research_campaign_three_hypothesis_registry_v1()

    assert registry.proposal_count == 5
    assert registry.accepted_for_qualification_count == 4
    assert registry.rejected_near_duplicate_count == 1
    assert registry.prospective_candidate_alpha_trial_count == 3
    assert registry.prospective_risk_guard_trial_count == 1
    assert registry.prospective_total_trial_count == 4
    assert registry.formal_trial_count_registered == 0
    assert registry.cumulative_consumed_formal_trial_count == 14
    assert registry.campaign_three_registered is False
    assert registry.development_outcome_access_authorized is False
    assert registry.validation_access_authorized is False
    assert registry.holdout_access_authorized is False
    assert all(item.contains_forward_outcomes is False for item in registry.proposals)
    assert all(item.outcome_access_authorized is False for item in registry.proposals)
    assert len({item.duplicate_signature for item in registry.proposals}) == 5
    assert registry.logical_fingerprint == (
        campaign_three_hypothesis_registry_fingerprint(registry)
    )


def test_hypothesis_display_identifier_does_not_change_duplicate_identity() -> None:
    original = quant_research_campaign_three_hypothesis_registry_v1().proposals[0]
    payload = original.model_dump(mode="json")
    payload["hypothesis_id"] = "whalpha.hypothesis.campaign-three.renamed-display-id"

    assert hypothesis_duplicate_signature(payload) == original.duplicate_signature


def test_rejected_near_duplicate_is_retained_without_trial_budget() -> None:
    registry = quant_research_campaign_three_hypothesis_registry_v1()
    rejected = tuple(
        item
        for item in registry.proposals
        if item.novelty_disposition
        is CampaignThreeNoveltyDisposition.REJECTED_NEAR_DUPLICATE
    )

    assert len(rejected) == 1
    assert rejected[0].prospective_trial_count == 0
    assert rejected[0].rejection_reason is not None


def test_card_rejects_formula_drift_even_with_recomputed_hashes() -> None:
    card = quant_research_campaign_three_hypothesis_registry_v1().proposals[0]
    payload = card.model_dump(mode="python")
    payload["state_transform"] = "share-0.5"
    payload["duplicate_signature"] = hypothesis_duplicate_signature(payload)
    payload["logical_fingerprint"] = "0" * 64

    with pytest.raises(ValidationError, match="hypothesis card differs"):
        CampaignThreeHypothesisCardV1.model_validate(payload)


def test_registry_rejects_authority_or_proposal_drift() -> None:
    source = quant_research_campaign_three_hypothesis_registry_v1()

    authority = source.model_dump(mode="python")
    authority["development_outcome_access_authorized"] = True
    with pytest.raises(ValidationError, match="Input should be False"):
        CampaignThreeHypothesisRegistryV1.model_validate(authority)

    proposal = source.model_dump(mode="python")
    proposals = list(deepcopy(proposal["proposals"]))
    proposals.reverse()
    proposal["proposals"] = proposals
    proposal["logical_fingerprint"] = campaign_three_hypothesis_registry_fingerprint(
        proposal
    )
    with pytest.raises(ValidationError, match="hypothesis registry differs"):
        CampaignThreeHypothesisRegistryV1.model_validate(proposal)
