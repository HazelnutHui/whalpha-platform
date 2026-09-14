from __future__ import annotations

from decimal import Decimal

import pytest

from tip_api.services import strong_leader_pullback_terminal_gap_census_v4 as service


def test_extract_timing_evidence_normalizes_and_bounds_context() -> None:
    text = (
        "Before.\nThe exchange will maintain the halt on trading, effective at "
        "8:00 p.m. Eastern time on February 26, 2026, through the day on "
        "February 27, 2026. After."
    )

    evidence = service._extract_timing_evidence(
        text,
        r"maintain the halt on trading.{0,180}effective at 8:00 p\.m\. Eastern "
        r"time on February 26, 2026.{0,180}through the day on February 27, 2026",
    )

    assert "maintain the halt on trading" in evidence
    assert "through the day on February 27, 2026" in evidence
    assert "\n" not in evidence


def test_extract_timing_evidence_rejects_ambiguous_match() -> None:
    with pytest.raises(
        service.StrongLeaderPullbackTerminalGapCensusV4Error,
        match="exact timing evidence differs",
    ):
        service._extract_timing_evidence("halt halt", r"halt")


def test_fixed_values_preserve_declared_precision() -> None:
    assert service._fixed(Decimal("64.05652"), 16) == "64.0565200000000000"
    assert service._fixed(Decimal("79.03"), 10) == "79.0300000000"


def test_ruleset_binds_all_five_cases() -> None:
    assert service._EXPECTED_SEQUENCES == frozenset({92, 109, 136, 161, 194})
    assert len(service._ruleset_fingerprint()) == 64
