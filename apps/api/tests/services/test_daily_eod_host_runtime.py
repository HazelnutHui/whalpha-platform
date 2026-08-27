from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from tip_api.services.daily_eod_host_runtime import (
    DailyEodHostRuntimeError,
    build_host_runtime_config_candidate,
    canonical_host_runtime_config_bytes,
    read_host_runtime_config,
    verify_dell_runtime,
)
from tip_api.services.daily_eod_readiness import DailyEodReadinessPolicy
from tip_api.services.daily_eod_standing_authorization import (
    APPROVED_CANONICAL_DATA_ROOT,
)


REVISION = "a" * 40
POLICY = DailyEodReadinessPolicy().logical_fingerprint
REPOSITORY = Path("/opt/trading-intelligence-platform")
RUN_ROOT = Path("/var/lib/trading-intelligence-platform/daily-eod")
AUTH_ROOT = Path("/etc/trading-intelligence-platform/authorization")


def candidate(**overrides):
    values = {
        "config_id": "dell-daily-eod-runtime-v1",
        "host": "dell5820",
        "repository_root": REPOSITORY,
        "implementation_revision": REVISION,
        "data_root": APPROVED_CANONICAL_DATA_ROOT,
        "run_root": RUN_ROOT,
        "authorization_root": AUTH_ROOT,
        "authorization_path": AUTH_ROOT / "daily-eod.json",
        "authorization_file_sha256": "b" * 64,
        "credential_path": Path("/etc/trading-intelligence-platform/massive.env"),
        "readiness_policy_fingerprint": POLICY,
        "capabilities_enabled": False,
    }
    values.update(overrides)
    return build_host_runtime_config_candidate(**values)


def test_candidate_is_default_disabled_and_cannot_authorize_scheduler() -> None:
    config = candidate()

    assert config.capabilities_enabled is False
    assert config.one_transition_per_invocation is True
    assert config.scheduler_enabled is False
    assert config.publication_authorized is False
    assert config.deployment_authorized is False
    assert len(config.config_content_sha256) == 64


def test_candidate_rejects_wrong_data_root_or_in_repository_credential() -> None:
    with pytest.raises(ValidationError, match="path boundary"):
        candidate(data_root=Path("/data"))
    with pytest.raises(ValidationError, match="path boundary"):
        candidate(credential_path=REPOSITORY / "secret.env")


def test_owner_only_canonical_config_requires_external_file_sha(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    root.mkdir(mode=0o700)
    path = root / "host.json"
    raw = canonical_host_runtime_config_bytes(candidate())
    path.write_bytes(raw)
    path.chmod(0o400)

    loaded = read_host_runtime_config(
        config_path=path,
        config_root=root,
        repository_root=REPOSITORY,
        expected_file_sha256=hashlib.sha256(raw).hexdigest(),
    )

    assert loaded.config_id == "dell-daily-eod-runtime-v1"
    with pytest.raises(DailyEodHostRuntimeError, match="SHA mismatch"):
        read_host_runtime_config(
            config_path=path,
            config_root=root,
            repository_root=REPOSITORY,
            expected_file_sha256="c" * 64,
        )


def test_runtime_config_rejects_unsafe_mode_or_noncanonical_bytes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    root.mkdir(mode=0o700)
    path = root / "host.json"
    path.write_text("{}", encoding="utf-8")
    path.chmod(0o600)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(DailyEodHostRuntimeError, match="custody is unsafe"):
        read_host_runtime_config(
            config_path=path,
            config_root=root,
            repository_root=REPOSITORY,
            expected_file_sha256=expected,
        )


def runner(*, revision: str = REVISION, status: str = ""):
    def run(command, **_kwargs):
        output = revision + "\n" if "rev-parse" in command else status
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    return run


def test_runtime_verifies_actual_host_clean_revision_and_current_policy(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    config = candidate(repository_root=repository)

    verified = verify_dell_runtime(
        config=config,
        source_repository_root=repository,
        hostname_reader=lambda: "dell5820.example",
        command_runner=runner(),
    )

    assert verified.host == "dell5820"
    assert verified.implementation_revision == REVISION
    assert verified.worktree_clean is True


@pytest.mark.parametrize(
    ("hostname", "command_runner", "match"),
    (
        ("other-host", runner(), "actual host"),
        ("dell5820", runner(revision="d" * 40), "revision differs"),
        ("dell5820", runner(status=" M changed.py\n"), "not clean"),
    ),
)
def test_runtime_fails_closed_on_host_revision_or_dirty_tree(
    tmp_path: Path,
    hostname: str,
    command_runner,
    match: str,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    config = candidate(repository_root=repository)

    with pytest.raises(DailyEodHostRuntimeError, match=match):
        verify_dell_runtime(
            config=config,
            source_repository_root=repository,
            hostname_reader=lambda: hostname,
            command_runner=command_runner,
        )


def test_executing_source_root_must_equal_pinned_repository(tmp_path: Path) -> None:
    source = tmp_path / "other-source"
    source.mkdir()

    with pytest.raises(DailyEodHostRuntimeError, match="executing source"):
        verify_dell_runtime(
            config=candidate(),
            source_repository_root=source,
            hostname_reader=lambda: "dell5820",
            command_runner=runner(),
        )
