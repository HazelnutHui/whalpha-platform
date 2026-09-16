from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_discovery_trial_ledger_v5 import (
    QuantResearchDiscoveryTrialLedgerV5,
    discovery_trial_ledger_v5_fingerprint,
    quant_research_discovery_trial_ledger_v5,
)


def test_discovery_trial_ledger_v5_closes_campaign_three() -> None:
    first = quant_research_discovery_trial_ledger_v5()
    second = quant_research_discovery_trial_ledger_v5()

    assert first == second
    assert first.completed_campaign_count == 3
    assert first.registered_unread_campaign_count == 0
    assert first.cumulative_formal_trial_count == 17
    assert first.cumulative_candidate_alpha_trial_count == 11
    assert first.cumulative_risk_guard_trial_count == 6
    assert first.cumulative_candidate_alpha_admitted_count == 0
    assert first.cumulative_qualified_risk_evidence_count == 3
    assert first.cumulative_model_input_authorized_factor_count == 0
    campaign = first.campaigns[2]
    assert campaign.status == "closed_no_candidate_alpha"
    assert campaign.formal_trial_count == 3
    assert campaign.rejected_candidate_alpha_trial_count == 2
    assert campaign.rejected_risk_guard_trial_count == 1
    assert campaign.exact_replay_verified is True
    assert all(
        trial.outcome_accessed is True
        and trial.disposition == "rejected_screen"
        and trial.validation_accessed is False
        and trial.holdout_accessed is False
        and trial.model_input_authorized is False
        for trial in campaign.formal_trials
    )
    assert first.development_screen_execution_authorized is False
    assert first.validation_access_authorized is False
    assert first.holdout_access_authorized is False
    assert first.logical_fingerprint == discovery_trial_ledger_v5_fingerprint(first)


def test_discovery_trial_ledger_v5_rejects_erased_outcome_access() -> None:
    payload = quant_research_discovery_trial_ledger_v5().model_dump(mode="python")
    campaigns = deepcopy(payload["campaigns"])
    campaigns[2]["formal_trials"][0]["outcome_accessed"] = False
    payload["campaigns"] = campaigns
    payload["logical_fingerprint"] = discovery_trial_ledger_v5_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryTrialLedgerV5.model_validate(payload)


def test_discovery_trial_ledger_v5_rejects_changed_report_identity() -> None:
    payload = quant_research_discovery_trial_ledger_v5().model_dump(mode="python")
    campaigns = deepcopy(payload["campaigns"])
    campaigns[2]["report_sha256"] = "0" * 64
    payload["campaigns"] = campaigns
    payload["logical_fingerprint"] = discovery_trial_ledger_v5_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryTrialLedgerV5.model_validate(payload)


def test_discovery_trial_ledger_v5_rejects_new_execution_permission() -> None:
    payload = quant_research_discovery_trial_ledger_v5().model_dump(mode="python")
    payload["development_screen_execution_authorized"] = True
    payload["logical_fingerprint"] = discovery_trial_ledger_v5_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryTrialLedgerV5.model_validate(payload)
