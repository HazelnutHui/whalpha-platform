from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services.daily_eod_automation import (
    DailyEodAutomationError,
    PlanStatus,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_pipeline_scheduler import (
    PipelineWakeStatus,
    plan_daily_eod_pipeline_wake,
)
from tip_api.services.daily_eod_workspace import (
    CONTRACT_VERSION,
    DailyEodWorkspaceError,
    derive_daily_eod_workspace_layout,
    verify_daily_eod_workspace_layout,
)


TARGET = date(2026, 8, 28)
PRIOR = date(2026, 8, 27)


def _layout(tmp_path: Path):
    return derive_daily_eod_workspace_layout(
        workspace_root=(
            Path("/home/hui/.local/state")
            / f"whalpha-test-{tmp_path.name}"
            / "daily-eod"
        ),
        data_root=tmp_path / "data",
        repository_root=tmp_path / "repo",
        target_session=TARGET,
        prior_session=PRIOR,
    )


def test_layout_is_deterministic_session_partitioned_and_write_free(tmp_path) -> None:
    before = tuple(tmp_path.rglob("*"))
    layout = _layout(tmp_path)

    assert layout.contract_version == CONTRACT_VERSION
    assert layout.session_root.name == "session_date=2026-08-28"
    assert layout.prior_session_root.name == "session_date=2026-08-27"
    assert layout.phase1b_audit.parent == layout.session_root
    assert layout.prior_phase1b_audit.parent == layout.prior_session_root
    assert layout.run_root == layout.workspace_root / "journal"
    assert layout.panel_cache_root == layout.workspace_root / "cache" / "panels"
    assert len(layout.logical_content_fingerprint) == 64
    assert tuple(tmp_path.rglob("*")) == before
    verify_daily_eod_workspace_layout(layout)


def test_workspace_paths_are_accepted_by_existing_automation_plan(tmp_path) -> None:
    layout = _layout(tmp_path)

    plan = plan_daily_eod_automation(
        target_session=TARGET,
        paths=layout.as_automation_paths(),
    )

    assert plan.status is PlanStatus.WAITING_FOR_AUTHORIZED_INPUT
    assert plan.reason_codes == ("identity_required",)

    wake = plan_daily_eod_pipeline_wake(
        checked_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
        completed_sessions=(PRIOR, TARGET),
        latest_pipeline_plan=plan,
    )
    assert wake.status is PipelineWakeStatus.BLOCKED


def test_current_canonical_workspace_blocks_before_unproven_real_cli_custody(
    monkeypatch,
    tmp_path,
) -> None:
    layout = _layout(tmp_path)
    paths = layout.as_automation_paths()
    identity_path = (
        paths.data_root
        / "market-data/snapshots/instrument-master/as_of_date=2026-08-28"
    )
    eod_path = (
        paths.data_root
        / "market-data/eod-price-bars/schema_version=1/session_date=2026-08-28"
    )
    monkeypatch.setattr(
        "tip_api.services.daily_eod_automation._lexists",
        lambda path: path in {identity_path, eod_path},
    )
    monkeypatch.setattr(
        "tip_api.services.daily_eod_automation.load_identity_snapshot",
        lambda *args, **kwargs: SimpleNamespace(
            as_of_date=TARGET,
            manifest={"snapshot_content_sha256": "a" * 64},
        ),
    )

    class EodRepository:
        def __init__(self, root):
            self.root = root

        def inspect_session(self, session):
            return SimpleNamespace(
                session_date=session,
                content_fingerprint="b" * 64,
                identity_snapshot_fingerprint="a" * 64,
            )

    monkeypatch.setattr(
        "tip_api.services.daily_eod_automation.CanonicalEodReadRepository",
        EodRepository,
    )

    plan = plan_daily_eod_automation(target_session=TARGET, paths=paths)

    assert plan.status is PlanStatus.BLOCKED
    assert plan.reason_codes == (
        "persistent_workspace_cli_custody_unreconciled",
    )


def test_workspace_layout_rejects_overlap_and_ephemeral_root(tmp_path) -> None:
    with pytest.raises(DailyEodWorkspaceError, match="outside"):
        derive_daily_eod_workspace_layout(
            workspace_root=Path("/home/hui/.local/state/overlap-data/work"),
            data_root=Path("/home/hui/.local/state/overlap-data"),
            repository_root=tmp_path / "repo",
            target_session=TARGET,
            prior_session=PRIOR,
        )
    with pytest.raises(DailyEodWorkspaceError, match="ephemeral"):
        derive_daily_eod_workspace_layout(
            workspace_root=Path("/tmp"),
            data_root=tmp_path / "data",
            repository_root=tmp_path / "repo",
            target_session=TARGET,
            prior_session=PRIOR,
        )


def test_workspace_layout_tamper_is_rejected(tmp_path) -> None:
    layout = _layout(tmp_path)

    with pytest.raises(DailyEodWorkspaceError, match="differs"):
        verify_daily_eod_workspace_layout(
            replace(layout, candidate_audit=layout.session_root / "changed")
        )


def test_workspace_layout_rejects_nonadjacent_prior_session(tmp_path) -> None:
    with pytest.raises(DailyEodWorkspaceError, match="adjacent XNYS"):
        derive_daily_eod_workspace_layout(
            workspace_root=(
                Path("/home/hui/.local/state")
                / f"whalpha-test-{tmp_path.name}"
                / "daily-eod"
            ),
            data_root=tmp_path / "data",
            repository_root=tmp_path / "repo",
            target_session=TARGET,
            prior_session=date(2026, 8, 26),
        )


def test_workspace_automation_path_tamper_is_rejected(tmp_path) -> None:
    layout = _layout(tmp_path)
    paths = replace(
        layout.as_automation_paths(),
        phase1a_audit=layout.session_root / "changed",
    )

    with pytest.raises(DailyEodAutomationError, match="persistent workspace layout"):
        plan_daily_eod_automation(target_session=TARGET, paths=paths)
