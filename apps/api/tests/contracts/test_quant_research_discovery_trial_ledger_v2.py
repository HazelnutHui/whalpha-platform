from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_discovery_trial_ledger_v2 import (
    QuantResearchDiscoveryTrialLedgerV2,
    discovery_trial_ledger_v2_fingerprint,
    quant_research_discovery_trial_ledger_v2,
)


def test_discovery_trial_ledger_v2_carries_v1_and_registers_six_unread_trials() -> None:
    first = quant_research_discovery_trial_ledger_v2()
    second = quant_research_discovery_trial_ledger_v2()

    assert first == second
    assert first.completed_campaign_count == 1
    assert first.registered_unread_campaign_count == 1
    assert first.cumulative_formal_trial_count == 14
    assert first.cumulative_candidate_alpha_trial_count == 9
    assert first.cumulative_risk_guard_trial_count == 5
    assert first.cumulative_candidate_alpha_admitted_count == 0
    assert first.cumulative_retained_risk_evidence_count == 1
    assert all(
        trial.outcome_accessed is False
        and trial.report_fingerprint is None
        and trial.model_input_authorized is False
        for trial in first.campaigns[1].formal_trials
    )
    assert first.validation_access_authorized is False
    assert first.holdout_access_authorized is False
    assert first.logical_fingerprint == discovery_trial_ledger_v2_fingerprint(first)


def test_discovery_trial_ledger_v2_rejects_removed_v1_campaign() -> None:
    payload = quant_research_discovery_trial_ledger_v2().model_dump(mode="python")
    payload["campaigns"] = (payload["campaigns"][1], payload["campaigns"][1])
    payload["logical_fingerprint"] = discovery_trial_ledger_v2_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryTrialLedgerV2.model_validate(payload)


def test_discovery_trial_ledger_v2_rejects_premature_outcome_claim() -> None:
    payload = quant_research_discovery_trial_ledger_v2().model_dump(mode="python")
    campaigns = deepcopy(payload["campaigns"])
    campaigns[1]["formal_trials"][0]["outcome_accessed"] = True
    payload["campaigns"] = campaigns
    payload["logical_fingerprint"] = discovery_trial_ledger_v2_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryTrialLedgerV2.model_validate(payload)


def test_discovery_trial_ledger_v2_rejects_removed_pending_trial() -> None:
    payload = quant_research_discovery_trial_ledger_v2().model_dump(mode="python")
    campaigns = deepcopy(payload["campaigns"])
    campaigns[1]["formal_trials"] = campaigns[1]["formal_trials"][:-1]
    campaigns[1]["formal_trial_count"] = 5
    payload["campaigns"] = campaigns
    payload["cumulative_formal_trial_count"] = 13
    payload["logical_fingerprint"] = discovery_trial_ledger_v2_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryTrialLedgerV2.model_validate(payload)
