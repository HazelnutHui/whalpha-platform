"""Read-only CLI for reconciling external daily EOD control artifacts."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from tip_api.services.daily_eod_email_delivery import (
    DailyEodEmailConfigError,
    read_email_transport_config,
)
from tip_api.services.daily_eod_external_preflight import (
    CONTRACT_VERSION,
    DailyEodExternalPreflightError,
    preflight_external_controls,
)
from tip_api.services.daily_eod_host_runtime import (
    DailyEodHostRuntimeError,
    read_host_runtime_config,
    verify_dell_runtime,
)
from tip_api.services.daily_eod_standing_authorization import (
    DailyEodStandingAuthorizationError,
    read_standing_authorization,
)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _validate_arguments(parser, args)
    try:
        with _network_prohibited():
            source_root = _source_repository_root()
            host_config = read_host_runtime_config(
                config_path=args.host_config,
                config_root=args.host_config.parent,
                repository_root=source_root,
                expected_file_sha256=args.host_config_sha256,
            )
            verified_runtime = verify_dell_runtime(
                config=host_config,
                source_repository_root=source_root,
            )
            authorization = read_standing_authorization(
                authorization_path=args.authorization,
                authorization_root=args.authorization.parent,
                repository_root=source_root,
                expected_file_sha256=args.authorization_sha256,
            )
            email_config = None
            if not args.without_email:
                email_config = read_email_transport_config(
                    config_path=args.email_config,
                    config_root=args.email_config.parent,
                    repository_root=source_root,
                    expected_file_sha256=args.email_config_sha256,
                )
            result = preflight_external_controls(
                host_config=host_config,
                authorization=authorization,
                email_config=email_config,
                verified_runtime=verified_runtime,
                checked_at=args.checked_at,
                host_config_path=args.host_config,
                host_config_file_sha256=args.host_config_sha256,
                authorization_path=args.authorization,
                authorization_file_sha256=args.authorization_sha256,
                email_config_path=args.email_config,
                email_config_file_sha256=args.email_config_sha256,
            )
    except (
        DailyEodEmailConfigError,
        DailyEodExternalPreflightError,
        DailyEodHostRuntimeError,
        DailyEodStandingAuthorizationError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "status": "rejected",
                    "reason_code": "external_control_preflight_rejected",
                    "error_type": type(exc).__name__,
                    "credential_file_access_count": 0,
                    "external_request_count": 0,
                    "filesystem_write_count": 0,
                    "production_write_count": 0,
                    "controlled_rehearsal_authorized": False,
                    "publication_authorized": False,
                    "deployment_authorized": False,
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
            "Reconcile external Dell daily controls without credentials, "
            "networking, writes, or activation."
        )
    )
    parser.add_argument("--checked-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--host-config", required=True, type=Path)
    parser.add_argument("--host-config-sha256", required=True)
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--authorization-sha256", required=True)
    parser.add_argument("--without-email", action="store_true")
    parser.add_argument("--email-config", type=Path)
    parser.add_argument("--email-config-sha256")
    return parser


def _validate_arguments(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    for name in ("host_config", "authorization"):
        if not getattr(args, name).is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    for name in (
        "host_config_sha256",
        "authorization_sha256",
    ):
        if not _is_fingerprint(getattr(args, name)):
            parser.error(f"--{name.replace('_', '-')} must be a SHA-256 fingerprint")
    email_values = (args.email_config, args.email_config_sha256)
    if args.without_email:
        if any(value is not None for value in email_values):
            parser.error("--without-email cannot include email config arguments")
    elif (
        args.email_config is None
        or not args.email_config.is_absolute()
        or not _is_fingerprint(args.email_config_sha256)
    ):
        parser.error(
            "email preflight requires absolute --email-config and "
            "--email-config-sha256, or explicit --without-email"
        )


def _source_repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise DailyEodExternalPreflightError(
        "executing source repository root is unavailable"
    )


@contextmanager
def _network_prohibited():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during external preflight")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during external preflight")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during external preflight")

    socket.socket = GuardedSocket
    socket.create_connection = rejected
    socket.getaddrinfo = rejected
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create
        socket.getaddrinfo = original_getaddrinfo


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
