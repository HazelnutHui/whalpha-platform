from pathlib import Path
import os

import pytest
from pydantic import ValidationError

from tip_api.providers.sec.config import SEC_USER_AGENT_ENV, SecProviderConfig
from tip_api.providers.sec.credential import SecCredentialFileError, load_sec_provider_config_from_file

SENTINEL = "trading-intelligence-platform fixture-contact@invalid.example"


def write_config(path: Path, content: str, mode: int = 0o600) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)
    return path


def test_config_uses_secret_and_redacts_user_agent() -> None:
    config = SecProviderConfig.from_environment({SEC_USER_AGENT_ENV: SENTINEL})
    assert config.user_agent.get_secret_value() == SENTINEL
    assert SENTINEL not in repr(config) and "fixture-contact" not in repr(config)


@pytest.mark.parametrize("value", ["", "browser-agent", "trading-intelligence-platform no-contact"])
def test_invalid_user_agent_error_is_redacted(value: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        SecProviderConfig.from_environment({SEC_USER_AGENT_ENV: value})
    assert value not in str(exc_info.value) or not value


def test_loader_accepts_only_whitelisted_secure_file(tmp_path: Path) -> None:
    path = write_config(tmp_path / "sec.env", f"{SEC_USER_AGENT_ENV}={SENTINEL}\n")
    loaded = load_sec_provider_config_from_file(path, environ={})
    assert loaded.user_agent.get_secret_value() == SENTINEL


def test_loader_rejects_symlink_and_broad_permissions(tmp_path: Path) -> None:
    target = write_config(tmp_path / "target", f"{SEC_USER_AGENT_ENV}={SENTINEL}\n")
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(SecCredentialFileError, match="symlink"):
        load_sec_provider_config_from_file(link)
    target.chmod(0o640)
    with pytest.raises(SecCredentialFileError, match="permissions"):
        load_sec_provider_config_from_file(target)


def test_loader_rejects_owner_mismatch_without_leaking_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_config(tmp_path / "sec.env", f"{SEC_USER_AGENT_ENV}={SENTINEL}\n")
    monkeypatch.setattr(os, "getuid", lambda: path.stat().st_uid + 1)
    with pytest.raises(SecCredentialFileError) as exc_info:
        load_sec_provider_config_from_file(path)
    assert SENTINEL not in str(exc_info.value)


@pytest.mark.parametrize("content", [
    "UNKNOWN=value\n",
    f"{SEC_USER_AGENT_ENV}={SENTINEL}\n{SEC_USER_AGENT_ENV}=duplicate\n",
    f"export {SEC_USER_AGENT_ENV}={SENTINEL}\n",
    f"{SEC_USER_AGENT_ENV}=$(cat private)\n",
])
def test_loader_rejects_unapproved_syntax_without_exposure(tmp_path: Path, content: str) -> None:
    path = write_config(tmp_path / "sec.env", content)
    with pytest.raises((SecCredentialFileError, ValidationError)) as exc_info:
        load_sec_provider_config_from_file(path)
    assert SENTINEL not in str(exc_info.value)
