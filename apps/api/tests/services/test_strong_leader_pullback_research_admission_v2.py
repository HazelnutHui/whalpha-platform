from __future__ import annotations

import pytest
from pydantic import ValidationError

from tip_api.services import strong_leader_pullback_research_admission_v2 as service


def _features(**changes: object) -> service.ReconstructedFeatureEvidenceV1:
    values: dict[str, object] = {
        "diagnostics_report_sha256": "1" * 64,
        "diagnostics_logical_fingerprint": "2" * 64,
        "total_session_count": 287,
        "complete_cross_section_session_count": 274,
        "excluded_session_count": 13,
        "expected_path_count": 437402,
        "complete_path_count": 417209,
        "excluded_path_count": 20193,
        "exclusions": (
            {
                "reason_code": "feature_regime_bootstrap_unavailable",
                "session_count": 1,
                "path_count": 1547,
            },
            {
                "reason_code": "split_evidence_quarantined",
                "session_count": 12,
                "path_count": 18646,
            },
        ),
    }
    values.update(changes)
    return service.ReconstructedFeatureEvidenceV1.model_validate(values)


def _adjustments(**changes: object) -> service.MechanicalAdjustmentEvidenceV1:
    values: dict[str, object] = {
        "source_fingerprint": "3" * 64,
        "source_range_naturally_complete": True,
        "independent_range_composition_matches": True,
        "repeated_economic_rows_match": True,
        "source_vintage_frozen": True,
        "unresolved_action_hazard_sessions_excluded": True,
    }
    values.update(changes)
    return service.MechanicalAdjustmentEvidenceV1.model_validate(values)


def _terminal(**changes: object) -> service.TerminalReferenceEvidenceV1:
    values: dict[str, object] = {
        "terminal_population_fingerprint": "4" * 64,
        "crossing_path_count": 302,
        "exact_terminal_reference_path_count": 214,
        "interval_terminal_reference_path_count": 88,
        "unbounded_terminal_reference_path_count": 0,
        "interval_rules_frozen_before_outcomes": True,
    }
    values.update(changes)
    return service.TerminalReferenceEvidenceV1.model_validate(values)


def _controls(**changes: object) -> service.ResearchControlEvidenceV1:
    values: dict[str, object] = {
        "chronological_plan_fingerprint": "5" * 64,
        "holdout_sealed_and_unconsumed": True,
    }
    values.update(changes)
    return service.ResearchControlEvidenceV1.model_validate(values)


def test_ready_lane_opens_only_reconstructed_development() -> None:
    result = service.assess_strong_leader_pullback_research_admission_v2(
        features=_features(),
        adjustments=_adjustments(),
        terminal_references=_terminal(),
        controls=_controls(),
    )

    assert (
        result.status
        is service.ResearchAdmissionV2Status.READY_FOR_RECONSTRUCTED_DEVELOPMENT
    )
    assert result.unresolved_gate_ids == ()
    assert result.development_label_construction_authorized is True
    assert result.development_parameter_selection_authorized is True
    assert result.validation_authorized is False
    assert result.holdout_access_authorized is False
    assert result.performance_claim_authorized is False
    assert result.candidate_activation_authorized is False
    assert result.reconstructed_not_as_operated_disclosure_required is True


@pytest.mark.parametrize(
    ("family", "changes", "expected_gate"),
    (
        (
            "features",
            {
                "total_session_count": 264,
                "complete_cross_section_session_count": 251,
            },
            "minimum_complete_feature_sessions",
        ),
        (
            "adjustments",
            {"source_range_naturally_complete": False},
            "mechanical_split_adjustment_evidence",
        ),
        (
            "terminal",
            {
                "interval_terminal_reference_path_count": 80,
                "unbounded_terminal_reference_path_count": 8,
            },
            "finite_terminal_reference_intervals",
        ),
        (
            "terminal",
            {"interval_rules_frozen_before_outcomes": False},
            "preoutcome_terminal_interval_policy",
        ),
        (
            "controls",
            {"holdout_sealed_and_unconsumed": False},
            "sealed_unconsumed_holdout",
        ),
    ),
)
def test_incomplete_evidence_blocks_without_opening_labels(
    family: str, changes: dict[str, object], expected_gate: str
) -> None:
    features = _features(**changes) if family == "features" else _features()
    adjustments = _adjustments(**changes) if family == "adjustments" else _adjustments()
    terminal = _terminal(**changes) if family == "terminal" else _terminal()
    controls = _controls(**changes) if family == "controls" else _controls()

    result = service.assess_strong_leader_pullback_research_admission_v2(
        features=features,
        adjustments=adjustments,
        terminal_references=terminal,
        controls=controls,
    )

    assert result.status is service.ResearchAdmissionV2Status.BLOCKED
    assert expected_gate in result.unresolved_gate_ids
    assert result.development_label_construction_authorized is False
    assert result.development_parameter_selection_authorized is False


def test_feature_evidence_rejects_unreconciled_or_reordered_exclusions() -> None:
    with pytest.raises(ValidationError, match="counts do not reconcile"):
        _features(excluded_path_count=20192)
    with pytest.raises(ValidationError, match="unique and sorted"):
        _features(exclusions=tuple(reversed(_features().exclusions)))


def test_terminal_evidence_never_silently_drops_paths() -> None:
    with pytest.raises(ValidationError, match="path counts do not reconcile"):
        _terminal(interval_terminal_reference_path_count=87)


def test_result_fingerprint_and_authority_are_tamper_evident() -> None:
    result = service.assess_strong_leader_pullback_research_admission_v2(
        features=_features(),
        adjustments=_adjustments(),
        terminal_references=_terminal(),
        controls=_controls(),
    )
    payload = result.model_dump(mode="json")
    payload["holdout_access_authorized"] = True

    with pytest.raises(ValidationError):
        service.StrongLeaderPullbackResearchAdmissionV2.model_validate(payload)
