"""Structured, non-secret OCI Dashboard deployment state and exact predicates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tip_api.services.oci_dashboard_serving_bundle import (
    CompletedOciDashboardServingBundle,
    OciDashboardServingBundleError,
    read_oci_dashboard_serving_bundle,
)
from tip_api.services.private_dashboard_snapshot import sha256_file


CONTRACT_VERSION = "oci-dashboard-remote-state/1.0"
MAXIMUM_INSPECTION_AGE = timedelta(minutes=5)


class OciDashboardDeploymentStateError(RuntimeError):
    """Raised when remote deployment state is malformed, stale, or unsafe."""


class OciDashboardRemoteStateV1(BaseModel):
    """One target-specific, read-only report; it contains no credential values."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["oci-dashboard-remote-state/1.0"] = CONTRACT_VERSION
    inspected_at: datetime
    inspected_target_release: str
    remote_host: Literal["hui"]
    remote_user: Literal["ubuntu"]
    remote_base: Literal["/srv/whalpha"]
    current_release_id: str | None
    current_manifest_sha256: str | None
    current_checksums_sha256: str | None
    current_bundle_logical_fingerprint: str | None
    current_source_revision: str | None
    target_release_exists: bool
    staging_release_ids: tuple[str, ...]
    failed_release_ids: tuple[str, ...]
    nginx_active: bool
    nginx_enabled: bool
    auth_service_active: bool
    auth_service_enabled: bool
    auth_listener_localhost_only: bool
    unexpected_private_listener: bool
    protected_routes_verified: bool
    guest_session_verified: bool
    guest_and_credential_route_policy_identical: bool
    credential_login_tested: Literal[False] = False
    failed_system_unit_count: int
    state_fingerprint: str

    @field_validator(
        "current_manifest_sha256",
        "current_checksums_sha256",
        "current_bundle_logical_fingerprint",
        "state_fingerprint",
    )
    @classmethod
    def optional_fingerprints(cls, value: str | None) -> str | None:
        if value is not None and not _is_fingerprint(value):
            raise ValueError("remote-state fingerprint is malformed")
        return value

    @field_validator("current_source_revision")
    @classmethod
    def optional_revision(cls, value: str | None) -> str | None:
        if value is not None and not _is_revision(value):
            raise ValueError("remote-state source revision is malformed")
        return value

    @model_validator(mode="after")
    def exact_contract(self) -> "OciDashboardRemoteStateV1":
        if (
            self.inspected_at.tzinfo is None
            or self.inspected_at.utcoffset() is None
            or self.inspected_at.utcoffset().total_seconds() != 0
            or self.inspected_at.microsecond != 0
            or self.failed_system_unit_count < 0
            or tuple(sorted(set(self.staging_release_ids))) != self.staging_release_ids
            or tuple(sorted(set(self.failed_release_ids))) != self.failed_release_ids
        ):
            raise ValueError("remote-state fixed boundary mismatch")
        _validate_release(self.inspected_target_release)
        for value in self.staging_release_ids + self.failed_release_ids:
            _validate_release(value)
        current_values = (
            self.current_manifest_sha256,
            self.current_checksums_sha256,
            self.current_bundle_logical_fingerprint,
            self.current_source_revision,
        )
        if self.current_release_id is None:
            if any(value is not None for value in current_values):
                raise ValueError("absent current release has identity fields")
        else:
            _validate_release(self.current_release_id)
            if any(value is None for value in current_values):
                raise ValueError("current release identity is incomplete")
        expected = _fingerprint(
            self.model_dump(
                mode="json",
                exclude={"inspected_at", "state_fingerprint"},
            )
        )
        if self.state_fingerprint != expected:
            raise ValueError("remote-state fingerprint mismatch")
        return self


@dataclass(frozen=True, slots=True)
class OciDashboardDeploymentBinding:
    bundle: CompletedOciDashboardServingBundle
    manifest_sha256: str
    checksums_sha256: str


def build_remote_state(**values: object) -> OciDashboardRemoteStateV1:
    """Build and fingerprint a report from an already read-only inspection."""

    base = {"contract_version": CONTRACT_VERSION, **values}
    logical = {key: value for key, value in base.items() if key != "inspected_at"}
    return OciDashboardRemoteStateV1.model_validate(
        {**base, "state_fingerprint": _fingerprint(logical)}
    )


def parse_remote_state_json(raw: str) -> OciDashboardRemoteStateV1:
    """Parse exactly one canonical JSON object emitted by the inspector."""

    try:
        payload = json.loads(raw)
        state = OciDashboardRemoteStateV1.model_validate(payload)
    except (json.JSONDecodeError, ValueError) as exc:
        raise OciDashboardDeploymentStateError("remote-state report is invalid") from exc
    canonical = json.dumps(
        state.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    if raw.strip() != canonical:
        raise OciDashboardDeploymentStateError("remote-state report is not canonical")
    return state


def read_deployment_binding(
    bundle_path: Path,
    *,
    expected_bundle_logical_fingerprint: str,
) -> OciDashboardDeploymentBinding:
    """Reread one local bundle and bind the two remote-verifiable inventories."""

    if not _is_fingerprint(expected_bundle_logical_fingerprint):
        raise OciDashboardDeploymentStateError("approved bundle fingerprint is malformed")
    try:
        bundle = read_oci_dashboard_serving_bundle(bundle_path)
    except OciDashboardServingBundleError as exc:
        raise OciDashboardDeploymentStateError("approved Serving Bundle is invalid") from exc
    if bundle.bundle_logical_fingerprint != expected_bundle_logical_fingerprint:
        raise OciDashboardDeploymentStateError("Serving Bundle differs from approval")
    return OciDashboardDeploymentBinding(
        bundle=bundle,
        manifest_sha256=sha256_file(bundle.path / "deployment-manifest.json"),
        checksums_sha256=sha256_file(bundle.path / "checksums.sha256"),
    )


def validate_remote_precondition(
    state: OciDashboardRemoteStateV1,
    *,
    target_release: str,
    expected_state_fingerprint: str,
    expected_current_release: str,
    checked_at: datetime,
) -> None:
    """Require the exact fresh healthy pre-state and a wholly absent target."""

    observed = _aware_utc(checked_at)
    inspected = _aware_utc(state.inspected_at)
    if observed < inspected or observed - inspected > MAXIMUM_INSPECTION_AGE:
        raise OciDashboardDeploymentStateError("remote preflight report is stale")
    if (
        state.inspected_target_release != target_release
        or state.state_fingerprint != expected_state_fingerprint
        or state.current_release_id != expected_current_release
        or state.target_release_exists
        or state.staging_release_ids
        or state.failed_release_ids
        or not _healthy(state)
    ):
        raise OciDashboardDeploymentStateError("remote precondition differs from approval")


def validate_remote_postcondition(
    state: OciDashboardRemoteStateV1,
    *,
    binding: OciDashboardDeploymentBinding,
) -> None:
    """Require independent proof of the exact deployed bytes and serving boundary."""

    manifest = binding.bundle.deployment_manifest
    if (
        state.inspected_target_release != manifest.release_id
        or state.current_release_id != manifest.release_id
        or not state.target_release_exists
        or state.current_manifest_sha256 != binding.manifest_sha256
        or state.current_checksums_sha256 != binding.checksums_sha256
        or state.current_bundle_logical_fingerprint
        != binding.bundle.bundle_logical_fingerprint
        or state.current_source_revision != manifest.git_commit
        or state.staging_release_ids
        or state.failed_release_ids
        or not _healthy(state)
    ):
        raise OciDashboardDeploymentStateError(
            "remote postcondition does not prove the exact Serving Bundle"
        )


def remote_state_is_unchanged_not_completed(
    state: OciDashboardRemoteStateV1,
    *,
    target_release: str,
    expected_state_fingerprint: str,
    expected_current_release: str,
) -> bool:
    return (
        state.inspected_target_release == target_release
        and state.state_fingerprint == expected_state_fingerprint
        and state.current_release_id == expected_current_release
        and not state.target_release_exists
        and not state.staging_release_ids
        and not state.failed_release_ids
        and _healthy(state)
    )


def _healthy(state: OciDashboardRemoteStateV1) -> bool:
    return (
        state.nginx_active
        and state.nginx_enabled
        and state.auth_service_active
        and state.auth_service_enabled
        and state.auth_listener_localhost_only
        and not state.unexpected_private_listener
        and state.protected_routes_verified
        and state.guest_session_verified
        and state.guest_and_credential_route_policy_identical
        and not state.credential_login_tested
        and state.failed_system_unit_count == 0
    )


def _validate_release(value: str) -> None:
    import re

    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}", value) is None:
        raise ValueError("remote-state release ID is malformed")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise OciDashboardDeploymentStateError("inspection comparison must be timezone-aware")
    return value.astimezone(UTC)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_revision(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(character in "0123456789abcdef" for character in value)
    )
