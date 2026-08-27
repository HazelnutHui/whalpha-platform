"""Offline, tmp-only Market Regime Phase 1b state replay CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import socket
import time
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.contracts.market_data.v2.dashboard_universe_activation import PUBLIC_UNIVERSE_ORDER
from tip_api.parameters.market_regime.state_v1_0_1 import (
    FROZEN_PHASE1A_AUDIT_FINGERPRINT,
    PHASE1A_CALCULATION_VERSION,
    PHASE1A_PARAMETER_FINGERPRINT,
    STATE_CALCULATION_VERSION,
    STATE_PARAMETER_FINGERPRINT,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.market_regime_audit import (
    read_market_regime_audit,
    read_market_regime_audit_contents,
)
from tip_api.services.market_regime_history import calculate_phase1a_composite_history
from tip_api.services.market_regime_sources import load_formal_market_regime_history_panel
from tip_api.services.market_regime_state import (
    append_regime_state_history,
    replay_regime_state_history,
    state_history_fingerprint,
)
from tip_api.services.market_regime_state_audit import (
    _validate_tmp_output_dir,
    read_market_regime_state_audit,
    read_market_regime_state_audit_contents,
    write_market_regime_state_audit,
)
from tip_api.services.market_regime_state_oracle import (
    compare_incremental_with_independent_state_oracle,
    compare_with_independent_state_oracle,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay deterministic Market Regime Phase 1b states offline into a canonical /tmp audit."
    )
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--universe-id",
        action="append",
        required=True,
        choices=PUBLIC_UNIVERSE_ORDER,
        help="Repeat in Primary-first catalog order.",
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--phase1a-audit", required=True, type=Path)
    parser.add_argument(
        "--prior-state-audit",
        type=Path,
        help="Formally verified immediately prior Phase 1b audit for one-session append.",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verify-output", action="store_true", help="Reread an existing completed state audit only.")
    args = parser.parse_args(argv)
    for name in ("data_root", "phase1a_audit", "prior_state_audit", "output_dir"):
        value = getattr(args, name)
        if value is not None and not value.is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    if tuple(args.universe_id) != tuple(dict.fromkeys(args.universe_id)):
        parser.error("duplicate --universe-id is not allowed")
    ordered = tuple(item for item in PUBLIC_UNIVERSE_ORDER if item in args.universe_id)
    if tuple(args.universe_id) != ordered:
        parser.error("--universe-id values must use Primary-first catalog order")
    if args.verify_output:
        manifest = read_market_regime_state_audit(args.output_dir)
        print(json.dumps(_summary(manifest, args.output_dir), sort_keys=True, separators=(",", ":")))
        return 0

    _validate_tmp_output_dir(args.output_dir)
    total_started = time.monotonic()
    timings: dict[str, str] = {}
    with _offline_socket_guard():
        if args.prior_state_audit is not None:
            manifest = _run_incremental(
                as_of_session=args.as_of_session,
                universe_ids=ordered,
                phase1a_audit_path=args.phase1a_audit,
                prior_state_audit_path=args.prior_state_audit,
                output_dir=args.output_dir,
                total_started=total_started,
            )
            print(json.dumps(_summary(manifest, args.output_dir), sort_keys=True, separators=(",", ":")))
            return 0
        input_started = time.monotonic()
        phase1a_audit = read_market_regime_audit(args.phase1a_audit)
        _validate_phase1a_audit(phase1a_audit, args.as_of_session, ordered)
        panel = load_formal_market_regime_history_panel(
            data_root=args.data_root,
            as_of_session=args.as_of_session,
        )
        timings["source_load_seconds"] = _seconds(time.monotonic() - input_started)

        phase1a_started = time.monotonic()
        composite_history = calculate_phase1a_composite_history(panel=panel, universe_ids=ordered)
        timings["phase1a_history_calculation_seconds"] = _seconds(time.monotonic() - phase1a_started)
        current_fingerprints = [
            composite_history.composites_by_universe[item][-1].logical_fingerprint for item in ordered
        ]
        if current_fingerprints != phase1a_audit.get("composite_fingerprints"):
            raise RuntimeError("replayed current Phase 1a composite fingerprints do not match approved audit")

        state_sessions = tuple(
            item.as_of_session for item in composite_history.composites_by_universe[ordered[0]]
        )
        state_started = time.monotonic()
        histories = {}
        explanations = {}
        equivalence = {}
        for universe_id in ordered:
            composites = composite_history.composites_by_universe[universe_id]
            records, ledger = replay_regime_state_history(
                composites=composites,
                expected_sessions=state_sessions,
                universe_id=universe_id,
            )
            histories[universe_id] = records
            explanations[universe_id] = ledger
            equivalence[universe_id] = _equivalence_checks(
                composites=composites,
                sessions=state_sessions,
                universe_id=universe_id,
                full_records=records,
            )
        timings["state_classification_seconds"] = _seconds(time.monotonic() - state_started)

        oracle_started = time.monotonic()
        oracle_reports = []
        for universe_id in ordered:
            flags = equivalence[universe_id]
            oracle_reports.append(
                compare_with_independent_state_oracle(
                    composites=composite_history.composites_by_universe[universe_id],
                    expected_sessions=state_sessions,
                    universe_id=universe_id,
                    records=histories[universe_id],
                    explanations=explanations[universe_id],
                    append_full_replay_match=flags["append_full_replay_match"],
                    restart_replay_match=flags["restart_replay_match"],
                    input_permutation_match=flags["input_permutation_match"],
                    future_prefix_stable=flags["future_prefix_stable"],
                )
            )
        timings["state_oracle_seconds"] = _seconds(time.monotonic() - oracle_started)
        timings["total_before_audit_write_seconds"] = _seconds(time.monotonic() - total_started)
        manifest = write_market_regime_state_audit(
            output_dir=args.output_dir,
            panel=panel,
            phase1a_audit_manifest=phase1a_audit,
            histories=histories,
            explanations=explanations,
            oracle_reports=tuple(oracle_reports),
            first_calculable_session=composite_history.first_calculable_session,
            generated_at=datetime.now(UTC),
            timings=timings,
            peak_memory_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        )
    print(json.dumps(_summary(manifest, args.output_dir), sort_keys=True, separators=(",", ":")))
    return 1 if manifest["oracle_mismatch_count"] else 0


def _run_incremental(
    *,
    as_of_session: date,
    universe_ids: tuple[str, ...],
    phase1a_audit_path: Path,
    prior_state_audit_path: Path,
    output_dir: Path,
    total_started: float,
) -> dict[str, object]:
    """Append one state session without reopening canonical EOD partitions."""

    timings: dict[str, str] = {}
    started = time.monotonic()
    phase1a = read_market_regime_audit_contents(phase1a_audit_path)
    _validate_phase1a_audit(phase1a.manifest, as_of_session, universe_ids)
    _validate_phase1a_contents(phase1a, as_of_session, universe_ids)
    timings["phase1a_audit_read_validate_seconds"] = _seconds(time.monotonic() - started)

    started = time.monotonic()
    prior = read_market_regime_state_audit_contents(prior_state_audit_path)
    _validate_incremental_prior(
        prior=prior,
        phase1a=phase1a,
        as_of_session=as_of_session,
        universe_ids=universe_ids,
    )
    timings["prior_state_audit_read_validate_seconds"] = _seconds(time.monotonic() - started)

    composite_by_universe = {item.universe_id: item for item in phase1a.composites}
    histories = {}
    explanations = {}
    oracle_reports = []
    prefix_preserved = True
    restart_match = True
    started = time.monotonic()
    for universe_id in universe_ids:
        prior_history = prior.histories[universe_id]
        appended, appended_explanations = append_regime_state_history(
            existing_history=prior_history,
            composites=(composite_by_universe[universe_id],),
            expected_sessions=(as_of_session,),
            universe_id=universe_id,
        )
        repeated, repeated_explanations = append_regime_state_history(
            existing_history=prior_history,
            composites=(composite_by_universe[universe_id],),
            expected_sessions=(as_of_session,),
            universe_id=universe_id,
        )
        if len(appended) != 1 or len(appended_explanations) != 1:
            raise RuntimeError("incremental Phase 1b append did not emit exactly one row")
        local_restart = (
            repeated[0].logical_fingerprint == appended[0].logical_fingerprint
            and repeated_explanations[0].model_dump(mode="json")
            == appended_explanations[0].model_dump(mode="json")
        )
        restart_match &= local_restart
        histories[universe_id] = (*prior_history, appended[0])
        explanations[universe_id] = (*prior.explanations[universe_id], appended_explanations[0])
        prefix_preserved &= tuple(histories[universe_id][:-1]) == prior_history
        oracle_reports.append(
            compare_incremental_with_independent_state_oracle(
                prior_record=prior_history[-1],
                composite=composite_by_universe[universe_id],
                expected_session=as_of_session,
                universe_id=universe_id,
                record=appended[0],
                explanation=appended_explanations[0],
                restart_match=local_restart,
            )
        )
    timings["incremental_state_append_and_oracle_seconds"] = _seconds(time.monotonic() - started)
    if not prefix_preserved or not restart_match or any(item.mismatch_count for item in oracle_reports):
        raise RuntimeError("incremental Phase 1b equivalence or Oracle gate failed")
    timings["total_before_audit_write_seconds"] = _seconds(time.monotonic() - total_started)
    validation = _incremental_validation_ledger(
        prior=prior,
        phase1a=phase1a,
        histories=histories,
        oracle_reports=tuple(oracle_reports),
        as_of_session=as_of_session,
        prefix_preserved=prefix_preserved,
        restart_match=restart_match,
    )
    return write_market_regime_state_audit(
        output_dir=output_dir,
        panel=None,
        phase1a_audit_manifest=phase1a.manifest,
        phase1a_input_manifest=phase1a.input_manifest,
        histories=histories,
        explanations=explanations,
        oracle_reports=tuple(oracle_reports),
        first_calculable_session=date.fromisoformat(str(prior.manifest["first_calculable_session"])),
        generated_at=datetime.now(UTC),
        timings=timings,
        peak_memory_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        incremental_validation=validation,
    )


def _validate_phase1a_audit(manifest: dict[str, object], session: date, universe_ids: tuple[str, ...]) -> None:
    if manifest.get("calculation_version") != PHASE1A_CALCULATION_VERSION:
        raise RuntimeError("Phase 1a calculation version mismatch")
    if manifest.get("parameter_set_fingerprint") != PHASE1A_PARAMETER_FINGERPRINT:
        raise RuntimeError("Phase 1a parameter fingerprint mismatch")
    if manifest.get("as_of_session") != session.isoformat() or tuple(manifest.get("universe_ids", ())) != universe_ids:
        raise RuntimeError("Phase 1a audit session or Universe order mismatch")
    if session == date(2026, 8, 21) and manifest.get("logical_content_fingerprint") != FROZEN_PHASE1A_AUDIT_FINGERPRINT:
        raise RuntimeError("frozen Phase 1a aggregate logical fingerprint mismatch")


def _validate_phase1a_contents(phase1a, session: date, universe_ids: tuple[str, ...]) -> None:
    composites = phase1a.composites
    if tuple(item.universe_id for item in composites) != universe_ids or any(
        item.as_of_session != session for item in composites
    ):
        raise RuntimeError("Phase 1a Composite session or Universe order mismatch")
    source = phase1a.input_manifest
    if source.get("as_of_session") != session.isoformat():
        raise RuntimeError("Phase 1a input manifest session mismatch")
    history_sessions = tuple(date.fromisoformat(item) for item in source.get("history_sessions", ()))
    if not history_sessions or history_sessions[-1] != session:
        raise RuntimeError("Phase 1a source history does not end at current session")
    source_universes = tuple(item.get("universe_id") for item in source.get("universes", ()))
    if source_universes != universe_ids:
        raise RuntimeError("Phase 1a source Universe order mismatch")
    source_memberships = {
        item["universe_id"]: item["membership_fingerprint"]
        for item in source.get("universes", ())
    }
    if any(
        item.membership_fingerprint != source_memberships.get(item.universe_id)
        or item.activation_pointer_fingerprint != source.get("activation_pointer_fingerprint")
        for item in composites
    ):
        raise RuntimeError("Phase 1a Composite source binding mismatch")


def _validate_incremental_prior(*, prior, phase1a, as_of_session, universe_ids) -> None:
    manifest = prior.manifest
    if manifest.get("calculation_version") != STATE_CALCULATION_VERSION:
        raise RuntimeError("prior Phase 1b audit is not the corrected stable-prefix calculation")
    if manifest.get("state_parameter_fingerprint") != STATE_PARAMETER_FINGERPRINT:
        raise RuntimeError("prior Phase 1b state parameter mismatch")
    prior_session = date.fromisoformat(str(manifest.get("as_of_session")))
    if ExchangeCalendar().previous_session(as_of_session) != prior_session:
        raise RuntimeError("prior Phase 1b audit is not the immediately preceding XNYS session")
    if tuple(manifest.get("universe_ids", ())) != universe_ids:
        raise RuntimeError("prior Phase 1b Universe order mismatch")
    if tuple(prior.histories) != universe_ids or tuple(prior.explanations) != universe_ids:
        raise RuntimeError("prior Phase 1b history is incomplete")
    for universe_id in universe_ids:
        rows = prior.histories[universe_id]
        explanations = prior.explanations[universe_id]
        if not rows or rows[-1].as_of_session != prior_session:
            raise RuntimeError("prior Phase 1b history does not end at prior as-of")
        if tuple(item.as_of_session for item in explanations) != tuple(
            item.as_of_session for item in rows
        ):
            raise RuntimeError("prior Phase 1b explanation prefix is incomplete")
    prior_source = prior.source_manifest
    current_source = phase1a.input_manifest
    if prior_source.get("activation_pointer_fingerprint") != current_source.get(
        "activation_pointer_fingerprint"
    ):
        raise RuntimeError("Phase 1b Activation changed; a cold replay is required")
    prior_memberships = {
        item["universe_id"]: item["membership_fingerprint"]
        for item in prior_source.get("universes", ())
    }
    current_memberships = {
        item["universe_id"]: item["membership_fingerprint"]
        for item in current_source.get("universes", ())
    }
    if prior_memberships != current_memberships:
        raise RuntimeError("Phase 1b Universe membership changed; a cold replay is required")


def _incremental_validation_ledger(
    *, prior, phase1a, histories, oracle_reports, as_of_session,
    prefix_preserved, restart_match,
):
    if prior.validation_ledger is None:
        segments = ({
            "scope": "verified_stable_prefix_cold_audit",
            "through_session": prior.manifest["as_of_session"],
            "audit_logical_fingerprint": prior.manifest["logical_content_fingerprint"],
            "oracle_fingerprints": prior.manifest["oracle_fingerprints"],
        },)
    else:
        segments = tuple(prior.validation_ledger.get("validation_segments", ()))
    segments = (*segments, {
        "scope": "current_session_independent_state_append_oracle",
        "session": as_of_session.isoformat(),
        "oracle_fingerprints": [item.oracle_history_fingerprint for item in oracle_reports],
        "oracle_mismatch_count": sum(item.mismatch_count for item in oracle_reports),
    })
    source_artifact = next(
        item for item in prior.manifest["artifacts"] if item["name"] == "source-input-manifest.json"
    )
    return {
        "validation_scope": "verified_prior_plus_current_session_oracle",
        "prior_audit_logical_fingerprint": prior.manifest["logical_content_fingerprint"],
        "prior_as_of_session": prior.manifest["as_of_session"],
        "current_as_of_session": as_of_session.isoformat(),
        "prior_history_logical_fingerprints": prior.manifest["history_logical_fingerprints"],
        "prior_explanation_records_fingerprint": _fingerprint([
            item.model_dump(mode="json")
            for universe_id in histories
            for item in prior.explanations[universe_id]
        ]),
        "prior_source_manifest_fingerprint": source_artifact["logical_content_fingerprint"],
        "current_phase1a_audit_logical_fingerprint": phase1a.manifest[
            "logical_content_fingerprint"
        ],
        "current_phase1a_composite_fingerprints": phase1a.manifest["composite_fingerprints"],
        "current_session_oracle_fingerprints": [
            item.oracle_history_fingerprint for item in oracle_reports
        ],
        "reuse_checks": {
            "prior_audit_formally_reread": True,
            "phase1a_audit_formally_reread": True,
            "immediate_xnys_successor": True,
            "calculation_and_parameters_compatible": True,
            "activation_unchanged": True,
            "membership_unchanged": True,
            "prior_state_prefix_preserved": prefix_preserved,
            "incremental_restart_match": restart_match,
        },
        "validation_segments": segments,
    }


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _equivalence_checks(*, composites, sessions, universe_id, full_records):
    split = max(1, len(sessions) // 2)
    prefix_records, _ = replay_regime_state_history(
        composites=composites[:split],
        expected_sessions=sessions[:split],
        universe_id=universe_id,
    )
    suffix_records, _ = append_regime_state_history(
        existing_history=prefix_records,
        composites=composites[split:],
        expected_sessions=sessions[split:],
        universe_id=universe_id,
    )
    append_match = tuple(item.logical_fingerprint for item in prefix_records + suffix_records) == tuple(
        item.logical_fingerprint for item in full_records
    )
    restart_split = min(len(sessions) - 1, split + 1)
    restart_prefix, _ = replay_regime_state_history(
        composites=composites[:restart_split],
        expected_sessions=sessions[:restart_split],
        universe_id=universe_id,
    )
    restart_suffix, _ = append_regime_state_history(
        existing_history=restart_prefix,
        composites=composites[restart_split:],
        expected_sessions=sessions[restart_split:],
        universe_id=universe_id,
    )
    restart_match = tuple(item.logical_fingerprint for item in restart_prefix + restart_suffix) == tuple(
        item.logical_fingerprint for item in full_records
    )
    permuted, _ = replay_regime_state_history(
        composites=tuple(reversed(composites)),
        expected_sessions=sessions,
        universe_id=universe_id,
    )
    permutation_match = state_history_fingerprint(permuted) == state_history_fingerprint(full_records)
    prefix_only, _ = replay_regime_state_history(
        composites=composites[:-1],
        expected_sessions=sessions[:-1],
        universe_id=universe_id,
    )
    future_prefix_stable = tuple(item.logical_fingerprint for item in prefix_only) == tuple(
        item.logical_fingerprint for item in full_records[:-1]
    )
    return {
        "append_full_replay_match": append_match,
        "restart_replay_match": restart_match,
        "input_permutation_match": permutation_match,
        "future_prefix_stable": future_prefix_stable,
    }


def _summary(manifest: dict[str, object], output_dir: Path) -> dict[str, object]:
    return {
        "status": "completed" if manifest.get("oracle_mismatch_count") == 0 else "oracle_mismatch",
        "as_of_session": manifest.get("as_of_session"),
        "universe_ids": manifest.get("universe_ids"),
        "output_dir": str(output_dir),
        "logical_content_fingerprint": manifest.get("logical_content_fingerprint"),
        "history_logical_fingerprints": manifest.get("history_logical_fingerprints"),
        "oracle_mismatch_count": manifest.get("oracle_mismatch_count"),
        "external_request_count": 0,
        "production_write_count": 0,
    }


def _seconds(value: float) -> str:
    return format(value, ".6f")


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during offline Market Regime state replay")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during offline Market Regime state replay")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during offline Market Regime state replay")

    socket.socket = GuardedSocket
    socket.create_connection = rejected
    socket.getaddrinfo = rejected
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create_connection
        socket.getaddrinfo = original_getaddrinfo


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
