from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_discovery_cycle_state_v2 import (
    QuantResearchDiscoveryCycleStateV2,
    discovery_cycle_state_v2_fingerprint,
    quant_research_discovery_cycle_state_v2,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
WEB_CYCLE_STATE_RECORD = (
    REPOSITORY_ROOT
    / "apps"
    / "web"
    / "src"
    / "modelRecords"
    / "quant-research-discovery-cycle-state-v2.json"
)


def test_discovery_cycle_state_v2_returns_to_outcome_blind_intake() -> None:
    state = quant_research_discovery_cycle_state_v2()

    assert state.current_status == "ready_for_next_campaign_design"
    assert state.current_stage == "hypothesis_intake"
    assert state.completed_campaign_count == 3
    assert state.cumulative_formal_trial_count == 17
    assert state.active_campaign_id is None
    assert state.next_campaign_registered is False
    assert state.admitted_alpha_count == 0
    assert state.active_model_count == 0
    assert state.active_strategy_count == 0
    assert state.logical_fingerprint == discovery_cycle_state_v2_fingerprint(state)


def test_discovery_cycle_state_v2_rejects_unregistered_active_campaign() -> None:
    payload = quant_research_discovery_cycle_state_v2().model_dump(mode="python")
    payload["next_campaign_registered"] = True
    payload["logical_fingerprint"] = discovery_cycle_state_v2_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryCycleStateV2.model_validate(payload)


def test_checked_in_web_cycle_state_projection_matches_contract() -> None:
    state = quant_research_discovery_cycle_state_v2()
    projection = json.loads(WEB_CYCLE_STATE_RECORD.read_text(encoding="utf-8"))

    assert projection == state.model_dump(mode="json")
