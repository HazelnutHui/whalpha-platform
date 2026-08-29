"""Network- and write-free review CLI for a non-installed user timer."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from pathlib import Path

from tip_api.services.daily_eod_scheduler_systemd import (
    REVIEW_CONTRACT_VERSION,
    DailyEodSchedulerSystemdError,
    review_scheduler_systemd_candidate,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Review exact Dell user-systemd unit bytes without writing, installing, "
            "enabling, networking, or invoking the coordinator."
        )
    )
    parser.add_argument("--config-id", required=True)
    parser.add_argument("--review-enabled-candidate", action="store_true")
    args = parser.parse_args(argv)
    try:
        with _offline_socket_guard():
            review = review_scheduler_systemd_candidate(
                config_id=args.config_id,
                repository_root=_source_repository_root(),
                activation_candidate_enabled=args.review_enabled_candidate,
            )
    except (DailyEodSchedulerSystemdError, OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "contract_version": REVIEW_CONTRACT_VERSION,
                    "status": "rejected",
                    "reason_code": "scheduler_systemd_candidate_review_rejected",
                    "error_type": type(exc).__name__,
                    "installation_performed": False,
                    "activation_performed": False,
                    "scheduler_installed": False,
                    "coordinator_invocation_count": 0,
                    "credential_access_count": 0,
                    "external_request_count": 0,
                    "filesystem_write_count": 0,
                    "production_write_count": 0,
                    "publication_authorized": False,
                    "deployment_authorized": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(review.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


def _source_repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise DailyEodSchedulerSystemdError(
        "scheduler source repository root is unavailable"
    )


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during systemd candidate review")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during systemd candidate review")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during systemd candidate review")

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
