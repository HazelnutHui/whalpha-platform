from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_successor_source_qualification import (
    SourceQualificationDecision,
    SuccessorSourceQualificationReportV1,
    quant_research_successor_source_qualification_v1,
    successor_source_qualification_fingerprint,
)


def test_successor_source_qualification_closes_without_trials_or_outcomes() -> None:
    report = quant_research_successor_source_qualification_v1()

    assert report.status == "closed_source_blocked"
    assert report.qualified_candidate_alpha_count == 0
    assert report.qualified_risk_guard_count == 0
    assert report.blocked_candidate_alpha_count == 3
    assert report.blocked_risk_guard_count == 1
    assert report.formal_trial_count_registered == 0
    assert report.intake_continuation_authorized is False
    assert all(item.outcome_read_count == 0 for item in report.cards)
    assert all(item.formal_trial_count_registered == 0 for item in report.cards)
    assert report.logical_fingerprint == successor_source_qualification_fingerprint(report)


def test_cash_quality_retains_foundation_without_claiming_feature_coverage() -> None:
    report = quant_research_successor_source_qualification_v1()
    cash = next(item for item in report.cards if "cash-earnings" in item.hypothesis_id)

    assert cash.source_foundation_present is True
    assert cash.local_exact_feature_row_count == 0
    assert cash.local_eligible_session_count == 0
    assert cash.decision is SourceQualificationDecision.BLOCKED_FORMULA_IDENTITY_COVERAGE
    assert "latest_restatement_backfill" in cash.forbidden_substitutes


def test_source_qualification_rejects_authority_or_decision_drift() -> None:
    source = quant_research_successor_source_qualification_v1()
    authority = source.model_dump(mode="python")
    authority["development_outcome_access_authorized"] = True
    with pytest.raises(ValidationError, match="Input should be False"):
        SuccessorSourceQualificationReportV1.model_validate(authority)

    decision = source.model_dump(mode="python")
    cards = list(deepcopy(decision["cards"]))
    cards[0]["decision"] = "blocked_formula_identity_coverage"
    decision["cards"] = cards
    decision["logical_fingerprint"] = successor_source_qualification_fingerprint(decision)
    with pytest.raises(ValidationError, match="source qualification report differs"):
        SuccessorSourceQualificationReportV1.model_validate(decision)
