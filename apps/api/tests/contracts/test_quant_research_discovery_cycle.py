from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_discovery_cycle import (
    QuantResearchDiscoveryCycleV1,
    QuantResearchDiscoveryStageId,
    discovery_cycle_fingerprint,
    quant_research_discovery_cycle_v1,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
WEB_CYCLE_RECORD = (
    REPOSITORY_ROOT
    / "apps"
    / "web"
    / "src"
    / "modelRecords"
    / "quant-research-discovery-cycle-v1.json"
)


def test_discovery_cycle_is_renewable_but_each_campaign_is_bounded() -> None:
    cycle = quant_research_discovery_cycle_v1()

    assert cycle.operating_mode == "continuous_sequence_of_finite_campaigns"
    assert cycle.current_stage is QuantResearchDiscoveryStageId.HYPOTHESIS_INTAKE
    assert cycle.completed_campaign_count == 2
    assert cycle.cumulative_formal_trial_count == 14
    assert cycle.active_campaign_id is None
    assert cycle.next_campaign_registered is False
    assert cycle.program_campaign_limit is None
    assert cycle.next_design_after_close_authorized is True
    assert cycle.outcome_access_requires_new_registered_campaign is True
    assert cycle.failed_campaign_reopen_authorized is False
    assert [item.outcome_access_allowed for item in cycle.stages] == [
        False,
        False,
        False,
        False,
        False,
        True,
        True,
        False,
    ]
    assert cycle.logical_fingerprint == discovery_cycle_fingerprint(cycle)


def test_discovery_cycle_rejects_outcome_access_during_idea_intake() -> None:
    payload = quant_research_discovery_cycle_v1().model_dump(mode="python")
    stages = deepcopy(payload["stages"])
    stages[0]["outcome_access_allowed"] = True
    payload["stages"] = stages
    payload["logical_fingerprint"] = discovery_cycle_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryCycleV1.model_validate(payload)


def test_discovery_cycle_rejects_duplicate_identity_dimension_removal() -> None:
    payload = quant_research_discovery_cycle_v1().model_dump(mode="python")
    payload["dedup_identity_fields"] = payload["dedup_identity_fields"][:-1]
    payload["logical_fingerprint"] = discovery_cycle_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryCycleV1.model_validate(payload)


def test_checked_in_web_cycle_projection_matches_contract() -> None:
    cycle = quant_research_discovery_cycle_v1()
    projection = json.loads(WEB_CYCLE_RECORD.read_text(encoding="utf-8"))

    assert projection == cycle.model_dump(mode="json")

