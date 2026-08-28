"""Admin CLI for approved Dashboard Snapshot V2 publication."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.contracts.market_data.v2.dashboard_snapshot import (
    DashboardSnapshotApprovalPlanV2,
    DashboardSnapshotApprovalPlanV2_1,
    DashboardSnapshotApprovalPlanV2_2,
    DashboardSnapshotApprovalPlanV2_3,
    DashboardSnapshotApprovalPlanV2_4,
)
from tip_api.contracts.analytics.v1 import (
    REVIEW_ACKNOWLEDGEMENT,
    ReviewDeploymentAuthorizationV1,
    approved_review_authorization,
)
from tip_api.persistence.parquet.dashboard_snapshot_active import (
    DashboardSnapshotPublicationError, build_approval_plan, current_state_fingerprint,
    publish_and_activate, read_active_dashboard_snapshot, rollback, validate_plan, verify_then_link,
)
from tip_api.persistence.parquet.dashboard_universe_activation_active import (
    read_active_dashboard_universe_activation,
    read_dashboard_universe_activation_pointer,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.market_intelligence_active import read_active_market_intelligence
from tip_api.services.private_dashboard_snapshot import build_private_dashboard_snapshot, deterministic_json_bytes

ROOT=Path("/data/trading-intelligence-platform")
REPO_ROOT=Path(__file__).resolve().parents[5]
LEGACY_ROOT=REPO_ROOT/"build/private-dashboard"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_plan(path: Path, digest: str) -> DashboardSnapshotApprovalPlanV2 | DashboardSnapshotApprovalPlanV2_1 | DashboardSnapshotApprovalPlanV2_2 | DashboardSnapshotApprovalPlanV2_3 | DashboardSnapshotApprovalPlanV2_4:
    if not path.is_absolute() or not path.resolve(strict=True).is_relative_to(Path("/tmp")) or path.is_symlink():
        raise DashboardSnapshotPublicationError("approved plan must be a regular /tmp file")
    if _sha(path)!=digest: raise DashboardSnapshotPublicationError("approved plan SHA-256 mismatch")
    value=json.loads(path.read_text())
    plan_type={
        "2.0": DashboardSnapshotApprovalPlanV2,
        "2.1": DashboardSnapshotApprovalPlanV2_1,
        "2.2": DashboardSnapshotApprovalPlanV2_2,
        "2.3": DashboardSnapshotApprovalPlanV2_3,
        "2.4": DashboardSnapshotApprovalPlanV2_4,
    }.get(value.get("plan_version"))
    if plan_type is None:
        raise DashboardSnapshotPublicationError("unsupported snapshot plan version")
    plan=plan_type.model_validate(value);validate_plan(plan);return plan


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
    p.add_argument("--market-intelligence-publication-id")
    p.add_argument("--analysis-session",type=date.fromisoformat)
    p.add_argument("--review-deployment",action="store_true")
    p.add_argument("--review-approved-as-of-session",type=date.fromisoformat)
    p.add_argument("--review-expected-latest-session",type=date.fromisoformat)
    p.add_argument("--review-expected-lag-sessions",type=int)
    p.add_argument("--review-acknowledgement")
    return p


def main(argv: list[str]|None=None) -> int:
    args=_parser().parse_args(argv)
    approved_mode=args.apply or args.verify_then_link
    if approved_mode:
        if not all((args.approved_plan,args.approved_plan_sha256,args.expected_current_state_fingerprint,args.analysis_session)) or any((args.approval_package,args.output_root,args.release_id,args.generated_at,args.market_intelligence_publication_id,args.review_deployment,args.review_approved_as_of_session,args.review_expected_latest_session,args.review_expected_lag_sessions)):
            _parser().error("approved operation requires plan, plan SHA-256, analysis session and expected current-state fingerprint only")
        plan=_load_plan(args.approved_plan,args.approved_plan_sha256)
        if plan.expected_current_state_fingerprint!=args.expected_current_state_fingerprint or plan.analysis_session!=args.analysis_session:
            raise DashboardSnapshotPublicationError("expected current-state fingerprint disagrees with plan")
        freshness_validator=_approved_freshness_validator(plan,args)
        freshness_validator()
        if args.apply:
            result=publish_and_activate(root=ROOT,legacy_root=LEGACY_ROOT,plan=plan,
                expected_current_state_fingerprint=args.expected_current_state_fingerprint,
                freshness_validator=freshness_validator)
        else:
            result=verify_then_link(root=ROOT,legacy_root=LEGACY_ROOT,plan=plan,
                expected_current_state_fingerprint=args.expected_current_state_fingerprint,
                freshness_validator=freshness_validator)
        print(json.dumps({"status":"completed","release_id":result.manifest.release_id,
                          "pointer_fingerprint":result.pointer.pointer_content_fingerprint if result.pointer else None},sort_keys=True))
        return 0
    if any((args.approved_plan,args.approved_plan_sha256,args.expected_current_state_fingerprint)):
        _parser().error("approval arguments require --apply or --verify-then-link")
    if args.analysis_session is None:
        _parser().error("dry-run requires an explicit --analysis-session")
    review=_review_authorization_from_args(args)
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
    activation_pointer=read_dashboard_universe_activation_pointer(ROOT)
    if activation_pointer is None:
        raise DashboardSnapshotPublicationError("Activation V2 pointer is required")
    activation=read_active_dashboard_universe_activation(
        ROOT,analysis_session=activation_pointer.active.analysis_session,validate_sources=True
    )
    market_intelligence = None
    if args.market_intelligence_publication_id:
        market_intelligence = read_active_market_intelligence(ROOT, validate_sources=True)
        if market_intelligence.payload.publication_id != args.market_intelligence_publication_id:
            raise DashboardSnapshotPublicationError(
                "explicit Market Intelligence publication is not the active formal release"
            )
        if market_intelligence.payload.analysis_session != args.analysis_session:
            raise DashboardSnapshotPublicationError(
                "Market Intelligence analysis session differs from explicit snapshot session"
            )
        if market_intelligence.payload.review_deployment != review:
            raise DashboardSnapshotPublicationError(
                "snapshot review authorization differs from active Market Intelligence"
            )
    candidate=build_private_dashboard_snapshot(data_root=ROOT,output_root=output,allowed_output_root=output,
        release_id=args.release_id,generated_at=generated,dashboard_activation=activation,
        market_intelligence=market_intelligence)
    manifest=candidate.manifest
    response={"status":"dry_run_ready","candidate_path":str(candidate.output_dir),
              "freshness_status":manifest.freshness_status,"session_lag":manifest.session_lag,
              "expected_latest_completed_session":manifest.expected_latest_completed_session,
              "actual_latest_completed_session":manifest.actual_latest_completed_session,
              "production_writes":0,"approval_package":None}
    normal_ready = (
        live_freshness.freshness_status.value == "fresh" and live_freshness.session_lag == 0
        and manifest.freshness_status == "fresh" and manifest.session_lag == 0
    )
    review_ready = review is not None and (
        live_freshness.actual_latest_completed_session == review.approved_as_of_session
        and live_freshness.expected_latest_completed_session == review.expected_latest_session
        and live_freshness.session_lag == review.expected_lag_sessions
        and live_freshness.freshness_status.value == "stale"
        and manifest.review_mode
    )
    if not (normal_ready or review_ready):
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


def _review_authorization_from_args(args: argparse.Namespace) -> ReviewDeploymentAuthorizationV1 | None:
    values=(args.review_approved_as_of_session,args.review_expected_latest_session,
            args.review_expected_lag_sessions,args.review_acknowledgement)
    if args.review_deployment != all(value is not None for value in values):
        raise DashboardSnapshotPublicationError(
            "review snapshot requires all exact authorization bindings"
        )
    if not args.review_deployment:
        return None
    try:
        return approved_review_authorization(
            approved_as_of_session=args.review_approved_as_of_session,
            expected_latest_session=args.review_expected_latest_session,
            expected_lag_sessions=args.review_expected_lag_sessions,
            explicit_user_acknowledgement=args.review_acknowledgement,
        )
    except ValueError as exc:
        raise DashboardSnapshotPublicationError(str(exc)) from exc


def _approved_freshness_validator(plan: DashboardSnapshotApprovalPlanV2,args: argparse.Namespace):
    if plan.normal_freshness:
        if args.review_acknowledgement is not None:
            raise DashboardSnapshotPublicationError(
                "fresh snapshot cannot use review acknowledgement"
            )
        return _formal_freshness_gate
    review=plan.review_deployment
    if (not plan.activation_allowed_by_review_authorization or review is None
        or args.review_acknowledgement != REVIEW_ACKNOWLEDGEMENT
        or args.review_acknowledgement != review.explicit_user_acknowledgement):
        raise DashboardSnapshotPublicationError(
            "approved stale review requires the exact explicit acknowledgement"
        )
    def gate() -> None:
        value=_formal_freshness()
        if (value.actual_latest_completed_session != review.approved_as_of_session
            or value.expected_latest_completed_session != review.expected_latest_session
            or value.session_lag != review.expected_lag_sessions
            or value.freshness_status.value != "stale"
            or plan.analysis_session != review.approved_as_of_session):
            raise DashboardSnapshotPublicationError(
                "formal freshness no longer matches the exact snapshot review authorization"
            )
    return gate


if __name__=="__main__":
    try: raise SystemExit(main())
    except DashboardSnapshotPublicationError as exc:
        print(str(exc),file=__import__("sys").stderr);raise SystemExit(1)
