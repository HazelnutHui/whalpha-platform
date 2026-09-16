from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tip_api.contracts.analytics.v1.quant_research_campaign_three_hypotheses import (
    CampaignThreeHypothesisRole,
    quant_research_campaign_three_hypothesis_registry_v1,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_input_qualification import (
    CampaignThreeFactorVariationEvidence,
    CampaignThreeInputDecision,
    CampaignThreeInputQualificationDecisionV1,
    CampaignThreeInputQualificationReportV1,
    CampaignThreeInputQualificationStatus,
    input_qualification_fingerprint,
    quant_research_campaign_three_input_qualification_protocol_v1,
)


def test_campaign_three_input_protocol_is_stable_and_outcome_blind() -> None:
    protocol = quant_research_campaign_three_input_qualification_protocol_v1()

    assert protocol.development_session_count == 106
    assert protocol.first_half_session_count == 53
    assert protocol.second_half_session_count == 53
    assert protocol.minimum_qualified_candidate_alpha_count == 2
    assert protocol.minimum_qualified_risk_guard_count == 1
    assert not protocol.development_outcome_read_authorized
    assert not protocol.full_panel_hindsight_thresholds_authorized
    assert protocol.logical_fingerprint == input_qualification_fingerprint(protocol)


def test_campaign_three_input_decision_rejects_unsupported_state() -> None:
    hypothesis = quant_research_campaign_three_hypothesis_registry_v1().proposals[2]
    reasons = (
        "alpha_half_natural_zero_side_below_floor",
        "alpha_natural_zero_side_below_floor",
        "alpha_state_run_concentration_above_ceiling",
        "alpha_state_side_concentration_above_ceiling",
    )
    decision = _decision(
        hypothesis=hypothesis,
        decision=CampaignThreeInputDecision.REJECTED_INPUT_SUPPORT,
        reasons=reasons,
        positive=15,
        negative=91,
        first_positive=3,
        first_negative=50,
        second_positive=12,
        second_negative=41,
        episodes=15,
        longest=36,
        maximum_side_share="0.8584905660",
    )

    assert decision.reason_codes == reasons
    payload = decision.model_dump(mode="json")
    payload["decision"] = CampaignThreeInputDecision.QUALIFIED_FOR_PROTOCOL_FREEZE
    with pytest.raises(ValueError, match="decision gate differs"):
        CampaignThreeInputQualificationDecisionV1.model_validate(payload)


def test_campaign_three_input_report_accepts_two_alpha_and_one_risk() -> None:
    report = _report()

    assert report.status is CampaignThreeInputQualificationStatus.READY_FOR_PROTOCOL_FREEZE
    assert report.qualified_candidate_alpha_count == 2
    assert report.rejected_candidate_alpha_count == 1
    assert report.qualified_risk_guard_count == 1
    assert report.formal_trial_count_registered == 0
    assert not report.campaign_three_registered
    assert report.logical_fingerprint == input_qualification_fingerprint(report)


def _report() -> CampaignThreeInputQualificationReportV1:
    registry = quant_research_campaign_three_hypothesis_registry_v1()
    accepted = tuple(item for item in registry.proposals if item.prospective_trial_count)
    decisions = (
        _qualified_alpha(accepted[0], positive=68, negative=38),
        _qualified_alpha(accepted[1], positive=60, negative=46),
        _decision(
            hypothesis=accepted[2],
            decision=CampaignThreeInputDecision.REJECTED_INPUT_SUPPORT,
            reasons=(
                "alpha_half_natural_zero_side_below_floor",
                "alpha_natural_zero_side_below_floor",
                "alpha_state_run_concentration_above_ceiling",
                "alpha_state_side_concentration_above_ceiling",
            ),
            positive=15,
            negative=91,
            first_positive=3,
            first_negative=50,
            second_positive=12,
            second_negative=41,
            episodes=15,
            longest=36,
            maximum_side_share="0.8584905660",
        ),
        _decision(
            hypothesis=accepted[3],
            decision=CampaignThreeInputDecision.QUALIFIED_FOR_PROTOCOL_FREEZE,
            reasons=(),
            positive=106,
            negative=0,
            first_positive=53,
            first_negative=0,
            second_positive=53,
            second_negative=0,
            episodes=None,
            longest=None,
            maximum_side_share=None,
        ),
    )
    protocol = quant_research_campaign_three_input_qualification_protocol_v1()
    payload = {
        "protocol_fingerprint": protocol.logical_fingerprint,
        "source_revision": "a" * 40,
        "created_at": datetime(2026, 9, 16, tzinfo=UTC),
        "source_hypothesis_registry_fingerprint": registry.logical_fingerprint,
        "development_session_partition_fingerprint": "b" * 64,
        "decisions": decisions,
        "qualified_candidate_alpha_count": 2,
        "rejected_candidate_alpha_count": 1,
        "qualified_risk_guard_count": 1,
        "rejected_risk_guard_count": 0,
        "status": CampaignThreeInputQualificationStatus.READY_FOR_PROTOCOL_FREEZE,
        "limitation_codes": (
            "development_membership_reconstructed_not_as_operated",
            "input_qualification_does_not_authorize_outcome_access",
        ),
    }
    provisional = CampaignThreeInputQualificationReportV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return CampaignThreeInputQualificationReportV1.model_validate(
        {
            **payload,
            "logical_fingerprint": input_qualification_fingerprint(provisional),
        }
    )


def _qualified_alpha(hypothesis, *, positive: int, negative: int):
    return _decision(
        hypothesis=hypothesis,
        decision=CampaignThreeInputDecision.QUALIFIED_FOR_PROTOCOL_FREEZE,
        reasons=(),
        positive=positive,
        negative=negative,
        first_positive=max(8, positive // 2),
        first_negative=max(8, negative // 2),
        second_positive=positive - max(8, positive // 2),
        second_negative=negative - max(8, negative // 2),
        episodes=20,
        longest=20,
        maximum_side_share=f"{max(positive, negative) / 106:.10f}",
    )


def _decision(
    *,
    hypothesis,
    decision,
    reasons,
    positive,
    negative,
    first_positive,
    first_negative,
    second_positive,
    second_negative,
    episodes,
    longest,
    maximum_side_share,
):
    variation = (
        CampaignThreeFactorVariationEvidence.V1_COMPLETE_SESSION_AND_PAIRWISE_ELIGIBILITY
        if hypothesis.source_factor_catalog == "v1"
        else CampaignThreeFactorVariationEvidence.V2_EXACT_DEVELOPMENT_REPLAY
    )
    return CampaignThreeInputQualificationDecisionV1(
        hypothesis_id=hypothesis.hypothesis_id,
        role=hypothesis.role,
        source_factor_catalog=hypothesis.source_factor_catalog,
        source_factor_id=hypothesis.source_factor_id,
        state_metric_id=hypothesis.state_metric_id,
        factor_variation_evidence=variation,
        factor_eligible_session_count=106,
        factor_first_half_eligible_session_count=53,
        factor_second_half_eligible_session_count=53,
        factor_minimum_available_instruments=1500,
        factor_minimum_distinct_values=2,
        source_same_session_tie_excess_rate="0.0100000000",
        state_available_session_count=106,
        state_first_half_available_session_count=53,
        state_second_half_available_session_count=53,
        state_distinct_value_count=106,
        state_first_half_distinct_value_count=53,
        state_second_half_distinct_value_count=53,
        state_positive_session_count=positive,
        state_negative_session_count=negative,
        state_zero_session_count=106 - positive - negative,
        state_first_half_positive_session_count=first_positive,
        state_first_half_negative_session_count=first_negative,
        state_second_half_positive_session_count=second_positive,
        state_second_half_negative_session_count=second_negative,
        state_same_side_episode_count=episodes,
        state_longest_same_side_run=longest,
        state_maximum_natural_zero_side_share=maximum_side_share,
        decision=decision,
        reason_codes=reasons,
    )
