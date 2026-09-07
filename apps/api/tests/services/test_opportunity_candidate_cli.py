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
from tip_api.services import opportunity_candidate_segmented_append as candidate_append
from tip_api.services import opportunity_candidate_segmented_session_candidate as session_candidate
from tip_api.services.opportunity_candidate_audit import (
    CANDIDATE_PERIODIC_BUSINESS_PROJECTIONS,
    OpportunityCandidateAuditError,
    read_opportunity_candidate_business_fingerprints,
    read_opportunity_candidate_audit_contents,
    read_opportunity_candidate_incremental_source,
    write_opportunity_candidate_audit,
)
from tip_api.services.opportunity_candidate_segmented_append import (
    COMPOSED_APPEND_CONTRACT,
    CandidateSegmentedAppendError,
    read_candidate_segmented_append,
    read_candidate_segmented_parent,
    write_candidate_segmented_append,
    write_candidate_segmented_append_from_session_candidate,
)
from tip_api.services.opportunity_candidate_segmented_session_candidate import (
    CandidateSegmentedSessionCandidateError,
    read_candidate_segmented_session_candidate,
    write_candidate_segmented_session_candidate,
)
from tip_api.services.opportunity_candidate_segmented_shadow import (
    write_candidate_segmented_shadow,
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


def _panels(ends=(25, 26)):
    sessions = tuple(
        date(2026, 7, 1) + timedelta(days=index)
        for index in range(max(ends) + 1)
    )
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
    for end in ends:
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


def test_segmented_session_cli_options_are_paired(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_audit_api", lambda: pytest.fail("audit API must not load"))
    with pytest.raises(SystemExit):
        cli.main([
            "--as-of-session", "2026-08-24",
            "--data-root", str(tmp_path),
            "--phase1b-audit", str(tmp_path / "phase1b"),
            "--prior-candidate-audit", str(tmp_path / "prior"),
            "--output-dir", str(tmp_path / "candidate-audit"),
            "--segmented-parent-shadow", str(tmp_path / "shadow"),
        ])


def _tier_manifest(*, incremental: bool, suffix: str = "a"):
    return {
        "schema_version": "1.1" if incremental else "1.0",
        **({"execution_mode": "verified_prior_incremental"} if incremental else {}),
        "as_of_session": "2026-08-26",
        "logical_content_fingerprint": suffix * 64,
        "oracle_mismatch_count": 0,
        "artifacts": [
            {"name": name, "logical_content_fingerprint": f"{index:064x}"}
            for index, name in enumerate(CANDIDATE_PERIODIC_BUSINESS_PROJECTIONS, start=1)
        ],
    }


def _tier_business(manifest):
    return {
        item["name"]: item["logical_content_fingerprint"]
        for item in manifest["artifacts"]
    }


def test_validation_tiers_require_their_exact_audit_modes() -> None:
    incremental = _tier_manifest(incremental=True)
    cold = _tier_manifest(incremental=False, suffix="b")
    assert cli._validate_completed_tier("daily", incremental, None)["validation_scope"].startswith(
        "verified_prior"
    )
    assert cli._validate_completed_tier("code_change", cold, None) == {
        "validation_scope": "cold_full_replay"
    }
    periodic = cli._validate_completed_tier(
        "periodic",
        incremental,
        cold,
        business_fingerprints=_tier_business(incremental),
        reference_business_fingerprints=_tier_business(cold),
    )
    assert periodic["business_artifact_match"] is True
    assert periodic["business_artifact_count"] == len(CANDIDATE_PERIODIC_BUSINESS_PROJECTIONS)
    with pytest.raises(RuntimeError, match="daily validation requires"):
        cli._validate_completed_tier("daily", cold, None)
    with pytest.raises(RuntimeError, match="code-change validation requires"):
        cli._validate_completed_tier("code_change", incremental, None)


def test_periodic_validation_fails_closed_on_business_difference() -> None:
    incremental = _tier_manifest(incremental=True)
    cold = _tier_manifest(incremental=False, suffix="b")
    cold["artifacts"][4]["logical_content_fingerprint"] = "f" * 64
    with pytest.raises(RuntimeError, match="candidate-score-history.json"):
        cli._validate_completed_tier(
            "periodic",
            incremental,
            cold,
            business_fingerprints=_tier_business(incremental),
            reference_business_fingerprints=_tier_business(cold),
        )


def test_periodic_verify_formally_reads_both_audits(monkeypatch, tmp_path, capsys) -> None:
    output = tmp_path / "candidate-incremental"
    reference = tmp_path / "candidate-cold"
    manifests = {output: _tier_manifest(incremental=True), reference: _tier_manifest(incremental=False)}
    calls = []
    monkeypatch.setattr(
        cli,
        "_audit_api",
        lambda: (
            lambda path: pytest.fail("ordinary reader must not replace the business projection reader"),
            lambda **kwargs: pytest.fail("writer must not run"),
            lambda path: pytest.fail("output validator must not run"),
        ),
    )
    monkeypatch.setattr(
        cli,
        "_read_candidate_business_fingerprints",
        lambda path: calls.append(path) or (manifests[path], _tier_business(manifests[path])),
    )
    assert cli.main([
        "--as-of-session", "2026-08-26",
        "--data-root", str(tmp_path),
        "--phase1b-audit", str(tmp_path / "phase1b"),
        "--output-dir", str(output),
        "--verify-output",
        "--validation-tier", "periodic",
        "--reference-audit", str(reference),
    ]) == 0
    assert calls == [output, reference]
    rendered = capsys.readouterr().out
    assert '"validation_tier":"periodic"' in rendered
    assert '"business_artifact_match":true' in rendered


def test_daily_tier_requires_prior_audit_before_loading_services(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_audit_api", lambda: pytest.fail("audit API must not load"))
    with pytest.raises(SystemExit):
        cli.main([
            "--as-of-session", "2026-08-26",
            "--data-root", str(tmp_path),
            "--phase1b-audit", str(tmp_path / "phase1b"),
            "--output-dir", str(tmp_path / "candidate"),
            "--validation-tier", "daily",
        ])


@pytest.mark.parametrize("value", ["0", "9", "not-a-number"])
def test_cli_rejects_unsafe_worker_counts_before_loading_services(monkeypatch, tmp_path, value) -> None:
    monkeypatch.setattr(cli, "_audit_api", lambda: pytest.fail("audit API must not load"))
    with pytest.raises(SystemExit):
        cli.main([
            "--as-of-session", "2026-08-26",
            "--data-root", str(tmp_path),
            "--phase1b-audit", str(tmp_path / "phase1b"),
            "--output-dir", str(tmp_path / "candidate"),
            "--max-workers", value,
        ])


def test_completed_resumable_work_finalizes_before_source_reads(monkeypatch, tmp_path, capsys) -> None:
    output = tmp_path / "candidate-audit"
    work = tmp_path / "candidate-work"
    calls = []
    monkeypatch.setattr(
        cli,
        "_audit_api",
        lambda: (
            lambda path: pytest.fail("completed output reader must not run"),
            lambda **kwargs: pytest.fail("candidate writer must not run"),
            lambda path: calls.append(("validate", path)) or path,
        ),
    )
    monkeypatch.setattr(
        cli,
        "_finalize_resumable_audit",
        lambda work_dir, output_dir, *, validation_tier: calls.append(
            ("finalize", work_dir, output_dir, validation_tier)
        )
        or {"schema_version": "1.0", "as_of_session": "2026-08-24", "oracle_mismatch_count": 0},
    )
    monkeypatch.setattr(cli, "read_market_regime_state_audit", lambda path: pytest.fail("Phase1b must not be read"))
    assert cli.main([
        "--as-of-session", "2026-08-24",
        "--data-root", str(tmp_path),
        "--phase1b-audit", str(tmp_path / "phase1b"),
        "--output-dir", str(output),
        "--audit-work-dir", str(work),
    ]) == 0
    assert calls == [
        ("validate", output),
        ("finalize", work, output, "code_change"),
    ]
    assert '"status":"completed"' in capsys.readouterr().out


def test_completed_resumable_daily_run_requires_its_direct_session_candidate(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    output = tmp_path / "candidate-audit"
    work = tmp_path / "candidate-work"
    parent = tmp_path / "candidate-parent"
    session = tmp_path / "candidate-session"
    logical_fingerprint = "a" * 64
    completed = {
        "schema_version": "1.1",
        "execution_mode": "verified_prior_incremental",
        "as_of_session": "2026-08-24",
        "logical_content_fingerprint": logical_fingerprint,
        "oracle_mismatch_count": 0,
    }
    calls = []
    monkeypatch.setattr(
        cli,
        "_audit_api",
        lambda: (
            lambda path: pytest.fail("completed output reader must not run"),
            lambda **kwargs: pytest.fail("candidate writer must not run"),
            lambda path: calls.append(("validate", path)) or path,
        ),
    )
    monkeypatch.setattr(
        cli,
        "_finalize_resumable_audit",
        lambda work_dir, output_dir, *, validation_tier: completed,
    )
    monkeypatch.setattr(
        cli,
        "_read_segmented_session_candidate",
        lambda **kwargs: calls.append(("read_segmented", kwargs))
        or SimpleNamespace(
            manifest={
                "as_of_session": "2026-08-24",
                "logical_content_fingerprint": "b" * 64,
                "intended_source_audit": {
                    "logical_content_fingerprint": logical_fingerprint,
                },
            }
        ),
    )
    monkeypatch.setattr(
        cli,
        "read_market_regime_state_audit",
        lambda path: pytest.fail("Phase1b must not be read"),
    )

    assert cli.main([
        "--as-of-session", "2026-08-24",
        "--data-root", str(tmp_path),
        "--phase1b-audit", str(tmp_path / "phase1b"),
        "--prior-candidate-audit", str(tmp_path / "prior"),
        "--output-dir", str(output),
        "--audit-work-dir", str(work),
        "--validation-tier", "daily",
        "--segmented-parent-shadow", str(parent),
        "--segmented-session-output", str(session),
    ]) == 0
    assert calls == [
        ("validate", output),
        (
            "read_segmented",
            {"parent_shadow": parent, "output_dir": session},
        ),
    ]
    rendered = capsys.readouterr().out
    assert '"segmented_session_candidate"' in rendered
    assert '"logical_content_fingerprint":"' + "b" * 64 + '"' in rendered


@pytest.mark.parametrize(
    ("validation_tier", "expected_scope"),
    [
        ("daily", "validated_write_plus_physical_custody"),
        ("periodic", "full_semantic_reread"),
        ("code_change", "full_semantic_reread"),
    ],
)
def test_candidate_finalization_scope_is_validation_tier_bound(
    monkeypatch,
    tmp_path,
    validation_tier,
    expected_scope,
) -> None:
    import tip_api.services.opportunity_candidate_audit as audit

    calls = []
    monkeypatch.setattr(
        audit,
        "finalize_resumable_candidate_audit",
        lambda work_dir, output_dir, *, validation_scope: calls.append(
            (work_dir, output_dir, validation_scope)
        )
        or {"completion_status": "completed"},
    )
    work = tmp_path / "work"
    output = tmp_path / "output"
    assert cli._finalize_resumable_audit(
        work,
        output,
        validation_tier=validation_tier,
    ) == {"completion_status": "completed"}
    assert calls == [(work, output, expected_scope)]


def test_socket_guard_blocks_network_allows_local_process_ipc_and_restores(tmp_path) -> None:
    original = socket.socket
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    local_path = tmp_path / "candidate-worker.sock"
    listener.bind(str(local_path))
    listener.listen(1)
    with cli._offline_socket_guard():
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.create_connection(("127.0.0.1", 9))
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.getaddrinfo("example.invalid", 443)
        guarded = socket.socket()
        with pytest.raises(RuntimeError, match="network is prohibited"):
            guarded.connect(("127.0.0.1", 9))
        guarded.close()
        local = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        local.connect(str(local_path))
        local.close()
    listener.close()
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
    assert run.runtime_metrics["candidate_independent_oracle_invocation_count"] == 1
    assert run.runtime_metrics["candidate_oracle_session_job_count"] == 2
    assert run.runtime_metrics["candidate_oracle_effective_max_workers"] == 1
    assert Decimal(run.timings["candidate_score_calculation_wall_seconds"]) >= 0
    assert Decimal(run.timings["candidate_independent_oracle_cpu_seconds"]) >= 0

    parallel = cli._calculate_offline(
        data_root=tmp_path,
        candidate_sessions=tuple(item.as_of_session for item in panels),
        regime_records=_regime_records(panels),
        max_workers=2,
    )
    assert parallel.oracle_report == run.oracle_report
    assert parallel.equivalence_flags == run.equivalence_flags
    assert parallel.score_history == run.score_history
    assert parallel.state_history == run.state_history
    assert parallel.current_risk_results == run.current_risk_results
    assert parallel.runtime_metrics["candidate_oracle_session_job_count"] == 2
    assert parallel.runtime_metrics["candidate_oracle_effective_max_workers"] == 2


def test_incremental_panel_uses_exact_stage_cache_without_data_read(monkeypatch) -> None:
    panel = _panels()[-1]
    root = Path(tempfile.mkdtemp(prefix="candidate-panel-cache-hit-", dir="/tmp"))
    root.chmod(0o700)
    try:
        manifest = cli.write_market_regime_panel_cache(cache_root=root, panel=panel)
        monkeypatch.setattr(
            cli,
            "load_formal_market_regime_panels",
            lambda **kwargs: pytest.fail("canonical data must not be reread on an exact cache hit"),
        )
        reread, status, fingerprint = cli._load_incremental_panel(
            data_root=Path("/data/unused"),
            current_session=panel.as_of_session,
            panel_cache_root=root,
            expected_panel_source=cli.panel_source_boundary(panel),
        )
        assert reread == replace(
            panel,
            bars=tuple(sorted(panel.bars, key=lambda item: (item.session_date, str(item.instrument_id)))),
        )
        assert status == "hit"
        assert fingerprint == manifest["logical_content_fingerprint"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_incremental_panel_cache_miss_runs_formal_reader_and_populates(monkeypatch, tmp_path) -> None:
    panel = _panels()[-1]
    root = Path(tempfile.mkdtemp(prefix="candidate-panel-cache-miss-", dir="/tmp"))
    shutil.rmtree(root)
    calls = []
    monkeypatch.setattr(
        cli,
        "load_formal_market_regime_panels",
        lambda **kwargs: calls.append(kwargs) or (panel,),
    )
    try:
        loaded, status, fingerprint = cli._load_incremental_panel(
            data_root=tmp_path,
            current_session=panel.as_of_session,
            panel_cache_root=root,
            expected_panel_source=cli.panel_source_boundary(panel),
        )
        assert loaded == panel
        assert status == "populated"
        assert isinstance(fingerprint, str) and len(fingerprint) == 64
        assert calls == [{"data_root": tmp_path, "as_of_sessions": (panel.as_of_session,)}]
        reread, _, _ = cli._load_incremental_panel(
            data_root=tmp_path,
            current_session=panel.as_of_session,
            panel_cache_root=root,
            expected_panel_source=cli.panel_source_boundary(panel),
        )
        assert reread == replace(
            panel,
            bars=tuple(sorted(panel.bars, key=lambda item: (item.session_date, str(item.instrument_id)))),
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_incremental_panel_rejects_malformed_current_phase1b_source(tmp_path) -> None:
    source = cli.panel_source_boundary(_panels()[-1])
    source["source_custody_mode"] = "verified_prior_state_plus_current_phase1a_audit"
    source["history_source_fingerprint"] = "malformed"
    with pytest.raises(RuntimeError, match="source custody is malformed"):
        cli._load_incremental_panel(
            data_root=tmp_path,
            current_session=_panels()[-1].as_of_session,
            panel_cache_root=None,
            expected_panel_source=source,
        )


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
    calculation_kwargs = {}

    def write_audit(**kwargs):
        captured.update(kwargs)
        return {
            "schema_version": "1.0",
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
    monkeypatch.setattr(
        cli,
        "_calculate_offline",
        lambda **kwargs: calculation_kwargs.update(kwargs) or run,
    )

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
    assert captured["runtime_metrics"]["candidate_oracle_requested_max_workers"] == 4
    assert calculation_kwargs["max_workers"] == 4
    assert "candidate_offline_calculation_wall_seconds" in captured["timings"]
    assert "audit_projection_build_cpu_seconds" in captured["timings"]
    assert "panel" not in captured
    assert '"status":"completed"' in capsys.readouterr().out


def test_daily_main_emits_direct_segment_from_current_objects(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    panels = _panels()
    by_session = {item.as_of_session: item for item in panels}
    monkeypatch.setattr(
        cli,
        "load_formal_market_regime_panels",
        lambda *, data_root, as_of_sessions: tuple(
            by_session[item] for item in as_of_sessions
        ),
    )
    full = cli._calculate_offline(
        data_root=tmp_path,
        candidate_sessions=tuple(item.as_of_session for item in panels),
        regime_records=_regime_records(panels),
    )
    current_score_history = {
        universe_id: (full.score_history[universe_id][-1],)
        for universe_id in (PRIMARY, SECONDARY)
    }
    run = cli.CandidateIncrementalRun(
        panels=full.panels,
        score_history=full.score_history,
        state_history=full.state_history,
        current_risk_results=full.current_risk_results,
        oracle_report=full.oracle_report,
        equivalence_flags={
            **full.equivalence_flags,
            "prior_prefix_preserved": True,
            "future_prefix_stable": True,
        },
        candidate_sessions=full.candidate_sessions,
        timings=full.timings,
        runtime_metrics=full.runtime_metrics,
        current_score_history=current_score_history,
    )
    prior = SimpleNamespace(
        source_panels=({"as_of_session": panels[0].as_of_session.isoformat()},),
        manifest={
            "as_of_session": panels[0].as_of_session.isoformat(),
            "logical_content_fingerprint": "1" * 64,
            "oracle_fingerprint": "2" * 64,
            "candidate_history_fingerprint": "3" * 64,
            "candidate_state_history_fingerprint": "4" * 64,
        },
        validation_ledger=None,
        raw_facts=(),
        normalization_ledger=(),
    )
    source_logical = "5" * 64
    captured_audit = {}
    captured_segment = {}

    def write_audit(**kwargs):
        captured_audit.update(kwargs)
        return {
            "schema_version": "1.1",
            "execution_mode": "verified_prior_incremental",
            "as_of_session": panels[-1].as_of_session.isoformat(),
            "universe_ids": [PRIMARY, SECONDARY],
            "logical_content_fingerprint": source_logical,
            "oracle_mismatch_count": 0,
        }

    monkeypatch.setattr(
        cli,
        "_audit_api",
        lambda: (
            lambda path: pytest.fail("completed audit reader must not run"),
            write_audit,
            lambda path: path,
        ),
    )
    monkeypatch.setattr(cli, "read_market_regime_state_audit", lambda path: {})
    monkeypatch.setattr(cli, "_read_phase1b_payloads", lambda path: ((), {}, {}))
    monkeypatch.setattr(cli, "_validate_phase1b", lambda **kwargs: None)
    monkeypatch.setattr(cli, "_read_prior_candidate_audit", lambda path: prior)
    monkeypatch.setattr(cli, "_calculate_incremental", lambda **kwargs: run)
    monkeypatch.setattr(
        cli,
        "ExchangeCalendar",
        lambda: SimpleNamespace(previous_session=lambda value: panels[0].as_of_session),
    )

    def write_segment(**kwargs):
        captured_segment.update(kwargs)
        return {
            "as_of_session": panels[-1].as_of_session.isoformat(),
            "logical_content_fingerprint": "6" * 64,
        }

    monkeypatch.setattr(cli, "_write_segmented_session_candidate", write_segment)
    parent = tmp_path / "parent-shadow"
    session = tmp_path / "session-candidate"
    assert cli.main([
        "--as-of-session", panels[-1].as_of_session.isoformat(),
        "--data-root", str(tmp_path),
        "--phase1b-audit", str(tmp_path / "phase1b"),
        "--prior-candidate-audit", str(tmp_path / "prior"),
        "--validation-tier", "daily",
        "--output-dir", str(tmp_path / "candidate-audit"),
        "--segmented-parent-shadow", str(parent),
        "--segmented-session-output", str(session),
    ]) == 0
    assert captured_segment["parent_shadow"] == parent
    assert captured_segment["source_audit_manifest"][
        "logical_content_fingerprint"
    ] == source_logical
    assert captured_segment["incremental_validation"] == captured_audit[
        "incremental_validation"
    ]
    assert captured_segment["panel"] == panels[-1]
    assert captured_segment["candidate_batches"] == tuple(
        current_score_history[universe_id][0]
        for universe_id in (PRIMARY, SECONDARY)
    )
    assert all(
        row.as_of_session == panels[-1].as_of_session
        for row in captured_segment["state_records"]
    )
    assert captured_segment["output_dir"] == session
    assert '"segmented_session_candidate"' in capsys.readouterr().out


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
    cold_dir = Path(tempfile.mkdtemp(prefix="candidate-cold-", dir="/tmp"))
    tampered_dir = Path(tempfile.mkdtemp(prefix="candidate-incremental-tampered-", dir="/tmp"))
    parent_shadow = Path(tempfile.mkdtemp(prefix="candidate-parent-shadow-", dir="/tmp"))
    append_dir = Path(tempfile.mkdtemp(prefix="candidate-segment-append-", dir="/tmp"))
    session_dir = Path(tempfile.mkdtemp(prefix="candidate-session-direct-", dir="/tmp"))
    composed_dir = Path(tempfile.mkdtemp(prefix="candidate-segment-composed-", dir="/tmp"))
    for path in (parent_shadow, append_dir, session_dir, composed_dir):
        shutil.rmtree(path)
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
        incremental_source = read_opportunity_candidate_incremental_source(prior_dir)
        assert incremental_source.manifest == prior.manifest
        assert incremental_source.source_panels == prior.source_panels
        assert incremental_source.candidate_batches == prior.candidate_batches
        assert incremental_source.state_history == prior.state_history
        assert incremental_source.risk_results == prior.risk_results
        assert incremental_source.raw_facts == prior.raw_facts
        assert incremental_source.normalization_ledger == prior.normalization_ledger
        assert incremental_source.validation_ledger == prior.validation_ledger
        incremental = cli._calculate_incremental(
            data_root=tmp_path,
            candidate_sessions=tuple(item.as_of_session for item in panels),
            regime_records=regimes,
            prior_audit=prior,
            max_workers=4,
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
        assert incremental.runtime_metrics["candidate_oracle_effective_max_workers"] == 1

        incremental_validation = cli._incremental_validation_ledger(
            prior_audit=prior,
            run=incremental,
        )
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
            incremental_validation=incremental_validation,
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
        write_candidate_segmented_shadow(
            source_audit=prior_dir,
            output_dir=parent_shadow,
        )
        append_manifest = write_candidate_segmented_append(
            parent_shadow=parent_shadow,
            source_audit=incremental_dir,
            output_dir=append_dir,
        )
        direct_kwargs = {
            "parent_shadow": parent_shadow,
            "source_audit_manifest": manifest,
            "incremental_validation": incremental_validation,
            "panel": incremental.panels[-1],
            "candidate_batches": tuple(
                batch
                for universe_id in (PRIMARY, SECONDARY)
                for batch in incremental.current_score_history[universe_id]
            ),
            "state_records": tuple(
                row
                for universe_id in (PRIMARY, SECONDARY)
                for row in incremental.state_history[universe_id]
                if row.as_of_session == panels[-1].as_of_session
            ),
            "risk_results": incremental.current_risk_results,
            "oracle_comparison": incremental.oracle_report,
            "raw_facts": cli._raw_fact_records(incremental.current_score_history),
            "normalization_records": cli._normalization_records(
                incremental.current_score_history
            ),
        }
        direct_manifest = write_candidate_segmented_session_candidate(
            **direct_kwargs,
            output_dir=session_dir,
        )
        direct = read_candidate_segmented_session_candidate(
            parent_shadow=parent_shadow,
            output_dir=session_dir,
        )
        appended = read_candidate_segmented_append(
            parent_shadow=parent_shadow,
            output_dir=append_dir,
        )
        assert direct.manifest == direct_manifest
        assert direct_manifest["current_projection_fingerprints"] == append_manifest[
            "current_projection_fingerprints"
        ]
        for field in direct_manifest["current_projection_fingerprints"]:
            assert direct.payload[field] == appended.segment[field]
        assert direct.payload["raw_fact_session_ordinals"] == list(
            range(len(direct.payload["raw_facts"]))
        )
        assert "raw_fact_source_ordinals" not in direct.payload
        assert direct_manifest["publication_authorized"] is False
        assert direct_manifest["production_write_count"] == 0
        assert write_candidate_segmented_session_candidate(
            **direct_kwargs,
            output_dir=session_dir,
        ) == direct_manifest
        with monkeypatch.context() as isolated:
            def reject_cumulative_history(*args, **kwargs):
                raise AssertionError("cumulative Candidate history was parsed")

            isolated.setattr(
                candidate_append.v1,
                "_read_opportunity_candidate_audit",
                reject_cumulative_history,
            )
            composed_manifest = (
                write_candidate_segmented_append_from_session_candidate(
                    parent_shadow=parent_shadow,
                    source_audit=incremental_dir,
                    session_candidate=session_dir,
                    output_dir=composed_dir,
                )
            )
        composed = read_candidate_segmented_append(
            parent_shadow=parent_shadow,
            output_dir=composed_dir,
        )
        assert composed.manifest == composed_manifest
        assert composed_manifest["contract_version"] == COMPOSED_APPEND_CONTRACT
        assert composed_manifest["parent"] == append_manifest["parent"]
        assert composed_manifest["source_audit"]["manifest_sha256"] == (
            append_manifest["source_audit"]["manifest_sha256"]
        )
        assert composed_manifest["source_audit"][
            "logical_content_fingerprint"
        ] == append_manifest["source_audit"]["logical_content_fingerprint"]
        assert composed_manifest["source_audit"][
            "physical_completion_verified"
        ] is True
        assert composed_manifest["prefix_binding"] == "exact_parent_versioned_chain"
        assert composed_manifest["current_projection_fingerprints"] == (
            append_manifest["current_projection_fingerprints"]
        )
        assert composed_manifest["segment"] == {
            **direct_manifest["payload"],
            "relative_path": candidate_append.APPEND_SEGMENT,
        }
        for field in composed_manifest["current_projection_fingerprints"]:
            assert composed.segment[field] == appended.segment[field]
        assert composed.segment["raw_fact_session_ordinals"] == list(
            range(len(composed.segment["raw_facts"]))
        )
        assert "raw_fact_source_ordinals" not in composed.segment
        assert composed_manifest["chain_node"]["prior_chain_fingerprint"] == (
            append_manifest["chain_node"]["prior_chain_fingerprint"]
        )
        assert composed_manifest["chain_node"]["chain_fingerprint"] != (
            append_manifest["chain_node"]["chain_fingerprint"]
        )
        assert write_candidate_segmented_append_from_session_candidate(
            parent_shadow=parent_shadow,
            source_audit=incremental_dir,
            session_candidate=session_dir,
            output_dir=composed_dir,
        ) == composed_manifest

        composed_recovery = composed_dir.with_name(f"{composed_dir.name}-recovery")
        real_composed_rename = candidate_append.os.rename

        def interrupt_composed_delivery(source, destination):
            if Path(destination) == composed_recovery:
                raise OSError("simulated composed-append delivery interruption")
            return real_composed_rename(source, destination)

        monkeypatch.setattr(
            candidate_append.os,
            "rename",
            interrupt_composed_delivery,
        )
        with pytest.raises(OSError, match="simulated composed-append"):
            write_candidate_segmented_append_from_session_candidate(
                parent_shadow=parent_shadow,
                source_audit=incremental_dir,
                session_candidate=session_dir,
                output_dir=composed_recovery,
            )
        composed_stage = composed_recovery.with_name(
            f".{composed_recovery.name}.staging"
        )
        assert composed_stage.is_dir()
        monkeypatch.setattr(candidate_append.os, "rename", real_composed_rename)
        assert write_candidate_segmented_append_from_session_candidate(
            parent_shadow=parent_shadow,
            source_audit=incremental_dir,
            session_candidate=session_dir,
            output_dir=composed_recovery,
        ) == composed_manifest
        assert composed_recovery.is_dir()
        assert not composed_stage.exists()

        wrong_source = composed_dir.with_name(f"{composed_dir.name}-wrong-source")
        with pytest.raises(
            CandidateSegmentedAppendError,
            match="parent, direct candidate, and completed V1 differ",
        ):
            write_candidate_segmented_append_from_session_candidate(
                parent_shadow=parent_shadow,
                source_audit=prior_dir,
                session_candidate=session_dir,
                output_dir=wrong_source,
            )
        assert not wrong_source.exists()

        recovery_dir = session_dir.with_name(f"{session_dir.name}-recovery")
        real_rename = session_candidate.os.rename

        def interrupt_delivery(source, destination):
            if Path(destination) == recovery_dir:
                raise OSError("simulated direct-session delivery interruption")
            return real_rename(source, destination)

        monkeypatch.setattr(session_candidate.os, "rename", interrupt_delivery)
        with pytest.raises(OSError, match="simulated direct-session"):
            write_candidate_segmented_session_candidate(
                **direct_kwargs,
                output_dir=recovery_dir,
            )
        recovery_stage = recovery_dir.with_name(f".{recovery_dir.name}.staging")
        assert recovery_stage.is_dir()
        monkeypatch.setattr(session_candidate.os, "rename", real_rename)
        assert write_candidate_segmented_session_candidate(
            **direct_kwargs,
            output_dir=recovery_dir,
        ) == direct_manifest
        assert recovery_dir.is_dir()
        assert not recovery_stage.exists()

        changed_validation = {
            **incremental_validation,
            "prior_audit_logical_fingerprint": "0" * 64,
        }
        rejected_dir = session_dir.with_name(f"{session_dir.name}-rejected")
        with pytest.raises(
            CandidateSegmentedSessionCandidateError,
            match="exact parent audit",
        ):
            write_candidate_segmented_session_candidate(
                **{
                    **direct_kwargs,
                    "incremental_validation": changed_validation,
                },
                output_dir=rejected_dir,
            )
        assert not rejected_dir.exists()

        wrong_universe_dir = session_dir.with_name(
            f"{session_dir.name}-wrong-universe"
        )
        with pytest.raises(
            CandidateSegmentedSessionCandidateError,
            match="source audit identity",
        ):
            write_candidate_segmented_session_candidate(
                **{
                    **direct_kwargs,
                    "source_audit_manifest": {
                        **manifest,
                        "universe_ids": [SECONDARY, PRIMARY],
                    },
                },
                output_dir=wrong_universe_dir,
            )
        assert not wrong_universe_dir.exists()
        write_opportunity_candidate_audit(
            output_dir=cold_dir,
            panels=cold_run.panels,
            candidate_batches=tuple(
                batch
                for universe_id in (PRIMARY, SECONDARY)
                for batch in cold_run.score_history[universe_id]
            ),
            state_history=tuple(
                row
                for universe_id in (PRIMARY, SECONDARY)
                for row in cold_run.state_history[universe_id]
            ),
            risk_results=cold_run.current_risk_results,
            oracle_comparison=cold_run.oracle_report,
            equivalence_flags=cold_run.equivalence_flags,
            raw_facts=cli._raw_fact_records(cold_run.score_history),
            normalization_ledger=cli._normalization_records(cold_run.score_history),
            generated_at=datetime.now(UTC),
            timings={},
            peak_memory_kib=1,
        )
        _, incremental_business = read_opportunity_candidate_business_fingerprints(
            incremental_dir
        )
        _, cold_business = read_opportunity_candidate_business_fingerprints(cold_dir)
        assert incremental_business == cold_business
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
        shutil.rmtree(cold_dir, ignore_errors=True)
        shutil.rmtree(tampered_dir, ignore_errors=True)
        shutil.rmtree(parent_shadow, ignore_errors=True)
        shutil.rmtree(append_dir, ignore_errors=True)
        shutil.rmtree(session_dir, ignore_errors=True)
        shutil.rmtree(composed_dir, ignore_errors=True)
        shutil.rmtree(
            composed_dir.with_name(f"{composed_dir.name}-recovery"),
            ignore_errors=True,
        )
        shutil.rmtree(
            composed_dir.with_name(f".{composed_dir.name}-recovery.staging"),
            ignore_errors=True,
        )
        shutil.rmtree(
            composed_dir.with_name(f"{composed_dir.name}-wrong-source"),
            ignore_errors=True,
        )
        shutil.rmtree(
            session_dir.with_name(f"{session_dir.name}-recovery"),
            ignore_errors=True,
        )
        shutil.rmtree(
            session_dir.with_name(f".{session_dir.name}-recovery.staging"),
            ignore_errors=True,
        )
        shutil.rmtree(
            session_dir.with_name(f"{session_dir.name}-rejected"),
            ignore_errors=True,
        )
        shutil.rmtree(
            session_dir.with_name(f"{session_dir.name}-wrong-universe"),
            ignore_errors=True,
        )


def test_segmented_candidate_chain_accepts_two_ordered_appends(
    monkeypatch,
    tmp_path,
) -> None:
    panels = _panels((25, 26, 27))
    regimes = _regime_records(panels)
    by_session = {item.as_of_session: item for item in panels}
    monkeypatch.setattr(
        cli,
        "load_formal_market_regime_panels",
        lambda *, data_root, as_of_sessions: tuple(
            by_session[item] for item in as_of_sessions
        ),
    )
    directories = {
        name: Path(tempfile.mkdtemp(prefix=f"candidate-chain-{name}-", dir="/tmp"))
        for name in (
            "base-v1",
            "first-v1",
            "second-v1",
            "base-shadow",
            "first-direct",
            "first-append",
            "second-direct",
            "second-append",
        )
    }
    for name in (
        "base-shadow",
        "first-direct",
        "first-append",
        "second-direct",
        "second-append",
    ):
        shutil.rmtree(directories[name])

    def all_batches(run):
        return tuple(
            batch
            for universe_id in (PRIMARY, SECONDARY)
            for batch in run.score_history[universe_id]
        )

    def all_states(run):
        return tuple(
            row
            for universe_id in (PRIMARY, SECONDARY)
            for row in run.state_history[universe_id]
        )

    def current_direct_kwargs(*, run, manifest, validation, panel):
        return {
            "source_audit_manifest": manifest,
            "incremental_validation": validation,
            "panel": panel,
            "candidate_batches": tuple(
                batch
                for universe_id in (PRIMARY, SECONDARY)
                for batch in run.current_score_history[universe_id]
            ),
            "state_records": tuple(
                row
                for row in all_states(run)
                if row.as_of_session == panel.as_of_session
            ),
            "risk_results": run.current_risk_results,
            "oracle_comparison": run.oracle_report,
            "raw_facts": cli._raw_fact_records(run.current_score_history),
            "normalization_records": cli._normalization_records(
                run.current_score_history
            ),
        }

    def append_incremental(*, prior, selected_panels, output_dir):
        run = cli._calculate_incremental(
            data_root=tmp_path,
            candidate_sessions=tuple(
                item.as_of_session for item in selected_panels
            ),
            regime_records=regimes,
            prior_audit=prior,
            max_workers=2,
        )
        validation = cli._incremental_validation_ledger(
            prior_audit=prior,
            run=run,
        )
        manifest = write_opportunity_candidate_audit(
            output_dir=output_dir,
            panels=run.panels,
            prior_source_panels=prior.source_panels,
            candidate_batches=all_batches(run),
            state_history=all_states(run),
            risk_results=run.current_risk_results,
            oracle_comparison=run.oracle_report,
            equivalence_flags=run.equivalence_flags,
            raw_facts=(
                *prior.raw_facts,
                *cli._raw_fact_records(run.current_score_history),
            ),
            normalization_ledger=(
                *prior.normalization_ledger,
                *cli._normalization_records(run.current_score_history),
            ),
            incremental_validation=validation,
            generated_at=datetime.now(UTC),
            timings={},
            peak_memory_kib=1,
        )
        return run, validation, manifest

    try:
        base_run = cli._calculate_offline(
            data_root=tmp_path,
            candidate_sessions=(panels[0].as_of_session,),
            regime_records=regimes,
        )
        write_opportunity_candidate_audit(
            output_dir=directories["base-v1"],
            panels=base_run.panels,
            candidate_batches=all_batches(base_run),
            state_history=all_states(base_run),
            risk_results=base_run.current_risk_results,
            oracle_comparison=base_run.oracle_report,
            equivalence_flags=base_run.equivalence_flags,
            raw_facts=cli._raw_fact_records(base_run.score_history),
            normalization_ledger=cli._normalization_records(
                base_run.score_history
            ),
            generated_at=datetime.now(UTC),
            timings={},
            peak_memory_kib=1,
        )
        base = read_opportunity_candidate_audit_contents(directories["base-v1"])
        first_run, first_validation, first_v1_manifest = append_incremental(
            prior=base,
            selected_panels=panels[:2],
            output_dir=directories["first-v1"],
        )
        first = read_opportunity_candidate_audit_contents(
            directories["first-v1"]
        )
        second_run, second_validation, second_v1_manifest = append_incremental(
            prior=first,
            selected_panels=panels,
            output_dir=directories["second-v1"],
        )

        base_shadow_manifest = write_candidate_segmented_shadow(
            source_audit=directories["base-v1"],
            output_dir=directories["base-shadow"],
        )
        first_direct_manifest = write_candidate_segmented_session_candidate(
            parent_shadow=directories["base-shadow"],
            **current_direct_kwargs(
                run=first_run,
                manifest=first_v1_manifest,
                validation=first_validation,
                panel=panels[1],
            ),
            output_dir=directories["first-direct"],
        )
        first_append_manifest = (
            write_candidate_segmented_append_from_session_candidate(
                parent_shadow=directories["base-shadow"],
                source_audit=directories["first-v1"],
                session_candidate=directories["first-direct"],
                output_dir=directories["first-append"],
            )
        )
        first_append = read_candidate_segmented_append(
            parent_shadow=directories["base-shadow"],
            output_dir=directories["first-append"],
        )

        second_direct_manifest = write_candidate_segmented_session_candidate(
            parent_shadow=directories["base-shadow"],
            parent_appends=(directories["first-append"],),
            **current_direct_kwargs(
                run=second_run,
                manifest=second_v1_manifest,
                validation=second_validation,
                panel=panels[2],
            ),
            output_dir=directories["second-direct"],
        )
        second_append_manifest = (
            write_candidate_segmented_append_from_session_candidate(
                parent_shadow=directories["base-shadow"],
                parent_appends=(directories["first-append"],),
                source_audit=directories["second-v1"],
                session_candidate=directories["second-direct"],
                output_dir=directories["second-append"],
            )
        )
        second_append = read_candidate_segmented_append(
            parent_shadow=directories["base-shadow"],
            parent_appends=(directories["first-append"],),
            output_dir=directories["second-append"],
        )
        second_direct = read_candidate_segmented_session_candidate(
            parent_shadow=directories["base-shadow"],
            parent_appends=(directories["first-append"],),
            output_dir=directories["second-direct"],
        )
        complete_parent = read_candidate_segmented_parent(
            base_shadow=directories["base-shadow"],
            parent_appends=(
                directories["first-append"],
                directories["second-append"],
            ),
        )

        assert first_append.manifest == first_append_manifest
        assert second_append.manifest == second_append_manifest
        assert second_direct_manifest["parent"]["manifest_sha256"] == (
            first_append.manifest_sha256
        )
        assert second_append_manifest["parent"]["manifest_sha256"] == (
            first_append.manifest_sha256
        )
        assert second_append_manifest["chain_node"][
            "prior_chain_fingerprint"
        ] == first_append_manifest["chain_node"]["chain_fingerprint"]
        assert second_append_manifest["session_ordinal"] == (
            first_append_manifest["session_ordinal"] + 1
        )
        assert second_append_manifest["current_projection_fingerprints"] == (
            second_direct_manifest["current_projection_fingerprints"]
        )
        for field in second_direct_manifest["current_projection_fingerprints"]:
            assert second_append.segment[field] == second_direct.payload[field]
        assert complete_parent.append_count == 2
        assert complete_parent.session_count == 3
        assert complete_parent.as_of_session == panels[2].as_of_session.isoformat()
        assert complete_parent.manifest == second_append_manifest
        assert complete_parent.manifest_sha256 == second_append.manifest_sha256
        assert complete_parent.final_chain_fingerprint == (
            second_append_manifest["chain_node"]["chain_fingerprint"]
        )
        assert complete_parent.source_audit_logical_fingerprint == (
            second_v1_manifest["logical_content_fingerprint"]
        )
        assert complete_parent.production_write_count == 0
        assert complete_parent.publication_authorized is False
        assert write_candidate_segmented_session_candidate(
            parent_shadow=directories["base-shadow"],
            parent_appends=(directories["first-append"],),
            **current_direct_kwargs(
                run=second_run,
                manifest=second_v1_manifest,
                validation=second_validation,
                panel=panels[2],
            ),
            output_dir=directories["second-direct"],
        ) == second_direct_manifest
        assert write_candidate_segmented_append_from_session_candidate(
            parent_shadow=directories["base-shadow"],
            parent_appends=(directories["first-append"],),
            source_audit=directories["second-v1"],
            session_candidate=directories["second-direct"],
            output_dir=directories["second-append"],
        ) == second_append_manifest
        assert read_candidate_segmented_parent(
            base_shadow=directories["base-shadow"],
        ).manifest["logical_content_fingerprint"] == base_shadow_manifest[
            "logical_content_fingerprint"
        ]

        with pytest.raises(CandidateSegmentedAppendError, match="parent chain"):
            read_candidate_segmented_append(
                parent_shadow=directories["base-shadow"],
                output_dir=directories["second-append"],
            )
        with pytest.raises(CandidateSegmentedAppendError, match="parent chain"):
            read_candidate_segmented_parent(
                base_shadow=directories["base-shadow"],
                parent_appends=(
                    directories["second-append"],
                    directories["first-append"],
                ),
            )
    finally:
        for path in directories.values():
            shutil.rmtree(path, ignore_errors=True)
