"""Offline, socket-guarded Candidate entry-geometry shadow CLI."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.contracts.analytics.v1 import OpportunityCandidateBatchV1, OpportunityCandidateStateRecordV1
from tip_api.services.candidate_entry_geometry import calculate_candidate_entry_geometry
from tip_api.services.candidate_entry_geometry_audit import (
    read_candidate_entry_geometry_audit,
    validate_entry_geometry_tmp_output_dir,
    write_candidate_entry_geometry_audit,
)
from tip_api.services.candidate_entry_geometry_oracle import (
    compare_with_independent_entry_geometry_oracle,
)
from tip_api.services.market_regime_sources import load_formal_market_regime_panel
from tip_api.services.opportunity_candidate_audit import read_opportunity_candidate_audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calculate Candidate entry geometry into a shadow-only /tmp audit.")
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--candidate-audit", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verify-output", action="store_true")
    args = parser.parse_args(argv)
    for name in ("data_root", "candidate_audit", "output_dir"):
        if not getattr(args, name).is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    if args.verify_output:
        manifest = read_candidate_entry_geometry_audit(args.output_dir)
        print(json.dumps(_summary(manifest, args.output_dir), sort_keys=True, separators=(",", ":")))
        return 0
    validate_entry_geometry_tmp_output_dir(args.output_dir)
    with _offline_socket_guard():
        source_manifest = read_opportunity_candidate_audit(args.candidate_audit)
        if source_manifest.get("as_of_session") != args.as_of_session.isoformat():
            raise RuntimeError("Candidate audit and requested entry-geometry session differ")
        score_rows = _read_records(args.candidate_audit / "candidate-score-history.json")
        state_rows = _read_records(args.candidate_audit / "candidate-state-history.json")
        batches = tuple(
            OpportunityCandidateBatchV1.model_validate(item)
            for item in score_rows
            if item.get("as_of_session") == args.as_of_session.isoformat()
        )
        universe_ids = tuple(source_manifest["universe_ids"])
        if tuple(item.universe_id for item in batches) != universe_ids:
            raise RuntimeError("current Candidate batches are not complete and Primary-first")
        states = tuple(
            OpportunityCandidateStateRecordV1.model_validate(item)
            for item in state_rows
            if item.get("as_of_session") == args.as_of_session.isoformat()
        )
        panel = load_formal_market_regime_panel(data_root=args.data_root, as_of_session=args.as_of_session)
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
        manifest = write_candidate_entry_geometry_audit(
            output_dir=args.output_dir,
            candidate_audit_dir=args.candidate_audit,
            candidate_audit_manifest=source_manifest,
            batches=tuple(output_batches),
            oracle_reports=tuple(oracle_reports),
            generated_at=datetime.now(UTC),
        )
    print(json.dumps(_summary(manifest, args.output_dir), sort_keys=True, separators=(",", ":")))
    return 0


def _read_records(path: Path) -> list[dict]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Candidate audit record source is unsafe")
    payload = json.loads(path.read_bytes())
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise RuntimeError("Candidate audit record payload is malformed")
    return records


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
