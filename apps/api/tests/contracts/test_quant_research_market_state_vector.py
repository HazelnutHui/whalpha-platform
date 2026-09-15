from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_market_state_vector import (
    QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER,
    QuantResearchMarketStateVectorDefinitionV1,
    market_state_vector_definition_fingerprint,
    quant_research_market_state_vector_definition_v1,
)


def test_market_state_vector_keeps_evidence_tiers_and_outcomes_separate() -> None:
    value = quant_research_market_state_vector_definition_v1()

    assert tuple(item.metric_id for item in value.definitions) == (
        QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER
    )
    assert [item.evidence_tier.value for item in value.definitions[:6]] == [
        "benchmark_exact"
    ] * 6
    assert [item.evidence_tier.value for item in value.definitions[6:]] == [
        "reconstructed_research_only"
    ] * 4
    assert value.emits_continuous_metrics_only is True
    assert value.state_thresholds_selected is False
    assert value.interactions_registered is False
    assert value.campaign_three_registered is False
    assert value.development_outcome_read_authorized is False


def test_market_state_vector_rejects_metric_or_authority_tamper() -> None:
    payload = quant_research_market_state_vector_definition_v1().model_dump(
        mode="python"
    )
    changed = deepcopy(payload)
    changed["definitions"][0]["exact_formula"] = "tampered"
    changed["logical_fingerprint"] = market_state_vector_definition_fingerprint(
        changed
    )
    with pytest.raises(ValidationError):
        QuantResearchMarketStateVectorDefinitionV1.model_validate(changed)

    changed = deepcopy(payload)
    changed["development_outcome_read_authorized"] = True
    with pytest.raises(ValidationError):
        QuantResearchMarketStateVectorDefinitionV1.model_validate(changed)
