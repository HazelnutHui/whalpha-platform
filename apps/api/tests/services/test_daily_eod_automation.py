from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_automation as automation


TARGET = date(2026, 8, 26)
PRIOR = date(2026, 8, 25)
IDENTITY_FP = "1" * 64
EOD_FP = "2" * 64
PHASE1A_FP = "3" * 64
PRIOR_PHASE1B_FP = "4" * 64
PHASE1B_FP = "5" * 64
PRIOR_CANDIDATE_FP = "6" * 64
CANDIDATE_FP = "7" * 64
ENTRY_FP = "8" * 64
PHASE2_FP = "9" * 64
PREVIEW_FP = "a" * 64
STRATEGY_FP = "b" * 64
MI_PLAN_FP = "c" * 64


def _paths(tmp_path: Path) -> automation.DailyEodAutomationPaths:
    suffix = tmp_path.name
    return automation.DailyEodAutomationPaths(
        data_root=tmp_path,
        phase1a_audit=Path(f"/tmp/{suffix}-phase1a"),
        prior_phase1b_audit=Path(f"/tmp/{suffix}-prior-phase1b"),
        phase1b_audit=Path(f"/tmp/{suffix}-phase1b"),
        prior_candidate_audit=Path(f"/tmp/{suffix}-prior-candidate"),
        candidate_audit=Path(f"/tmp/{suffix}-candidate"),
        entry_geometry_audit=Path(f"/tmp/{suffix}-entry"),
        phase2_audit=Path(f"/tmp/{suffix}-phase2"),
        preview_bundle=Path(f"/tmp/{suffix}-preview"),
        strategy_channel_audit=Path(f"/tmp/{suffix}-strategy"),
        market_intelligence_output_root=Path(f"/tmp/{suffix}-mi-output"),
        market_intelligence_approval_plan=Path(f"/tmp/{suffix}-mi-plan.json"),
    )


def _install_completed_readers(monkeypatch, paths, *, existing=None) -> None:
    existing_paths = set(existing or automation._stage_locations(TARGET, paths).values())
    existing_paths.update((paths.prior_phase1b_audit, paths.prior_candidate_audit))
    monkeypatch.setattr(automation, "_lexists", lambda path: path in existing_paths)
    monkeypatch.setattr(
        automation,
        "load_identity_snapshot",
        lambda *args, **kwargs: SimpleNamespace(
            as_of_date=TARGET,
            manifest={"snapshot_content_sha256": IDENTITY_FP},
        ),
    )

    class EodRepository:
        def __init__(self, root):
            self.root = root

        def inspect_session(self, session):
            return SimpleNamespace(
                session_date=session,
                content_fingerprint=EOD_FP,
                identity_snapshot_fingerprint=IDENTITY_FP,
            )

    monkeypatch.setattr(automation, "CanonicalEodReadRepository", EodRepository)
    monkeypatch.setattr(
        automation,
        "read_market_regime_audit_contents",
        lambda path: SimpleNamespace(
            manifest={
                "as_of_session": TARGET.isoformat(),
                "logical_content_fingerprint": PHASE1A_FP,
            },
            input_manifest={
                "identity_logical_fingerprint": IDENTITY_FP,
                "eod_content_fingerprint": EOD_FP,
            },
        ),
    )

    def state_reader(path):
        if path == paths.prior_phase1b_audit:
            return SimpleNamespace(
                manifest={
                    "as_of_session": PRIOR.isoformat(),
                    "logical_content_fingerprint": PRIOR_PHASE1B_FP,
                },
                source_manifest={},
            )
        return SimpleNamespace(
            manifest={
                "as_of_session": TARGET.isoformat(),
                "logical_content_fingerprint": PHASE1B_FP,
                "execution_mode": "verified_prior_incremental",
                "prior_as_of_session": PRIOR.isoformat(),
                "prior_audit_logical_fingerprint": PRIOR_PHASE1B_FP,
            },
            source_manifest={"phase1a_audit_logical_fingerprint": PHASE1A_FP},
        )

    monkeypatch.setattr(automation, "read_market_regime_state_audit_contents", state_reader)

    def candidate_reader(path):
        if path == paths.prior_candidate_audit:
            return SimpleNamespace(
                manifest={
                    "as_of_session": PRIOR.isoformat(),
                    "logical_content_fingerprint": PRIOR_CANDIDATE_FP,
                }
            )
        return SimpleNamespace(
            manifest={
                "as_of_session": TARGET.isoformat(),
                "logical_content_fingerprint": CANDIDATE_FP,
                "execution_mode": "verified_prior_incremental",
                "prior_as_of_session": PRIOR.isoformat(),
                "prior_audit_logical_fingerprint": PRIOR_CANDIDATE_FP,
            },
            validation_ledger={
                "validation_tier": "daily",
                "validation_scope": "verified_prior_plus_current_session_oracle",
            },
        )

    monkeypatch.setattr(
        automation, "read_opportunity_candidate_planning_evidence", candidate_reader
    )
    monkeypatch.setattr(
        automation,
        "read_candidate_entry_geometry_audit",
        lambda path: {
            "as_of_session": TARGET.isoformat(),
            "logical_content_fingerprint": ENTRY_FP,
            "source": {"candidate_audit_logical_fingerprint": CANDIDATE_FP},
        },
    )
    monkeypatch.setattr(
        automation,
        "read_etf_relationship_planning_evidence",
        lambda path: SimpleNamespace(
            manifest={
                "as_of_session": TARGET.isoformat(),
                "logical_content_fingerprint": PHASE2_FP,
            },
            source_manifest={
                "phase1a_audit_logical_fingerprint": PHASE1A_FP,
                "phase1b_audit_logical_fingerprint": PHASE1B_FP,
            },
        ),
    )
    monkeypatch.setattr(
        automation,
        "read_market_regime_preview_bundle",
        lambda path: SimpleNamespace(
            payload=SimpleNamespace(
                as_of_session=TARGET,
                logical_fingerprint=PREVIEW_FP,
                source_logical_fingerprints=SimpleNamespace(
                    phase1a=PHASE1A_FP,
                    phase1b=PHASE1B_FP,
                    phase2=PHASE2_FP,
                ),
            )
        ),
    )
    monkeypatch.setattr(
        automation,
        "read_candidate_strategy_channel_audit",
        lambda path: {
            "as_of_session": TARGET.isoformat(),
            "logical_content_fingerprint": STRATEGY_FP,
            "source": {
                "candidate_audit": {
                    "logical_content_fingerprint": CANDIDATE_FP,
                },
                "entry_geometry_audit": {
                    "logical_content_fingerprint": ENTRY_FP,
                },
            },
        },
    )
    monkeypatch.setattr(
        automation,
        "read_market_intelligence_approval_plan",
        lambda path: SimpleNamespace(
            analysis_session=TARGET,
            plan_content_fingerprint=MI_PLAN_FP,
            plan_version="1.2",
            data_root=str(paths.data_root),
            preview_bundle_path=str(paths.preview_bundle),
            phase1a_audit_path=str(paths.phase1a_audit),
            phase1b_audit_path=str(paths.phase1b_audit),
            phase2_audit_path=str(paths.phase2_audit),
            candidate_audit_path=str(paths.candidate_audit),
            entry_geometry_audit_path=str(paths.entry_geometry_audit),
            candidate_path=str(
                paths.market_intelligence_output_root
                / "market-intelligence.plan.artifacts"
            ),
            source=SimpleNamespace(
                phase_logical_fingerprints=SimpleNamespace(
                    phase1a=PHASE1A_FP,
                    phase1b=PHASE1B_FP,
                    phase2=PHASE2_FP,
                ),
                preview_payload_logical_fingerprint=PREVIEW_FP,
            ),
            candidate_source=SimpleNamespace(
                candidate_audit_logical_fingerprint=CANDIDATE_FP,
            ),
            entry_geometry_audit_logical_fingerprint=ENTRY_FP,
            activation_allowed=True,
        ),
    )


def test_all_formal_analytics_are_ready_for_separate_publication_review(monkeypatch, tmp_path) -> None:
    paths = _paths(tmp_path)
    _install_completed_readers(monkeypatch, paths)
    first = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    second = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert first.status is automation.PlanStatus.ANALYTICS_READY
    assert first.next_action is automation.NextAction.REVIEW_PUBLICATION
    assert first.logical_content_fingerprint == second.logical_content_fingerprint
    assert first.publication_authorized is False
    assert first.deployment_authorized is False
    assert first.scheduler_enabled is False
    assert first.external_request_count == 0
    assert first.production_write_count == 0
    assert [item.stage for item in first.observations] == [
        "identity",
        "eod",
        "phase1a",
        "prior_phase1b",
        "phase1b",
        "prior_candidate",
        "candidate",
        "entry_geometry",
        "phase2",
        "preview",
        "strategy_channels",
        "publication_plan",
    ]


def test_missing_identity_reports_authorized_catchup_as_only_next_action(monkeypatch, tmp_path) -> None:
    paths = _paths(tmp_path)
    monkeypatch.setattr(automation, "_lexists", lambda path: False)
    monkeypatch.setattr(
        automation,
        "load_identity_snapshot",
        lambda *args, **kwargs: pytest.fail("missing identity must not be read"),
    )
    plan = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert plan.status is automation.PlanStatus.WAITING_FOR_AUTHORIZED_INPUT
    assert plan.next_action is automation.NextAction.PREPARE_IDENTITY_CATCHUP
    assert plan.reason_codes == ("identity_required",)


def test_missing_phase1a_with_existing_downstream_artifact_blocks(monkeypatch, tmp_path) -> None:
    paths = _paths(tmp_path)
    locations = automation._stage_locations(TARGET, paths)
    existing = {locations["identity"], locations["eod"], locations["candidate"]}
    _install_completed_readers(monkeypatch, paths, existing=existing)
    plan = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert plan.status is automation.PlanStatus.BLOCKED
    assert plan.next_action is automation.NextAction.OPERATOR_DIAGNOSIS
    assert plan.reason_codes == ("downstream_artifact_without_verified_prerequisite",)


def test_verified_prior_makes_missing_phase1b_ready_for_incremental_calculation(monkeypatch, tmp_path) -> None:
    paths = _paths(tmp_path)
    locations = automation._stage_locations(TARGET, paths)
    existing = {locations["identity"], locations["eod"], locations["phase1a"]}
    _install_completed_readers(monkeypatch, paths, existing=existing)
    plan = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert plan.status is automation.PlanStatus.READY_FOR_OFFLINE_CALCULATION
    assert plan.next_action is automation.NextAction.CALCULATE_PHASE1B_INCREMENTAL
    assert plan.reason_codes == ("phase1b_required",)


@pytest.mark.parametrize(
    ("missing_stage", "expected_action"),
    [
        ("phase2", automation.NextAction.CALCULATE_ETF_RELATIONSHIPS),
        ("preview", automation.NextAction.BUILD_MARKET_PREVIEW),
        ("strategy_channels", automation.NextAction.CALCULATE_STRATEGY_CHANNELS),
    ],
)
def test_missing_latter_half_stage_selects_one_exact_offline_action(
    monkeypatch, tmp_path, missing_stage, expected_action
) -> None:
    paths = _paths(tmp_path)
    locations = automation._stage_locations(TARGET, paths)
    stage_order = tuple(locations)
    missing_index = stage_order.index(missing_stage)
    existing = {locations[name] for name in stage_order[:missing_index]}
    _install_completed_readers(monkeypatch, paths, existing=existing)
    plan = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert plan.status is automation.PlanStatus.READY_FOR_OFFLINE_CALCULATION
    assert plan.next_action is expected_action
    assert plan.reason_codes == (f"{missing_stage}_required",)
    assert plan.publication_authorized is False
    assert plan.deployment_authorized is False


def test_missing_publication_plan_selects_one_exact_review_preparation(monkeypatch, tmp_path) -> None:
    paths = _paths(tmp_path)
    locations = automation._stage_locations(TARGET, paths)
    existing = {
        path
        for stage, path in locations.items()
        if stage not in {"publication_output", "publication_plan"}
    }
    _install_completed_readers(monkeypatch, paths, existing=existing)
    plan = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert plan.status is automation.PlanStatus.READY_FOR_OFFLINE_CALCULATION
    assert (
        plan.next_action
        is automation.NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN
    )
    assert plan.reason_codes == ("publication_plan_required",)
    assert plan.observations[-1].stage == "publication_plan"
    assert plan.observations[-1].status is automation.ArtifactStatus.MISSING


@pytest.mark.parametrize("present_stage", ("publication_output", "publication_plan"))
def test_partial_publication_plan_artifacts_block(monkeypatch, tmp_path, present_stage) -> None:
    paths = _paths(tmp_path)
    locations = automation._stage_locations(TARGET, paths)
    existing = {
        path
        for stage, path in locations.items()
        if stage not in {"publication_output", "publication_plan"}
    }
    existing.add(locations[present_stage])
    _install_completed_readers(monkeypatch, paths, existing=existing)
    plan = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert plan.status is automation.PlanStatus.BLOCKED
    assert plan.reason_codes == ("publication_plan_partial",)


def test_publication_plan_source_lineage_mismatch_blocks(monkeypatch, tmp_path) -> None:
    paths = _paths(tmp_path)
    _install_completed_readers(monkeypatch, paths)
    monkeypatch.setattr(
        automation,
        "read_market_intelligence_approval_plan",
        lambda path: SimpleNamespace(
            analysis_session=TARGET,
            plan_content_fingerprint=MI_PLAN_FP,
            plan_version="1.2",
            data_root=str(paths.data_root),
            preview_bundle_path=str(paths.preview_bundle),
            phase1a_audit_path=str(paths.phase1a_audit),
            phase1b_audit_path=str(paths.phase1b_audit),
            phase2_audit_path=str(paths.phase2_audit),
            candidate_audit_path=str(paths.candidate_audit),
            entry_geometry_audit_path=str(paths.entry_geometry_audit),
            candidate_path=str(
                paths.market_intelligence_output_root
                / "market-intelligence.plan.artifacts"
            ),
            source=SimpleNamespace(
                phase_logical_fingerprints=SimpleNamespace(
                    phase1a=PHASE1A_FP,
                    phase1b=PHASE1B_FP,
                    phase2="f" * 64,
                ),
                preview_payload_logical_fingerprint=PREVIEW_FP,
            ),
            candidate_source=SimpleNamespace(
                candidate_audit_logical_fingerprint=CANDIDATE_FP,
            ),
            entry_geometry_audit_logical_fingerprint=ENTRY_FP,
            activation_allowed=True,
        ),
    )
    plan = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert plan.status is automation.PlanStatus.BLOCKED
    assert plan.reason_codes == ("publication_plan_source_binding_mismatch",)


@pytest.mark.parametrize(
    ("reader_name", "replacement", "reason_code"),
    [
        (
            "read_etf_relationship_planning_evidence",
            lambda path: SimpleNamespace(
                manifest={
                    "as_of_session": TARGET.isoformat(),
                    "logical_content_fingerprint": PHASE2_FP,
                },
                source_manifest={
                    "phase1a_audit_logical_fingerprint": "f" * 64,
                    "phase1b_audit_logical_fingerprint": PHASE1B_FP,
                },
            ),
            "phase2_source_binding_mismatch",
        ),
        (
            "read_market_regime_preview_bundle",
            lambda path: SimpleNamespace(
                payload=SimpleNamespace(
                    as_of_session=TARGET,
                    logical_fingerprint=PREVIEW_FP,
                    source_logical_fingerprints=SimpleNamespace(
                        phase1a=PHASE1A_FP,
                        phase1b=PHASE1B_FP,
                        phase2="f" * 64,
                    ),
                )
            ),
            "preview_source_binding_mismatch",
        ),
        (
            "read_candidate_strategy_channel_audit",
            lambda path: {
                "as_of_session": TARGET.isoformat(),
                "logical_content_fingerprint": STRATEGY_FP,
                "source": {
                    "candidate_audit": {
                        "logical_content_fingerprint": CANDIDATE_FP,
                    },
                    "entry_geometry_audit": {
                        "logical_content_fingerprint": "f" * 64,
                    },
                },
            },
            "strategy_channels_source_binding_mismatch",
        ),
    ],
)
def test_latter_half_source_lineage_mismatch_blocks(
    monkeypatch, tmp_path, reader_name, replacement, reason_code
) -> None:
    paths = _paths(tmp_path)
    _install_completed_readers(monkeypatch, paths)
    monkeypatch.setattr(automation, reader_name, replacement)
    plan = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert plan.status is automation.PlanStatus.BLOCKED
    assert plan.next_action is automation.NextAction.OPERATOR_DIAGNOSIS
    assert plan.reason_codes == (reason_code,)


def test_existing_candidate_that_fails_formal_reader_blocks(monkeypatch, tmp_path) -> None:
    paths = _paths(tmp_path)
    _install_completed_readers(monkeypatch, paths)
    monkeypatch.setattr(
        automation,
        "read_opportunity_candidate_planning_evidence",
        lambda path: (
            SimpleNamespace(
                manifest={
                    "as_of_session": PRIOR.isoformat(),
                    "logical_content_fingerprint": PRIOR_CANDIDATE_FP,
                }
            )
            if path == paths.prior_candidate_audit
            else (_ for _ in ()).throw(RuntimeError("corrupt"))
        ),
    )
    plan = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert plan.status is automation.PlanStatus.BLOCKED
    assert plan.reason_codes == ("candidate_invalid",)
    assert plan.observations[-1].reason_codes == ("formal_reader_failed_closed",)


def test_wrong_candidate_prior_fingerprint_blocks(monkeypatch, tmp_path) -> None:
    paths = _paths(tmp_path)
    _install_completed_readers(monkeypatch, paths)

    def candidate_reader(path):
        if path == paths.prior_candidate_audit:
            return SimpleNamespace(
                manifest={
                    "as_of_session": PRIOR.isoformat(),
                    "logical_content_fingerprint": PRIOR_CANDIDATE_FP,
                }
            )
        return SimpleNamespace(
            manifest={
                "as_of_session": TARGET.isoformat(),
                "logical_content_fingerprint": CANDIDATE_FP,
                "execution_mode": "verified_prior_incremental",
                "prior_as_of_session": PRIOR.isoformat(),
                "prior_audit_logical_fingerprint": "9" * 64,
            },
            validation_ledger={
                "validation_tier": "daily",
                "validation_scope": "verified_prior_plus_current_session_oracle",
            },
        )

    monkeypatch.setattr(
        automation, "read_opportunity_candidate_planning_evidence", candidate_reader
    )
    plan = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert plan.status is automation.PlanStatus.BLOCKED
    assert plan.reason_codes == ("candidate_prior_binding_mismatch",)


def test_candidate_without_explicit_daily_validation_tier_blocks(monkeypatch, tmp_path) -> None:
    paths = _paths(tmp_path)
    _install_completed_readers(monkeypatch, paths)

    def candidate_reader(path):
        if path == paths.prior_candidate_audit:
            return SimpleNamespace(
                manifest={
                    "as_of_session": PRIOR.isoformat(),
                    "logical_content_fingerprint": PRIOR_CANDIDATE_FP,
                }
            )
        return SimpleNamespace(
            manifest={
                "as_of_session": TARGET.isoformat(),
                "logical_content_fingerprint": CANDIDATE_FP,
                "execution_mode": "verified_prior_incremental",
                "prior_as_of_session": PRIOR.isoformat(),
                "prior_audit_logical_fingerprint": PRIOR_CANDIDATE_FP,
            },
            validation_ledger={
                "validation_scope": "verified_prior_plus_current_session_oracle",
            },
        )

    monkeypatch.setattr(
        automation, "read_opportunity_candidate_planning_evidence", candidate_reader
    )
    plan = automation.plan_daily_eod_automation(target_session=TARGET, paths=paths)
    assert plan.status is automation.PlanStatus.BLOCKED
    assert plan.reason_codes == ("candidate_daily_validation_missing",)


def test_audit_paths_must_be_distinct_direct_tmp_children(tmp_path) -> None:
    paths = _paths(tmp_path)
    duplicate = automation.DailyEodAutomationPaths(
        data_root=paths.data_root,
        phase1a_audit=paths.phase1a_audit,
        prior_phase1b_audit=paths.phase1a_audit,
        phase1b_audit=paths.phase1b_audit,
        prior_candidate_audit=paths.prior_candidate_audit,
        candidate_audit=paths.candidate_audit,
        entry_geometry_audit=paths.entry_geometry_audit,
        phase2_audit=paths.phase2_audit,
        preview_bundle=paths.preview_bundle,
        strategy_channel_audit=paths.strategy_channel_audit,
        market_intelligence_output_root=paths.market_intelligence_output_root,
        market_intelligence_approval_plan=paths.market_intelligence_approval_plan,
    )
    with pytest.raises(automation.DailyEodAutomationError, match="distinct"):
        automation.plan_daily_eod_automation(target_session=TARGET, paths=duplicate)

    nested = replace(paths, phase1a_audit=tmp_path / "nested")
    with pytest.raises(automation.DailyEodAutomationError, match="direct children"):
        automation.plan_daily_eod_automation(target_session=TARGET, paths=nested)


def test_non_session_target_is_rejected_before_artifact_reads(monkeypatch, tmp_path) -> None:
    paths = _paths(tmp_path)
    monkeypatch.setattr(
        automation,
        "load_identity_snapshot",
        lambda *args, **kwargs: pytest.fail("artifact readers must not run"),
    )
    with pytest.raises(automation.DailyEodAutomationError, match="XNYS session"):
        automation.plan_daily_eod_automation(
            target_session=date(2026, 8, 29),
            paths=paths,
        )
