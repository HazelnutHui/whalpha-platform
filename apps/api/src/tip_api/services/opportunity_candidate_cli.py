"""Offline, socket-guarded Phase 5C candidate calculation CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import socket
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
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
from tip_api.parameters.market_regime.state_v1_0_0 import (
    STATE_CALCULATION_VERSION,
    STATE_PARAMETER_FINGERPRINT,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.market_regime_sources import MarketRegimeInputPanel, load_formal_market_regime_panel
from tip_api.services.market_regime_state_audit import read_market_regime_state_audit
from tip_api.services.opportunity_candidate_oracle import (
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Calculate Phase 5C opportunity candidates offline into a canonical /tmp audit."
    )
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--phase1b-audit", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verify-output", action="store_true", help="Reread an existing completed audit only.")
    args = parser.parse_args(argv)
    for name in ("data_root", "phase1b_audit", "output_dir"):
        if not getattr(args, name).is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")

    read_audit, write_audit, validate_output = _audit_api()
    if args.verify_output:
        manifest = read_audit(args.output_dir)
        print(json.dumps(_summary(manifest, args.output_dir), sort_keys=True, separators=(",", ":")))
        return 0

    validate_output(args.output_dir)
    started = time.monotonic()
    with _offline_socket_guard():
        phase1b = read_market_regime_state_audit(args.phase1b_audit)
        state_records, source_payload, current_payload = _read_phase1b_payloads(args.phase1b_audit)
        _validate_phase1b(
            manifest=phase1b,
            state_records=state_records,
            source_payload=source_payload,
            current_payload=current_payload,
            as_of_session=args.as_of_session,
        )
        available_eod_sessions = tuple(
            item.session_date for item in CanonicalEodReadRepository(args.data_root).list_sessions()
        )
        candidate_sessions = _select_candidate_sessions(
            state_records=state_records,
            available_eod_sessions=available_eod_sessions,
            as_of_session=args.as_of_session,
            calendar=ExchangeCalendar(),
        )
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
            raw_facts=_raw_fact_records(run.score_history),
            normalization_ledger=_normalization_records(run.score_history),
            generated_at=datetime.now(UTC),
            timings={"total_before_audit_write_seconds": elapsed},
            peak_memory_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        )
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
    history_sessions = tuple(date.fromisoformat(item) for item in source_payload.get("history_sessions", ()))
    if tuple(sorted(history_sessions)) != history_sessions or len(set(history_sessions)) != len(history_sessions):
        raise RuntimeError("Phase 1b source history sessions are not unique and ascending")
    if not history_sessions or history_sessions[-1] != as_of_session:
        raise RuntimeError("Phase 1b source history does not end at as-of")
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
    regime_by_key = {(item.as_of_session, item.universe_id): item for item in regime_records}
    panels: list[MarketRegimeInputPanel] = []
    batches_by_universe: dict[str, list[OpportunityCandidateBatchV1]] = {
        universe_id: [] for universe_id in PUBLIC_UNIVERSE_ORDER
    }
    states_by_universe_and_id: dict[tuple[str, UUID], list[OpportunityCandidateStateRecordV1]] = {}
    observations_by_universe_and_id: dict[tuple[str, UUID], list[CandidateStateObservationV1]] = {}
    oracle_reports: list[CandidateOracleComparisonV1] = []

    for session_index, session in enumerate(candidate_sessions):
        panel = load_formal_market_regime_panel(data_root=data_root, as_of_session=session)
        _validate_panel_catalog(panel, session)
        panels.append(panel)
        session_batches = []
        session_observations: dict[tuple[str, UUID], CandidateStateObservationV1] = {}
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
            candidates = {item.instrument_id: item for item in batch.candidates}
            metadata = _member_metadata(panel, member_ids, candidates, universe_id)
            for instrument_id in member_ids:
                candidate = candidates.get(instrument_id)
                observation = None
                if candidate is not None:
                    observation = CandidateStateObservationV1(
                        candidate=candidate,
                        regime_state=regime.confirmed_state,
                        breakout_fact=_breakout_fact(panel, candidate),
                    )
                    session_observations[(universe_id, instrument_id)] = observation
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
            risk = tuple(
                rank_opportunity_candidates(batch=batch, risk_mode=mode)
                for batch in session_batches
                for mode in CandidateRiskMode
            )
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

    current_batches = tuple(batches_by_universe[item][-1] for item in PUBLIC_UNIVERSE_ORDER)
    current_risk = tuple(
        rank_opportunity_candidates(batch=batch, risk_mode=mode)
        for batch in current_batches
        for mode in CandidateRiskMode
    )
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
    )


def _validate_panel_catalog(panel: MarketRegimeInputPanel, session: date) -> None:
    if panel.as_of_session != session:
        raise RuntimeError("formal candidate panel session mismatch")
    if tuple(item.universe_id for item in sorted(panel.universes, key=lambda item: item.catalog_order)) != PUBLIC_UNIVERSE_ORDER:
        raise RuntimeError("formal candidate panel Universe order mismatch")


def _member_metadata(panel, member_ids, candidates, universe_id):
    latest_by_id = {}
    for bar in sorted(panel.bars, key=lambda item: (item.session_date, str(item.instrument_id))):
        if bar.instrument_id in set(member_ids):
            latest_by_id[bar.instrument_id] = bar
    primary_ids = panel.select_universe(PUBLIC_UNIVERSE_ORDER[0]).member_ids
    output = {}
    for instrument_id in member_ids:
        if instrument_id in candidates:
            output[instrument_id] = (candidates[instrument_id].ticker, candidates[instrument_id].security_type)
        elif instrument_id in latest_by_id:
            output[instrument_id] = (latest_by_id[instrument_id].ticker, "CS" if instrument_id in primary_ids else "ADRC")
        else:
            raise RuntimeError(f"cannot source candidate-state display identity for missing member: {instrument_id}")
    return output


def _breakout_fact(panel, candidate):
    prior_sessions = panel.sessions[-6:-1]
    by_session = {
        item.session_date: item
        for item in panel.bars
        if item.instrument_id == candidate.instrument_id
    }
    if (
        len(prior_sessions) != 5
        or any(session not in by_session for session in (*prior_sessions, panel.as_of_session))
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
    close = by_session[panel.as_of_session].close
    prior_high = max(by_session[item].close for item in prior_sessions)
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
