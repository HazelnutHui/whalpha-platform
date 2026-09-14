from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.persistence.eod_read import EodInstrumentPresenceSessionRead
from tip_api.services import strong_leader_pullback_terminal_boundary_census as service
from tip_api.services import strong_leader_pullback_terminal_boundary_census_cli as cli
from tip_api.services.market_calendar import ExchangeCalendar


SHA_A = "a" * 64
SHA_B = "b" * 64


def test_boundary_census_separates_identity_and_eod_boundaries() -> None:
    inputs = _inputs()
    inputs.pop("signal_index")
    report = service._build_report(
        **inputs,
        implementation_revision="1" * 40,
        evaluated_at=datetime(2026, 9, 14, 8, tzinfo=timezone.utc),
    )

    assert report.lifecycle_instrument_count == 2
    assert report.changed_instrument_count == 1
    assert report.newly_horizon_5_in_scope_instrument_count == 1
    assert report.legacy_horizon_5_crossing_instrument_count == 1
    assert report.corrected_horizon_5_crossing_instrument_count == 2
    assert report.legacy_horizon_5_crossing_path_count == 1
    assert report.corrected_horizon_5_crossing_path_count == 2
    assert report.terminal_outcome_count == 0
    assert report.research_admission_count == 0


def test_boundary_census_rejects_missing_signal_session_eod() -> None:
    inputs = _inputs()
    reads = list(inputs["eod_reads"])
    signal_session = inputs["extended_sessions"][inputs["signal_index"]]
    index = next(
        index
        for index, item in enumerate(reads)
        if item.integrity.session_date == signal_session
    )
    reads[index] = EodInstrumentPresenceSessionRead(
        integrity=reads[index].integrity,
        instrument_ids=frozenset(),
        available_at=reads[index].available_at,
    )
    inputs["eod_reads"] = tuple(reads)
    inputs.pop("signal_index")

    with pytest.raises(
        service.StrongLeaderPullbackTerminalBoundaryCensusError,
        match="signal-session EOD",
    ):
        service._build_report(
            **inputs,
            implementation_revision="1" * 40,
            evaluated_at=datetime(2026, 9, 14, 8, tzinfo=timezone.utc),
        )


def test_boundary_census_write_is_immutable_and_formally_reread(
    tmp_path: Path,
) -> None:
    inputs = _inputs()
    inputs.pop("signal_index")
    report = service._build_report(
        **inputs,
        implementation_revision="1" * 40,
        evaluated_at=datetime(2026, 9, 14, 8, tzinfo=timezone.utc),
    )
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    output = custody / "census=v1"

    first = service._write_report(
        output_root=output, output_custody_root=custody, report=report
    )
    second = service._write_report(
        output_root=output, output_custody_root=custody, report=report
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert (output / service.REPORT_FILE).stat().st_mode & 0o777 == 0o400


def test_boundary_census_cli_fails_closed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "1" * 40)

    def stopped(**_kwargs: object) -> object:
        raise service.StrongLeaderPullbackTerminalBoundaryCensusError("stopped")

    monkeypatch.setattr(
        service,
        "build_strong_leader_pullback_terminal_boundary_census",
        stopped,
    )

    assert cli.main(_cli_args()) == 1
    output = capsys.readouterr().err
    assert '"status":"stopped"' in output
    assert '"canonical_data_write_count":0' in output


def _inputs() -> dict[str, object]:
    calendar = ExchangeCalendar()
    signal_sessions = calendar.sessions_in_range(
        service.STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION,
        service.STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
    )
    extended = calendar.sessions_before(signal_sessions[0], 20) + signal_sessions
    for _ in range(5):
        extended += (calendar.next_session(extended[-1]),)
    signal_index = extended.index(
        next(
            day
            for day in signal_sessions
            if day.year == 2025 and day.month == 12 and day.day >= 1
        )
    )
    new_id = UUID(int=1)
    aligned_id = UUID(int=2)
    new_identity_last = extended[signal_index + 5]
    new_eod_last = extended[signal_index + 4]
    aligned_last = extended[signal_index + 3]
    records = (
        SimpleNamespace(
            instrument_id=new_id,
            canonical_first_observed_date=extended[0],
            canonical_last_observed_date=new_identity_last,
            provider_delist_date_candidate=extended[signal_index + 5],
            included_path_count=1,
            horizon_1_crosses_last_observed_path_count=0,
            horizon_3_crosses_last_observed_path_count=0,
            horizon_5_crosses_last_observed_path_count=0,
        ),
        SimpleNamespace(
            instrument_id=aligned_id,
            canonical_first_observed_date=extended[0],
            canonical_last_observed_date=aligned_last,
            provider_delist_date_candidate=extended[signal_index + 4],
            included_path_count=1,
            horizon_1_crosses_last_observed_path_count=0,
            horizon_3_crosses_last_observed_path_count=0,
            horizon_5_crosses_last_observed_path_count=1,
        ),
    )
    manifest = SimpleNamespace(
        development_census_sha256=SHA_A,
        development_census_logical_fingerprint=SHA_B,
        membership_binding_fingerprint=SHA_A,
        logical_fingerprint=SHA_B,
        horizon_1_lifecycle_crossing_path_count=0,
        horizon_3_lifecycle_crossing_path_count=0,
        horizon_5_lifecycle_crossing_path_count=1,
        horizon_1_lifecycle_crossing_instrument_count=0,
        horizon_3_lifecycle_crossing_instrument_count=0,
        horizon_5_lifecycle_crossing_instrument_count=1,
    )
    blocker = SimpleNamespace(
        manifest=manifest,
        manifest_sha256=SHA_A,
        lifecycle_records=records,
    )
    eod_scope = tuple(
        item for item in extended if signal_sessions[0] <= item <= extended[-1]
    )
    reads = tuple(
        EodInstrumentPresenceSessionRead(
            integrity=SimpleNamespace(
                session_date=session,
                record_count=2,
                content_fingerprint=SHA_A,
                parquet_sha256=SHA_B,
                identity_snapshot_date=session,
                identity_snapshot_fingerprint=SHA_A,
            ),
            instrument_ids=frozenset(
                {
                    *({new_id} if session <= new_eod_last else set()),
                    *({aligned_id} if session <= aligned_last else set()),
                }
            ),
            available_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
        )
        for session in eod_scope
    )
    return {
        "blocker": blocker,
        "development": SimpleNamespace(logical_fingerprint=SHA_B),
        "development_sha256": SHA_A,
        "membership_binding": SHA_A,
        "extended_sessions": extended,
        "signal_sessions": signal_sessions,
        "signals": {new_id: (signal_index,), aligned_id: (signal_index,)},
        "eod_reads": reads,
        "signal_index": signal_index,
    }


def _cli_args() -> list[str]:
    return [
        "--data-root",
        "/data/trading-intelligence-platform",
        "--development-census",
        "/tmp/development",
        "--blocker-census",
        "/tmp/blocker",
        "--blocker-census-custody-root",
        "/tmp",
        "--output-root",
        "/tmp/census=v1",
        "--output-custody-root",
        "/tmp",
        "--evaluated-at",
        "2026-09-14T08:00:00Z",
        "--execute",
    ]
