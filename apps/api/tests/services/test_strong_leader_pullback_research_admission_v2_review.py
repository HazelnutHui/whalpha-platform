from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tip_api.services import strong_leader_pullback_research_admission_v2 as admission
from tip_api.services import strong_leader_pullback_research_admission_v2_review as service


def _decision() -> tuple[
    admission.ReconstructedFeatureEvidenceV1,
    admission.MechanicalAdjustmentEvidenceV1,
    admission.TerminalReferenceEvidenceV1,
    admission.ResearchControlEvidenceV1,
    admission.StrongLeaderPullbackResearchAdmissionV2,
]:
    features = admission.ReconstructedFeatureEvidenceV1(
        diagnostics_report_sha256="1" * 64,
        diagnostics_logical_fingerprint="2" * 64,
        total_session_count=287,
        feature_window_warmup_session_count=20,
        rankable_cross_section_session_count=267,
        complete_cross_section_session_count=254,
        excluded_session_count=13,
        expected_path_count=437_402,
        complete_path_count=417_209,
        excluded_path_count=20_193,
        exclusions=(
            admission.FeatureSessionExclusionV1(
                reason_code="feature_regime_bootstrap_unavailable",
                session_count=1,
                path_count=1_547,
            ),
            admission.FeatureSessionExclusionV1(
                reason_code="split_evidence_quarantined",
                session_count=12,
                path_count=18_646,
            ),
        ),
    )
    adjustments = admission.MechanicalAdjustmentEvidenceV1(
        source_fingerprint="3" * 64,
        source_range_naturally_complete=True,
        independent_range_composition_matches=True,
        repeated_economic_rows_match=True,
        source_vintage_frozen=True,
        unresolved_action_hazard_sessions_excluded=True,
    )
    terminal = admission.TerminalReferenceEvidenceV1(
        terminal_population_fingerprint="4" * 64,
        crossing_path_count=302,
        exact_terminal_reference_path_count=219,
        interval_terminal_reference_path_count=83,
        unbounded_terminal_reference_path_count=0,
        interval_rules_frozen_before_outcomes=True,
    )
    controls = admission.ResearchControlEvidenceV1(
        chronological_plan_fingerprint="5" * 64,
        holdout_sealed_and_unconsumed=True,
    )
    return (
        features,
        adjustments,
        terminal,
        controls,
        admission.assess_strong_leader_pullback_research_admission_v2(
            features=features,
            adjustments=adjustments,
            terminal_references=terminal,
            controls=controls,
        ),
    )


def _report() -> service.StrongLeaderPullbackResearchAdmissionV2Review:
    features, adjustments, terminal, controls, decision = _decision()
    values = {
        "reviewed_at": datetime(2026, 9, 15, tzinfo=UTC),
        "implementation_revision": "a" * 40,
        "development_census_report_sha256": "1" * 64,
        "development_census_logical_fingerprint": "2" * 64,
        "diagnostics_report_sha256": "3" * 64,
        "diagnostics_logical_fingerprint": "4" * 64,
        "current_split_source_manifest_sha256": "5" * 64,
        "current_split_source_logical_fingerprint": "6" * 64,
        "repeat_split_source_manifest_sha256": "7" * 64,
        "repeat_split_source_logical_fingerprint": "8" * 64,
        "prior_split_source_manifest_sha256": "9" * 64,
        "prior_split_source_logical_fingerprint": "a" * 64,
        "split_resolution_shadow_manifest_sha256": "b" * 64,
        "split_resolution_shadow_logical_fingerprint": "c" * 64,
        "canonical_split_action_manifest_sha256": "d" * 64,
        "canonical_split_action_logical_fingerprint": "e" * 64,
        "canonical_split_adjustment_manifest_sha256": "f" * 64,
        "canonical_split_adjustment_logical_fingerprint": "1" * 64,
        "final_terminal_report_sha256": "2" * 64,
        "final_terminal_logical_fingerprint": "3" * 64,
        "feature_evidence": features,
        "adjustment_evidence": adjustments,
        "terminal_evidence": terminal,
        "control_evidence": controls,
        "decision": decision,
    }
    provisional = service.StrongLeaderPullbackResearchAdmissionV2Review.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return service.StrongLeaderPullbackResearchAdmissionV2Review.model_validate(
        {
            **values,
            "logical_fingerprint": service._fingerprint(
                provisional.model_dump(
                    mode="json", exclude={"logical_fingerprint"}
                )
            ),
        }
    )


def test_review_binds_ready_decision_without_broadening_authority() -> None:
    report = _report()

    assert report.decision.development_label_construction_authorized is True
    assert report.validation_authorized is False
    assert report.holdout_access_authorized is False
    assert report.candidate_activation_authorized is False
    assert report.contains_forward_outcomes is False


def test_review_rejects_decision_or_fingerprint_tampering() -> None:
    report = _report()
    payload = report.model_dump(mode="json")
    payload["decision"]["development_label_construction_authorized"] = False
    with pytest.raises(ValidationError):
        service.StrongLeaderPullbackResearchAdmissionV2Review.model_validate(payload)


def test_split_term_identity_ignores_only_provider_metadata() -> None:
    original = {
        "id": "old",
        "ticker": "ABC",
        "execution_date": "2026-01-02",
        "split_from": 1,
        "split_to": 2,
        "historical_adjustment_factor": 0.5,
    }
    revised = {
        **original,
        "id": "new",
        "historical_adjustment_factor": 0.25,
    }

    assert service._row_key(original) != service._row_key(revised)
    assert service._term_key(original) == service._term_key(revised)
