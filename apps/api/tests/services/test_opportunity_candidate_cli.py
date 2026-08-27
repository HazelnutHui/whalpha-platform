from __future__ import annotations

import socket
import shutil
import tempfile
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid5

import pytest

from tip_api.parameters.market_regime.candidate_v1_1_1 import CANDIDATE_STATE_PARAMETER_FINGERPRINT
from tip_api.parameters.market_regime.state_v1_0_1 import STATE_CALCULATION_VERSION, STATE_PARAMETER_FINGERPRINT
from tip_api.services import opportunity_candidate_cli as cli
from tip_api.services.opportunity_candidate_audit import (
    OpportunityCandidateAuditError,
    read_opportunity_candidate_audit_contents,
    write_opportunity_candidate_audit,
)
from tip_api.services.market_regime_sources import (
    MarketRegimeBar,
    MarketRegimeInputPanel,
    MarketRegimeSourceSession,
    MarketRegimeUniverseSource,
)


PRIMARY = "provider_classified_common_shares_v1"
SECONDARY = "provider_classified_common_shares_plus_adrs_v1"
NS = UUID("f400a08a-1b6c-5bb4-9c66-b28ddf9bf017")


def _id(label):
    return uuid5(NS, label)


def _panels():
    sessions = tuple(date(2026, 7, 1) + timedelta(days=index) for index in range(27))
    primary = tuple(_id(f"stock-{index}") for index in range(8))
    adrs = tuple(_id(f"adr-{index}") for index in range(2))
    etfs = {ticker: _id(f"etf-{ticker}") for ticker in ("SPY", "QQQ", "IWM", "DIA", "XLK", "SMH")}
    all_bars = []
    for day_index, session in enumerate(sessions):
        day = Decimal(day_index)
        for index, instrument_id in enumerate((*primary, *adrs)):
            close = Decimal("30") + Decimal(index) + day * (Decimal("0.15") + Decimal(index) / Decimal("100"))
            all_bars.append(_bar(instrument_id, f"S{index}" if index < 8 else f"A{index-8}", "common_stock", session, close, Decimal("3000000") + day * Decimal("20000")))
        for index, (ticker, instrument_id) in enumerate(etfs.items()):
            close = Decimal("90") + Decimal(index * 7) + day * (Decimal("0.2") + Decimal(index) / Decimal("50"))
            all_bars.append(_bar(instrument_id, ticker, "etf", session, close, Decimal("9000000") + day * Decimal("25000")))
    universe_rows = (
        MarketRegimeUniverseSource(PRIMARY, "Primary", True, 0, frozenset(primary), "a" * 64),
        MarketRegimeUniverseSource(SECONDARY, "Secondary", False, 1, frozenset((*primary, *adrs)), "b" * 64),
    )
    output = []
    for end in (25, 26):
        selected = sessions[end - 25 : end + 1]
        sources = tuple(MarketRegimeSourceSession(
            session_date=session, dataset_path=f"eod/{session}", record_count=16,
            content_fingerprint=f"{index+1:064x}", parquet_sha256=f"{index+101:064x}",
            identity_snapshot_date=session, identity_snapshot_fingerprint=f"{index+201:064x}",
        ) for index, session in enumerate(selected))
        output.append(MarketRegimeInputPanel(
            as_of_session=selected[-1], calendar_id="XNYS", calendar_version="fixture", sessions=selected,
            source_sessions=sources, bars=tuple(item for item in all_bars if item.session_date in set(selected)), universes=universe_rows,
            activation_pointer_fingerprint="c"*64, identity_logical_fingerprint="d"*64,
            eod_content_fingerprint="e"*64, eod_business_key_fingerprint="f"*64,
            history_source_fingerprint=("1" if end == 25 else "2")*64,
        ))
    return tuple(output)


def _bar(instrument_id, ticker, kind, session, close, volume):
    return MarketRegimeBar(
        instrument_id=instrument_id, ticker=ticker, instrument_type=kind, primary_exchange="XNYS",
        session_date=session, open=close, high=close*Decimal("1.01"), low=close*Decimal("0.99"), close=close, volume=volume,
    )


def _regime_records(panels):
    output = []
    for panel in panels:
        for index, universe_id in enumerate((PRIMARY, SECONDARY)):
            output.append(SimpleNamespace(
                as_of_session=panel.as_of_session, universe_id=universe_id,
                composite=Decimal("62.5") - Decimal(index), confirmed_state="balanced",
                logical_fingerprint=(f"{panel.as_of_session.toordinal()+index:064x}")[-64:],
            ))
    return tuple(output)


def test_verify_output_only_rereads_candidate_audit(monkeypatch, tmp_path, capsys) -> None:
    output = tmp_path / "candidate-audit"
    output.mkdir()
    calls = []
    monkeypatch.setattr(cli, "_audit_api", lambda: (
        lambda path: calls.append(("read", path)) or {"as_of_session": "2026-08-24", "oracle_mismatch_count": 0},
        lambda **kwargs: pytest.fail("writer must not run"),
        lambda path: pytest.fail("output validator must not run in reread mode"),
    ))
    monkeypatch.setattr(cli, "read_market_regime_state_audit", lambda path: pytest.fail("Phase1b must not be read"))
    monkeypatch.setattr(cli, "load_formal_market_regime_panels", lambda **kwargs: pytest.fail("/data must not be read"))
    assert cli.main([
        "--as-of-session", "2026-08-24", "--data-root", str(tmp_path),
        "--phase1b-audit", str(tmp_path / "phase1b"), "--output-dir", str(output), "--verify-output",
    ]) == 0
    assert calls == [("read", output)]
    assert '"status":"completed"' in capsys.readouterr().out


def test_relative_paths_are_rejected_before_any_reader(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_audit_api", lambda: pytest.fail("audit API must not load"))
    with pytest.raises(SystemExit):
        cli.main([
            "--as-of-session", "2026-08-24", "--data-root", "relative",
            "--phase1b-audit", "/tmp/phase1b", "--output-dir", "/tmp/candidates",
        ])


def test_socket_guard_blocks_connect_dns_and_restores() -> None:
    original = socket.socket
    with cli._offline_socket_guard():
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.create_connection(("127.0.0.1", 9))
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.getaddrinfo("example.invalid", 443)
        guarded = socket.socket()
        with pytest.raises(RuntimeError, match="network is prohibited"):
            guarded.connect(("127.0.0.1", 9))
        guarded.close()
    assert socket.socket is original


def test_phase1b_history_selects_only_full_candidate_panels() -> None:
    sessions = tuple(date(2026, 7, 1) + timedelta(days=index) for index in range(27))
    records = tuple(
        SimpleNamespace(
            as_of_session=session,
            universe_id=universe_id,
            logical_fingerprint=f"{session.toordinal() + index:064x}"[-64:],
        )
        for session in sessions[25:]
        for index, universe_id in enumerate((PRIMARY, SECONDARY))
    )
    cli._validate_phase1b(
        manifest={
            "calculation_version": STATE_CALCULATION_VERSION,
            "state_parameter_fingerprint": STATE_PARAMETER_FINGERPRINT,
            "as_of_session": sessions[-1].isoformat(),
            "universe_ids": [PRIMARY, SECONDARY],
        },
        state_records=records,
        source_payload={"history_sessions": [item.isoformat() for item in sessions]},
        current_payload={
            "records": [
                {
                    "universe_id": universe_id,
                    "current": {"logical_fingerprint": next(
                        item.logical_fingerprint for item in records
                        if item.as_of_session == sessions[-1] and item.universe_id == universe_id
                    )},
                }
                for universe_id in (PRIMARY, SECONDARY)
            ]
        },
        as_of_session=sessions[-1],
    )

    class FixtureCalendar:
        def sessions_before(self, session, count):
            index = sessions.index(session)
            return sessions[index - count:index]

    result = cli._select_candidate_sessions(
        state_records=records,
        available_eod_sessions=sessions,
        as_of_session=sessions[-1],
        calendar=FixtureCalendar(),
    )
    assert result == sessions[25:]


def test_two_session_offline_run_passes_oracle_and_replay_gates(monkeypatch, tmp_path) -> None:
    panels = _panels()
    by_session = {item.as_of_session: item for item in panels}
    monkeypatch.setattr(
        cli,
        "load_formal_market_regime_panels",
        lambda *, data_root, as_of_sessions: tuple(by_session[item] for item in as_of_sessions),
    )
    run = cli._calculate_offline(
        data_root=tmp_path,
        candidate_sessions=tuple(item.as_of_session for item in panels),
        regime_records=_regime_records(panels),
    )
    assert tuple(run.score_history) == (PRIMARY, SECONDARY)
    assert all(len(rows) == 2 for rows in run.score_history.values())
    assert len(run.current_risk_results) == 6
    assert run.oracle_report.mismatch_count == 0, run.oracle_report.mismatches[:5]
    assert run.oracle_report.shared_raw_fact_match
    assert run.oracle_report.input_permutation_match
    assert all(run.equivalence_flags.values())
    assert all(item.parameter_fingerprint == CANDIDATE_STATE_PARAMETER_FINGERPRINT for rows in run.state_history.values() for item in rows)
    assert run.runtime_metrics["panel_load_count"] == 2
    assert run.runtime_metrics["candidate_score_calculation_invocation_count"] == 4
    assert run.runtime_metrics["candidate_independent_oracle_invocation_count"] == 2
    assert Decimal(run.timings["candidate_score_calculation_wall_seconds"]) >= 0
    assert Decimal(run.timings["candidate_independent_oracle_cpu_seconds"]) >= 0


def test_formal_main_passes_all_panels_and_equivalence_flags_to_audit(
    monkeypatch, tmp_path, capsys,
) -> None:
    panels = _panels()
    by_session = {item.as_of_session: item for item in panels}
    monkeypatch.setattr(
        cli,
        "load_formal_market_regime_panels",
        lambda *, data_root, as_of_sessions: tuple(by_session[item] for item in as_of_sessions),
    )
    run = cli._calculate_offline(
        data_root=tmp_path,
        candidate_sessions=tuple(item.as_of_session for item in panels),
        regime_records=_regime_records(panels),
    )
    captured = {}

    def write_audit(**kwargs):
        captured.update(kwargs)
        return {
            "as_of_session": panels[-1].as_of_session.isoformat(),
            "universe_ids": [PRIMARY, SECONDARY],
            "oracle_mismatch_count": 0,
        }

    monkeypatch.setattr(
        cli,
        "_audit_api",
        lambda: (
            lambda path: pytest.fail("candidate audit reader must not run"),
            write_audit,
            lambda path: path,
        ),
    )
    monkeypatch.setattr(cli, "read_market_regime_state_audit", lambda path: {})
    monkeypatch.setattr(cli, "_read_phase1b_payloads", lambda path: ((), {}, {}))
    monkeypatch.setattr(cli, "_validate_phase1b", lambda **kwargs: None)
    monkeypatch.setattr(
        cli,
        "_select_candidate_sessions",
        lambda **kwargs: tuple(item.as_of_session for item in panels),
    )
    monkeypatch.setattr(
        cli,
        "_list_available_eod_sessions",
        lambda path: tuple(item.as_of_session for item in panels),
    )
    monkeypatch.setattr(cli, "_calculate_offline", lambda **kwargs: run)

    assert cli.main([
        "--as-of-session", panels[-1].as_of_session.isoformat(),
        "--data-root", str(tmp_path),
        "--phase1b-audit", str(tmp_path / "phase1b"),
        "--output-dir", str(tmp_path / "candidate-audit"),
    ]) == 0
    assert captured["panels"] == panels
    assert captured["equivalence_flags"] == run.equivalence_flags
    assert len(captured["candidate_batches"]) == 4
    assert captured["risk_results"] == run.current_risk_results
    assert captured["runtime_metrics"]["candidate_session_count"] == 2
    assert "candidate_offline_calculation_wall_seconds" in captured["timings"]
    assert "audit_projection_build_cpu_seconds" in captured["timings"]
    assert "panel" not in captured
    assert '"status":"completed"' in capsys.readouterr().out


def test_as_of_missing_member_uses_history_identity_and_emits_missing_state(monkeypatch, tmp_path) -> None:
    first, second = _panels()
    missing_id = next(iter(second.select_universe(PRIMARY).member_ids))
    second = replace(
        second,
        bars=tuple(
            item for item in second.bars
            if not (item.instrument_id == missing_id and item.session_date == second.as_of_session)
        ),
    )
    panels = (first, second)
    by_session = {item.as_of_session: item for item in panels}
    monkeypatch.setattr(
        cli,
        "load_formal_market_regime_panels",
        lambda *, data_root, as_of_sessions: tuple(by_session[item] for item in as_of_sessions),
    )
    run = cli._calculate_offline(
        data_root=tmp_path,
        candidate_sessions=tuple(item.as_of_session for item in panels),
        regime_records=_regime_records(panels),
    )
    primary_rows = [item for item in run.state_history[PRIMARY] if item.instrument_id == missing_id]
    assert len(primary_rows) == 2
    assert primary_rows[-1].state_availability.value == "unavailable"
    assert primary_rows[-1].consecutive_missing_sessions == 1
    assert run.oracle_report.mismatch_count == 0


def test_verified_prior_increment_matches_cold_business_outputs(monkeypatch, tmp_path) -> None:
    panels = _panels()
    regimes = _regime_records(panels)
    by_session = {item.as_of_session: item for item in panels}
    monkeypatch.setattr(
        cli,
        "load_formal_market_regime_panels",
        lambda *, data_root, as_of_sessions: tuple(by_session[item] for item in as_of_sessions),
    )
    prior_run = cli._calculate_offline(
        data_root=tmp_path,
        candidate_sessions=(panels[0].as_of_session,),
        regime_records=regimes,
    )
    cold_run = cli._calculate_offline(
        data_root=tmp_path,
        candidate_sessions=tuple(item.as_of_session for item in panels),
        regime_records=regimes,
    )
    prior_dir = Path(tempfile.mkdtemp(prefix="candidate-prior-", dir="/tmp"))
    incremental_dir = Path(tempfile.mkdtemp(prefix="candidate-incremental-", dir="/tmp"))
    tampered_dir = Path(tempfile.mkdtemp(prefix="candidate-incremental-tampered-", dir="/tmp"))
    try:
        write_opportunity_candidate_audit(
            output_dir=prior_dir,
            panels=(panels[0],),
            candidate_batches=tuple(
                batch for universe_id in (PRIMARY, SECONDARY) for batch in prior_run.score_history[universe_id]
            ),
            state_history=tuple(
                row for universe_id in (PRIMARY, SECONDARY) for row in prior_run.state_history[universe_id]
            ),
            risk_results=prior_run.current_risk_results,
            oracle_comparison=prior_run.oracle_report,
            equivalence_flags=prior_run.equivalence_flags,
            raw_facts=cli._raw_fact_records(prior_run.score_history),
            normalization_ledger=cli._normalization_records(prior_run.score_history),
            generated_at=datetime.now(UTC),
            timings={},
            peak_memory_kib=1,
        )
        prior = read_opportunity_candidate_audit_contents(prior_dir)
        incremental = cli._calculate_incremental(
            data_root=tmp_path,
            candidate_sessions=tuple(item.as_of_session for item in panels),
            regime_records=regimes,
            prior_audit=prior,
        )

        def batch_fingerprints(run):
            return tuple(
                batch.logical_fingerprint
                for session in tuple(item.as_of_session for item in panels)
                for universe_id in (PRIMARY, SECONDARY)
                for batch in run.score_history[universe_id]
                if batch.as_of_session == session
            )

        def state_fingerprints(run):
            return tuple(
                row.logical_fingerprint
                for session in tuple(item.as_of_session for item in panels)
                for universe_id in (PRIMARY, SECONDARY)
                for row in run.state_history[universe_id]
                if row.as_of_session == session
            )

        assert batch_fingerprints(incremental) == batch_fingerprints(cold_run)
        assert state_fingerprints(incremental) == state_fingerprints(cold_run)
        assert tuple(item.logical_fingerprint for item in incremental.current_risk_results) == tuple(
            item.logical_fingerprint for item in cold_run.current_risk_results
        )
        assert incremental.oracle_report.mismatch_count == 0
        assert all(incremental.equivalence_flags.values())

        manifest = write_opportunity_candidate_audit(
            output_dir=incremental_dir,
            panels=incremental.panels,
            prior_source_panels=prior.source_panels,
            candidate_batches=tuple(
                batch for universe_id in (PRIMARY, SECONDARY) for batch in incremental.score_history[universe_id]
            ),
            state_history=tuple(
                row for universe_id in (PRIMARY, SECONDARY) for row in incremental.state_history[universe_id]
            ),
            risk_results=incremental.current_risk_results,
            oracle_comparison=incremental.oracle_report,
            equivalence_flags=incremental.equivalence_flags,
            raw_facts=(*prior.raw_facts, *cli._raw_fact_records(incremental.current_score_history)),
            normalization_ledger=(
                *prior.normalization_ledger,
                *cli._normalization_records(incremental.current_score_history),
            ),
            incremental_validation=cli._incremental_validation_ledger(
                prior_audit=prior,
                run=incremental,
            ),
            generated_at=datetime.now(UTC),
            timings={},
            peak_memory_kib=1,
        )
        reread = read_opportunity_candidate_audit_contents(incremental_dir)
        assert manifest["schema_version"] == "1.1"
        assert manifest["execution_mode"] == "verified_prior_incremental"
        assert reread.validation_ledger["prior_audit_logical_fingerprint"] == prior.manifest[
            "logical_content_fingerprint"
        ]
        assert tuple(item.logical_fingerprint for item in reread.candidate_batches) == batch_fingerprints(cold_run)
        changed_raw = list(prior.raw_facts)
        changed_raw[0] = {**changed_raw[0], "ticker": "TAMPERED"}
        with pytest.raises(OpportunityCandidateAuditError, match="raw-fact prefix"):
            write_opportunity_candidate_audit(
                output_dir=tampered_dir,
                panels=incremental.panels,
                prior_source_panels=prior.source_panels,
                candidate_batches=tuple(
                    batch for universe_id in (PRIMARY, SECONDARY) for batch in incremental.score_history[universe_id]
                ),
                state_history=tuple(
                    row for universe_id in (PRIMARY, SECONDARY) for row in incremental.state_history[universe_id]
                ),
                risk_results=incremental.current_risk_results,
                oracle_comparison=incremental.oracle_report,
                equivalence_flags=incremental.equivalence_flags,
                raw_facts=(*changed_raw, *cli._raw_fact_records(incremental.current_score_history)),
                normalization_ledger=(
                    *prior.normalization_ledger,
                    *cli._normalization_records(incremental.current_score_history),
                ),
                incremental_validation=cli._incremental_validation_ledger(
                    prior_audit=prior,
                    run=incremental,
                ),
                generated_at=datetime.now(UTC),
                timings={},
                peak_memory_kib=1,
            )
    finally:
        shutil.rmtree(prior_dir, ignore_errors=True)
        shutil.rmtree(incremental_dir, ignore_errors=True)
        shutil.rmtree(tampered_dir, ignore_errors=True)
