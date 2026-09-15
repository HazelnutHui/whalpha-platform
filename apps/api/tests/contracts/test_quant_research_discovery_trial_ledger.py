from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_discovery_trial_ledger import (
    QuantResearchDiscoveryTrialDisposition,
    QuantResearchDiscoveryTrialLedgerV1,
    discovery_trial_ledger_fingerprint,
    quant_research_discovery_trial_ledger_v1,
)


def test_discovery_trial_ledger_reconciles_consumed_v1_trials() -> None:
    first = quant_research_discovery_trial_ledger_v1()
    second = quant_research_discovery_trial_ledger_v1()

    assert first == second
    assert first.completed_campaign_count == 1
    assert first.cumulative_formal_trial_count == 8
    assert first.cumulative_candidate_alpha_trial_count == 5
    assert first.cumulative_risk_guard_trial_count == 3
    assert first.cumulative_candidate_alpha_admitted_count == 0
    assert first.cumulative_retained_risk_evidence_count == 1
    assert sum(
        trial.disposition
        is QuantResearchDiscoveryTrialDisposition.RETAINED_RISK_EVIDENCE
        for trial in first.campaigns[0].formal_trials
    ) == 1
    assert first.validation_access_authorized is False
    assert first.holdout_access_authorized is False
    assert first.logical_fingerprint == discovery_trial_ledger_fingerprint(first)


def test_discovery_trial_ledger_rejects_removed_failure_even_with_new_hash() -> None:
    payload = quant_research_discovery_trial_ledger_v1().model_dump(mode="python")
    campaign = deepcopy(payload["campaigns"][0])
    campaign["formal_trials"] = campaign["formal_trials"][:-1]
    campaign["formal_trial_count"] = 7
    payload["campaigns"] = [campaign]
    payload["cumulative_formal_trial_count"] = 7
    payload["logical_fingerprint"] = discovery_trial_ledger_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryTrialLedgerV1.model_validate(payload)


def test_discovery_trial_ledger_rejects_relabeling_failure_as_retained() -> None:
    payload = quant_research_discovery_trial_ledger_v1().model_dump(mode="python")
    campaigns = deepcopy(payload["campaigns"])
    campaigns[0]["formal_trials"][0]["disposition"] = "retained_risk_evidence"
    payload["campaigns"] = campaigns
    payload["logical_fingerprint"] = discovery_trial_ledger_fingerprint(payload)

    with pytest.raises(ValidationError, match="campaign ledger differs"):
        QuantResearchDiscoveryTrialLedgerV1.model_validate(payload)
