"""Secure SEC User-Agent configuration-file loader."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Mapping

from tip_api.providers.sec.config import SEC_USER_AGENT_ENV, SecProviderConfig

SEC_ENV_FILE_ENV = "TIP_SEC_ENV_FILE"
DEFAULT_SEC_ENV_FILE = Path("~/.config/trading-intelligence-platform/sec.env")


class SecCredentialFileError(ValueError):
    """A fixed, non-secret SEC configuration error."""


def load_sec_provider_config_from_file(
    path: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> SecProviderConfig:
    env = os.environ if environ is None else environ
    candidate = path if path is not None else env.get(SEC_ENV_FILE_ENV, str(DEFAULT_SEC_ENV_FILE))
    config_path = Path(str(candidate).strip()).expanduser()
    if not str(candidate).strip():
        raise SecCredentialFileError("SEC configuration file path is invalid")
    _validate_metadata(config_path)
    return SecProviderConfig.from_environment(_parse_file(config_path))


def _validate_metadata(path: Path) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise SecCredentialFileError("SEC configuration file is unavailable") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise SecCredentialFileError("SEC configuration file must not be a symlink")
    if not stat.S_ISREG(metadata.st_mode):
        raise SecCredentialFileError("SEC configuration file must be a regular file")
    if metadata.st_uid != os.getuid():
        raise SecCredentialFileError("SEC configuration file must be owned by the current user")
    if metadata.st_mode & 0o077:
        raise SecCredentialFileError("SEC configuration file permissions are too broad")


def _parse_file(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise SecCredentialFileError("SEC configuration file must be UTF-8") from exc
    values: dict[str, str] = {}
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export ") or "=" not in stripped:
            raise SecCredentialFileError(f"SEC configuration line {line_number} is invalid")
        key, value = stripped.split("=", 1)
        if key.strip() != SEC_USER_AGENT_ENV or key.strip() in values:
            raise SecCredentialFileError(f"SEC configuration line {line_number} is unsupported")
        if any(token in value for token in ("$(", "`", "\n", "\r")):
            raise SecCredentialFileError(f"SEC configuration line {line_number} is invalid")
        values[key.strip()] = value.strip()
    return values
