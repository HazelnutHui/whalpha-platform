from __future__ import annotations

import hashlib
import socket
from pathlib import Path

import pytest

from tip_api.services import quant_research_factor_diagnostics_cli as service


def test_code_fingerprints_bind_exact_calculation_and_diagnostic_files() -> None:
    assert service._calculation_code_sha256() == service._calculation_code_sha256()
    assert service._diagnostic_code_sha256() == service._diagnostic_code_sha256()
    assert service._calculation_code_sha256() != service._diagnostic_code_sha256()
    assert len(service._calculation_code_sha256()) == 64


def test_combined_sha256_is_order_independent_and_content_bound(tmp_path) -> None:
    first = tmp_path / "a"
    second = tmp_path / "b"
    first.write_bytes(b"one")
    second.write_bytes(b"two")

    expected = service._combined_sha256((first, second))
    assert service._combined_sha256((second, first)) == expected
    second.write_bytes(b"changed")
    assert service._combined_sha256((first, second)) != expected


def test_network_guard_rejects_socket_creation() -> None:
    with service._network_disabled():
        with pytest.raises(RuntimeError, match="network access is disabled"):
            socket.socket()
