"""Network- and write-free CLI for an exact OCI deployment config candidate."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from pathlib import Path

from tip_api.services.oci_dashboard_deployment_review import (
    CONTRACT_VERSION,
    OciDashboardDeploymentReviewError,
    review_deployment_runtime_candidate,
)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not args.run_root.is_absolute():
        parser.error("--run-root must be absolute")
    try:
        with _network_prohibited():
            result = review_deployment_runtime_candidate(
                config_id=args.config_id,
                repository_root=_source_repository_root(),
                run_root=args.run_root,
                capability_enabled=args.review_enabled_candidate,
            )
    except (OciDashboardDeploymentReviewError, OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "status": "rejected",
                    "reason_code": "deployment_runtime_candidate_review_rejected",
                    "error_type": type(exc).__name__,
                    "installation_performed": False,
                    "credential_access_count": 0,
                    "external_request_count": 0,
                    "filesystem_write_count": 0,
                    "production_write_count": 0,
                    "deployment_authorized": False,
                    "rollback_authorized": False,
                    "scheduler_enabled": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Review one exact external OCI deployment runtime candidate without "
            "installing it, networking, reading credentials, or authorizing deployment."
        )
    )
    parser.add_argument("--config-id", required=True)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument(
        "--review-enabled-candidate",
        action="store_true",
        help=(
            "Render capability_enabled=true only inside the non-installed review "
            "candidate; this does not authorize or run deployment."
        ),
    )
    return parser


def _source_repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise OciDashboardDeploymentReviewError(
        "executing source repository root is unavailable"
    )


@contextmanager
def _network_prohibited():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during deployment candidate review")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during deployment candidate review")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during deployment candidate review")

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
