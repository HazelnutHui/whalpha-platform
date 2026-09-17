from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_successor_hypotheses import (
    SuccessorHypothesisCardV1,
    SuccessorHypothesisRegistryV1,
    SuccessorHypothesisRole,
    quant_research_successor_hypothesis_registry_v1,
    successor_duplicate_signature,
    successor_registry_fingerprint,
)


def test_successor_intake_is_finite_distinct_and_outcome_blind() -> None:
    registry = quant_research_successor_hypothesis_registry_v1()

    assert registry.card_count == 4
    assert registry.candidate_alpha_card_count == 3
    assert registry.risk_guard_card_count == 1
    assert registry.consumed_formal_trial_count == 17
    assert registry.formal_trial_count_registered == 0
    assert len({item.duplicate_signature for item in registry.cards}) == 4
    assert all(item.prospective_outcome_trial_count == 0 for item in registry.cards)
    assert all(item.contains_forward_outcomes is False for item in registry.cards)
    assert registry.development_outcome_access_authorized is False
    assert registry.validation_access_authorized is False
    assert registry.holdout_access_authorized is False
    assert registry.logical_fingerprint == successor_registry_fingerprint(registry)


def test_successor_intake_has_three_alpha_cards_and_one_event_guard() -> None:
    registry = quant_research_successor_hypothesis_registry_v1()

    assert sum(item.role is SuccessorHypothesisRole.CANDIDATE_ALPHA for item in registry.cards) == 3
    assert sum(item.role is SuccessorHypothesisRole.RISK_GUARD for item in registry.cards) == 1
    event_guard = next(item for item in registry.cards if item.role is SuccessorHypothesisRole.RISK_GUARD)
    assert event_guard.orientation == "true_is_risk_exclusion"
    assert "return forecast" in event_guard.prior_trial_comparison


def test_display_id_does_not_change_successor_duplicate_identity() -> None:
    card = quant_research_successor_hypothesis_registry_v1().cards[0]
    payload = card.model_dump(mode="json")
    payload["hypothesis_id"] = "whalpha.hypothesis.successor-one.renamed"

    assert successor_duplicate_signature(payload) == card.duplicate_signature


def test_successor_card_rejects_formula_drift() -> None:
    card = quant_research_successor_hypothesis_registry_v1().cards[0]
    payload = card.model_dump(mode="python")
    payload["exact_formula"] = "price_momentum_21_sessions"
    payload["duplicate_signature"] = successor_duplicate_signature(payload)
    payload["logical_fingerprint"] = "0" * 64

    with pytest.raises(ValidationError, match="successor hypothesis card differs"):
        SuccessorHypothesisCardV1.model_validate(payload)


def test_successor_registry_rejects_authority_and_order_drift() -> None:
    source = quant_research_successor_hypothesis_registry_v1()
    authority = source.model_dump(mode="python")
    authority["development_outcome_access_authorized"] = True
    with pytest.raises(ValidationError, match="Input should be False"):
        SuccessorHypothesisRegistryV1.model_validate(authority)

    order = source.model_dump(mode="python")
    cards = list(deepcopy(order["cards"]))
    cards.reverse()
    order["cards"] = cards
    order["logical_fingerprint"] = successor_registry_fingerprint(order)
    with pytest.raises(ValidationError, match="successor hypothesis registry differs"):
        SuccessorHypothesisRegistryV1.model_validate(order)
