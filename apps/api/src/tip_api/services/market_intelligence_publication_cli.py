"""Offline, approval-bound Market Intelligence publication administrator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.contracts.analytics.v1 import (
    REVIEW_ACKNOWLEDGEMENT,
    MarketIntelligenceApprovalPlanV1,
    MarketIntelligenceApprovalPlanV1_1,
    MarketIntelligenceApprovalPlanV1_2,
    ReviewDeploymentAuthorizationV1,
    approved_review_authorization,
)
from tip_api.contracts.analytics.v1.market_intelligence import MARKET_INTELLIGENCE_REVISION
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.market_intelligence_active import (
    MarketIntelligencePublicationError,
    build_approval_plan,
    build_market_intelligence_candidate,
    canonical_bytes,
    publish_and_activate,
    rollback,
    validate_plan,
    verify_then_link,
)
from tip_api.services.market_calendar import ExchangeCalendar, evaluate_market_data_freshness


DEFAULT_ROOT = Path("/data/trading-intelligence-platform")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build, verify, publish, or roll back immutable Market Intelligence."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify-then-link", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--analysis-session", type=date.fromisoformat)
    parser.add_argument("--revision")
    parser.add_argument("--preview-bundle", type=Path)
    parser.add_argument("--phase1a-audit", type=Path)
    parser.add_argument("--phase1b-audit", type=Path)
    parser.add_argument("--phase2-audit", type=Path)
    parser.add_argument("--candidate-audit", type=Path)
    parser.add_argument("--entry-geometry-audit", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--approval-package", type=Path)
    parser.add_argument("--publication-id")
    parser.add_argument("--created-at")
    parser.add_argument("--approved-plan", type=Path)
    parser.add_argument("--approved-plan-sha256")
    parser.add_argument("--expected-current-state-fingerprint")
    parser.add_argument("--expected-active-pointer-fingerprint")
    parser.add_argument("--rollback-apply", action="store_true")
    parser.add_argument("--review-deployment", action="store_true")
    parser.add_argument("--review-approved-as-of-session", type=date.fromisoformat)
    parser.add_argument("--review-expected-latest-session", type=date.fromisoformat)
    parser.add_argument("--review-expected-lag-sessions", type=int)
    parser.add_argument("--review-acknowledgement")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not args.data_root.is_absolute() or args.data_root != DEFAULT_ROOT:
        parser.error("--data-root must be the exact formal data root")

    with _socket_guard():
        if args.plan:
            _require_plan_arguments(parser, args)
            return _plan(args)
        if args.rollback:
            _require_rollback_arguments(parser, args)
            result = rollback(
                root=args.data_root,
                expected_active_pointer_fingerprint=args.expected_active_pointer_fingerprint,
                apply=args.rollback_apply,
            )
            print(
                json.dumps(
                    {
                        "status": "rollback_applied" if args.rollback_apply else "rollback_dry_run",
                        "publication_id": result.payload.publication_id,
                        "production_write_count": 1 if args.rollback_apply else 0,
                    },
                    sort_keys=True,
                )
            )
            return 0
        _require_approved_arguments(parser, args)
        plan = _load_plan(args.approved_plan, args.approved_plan_sha256)
        if (
            plan.analysis_session != args.analysis_session
            or plan.revision != args.revision
            or plan.expected_current_state_fingerprint
            != args.expected_current_state_fingerprint
        ):
            raise MarketIntelligencePublicationError("CLI bindings disagree with approved plan")
        freshness_validator = _approved_freshness_validator(args.data_root, plan, args)
        freshness_validator()
        operation = verify_then_link if args.verify_then_link else publish_and_activate
        result = operation(
            root=args.data_root,
            plan=plan,
            expected_current_state_fingerprint=args.expected_current_state_fingerprint,
            freshness_validator=freshness_validator,
        )
        print(
            json.dumps(
                {
                    "status": "completed",
                    "operation": "verify_then_link" if args.verify_then_link else "apply",
                    "publication_id": result.payload.publication_id,
                    "pointer_fingerprint": (
                        result.pointer.pointer_content_fingerprint if result.pointer else None
                    ),
                },
                sort_keys=True,
            )
        )
        return 0


def _plan(args: argparse.Namespace) -> int:
    created_at = _parse_utc(args.created_at)
    output = _new_tmp_directory(args.output_root)
    publication_id = args.publication_id or (
        f"{args.analysis_session.isoformat()}T{created_at.strftime('%H%M%S')}Z-"
        f"{_repo_head_short()}"
    )
    candidate = output / "market-intelligence.plan.artifacts"
    review = _review_authorization_from_plan_args(args)
    completed = build_market_intelligence_candidate(
        data_root=args.data_root,
        analysis_session=args.analysis_session,
        publication_id=publication_id,
        generated_at=created_at,
        preview_bundle_path=args.preview_bundle,
        phase1a_audit_path=args.phase1a_audit,
        phase1b_audit_path=args.phase1b_audit,
        phase2_audit_path=args.phase2_audit,
        candidate_audit_path=args.candidate_audit,
        entry_geometry_audit_path=args.entry_geometry_audit,
        candidate_path=candidate,
        review_deployment=review,
    )
    freshness = _freshness(args.data_root, created_at)
    plan = build_approval_plan(
        root=args.data_root,
        candidate=completed.path,
        preview_bundle_path=args.preview_bundle,
        phase1a_audit_path=args.phase1a_audit,
        phase1b_audit_path=args.phase1b_audit,
        phase2_audit_path=args.phase2_audit,
        candidate_audit_path=args.candidate_audit,
        entry_geometry_audit_path=args.entry_geometry_audit,
        expected_current_state_fingerprint=args.expected_current_state_fingerprint,
        expected_latest_completed_session=freshness.expected_latest_completed_session,
        actual_latest_completed_session=freshness.actual_latest_completed_session,
        freshness_status=freshness.freshness_status.value,
        session_lag=freshness.session_lag,
        created_at=created_at,
    )
    raw = canonical_bytes(plan.model_dump(mode="json"))
    plan_path = args.approval_package
    _new_tmp_file(plan_path, raw, 0o444)
    response = {
        "status": (
            "dry_run_ready"
            if plan.activation_allowed or plan.activation_allowed_by_review_authorization
            else "freshness_blocked"
        ),
        "production_write_count": 0,
        "candidate_path": str(completed.path),
        "approval_package": str(plan_path),
        "approval_package_bytes": len(raw),
        "approval_package_sha256": hashlib.sha256(raw).hexdigest(),
        "plan_content_fingerprint": plan.plan_content_fingerprint,
        "publication_id": plan.publication_id,
        "target_path": plan.target_path,
        "pointer_path": plan.pointer_path,
        "payload_sha256": plan.payload_sha256,
        "manifest_sha256": plan.manifest_sha256,
        "planned_pointer_fingerprint": plan.planned_pointer_fingerprint,
        "expected_current_state_fingerprint": plan.expected_current_state_fingerprint,
        "actual_latest_completed_session": plan.actual_latest_completed_session.isoformat(),
        "expected_latest_completed_session": (
            plan.expected_latest_completed_session.isoformat()
            if plan.expected_latest_completed_session
            else None
        ),
        "freshness_status": plan.freshness_status,
        "session_lag": plan.session_lag,
        "review_mode": plan.review_mode,
        "normal_freshness": plan.normal_freshness,
        "activation_allowed_by_review_authorization": (
            plan.activation_allowed_by_review_authorization
        ),
    }
    print(json.dumps(response, sort_keys=True))
    return 0


def _require_plan_arguments(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    required = (
        args.analysis_session,
        args.revision,
        args.preview_bundle,
        args.phase1a_audit,
        args.phase1b_audit,
        args.phase2_audit,
        args.candidate_audit,
        args.output_root,
        args.approval_package,
        args.expected_current_state_fingerprint,
        args.created_at,
    )
    if not all(required) or args.revision != MARKET_INTELLIGENCE_REVISION:
        parser.error("--plan requires all explicit source, session, revision, output and state bindings")
    if any((args.approved_plan, args.approved_plan_sha256, args.expected_active_pointer_fingerprint)):
        parser.error("approved operation arguments cannot be combined with --plan")
    review_values = (
        args.review_approved_as_of_session,
        args.review_expected_latest_session,
        args.review_expected_lag_sessions,
        args.review_acknowledgement,
    )
    if args.review_deployment != all(value is not None for value in review_values):
        parser.error("review plan requires all exact review authorization bindings")
    if any(value is not None for value in review_values) and not args.review_deployment:
        parser.error("review authorization bindings require --review-deployment")


def _require_approved_arguments(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not all(
        (
            args.analysis_session,
            args.revision,
            args.approved_plan,
            args.approved_plan_sha256,
            args.expected_current_state_fingerprint,
        )
    ):
        parser.error("approved operation requires plan, full-file SHA, session, revision and state")
    forbidden = (
        args.preview_bundle,
        args.phase1a_audit,
        args.phase1b_audit,
        args.phase2_audit,
        args.candidate_audit,
        args.entry_geometry_audit,
        args.output_root,
        args.approval_package,
        args.publication_id,
        args.created_at,
        args.expected_active_pointer_fingerprint,
        args.rollback_apply,
        args.review_deployment,
        args.review_approved_as_of_session,
        args.review_expected_latest_session,
        args.review_expected_lag_sessions,
    )
    if any(forbidden) or args.revision != MARKET_INTELLIGENCE_REVISION:
        parser.error("approved operation has conflicting or invalid arguments")


def _require_rollback_arguments(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not args.expected_active_pointer_fingerprint:
        parser.error("rollback requires the approved active pointer fingerprint")
    forbidden = (
        args.analysis_session,
        args.revision,
        args.preview_bundle,
        args.phase1a_audit,
        args.phase1b_audit,
        args.phase2_audit,
        args.candidate_audit,
        args.entry_geometry_audit,
        args.output_root,
        args.approval_package,
        args.publication_id,
        args.created_at,
        args.approved_plan,
        args.approved_plan_sha256,
        args.expected_current_state_fingerprint,
        args.review_deployment,
        args.review_approved_as_of_session,
        args.review_expected_latest_session,
        args.review_expected_lag_sessions,
        args.review_acknowledgement,
    )
    if any(forbidden):
        parser.error("rollback only accepts its approved pointer digest")


def _load_plan(
    path: Path, expected_sha256: str
) -> MarketIntelligenceApprovalPlanV1 | MarketIntelligenceApprovalPlanV1_1 | MarketIntelligenceApprovalPlanV1_2:
    if (
        not path.is_absolute()
        or not path.resolve(strict=True).is_relative_to(Path("/tmp"))
        or path.is_symlink()
        or not path.is_file()
    ):
        raise MarketIntelligencePublicationError("approved plan must be a regular /tmp file")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise MarketIntelligencePublicationError("approved plan full-file SHA-256 mismatch")
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise MarketIntelligencePublicationError("approved plan JSON is malformed") from exc
    if canonical_bytes(value) != raw:
        raise MarketIntelligencePublicationError("approved plan JSON is non-canonical")
    plan_type = {
        "1.0": MarketIntelligenceApprovalPlanV1,
        "1.1": MarketIntelligenceApprovalPlanV1_1,
        "1.2": MarketIntelligenceApprovalPlanV1_2,
    }.get(value.get("plan_version"))
    if plan_type is None:
        raise MarketIntelligencePublicationError("unsupported Market Intelligence plan version")
    plan = plan_type.model_validate(value)
    validate_plan(plan)
    return plan


def _freshness(root: Path, checked_at: datetime):
    sessions = CanonicalEodReadRepository(root).list_sessions()
    if not sessions:
        raise MarketIntelligencePublicationError("no completed EOD session exists")
    actual = max(item.session_date for item in sessions)
    return evaluate_market_data_freshness(
        calendar=ExchangeCalendar(), actual_latest_completed_session=actual, checked_at=checked_at
    )


def _freshness_gate(root: Path) -> None:
    value = _freshness(root, datetime.now(UTC))
    if value.freshness_status.value != "fresh" or value.session_lag != 0:
        raise MarketIntelligencePublicationError(
            "Market Intelligence activation is blocked by stale EOD freshness"
        )


def _review_authorization_from_plan_args(
    args: argparse.Namespace,
) -> ReviewDeploymentAuthorizationV1 | None:
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
        raise MarketIntelligencePublicationError(str(exc)) from exc


def _approved_freshness_validator(
    root: Path,
    plan: MarketIntelligenceApprovalPlanV1,
    args: argparse.Namespace,
):
    if plan.activation_allowed:
        if args.review_acknowledgement is not None:
            raise MarketIntelligencePublicationError(
                "fresh publication cannot use review acknowledgement"
            )
        return lambda: _freshness_gate(root)
    review = plan.review_deployment
    if (
        not plan.activation_allowed_by_review_authorization
        or review is None
        or args.review_acknowledgement != REVIEW_ACKNOWLEDGEMENT
        or args.review_acknowledgement != review.explicit_user_acknowledgement
    ):
        raise MarketIntelligencePublicationError(
            "approved stale review requires the exact explicit acknowledgement"
        )

    def gate() -> None:
        value = _freshness(root, datetime.now(UTC))
        if (
            value.actual_latest_completed_session != review.approved_as_of_session
            or value.expected_latest_completed_session != review.expected_latest_session
            or value.session_lag != review.expected_lag_sessions
            or value.freshness_status.value != "stale"
            or plan.analysis_session != review.approved_as_of_session
        ):
            raise MarketIntelligencePublicationError(
                "formal freshness no longer matches the exact review authorization"
            )

    return gate


def _parse_utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() != UTC.utcoffset(result):
        raise MarketIntelligencePublicationError("--created-at must be an explicit UTC timestamp")
    return result.astimezone(UTC)


def _repo_head_short() -> str:
    head = Path(__file__).resolve().parents[5] / ".git" / "HEAD"
    value = head.read_text(encoding="ascii").strip()
    if value.startswith("ref: "):
        value = (head.parent / value[5:]).read_text(encoding="ascii").strip()
    if len(value) < 12 or any(character not in "0123456789abcdef" for character in value):
        raise MarketIntelligencePublicationError("repository HEAD is not a direct commit")
    return value[:12]


def _new_tmp_directory(path: Path) -> Path:
    if not path.is_absolute() or not path.is_relative_to(Path("/tmp")) or path.exists():
        raise MarketIntelligencePublicationError("output root must be a new absolute /tmp path")
    path.mkdir(mode=0o700, parents=False)
    return path


def _new_tmp_file(path: Path, raw: bytes, mode: int) -> None:
    if (
        not path.is_absolute()
        or not path.is_relative_to(Path("/tmp"))
        or path.exists()
        or path.parent.is_symlink()
        or not path.parent.is_dir()
    ):
        raise MarketIntelligencePublicationError("approval package must be a new /tmp file")
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    path.chmod(mode)


@contextmanager
def _socket_guard():
    original_socket = socket.socket
    original_connection = socket.create_connection

    class GuardedSocket(original_socket):
        def connect(self, address):  # type: ignore[no-untyped-def]
            raise MarketIntelligencePublicationError("network access is disabled")

        def connect_ex(self, address):  # type: ignore[no-untyped-def]
            raise MarketIntelligencePublicationError("network access is disabled")

    def denied(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise MarketIntelligencePublicationError("network access is disabled")

    socket.socket = GuardedSocket
    socket.create_connection = denied
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_connection


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MarketIntelligencePublicationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
