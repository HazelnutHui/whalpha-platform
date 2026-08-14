"""Credential-file loading for Massive provider configuration."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Mapping

from tip_api.providers.massive.config import (
    MASSIVE_API_KEY_ENV,
    MASSIVE_BASE_URL_ENV,
    MASSIVE_TIMEOUT_ENV,
    MassiveProviderConfig,
)

MASSIVE_ENV_FILE_ENV = "TIP_MASSIVE_ENV_FILE"
DEFAULT_MASSIVE_ENV_FILE = Path("~/.config/trading-intelligence-platform/massive.env")
_ALLOWED_KEYS = frozenset({MASSIVE_API_KEY_ENV, MASSIVE_BASE_URL_ENV, MASSIVE_TIMEOUT_ENV})


class MassiveCredentialFileError(ValueError):
    """Raised when the Massive credential file boundary is invalid."""


def load_massive_provider_config_from_file(
    path: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> MassiveProviderConfig:
    """Load Massive provider config from a tightly parsed env file.

    This function never evaluates shell syntax and never prints or logs secret
    values. Only the supported Massive configuration keys are accepted.
    """

    env = os.environ if environ is None else environ
    credential_path = _resolve_credential_path(path, env)
    _validate_credential_file_metadata(credential_path)
    return MassiveProviderConfig.from_environment(_parse_env_file(credential_path))


def _resolve_credential_path(path: str | Path | None, environ: Mapping[str, str]) -> Path:
    if path is None:
        path = environ.get(MASSIVE_ENV_FILE_ENV, str(DEFAULT_MASSIVE_ENV_FILE))
    text = str(path).strip()
    if not text:
        raise MassiveCredentialFileError("Massive credential file path must not be empty")
    return Path(text).expanduser()


def _validate_credential_file_metadata(path: Path) -> None:
    try:
        link_stat = path.lstat()
    except FileNotFoundError as exc:
        raise MassiveCredentialFileError("Massive credential file does not exist") from exc
    if stat.S_ISLNK(link_stat.st_mode):
        raise MassiveCredentialFileError("Massive credential file must not be a symlink")
    if not stat.S_ISREG(link_stat.st_mode):
        raise MassiveCredentialFileError("Massive credential file must be a regular file")
    if link_stat.st_uid != os.getuid():
        raise MassiveCredentialFileError("Massive credential file must be owned by the current user")
    if link_stat.st_mode & 0o077:
        raise MassiveCredentialFileError("Massive credential file must not be readable or writable by group or other")


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text().splitlines()
    except UnicodeDecodeError as exc:
        raise MassiveCredentialFileError("Massive credential file must be UTF-8 text") from exc
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            raise MassiveCredentialFileError("Massive credential file must not use export syntax")
        if "=" not in stripped:
            raise MassiveCredentialFileError(f"Malformed Massive credential file line: {line_number}")
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in _ALLOWED_KEYS:
            raise MassiveCredentialFileError(f"Unsupported Massive credential key on line: {line_number}")
        if key in values:
            raise MassiveCredentialFileError(f"Duplicate Massive credential key on line: {line_number}")
        if "$(" in value or "`" in value or ";" in value or "&&" in value or "||" in value:
            raise MassiveCredentialFileError(f"Unsupported shell syntax in Massive credential file line: {line_number}")
        values[key] = value
    return values
