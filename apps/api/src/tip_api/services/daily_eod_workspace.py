"""Deterministic persistent workspace layout for distinct daily EOD wakes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from tip_api.services.market_calendar import ExchangeCalendar

if TYPE_CHECKING:
    from tip_api.services.daily_eod_automation import DailyEodAutomationPaths


CONTRACT_VERSION = "daily-eod-workspace-layout/1.0"


class DailyEodWorkspaceError(RuntimeError):
    """Raised when a persistent daily workspace path is unsafe or ambiguous."""


@dataclass(frozen=True, slots=True)
class DailyEodWorkspaceLayout:
    contract_version: str
    workspace_root: Path
    data_root: Path
    repository_root: Path
    target_session: date
    prior_session: date
    session_root: Path
    prior_session_root: Path
    run_root: Path
    panel_cache_root: Path
    package_path: Path
    canonical_apply_plan: Path
    candidate_work_dir: Path
    phase1a_audit: Path
    prior_phase1b_audit: Path
    phase1b_audit: Path
    prior_candidate_audit: Path
    candidate_audit: Path
    entry_geometry_audit: Path
    phase2_audit: Path
    preview_bundle: Path
    strategy_channel_audit: Path
    market_intelligence_output_root: Path
    market_intelligence_approval_plan: Path
    snapshot_output_root: Path
    snapshot_approval_plan: Path
    serving_bundle_root: Path
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))  # type: ignore[return-value]

    def as_automation_paths(self) -> "DailyEodAutomationPaths":
        from tip_api.services.daily_eod_automation import DailyEodAutomationPaths

        return DailyEodAutomationPaths(
            data_root=self.data_root,
            phase1a_audit=self.phase1a_audit,
            prior_phase1b_audit=self.prior_phase1b_audit,
            phase1b_audit=self.phase1b_audit,
            prior_candidate_audit=self.prior_candidate_audit,
            candidate_audit=self.candidate_audit,
            entry_geometry_audit=self.entry_geometry_audit,
            phase2_audit=self.phase2_audit,
            preview_bundle=self.preview_bundle,
            strategy_channel_audit=self.strategy_channel_audit,
            market_intelligence_output_root=self.market_intelligence_output_root,
            market_intelligence_approval_plan=self.market_intelligence_approval_plan,
            snapshot_output_root=self.snapshot_output_root,
            snapshot_approval_plan=self.snapshot_approval_plan,
            serving_bundle_root=self.serving_bundle_root,
        )


def derive_daily_eod_workspace_layout(
    *,
    workspace_root: Path,
    data_root: Path,
    repository_root: Path,
    target_session: date,
    prior_session: date,
) -> DailyEodWorkspaceLayout:
    """Derive paths only; never create or modify the workspace."""

    _validate_roots(
        workspace_root=workspace_root,
        data_root=data_root,
        repository_root=repository_root,
    )
    calendar = ExchangeCalendar()
    if (
        not calendar.is_session(target_session)
        or calendar.previous_session(target_session) != prior_session
    ):
        raise DailyEodWorkspaceError(
            "daily workspace requires adjacent XNYS target and prior sessions"
        )
    session_root = _session_root(workspace_root, target_session)
    prior_root = _session_root(workspace_root, prior_session)
    base: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "workspace_root": workspace_root,
        "data_root": data_root,
        "repository_root": repository_root,
        "target_session": target_session,
        "prior_session": prior_session,
        "session_root": session_root,
        "prior_session_root": prior_root,
        "run_root": workspace_root / "journal",
        "panel_cache_root": workspace_root / "cache" / "panels",
        "package_path": session_root / "acquisition-package",
        "canonical_apply_plan": session_root / "canonical-apply-plan.json",
        "candidate_work_dir": session_root / "candidate-work",
        "phase1a_audit": session_root / "market-regime-phase1a",
        "prior_phase1b_audit": prior_root / "market-regime-phase1b",
        "phase1b_audit": session_root / "market-regime-phase1b",
        "prior_candidate_audit": prior_root / "opportunity-candidate",
        "candidate_audit": session_root / "opportunity-candidate",
        "entry_geometry_audit": session_root / "entry-geometry",
        "phase2_audit": session_root / "etf-relationships",
        "preview_bundle": session_root / "market-preview",
        "strategy_channel_audit": session_root / "strategy-channels",
        "market_intelligence_output_root": session_root / "market-intelligence",
        "market_intelligence_approval_plan": (
            session_root / "market-intelligence-plan.json"
        ),
        "snapshot_output_root": session_root / "dashboard-snapshot",
        "snapshot_approval_plan": session_root / "dashboard-snapshot-plan.json",
        "serving_bundle_root": session_root / "serving-bundle",
    }
    logical = _jsonable(base)
    return DailyEodWorkspaceLayout(
        **base,
        logical_content_fingerprint=_fingerprint(logical),
    )


def verify_daily_eod_workspace_layout(layout: DailyEodWorkspaceLayout) -> None:
    """Re-derive and compare the complete layout and content fingerprint."""

    if not isinstance(layout, DailyEodWorkspaceLayout):
        raise DailyEodWorkspaceError("daily workspace layout contract is invalid")
    expected = derive_daily_eod_workspace_layout(
        workspace_root=layout.workspace_root,
        data_root=layout.data_root,
        repository_root=layout.repository_root,
        target_session=layout.target_session,
        prior_session=layout.prior_session,
    )
    if layout != expected:
        raise DailyEodWorkspaceError("daily workspace layout content differs")


def validate_workspace_automation_paths(paths: "DailyEodAutomationPaths") -> None:
    """Accept only the exact per-session portion of a persistent layout."""

    current_root = paths.phase1a_audit.parent
    if (
        not current_root.name.startswith("session_date=")
        or current_root.parent.name != "sessions"
    ):
        raise DailyEodWorkspaceError("daily workspace session root is malformed")
    prior_root = paths.prior_phase1b_audit.parent
    if (
        not prior_root.name.startswith("session_date=")
        or prior_root.parent != current_root.parent
        or paths.prior_candidate_audit.parent != prior_root
    ):
        raise DailyEodWorkspaceError("daily workspace prior-session root is malformed")
    try:
        target = date.fromisoformat(current_root.name.removeprefix("session_date="))
        prior = date.fromisoformat(prior_root.name.removeprefix("session_date="))
    except ValueError as exc:
        raise DailyEodWorkspaceError(
            "daily workspace session date is malformed"
        ) from exc
    workspace_root = current_root.parent.parent
    if _inside_git_repository(workspace_root):
        raise DailyEodWorkspaceError(
            "daily workspace must be outside a Git repository"
        )
    repository_placeholder = workspace_root.parent / ".repository-boundary"
    expected = derive_daily_eod_workspace_layout(
        workspace_root=workspace_root,
        data_root=paths.data_root,
        repository_root=repository_placeholder,
        target_session=target,
        prior_session=prior,
    ).as_automation_paths()
    if paths != expected:
        raise DailyEodWorkspaceError("daily workspace artifact paths differ")


def _validate_roots(
    *,
    workspace_root: Path,
    data_root: Path,
    repository_root: Path,
) -> None:
    roots = (workspace_root, data_root, repository_root)
    if any(not item.is_absolute() for item in roots):
        raise DailyEodWorkspaceError("daily workspace roots must be absolute")
    if workspace_root == Path("/") or _is_within(workspace_root, Path("/tmp")):
        raise DailyEodWorkspaceError("daily workspace root is too broad or ephemeral")
    if (
        _paths_overlap(workspace_root, data_root)
        or _paths_overlap(workspace_root, repository_root)
    ):
        raise DailyEodWorkspaceError(
            "daily workspace must be outside data and repository roots"
        )
    if workspace_root.resolve() != workspace_root:
        raise DailyEodWorkspaceError("daily workspace root cannot use a symlink")


def _session_root(workspace_root: Path, session: date) -> Path:
    return workspace_root / "sessions" / f"session_date={session.isoformat()}"


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _inside_git_repository(path: Path) -> bool:
    return any(
        (candidate / ".git").exists()
        for candidate in (path, *path.parents)
    )


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
