from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_market_state_vector import (
    QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER,
    QuantResearchMarketStateAvailability,
    QuantResearchMarketStateMetricValueV1,
    QuantResearchMarketStateVectorDefinitionV1,
    market_state_metric_definition_fingerprint,
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


def test_market_state_metric_rejects_false_coverage_or_share_range() -> None:
    metric_id = "reconstructed_member_positive_log_return_5s_share"
    common = {
        "metric_id": metric_id,
        "definition_fingerprint": market_state_metric_definition_fingerprint(
            metric_id
        ),
        "availability": QuantResearchMarketStateAvailability.AVAILABLE,
        "actual_observations": 500,
        "expected_observations": 600,
        "coverage_ratio": "0.8333333333",
    }
    with pytest.raises(ValidationError):
        QuantResearchMarketStateMetricValueV1(
            **common,
            value="1.1000000000",
        )
    with pytest.raises(ValidationError):
        QuantResearchMarketStateMetricValueV1(
            **{**common, "coverage_ratio": "1.0000000000"},
            value="0.5000000000",
        )
