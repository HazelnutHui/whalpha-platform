"""Offline, tmp-only Market Regime Phase 1b state replay CLI."""

from __future__ import annotations

import argparse
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
)
from tip_api.services.market_regime_audit import read_market_regime_audit
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
    write_market_regime_state_audit,
)
from tip_api.services.market_regime_state_oracle import compare_with_independent_state_oracle


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
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verify-output", action="store_true", help="Reread an existing completed state audit only.")
    args = parser.parse_args(argv)
    for name in ("data_root", "phase1a_audit", "output_dir"):
        if not getattr(args, name).is_absolute():
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


def _validate_phase1a_audit(manifest: dict[str, object], session: date, universe_ids: tuple[str, ...]) -> None:
    if manifest.get("calculation_version") != PHASE1A_CALCULATION_VERSION:
        raise RuntimeError("Phase 1a calculation version mismatch")
    if manifest.get("parameter_set_fingerprint") != PHASE1A_PARAMETER_FINGERPRINT:
        raise RuntimeError("Phase 1a parameter fingerprint mismatch")
    if manifest.get("as_of_session") != session.isoformat() or tuple(manifest.get("universe_ids", ())) != universe_ids:
        raise RuntimeError("Phase 1a audit session or Universe order mismatch")
    if session == date(2026, 8, 21) and manifest.get("logical_content_fingerprint") != FROZEN_PHASE1A_AUDIT_FINGERPRINT:
        raise RuntimeError("frozen Phase 1a aggregate logical fingerprint mismatch")


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
