"""Offline, socket-guarded Candidate entry-geometry shadow CLI."""

from __future__ import annotations

import argparse
import json
import resource
import socket
import time
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.services.candidate_entry_geometry import calculate_candidate_entry_geometry
from tip_api.services.candidate_entry_geometry_audit import (
    read_candidate_entry_geometry_audit,
    validate_entry_geometry_tmp_output_dir,
    write_candidate_entry_geometry_audit,
)
from tip_api.services.candidate_entry_geometry_oracle import (
    compare_with_independent_entry_geometry_oracle,
)
from tip_api.services.market_regime_panel_cache import (
    MarketRegimePanelCacheError,
    load_market_regime_panel_with_cache,
)
from tip_api.services.opportunity_candidate_audit import (
    read_opportunity_candidate_current_batches,
    read_opportunity_candidate_state_history,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calculate Candidate entry geometry into a shadow-only /tmp audit.")
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--candidate-audit", required=True, type=Path)
    parser.add_argument("--panel-cache-root", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verify-output", action="store_true")
    args = parser.parse_args(argv)
    for name in (
        "data_root",
        "candidate_audit",
        "panel_cache_root",
        "output_dir",
    ):
        value = getattr(args, name)
        if value is not None and not value.is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    if args.verify_output:
        manifest = read_candidate_entry_geometry_audit(args.output_dir)
        print(json.dumps(_summary(manifest, args.output_dir), sort_keys=True, separators=(",", ":")))
        return 0
    validate_entry_geometry_tmp_output_dir(args.output_dir)
    started = time.perf_counter()
    timings: dict[str, float] = {}
    with _offline_socket_guard():
        stage = time.perf_counter()
        candidate_evidence = read_opportunity_candidate_current_batches(
            args.candidate_audit,
            as_of_session=args.as_of_session,
        )
        states = read_opportunity_candidate_state_history(args.candidate_audit)
        source_manifest = candidate_evidence.manifest
        timings["candidate_and_state_reread_seconds"] = time.perf_counter() - stage
        if source_manifest.get("as_of_session") != args.as_of_session.isoformat():
            raise RuntimeError("Candidate audit and requested entry-geometry session differ")
        batches = candidate_evidence.candidate_batches
        universe_ids = tuple(source_manifest["universe_ids"])
        if tuple(item.universe_id for item in batches) != universe_ids:
            raise RuntimeError("current Candidate batches are not complete and Primary-first")
        states = tuple(
            item for item in states if item.as_of_session == args.as_of_session
        )
        stage = time.perf_counter()
        try:
            panel, cache_status, cache_fingerprint = (
                load_market_regime_panel_with_cache(
                    data_root=args.data_root,
                    as_of_session=args.as_of_session,
                    cache_root=args.panel_cache_root,
                    expected_source=candidate_evidence.source_panel,
                )
            )
        except MarketRegimePanelCacheError as exc:
            raise RuntimeError(
                "entry-geometry panel cache failed formal validation"
            ) from exc
        timings["panel_load_seconds"] = time.perf_counter() - stage
        stage = time.perf_counter()
        output_batches = []
        oracle_reports = []
        for batch in batches:
            universe_states = tuple(item for item in states if item.universe_id == batch.universe_id)
            result = calculate_candidate_entry_geometry(
                panel=panel,
                candidate_batch=batch,
                state_records=universe_states,
            )
            oracle = compare_with_independent_entry_geometry_oracle(
                panel=panel,
                candidate_batch=batch,
                state_records=universe_states,
                actual=result,
            )
            if oracle.mismatch_count or not oracle.input_permutation_match:
                raise RuntimeError("entry-geometry Oracle or permutation gate failed")
            output_batches.append(result)
            oracle_reports.append(oracle)
        timings["calculation_and_oracle_seconds"] = time.perf_counter() - stage
        stage = time.perf_counter()
        manifest = write_candidate_entry_geometry_audit(
            output_dir=args.output_dir,
            candidate_audit_dir=args.candidate_audit,
            candidate_audit_manifest=source_manifest,
            batches=tuple(output_batches),
            oracle_reports=tuple(oracle_reports),
            generated_at=datetime.now(UTC),
        )
        timings["audit_write_and_reread_seconds"] = time.perf_counter() - stage
    timings["total_seconds"] = time.perf_counter() - started
    print(
        json.dumps(
            {
                **_summary(manifest, args.output_dir),
                "panel_cache_status": cache_status,
                "panel_cache_logical_fingerprint": cache_fingerprint,
                "timings": timings,
                "peak_memory_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def _summary(manifest, output_dir):
    return {
        "status": "completed" if manifest.get("oracle_mismatch_count") == 0 else "oracle_mismatch",
        "as_of_session": manifest.get("as_of_session"),
        "universe_ids": manifest.get("universe_ids"),
        "output_dir": str(output_dir),
        "logical_content_fingerprint": manifest.get("logical_content_fingerprint"),
        "oracle_mismatch_count": manifest.get("oracle_mismatch_count"),
        "input_permutation_match": manifest.get("input_permutation_match"),
        "shadow_only": manifest.get("shadow_only"),
        "external_request_count": 0,
        "production_write_count": 0,
    }


@contextmanager
def _offline_socket_guard():
    original_socket, original_create, original_getaddrinfo = socket.socket, socket.create_connection, socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during entry-geometry audit")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during entry-geometry audit")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during entry-geometry audit")

    socket.socket, socket.create_connection, socket.getaddrinfo = GuardedSocket, rejected, rejected
    try:
        yield
    finally:
        socket.socket, socket.create_connection, socket.getaddrinfo = original_socket, original_create, original_getaddrinfo


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
