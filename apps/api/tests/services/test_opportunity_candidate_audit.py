from __future__ import annotations

import json
import hashlib
import shutil
import stat
import tempfile
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid5

import pytest
import tip_api.services.opportunity_candidate_audit as candidate_audit

from tip_api.services.opportunity_candidate_audit import (
    CANDIDATE_ARTIFACT_FILES,
    CANDIDATE_AUDIT_MANIFEST,
    OpportunityCandidateAuditError,
    _canonical_bytes,
    _fingerprint,
    read_opportunity_candidate_audit,
    read_opportunity_candidate_current_batches,
    read_opportunity_candidate_publication_evidence,
    validate_tmp_output_dir,
    write_opportunity_candidate_audit,
)
from tip_api.contracts.analytics.v1 import (
    CandidateBreakoutAvailability,
    CandidateBreakoutFactV1,
    CandidatePriorStateSourceV1,
    CandidateRiskMode,
    CandidateStateObservationV1,
    RegimeState,
)
from tip_api.parameters.market_regime.candidate_v1_1_1 import CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT
from tip_api.services.market_regime_sources import (
    MarketRegimeBar,
    MarketRegimeInputPanel,
    MarketRegimeSourceSession,
    MarketRegimeUniverseSource,
)
from tip_api.services.opportunity_candidate_oracle import (
    CandidateStateOracleCase,
    compare_with_independent_candidate_oracle,
)
from tip_api.services.opportunity_candidate_state import replay_opportunity_candidate_state_history
from tip_api.services.opportunity_candidates import calculate_opportunity_candidate_scores, rank_opportunity_candidates


PRIMARY = "provider_classified_common_shares_v1"
SECONDARY = "provider_classified_common_shares_plus_adrs_v1"
NS = UUID("9a4e4470-ddad-5b95-96d6-2faab930dc20")


def _id(label: str) -> UUID:
    return uuid5(NS, label)


def _panel() -> MarketRegimeInputPanel:
    sessions = tuple(date(2026, 7, 1) + timedelta(days=index) for index in range(26))
    primary = tuple(_id(f"stock-{index}") for index in range(8))
    adrs = tuple(_id(f"adr-{index}") for index in range(2))
    etfs = {ticker: _id(f"etf-{ticker}") for ticker in ("SPY", "QQQ", "IWM", "DIA", "XLK", "SMH")}
    bars = []
    for day_index, session in enumerate(sessions):
        day = Decimal(day_index)
        for index, instrument_id in enumerate((*primary, *adrs)):
            close = Decimal(30 + index) + day * (Decimal("0.15") + Decimal(index) / Decimal(100))
            bars.append(
                MarketRegimeBar(
                    instrument_id=instrument_id,
                    ticker=(f"S{index:02d}" if index < len(primary) else f"A{index-len(primary):02d}"),
                    instrument_type="common_stock",
                    primary_exchange="XNYS",
                    session_date=session,
                    open=close,
                    high=close * Decimal("1.01"),
                    low=close * Decimal("0.99"),
                    close=close,
                    volume=Decimal(2_500_000 + index * 30_000 + day_index * 20_000),
                )
            )
        for index, (ticker, instrument_id) in enumerate(etfs.items()):
            close = Decimal(90 + index * 5) + day * (Decimal("0.18") + Decimal(index) / Decimal(50))
            bars.append(
                MarketRegimeBar(
                    instrument_id=instrument_id,
                    ticker=ticker,
                    instrument_type="etf",
                    primary_exchange="ARCX",
                    session_date=session,
                    open=close,
                    high=close * Decimal("1.01"),
                    low=close * Decimal("0.99"),
                    close=close,
                    volume=Decimal(9_000_000 + index * 100_000 + day_index * 25_000),
                )
            )
    source_sessions = tuple(
        MarketRegimeSourceSession(
            session_date=session,
            dataset_path=f"market-data/eod/session={session.isoformat()}",
            record_count=len(primary) + len(adrs) + len(etfs),
            content_fingerprint=f"{index + 1:064x}",
            parquet_sha256=f"{index + 101:064x}",
            identity_snapshot_date=session,
            identity_snapshot_fingerprint=f"{index + 201:064x}",
        )
        for index, session in enumerate(sessions)
    )
    return MarketRegimeInputPanel(
        as_of_session=sessions[-1],
        calendar_id="XNYS",
        calendar_version="candidate-audit-fixture",
        sessions=sessions,
        source_sessions=source_sessions,
        bars=tuple(bars),
        universes=(
            MarketRegimeUniverseSource(PRIMARY, "Primary", True, 0, frozenset(primary), "a" * 64),
            MarketRegimeUniverseSource(SECONDARY, "Secondary", False, 1, frozenset((*primary, *adrs)), "b" * 64),
        ),
        activation_pointer_fingerprint="c" * 64,
        identity_logical_fingerprint="d" * 64,
        eod_content_fingerprint="e" * 64,
        eod_business_key_fingerprint="f" * 64,
        history_source_fingerprint="1" * 64,
    )


def _bootstrap(panel: MarketRegimeInputPanel, universe_id: str) -> CandidatePriorStateSourceV1:
    return CandidatePriorStateSourceV1(
        universe_id=universe_id,
        as_of_session=panel.as_of_session,
        bootstrap=True,
        source_state_session=None,
        state_history_fingerprint=CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT,
        supports=(),
    )


def _actuals(panel: MarketRegimeInputPanel):
    contexts = {
        PRIMARY: (Decimal("62.5000"), RegimeState.BALANCED),
        SECONDARY: (Decimal("58.2500"), RegimeState.DEFENSIVE),
    }
    batches = tuple(
        calculate_opportunity_candidate_scores(
            panel=panel,
            universe_id=universe_id,
            regime_score=score,
            regime_state=state,
            regime_source_fingerprint=("2" if universe_id == PRIMARY else "3") * 64,
            prior_state_source=_bootstrap(panel, universe_id),
        )
        for universe_id, (score, state) in contexts.items()
    )
    risks = tuple(
        rank_opportunity_candidates(batch=batch, risk_mode=mode)
        for batch in batches
        for mode in CandidateRiskMode
    )
    return batches, risks, contexts


def _state_case(panel: MarketRegimeInputPanel, batch):
    candidate = batch.candidates[0]
    instrument_bars = {
        item.session_date: item for item in panel.bars if item.instrument_id == candidate.instrument_id
    }
    prior_sessions = panel.sessions[-6:-1]
    close = instrument_bars[panel.as_of_session].close
    prior_high = max(instrument_bars[item].close for item in prior_sessions)
    ratio = Decimal(candidate.current_volume_ratio)
    breakout = CandidateBreakoutFactV1(
        as_of_session=panel.as_of_session,
        instrument_id=candidate.instrument_id,
        availability=CandidateBreakoutAvailability.AVAILABLE,
        close=f"{close:.10f}",
        prior_five_session_close_high=f"{prior_high:.10f}",
        current_volume_ratio=candidate.current_volume_ratio,
        prior_five_sessions=prior_sessions,
        triggered=close > prior_high and ratio >= Decimal("1.20"),
        missing_reason=None,
        reason_codes=("typed_breakout_fact",),
    )
    observation = CandidateStateObservationV1(
        candidate=candidate,
        regime_state=RegimeState.BALANCED,
        breakout_fact=breakout,
    )
    records = replay_opportunity_candidate_state_history(
        observations=(observation,),
        expected_sessions=(panel.as_of_session,),
        universe_id=batch.universe_id,
        instrument_id=candidate.instrument_id,
        ticker=candidate.ticker,
        security_type=candidate.security_type,
    )
    return CandidateStateOracleCase(
        observations=(observation,),
        expected_sessions=(panel.as_of_session,),
        universe_id=batch.universe_id,
        instrument_id=candidate.instrument_id,
        ticker=candidate.ticker,
        security_type=candidate.security_type,
        actual_records=records,
    )


def _inputs():
    panel = _panel()
    batches, risks, contexts = _actuals(panel)
    state_case = _state_case(panel, batches[0])
    oracle = compare_with_independent_candidate_oracle(
        panel=panel,
        batches=batches,
        regime_context_by_universe=contexts,
        risk_results=risks,
        state_cases=(state_case,),
    )
    raw_facts = {
        "shared": [
            {
                "instrument_id": str(batches[0].candidates[0].instrument_id),
                "latest_price": batches[0].candidates[0].latest_price,
                "evidence_type": "fact",
            }
        ]
    }
    normalization = [
        {
            "universe_id": batch.universe_id,
            "as_of_session": batch.as_of_session,
            "method": "inclusive_linear_type7_decimal",
        }
        for batch in reversed(batches)
    ]
    return panel, batches, state_case.actual_records, risks, oracle, raw_facts, normalization


def _write(
    target: Path,
    *,
    generated_at: datetime = datetime(2026, 8, 26, tzinfo=UTC),
    work_dir: Path | None = None,
    defer_finalization: bool = False,
):
    panel, batches, states, risks, oracle, raw_facts, normalization = _inputs()
    return write_opportunity_candidate_audit(
        output_dir=target,
        panels=(panel,),
        candidate_batches=batches,
        state_history=states,
        risk_results=risks,
        oracle_comparison=oracle,
        equivalence_flags={
            "append_full_replay_match": True,
            "restart_replay_match": True,
            "future_prefix_stable": True,
            "input_permutation_match": True,
        },
        raw_facts=raw_facts,
        normalization_ledger=normalization,
        generated_at=generated_at,
        timings={"oracle": "0.100000", "total": "0.200000"},
        peak_memory_kib=512,
        runtime_metrics={"process_io_read_bytes_delta": 123},
        work_dir=work_dir,
        defer_finalization=defer_finalization,
    )


def test_canonical_tmp_audit_round_trip_and_manifest_bindings() -> None:
    target = Path(tempfile.mkdtemp(prefix="mrom-candidate-audit-", dir="/tmp"))
    try:
        manifest = _write(target)
        reread = read_opportunity_candidate_audit(target)
        assert reread["logical_content_fingerprint"] == manifest["logical_content_fingerprint"]
        assert reread["oracle_mismatch_count"] == 0
        assert reread["shared_raw_fact_match"] is True
        assert reread["input_permutation_match"] is True
        assert reread["external_request_count"] == 0
        assert reread["production_write_count"] == 0
        assert reread["universe_ids"] == [PRIMARY, SECONDARY]
        scores = json.loads((target / "candidate-score-history.json").read_bytes())["records"]
        assert [item["universe_id"] for item in scores] == [PRIMARY, SECONDARY]
        risks = json.loads((target / "current-risk-mode-results.json").read_bytes())["records"]
        assert [(item["universe_id"], item["risk_mode"]) for item in risks] == [
            (universe, mode)
            for universe in (PRIMARY, SECONDARY)
            for mode in ("conservative", "balanced", "aggressive")
        ]
        assert {item.name for item in target.iterdir()} == set(CANDIDATE_ARTIFACT_FILES) | {
            CANDIDATE_AUDIT_MANIFEST
        }
        assert stat.S_IMODE(target.stat().st_mode) == 0o700
        for item in target.iterdir():
            assert stat.S_IMODE(item.stat().st_mode) == 0o400
            raw = item.read_bytes()
            assert raw.endswith(b"\n")
            assert json.dumps(
                json.loads(raw), sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode() + b"\n" == raw
    finally:
        shutil.rmtree(target, ignore_errors=True)


def test_publication_evidence_rehashes_bytes_without_business_row_reparse() -> None:
    target = Path(tempfile.mkdtemp(prefix="mrom-candidate-publication-evidence-", dir="/tmp"))
    try:
        manifest = _write(target)
        evidence = read_opportunity_candidate_publication_evidence(target)
        assert evidence.manifest["logical_content_fingerprint"] == manifest[
            "logical_content_fingerprint"
        ]
        assert evidence.manifest_sha256 == hashlib.sha256(
            (target / CANDIDATE_AUDIT_MANIFEST).read_bytes()
        ).hexdigest()

        artifact = target / "raw-candidate-facts.json"
        artifact.chmod(0o600)
        artifact.write_bytes(artifact.read_bytes() + b" ")
        artifact.chmod(0o400)
        with pytest.raises(OpportunityCandidateAuditError, match="custody mismatch"):
            read_opportunity_candidate_publication_evidence(target)
    finally:
        shutil.rmtree(target, ignore_errors=True)


def test_current_batch_projection_rehashes_custody_without_historical_replay(
    monkeypatch,
) -> None:
    target = Path(tempfile.mkdtemp(prefix="mrom-candidate-current-projection-", dir="/tmp"))
    try:
        manifest = _write(target)

        def reject_full_replay(*args, **kwargs):
            raise AssertionError("current projection must not invoke the full audit reader")

        monkeypatch.setattr(
            candidate_audit,
            "_read_opportunity_candidate_audit",
            reject_full_replay,
        )
        evidence = read_opportunity_candidate_current_batches(
            target,
            as_of_session=_panel().as_of_session,
        )

        assert evidence.manifest_sha256 == hashlib.sha256(
            (target / CANDIDATE_AUDIT_MANIFEST).read_bytes()
        ).hexdigest()
        assert tuple(item.universe_id for item in evidence.candidate_batches) == (
            PRIMARY,
            SECONDARY,
        )
        assert [item.logical_fingerprint for item in evidence.candidate_batches] == (
            manifest["candidate_batch_fingerprints"][-2:]
        )
        assert evidence.source_panel["as_of_session"] == manifest["as_of_session"]
        with pytest.raises(OpportunityCandidateAuditError, match="as-of session"):
            read_opportunity_candidate_current_batches(
                target,
                as_of_session=_panel().as_of_session - timedelta(days=1),
            )
    finally:
        shutil.rmtree(target, ignore_errors=True)


def test_logical_manifest_is_independent_of_runtime_metadata_and_input_order() -> None:
    first = Path(tempfile.mkdtemp(prefix="mrom-candidate-first-", dir="/tmp"))
    second = Path(tempfile.mkdtemp(prefix="mrom-candidate-second-", dir="/tmp"))
    try:
        a = _write(first, generated_at=datetime(2026, 8, 26, tzinfo=UTC))
        panel, batches, states, risks, oracle, raw_facts, normalization = _inputs()
        b = write_opportunity_candidate_audit(
            output_dir=second,
            panels=(panel,),
            candidate_batches=tuple(reversed(batches)),
            state_history=tuple(reversed(states)),
            risk_results=tuple(reversed(risks)),
            oracle_comparison=oracle,
            equivalence_flags={
                "append_full_replay_match": True,
                "restart_replay_match": True,
                "future_prefix_stable": True,
                "input_permutation_match": True,
            },
            raw_facts=raw_facts,
            normalization_ledger=tuple(reversed(normalization)),
            generated_at=datetime(2026, 8, 27, tzinfo=UTC),
            timings={"total": "9.9"},
            peak_memory_kib=999,
            runtime_metrics={"process_io_read_bytes_delta": 999},
        )
        assert a["logical_content_fingerprint"] == b["logical_content_fingerprint"]
        assert a["generated_at"] != b["generated_at"]
        assert a["timings"] != b["timings"]
        assert a["runtime_metrics"] != b["runtime_metrics"]
    finally:
        shutil.rmtree(first, ignore_errors=True)
        shutil.rmtree(second, ignore_errors=True)


def test_streamed_canonical_encoder_matches_legacy_json_encoding() -> None:
    value = {
        "z": [1, True, None, {"accent": "e\u0301", "中文": "市场"}],
        "a": {"float": 0.00001, "escaped": "line\nbreak"},
    }
    expected = (
        json.dumps(
            candidate_audit._normalize_nfc(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    assert _canonical_bytes(value) == expected


def test_resumable_writer_reuses_verified_artifact_prefix(monkeypatch) -> None:
    output = Path(tempfile.mkdtemp(prefix="mrom-candidate-resume-output-", dir="/tmp"))
    work = Path(tempfile.mkdtemp(prefix="mrom-candidate-resume-work-", dir="/tmp"))
    baseline = Path(tempfile.mkdtemp(prefix="mrom-candidate-resume-baseline-", dir="/tmp"))
    shutil.rmtree(output)
    shutil.rmtree(work)
    original = candidate_audit._write_or_reuse_resumable_artifact
    calls = 0

    def interrupt_after_first(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated interruption")
        return original(*args, **kwargs)

    try:
        baseline_manifest = _write(baseline)
        monkeypatch.setattr(candidate_audit, "_write_or_reuse_resumable_artifact", interrupt_after_first)
        with pytest.raises(RuntimeError, match="simulated interruption"):
            _write(output, work_dir=work)
        assert not output.exists()
        journal = json.loads((work / candidate_audit.CANDIDATE_AUDIT_RESUME_FILE).read_bytes())
        assert len(journal["completed_artifacts"]) == 1
        assert journal["next_artifact"] == CANDIDATE_ARTIFACT_FILES[1]

        monkeypatch.setattr(candidate_audit, "_write_or_reuse_resumable_artifact", original)
        resumed = _write(output, work_dir=work)
        assert resumed["logical_content_fingerprint"] == baseline_manifest["logical_content_fingerprint"]
        assert resumed["runtime_metrics"]["audit_artifact_resume_reuse_count"] == 1
        assert not work.exists()
        for name in CANDIDATE_ARTIFACT_FILES:
            assert (output / name).read_bytes() == (baseline / name).read_bytes()
    finally:
        shutil.rmtree(output, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(baseline, ignore_errors=True)


def test_resumable_writer_fails_closed_on_corrupt_completed_artifact(monkeypatch) -> None:
    output = Path(tempfile.mkdtemp(prefix="mrom-candidate-corrupt-output-", dir="/tmp"))
    work = Path(tempfile.mkdtemp(prefix="mrom-candidate-corrupt-work-", dir="/tmp"))
    shutil.rmtree(output)
    shutil.rmtree(work)
    original = candidate_audit._write_or_reuse_resumable_artifact
    calls = 0

    def interrupt_after_first(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated interruption")
        return original(*args, **kwargs)

    try:
        monkeypatch.setattr(candidate_audit, "_write_or_reuse_resumable_artifact", interrupt_after_first)
        with pytest.raises(RuntimeError, match="simulated interruption"):
            _write(output, work_dir=work)
        artifact = work / CANDIDATE_ARTIFACT_FILES[0]
        artifact.chmod(0o600)
        artifact.write_text("{}\n", encoding="utf-8")
        artifact.chmod(0o400)

        monkeypatch.setattr(candidate_audit, "_write_or_reuse_resumable_artifact", original)
        with pytest.raises(OpportunityCandidateAuditError, match="fingerprint|descriptor"):
            _write(output, work_dir=work)
        assert not output.exists()
        assert work.is_dir()
    finally:
        shutil.rmtree(output, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


def test_completed_work_directory_finalizes_without_recalculation(monkeypatch) -> None:
    output = Path(tempfile.mkdtemp(prefix="mrom-candidate-finalize-output-", dir="/tmp"))
    work = Path(tempfile.mkdtemp(prefix="mrom-candidate-finalize-work-", dir="/tmp"))
    shutil.rmtree(output)
    shutil.rmtree(work)
    original_rename = candidate_audit.os.rename

    def interrupt_delivery(source, destination):
        if Path(source) == work and Path(destination) == output:
            raise RuntimeError("simulated final delivery interruption")
        return original_rename(source, destination)

    try:
        monkeypatch.setattr(candidate_audit.os, "rename", interrupt_delivery)
        with pytest.raises(RuntimeError, match="final delivery"):
            _write(output, work_dir=work)
        assert (work / CANDIDATE_AUDIT_MANIFEST).is_file()
        assert not (work / candidate_audit.CANDIDATE_AUDIT_RESUME_FILE).exists()

        monkeypatch.setattr(candidate_audit.os, "rename", original_rename)
        manifest = candidate_audit.finalize_resumable_candidate_audit(work, output)
        assert manifest is not None and manifest["completion_status"] == "completed"
        assert output.is_dir() and not work.exists()
    finally:
        shutil.rmtree(output, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


def test_prepared_manifest_and_complete_journal_finalize_after_interruption(monkeypatch) -> None:
    output = Path(tempfile.mkdtemp(prefix="mrom-candidate-pending-output-", dir="/tmp"))
    work = Path(tempfile.mkdtemp(prefix="mrom-candidate-pending-work-", dir="/tmp"))
    shutil.rmtree(output)
    shutil.rmtree(work)
    original_unlink = Path.unlink

    def interrupt_journal_removal(path, *args, **kwargs):
        if path == work / candidate_audit.CANDIDATE_AUDIT_RESUME_FILE:
            raise RuntimeError("simulated journal removal interruption")
        return original_unlink(path, *args, **kwargs)

    try:
        monkeypatch.setattr(Path, "unlink", interrupt_journal_removal)
        with pytest.raises(RuntimeError, match="journal removal"):
            _write(output, work_dir=work)
        assert (work / candidate_audit.CANDIDATE_AUDIT_RESUME_FILE).is_file()
        assert (work / candidate_audit.CANDIDATE_AUDIT_PENDING_MANIFEST).is_file()

        monkeypatch.setattr(Path, "unlink", original_unlink)
        manifest = candidate_audit.finalize_resumable_candidate_audit(work, output)
        assert manifest is not None and manifest["oracle_mismatch_count"] == 0
        assert output.is_dir() and not work.exists()
    finally:
        shutil.rmtree(output, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


def test_deferred_finalization_preserves_work_until_separate_formal_reread() -> None:
    output = Path(tempfile.mkdtemp(prefix="mrom-candidate-deferred-output-", dir="/tmp"))
    work = Path(tempfile.mkdtemp(prefix="mrom-candidate-deferred-work-", dir="/tmp"))
    shutil.rmtree(output)
    shutil.rmtree(work)
    try:
        prepared = _write(output, work_dir=work, defer_finalization=True)
        assert not output.exists()
        assert (work / candidate_audit.CANDIDATE_AUDIT_RESUME_FILE).is_file()
        assert (work / candidate_audit.CANDIDATE_AUDIT_PENDING_MANIFEST).is_file()
        completed = candidate_audit.finalize_resumable_candidate_audit(work, output)
        assert completed is not None
        assert completed["logical_content_fingerprint"] == prepared["logical_content_fingerprint"]
        assert output.is_dir() and not work.exists()
    finally:
        shutil.rmtree(output, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


@pytest.mark.parametrize("gate", ["mismatch", "shared", "permutation"])
def test_writer_rejects_failed_oracle_gate(gate: str) -> None:
    target = Path(tempfile.mkdtemp(prefix="mrom-candidate-reject-", dir="/tmp"))
    panel, batches, states, risks, oracle, raw_facts, normalization = _inputs()
    if gate == "mismatch":
        oracle = replace(oracle, mismatch_count=1, mismatches=("fixture",))
    elif gate == "shared":
        oracle = replace(oracle, shared_raw_fact_match=False)
    else:
        oracle = replace(oracle, input_permutation_match=False)
    try:
        with pytest.raises(OpportunityCandidateAuditError, match="Oracle equivalence"):
            write_opportunity_candidate_audit(
                output_dir=target,
                panels=(panel,),
                candidate_batches=batches,
                state_history=states,
                risk_results=risks,
                oracle_comparison=oracle,
                equivalence_flags={
                    "append_full_replay_match": True,
                    "restart_replay_match": True,
                    "future_prefix_stable": True,
                },
                raw_facts=raw_facts,
                normalization_ledger=normalization,
                generated_at=datetime.now(UTC),
                timings={},
                peak_memory_kib=1,
            )
        assert not any(target.iterdir())
    finally:
        shutil.rmtree(target, ignore_errors=True)


def test_reread_rejects_extra_symlink_and_artifact_tampering(tmp_path: Path) -> None:
    target = Path(tempfile.mkdtemp(prefix="mrom-candidate-tamper-", dir="/tmp"))
    link = Path(str(target) + "-link")
    try:
        _write(target)
        link.symlink_to(target, target_is_directory=True)
        with pytest.raises(OpportunityCandidateAuditError, match="symlink"):
            read_opportunity_candidate_audit(link)

        extra = target / "extra.json"
        extra.write_text("{}\n", encoding="utf-8")
        extra.chmod(0o400)
        with pytest.raises(OpportunityCandidateAuditError, match="extras"):
            read_opportunity_candidate_audit(target)
        extra.chmod(0o600)
        extra.unlink()

        artifact = target / CANDIDATE_ARTIFACT_FILES[0]
        artifact.chmod(0o600)
        artifact.write_bytes(artifact.read_bytes() + b" ")
        artifact.chmod(0o400)
        with pytest.raises(OpportunityCandidateAuditError, match="custody mismatch"):
            read_opportunity_candidate_audit(target)
    finally:
        link.unlink(missing_ok=True)
        shutil.rmtree(target, ignore_errors=True)


def test_output_boundary_rejects_non_tmp_nested_nonempty_and_symlink(tmp_path: Path) -> None:
    for unsafe in (Path("relative"), Path("/data/candidate-audit"), tmp_path / "nested"):
        with pytest.raises(OpportunityCandidateAuditError, match="direct child"):
            validate_tmp_output_dir(unsafe)

    nonempty = Path(tempfile.mkdtemp(prefix="mrom-candidate-nonempty-", dir="/tmp"))
    link = Path(str(nonempty) + "-link")
    try:
        (nonempty / "sentinel").write_text("preserve", encoding="utf-8")
        with pytest.raises(OpportunityCandidateAuditError, match="non-empty"):
            validate_tmp_output_dir(nonempty)
        link.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(OpportunityCandidateAuditError, match="symlink"):
            validate_tmp_output_dir(link)
    finally:
        link.unlink(missing_ok=True)
        shutil.rmtree(nonempty, ignore_errors=True)


def _shift_panel(panel: MarketRegimeInputPanel, days: int) -> MarketRegimeInputPanel:
    delta = timedelta(days=days)
    return replace(
        panel,
        as_of_session=panel.as_of_session + delta,
        sessions=tuple(item + delta for item in panel.sessions),
        source_sessions=tuple(
            replace(
                item,
                session_date=item.session_date + delta,
                dataset_path=f"market-data/eod/session={(item.session_date + delta).isoformat()}",
                identity_snapshot_date=item.identity_snapshot_date + delta,
            )
            for item in panel.source_sessions
        ),
        bars=tuple(replace(item, session_date=item.session_date + delta) for item in panel.bars),
        history_source_fingerprint="9" * 64,
    )


def test_each_candidate_session_requires_its_own_complete_source_panel() -> None:
    current, current_batches, states, risks, oracle, raw_facts, normalization = _inputs()
    previous = _shift_panel(current, -1)
    previous_batches, _, _ = _actuals(previous)
    target = Path(tempfile.mkdtemp(prefix="mrom-candidate-panels-", dir="/tmp"))
    missing = Path(tempfile.mkdtemp(prefix="mrom-candidate-missing-panel-", dir="/tmp"))
    flags = {
        "append_full_replay_match": True,
        "restart_replay_match": True,
        "future_prefix_stable": True,
    }
    try:
        manifest = write_opportunity_candidate_audit(
            output_dir=target,
            panels=(previous, current),
            candidate_batches=(*current_batches, *previous_batches),
            state_history=states,
            risk_results=risks,
            oracle_comparison=oracle,
            equivalence_flags=flags,
            raw_facts=raw_facts,
            normalization_ledger=normalization,
            generated_at=datetime.now(UTC),
            timings={},
            peak_memory_kib=1,
        )
        assert manifest["universe_ids"] == [PRIMARY, SECONDARY]
        source = json.loads((target / "source-input-manifest.json").read_bytes())
        assert [item["as_of_session"] for item in source["panels"]] == [
            previous.as_of_session.isoformat(),
            current.as_of_session.isoformat(),
        ]
        assert source["panels"][0]["source_sessions"][0]["session_date"] not in {
            item["session_date"] for item in source["panels"][1]["source_sessions"]
        }
        with pytest.raises(OpportunityCandidateAuditError, match="source panel"):
            write_opportunity_candidate_audit(
                output_dir=missing,
                panels=(current,),
                candidate_batches=(*previous_batches, *current_batches),
                state_history=states,
                risk_results=risks,
                oracle_comparison=oracle,
                equivalence_flags=flags,
                raw_facts=raw_facts,
                normalization_ledger=normalization,
                generated_at=datetime.now(UTC),
                timings={},
                peak_memory_kib=1,
            )
    finally:
        shutil.rmtree(target, ignore_errors=True)
        shutil.rmtree(missing, ignore_errors=True)


def test_reread_recomputes_nested_typed_record_fingerprint_after_outer_resign() -> None:
    target = Path(tempfile.mkdtemp(prefix="mrom-candidate-resign-", dir="/tmp"))
    try:
        _write(target)
        score_path = target / "candidate-score-history.json"
        score_payload = json.loads(score_path.read_bytes())
        score_payload.pop("logical_content_fingerprint")
        score_payload["records"][0]["candidates"][0]["logical_fingerprint"] = "0" * 64
        history_fingerprint = _fingerprint(score_payload["records"])
        score_payload["candidate_history_fingerprint"] = history_fingerprint
        score_payload["logical_content_fingerprint"] = _fingerprint(score_payload)
        score_raw = _canonical_bytes(score_payload)
        score_path.chmod(0o600)
        score_path.write_bytes(score_raw)
        score_path.chmod(0o400)

        manifest_path = target / CANDIDATE_AUDIT_MANIFEST
        manifest = json.loads(manifest_path.read_bytes())
        manifest["candidate_history_fingerprint"] = history_fingerprint
        artifact = next(item for item in manifest["artifacts"] if item["name"] == score_path.name)
        artifact.update(
            bytes=len(score_raw),
            sha256=hashlib.sha256(score_raw).hexdigest(),
            logical_content_fingerprint=score_payload["logical_content_fingerprint"],
        )
        runtime_keys = {
            "logical_content_fingerprint",
            "generated_at",
            "timings",
            "peak_memory_kib",
            "runtime_metrics",
            "completion_status",
        }
        manifest["logical_content_fingerprint"] = _fingerprint(
            {key: value for key, value in manifest.items() if key not in runtime_keys}
        )
        manifest_path.chmod(0o600)
        manifest_path.write_bytes(_canonical_bytes(manifest))
        manifest_path.chmod(0o400)
        with pytest.raises(OpportunityCandidateAuditError, match="candidate score logical fingerprint"):
            read_opportunity_candidate_audit(target)
    finally:
        shutil.rmtree(target, ignore_errors=True)


@pytest.mark.parametrize("mutation", ["false", "missing"])
def test_reread_rejects_false_or_missing_replay_equivalence_gate(mutation: str) -> None:
    target = Path(tempfile.mkdtemp(prefix="mrom-candidate-equivalence-", dir="/tmp"))
    try:
        _write(target)
        manifest_path = target / CANDIDATE_AUDIT_MANIFEST
        manifest = json.loads(manifest_path.read_bytes())
        if mutation == "false":
            manifest["equivalence_flags"]["restart_replay_match"] = False
        else:
            del manifest["equivalence_flags"]["restart_replay_match"]
        runtime_keys = {
            "logical_content_fingerprint",
            "generated_at",
            "timings",
            "peak_memory_kib",
            "runtime_metrics",
            "completion_status",
        }
        manifest["logical_content_fingerprint"] = _fingerprint(
            {key: value for key, value in manifest.items() if key not in runtime_keys}
        )
        manifest_path.chmod(0o600)
        manifest_path.write_bytes(_canonical_bytes(manifest))
        manifest_path.chmod(0o400)
        with pytest.raises(OpportunityCandidateAuditError, match="replay equivalence"):
            read_opportunity_candidate_audit(target)
    finally:
        shutil.rmtree(target, ignore_errors=True)
