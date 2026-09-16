from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from tip_api.contracts.analytics.v1.quant_research_market_state_vector import (
    QuantResearchMarketStateAvailability,
)
from tip_api.services import quant_research_market_state_qualification_cli as cli
from tip_api.services.quant_research_market_state_vector import (
    QuantResearchMarketStateBarV1,
)


def test_market_state_membership_read_binds_manifest_hashes(
    tmp_path, monkeypatch
) -> None:
    sessions = (date(2026, 1, 2), date(2026, 1, 5))
    partitions = {}
    for index, session in enumerate(sessions):
        partition = tmp_path / session.isoformat()
        partition.mkdir()
        (partition / "manifest.json").write_bytes(f"manifest-{index}".encode())
        partitions[session] = partition
    calls = []

    def read_membership(*, shadow_root, partition, census_session):
        calls.append((shadow_root, partition, census_session.session_date))
        return (
            (SimpleNamespace(instrument_id=UUID(int=len(calls))),),
            f"{len(calls):064x}",
        )

    monkeypatch.setattr(cli, "_read_membership", read_membership)
    census = SimpleNamespace(
        sessions=tuple(SimpleNamespace(session_date=item) for item in sessions)
    )

    memberships, logical, hashes = cli._read_market_state_memberships(
        shadow_root=tmp_path,
        partitions=partitions,
        census=census,
        ordered_sessions=sessions,
    )

    assert len(calls) == 2
    assert tuple(memberships) == sessions
    assert memberships[sessions[0]] == (UUID(int=1),)
    assert memberships[sessions[1]] == (UUID(int=2),)
    assert all(len(value) == 64 for value in logical.values())
    assert all(len(value) == 64 for value in hashes.values())


def test_market_state_session_retains_one_benchmark_quarantine(
    monkeypatch,
) -> None:
    sessions = tuple(date(2026, 1, 1) + timedelta(days=index) for index in range(21))
    member_ids = tuple(UUID(int=1000 + index) for index in range(600))
    benchmark_ids = {
        "SPY": UUID(int=1),
        "QQQ": UUID(int=2),
        "IWM": UUID(int=3),
        "DIA": UUID(int=4),
    }
    every_id = (*member_ids, *benchmark_ids.values())
    window = tuple(
        (session, {instrument_id: object() for instrument_id in every_id})
        for session in sessions
    )

    monkeypatch.setattr(cli, "_valid_bar", lambda bar: True)
    monkeypatch.setattr(
        cli,
        "_split_path_status",
        lambda **kwargs: (frozenset({benchmark_ids["QQQ"]}), frozenset()),
    )

    def series(*, instrument_id, source_sessions, **kwargs):
        return tuple(
            QuantResearchMarketStateBarV1(
                session=session,
                close=Decimal("100") + Decimal(index),
            )
            for index, session in enumerate(source_sessions)
        )

    monkeypatch.setattr(cli, "_market_state_series", series)
    value = cli._build_session(
        source_session=sessions[-1],
        window=window,
        member_ids=member_ids,
        membership_logical_fingerprint="2" * 64,
        membership_manifest_sha256="1" * 64,
        benchmark_ids=benchmark_ids,
        active_action_keys=set(),
        quarantined_action_keys=set(),
        unresolved_impact_keys=set(),
        clear_adjustments={},
        quarantined_adjustment_keys=set(),
        action_start=sessions[0],
        adjustment_start=sessions[0],
    )
    by_id = {item.metric_id: item for item in value.metrics}

    assert value.declared_member_count == 600
    assert value.complete_member_count == 600
    assert by_id["spy_log_return_20s"].availability is (
        QuantResearchMarketStateAvailability.AVAILABLE
    )
    assert by_id["qqq_spy_relative_log_return_20s"].availability is (
        QuantResearchMarketStateAvailability.UNAVAILABLE
    )
    assert by_id["broad_etf_mean_log_distance_to_sma20"].availability is (
        QuantResearchMarketStateAvailability.UNAVAILABLE
    )
    assert by_id["reconstructed_member_above_sma20_share"].availability is (
        QuantResearchMarketStateAvailability.AVAILABLE
    )


def test_market_state_session_represents_zero_member_warmup_without_failing(
    monkeypatch,
) -> None:
    sessions = tuple(date(2026, 1, 1) + timedelta(days=index) for index in range(21))
    benchmark_ids = {
        "SPY": UUID(int=1),
        "QQQ": UUID(int=2),
        "IWM": UUID(int=3),
        "DIA": UUID(int=4),
    }
    window = tuple(
        (
            session,
            {instrument_id: object() for instrument_id in benchmark_ids.values()},
        )
        for session in sessions
    )

    monkeypatch.setattr(cli, "_valid_bar", lambda bar: True)
    monkeypatch.setattr(
        cli,
        "_split_path_status",
        lambda **kwargs: (frozenset(), frozenset()),
    )
    monkeypatch.setattr(
        cli,
        "_market_state_series",
        lambda *, source_sessions, **kwargs: tuple(
            QuantResearchMarketStateBarV1(
                session=session,
                close=Decimal("100") + Decimal(index),
            )
            for index, session in enumerate(source_sessions)
        ),
    )

    value = cli._build_session(
        source_session=sessions[-1],
        window=window,
        member_ids=(),
        membership_logical_fingerprint="2" * 64,
        membership_manifest_sha256="1" * 64,
        benchmark_ids=benchmark_ids,
        active_action_keys=set(),
        quarantined_action_keys=set(),
        unresolved_impact_keys=set(),
        clear_adjustments={},
        quarantined_adjustment_keys=set(),
        action_start=sessions[0],
        adjustment_start=sessions[0],
    )

    assert value.declared_member_count == 0
    assert value.complete_member_count == 0
    assert all(
        item.expected_observations == 1
        and item.actual_observations == 0
        and item.availability is QuantResearchMarketStateAvailability.UNAVAILABLE
        for item in value.metrics[6:]
    )
