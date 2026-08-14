from __future__ import annotations

import os
from pathlib import Path

import pytest

from tip_api.providers.massive.credential import (
    MASSIVE_ENV_FILE_ENV,
    MassiveCredentialFileError,
    load_massive_provider_config_from_file,
)

SENTINEL_SECRET = "test-secret-must-never-appear"


def write_credential(path: Path, text: str, mode: int = 0o600) -> Path:
    path.write_text(text)
    path.chmod(mode)
    return path


def test_credential_file_permission_correct(tmp_path: Path) -> None:
    path = write_credential(tmp_path / "massive.env", f"TIP_MASSIVE_API_KEY={SENTINEL_SECRET}\n")

    config = load_massive_provider_config_from_file(path)

    assert config.api_key.get_secret_value() == SENTINEL_SECRET
    assert SENTINEL_SECRET not in repr(config)


def test_env_file_path_can_be_overridden_by_non_secret_environment(tmp_path: Path) -> None:
    path = write_credential(tmp_path / "massive.env", f"TIP_MASSIVE_API_KEY={SENTINEL_SECRET}\n")

    config = load_massive_provider_config_from_file(environ={MASSIVE_ENV_FILE_ENV: str(path)})

    assert config.api_key.get_secret_value() == SENTINEL_SECRET


def test_symlink_is_rejected(tmp_path: Path) -> None:
    target = write_credential(tmp_path / "target.env", f"TIP_MASSIVE_API_KEY={SENTINEL_SECRET}\n")
    link = tmp_path / "massive.env"
    link.symlink_to(target)

    with pytest.raises(MassiveCredentialFileError, match="symlink"):
        load_massive_provider_config_from_file(link)


def test_group_or_other_readable_is_rejected(tmp_path: Path) -> None:
    path = write_credential(tmp_path / "massive.env", f"TIP_MASSIVE_API_KEY={SENTINEL_SECRET}\n", mode=0o640)

    with pytest.raises(MassiveCredentialFileError, match="group or other"):
        load_massive_provider_config_from_file(path)


def test_owner_mismatch_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_credential(tmp_path / "massive.env", f"TIP_MASSIVE_API_KEY={SENTINEL_SECRET}\n")
    monkeypatch.setattr(os, "getuid", lambda: path.stat().st_uid + 1)

    with pytest.raises(MassiveCredentialFileError, match="current user"):
        load_massive_provider_config_from_file(path)


@pytest.mark.parametrize(
    "content, match",
    [
        ("TIP_MASSIVE_API_KEY\n", "Malformed"),
        (f"TIP_MASSIVE_API_KEY={SENTINEL_SECRET}\nTIP_MASSIVE_API_KEY=second\n", "Duplicate"),
        (f"TIP_MASSIVE_API_KEY={SENTINEL_SECRET}\nUNKNOWN=x\n", "Unsupported"),
        ("TIP_MASSIVE_API_KEY=   \n", "Massive API key is required"),
        (f"export TIP_MASSIVE_API_KEY={SENTINEL_SECRET}\n", "export"),
        ("TIP_MASSIVE_API_KEY=$(cat secret)\n", "shell syntax"),
        ("TIP_MASSIVE_API_KEY=`cat secret`\n", "shell syntax"),
    ],
)
def test_credential_file_rejects_unsafe_or_malformed_lines(tmp_path: Path, content: str, match: str) -> None:
    path = write_credential(tmp_path / "massive.env", content)

    with pytest.raises((MassiveCredentialFileError, ValueError), match=match) as exc_info:
        load_massive_provider_config_from_file(path)

    assert SENTINEL_SECRET not in str(exc_info.value)
