from __future__ import annotations

import socket
from datetime import date, timedelta
from uuid import UUID

import pytest

from tip_api.services.strong_leader_pullback_diagnostics_cli import (
    _network_disabled,
    _split_path_status,
)


IDS = tuple(
    UUID(f"00000000-0000-4000-8000-{index:012d}") for index in range(1, 4)
)


def _sessions():
    first = date(2026, 1, 2)
    return tuple(first + timedelta(days=index) for index in range(21))


def test_split_status_distinguishes_clear_exposure_from_quarantine():
    sessions = _sessions()
    active = {(IDS[0], sessions[5]), (IDS[2], sessions[6])}
    unresolved = {(IDS[1], sessions[7])}

    hazard, clear = _split_path_status(
        required_ids=frozenset(IDS),
        sessions=sessions,
        active_action_keys=active,
        quarantined_action_keys=set(),
        unresolved_impact_keys=unresolved,
        clear_adjustments={(IDS[0], sessions[0]): object()},
        quarantined_adjustment_keys=set(),
        action_start=sessions[0],
        adjustment_start=sessions[0],
    )

    assert hazard == frozenset((IDS[1], IDS[2]))
    assert clear == frozenset((IDS[0],))


def test_split_status_rejects_the_whole_uncovered_window():
    sessions = _sessions()

    hazard, clear = _split_path_status(
        required_ids=frozenset(IDS),
        sessions=sessions,
        active_action_keys=set(),
        quarantined_action_keys=set(),
        unresolved_impact_keys=set(),
        clear_adjustments={},
        quarantined_adjustment_keys=set(),
        action_start=sessions[1],
        adjustment_start=sessions[0],
    )

    assert hazard == frozenset(IDS)
    assert clear == frozenset()


def test_quarantined_adjustment_without_an_active_window_event_is_not_promoted():
    sessions = _sessions()

    hazard, clear = _split_path_status(
        required_ids=frozenset((IDS[0],)),
        sessions=sessions,
        active_action_keys=set(),
        quarantined_action_keys=set(),
        unresolved_impact_keys=set(),
        clear_adjustments={},
        quarantined_adjustment_keys={(IDS[0], sessions[5])},
        action_start=sessions[0],
        adjustment_start=sessions[0],
    )

    assert hazard == frozenset()
    assert clear == frozenset()


def test_diagnostic_runner_disables_and_restores_network_access():
    original = socket.socket

    with _network_disabled():
        with pytest.raises(RuntimeError, match="network access is disabled"):
            socket.socket()

    assert socket.socket is original
