"""Offline, socket-guarded Phase 5C candidate calculation CLI."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import resource
import socket
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import UUID

from tip_api.contracts.analytics.v1 import (
    CandidateBreakoutAvailability,
    CandidateBreakoutFactV1,
    CandidateRiskMode,
    CandidateStateObservationV1,
    MarketRegimeStateRecordV1,
    OpportunityCandidateBatchV1,
    OpportunityCandidateStateRecordV1,
)
from tip_api.contracts.market_data.v2.dashboard_universe_activation import PUBLIC_UNIVERSE_ORDER
from tip_api.parameters.market_regime.candidate_v1_1_1 import (
    CANDIDATE_PANEL_SESSION_COUNT,
    CANDIDATE_STATE_PARAMETER_FINGERPRINT,
)
from tip_api.parameters.market_regime.state_v1_0_1 import (
    STATE_CALCULATION_VERSION,
    STATE_PARAMETER_FINGERPRINT,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.market_regime_sources import (
    MarketRegimeInputPanel,
    load_formal_market_regime_panels,
)
from tip_api.services.market_regime_panel_cache import (
    MarketRegimePanelCacheError,
    MarketRegimePanelCacheMiss,
    normalize_source_boundary,
    panel_source_boundary,
    read_market_regime_panel_cache,
    write_market_regime_panel_cache,
)
from tip_api.services.market_regime_state_audit import read_market_regime_state_audit
from tip_api.services.opportunity_candidate_oracle import (
    CandidateIncrementalStateOracleCase,
    CandidateOracleComparisonV1,
    CandidateStateOracleCase,
    compare_with_independent_candidate_oracle,
)
from tip_api.services.opportunity_candidate_state import (
    append_opportunity_candidate_state_history,
    candidate_prior_state_source_from_history,
    opportunity_candidate_state_history_fingerprint,
    replay_opportunity_candidate_state_history,
)
from tip_api.services.opportunity_candidates import (
    calculate_opportunity_candidate_scores,
    rank_opportunity_candidates,
)


@dataclass(frozen=True, slots=True)
class CandidateOfflineRun:
    panels: tuple[MarketRegimeInputPanel, ...]
    score_history: Mapping[str, tuple[OpportunityCandidateBatchV1, ...]]
    state_history: Mapping[str, tuple[OpportunityCandidateStateRecordV1, ...]]
    current_risk_results: tuple[Any, ...]
    oracle_report: CandidateOracleComparisonV1
    equivalence_flags: Mapping[str, bool]
    candidate_sessions: tuple[date, ...]
    timings: Mapping[str, str]
    runtime_metrics: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class CandidateIncrementalRun:
    panels: tuple[MarketRegimeInputPanel, ...]
    score_history: Mapping[str, tuple[OpportunityCandidateBatchV1, ...]]
    state_history: Mapping[str, tuple[OpportunityCandidateStateRecordV1, ...]]
    current_risk_results: tuple[Any, ...]
    oracle_report: CandidateOracleComparisonV1
    equivalence_flags: Mapping[str, bool]
    candidate_sessions: tuple[date, ...]
    timings: Mapping[str, str]
    runtime_metrics: Mapping[str, int]
    current_score_history: Mapping[str, tuple[OpportunityCandidateBatchV1, ...]]
    panel_cache_status: str = "disabled"
    panel_cache_logical_fingerprint: str | None = None


@dataclass(slots=True)
class _StageProfiler:
    """Collect physical runtime evidence without entering logical fingerprints."""

    _wall_seconds: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    _cpu_seconds: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    _invocations: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @contextmanager
    def stage(self, name: str):
        wall_started = time.perf_counter()
        cpu_started = time.process_time()
        try:
            yield
        finally:
            self._wall_seconds[name] += time.perf_counter() - wall_started
            self._cpu_seconds[name] += time.process_time() - cpu_started
            self._invocations[name] += 1

    def timings(self) -> dict[str, str]:
        return {
            key: value
            for name in sorted(self._wall_seconds)
            for key, value in (
                (f"{name}_wall_seconds", _seconds(self._wall_seconds[name])),
                (f"{name}_cpu_seconds", _seconds(self._cpu_seconds[name])),
            )
        }

    def invocation_metrics(self) -> dict[str, int]:
        return {
            f"{name}_invocation_count": self._invocations[name]
            for name in sorted(self._invocations)
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Calculate Phase 5C opportunity candidates offline into a canonical /tmp audit."
    )
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--phase1b-audit", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--panel-cache-root",
        type=Path,
        help="Optional owner-controlled Dell-local content-addressed panel cache.",
    )
    parser.add_argument(
        "--audit-work-dir",
        type=Path,
        help="Optional owner-controlled /tmp work directory for resumable streamed audit artifacts.",
    )
    parser.add_argument(
        "--prior-candidate-audit",
        type=Path,
        help="Formally verified immediately prior Candidate audit for one-session incremental execution.",
    )
    parser.add_argument("--verify-output", action="store_true", help="Reread an existing completed audit only.")
    args = parser.parse_args(argv)
    for name in (
        "data_root",
        "phase1b_audit",
        "output_dir",
        "prior_candidate_audit",
        "panel_cache_root",
        "audit_work_dir",
    ):
        value = getattr(args, name)
        if value is not None and not value.is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")

    read_audit, write_audit, validate_output = _audit_api()
    if args.verify_output:
        manifest = read_audit(args.output_dir)
        print(json.dumps(_summary(manifest, args.output_dir), sort_keys=True, separators=(",", ":")))
        return 0

    validate_output(args.output_dir)
    if args.audit_work_dir is not None:
        completed = _finalize_resumable_audit(args.audit_work_dir, args.output_dir)
        if completed is not None:
            print(json.dumps(_summary(completed, args.output_dir), sort_keys=True, separators=(",", ":")))
            return 0
    profiler = _StageProfiler()
    io_before = _process_io_counters()
    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    started = time.monotonic()
    with _offline_socket_guard():
        with profiler.stage("phase1b_source_read_validate"):
            phase1b = read_market_regime_state_audit(args.phase1b_audit)
            state_records, source_payload, current_payload = _read_phase1b_payloads(args.phase1b_audit)
            _validate_phase1b(
                manifest=phase1b,
                state_records=state_records,
                source_payload=source_payload,
                current_payload=current_payload,
                as_of_session=args.as_of_session,
            )
        prior_audit = None
        if args.prior_candidate_audit is not None:
            with profiler.stage("prior_candidate_audit_read_validate"):
                prior_audit = _read_prior_candidate_audit(args.prior_candidate_audit)
            with profiler.stage("candidate_session_selection"):
                prior_sessions = tuple(
                    date.fromisoformat(item["as_of_session"])
                    for item in prior_audit.source_panels
                )
                if not prior_sessions or ExchangeCalendar().previous_session(args.as_of_session) != prior_sessions[-1]:
                    raise RuntimeError("prior Candidate audit is not the immediately preceding XNYS session")
                candidate_sessions = (*prior_sessions, args.as_of_session)
            with profiler.stage("candidate_incremental_calculation"):
                run = _calculate_incremental(
                    data_root=args.data_root,
                    candidate_sessions=candidate_sessions,
                    regime_records=state_records,
                    prior_audit=prior_audit,
                    panel_cache_root=args.panel_cache_root,
                    expected_panel_source=source_payload,
                )
        else:
            with profiler.stage("candidate_session_selection"):
                available_eod_sessions = tuple(
                    _list_available_eod_sessions(args.data_root)
                )
                candidate_sessions = _select_candidate_sessions(
                    state_records=state_records,
                    available_eod_sessions=available_eod_sessions,
                    as_of_session=args.as_of_session,
                    calendar=ExchangeCalendar(),
                )
            with profiler.stage("candidate_offline_calculation"):
                run = _calculate_offline(
                    data_root=args.data_root,
                    candidate_sessions=candidate_sessions,
                    regime_records=state_records,
                )
        if (
            run.oracle_report.mismatch_count
            or not run.oracle_report.shared_raw_fact_match
            or not run.oracle_report.input_permutation_match
            or not all(run.equivalence_flags.values())
        ):
            raise RuntimeError("candidate Oracle or replay-equivalence gate failed")
        elapsed = _seconds(time.monotonic() - started)
        with profiler.stage("audit_projection_build"):
            if prior_audit is None:
                raw_facts = _raw_fact_records(run.score_history)
                normalization_ledger = _normalization_records(run.score_history)
            else:
                raw_facts = (*prior_audit.raw_facts, *_raw_fact_records(run.current_score_history))
                normalization_ledger = (
                    *prior_audit.normalization_ledger,
                    *_normalization_records(run.current_score_history),
                )
        usage_after = resource.getrusage(resource.RUSAGE_SELF)
        io_after = _process_io_counters()
        timings = {
            **profiler.timings(),
            **run.timings,
            "total_before_audit_write_seconds": elapsed,
        }
        runtime_metrics = {
            **profiler.invocation_metrics(),
            **run.runtime_metrics,
            **_resource_deltas(usage_before, usage_after),
            **_io_deltas(io_before, io_after),
            "candidate_session_count": len(candidate_sessions),
        }
        incremental_kwargs = {}
        if prior_audit is not None:
            incremental_kwargs = {
                "prior_source_panels": prior_audit.source_panels,
                "incremental_validation": _incremental_validation_ledger(
                    prior_audit=prior_audit,
                    run=run,
                ),
            }
        manifest = write_audit(
            output_dir=args.output_dir,
            panels=run.panels,
            candidate_batches=tuple(
                batch
                for universe_id in PUBLIC_UNIVERSE_ORDER
                for batch in run.score_history[universe_id]
            ),
            state_history=tuple(
                row
                for universe_id in PUBLIC_UNIVERSE_ORDER
                for row in run.state_history[universe_id]
            ),
            risk_results=run.current_risk_results,
            oracle_comparison=run.oracle_report,
            equivalence_flags=run.equivalence_flags,
            raw_facts=raw_facts,
            normalization_ledger=normalization_ledger,
            generated_at=datetime.now(UTC),
            timings=timings,
            peak_memory_kib=usage_after.ru_maxrss,
            runtime_metrics=runtime_metrics,
            **(
                {"work_dir": args.audit_work_dir, "defer_finalization": True}
                if args.audit_work_dir is not None
                else {}
            ),
            **incremental_kwargs,
        )
        if args.audit_work_dir is not None:
            prepared_fingerprint = manifest["logical_content_fingerprint"]
            del run, prior_audit, raw_facts, normalization_ledger, incremental_kwargs
            gc.collect()
            completed = _finalize_resumable_audit(args.audit_work_dir, args.output_dir)
            if completed is None or completed.get("logical_content_fingerprint") != prepared_fingerprint:
                raise RuntimeError("resumable Candidate audit did not complete its formal finalization")
            manifest = completed
    print(json.dumps(_summary(manifest, args.output_dir), sort_keys=True, separators=(",", ":")))
    return 0


def _audit_api():
    # Imported lazily so --verify-output tests can prove the source/data path is never touched.
    from tip_api.services.opportunity_candidate_audit import (
        read_opportunity_candidate_audit,
        validate_tmp_output_dir,
        write_opportunity_candidate_audit,
    )

    return read_opportunity_candidate_audit, write_opportunity_candidate_audit, validate_tmp_output_dir


def _read_prior_candidate_audit(path: Path):
    from tip_api.services.opportunity_candidate_audit import read_opportunity_candidate_audit_contents

    return read_opportunity_candidate_audit_contents(path)


def _finalize_resumable_audit(work_dir: Path, output_dir: Path):
    from tip_api.services.opportunity_candidate_audit import finalize_resumable_candidate_audit

    return finalize_resumable_candidate_audit(work_dir, output_dir)


def _list_available_eod_sessions(data_root: Path) -> tuple[date, ...]:
    return tuple(item.session_date for item in CanonicalEodReadRepository(data_root).list_sessions())


def _read_phase1b_payloads(
    path: Path,
) -> tuple[tuple[MarketRegimeStateRecordV1, ...], dict[str, Any], dict[str, Any]]:
    state_payload = json.loads((path / "state-history.json").read_text(encoding="utf-8"))
    source_payload = json.loads((path / "source-input-manifest.json").read_text(encoding="utf-8"))
    current_payload = json.loads((path / "current-state-summary.json").read_text(encoding="utf-8"))
    records = tuple(MarketRegimeStateRecordV1.model_validate(item) for item in state_payload["records"])
    return records, source_payload, current_payload


def _validate_phase1b(
    *, manifest: Mapping[str, Any], state_records: Sequence[MarketRegimeStateRecordV1],
    source_payload: Mapping[str, Any], current_payload: Mapping[str, Any], as_of_session: date,
) -> None:
    if manifest.get("calculation_version") != STATE_CALCULATION_VERSION:
        raise RuntimeError("Phase 1b calculation version mismatch")
    if manifest.get("state_parameter_fingerprint") != STATE_PARAMETER_FINGERPRINT:
        raise RuntimeError("Phase 1b parameter fingerprint mismatch")
    if manifest.get("as_of_session") != as_of_session.isoformat():
        raise RuntimeError("Phase 1b as-of session mismatch")
    if tuple(manifest.get("universe_ids", ())) != PUBLIC_UNIVERSE_ORDER:
        raise RuntimeError("Phase 1b Universe order mismatch")
    state_sessions = tuple(
        date.fromisoformat(item)
        for item in source_payload.get("state_sessions", source_payload.get("history_sessions", ()))
    )
    if tuple(sorted(state_sessions)) != state_sessions or len(set(state_sessions)) != len(state_sessions):
        raise RuntimeError("Phase 1b state sessions are not unique and ascending")
    if not state_sessions or state_sessions[-1] != as_of_session:
        raise RuntimeError("Phase 1b state history does not end at as-of")
    current_rows = tuple(current_payload.get("records", ()))
    if tuple(item.get("universe_id") for item in current_rows) != PUBLIC_UNIVERSE_ORDER:
        raise RuntimeError("Phase 1b current-state Universe order mismatch")
    current_by_universe = {
        item.universe_id: item
        for item in state_records
        if item.as_of_session == as_of_session
    }
    if any(
        row.get("current", {}).get("logical_fingerprint")
        != current_by_universe[row["universe_id"]].logical_fingerprint
        for row in current_rows
    ):
        raise RuntimeError("Phase 1b current-state summary does not match state history")


def _select_candidate_sessions(
    *, state_records: Sequence[MarketRegimeStateRecordV1], available_eod_sessions: Sequence[date],
    as_of_session: date, calendar: ExchangeCalendar,
) -> tuple[date, ...]:
    available = set(available_eod_sessions)
    by_session: dict[date, set[str]] = defaultdict(set)
    for item in state_records:
        if item.as_of_session <= as_of_session:
            by_session[item.as_of_session].add(item.universe_id)
    candidates = []
    for session in sorted(by_session):
        if by_session[session] != set(PUBLIC_UNIVERSE_ORDER):
            raise RuntimeError("Phase 1b state history has an incomplete Universe session")
        required = calendar.sessions_before(session, CANDIDATE_PANEL_SESSION_COUNT - 1) + (session,)
        if len(required) != CANDIDATE_PANEL_SESSION_COUNT:
            raise RuntimeError("calendar could not resolve an exact candidate panel")
        if set(required) <= available:
            candidates.append(session)
    if not candidates or candidates[-1] != as_of_session:
        raise RuntimeError("canonical EOD does not contain the required as-of candidate window")
    return tuple(candidates)


def _calculate_offline(
    *, data_root: Path, candidate_sessions: tuple[date, ...],
    regime_records: Sequence[MarketRegimeStateRecordV1],
) -> CandidateOfflineRun:
    profiler = _StageProfiler()
    regime_by_key = {(item.as_of_session, item.universe_id): item for item in regime_records}
    panels: list[MarketRegimeInputPanel] = []
    batches_by_universe: dict[str, list[OpportunityCandidateBatchV1]] = {
        universe_id: [] for universe_id in PUBLIC_UNIVERSE_ORDER
    }
    states_by_universe_and_id: dict[tuple[str, UUID], list[OpportunityCandidateStateRecordV1]] = {}
    observations_by_universe_and_id: dict[tuple[str, UUID], list[CandidateStateObservationV1]] = {}
    oracle_reports: list[CandidateOracleComparisonV1] = []
    final_session_risk = ()

    with profiler.stage("panel_load_validate"):
        loaded_panels = load_formal_market_regime_panels(
            data_root=data_root,
            as_of_sessions=candidate_sessions,
        )
        for session, panel in zip(candidate_sessions, loaded_panels, strict=True):
            _validate_panel_catalog(panel, session)

    for session_index, (session, panel) in enumerate(zip(candidate_sessions, loaded_panels, strict=True)):
        with profiler.stage("candidate_state_index_build"):
            bars_by_instrument, latest_bar_by_instrument = _index_panel_bars(panel)
        panels.append(panel)
        session_batches = []
        for universe_id in PUBLIC_UNIVERSE_ORDER:
            member_ids = tuple(sorted(panel.select_universe(universe_id).member_ids, key=str))
            as_of_bar_ids = {
                item.instrument_id
                for item in panel.bars
                if item.session_date == session
            }
            covered_member_ids = tuple(
                instrument_id for instrument_id in member_ids if instrument_id in as_of_bar_ids
            )
            prior_flat = tuple(
                row
                for (candidate_universe, _), history in states_by_universe_and_id.items()
                if candidate_universe == universe_id
                for row in history
            )
            prior_source = candidate_prior_state_source_from_history(
                history=prior_flat,
                as_of_session=session,
                universe_id=universe_id,
                instrument_ids=covered_member_ids,
            )
            regime = regime_by_key[(session, universe_id)]
            with profiler.stage("candidate_score_calculation"):
                batch = calculate_opportunity_candidate_scores(
                    panel=panel,
                    universe_id=universe_id,
                    regime_score=regime.composite,
                    regime_state=regime.confirmed_state,
                    regime_source_fingerprint=regime.logical_fingerprint,
                    prior_state_source=prior_source,
                )
            batches_by_universe[universe_id].append(batch)
            session_batches.append(batch)
            with profiler.stage("candidate_state_update"):
                candidates = {item.instrument_id: item for item in batch.candidates}
                metadata = _member_metadata(
                    panel,
                    member_ids,
                    candidates,
                    universe_id,
                    latest_bar_by_instrument=latest_bar_by_instrument,
                )
                for instrument_id in member_ids:
                    candidate = candidates.get(instrument_id)
                    observation = None
                    if candidate is not None:
                        observation = CandidateStateObservationV1(
                            candidate=candidate,
                            regime_state=regime.confirmed_state,
                            breakout_fact=_breakout_fact(
                                panel,
                                candidate,
                                bars_by_session=bars_by_instrument.get(candidate.instrument_id, {}),
                            ),
                        )
                        observations_by_universe_and_id.setdefault((universe_id, instrument_id), []).append(observation)
                    key = (universe_id, instrument_id)
                    history = states_by_universe_and_id.setdefault(key, [])
                    ticker, security_type = metadata[instrument_id]
                    if history:
                        new_rows = append_opportunity_candidate_state_history(
                            existing_history=tuple(history),
                            observations=(() if observation is None else (observation,)),
                            expected_sessions=(session,),
                            universe_id=universe_id,
                            instrument_id=instrument_id,
                            ticker=ticker,
                            security_type=security_type,
                        )
                    else:
                        new_rows = replay_opportunity_candidate_state_history(
                            observations=(() if observation is None else (observation,)),
                            expected_sessions=(session,),
                            universe_id=universe_id,
                            instrument_id=instrument_id,
                            ticker=ticker,
                            security_type=security_type,
                        )
                    history.extend(new_rows)

        state_cases = ()
        if session_index == len(candidate_sessions) - 1:
            state_cases = tuple(
                CandidateStateOracleCase(
                    observations=tuple(observations_by_universe_and_id.get(key, ())),
                    expected_sessions=candidate_sessions,
                    universe_id=key[0],
                    instrument_id=key[1],
                    ticker=history[-1].ticker,
                    security_type=history[-1].security_type,
                    actual_records=tuple(history),
                )
                for key, history in sorted(states_by_universe_and_id.items(), key=lambda item: (item[0][0], str(item[0][1])))
            )
        risk = ()
        if session_index == len(candidate_sessions) - 1:
            with profiler.stage("candidate_risk_ranking"):
                risk = tuple(
                    rank_opportunity_candidates(batch=batch, risk_mode=mode)
                    for batch in session_batches
                    for mode in CandidateRiskMode
                )
            final_session_risk = risk
        with profiler.stage("candidate_independent_oracle"):
            oracle_reports.append(
                compare_with_independent_candidate_oracle(
                    panel=panel,
                    batches=tuple(session_batches),
                    regime_context_by_universe={
                        universe_id: (
                            regime_by_key[(session, universe_id)].composite,
                            regime_by_key[(session, universe_id)].confirmed_state,
                        )
                        for universe_id in PUBLIC_UNIVERSE_ORDER
                    },
                    risk_results=risk,
                    state_cases=state_cases,
                )
            )

    current_risk = final_session_risk
    flattened_states = {
        universe_id: tuple(
            row
            for (candidate_universe, _), history in sorted(
                states_by_universe_and_id.items(), key=lambda item: (item[0][0], str(item[0][1]))
            )
            if candidate_universe == universe_id
            for row in history
        )
        for universe_id in PUBLIC_UNIVERSE_ORDER
    }
    with profiler.stage("candidate_replay_equivalence"):
        equivalence = _equivalence_checks(
            candidate_sessions=candidate_sessions,
            states=states_by_universe_and_id,
            observations=observations_by_universe_and_id,
        )
    return CandidateOfflineRun(
        panels=tuple(panels),
        score_history={key: tuple(value) for key, value in batches_by_universe.items()},
        state_history=flattened_states,
        current_risk_results=current_risk,
        oracle_report=_combine_oracles(oracle_reports),
        equivalence_flags=equivalence,
        candidate_sessions=candidate_sessions,
        timings=profiler.timings(),
        runtime_metrics={
            **profiler.invocation_metrics(),
            "panel_load_count": len(candidate_sessions),
            "candidate_batch_count": len(candidate_sessions) * len(PUBLIC_UNIVERSE_ORDER),
        },
    )


def _calculate_incremental(
    *,
    data_root: Path,
    candidate_sessions: tuple[date, ...],
    regime_records: Sequence[MarketRegimeStateRecordV1],
    prior_audit,
    panel_cache_root: Path | None = None,
    expected_panel_source: Mapping[str, Any] | None = None,
) -> CandidateIncrementalRun:
    """Append exactly one session to a formally verified Candidate audit."""

    profiler = _StageProfiler()
    if len(candidate_sessions) < 2:
        raise RuntimeError("incremental Candidate calculation requires a non-empty prior prefix")
    current_session = candidate_sessions[-1]
    prior_session = candidate_sessions[-2]
    regime_by_key = {(item.as_of_session, item.universe_id): item for item in regime_records}

    with profiler.stage("incremental_panel_load_validate"):
        panel, panel_cache_status, panel_cache_fingerprint = _load_incremental_panel(
            data_root=data_root,
            current_session=current_session,
            panel_cache_root=panel_cache_root,
            expected_panel_source=expected_panel_source,
        )
        _validate_panel_catalog(panel, current_session)
        _validate_incremental_prior(
            prior_audit=prior_audit,
            candidate_sessions=candidate_sessions,
            regime_by_key=regime_by_key,
            current_panel=panel,
        )

    prior_batches_by_universe = {
        universe_id: tuple(
            item for item in prior_audit.candidate_batches if item.universe_id == universe_id
        )
        for universe_id in PUBLIC_UNIVERSE_ORDER
    }
    histories: dict[tuple[str, UUID], list[OpportunityCandidateStateRecordV1]] = {}
    for row in prior_audit.state_history:
        histories.setdefault((row.universe_id, row.instrument_id), []).append(row)
    prior_state_fingerprints = tuple(item.logical_fingerprint for item in prior_audit.state_history)
    prior_batch_fingerprints = tuple(item.logical_fingerprint for item in prior_audit.candidate_batches)

    with profiler.stage("incremental_state_index_build"):
        bars_by_instrument, latest_bar_by_instrument = _index_panel_bars(panel)
    current_batches: dict[str, tuple[OpportunityCandidateBatchV1, ...]] = {}
    incremental_cases: list[CandidateIncrementalStateOracleCase] = []
    session_batches: list[OpportunityCandidateBatchV1] = []

    for universe_id in PUBLIC_UNIVERSE_ORDER:
        member_ids = tuple(sorted(panel.select_universe(universe_id).member_ids, key=str))
        as_of_bar_ids = {
            item.instrument_id for item in panel.bars if item.session_date == current_session
        }
        covered_member_ids = tuple(item for item in member_ids if item in as_of_bar_ids)
        prior_flat = tuple(
            row for row in prior_audit.state_history if row.universe_id == universe_id
        )
        prior_source = candidate_prior_state_source_from_history(
            history=prior_flat,
            as_of_session=current_session,
            universe_id=universe_id,
            instrument_ids=covered_member_ids,
        )
        regime = regime_by_key[(current_session, universe_id)]
        with profiler.stage("incremental_candidate_score_calculation"):
            batch = calculate_opportunity_candidate_scores(
                panel=panel,
                universe_id=universe_id,
                regime_score=regime.composite,
                regime_state=regime.confirmed_state,
                regime_source_fingerprint=regime.logical_fingerprint,
                prior_state_source=prior_source,
            )
        current_batches[universe_id] = (batch,)
        session_batches.append(batch)
        candidates = {item.instrument_id: item for item in batch.candidates}
        metadata = _member_metadata(
            panel,
            member_ids,
            candidates,
            universe_id,
            latest_bar_by_instrument=latest_bar_by_instrument,
        )
        with profiler.stage("incremental_candidate_state_append"):
            for instrument_id in member_ids:
                key = (universe_id, instrument_id)
                history = histories.get(key)
                if not history or history[-1].as_of_session != prior_session:
                    raise RuntimeError("incremental Candidate state prefix is incomplete")
                candidate = candidates.get(instrument_id)
                observation = None
                if candidate is not None:
                    observation = CandidateStateObservationV1(
                        candidate=candidate,
                        regime_state=regime.confirmed_state,
                        breakout_fact=_breakout_fact(
                            panel,
                            candidate,
                            bars_by_session=bars_by_instrument.get(instrument_id, {}),
                        ),
                    )
                ticker, security_type = metadata[instrument_id]
                appended = append_opportunity_candidate_state_history(
                    existing_history=tuple(history),
                    observations=(() if observation is None else (observation,)),
                    expected_sessions=(current_session,),
                    universe_id=universe_id,
                    instrument_id=instrument_id,
                    ticker=ticker,
                    security_type=security_type,
                )
                if len(appended) != 1:
                    raise RuntimeError("incremental Candidate state append did not emit exactly one row")
                repeated = append_opportunity_candidate_state_history(
                    existing_history=tuple(history),
                    observations=(() if observation is None else (observation,)),
                    expected_sessions=(current_session,),
                    universe_id=universe_id,
                    instrument_id=instrument_id,
                    ticker=ticker,
                    security_type=security_type,
                )
                if repeated[0].logical_fingerprint != appended[0].logical_fingerprint:
                    raise RuntimeError("incremental Candidate state restart equivalence failed")
                prior_record = history[-1]
                history.extend(appended)
                incremental_cases.append(
                    CandidateIncrementalStateOracleCase(
                        prior_record=prior_record,
                        observation=observation,
                        as_of_session=current_session,
                        universe_id=universe_id,
                        instrument_id=instrument_id,
                        ticker=ticker,
                        security_type=security_type,
                        actual_record=appended[0],
                    )
                )

    with profiler.stage("incremental_candidate_risk_ranking"):
        current_risk = tuple(
            rank_opportunity_candidates(batch=batch, risk_mode=mode)
            for batch in session_batches
            for mode in CandidateRiskMode
        )
    with profiler.stage("incremental_candidate_independent_oracle"):
        oracle = compare_with_independent_candidate_oracle(
            panel=panel,
            batches=tuple(session_batches),
            regime_context_by_universe={
                universe_id: (
                    regime_by_key[(current_session, universe_id)].composite,
                    regime_by_key[(current_session, universe_id)].confirmed_state,
                )
                for universe_id in PUBLIC_UNIVERSE_ORDER
            },
            risk_results=current_risk,
            incremental_state_cases=tuple(incremental_cases),
        )

    score_history = {
        universe_id: (*prior_batches_by_universe[universe_id], *current_batches[universe_id])
        for universe_id in PUBLIC_UNIVERSE_ORDER
    }
    state_history = {
        universe_id: tuple(
            row
            for (candidate_universe, _), rows in sorted(
                histories.items(), key=lambda item: (item[0][0], str(item[0][1]))
            )
            if candidate_universe == universe_id
            for row in rows
        )
        for universe_id in PUBLIC_UNIVERSE_ORDER
    }
    combined_batch_fingerprints = tuple(
        item.logical_fingerprint
        for session in candidate_sessions
        for universe_id in PUBLIC_UNIVERSE_ORDER
        for item in score_history[universe_id]
        if item.as_of_session == session
    )
    combined_state_fingerprints = tuple(
        row.logical_fingerprint
        for session in candidate_sessions
        for universe_id in PUBLIC_UNIVERSE_ORDER
        for row in state_history[universe_id]
        if row.as_of_session == session
    )
    flags = {
        "prior_prefix_preserved": combined_batch_fingerprints[:-len(PUBLIC_UNIVERSE_ORDER)]
        == prior_batch_fingerprints,
        "incremental_restart_match": oracle.mismatch_count == 0,
        "future_prefix_stable": combined_state_fingerprints[:-len(incremental_cases)]
        == prior_state_fingerprints,
        "input_permutation_match": oracle.input_permutation_match,
    }
    return CandidateIncrementalRun(
        panels=(panel,),
        score_history=score_history,
        state_history=state_history,
        current_risk_results=current_risk,
        oracle_report=oracle,
        equivalence_flags=flags,
        candidate_sessions=candidate_sessions,
        timings=profiler.timings(),
        runtime_metrics={
            **profiler.invocation_metrics(),
            "panel_load_count": 1,
            "candidate_batch_count": len(PUBLIC_UNIVERSE_ORDER),
            "reused_candidate_session_count": len(candidate_sessions) - 1,
            "panel_cache_hit_count": 1 if panel_cache_status == "hit" else 0,
            "panel_cache_write_count": 1 if panel_cache_status == "populated" else 0,
        },
        current_score_history=current_batches,
        panel_cache_status=panel_cache_status,
        panel_cache_logical_fingerprint=panel_cache_fingerprint,
    )


def _validate_incremental_prior(*, prior_audit, candidate_sessions, regime_by_key, current_panel) -> None:
    manifest = prior_audit.manifest
    prior_sessions = tuple(
        date.fromisoformat(item["as_of_session"]) for item in prior_audit.source_panels
    )
    if prior_sessions != candidate_sessions[:-1]:
        raise RuntimeError("prior Candidate audit does not exactly match the current session prefix")
    if manifest.get("as_of_session") != candidate_sessions[-2].isoformat():
        raise RuntimeError("prior Candidate audit is not the immediate predecessor")
    if tuple(manifest.get("universe_ids", ())) != PUBLIC_UNIVERSE_ORDER:
        raise RuntimeError("prior Candidate audit Universe order mismatch")
    prior_panel = prior_audit.source_panels[-1]
    if prior_panel.get("activation_pointer_fingerprint") != current_panel.activation_pointer_fingerprint:
        raise RuntimeError("Candidate Activation changed; a cold full replay is required")
    current_memberships = {
        item.universe_id: item.membership_fingerprint for item in current_panel.universes
    }
    prior_memberships = {
        item["universe_id"]: item["membership_fingerprint"]
        for item in prior_panel.get("universes", ())
    }
    if prior_memberships != current_memberships:
        raise RuntimeError("Candidate Universe membership changed; a cold full replay is required")
    batch_keys = {(item.as_of_session, item.universe_id) for item in prior_audit.candidate_batches}
    expected_keys = {
        (session, universe_id)
        for session in prior_sessions
        for universe_id in PUBLIC_UNIVERSE_ORDER
    }
    if batch_keys != expected_keys:
        raise RuntimeError("prior Candidate batch prefix is incomplete")
    for batch in prior_audit.candidate_batches:
        regime = regime_by_key.get((batch.as_of_session, batch.universe_id))
        if regime is None or batch.regime_source_fingerprint != regime.logical_fingerprint:
            raise RuntimeError("prior Candidate audit no longer matches Phase 1b history")


def _load_incremental_panel(
    *,
    data_root: Path,
    current_session: date,
    panel_cache_root: Path | None,
    expected_panel_source: Mapping[str, Any] | None,
) -> tuple[MarketRegimeInputPanel, str, str | None]:
    """Load an exact verified stage cache or populate it from the formal cold reader."""

    expected_boundary = None
    if expected_panel_source is not None:
        try:
            expected_boundary = normalize_source_boundary(expected_panel_source)
        except MarketRegimePanelCacheError as exc:
            # Legacy stable-prefix Phase 1b ledgers span more than the exact
            # Candidate panel and cannot select a cache entry. The cold reader
            # remains the compatible fallback.
            if (
                expected_panel_source.get("source_custody_mode")
                == "verified_prior_state_plus_current_phase1a_audit"
            ):
                raise RuntimeError("current Phase 1b panel source custody is malformed") from exc
            expected_boundary = None
    if panel_cache_root is not None and expected_boundary is not None and panel_cache_root.exists():
        try:
            panel, manifest = read_market_regime_panel_cache(
                cache_root=panel_cache_root,
                expected_source=expected_boundary,
            )
            return panel, "hit", manifest["logical_content_fingerprint"]
        except MarketRegimePanelCacheMiss:
            pass
        except MarketRegimePanelCacheError as exc:
            raise RuntimeError("candidate panel cache failed formal reread") from exc

    panels = load_formal_market_regime_panels(
        data_root=data_root,
        as_of_sessions=(current_session,),
    )
    if len(panels) != 1:
        raise RuntimeError("incremental Candidate calculation requires exactly one current panel")
    panel = panels[0]
    if expected_boundary is not None and panel_source_boundary(panel) != expected_boundary:
        raise RuntimeError("formal Candidate panel does not match Phase 1b source custody")
    if panel_cache_root is None:
        return panel, "disabled", None
    try:
        manifest = write_market_regime_panel_cache(cache_root=panel_cache_root, panel=panel)
    except MarketRegimePanelCacheError as exc:
        raise RuntimeError("candidate panel cache population failed") from exc
    return panel, "populated", manifest["logical_content_fingerprint"]


def _incremental_validation_ledger(*, prior_audit, run: CandidateIncrementalRun) -> dict[str, Any]:
    prior_validation = prior_audit.validation_ledger
    if prior_validation is None:
        segments = (
            {
                "scope": "verified_legacy_prefix",
                "through_session": prior_audit.manifest["as_of_session"],
                "audit_logical_fingerprint": prior_audit.manifest["logical_content_fingerprint"],
                "oracle_fingerprint": prior_audit.manifest["oracle_fingerprint"],
            },
        )
    else:
        segments = tuple(prior_validation.get("validation_segments", ()))
    segments = (
        *segments,
        {
            "scope": "current_session_independent_oracle",
            "session": run.candidate_sessions[-1].isoformat(),
            "oracle_fingerprint": run.oracle_report.oracle_fingerprint,
            "oracle_mismatch_count": run.oracle_report.mismatch_count,
        },
    )
    return {
        "validation_scope": "verified_prior_plus_current_session_oracle",
        "prior_audit_logical_fingerprint": prior_audit.manifest["logical_content_fingerprint"],
        "prior_as_of_session": prior_audit.manifest["as_of_session"],
        "current_as_of_session": run.candidate_sessions[-1].isoformat(),
        "prior_candidate_history_fingerprint": prior_audit.manifest["candidate_history_fingerprint"],
        "prior_candidate_state_history_fingerprint": prior_audit.manifest[
            "candidate_state_history_fingerprint"
        ],
        "prior_raw_facts_records_fingerprint": _records_fingerprint(prior_audit.raw_facts),
        "prior_normalization_records_fingerprint": _records_fingerprint(
            prior_audit.normalization_ledger
        ),
        "current_session_oracle_fingerprint": run.oracle_report.oracle_fingerprint,
        "current_panel_stage_cache_status": run.panel_cache_status,
        "current_panel_stage_logical_fingerprint": run.panel_cache_logical_fingerprint,
        "reuse_checks": {
            "prior_audit_formally_reread": True,
            "candidate_session_prefix_exact": True,
            "activation_unchanged": True,
            "membership_unchanged": True,
            "phase1b_prefix_compatible": True,
            "prior_candidate_prefix_preserved": run.equivalence_flags["prior_prefix_preserved"],
            "prior_state_prefix_preserved": run.equivalence_flags["future_prefix_stable"],
            "current_panel_formally_validated": True,
        },
        "validation_segments": segments,
    }


def _validate_panel_catalog(panel: MarketRegimeInputPanel, session: date) -> None:
    if panel.as_of_session != session:
        raise RuntimeError("formal candidate panel session mismatch")
    if tuple(item.universe_id for item in sorted(panel.universes, key=lambda item: item.catalog_order)) != PUBLIC_UNIVERSE_ORDER:
        raise RuntimeError("formal candidate panel Universe order mismatch")


def _index_panel_bars(panel):
    by_instrument = defaultdict(dict)
    latest_by_id = {}
    for bar in panel.bars:
        if bar.session_date in by_instrument[bar.instrument_id]:
            raise RuntimeError("duplicate candidate state instrument/session bar")
        by_instrument[bar.instrument_id][bar.session_date] = bar
        previous = latest_by_id.get(bar.instrument_id)
        if previous is None or bar.session_date > previous.session_date:
            latest_by_id[bar.instrument_id] = bar
    return dict(by_instrument), latest_by_id


def _member_metadata(panel, member_ids, candidates, universe_id, *, latest_bar_by_instrument):
    primary_ids = panel.select_universe(PUBLIC_UNIVERSE_ORDER[0]).member_ids
    output = {}
    for instrument_id in member_ids:
        if instrument_id in candidates:
            output[instrument_id] = (candidates[instrument_id].ticker, candidates[instrument_id].security_type)
        elif instrument_id in latest_bar_by_instrument:
            output[instrument_id] = (
                latest_bar_by_instrument[instrument_id].ticker,
                "CS" if instrument_id in primary_ids else "ADRC",
            )
        else:
            raise RuntimeError(f"cannot source candidate-state display identity for missing member: {instrument_id}")
    return output


def _breakout_fact(panel, candidate, *, bars_by_session):
    prior_sessions = panel.sessions[-6:-1]
    if (
        len(prior_sessions) != 5
        or any(session not in bars_by_session for session in (*prior_sessions, panel.as_of_session))
        or candidate.current_volume_ratio is None
    ):
        return CandidateBreakoutFactV1(
            as_of_session=panel.as_of_session,
            instrument_id=candidate.instrument_id,
            availability=CandidateBreakoutAvailability.UNAVAILABLE,
            close=None,
            prior_five_session_close_high=None,
            current_volume_ratio=None,
            prior_five_sessions=(),
            triggered=None,
            missing_reason="insufficient_prior_five_session_history",
            reason_codes=("insufficient_prior_five_session_history",),
        )
    close = bars_by_session[panel.as_of_session].close
    prior_high = max(bars_by_session[item].close for item in prior_sessions)
    ratio = Decimal(candidate.current_volume_ratio)
    return CandidateBreakoutFactV1(
        as_of_session=panel.as_of_session,
        instrument_id=candidate.instrument_id,
        availability=CandidateBreakoutAvailability.AVAILABLE,
        close=_raw(close),
        prior_five_session_close_high=_raw(prior_high),
        current_volume_ratio=candidate.current_volume_ratio,
        prior_five_sessions=prior_sessions,
        triggered=close > prior_high and ratio >= Decimal("1.20"),
        missing_reason=None,
        reason_codes=("typed_breakout_fact",),
    )


def _equivalence_checks(*, candidate_sessions, states, observations):
    append_match = restart_match = permutation_match = future_match = True
    for key, full in states.items():
        case_observations = tuple(observations.get(key, ()))
        midpoint = max(1, len(candidate_sessions) // 2)
        prefix = replay_opportunity_candidate_state_history(
            observations=tuple(item for item in case_observations if item.candidate.as_of_session in candidate_sessions[:midpoint]),
            expected_sessions=candidate_sessions[:midpoint], universe_id=key[0], instrument_id=key[1], ticker=full[-1].ticker, security_type=full[-1].security_type,
        )
        suffix = append_opportunity_candidate_state_history(
            existing_history=prefix,
            observations=tuple(item for item in case_observations if item.candidate.as_of_session in candidate_sessions[midpoint:]),
            expected_sessions=candidate_sessions[midpoint:], universe_id=key[0], instrument_id=key[1], ticker=full[-1].ticker, security_type=full[-1].security_type,
        ) if midpoint < len(candidate_sessions) else ()
        append_match &= tuple(item.logical_fingerprint for item in (*prefix, *suffix)) == tuple(item.logical_fingerprint for item in full)
        restarted = replay_opportunity_candidate_state_history(
            observations=tuple(reversed(case_observations)), expected_sessions=candidate_sessions,
            universe_id=key[0], instrument_id=key[1], ticker=full[-1].ticker, security_type=full[-1].security_type,
        )
        restart_match &= opportunity_candidate_state_history_fingerprint(restarted) == opportunity_candidate_state_history_fingerprint(full)
        permutation_match &= restart_match
        prefix_only = replay_opportunity_candidate_state_history(
            observations=tuple(item for item in case_observations if item.candidate.as_of_session in candidate_sessions[:-1]),
            expected_sessions=candidate_sessions[:-1], universe_id=key[0], instrument_id=key[1], ticker=full[-1].ticker, security_type=full[-1].security_type,
        ) if len(candidate_sessions) > 1 else ()
        future_match &= tuple(item.logical_fingerprint for item in prefix_only) == tuple(item.logical_fingerprint for item in full[:-1])
    return {
        "append_full_replay_match": append_match,
        "restart_replay_match": restart_match,
        "input_permutation_match": permutation_match,
        "future_prefix_stable": future_match,
    }


def _combine_oracles(reports: Sequence[CandidateOracleComparisonV1]) -> CandidateOracleComparisonV1:
    mismatches = tuple(item for report in reports for item in report.mismatches)
    fingerprint = hashlib.sha256("".join(item.oracle_fingerprint for item in reports).encode("ascii")).hexdigest()
    return CandidateOracleComparisonV1(
        candidate_count=sum(item.candidate_count for item in reports),
        risk_result_count=sum(item.risk_result_count for item in reports),
        state_record_count=sum(item.state_record_count for item in reports),
        raw_fact_count=sum(item.raw_fact_count for item in reports),
        mismatch_count=len(mismatches),
        mismatches=mismatches,
        shared_raw_fact_match=all(item.shared_raw_fact_match for item in reports),
        input_permutation_match=all(item.input_permutation_match for item in reports),
        oracle_fingerprint=fingerprint,
    )


def _raw_fact_records(
    score_history: Mapping[str, Sequence[OpportunityCandidateBatchV1]],
) -> tuple[dict[str, Any], ...]:
    """Extract one Universe-neutral raw projection per session/stable ID."""

    by_key: dict[tuple[date, UUID], dict[str, Any]] = {}
    for universe_id in PUBLIC_UNIVERSE_ORDER:
        for batch in score_history[universe_id]:
            for candidate in batch.candidates:
                raw_metrics = {
                    metric.metric_id: {
                        "raw_value": metric.raw_value,
                        "raw_unit": metric.raw_unit,
                        "availability": metric.availability.value,
                        "missing_reason": metric.missing_reason,
                        "source_sessions": [item.isoformat() for item in metric.source_sessions],
                    }
                    for component in candidate.components
                    for metric in component.metrics
                    if metric.metric_id != "regime_score"
                }
                row = {
                    "as_of_session": candidate.as_of_session.isoformat(),
                    "instrument_id": str(candidate.instrument_id),
                    "ticker": candidate.ticker,
                    "security_type": candidate.security_type,
                    "raw_metrics": dict(sorted(raw_metrics.items())),
                    "latest_price": candidate.latest_price,
                    "median_dollar_volume_20": candidate.median_dollar_volume_20,
                    "annualized_volatility_10": candidate.annualized_volatility_10,
                    "maximum_absolute_open_gap_5": candidate.maximum_absolute_open_gap_5,
                    "current_volume_ratio": candidate.current_volume_ratio,
                    "primary_driver_instrument_id": (
                        None if candidate.primary_driver_instrument_id is None else str(candidate.primary_driver_instrument_id)
                    ),
                    "primary_driver_ticker": candidate.primary_driver_ticker,
                    "driver_correlation_20": candidate.driver_correlation_20,
                    "corporate_action_review_required": candidate.corporate_action_review_required,
                }
                key = (candidate.as_of_session, candidate.instrument_id)
                if key in by_key and by_key[key] != row:
                    raise RuntimeError("shared candidate raw-fact projection differs across Universes")
                by_key[key] = row
    return tuple(by_key[key] for key in sorted(by_key, key=lambda item: (item[0], str(item[1]))))


def _normalization_records(
    score_history: Mapping[str, Sequence[OpportunityCandidateBatchV1]],
) -> tuple[dict[str, Any], ...]:
    """Persist Universe-context normalized values without calling them raw facts."""

    rows = []
    for universe_id in PUBLIC_UNIVERSE_ORDER:
        for batch in score_history[universe_id]:
            for candidate in batch.candidates:
                rows.append(
                    {
                        "as_of_session": candidate.as_of_session.isoformat(),
                        "universe_id": universe_id,
                        "instrument_id": str(candidate.instrument_id),
                        "normalized_metrics": {
                            metric.metric_id: metric.normalized_value
                            for component in candidate.components
                            for metric in component.metrics
                        },
                        "component_scores": {
                            component.component_id: component.score
                            for component in candidate.components
                        },
                        "base_score": candidate.base_score,
                        "candidate_record_fingerprint": candidate.logical_fingerprint,
                    }
                )
    return tuple(rows)


def _summary(manifest: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    return {
        "status": "completed" if manifest.get("oracle_mismatch_count", 0) == 0 else "oracle_mismatch",
        "as_of_session": manifest.get("as_of_session"),
        "universe_ids": manifest.get("universe_ids"),
        "output_dir": str(output_dir),
        "logical_content_fingerprint": manifest.get("logical_content_fingerprint"),
        "oracle_mismatch_count": manifest.get("oracle_mismatch_count"),
        "external_request_count": 0,
        "production_write_count": 0,
    }


def _seconds(value: float) -> str:
    return format(value, ".6f")


def _records_fingerprint(value: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _process_io_counters() -> dict[str, int]:
    """Read Linux process I/O counters when available; unsupported hosts return none."""

    path = Path("/proc/self/io")
    try:
        rows = path.read_text(encoding="ascii").splitlines()
    except (FileNotFoundError, PermissionError, OSError):
        return {}
    counters: dict[str, int] = {}
    for row in rows:
        name, separator, raw_value = row.partition(":")
        if separator and raw_value.strip().isdigit():
            counters[name.strip()] = int(raw_value.strip())
    return counters


def _io_deltas(before: Mapping[str, int], after: Mapping[str, int]) -> dict[str, int]:
    retained = {"rchar", "wchar", "syscr", "syscw", "read_bytes", "write_bytes"}
    return {
        f"process_io_{name}_delta": max(0, after[name] - before.get(name, 0))
        for name in sorted(after)
        if name in retained
    }


def _resource_deltas(before, after) -> dict[str, int]:
    return {
        "process_input_block_delta": max(0, int(after.ru_inblock - before.ru_inblock)),
        "process_output_block_delta": max(0, int(after.ru_oublock - before.ru_oublock)),
        "process_voluntary_context_switch_delta": max(0, int(after.ru_nvcsw - before.ru_nvcsw)),
        "process_involuntary_context_switch_delta": max(0, int(after.ru_nivcsw - before.ru_nivcsw)),
    }


def _raw(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.0000000001")), "f")


@contextmanager
def _offline_socket_guard():
    original_socket, original_create, original_getaddrinfo = socket.socket, socket.create_connection, socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during offline candidate calculation")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during offline candidate calculation")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during offline candidate calculation")

    socket.socket, socket.create_connection, socket.getaddrinfo = GuardedSocket, rejected, rejected
    try:
        yield
    finally:
        socket.socket, socket.create_connection, socket.getaddrinfo = original_socket, original_create, original_getaddrinfo


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
