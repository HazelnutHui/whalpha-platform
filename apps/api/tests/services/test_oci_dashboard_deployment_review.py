from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import oci_dashboard_deployment_review as review


REVISION = "a" * 40


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts/admin").mkdir(parents=True)
    for name in (
        "deploy-private-dashboard-oci.sh",
        "inspect-private-dashboard-oci.sh",
    ):
        path = root / "scripts/admin" / name
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        path.chmod(0o755)
    return root


def _runner(*_args, **_kwargs):
    value = _runner.outputs.pop(0)
    return SimpleNamespace(stdout=value)


def test_review_builds_exact_default_disabled_candidate_without_installing(tmp_path):
    root = _repository(tmp_path)
    before = _inventory(tmp_path)
    _runner.outputs = [
        REVISION + "\n",
        "main\n",
        "",
        REVISION + "\n",
        "main\n",
        "",
    ]
    result = review.review_deployment_runtime_candidate(
        config_id="oci-deployment-review-1",
        repository_root=root,
        run_root=tmp_path / "run",
        hostname_reader=lambda: "dell5820",
        user_reader=lambda: "hui",
        command_runner=_runner,
    )
    candidate = review.candidate_from_review(result)

    assert candidate.capability_enabled is False
    assert candidate.implementation_revision == REVISION
    assert result.installation_performed is False
    assert result.external_request_count == 0
    assert result.filesystem_write_count == 0
    assert result.deployment_authorized is False
    assert _inventory(tmp_path) == before


def test_enabled_review_candidate_still_grants_no_authority_and_tamper_blocks(tmp_path):
    root = _repository(tmp_path)
    _runner.outputs = [REVISION, "main", "", REVISION, "main", ""]
    result = review.review_deployment_runtime_candidate(
        config_id="oci-deployment-review-2",
        repository_root=root,
        run_root=tmp_path / "run",
        capability_enabled=True,
        hostname_reader=lambda: "dell5820",
        user_reader=lambda: "hui",
        command_runner=_runner,
    )
    assert review.candidate_from_review(result).capability_enabled is True
    assert result.deployment_authorized is False
    assert "separate_installation" in result.reason_code

    with pytest.raises(review.OciDashboardDeploymentReviewError, match="boundary"):
        review.candidate_from_review(
            replace(result, installation_performed=True)
        )
    changed = replace(
        result,
        capability_candidate_enabled=False,
        logical_content_fingerprint="",
    )
    payload = changed.as_dict()
    payload.pop("logical_content_fingerprint")
    changed = replace(
        changed,
        logical_content_fingerprint=review._fingerprint(payload),
    )
    with pytest.raises(review.OciDashboardDeploymentReviewError, match="identity"):
        review.candidate_from_review(changed)


def test_review_rejects_dirty_or_wrong_host_before_candidate(tmp_path):
    root = _repository(tmp_path)
    _runner.outputs = [REVISION, "main", " M changed"]
    with pytest.raises(review.OciDashboardDeploymentReviewError, match="clean main"):
        review.review_deployment_runtime_candidate(
            config_id="oci-deployment-review-3",
            repository_root=root,
            run_root=tmp_path / "run",
            hostname_reader=lambda: "dell5820",
            user_reader=lambda: "hui",
            command_runner=_runner,
        )
    with pytest.raises(review.OciDashboardDeploymentReviewError, match="Dell hui"):
        review.review_deployment_runtime_candidate(
            config_id="oci-deployment-review-4",
            repository_root=root,
            run_root=tmp_path / "run",
            hostname_reader=lambda: "windows",
            user_reader=lambda: "hui",
            command_runner=lambda *_a, **_k: pytest.fail("git must not run"),
        )


def _inventory(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }
