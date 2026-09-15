from __future__ import annotations

import socket

import pytest

from tip_api.services import quant_research_factor_screening_cli as service


def test_screening_code_hashes_are_stable_and_distinct() -> None:
    label = service._label_code_sha256()
    screening = service._screening_code_sha256()

    assert len(label) == 64
    assert len(screening) == 64
    assert label != screening
    assert label == service._label_code_sha256()
    assert screening == service._screening_code_sha256()


def test_runner_network_guard_rejects_socket_creation() -> None:
    with service._network_disabled():
        with pytest.raises(RuntimeError, match="network access is disabled"):
            socket.socket()
