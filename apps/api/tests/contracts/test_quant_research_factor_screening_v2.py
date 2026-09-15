from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QuantResearchFactorRoleV2,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_v2 import (
    QuantResearchFactorScreeningProtocolV2,
    factor_screening_v2_fingerprint,
    quant_research_factor_screening_protocol_v2,
)


def test_screening_v2_is_finite_registered_and_development_only() -> None:
    first = quant_research_factor_screening_protocol_v2()
    second = quant_research_factor_screening_protocol_v2()

    assert first == second
    assert first.formal_trial_count == 6
    assert first.prior_consumed_trial_count == 8
    assert first.cumulative_trial_count_after_registration == 14
    assert sum(
        item.role is QuantResearchFactorRoleV2.CANDIDATE_ALPHA
        for item in first.formal_hypotheses
    ) == 4
    assert sum(
        item.role is QuantResearchFactorRoleV2.RISK_GUARD
        for item in first.formal_hypotheses
    ) == 2
    assert first.setup_conditioner_trial_count == 0
    assert first.applicability_input_trial_count == 0
    assert first.primary_horizon_sessions == 3
    assert first.development_outcome_read_authorized is True
    assert first.validation_authorized is False
    assert first.holdout_access_authorized is False
    assert first.model_construction_authorized is False
    assert first.logical_fingerprint == factor_screening_v2_fingerprint(first)


def test_screening_v2_rejects_threshold_drift_after_registration() -> None:
    payload = quant_research_factor_screening_protocol_v2().model_dump(mode="json")
    payload["minimum_primary_mean_rank_ic"] = "0.0100000000"
    payload["logical_fingerprint"] = factor_screening_v2_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchFactorScreeningProtocolV2.model_validate(payload)


def test_screening_v2_rejects_trial_or_role_drift() -> None:
    payload = quant_research_factor_screening_protocol_v2().model_dump(mode="json")
    hypotheses = deepcopy(payload["formal_hypotheses"])
    hypotheses[0]["related_factor_group"] = "post_hoc_group"
    payload["formal_hypotheses"] = hypotheses
    payload["logical_fingerprint"] = factor_screening_v2_fingerprint(payload)

    with pytest.raises(ValidationError, match="Factor Catalog V2"):
        QuantResearchFactorScreeningProtocolV2.model_validate(payload)


def test_screening_v2_rejects_incremental_baseline_drift() -> None:
    payload = quant_research_factor_screening_protocol_v2().model_dump(mode="python")
    payload["incremental_baseline_definition_fingerprint"] = "0" * 64
    payload["logical_fingerprint"] = factor_screening_v2_fingerprint(payload)

    with pytest.raises(ValidationError, match="screening protocol differs"):
        QuantResearchFactorScreeningProtocolV2.model_validate(payload)
