"""Admin CLI for approved Dashboard Snapshot V2 publication."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from tip_api.contracts.market_data.v2.dashboard_snapshot import DashboardSnapshotApprovalPlanV2
from tip_api.persistence.parquet.dashboard_snapshot_active import (
    DashboardSnapshotPublicationError, build_approval_plan, current_state_fingerprint,
    publish_and_activate, read_active_dashboard_snapshot, rollback, validate_plan, verify_then_link,
)
from tip_api.persistence.parquet.dashboard_universe_activation_active import read_active_dashboard_universe_activation
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.private_dashboard_snapshot import build_private_dashboard_snapshot, deterministic_json_bytes

ROOT=Path("/data/trading-intelligence-platform")
REPO_ROOT=Path(__file__).resolve().parents[5]
LEGACY_ROOT=REPO_ROOT/"build/private-dashboard"
SESSION=datetime(2026,8,19,tzinfo=UTC).date()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_plan(path: Path, digest: str) -> DashboardSnapshotApprovalPlanV2:
    if not path.is_absolute() or not path.resolve(strict=True).is_relative_to(Path("/tmp")) or path.is_symlink():
        raise DashboardSnapshotPublicationError("approved plan must be a regular /tmp file")
    if _sha(path)!=digest: raise DashboardSnapshotPublicationError("approved plan SHA-256 mismatch")
    plan=DashboardSnapshotApprovalPlanV2.model_validate_json(path.read_text());validate_plan(plan);return plan


def _parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description="Build or publish a versioned Dashboard Snapshot V2.")
    p.add_argument("--approval-package",type=Path)
    p.add_argument("--output-root",type=Path)
    p.add_argument("--release-id")
    p.add_argument("--generated-at")
    p.add_argument("--apply",action="store_true")
    p.add_argument("--verify-then-link",action="store_true")
    p.add_argument("--approved-plan",type=Path)
    p.add_argument("--approved-plan-sha256")
    p.add_argument("--expected-current-state-fingerprint")
    return p


def main(argv: list[str]|None=None) -> int:
    args=_parser().parse_args(argv)
    approved_mode=args.apply or args.verify_then_link
    if approved_mode:
        if not all((args.approved_plan,args.approved_plan_sha256,args.expected_current_state_fingerprint)) or any((args.approval_package,args.output_root,args.release_id,args.generated_at)):
            _parser().error("approved operation requires plan, plan SHA-256, and expected current-state fingerprint only")
        plan=_load_plan(args.approved_plan,args.approved_plan_sha256)
        if plan.expected_current_state_fingerprint!=args.expected_current_state_fingerprint:
            raise DashboardSnapshotPublicationError("expected current-state fingerprint disagrees with plan")
        if args.apply:
            result=publish_and_activate(root=ROOT,legacy_root=LEGACY_ROOT,plan=plan,
                expected_current_state_fingerprint=args.expected_current_state_fingerprint,
                freshness_validator=_formal_freshness_gate)
        else:
            result=verify_then_link(root=ROOT,legacy_root=LEGACY_ROOT,plan=plan,
                expected_current_state_fingerprint=args.expected_current_state_fingerprint,
                freshness_validator=_formal_freshness_gate)
        print(json.dumps({"status":"completed","release_id":result.manifest.release_id,
                          "pointer_fingerprint":result.pointer.pointer_content_fingerprint if result.pointer else None},sort_keys=True))
        return 0
    if any((args.approved_plan,args.approved_plan_sha256,args.expected_current_state_fingerprint)):
        _parser().error("approval arguments require --apply or --verify-then-link")
    if args.approval_package is not None and args.output_root is None:
        _parser().error("--approval-package requires an explicit persistent --output-root under /tmp")
    generated=datetime.fromisoformat(args.generated_at.replace("Z","+00:00")) if args.generated_at else datetime.now(UTC)
    live_freshness = _formal_freshness()
    output=args.output_root
    temporary=None
    if output is None:
        temporary=tempfile.TemporaryDirectory(prefix="tip-dashboard-snapshot-v2-dryrun-",dir="/tmp")
        output=Path(temporary.name)
    if not output.is_absolute() or not output.resolve(strict=False).is_relative_to(Path("/tmp")):
        raise DashboardSnapshotPublicationError("dry-run output root must be under /tmp")
    activation=read_active_dashboard_universe_activation(ROOT,analysis_session=SESSION,validate_sources=True)
    candidate=build_private_dashboard_snapshot(data_root=ROOT,output_root=output,allowed_output_root=output,
        release_id=args.release_id,generated_at=generated,dashboard_activation=activation)
    manifest=candidate.manifest
    response={"status":"dry_run_ready","candidate_path":str(candidate.output_dir),
              "freshness_status":manifest.freshness_status,"session_lag":manifest.session_lag,
              "expected_latest_completed_session":manifest.expected_latest_completed_session,
              "actual_latest_completed_session":manifest.actual_latest_completed_session,
              "production_writes":0,"approval_package":None}
    if (
        live_freshness.freshness_status.value != "fresh" or live_freshness.session_lag != 0 or
        manifest.freshness_status != "fresh" or manifest.session_lag != 0
    ):
        response["status"]="stale_blocked"
        response["expected_latest_completed_session"] = (
            live_freshness.expected_latest_completed_session.isoformat()
            if live_freshness.expected_latest_completed_session else None
        )
        response["actual_latest_completed_session"] = (
            live_freshness.actual_latest_completed_session.isoformat()
            if live_freshness.actual_latest_completed_session else None
        )
        response["freshness_status"] = live_freshness.freshness_status.value
        response["session_lag"] = live_freshness.session_lag
        print(json.dumps(response,sort_keys=True));return 0
    plan=build_approval_plan(root=ROOT,legacy_root=LEGACY_ROOT,candidate=candidate.output_dir,
                             activation_logical_fingerprint=activation.manifest.logical_content_fingerprint,
                             generated_at=generated)
    response.update(plan=plan.model_dump(mode="json"),expected_current_state_fingerprint=plan.expected_current_state_fingerprint)
    if args.approval_package:
        package=args.approval_package
        if not package.is_absolute() or not package.resolve(strict=False).is_relative_to(Path("/tmp")) or package.exists():
            raise DashboardSnapshotPublicationError("approval package must be a new /tmp file")
        package.write_bytes(deterministic_json_bytes(plan.model_dump(mode="json")))
        with package.open("rb") as handle: os.fsync(handle.fileno())
        package.chmod(0o444); response["approval_package"]=str(package);response["approval_package_sha256"]=_sha(package)
    print(json.dumps(response,sort_keys=True));return 0


def _formal_freshness():
    from tip_api.services.market_calendar import ExchangeCalendar,evaluate_market_data_freshness
    sessions=CanonicalEodReadRepository(ROOT).list_sessions()
    actual=sorted(sessions,key=lambda item:item.session_date)[-1].session_date
    return evaluate_market_data_freshness(calendar=ExchangeCalendar(),actual_latest_completed_session=actual,checked_at=datetime.now(UTC))


def _formal_freshness_gate() -> None:
    value = _formal_freshness()
    if value.freshness_status.value!="fresh" or value.session_lag!=0:
        raise DashboardSnapshotPublicationError("Production snapshot apply blocked by stale EOD")


if __name__=="__main__":
    try: raise SystemExit(main())
    except DashboardSnapshotPublicationError as exc:
        print(str(exc),file=__import__("sys").stderr);raise SystemExit(1)
