from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_discovery_trial_ledger_v3 import (
    QuantResearchDiscoveryTrialLedgerV3,
    discovery_trial_ledger_v3_fingerprint,
    quant_research_discovery_trial_ledger_v3,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
WEB_FACTOR_SCREENING_V2_RECORD = (
    REPOSITORY_ROOT
    / "apps"
    / "web"
    / "src"
    / "modelRecords"
    / "quant-research-factor-screening-v2.json"
)


def test_discovery_trial_ledger_v3_closes_v2_and_preserves_all_trials() -> None:
    first = quant_research_discovery_trial_ledger_v3()
    second = quant_research_discovery_trial_ledger_v3()

    assert first == second
    assert first.completed_campaign_count == 2
    assert first.registered_unread_campaign_count == 0
    assert first.cumulative_formal_trial_count == 14
    assert first.cumulative_candidate_alpha_trial_count == 9
    assert first.cumulative_risk_guard_trial_count == 5
    assert first.cumulative_candidate_alpha_admitted_count == 0
    assert first.cumulative_qualified_risk_evidence_count == 3
    assert first.cumulative_model_input_authorized_factor_count == 0
    assert first.campaigns[1].report_status == "closed_no_candidate_alpha"
    assert first.campaigns[1].exact_replay_verified is True
    assert all(
        trial.outcome_accessed is True
        and trial.report_fingerprint == first.campaigns[1].report_fingerprint
        and trial.model_input_authorized is False
        for trial in first.campaigns[1].formal_trials
    )
    assert first.development_screen_execution_authorized is False
    assert first.validation_access_authorized is False
    assert first.holdout_access_authorized is False
    assert first.logical_fingerprint == discovery_trial_ledger_v3_fingerprint(first)


def test_discovery_trial_ledger_v3_rejects_reopened_v2_trial() -> None:
    payload = quant_research_discovery_trial_ledger_v3().model_dump(mode="python")
    campaigns = deepcopy(payload["campaigns"])
    campaigns[1]["formal_trials"][0]["outcome_accessed"] = False
    payload["campaigns"] = campaigns
    payload["logical_fingerprint"] = discovery_trial_ledger_v3_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryTrialLedgerV3.model_validate(payload)


def test_discovery_trial_ledger_v3_rejects_model_permission_without_alpha() -> None:
    payload = quant_research_discovery_trial_ledger_v3().model_dump(mode="python")
    payload["model_construction_authorized"] = True
    payload["logical_fingerprint"] = discovery_trial_ledger_v3_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryTrialLedgerV3.model_validate(payload)


def test_checked_in_web_projection_matches_completed_v2_ledger() -> None:
    ledger = quant_research_discovery_trial_ledger_v3()
    campaign = ledger.campaigns[1]
    projection = json.loads(WEB_FACTOR_SCREENING_V2_RECORD.read_text(encoding="utf-8"))

    assert projection["status"] == campaign.report_status
    assert projection["formal_trial_count"] == campaign.formal_trial_count
    assert projection["cumulative_trial_count"] == ledger.cumulative_formal_trial_count
    assert projection["selected_alpha_count"] == campaign.candidate_alpha_admitted_count
    assert projection["qualified_risk_evidence_count"] == (
        campaign.qualified_risk_evidence_count
    )
    assert projection["selected_model_input_count"] == (
        campaign.selected_model_input_count
    )
    assert projection["completed_ledger_fingerprint"] == ledger.logical_fingerprint
    assert projection["report_logical_fingerprint"] == campaign.report_fingerprint
    assert projection["report_sha256"] == campaign.report_sha256
    assert projection["exact_replay_verified"] is campaign.exact_replay_verified
    assert projection["model_construction_authorized"] is False
    assert projection["validation_authorized"] is False
    assert projection["holdout_access_authorized"] is False
    assert projection["candidate_activation_authorized"] is False
