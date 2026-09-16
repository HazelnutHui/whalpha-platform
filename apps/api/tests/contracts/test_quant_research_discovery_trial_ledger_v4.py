from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_discovery_trial_ledger_v4 import (
    QuantResearchDiscoveryTrialLedgerV4,
    discovery_trial_ledger_v4_fingerprint,
    quant_research_discovery_trial_ledger_v4,
)


def test_discovery_trial_ledger_v4_registers_three_unread_trials() -> None:
    first = quant_research_discovery_trial_ledger_v4()
    second = quant_research_discovery_trial_ledger_v4()

    assert first == second
    assert first.completed_campaign_count == 2
    assert first.registered_unread_campaign_count == 1
    assert first.cumulative_formal_trial_count == 17
    assert first.cumulative_candidate_alpha_trial_count == 11
    assert first.cumulative_risk_guard_trial_count == 6
    assert first.cumulative_candidate_alpha_admitted_count == 0
    assert first.cumulative_qualified_risk_evidence_count == 3
    assert first.cumulative_model_input_authorized_factor_count == 0
    assert first.campaigns[2].status == "registered_pending_development_authorization"
    assert first.campaigns[2].formal_trial_count == 3
    assert first.campaigns[2].rejected_before_outcomes_count == 2
    assert all(
        trial.outcome_accessed is False
        and trial.outcome_access_date is None
        and trial.report_fingerprint is None
        and trial.model_input_authorized is False
        for trial in first.campaigns[2].formal_trials
    )
    assert first.development_screen_execution_authorized is False
    assert first.development_access_requires_separate_typed_grant is True
    assert first.validation_access_authorized is False
    assert first.holdout_access_authorized is False
    assert first.logical_fingerprint == discovery_trial_ledger_v4_fingerprint(first)


def test_discovery_trial_ledger_v4_rejects_silent_outcome_access() -> None:
    payload = quant_research_discovery_trial_ledger_v4().model_dump(mode="python")
    campaigns = deepcopy(payload["campaigns"])
    campaigns[2]["formal_trials"][0]["outcome_accessed"] = True
    payload["campaigns"] = campaigns
    payload["logical_fingerprint"] = discovery_trial_ledger_v4_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryTrialLedgerV4.model_validate(payload)


def test_discovery_trial_ledger_v4_rejects_execution_permission() -> None:
    payload = quant_research_discovery_trial_ledger_v4().model_dump(mode="python")
    payload["development_screen_execution_authorized"] = True
    payload["logical_fingerprint"] = discovery_trial_ledger_v4_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchDiscoveryTrialLedgerV4.model_validate(payload)
