from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from tip_api.services import oci_dashboard_deployment_state as state


TARGET = "2026-08-29T120000Z-aaaaaaaaaaaa"
CURRENT = "2026-08-28T120000Z-bbbbbbbbbbbb"
SHA = "c" * 64
NOW = datetime(2026, 8, 29, 12, tzinfo=UTC)


def _state(**changes):
    values = {
        "inspected_at": NOW,
        "inspected_target_release": TARGET,
        "remote_host": "hui",
        "remote_user": "ubuntu",
        "remote_base": "/srv/whalpha",
        "current_release_id": CURRENT,
        "current_manifest_sha256": SHA,
        "current_checksums_sha256": SHA,
        "current_bundle_logical_fingerprint": SHA,
        "current_source_revision": "d" * 40,
        "target_release_exists": False,
        "staging_release_ids": (),
        "failed_release_ids": (),
        "nginx_active": True,
        "nginx_enabled": True,
        "auth_service_active": True,
        "auth_service_enabled": True,
        "auth_listener_localhost_only": True,
        "unexpected_private_listener": False,
        "protected_routes_verified": True,
        "guest_session_verified": True,
        "guest_and_credential_route_policy_identical": True,
        "credential_login_tested": False,
        "failed_system_unit_count": 0,
    }
    values.update(changes)
    return state.build_remote_state(**values)


def test_precondition_requires_fresh_exact_healthy_absent_target() -> None:
    report = _state()
    state.validate_remote_precondition(
        report,
        target_release=TARGET,
        expected_state_fingerprint=report.state_fingerprint,
        expected_current_release=CURRENT,
        checked_at=NOW + timedelta(minutes=1),
    )

    with pytest.raises(state.OciDashboardDeploymentStateError, match="precondition"):
        state.validate_remote_precondition(
            _state(staging_release_ids=(TARGET,)),
            target_release=TARGET,
            expected_state_fingerprint=report.state_fingerprint,
            expected_current_release=CURRENT,
            checked_at=NOW,
        )


def test_postcondition_binds_exact_remote_hashes_and_serving_health() -> None:
    binding = SimpleNamespace(
        manifest_sha256="1" * 64,
        checksums_sha256="2" * 64,
        bundle=SimpleNamespace(
            bundle_logical_fingerprint="3" * 64,
            deployment_manifest=SimpleNamespace(
                release_id=TARGET,
                git_commit="4" * 40,
            ),
        ),
    )
    report = _state(
        current_release_id=TARGET,
        current_manifest_sha256="1" * 64,
        current_checksums_sha256="2" * 64,
        current_bundle_logical_fingerprint="3" * 64,
        current_source_revision="4" * 40,
        target_release_exists=True,
    )
    state.validate_remote_postcondition(report, binding=binding)

    with pytest.raises(state.OciDashboardDeploymentStateError, match="postcondition"):
        state.validate_remote_postcondition(
            _state(
                current_release_id=TARGET,
                current_manifest_sha256="1" * 64,
                current_checksums_sha256="2" * 64,
                current_bundle_logical_fingerprint="3" * 64,
                current_source_revision="4" * 40,
                target_release_exists=True,
                auth_listener_localhost_only=False,
            ),
            binding=binding,
        )


def test_report_parser_rejects_noncanonical_or_tampered_state() -> None:
    report = _state()
    canonical = json.dumps(
        report.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    assert state.parse_remote_state_json(canonical) == report
    with pytest.raises(state.OciDashboardDeploymentStateError, match="canonical"):
        state.parse_remote_state_json(json.dumps(report.model_dump(mode="json")))


def test_recovery_not_completed_requires_same_state_and_no_residue() -> None:
    report = _state()
    assert state.remote_state_is_unchanged_not_completed(
        report,
        target_release=TARGET,
        expected_state_fingerprint=report.state_fingerprint,
        expected_current_release=CURRENT,
    )
    assert not state.remote_state_is_unchanged_not_completed(
        _state(failed_release_ids=(TARGET,)),
        target_release=TARGET,
        expected_state_fingerprint=report.state_fingerprint,
        expected_current_release=CURRENT,
    )
