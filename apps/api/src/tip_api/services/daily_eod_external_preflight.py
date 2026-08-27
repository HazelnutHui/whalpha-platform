"""Network-free reconciliation of external daily EOD control artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import ValidationError
from pydantic_core import to_jsonable_python

from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.daily_eod_email_delivery import (
    DailyEodEmailTransportConfigV1,
)
from tip_api.services.daily_eod_host_runtime import (
    DailyEodHostRuntimeConfigV1,
    VerifiedDellRuntime,
)
from tip_api.services.daily_eod_standing_authorization import (
    DailyEodStandingAuthorizationError,
    DailyEodStandingAuthorizationV1,
    StandingOperation,
    validate_standing_authorization_runtime,
)


CONTRACT_VERSION = "daily-eod-external-control-preflight/1.1"


class DailyEodExternalPreflightError(RuntimeError):
    """Raised when external controls are unsafe, inactive, or inconsistent."""


@dataclass(frozen=True, slots=True)
class DailyEodExternalPreflightResult:
    contract_version: str
    status: str
    checked_at: str
    host: str
    repository_root: str
    implementation_revision: str
    data_root: str
    run_root: str
    alert_root: str | None
    preflight_mode: str
    host_config_id: str
    authorization_id: str
    email_config_id: str | None
    host_config_file_sha256: str
    authorization_file_sha256: str
    email_config_file_sha256: str | None
    allowed_operations: tuple[str, ...]
    host_capabilities_enabled: bool
    email_transport_enabled: bool
    configuration_consistent: bool
    credential_paths_distinct: bool
    credential_file_access_count: int
    external_request_count: int
    filesystem_write_count: int
    production_write_count: int
    controlled_rehearsal_authorized: bool
    publication_authorized: bool
    deployment_authorized: bool
    scheduler_enabled: bool
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def preflight_external_controls(
    *,
    host_config: DailyEodHostRuntimeConfigV1,
    authorization: DailyEodStandingAuthorizationV1,
    email_config: DailyEodEmailTransportConfigV1 | None,
    verified_runtime: VerifiedDellRuntime,
    checked_at: datetime,
    host_config_path: Path,
    host_config_file_sha256: str,
    authorization_path: Path,
    authorization_file_sha256: str,
    email_config_path: Path | None,
    email_config_file_sha256: str | None,
) -> DailyEodExternalPreflightResult:
    """Prove configuration consistency without inspecting credentials or roots."""

    host_config = _revalidate(
        DailyEodHostRuntimeConfigV1,
        host_config,
        "host runtime config",
    )
    authorization = _revalidate(
        DailyEodStandingAuthorizationV1,
        authorization,
        "standing authorization",
    )
    if email_config is None:
        if email_config_path is not None or email_config_file_sha256 is not None:
            raise DailyEodExternalPreflightError(
                "email preflight inputs must be supplied together"
            )
    else:
        if email_config_path is None or email_config_file_sha256 is None:
            raise DailyEodExternalPreflightError(
                "email preflight inputs must be supplied together"
            )
        email_config = _revalidate(
            DailyEodEmailTransportConfigV1,
            email_config,
            "email transport config",
        )
    email_included = email_config is not None
    checked = _aware_utc(checked_at)
    file_shas = [
        host_config_file_sha256,
        authorization_file_sha256,
    ]
    paths = [host_config_path, authorization_path]
    if email_included:
        assert email_config_file_sha256 is not None
        assert email_config_path is not None
        file_shas.append(email_config_file_sha256)
        paths.append(email_config_path)
    path_tuple = tuple(paths)
    control_roots = tuple(path.parent for path in path_tuple)
    if (
        not isinstance(verified_runtime, VerifiedDellRuntime)
        or not verified_runtime.worktree_clean
        or not all(_is_fingerprint(value) for value in file_shas)
        or not all(path.is_absolute() for path in path_tuple)
        or any(
            _paths_overlap(left, right)
            for index, left in enumerate(control_roots)
            for right in control_roots[index + 1 :]
        )
    ):
        raise DailyEodExternalPreflightError(
            "external control custody identity is invalid"
        )
    repository_root = Path(host_config.repository_root)
    data_root = Path(host_config.data_root)
    run_root = Path(host_config.run_root)
    alert_root = None if email_config is None else Path(email_config.alert_root)
    protected_operational_roots = (repository_root, data_root, run_root) + (
        () if alert_root is None else (alert_root,)
    )
    if (
        any(
            _paths_overlap(control_root, protected_root)
            for control_root in control_roots
            for protected_root in protected_operational_roots
        )
        or Path(host_config.authorization_root) != authorization_path.parent
        or Path(host_config.authorization_path) != authorization_path
        or host_config.authorization_file_sha256 != authorization_file_sha256
    ):
        raise DailyEodExternalPreflightError(
            "external control artifact binding is inconsistent"
        )
    if (
        host_config.host != authorization.host
        or host_config.host != verified_runtime.host
        or host_config.repository_root != verified_runtime.repository_root
        or host_config.implementation_revision
        != authorization.implementation_revision
        or host_config.implementation_revision
        != verified_runtime.implementation_revision
        or host_config.data_root != authorization.data_root
        or host_config.run_root != authorization.run_root
        or host_config.readiness_policy_fingerprint
        != authorization.readiness_policy_fingerprint
        or host_config.readiness_policy_fingerprint
        != verified_runtime.readiness_policy_fingerprint
    ):
        raise DailyEodExternalPreflightError(
            "external control runtime binding is inconsistent"
        )
    if email_config is not None and (
        host_config.host != email_config.host
        or host_config.repository_root != email_config.repository_root
        or host_config.implementation_revision
        != email_config.implementation_revision
        or host_config.data_root != email_config.data_root
        or host_config.run_root != email_config.run_root
    ):
        raise DailyEodExternalPreflightError(
            "external control runtime binding is inconsistent"
        )
    required_operations = tuple(StandingOperation)
    if (
        not host_config.capabilities_enabled
        or authorization.allowed_operations != required_operations
        or (email_config is not None and not email_config.enabled)
    ):
        raise DailyEodExternalPreflightError(
            "external controls are not enabled for the complete daily scope"
        )
    credential_paths = [Path(host_config.credential_path)]
    if email_config is not None:
        credential_paths.append(Path(email_config.credential_path))
    protected_roots = (
        repository_root,
        data_root,
        run_root,
        *(value for value in (alert_root,) if value is not None),
        *control_roots,
    )
    if (
        any(
            left == right or _paths_overlap(left.parent, right.parent)
            for index, left in enumerate(credential_paths)
            for right in credential_paths[index + 1 :]
        )
        or any(
            _paths_overlap(path.parent, protected_root)
            for path in credential_paths
            for protected_root in protected_roots
        )
    ):
        raise DailyEodExternalPreflightError(
            "external credential paths are not independently custodied"
        )
    try:
        for operation in required_operations:
            validate_standing_authorization_runtime(
                authorization=authorization,
                evaluated_at=checked,
                operation=operation,
                actual_host=verified_runtime.host,
                actual_provider_id=MASSIVE_PROVIDER_ID,
                actual_data_root=data_root,
                actual_run_root=run_root,
                actual_implementation_revision=(
                    verified_runtime.implementation_revision
                ),
                actual_readiness_policy_fingerprint=(
                    verified_runtime.readiness_policy_fingerprint
                ),
            )
    except DailyEodStandingAuthorizationError as exc:
        raise DailyEodExternalPreflightError(
            "standing authorization is not active for complete daily scope"
        ) from exc
    base = {
        "contract_version": CONTRACT_VERSION,
        "status": "configuration_consistent",
        "checked_at": checked.isoformat(),
        "host": verified_runtime.host,
        "repository_root": verified_runtime.repository_root,
        "implementation_revision": verified_runtime.implementation_revision,
        "data_root": str(data_root),
        "run_root": str(run_root),
        "alert_root": None if alert_root is None else str(alert_root),
        "preflight_mode": (
            "data_and_email" if email_included else "daily_data_only"
        ),
        "host_config_id": host_config.config_id,
        "authorization_id": authorization.authorization_id,
        "email_config_id": (
            None if email_config is None else email_config.config_id
        ),
        "host_config_file_sha256": host_config_file_sha256,
        "authorization_file_sha256": authorization_file_sha256,
        "email_config_file_sha256": email_config_file_sha256,
        "allowed_operations": tuple(item.value for item in required_operations),
        "host_capabilities_enabled": True,
        "email_transport_enabled": bool(
            email_config is not None and email_config.enabled
        ),
        "configuration_consistent": True,
        "credential_paths_distinct": True,
        "credential_file_access_count": 0,
        "external_request_count": 0,
        "filesystem_write_count": 0,
        "production_write_count": 0,
        "controlled_rehearsal_authorized": False,
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_enabled": False,
    }
    return DailyEodExternalPreflightResult(
        **base,
        logical_content_fingerprint=_fingerprint(base),
    )


def _revalidate(model, value, label):  # type: ignore[no-untyped-def]
    try:
        return model.model_validate(value.model_dump(mode="json"))
    except (AttributeError, ValidationError, ValueError) as exc:
        raise DailyEodExternalPreflightError(f"{label} is invalid") from exc


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodExternalPreflightError("preflight timestamp is invalid")
    return value.astimezone(UTC)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=lambda item: item.value if isinstance(item, StrEnum) else str(item),
        )
        + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _paths_overlap(left: Path, right: Path) -> bool:
    return _is_within(left, right) or _is_within(right, left)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.absolute().relative_to(root.absolute())
        return True
    except ValueError:
        return False
