from __future__ import annotations

import stat
from datetime import date, datetime, timezone

import pytest

from tip_api.contracts.analytics.v1.quant_research_campaign_three_hypotheses import (
    CampaignThreeHypothesisRole,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_screening import (
    quant_research_campaign_three_screening_protocol_v1,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_screening_result import (
    CampaignThreeInteractionSummaryV1,
    CampaignThreeScreeningDecisionV1,
    CampaignThreeSessionEvidenceV1,
    _collection_fingerprint,
    build_campaign_three_screening_report_v1,
)
from tip_api.contracts.analytics.v1.quant_research_discovery_trial_ledger_v4 import (
    quant_research_discovery_trial_ledger_v4,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_result import (
    QuantResearchFactorScreeningDecisionStatus,
    QuantResearchFactorScreeningEndpoint,
    QuantResearchFactorScreeningLabelState,
    QuantResearchFactorScreeningReportStatus,
)
from tip_api.persistence.quant_research_campaign_three_screening import (
    CampaignThreeScreeningPersistenceError,
    read_campaign_three_screening_report,
    write_campaign_three_screening_report,
)


def _report():
    protocol = quant_research_campaign_three_screening_protocol_v1()
    evidence = []
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
        for horizon in (1, 3, 5):
            for endpoint in endpoints:
                item = CampaignThreeSessionEvidenceV1(
                    hypothesis_id=hypothesis.hypothesis_id,
                    role=hypothesis.role,
                    horizon_sessions=horizon,
                    endpoint=endpoint,
                    signal_session=date(2025, 7, 22),
                    instrument_count=100,
                    state_value="0.1000000000",
                    session_rank_ic="0.0100000000",
                )
                evidence.append(item)
                summaries.append(
                    CampaignThreeInteractionSummaryV1(
                        hypothesis_id=hypothesis.hypothesis_id,
                        role=hypothesis.role,
                        horizon_sessions=horizon,
                        endpoint=endpoint,
                        eligible_session_count=1,
                        first_half_session_count=1,
                        second_half_session_count=0,
                        evidence_collection_fingerprint=_collection_fingerprint(
                            (item,)
                        ),
                        favorable_state_session_count=(
                            1
                            if hypothesis.role
                            is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
                            else None
                        ),
                        reason_codes=("regression_unavailable",),
                    )
                )
    decisions = tuple(
        CampaignThreeScreeningDecisionV1(
            trial_id=hypothesis.trial_id,
            hypothesis_id=hypothesis.hypothesis_id,
            role=hypothesis.role,
            related_hypothesis_family=hypothesis.related_hypothesis_family,
            primary_endpoint_count=(
                2
                if hypothesis.role
                is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
                else 1
            ),
            raw_family_p_value="1.0000000000",
            holm_adjusted_p_value="1.0000000000",
            status=QuantResearchFactorScreeningDecisionStatus.INCONCLUSIVE_DATA,
            passed_all_frozen_gates=False,
            selected_for_model_candidate_set=False,
            failed_gate_codes=("regression_unavailable",),
        )
        for hypothesis in protocol.formal_hypotheses
    )
    evidence_tuple = tuple(evidence)
    return build_campaign_three_screening_report_v1(
        protocol_fingerprint=protocol.logical_fingerprint,
        registered_ledger_fingerprint=(
            quant_research_discovery_trial_ledger_v4().logical_fingerprint
        ),
        access_request_fingerprint="1" * 64,
        access_grant_fingerprint="2" * 64,
        implementation_revision="3" * 40,
        evaluator_code_sha256="4" * 64,
        created_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        source_v1_observation_collection_fingerprint="5" * 64,
        source_v2_observation_collection_fingerprint="6" * 64,
        source_label_collection_fingerprint="7" * 64,
        source_v1_eod_fingerprint="8" * 64,
        source_v1_adjustment_fingerprint="9" * 64,
        source_v2_eod_fingerprint="a" * 64,
        source_v2_adjustment_fingerprint="b" * 64,
        source_label_action_fingerprint="c" * 64,
        source_label_adjustment_fingerprint="d" * 64,
        source_terminal_reference_collection_fingerprint="e" * 64,
        session_evidence_collection_fingerprint=_collection_fingerprint(
            evidence_tuple
        ),
        label_state_counts={
            state.value: (
                503580
                if state is QuantResearchFactorScreeningLabelState.OBSERVED_EOD_EXACT
                else 0
            )
            for state in QuantResearchFactorScreeningLabelState
        },
        session_evidence=evidence_tuple,
        summaries=tuple(summaries),
        decisions=decisions,
        selected_candidate_alpha_ids=(),
        selected_risk_guard_ids=(),
        status=QuantResearchFactorScreeningReportStatus.INCONCLUSIVE_DATA,
        reason_codes=("candidate_alpha_screen_has_inconclusive_data",),
        limitation_codes=("development_selection_evidence_not_validated_alpha",),
    )


def test_campaign_three_report_round_trips_in_owner_only_custody(tmp_path) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    custody.chmod(0o700)
    root = custody / "report=test"
    report = _report()

    path, sha256, status = write_campaign_three_screening_report(
        output_root=root,
        output_custody_root=custody,
        report=report,
    )

    assert status == "published"
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o400
    assert read_campaign_three_screening_report(
        output_root=root,
        output_custody_root=custody,
    ) == (report, sha256)


def test_campaign_three_report_rejects_different_existing_content(tmp_path) -> None:
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    custody.chmod(0o700)
    root = custody / "report=test"
    report = _report()
    write_campaign_three_screening_report(
        output_root=root,
        output_custody_root=custody,
        report=report,
    )
    path = next(root.iterdir())
    path.chmod(0o600)

    with pytest.raises(CampaignThreeScreeningPersistenceError, match="file differs"):
        read_campaign_three_screening_report(
            output_root=root,
            output_custody_root=custody,
        )
