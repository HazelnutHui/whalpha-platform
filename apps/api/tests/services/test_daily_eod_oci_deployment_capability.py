from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services.daily_eod_automation import DailyEodAutomationPaths
from tip_api.services.daily_eod_coordinator import DeploymentTransitionContext
from tip_api.services.daily_eod_oci_deployment_capability import (
    DailyEodOciDeploymentCapability,
    DailyEodOciDeploymentCapabilityConfig,
    DailyEodOciDeploymentCapabilityError,
)


TARGET = date(2026, 8, 28)
RELEASE = "2026-08-29T120000Z-aaaaaaaaaaaa"
BUNDLE_FP = "1" * 64


class Transport:
    def __init__(self):
        self.calls = []
        self.states = [SimpleNamespace(name="pre"), SimpleNamespace(name="post")]

    def inspect(self, *, target_release):
        self.calls.append(("inspect", target_release))
        return self.states.pop(0)

    def apply(self, *, bundle_path, release_id, expected_current_release):
        self.calls.append(("apply", bundle_path, release_id, expected_current_release))


def test_capability_orders_preinspect_reservation_apply_postinspect_and_proof(tmp_path):
    bundle_path = Path(f"/tmp/{tmp_path.name}-bundle") / RELEASE
    paths = DailyEodAutomationPaths(
        data_root=tmp_path / "data",
        phase1a_audit=Path("/tmp/a"),
        prior_phase1b_audit=Path("/tmp/b"),
        phase1b_audit=Path("/tmp/c"),
        prior_candidate_audit=Path("/tmp/d"),
        candidate_audit=Path("/tmp/e"),
        entry_geometry_audit=Path("/tmp/f"),
        phase2_audit=Path("/tmp/g"),
        preview_bundle=Path("/tmp/h"),
        strategy_channel_audit=Path("/tmp/i"),
        market_intelligence_output_root=Path("/tmp/j"),
        market_intelligence_approval_plan=Path("/tmp/k"),
        snapshot_output_root=Path("/tmp/l"),
        snapshot_approval_plan=Path("/tmp/m"),
        serving_bundle_root=bundle_path.parent,
    )
    coordinator = SimpleNamespace(target_session=TARGET, run_root=tmp_path / "run", paths=paths)
    plan = SimpleNamespace(logical_content_fingerprint="2" * 64)
    context = DeploymentTransitionContext(
        coordinator=coordinator,
        automation_plan=plan,
        checked_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
        operation="deploy_oci_dashboard",
        bundle_path=bundle_path,
        release_id=RELEASE,
        bundle_logical_fingerprint=BUNDLE_FP,
    )
    transport = Transport()
    order = []
    binding = SimpleNamespace(
        bundle=SimpleNamespace(
            path=bundle_path,
            deployment_manifest=SimpleNamespace(release_id=RELEASE),
        )
    )

    def reserve(**kwargs):
        order.append(("reserve", kwargs["remote_state"].name))
        return SimpleNamespace(outcome="reserved", binding=binding)

    def record(**kwargs):
        order.append(("record", kwargs["remote_state"].name))
        return SimpleNamespace(
            outcome="succeeded",
            event=SimpleNamespace(event_fingerprint="3" * 64),
            reason_code="proven",
        )

    capability = DailyEodOciDeploymentCapability(
        config=DailyEodOciDeploymentCapabilityConfig(
            run_root=coordinator.run_root,
            automation_paths=paths,
            bundle_path=bundle_path,
            approved_bundle_logical_fingerprint=BUNDLE_FP,
            expected_remote_state_fingerprint="4" * 64,
            expected_current_release="2026-08-28T120000Z-bbbbbbbbbbbb",
            deployment_config_file_sha256="5" * 64,
        ),
        transport=transport,
        reserver=reserve,
        recorder=record,
        binding_reader=lambda *_a, **_k: binding,
    )

    evidence = capability.deploy(context)

    assert transport.calls == [
        ("inspect", RELEASE),
        (
            "apply",
            bundle_path,
            RELEASE,
            "2026-08-28T120000Z-bbbbbbbbbbbb",
        ),
        ("inspect", RELEASE),
    ]
    assert order == [("reserve", "pre"), ("record", "post")]
    assert evidence.external_request_count == 3
    assert evidence.production_write_count == 1


def test_invalid_local_approval_is_rejected_before_remote_inspection(tmp_path):
    transport = Transport()
    bad_path = Path("/not-tmp") / RELEASE
    paths = SimpleNamespace()
    coordinator = SimpleNamespace(target_session=TARGET, run_root=tmp_path / "run", paths=paths)
    context = DeploymentTransitionContext(
        coordinator=coordinator,
        automation_plan=SimpleNamespace(logical_content_fingerprint="2" * 64),
        checked_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
        operation="deploy_oci_dashboard",
        bundle_path=bad_path,
        release_id=RELEASE,
        bundle_logical_fingerprint=BUNDLE_FP,
    )
    capability = DailyEodOciDeploymentCapability(
        config=DailyEodOciDeploymentCapabilityConfig(
            run_root=coordinator.run_root,
            automation_paths=paths,
            bundle_path=bad_path,
            approved_bundle_logical_fingerprint=BUNDLE_FP,
            expected_remote_state_fingerprint="4" * 64,
            expected_current_release="2026-08-28T120000Z-bbbbbbbbbbbb",
            deployment_config_file_sha256="5" * 64,
        ),
        transport=transport,
    )
    with pytest.raises(DailyEodOciDeploymentCapabilityError, match="local"):
        capability.deploy(context)
    assert transport.calls == []
