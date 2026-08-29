from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import oci_dashboard_deployment_runtime as runtime


REVISION = "a" * 40


def _candidate(tmp_path, *, enabled=False):
    repo = tmp_path / "repo"
    (repo / "scripts/admin").mkdir(parents=True)
    for name in (
        "deploy-private-dashboard-oci.sh",
        "inspect-private-dashboard-oci.sh",
    ):
        path = repo / "scripts/admin" / name
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        path.chmod(0o755)
    run_root = tmp_path / "run"
    return runtime.build_deployment_runtime_candidate(
        config_id="oci-deployment-test-1",
        repository_root=repo,
        implementation_revision=REVISION,
        run_root=run_root,
        capability_enabled=enabled,
    )


def test_candidate_is_default_disabled_and_excludes_rollback_password_scheduler(tmp_path):
    config = _candidate(tmp_path)
    assert config.capability_enabled is False
    assert config.rollback_authorized is False
    assert config.password_access_authorized is False
    assert config.scheduler_enabled is False


def test_owner_pinned_config_rereads_and_runtime_requires_clean_main(tmp_path):
    config = _candidate(tmp_path, enabled=True)
    root = tmp_path / "config"
    root.mkdir(mode=0o700)
    path = root / "oci-deployment.json"
    raw = runtime._canonical_bytes(config.model_dump(mode="json"))
    path.write_bytes(raw)
    path.chmod(0o400)
    reread = runtime.read_deployment_runtime(
        config_path=path,
        config_root=root,
        repository_root=Path(config.repository_root),
        expected_file_sha256=hashlib.sha256(raw).hexdigest(),
    )
    outputs = iter((REVISION + "\n", "main\n", ""))
    verified = runtime.verify_deployment_runtime(
        reread,
        hostname_reader=lambda: "dell5820",
        user_reader=lambda: "hui",
        command_runner=lambda *_a, **_k: SimpleNamespace(stdout=next(outputs)),
    )
    assert verified.implementation_revision == REVISION

    dirty = iter((REVISION + "\n", "main\n", " M file\n"))
    with pytest.raises(runtime.OciDashboardDeploymentRuntimeError, match="changed"):
        runtime.verify_deployment_runtime(
            reread,
            hostname_reader=lambda: "dell5820",
            user_reader=lambda: "hui",
            command_runner=lambda *_a, **_k: SimpleNamespace(stdout=next(dirty)),
        )
