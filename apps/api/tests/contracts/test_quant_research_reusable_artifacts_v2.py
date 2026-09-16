from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_reusable_artifacts import (
    QuantResearchArtifactKind,
)
from tip_api.contracts.analytics.v1.quant_research_reusable_artifacts_v2 import (
    MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT,
    QuantResearchReusableArtifactRegistryV2,
    quant_research_reusable_artifact_registry_v2,
    reusable_artifact_registry_v2_fingerprint,
)


def test_registry_v2_registers_only_the_qualified_market_state_artifact() -> None:
    first = quant_research_reusable_artifact_registry_v2()
    second = quant_research_reusable_artifact_registry_v2()

    assert first == second
    assert first.implementation_status == "market_state_registered_outcomes_closed"
    assert first.materialized_artifact_count == 1
    assert first.materialized_market_state_artifact_count == 1
    assert first.materialized_artifacts[0].identity.artifact_kind is (
        QuantResearchArtifactKind.MARKET_STATE
    )
    assert first.materialized_artifacts[0].record_count == 287
    assert first.source_market_state_qualification_report_fingerprint == (
        MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
    )
    assert first.next_campaign_registered is False
    assert first.new_outcome_access_authorized is False
    assert first.validation_access_authorized is False
    assert first.holdout_access_authorized is False
    assert first.logical_fingerprint == reusable_artifact_registry_v2_fingerprint(
        first
    )


def test_registry_v2_rejects_market_state_content_drift() -> None:
    payload = quant_research_reusable_artifact_registry_v2().model_dump(
        mode="python"
    )
    artifacts = deepcopy(payload["materialized_artifacts"])
    artifacts[0]["content_sha256"] = "0" * 64
    payload["materialized_artifacts"] = artifacts
    payload["logical_fingerprint"] = reusable_artifact_registry_v2_fingerprint(
        payload
    )

    with pytest.raises(ValidationError, match="registered reusable-artifact"):
        QuantResearchReusableArtifactRegistryV2.model_validate(payload)


def test_registry_v2_rejects_outcome_authority() -> None:
    payload = quant_research_reusable_artifact_registry_v2().model_dump(
        mode="python"
    )
    payload["new_outcome_access_authorized"] = True

    with pytest.raises(ValidationError, match="Input should be False"):
        QuantResearchReusableArtifactRegistryV2.model_validate(payload)
