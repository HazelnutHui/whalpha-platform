"""Default-disabled CLI for exactly one Dell daily EOD transition."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from tip_api.services.daily_eod_authorized_capabilities import (
    DailyEodAuthorizedCapabilities,
    DailyEodAuthorizedCapabilityConfig,
    DailyEodAuthorizedCapabilityError,
)
from tip_api.services.daily_eod_automation import DailyEodAutomationPaths
from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorConfig,
    DailyEodCoordinatorError,
    coordinate_daily_eod_transition,
)
from tip_api.services.daily_eod_host_runtime import (
    DailyEodHostRuntimeError,
    read_host_runtime_config,
    verify_dell_runtime,
)
from tip_api.services.daily_eod_run_journal import DailyEodRunJournalError


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _validate_arguments(parser, args)
    automation_paths = DailyEodAutomationPaths(
        data_root=args.data_root,
        phase1a_audit=args.phase1a_audit,
        prior_phase1b_audit=args.prior_phase1b_audit,
        phase1b_audit=args.phase1b_audit,
        prior_candidate_audit=args.prior_candidate_audit,
        candidate_audit=args.candidate_audit,
        entry_geometry_audit=args.entry_geometry_audit,
    )
    coordinator_config = DailyEodCoordinatorConfig(
        target_session=args.target_session,
        latest_canonical_session=args.latest_canonical_session,
        paths=automation_paths,
        run_root=args.run_root,
        package_path=args.package,
        approval_plan_path=args.approval_plan,
        panel_cache_root=args.panel_cache_root,
        candidate_work_dir=args.candidate_work_dir,
    )
    try:
        capabilities = (
            _load_authorized_capabilities(args, automation_paths)
            if args.enable_authorized_capabilities
            else None
        )
        with _network_boundary(enabled=capabilities is not None):
            result = coordinate_daily_eod_transition(
                config=coordinator_config,
                checked_at=args.checked_at,
                execute_offline=args.execute_offline,
                fetch_capability=(None if capabilities is None else capabilities.fetch),
                apply_capability=(None if capabilities is None else capabilities.apply),
            )
    except (
        DailyEodAuthorizedCapabilityError,
        DailyEodCoordinatorError,
        DailyEodHostRuntimeError,
        DailyEodRunJournalError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "daily_eod_one_transition_rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": None,
                    "production_write_count": None,
                    "transition_outcome_formally_known": False,
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
    return (
        1
        if result.status
        in {CoordinatorStatus.BLOCKED, CoordinatorStatus.RECOVERY_REQUIRED}
        else 0
    )


def _load_authorized_capabilities(
    args: argparse.Namespace,
    automation_paths: DailyEodAutomationPaths,
) -> DailyEodAuthorizedCapabilities:
    source_root = _source_repository_root()
    host_config = read_host_runtime_config(
        config_path=args.host_config,
        config_root=args.host_config.parent,
        repository_root=source_root,
        expected_file_sha256=args.host_config_sha256,
    )
    if not host_config.capabilities_enabled:
        raise DailyEodHostRuntimeError(
            "host runtime capabilities are disabled"
        )
    verified = verify_dell_runtime(
        config=host_config,
        source_repository_root=source_root,
    )
    if (
        Path(host_config.data_root) != args.data_root
        or Path(host_config.run_root) != args.run_root
    ):
        raise DailyEodHostRuntimeError(
            "CLI data or run root differs from host runtime config"
        )
    return DailyEodAuthorizedCapabilities(
        config=DailyEodAuthorizedCapabilityConfig(
            authorization_path=Path(host_config.authorization_path),
            authorization_root=Path(host_config.authorization_root),
            repository_root=Path(host_config.repository_root),
            expected_authorization_file_sha256=(
                host_config.authorization_file_sha256
            ),
            actual_host=verified.host,
            implementation_revision=verified.implementation_revision,
            readiness_policy_fingerprint=verified.readiness_policy_fingerprint,
            data_root=Path(host_config.data_root),
            run_root=Path(host_config.run_root),
            automation_paths=automation_paths,
            credential_path=Path(host_config.credential_path),
            approved_plan_sha256=args.approved_plan_sha256,
            expected_current_state_fingerprint=(
                args.expected_current_state_fingerprint
            ),
        )
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Coordinate exactly one Dell daily EOD transition without looping."
    )
    parser.add_argument("--target-session", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--latest-canonical-session", required=True, type=date.fromisoformat
    )
    parser.add_argument("--checked-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--approval-plan", required=True, type=Path)
    parser.add_argument("--phase1a-audit", required=True, type=Path)
    parser.add_argument("--prior-phase1b-audit", required=True, type=Path)
    parser.add_argument("--phase1b-audit", required=True, type=Path)
    parser.add_argument("--prior-candidate-audit", required=True, type=Path)
    parser.add_argument("--candidate-audit", required=True, type=Path)
    parser.add_argument("--entry-geometry-audit", required=True, type=Path)
    parser.add_argument("--panel-cache-root", type=Path)
    parser.add_argument("--candidate-work-dir", type=Path)
    parser.add_argument("--execute-offline", action="store_true")
    parser.add_argument("--enable-authorized-capabilities", action="store_true")
    parser.add_argument("--host-config", type=Path)
    parser.add_argument("--host-config-sha256")
    parser.add_argument("--approved-plan-sha256")
    parser.add_argument("--expected-current-state-fingerprint")
    return parser


def _validate_arguments(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    path_names = (
        "data_root",
        "run_root",
        "package",
        "approval_plan",
        "phase1a_audit",
        "prior_phase1b_audit",
        "phase1b_audit",
        "prior_candidate_audit",
        "candidate_audit",
        "entry_geometry_audit",
        "panel_cache_root",
        "candidate_work_dir",
    )
    for name in path_names:
        value = getattr(args, name)
        if value is not None and not value.is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    host_values = (args.host_config, args.host_config_sha256)
    if args.enable_authorized_capabilities:
        if args.host_config is None or not _is_fingerprint(args.host_config_sha256):
            parser.error(
                "--enable-authorized-capabilities requires an absolute --host-config "
                "and --host-config-sha256"
            )
        if not args.host_config.is_absolute():
            parser.error("--host-config must be absolute")
    elif any(value is not None for value in host_values):
        parser.error(
            "host runtime arguments require --enable-authorized-capabilities"
        )
    apply_values = (
        args.approved_plan_sha256,
        args.expected_current_state_fingerprint,
    )
    if any(value is not None for value in apply_values) and not all(
        _is_fingerprint(value) for value in apply_values
    ):
        parser.error(
            "approved Apply inputs must be supplied together as SHA-256 fingerprints"
        )
    if any(value is not None for value in apply_values) and not args.enable_authorized_capabilities:
        parser.error(
            "approved Apply inputs require --enable-authorized-capabilities"
        )


def _source_repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise DailyEodHostRuntimeError("executing source repository root is unavailable")


@contextmanager
def _network_boundary(*, enabled: bool):
    if enabled:
        yield
        return
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited without authorized capabilities")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited without authorized capabilities")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited without authorized capabilities")

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
