from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from tip_api.contracts.analytics.v1.quant_research_campaign_three_hypotheses import (
    CampaignThreeHypothesisRole,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_screening import (
    quant_research_campaign_three_screening_protocol_v1,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_screening_result import (
    CampaignThreeInteractionSummaryV1,
    CampaignThreeSessionEvidenceV1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_result import (
    QuantResearchFactorScreeningDecisionStatus,
    QuantResearchFactorScreeningEndpoint,
)
from tip_api.services import quant_research_campaign_three_screening as service


def test_interaction_regression_recovers_intercept_and_slope() -> None:
    alpha, beta = service.calculate_interaction_regression(
        (-2.0, -1.0, 0.0, 1.0, 2.0),
        (0.0, 0.5, 1.0, 1.5, 2.0),
    )

    assert alpha == pytest.approx(1.0)
    assert beta == pytest.approx(0.5)


def test_circular_block_bootstrap_is_deterministic_and_uses_tenth_percentile() -> None:
    states = tuple((index - 30) / 30 for index in range(60))
    rank_ics = tuple(
        0.01 + 0.04 * value + ((index % 5) - 2) / 1000
        for index, value in enumerate(states)
    )

    first = service.calculate_circular_block_interaction_bootstrap(
        state_values=states,
        rank_ics=rank_ics,
        block_sessions=10,
        replicates=500,
        seed_material="campaign-three-test",
    )
    second = service.calculate_circular_block_interaction_bootstrap(
        state_values=states,
        rank_ics=rank_ics,
        block_sessions=10,
        replicates=500,
        seed_material="campaign-three-test",
    )

    assert first == second
    assert first[0] > 0
    assert 0 < first[1] <= 1


def test_summary_uses_original_calendar_halves_not_surviving_row_midpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = quant_research_campaign_three_screening_protocol_v1()
    hypothesis = protocol.formal_hypotheses[0]
    sessions = tuple(date(2025, 1, 1) + timedelta(days=index) for index in range(106))
    retained = (*sessions[:40], *sessions[53:93])
    evidence = tuple(
        CampaignThreeSessionEvidenceV1(
            hypothesis_id=hypothesis.hypothesis_id,
            role=hypothesis.role,
            horizon_sessions=3,
            endpoint=QuantResearchFactorScreeningEndpoint.LOWER,
            signal_session=session,
            instrument_count=100,
            state_value=f"{(index - 40) / 100:.10f}",
            session_rank_ic=f"{0.01 + index / 1000:.10f}",
        )
        for index, session in enumerate(retained)
    )
    monkeypatch.setattr(
        service,
        "calculate_circular_block_interaction_bootstrap",
        lambda **_: (0.001, 0.001),
    )

    result = service._summarize(
        hypothesis=hypothesis,
        horizon=3,
        endpoint=QuantResearchFactorScreeningEndpoint.LOWER,
        evidence=evidence,
        first_half=frozenset(sessions[:53]),
        second_half=frozenset(sessions[53:]),
    )

    assert result.eligible_session_count == 80
    assert result.first_half_session_count == 40
    assert result.second_half_session_count == 40
    assert "first_half_session_floor_not_met" not in result.reason_codes
    assert "second_half_session_floor_not_met" not in result.reason_codes


def test_unavailable_regression_is_explicit_even_with_many_sessions() -> None:
    protocol = quant_research_campaign_three_screening_protocol_v1()
    hypothesis = protocol.formal_hypotheses[0]

    summary = CampaignThreeInteractionSummaryV1(
        hypothesis_id=hypothesis.hypothesis_id,
        role=hypothesis.role,
        horizon_sessions=3,
        endpoint=QuantResearchFactorScreeningEndpoint.LOWER,
        eligible_session_count=80,
        first_half_session_count=40,
        second_half_session_count=40,
        evidence_collection_fingerprint="1" * 64,
        favorable_state_session_count=40,
        reason_codes=("regression_unavailable",),
    )

    assert summary.interaction_beta is None


def test_decisions_keep_every_registered_trial_in_holm_and_select_risk_only_with_alpha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = quant_research_campaign_three_screening_protocol_v1()
    summaries = []
    for hypothesis_index, hypothesis in enumerate(protocol.formal_hypotheses):
        endpoints = (
            (
                QuantResearchFactorScreeningEndpoint.LOWER,
                QuantResearchFactorScreeningEndpoint.UPPER,
            )
            if hypothesis.role
            is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
            else (QuantResearchFactorScreeningEndpoint.COMPLETE_PATH,)
        )
        for endpoint in endpoints:
            unavailable = hypothesis_index == 1
            summaries.append(
                SimpleNamespace(
                    hypothesis_id=hypothesis.hypothesis_id,
                    horizon_sessions=3,
                    endpoint=endpoint,
                    reason_codes=("regression_unavailable",) if unavailable else (),
                    interaction_beta=None if unavailable else "0.0500000000",
                    primary_block_lower_90pct=None if unavailable else "0.0100000000",
                    primary_block_one_sided_p_value=None if unavailable else "0.0010000000",
                    sensitivity_block_lower_90pct=None if unavailable else "0.0080000000",
                    sensitivity_block_one_sided_p_value=None if unavailable else "0.0020000000",
                    first_half_beta=None if unavailable else "0.0400000000",
                    second_half_beta=None if unavailable else "0.0300000000",
                    favorable_state_session_count=(
                        30
                        if hypothesis.role
                        is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
                        else None
                    ),
                    favorable_state_mean_rank_ic=(
                        None
                        if unavailable
                        or hypothesis.role
                        is CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION
                        else "0.0100000000"
                    ),
                )
            )
    captured = []
    original = service.calculate_holm_adjustment

    def capture(values):
        captured.append(dict(values))
        return original(values)

    monkeypatch.setattr(service, "calculate_holm_adjustment", capture)

    decisions, selected_alpha, selected_risk = service._decisions(tuple(summaries))

    assert sorted(len(item) for item in captured) == [1, 2]
    assert any(value == 1.0 for family in captured for value in family.values())
    assert selected_alpha == (protocol.formal_hypotheses[0].hypothesis_id,)
    assert selected_risk == (protocol.formal_hypotheses[2].hypothesis_id,)
    assert decisions[1].status is QuantResearchFactorScreeningDecisionStatus.INCONCLUSIVE_DATA


def test_risk_guard_cannot_be_selected_without_surviving_alpha() -> None:
    protocol = quant_research_campaign_three_screening_protocol_v1()
    summaries = []
    for hypothesis in protocol.formal_hypotheses:
        endpoints = (
            (
                QuantResearchFactorScreeningEndpoint.LOWER,
                QuantResearchFactorScreeningEndpoint.UPPER,
            )
            if hypothesis.role
            is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
            else (QuantResearchFactorScreeningEndpoint.COMPLETE_PATH,)
        )
        for endpoint in endpoints:
            alpha = hypothesis.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
            summaries.append(
                SimpleNamespace(
                    hypothesis_id=hypothesis.hypothesis_id,
                    horizon_sessions=3,
                    endpoint=endpoint,
                    reason_codes=(),
                    interaction_beta="-0.0100000000" if alpha else "0.0500000000",
                    primary_block_lower_90pct="-0.0200000000" if alpha else "0.0100000000",
                    primary_block_one_sided_p_value="0.5000000000" if alpha else "0.0010000000",
                    sensitivity_block_lower_90pct="-0.0200000000" if alpha else "0.0080000000",
                    sensitivity_block_one_sided_p_value=(
                        "0.5000000000" if alpha else "0.0020000000"
                    ),
                    first_half_beta="-0.0100000000" if alpha else "0.0400000000",
                    second_half_beta="-0.0100000000" if alpha else "0.0300000000",
                    favorable_state_session_count=30 if alpha else None,
                    favorable_state_mean_rank_ic="-0.0100000000" if alpha else None,
                )
            )

    decisions, selected_alpha, selected_risk = service._decisions(tuple(summaries))

    assert selected_alpha == ()
    assert selected_risk == ()
    risk = decisions[2]
    assert risk.passed_all_frozen_gates is True
    assert risk.status is QuantResearchFactorScreeningDecisionStatus.QUALIFIED_NOT_SELECTED_CAP
