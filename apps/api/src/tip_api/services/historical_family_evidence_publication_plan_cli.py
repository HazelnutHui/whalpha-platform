"""Offline CLI for exact two-family evidence publication plans."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from tip_api.persistence.eod_read import EodReadError
from tip_api.persistence.historical_research import HistoricalResearchPersistenceError
from tip_api.persistence.instrument_master import InstrumentMasterSnapshotPersistenceError
from tip_api.services.current_historical_mechanics_evidence import (
    CurrentHistoricalMechanicsEvidenceError,
)
from tip_api.services.historical_family_evidence_publication_plan import (
    HistoricalFamilyEvidencePublicationPlanError,
    build_current_historical_family_evidence_publication_plan,
    build_identity_extension_historical_family_evidence_publication_plan,
    build_reconciled_eod_historical_family_evidence_publication_plan,
    read_current_historical_family_evidence_publication_plan,
    read_identity_extension_historical_family_evidence_publication_plan,
    read_reconciled_eod_historical_family_evidence_publication_plan,
)
from tip_api.services.reconciled_eod_historical_mechanics_evidence import (
    DEFAULT_VALIDATION_WORKERS,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build or formally verify a no-write historical-family "
            "evidence publication plan."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--data-root", required=True, type=Path)
    build_parser.add_argument("--plan-path", required=True, type=Path)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--plan-path", required=True, type=Path)
    verify_parser.add_argument("--approved-plan-sha256", required=True)
    reconciled_build_parser = subparsers.add_parser("build-reconciled")
    reconciled_build_parser.add_argument("--data-root", required=True, type=Path)
    reconciled_build_parser.add_argument("--edition-id", required=True)
    reconciled_build_parser.add_argument(
        "--expected-interval-fingerprint",
        required=True,
    )
    reconciled_build_parser.add_argument(
        "--plan-path",
        required=True,
        type=Path,
    )
    reconciled_build_parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_VALIDATION_WORKERS,
    )
    reconciled_verify_parser = subparsers.add_parser("verify-reconciled")
    reconciled_verify_parser.add_argument("--plan-path", required=True, type=Path)
    reconciled_verify_parser.add_argument(
        "--approved-plan-sha256",
        required=True,
    )
    identity_build_parser = subparsers.add_parser("build-identity-extension")
    identity_build_parser.add_argument("--data-root", required=True, type=Path)
    identity_build_parser.add_argument(
        "--session",
        required=True,
        action="append",
        type=date.fromisoformat,
    )
    identity_build_parser.add_argument("--plan-path", required=True, type=Path)
    identity_verify_parser = subparsers.add_parser("verify-identity-extension")
    identity_verify_parser.add_argument("--plan-path", required=True, type=Path)
    identity_verify_parser.add_argument(
        "--approved-plan-sha256",
        required=True,
    )
    args = parser.parse_args(argv)

    try:
        with _offline_socket_guard():
            if args.command == "build":
                evidence = build_current_historical_family_evidence_publication_plan(
                    data_root=args.data_root,
                    plan_path=args.plan_path,
                )
                status = "plan_created"
            elif args.command == "verify":
                evidence = read_current_historical_family_evidence_publication_plan(
                    plan_path=args.plan_path,
                    approved_plan_sha256=args.approved_plan_sha256,
                )
                status = "plan_revalidated"
            elif args.command == "build-reconciled":
                evidence = (
                    build_reconciled_eod_historical_family_evidence_publication_plan(
                        data_root=args.data_root,
                        edition_id=args.edition_id,
                        expected_interval_manifest_fingerprint=(
                            args.expected_interval_fingerprint
                        ),
                        plan_path=args.plan_path,
                        max_workers=args.workers,
                    )
                )
                status = "plan_created"
            elif args.command == "verify-reconciled":
                evidence = (
                    read_reconciled_eod_historical_family_evidence_publication_plan(
                        plan_path=args.plan_path,
                        approved_plan_sha256=args.approved_plan_sha256,
                    )
                )
                status = "plan_revalidated"
            elif args.command == "build-identity-extension":
                evidence = (
                    build_identity_extension_historical_family_evidence_publication_plan(
                        data_root=args.data_root,
                        sessions=tuple(args.session),
                        plan_path=args.plan_path,
                    )
                )
                status = "plan_created"
            else:
                evidence = (
                    read_identity_extension_historical_family_evidence_publication_plan(
                        plan_path=args.plan_path,
                        approved_plan_sha256=args.approved_plan_sha256,
                    )
                )
                status = "plan_revalidated"
    except (
        CurrentHistoricalMechanicsEvidenceError,
        HistoricalFamilyEvidencePublicationPlanError,
        EodReadError,
        HistoricalResearchPersistenceError,
        InstrumentMasterSnapshotPersistenceError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "historical_family_evidence_plan_rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "apply_authorized": False,
                    "historical_coverage_authorized": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1

    plan = evidence.plan
    payload = {
        "status": status,
        "contract_version": plan.contract_version,
        "operation": plan.operation,
        "plan_path": str(evidence.plan_path),
        "plan_sha256": evidence.plan_sha256,
        "plan_logical_fingerprint": plan.logical_fingerprint,
        "family_set_fingerprint": plan.family_set_fingerprint,
        "first_session": plan.first_session.isoformat(),
        "last_session": plan.last_session.isoformat(),
        "session_count": plan.session_count,
        "inventory_change_file_count": plan.inventory_change_file_count,
        "inventory_change_bytes": plan.inventory_change_bytes,
        "target_absent_count": plan.target_absent_count,
        "families": [
            {
                "family": item.family.value,
                "record_count": item.record_count,
                "source_artifact_count": item.source_artifact_count,
                "source_file_count": item.source_file_count,
                "evidence_logical_fingerprint": (
                    item.evidence.logical_fingerprint
                ),
                "evidence_manifest_sha256": item.evidence_manifest_sha256,
                "target_path": item.target_path,
                "expected_target_state": item.expected_target_state,
            }
            for item in plan.families
        ],
        "external_request_count": plan.external_request_count,
        "canonical_data_write_count": plan.canonical_data_write_count,
        "apply_authorized": plan.apply_authorized,
        "historical_coverage_authorized": plan.historical_coverage_authorized,
        "research_development_authorized": (
            plan.research_development_authorized
        ),
        "research_performance_authorized": (
            plan.research_performance_authorized
        ),
    }
    if hasattr(plan, "source_edition_id"):
        payload["source_edition_id"] = plan.source_edition_id
        payload["source_interval_manifest_fingerprint"] = (
            plan.source_interval_manifest_fingerprint
        )
    if hasattr(plan, "purpose"):
        payload["purpose"] = plan.purpose
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during evidence planning")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during evidence planning")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during evidence planning")

    socket.socket = GuardedSocket
    socket.create_connection = rejected
    socket.getaddrinfo = rejected
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create
        socket.getaddrinfo = original_getaddrinfo


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
