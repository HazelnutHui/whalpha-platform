from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.persistence.parquet.market_intelligence_active import (
    MarketIntelligencePublicationError,
    pointer_path,
    target_path,
)
from tip_api.services.daily_eod_automation import (
    ArtifactObservation,
    ArtifactStatus,
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_market_intelligence_apply_custody import (
    DailyEodMarketIntelligenceApplyConfig,
    DailyEodMarketIntelligenceApplyCustodyError,
    record_market_intelligence_apply_success,
    recover_market_intelligence_apply,
    reserve_market_intelligence_apply,
)
from tip_api.services.daily_eod_run_journal import (
    locked_daily_eod_run_journal,
    unresolved_started_event,
)


TARGET = date(2026, 8, 28)
CHECKED = datetime(2026, 8, 28, 21, 0, tzinfo=UTC)
CURRENT_STATE = "1" * 64
CONSUMER_STATE = "2" * 64
PLAN_CONTENT = "3" * 64
POINTER_FINGERPRINT = "4" * 64
PUBLICATION_ID = "2026-08-28T210000Z-test"


def _paths(tmp_path: Path) -> DailyEodAutomationPaths:
    suffix = f"{tmp_path.parent.name}-{tmp_path.name}"
    return DailyEodAutomationPaths(
        data_root=tmp_path / "data",
        phase1a_audit=tmp_path / "phase1a",
        prior_phase1b_audit=tmp_path / "prior-phase1b",
        phase1b_audit=tmp_path / "phase1b",
        prior_candidate_audit=tmp_path / "prior-candidate",
        candidate_audit=tmp_path / "candidate",
        entry_geometry_audit=tmp_path / "entry",
        phase2_audit=tmp_path / "phase2",
        preview_bundle=tmp_path / "preview",
        strategy_channel_audit=tmp_path / "strategy",
        market_intelligence_output_root=Path(f"/tmp/{suffix}-mi-output"),
        market_intelligence_approval_plan=Path(f"/tmp/{suffix}-mi-plan.json"),
    )


def _fixture(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths = _paths(tmp_path)
    paths.data_root.mkdir()
    run_root = tmp_path / "runs"
    run_root.mkdir(mode=0o700)
    run_root.chmod(0o700)
    raw = b'{"fixture":"mi-plan"}\n'
    paths.market_intelligence_approval_plan.write_bytes(raw)
    approval = SimpleNamespace(
        operation="market_intelligence_publication",
        analysis_session=TARGET,
        data_root=str(paths.data_root),
        expected_current_state_fingerprint=CURRENT_STATE,
        expected_consumer_state_fingerprint=CONSUMER_STATE,
        target_path=str(target_path(paths.data_root, TARGET, PUBLICATION_ID)),
        pointer_path=str(pointer_path(paths.data_root)),
        publication_id=PUBLICATION_ID,
        plan_content_fingerprint=PLAN_CONTENT,
        planned_pointer_fingerprint=POINTER_FINGERPRINT,
        activation_allowed=True,
        activation_allowed_by_review_authorization=False,
        review_deployment=None,
        actual_latest_completed_session=TARGET,
        expected_latest_completed_session=TARGET,
        inventory_change_file_count=3,
        aggregate_sha256="5" * 64,
        payload_sha256="6" * 64,
    )
    config = DailyEodMarketIntelligenceApplyConfig(
        target_session=TARGET,
        approval_plan_path=paths.market_intelligence_approval_plan,
        approved_plan_sha256=hashlib.sha256(raw).hexdigest(),
        expected_current_state_fingerprint=CURRENT_STATE,
        review_acknowledgement_sha256=None,
        data_root=paths.data_root,
        run_root=run_root,
        automation_paths=paths,
    )
    observation = ArtifactObservation(
        stage="publication_plan",
        status=ArtifactStatus.COMPLETED,
        path=str(paths.market_intelligence_approval_plan),
        as_of_session=TARGET.isoformat(),
        logical_fingerprint=PLAN_CONTENT,
    )
    automation = DailyEodAutomationPlan(
        contract_version="daily-eod-automation-plan/1.2",
        target_session=TARGET.isoformat(),
        prior_session="2026-08-27",
        status=PlanStatus.ANALYTICS_READY,
        next_action=NextAction.REVIEW_PUBLICATION,
        reason_codes=("publication_plan_ready_for_review",),
        observations=(observation,),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint="7" * 64,
    )
    return config, approval, automation


def _reserve(monkeypatch, config, approval, automation):
    monkeypatch.setattr(
        "tip_api.services.daily_eod_market_intelligence_apply_custody."
        "validate_approved_market_intelligence_freshness",
        lambda **_kwargs: None,
    )
    return reserve_market_intelligence_apply(
        config=config,
        checked_at=CHECKED,
        expected_automation_plan_fingerprint=(
            automation.logical_content_fingerprint
        ),
        clock=lambda: datetime(2026, 8, 28, 21, 1, tzinfo=UTC),
        planner=lambda **_kwargs: automation,
        plan_reader=lambda _path: approval,
        inventory_reader=lambda _root: CURRENT_STATE,
        consumer_reader=lambda _root: CONSUMER_STATE,
    )


def _active(config, approval):
    return SimpleNamespace(
        pointer=SimpleNamespace(
            pointer_content_fingerprint=POINTER_FINGERPRINT,
        ),
        payload=SimpleNamespace(
            publication_id=PUBLICATION_ID,
            analysis_session=TARGET,
        ),
        path=Path(approval.target_path),
        reference=SimpleNamespace(
            aggregate_sha256=approval.aggregate_sha256,
            payload_sha256=approval.payload_sha256,
        ),
    )


def test_reservation_binds_plan_state_and_leaves_apply_unexecuted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config, approval, automation = _fixture(tmp_path)

    result = _reserve(monkeypatch, config, approval, automation)

    assert result.outcome == "reserved"
    assert result.approval_plan is approval
    assert result.as_dict()["apply_executed_by_custody"] is False
    assert result.event.details["planned_pointer_fingerprint"] == POINTER_FINGERPRINT
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=TARGET,
    ) as journal:
        assert unresolved_started_event(journal.read_events()) == result.event


def test_reservation_rejects_changed_inventory_or_existing_target(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config, approval, automation = _fixture(tmp_path)
    monkeypatch.setattr(
        "tip_api.services.daily_eod_market_intelligence_apply_custody."
        "validate_approved_market_intelligence_freshness",
        lambda **_kwargs: None,
    )
    with pytest.raises(
        DailyEodMarketIntelligenceApplyCustodyError,
        match="inventory changed",
    ):
        reserve_market_intelligence_apply(
            config=config,
            checked_at=CHECKED,
            expected_automation_plan_fingerprint=(
                automation.logical_content_fingerprint
            ),
            clock=lambda: datetime(2026, 8, 28, 21, 1, tzinfo=UTC),
            planner=lambda **_kwargs: automation,
            plan_reader=lambda _path: approval,
            inventory_reader=lambda _root: "8" * 64,
            consumer_reader=lambda _root: CONSUMER_STATE,
        )
    Path(approval.target_path).mkdir(parents=True)
    with pytest.raises(
        DailyEodMarketIntelligenceApplyCustodyError,
        match="no longer absent",
    ):
        _reserve(monkeypatch, config, approval, automation)


def test_success_requires_exact_active_pointer_and_closes_attempt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config, approval, automation = _fixture(tmp_path)
    _reserve(monkeypatch, config, approval, automation)

    result = record_market_intelligence_apply_success(
        config=config,
        clock=lambda: datetime(2026, 8, 28, 21, 2, tzinfo=UTC),
        plan_reader=lambda _path: approval,
        active_reader=lambda *_args, **_kwargs: _active(config, approval),
    )

    assert result.outcome == "succeeded"
    assert result.event.details["inventory_change_file_count"] == 3
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=TARGET,
    ) as journal:
        assert unresolved_started_event(journal.read_events()) is None


def test_recovery_never_writes_and_classifies_untouched_or_partial_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config, approval, automation = _fixture(tmp_path)
    _reserve(monkeypatch, config, approval, automation)

    result = recover_market_intelligence_apply(
        config=config,
        clock=lambda: datetime(2026, 8, 28, 21, 2, tzinfo=UTC),
        plan_reader=lambda _path: approval,
        active_reader=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            MarketIntelligencePublicationError("absent")
        ),
        inventory_reader=lambda _root: CURRENT_STATE,
        consumer_reader=lambda _root: CONSUMER_STATE,
    )
    assert result.outcome == "recovered_not_completed"
    assert result.as_dict()["production_write_count_by_custody"] == 0

    config2, approval2, automation2 = _fixture(tmp_path / "partial")
    _reserve(monkeypatch, config2, approval2, automation2)
    Path(approval2.target_path).mkdir(parents=True)
    blocked = recover_market_intelligence_apply(
        config=config2,
        clock=lambda: datetime(2026, 8, 28, 21, 2, tzinfo=UTC),
        plan_reader=lambda _path: approval2,
        active_reader=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            MarketIntelligencePublicationError("inactive")
        ),
        inventory_reader=lambda _root: "9" * 64,
        consumer_reader=lambda _root: CONSUMER_STATE,
    )
    assert blocked.outcome == "recovery_blocked"
