from __future__ import annotations

import os
import stat
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from tip_api.services import strong_leader_pullback_method_engineering_launch_review as service


def _family(
    family: str,
    status: str,
    *,
    development_ready: bool,
) -> SimpleNamespace:
    return SimpleNamespace(
        family=family,
        status=status,
        development_ready=development_ready,
        evidence_fingerprint={
            "eod_price_bar": "1" * 64,
            "point_in_time_identity": "2" * 64,
            "universe_membership": "3" * 64,
        }.get(family, "4" * 64),
    )


def _pre_research(**changes: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "decision_status": "rejected_data_blocked",
        "historical_coverage_manifest_published": False,
        "development_authorized": False,
        "true_return_labels_authorized": False,
        "strategy_research_started": False,
        "strategy_trigger_count": 0,
        "forward_outcome_count": 0,
        "performance_metric_count": 0,
        "parameter_selection_count": 0,
        "complete_cross_section_session_count": 0,
        "signal_session_count": 287,
        "included_path_count": 437402,
        "first_signal_session": "2025-06-23",
        "last_signal_session": "2026-08-12",
        "logical_fingerprint": "5" * 64,
        "blocker_codes": (
            "corporate_action_absence_neutrality_unproven",
            "historical_coverage_manifest_absent",
        ),
        "family_reviews": (
            _family(
                "eod_price_bar",
                "complete_reconstruction_input",
                development_ready=True,
            ),
            _family(
                "point_in_time_identity",
                "complete_reconstruction_input",
                development_ready=True,
            ),
            _family(
                "universe_membership",
                "reconstructed_not_as_operated",
                development_ready=True,
            ),
            _family(
                "corporate_action",
                "partial_bounded_source_only",
                development_ready=False,
            ),
        ),
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _report(
    **changes: object,
) -> service.StrongLeaderPullbackMethodEngineeringLaunchReviewV1:
    return service._build_report(
        pre_research=_pre_research(**changes),  # type: ignore[arg-type]
        pre_research_sha256="6" * 64,
        implementation_revision="7" * 40,
        reviewed_at=datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
    )


def test_rejected_performance_gate_can_launch_only_outcome_blind_engineering() -> None:
    report = _report()

    assert report.decision_status == "ready_for_outcome_blind_method_engineering"
    assert report.formal_data_gate_status == "rejected_data_blocked"
    assert report.method_engineering_authorized is True
    assert report.private_outcome_blind_feature_diagnostics_authorized is True
    assert report.quant_research_lab_method_surface_authorized is True
    assert report.selection_reuse_prohibited is True
    assert report.true_return_labels_authorized is False
    assert report.parameter_selection_authorized is False
    assert report.formal_development_stage_authorized is False
    assert report.validation_authorized is False
    assert report.holdout_access_authorized is False
    assert report.performance_claims_authorized is False
    assert report.candidate_activation_authorized is False
    assert report.canonical_data_write_count == 0
    assert report.network_request_count == 0
    assert tuple(item.family for item in report.method_input_families) == (
        "eod_price_bar",
        "point_in_time_identity",
        "universe_membership",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("true_return_labels_authorized", True),
        ("strategy_research_started", True),
        ("strategy_trigger_count", 1),
        ("forward_outcome_count", 1),
        ("performance_metric_count", 1),
        ("parameter_selection_count", 1),
        ("complete_cross_section_session_count", 1),
    ),
)
def test_launch_rejects_any_open_or_inconsistent_research_state(
    field: str, value: object
) -> None:
    with pytest.raises(
        service.StrongLeaderPullbackMethodEngineeringLaunchReviewError,
        match="not a safe method-engineering boundary",
    ):
        _report(**{field: value})


def test_launch_rejects_incomplete_method_input_family() -> None:
    families = list(_pre_research().family_reviews)
    families[2] = _family(
        "universe_membership",
        "reconstructed_not_as_operated",
        development_ready=False,
    )

    with pytest.raises(
        service.StrongLeaderPullbackMethodEngineeringLaunchReviewError,
        match="input families are not ready",
    ):
        _report(family_reviews=tuple(families))


def test_report_rejects_scope_or_fingerprint_tampering() -> None:
    payload = _report().model_dump(mode="json")
    payload["allowed_action_codes"] = payload["allowed_action_codes"][:-1]

    with pytest.raises(ValidationError, match="launch review differs"):
        service.StrongLeaderPullbackMethodEngineeringLaunchReviewV1.model_validate(
            payload
        )


def test_owner_only_write_reread_and_exact_replay(tmp_path) -> None:
    os.chmod(tmp_path, 0o700)
    output = tmp_path / "review=fixture-v1"
    report = _report()

    first = service._write_report(
        output_root=output,
        output_custody_root=tmp_path,
        report=report,
    )
    second = service._write_report(
        output_root=output,
        output_custody_root=tmp_path,
        report=report,
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert first.report_sha256 == second.report_sha256
    assert second.report == report
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE((output / service.REPORT_FILE).stat().st_mode) == 0o400
    assert tuple(output.iterdir()) == (output / service.REPORT_FILE,)


def test_output_must_be_direct_owner_only_custody_child(tmp_path) -> None:
    report = _report()
    os.chmod(tmp_path, 0o755)

    with pytest.raises(
        service.StrongLeaderPullbackMethodEngineeringLaunchReviewError,
        match="target is unsafe",
    ):
        service._write_report(
            output_root=tmp_path / "review=fixture-v1",
            output_custody_root=tmp_path,
            report=report,
        )
