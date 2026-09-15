from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_factor_catalog import (
    QuantResearchFactorRole,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening import (
    QuantResearchFactorScreeningProtocolV1,
    factor_screening_fingerprint,
    quant_research_factor_screening_protocol_v1,
)


def test_screening_protocol_is_finite_deterministic_and_development_only() -> None:
    first = quant_research_factor_screening_protocol_v1()
    second = quant_research_factor_screening_protocol_v1()

    assert first == second
    assert first.formal_trial_count == 8
    assert len(first.formal_hypotheses) == 8
    assert sum(
        item.role is QuantResearchFactorRole.CANDIDATE_ALPHA
        for item in first.formal_hypotheses
    ) == 5
    assert sum(
        item.role is QuantResearchFactorRole.RISK_GUARD
        for item in first.formal_hypotheses
    ) == 3
    assert first.setup_conditioner_trial_count == 0
    assert first.primary_horizon_sessions == 3
    assert first.development_outcome_read_authorized is True
    assert first.validation_authorized is False
    assert first.holdout_access_authorized is False
    assert first.model_construction_authorized is False
    assert first.logical_fingerprint == factor_screening_fingerprint(first)


def test_screening_protocol_rejects_post_registration_threshold_drift() -> None:
    payload = quant_research_factor_screening_protocol_v1().model_dump(mode="json")
    payload["minimum_primary_mean_rank_ic"] = "0.0100000000"
    payload["logical_fingerprint"] = factor_screening_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchFactorScreeningProtocolV1.model_validate(payload)


def test_screening_protocol_rejects_role_or_trial_registry_drift() -> None:
    payload = quant_research_factor_screening_protocol_v1().model_dump(mode="json")
    hypotheses = deepcopy(payload["formal_hypotheses"])
    hypotheses[0]["related_factor_group"] = "post_hoc_group"
    payload["formal_hypotheses"] = hypotheses
    payload["logical_fingerprint"] = factor_screening_fingerprint(payload)

    with pytest.raises(ValidationError, match="Factor Catalog V1"):
        QuantResearchFactorScreeningProtocolV1.model_validate(payload)
