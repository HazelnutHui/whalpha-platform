"""Offline CLI for the Candidate strategy-channel shadow audit."""

from __future__ import annotations

import argparse
import json
import resource
import socket
import time
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.contracts.analytics.v1 import CandidateEntryGeometryBatchV1
from tip_api.services.candidate_entry_geometry_audit import (
    read_candidate_entry_geometry_audit,
)
from tip_api.services.candidate_strategy_channel_audit import (
    read_candidate_strategy_channel_audit,
    validate_strategy_channel_tmp_output_dir,
    write_candidate_strategy_channel_audit,
)
from tip_api.services.candidate_strategy_channels import (
    build_candidate_strategy_channel_consumer,
    calculate_candidate_strategy_channels,
)
from tip_api.services.candidate_strategy_channels_oracle import (
    compare_with_independent_strategy_channel_oracle,
)
from tip_api.services.opportunity_candidate_audit import (
    read_opportunity_candidate_current_batches,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a shadow-only Candidate strategy-channel audit in /tmp."
    )
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument("--candidate-audit", required=True, type=Path)
    parser.add_argument("--entry-geometry-audit", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verify-output", action="store_true")
    args = parser.parse_args(argv)
    for name in ("candidate_audit", "entry_geometry_audit", "output_dir"):
        if not getattr(args, name).is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    if args.verify_output:
        manifest = read_candidate_strategy_channel_audit(args.output_dir)
        print(
            json.dumps(
                _summary(manifest, args.output_dir),
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0

    validate_strategy_channel_tmp_output_dir(args.output_dir)
    started = time.perf_counter()
    timings: dict[str, float] = {}
    with _offline_socket_guard():
        stage = time.perf_counter()
        candidate_evidence = read_opportunity_candidate_current_batches(
            args.candidate_audit,
            as_of_session=args.as_of_session,
        )
        timings["candidate_current_projection_seconds"] = (
            time.perf_counter() - stage
        )
        stage = time.perf_counter()
        entry_manifest = read_candidate_entry_geometry_audit(
            args.entry_geometry_audit
        )
        candidate_batches = candidate_evidence.candidate_batches
        entry_batches = tuple(
            CandidateEntryGeometryBatchV1.model_validate(row)
            for row in _read_records(
                args.entry_geometry_audit / "entry-geometry-batches.json"
            )
            if row.get("as_of_session") == args.as_of_session.isoformat()
        )
        timings["entry_geometry_reread_seconds"] = time.perf_counter() - stage
        universe_ids = tuple(candidate_evidence.manifest["universe_ids"])
        if (
            tuple(row.universe_id for row in candidate_batches) != universe_ids
            or tuple(row.universe_id for row in entry_batches) != universe_ids
        ):
            raise RuntimeError(
                "strategy audit current source batches are not complete and Primary-first"
            )
        stage = time.perf_counter()
        output_batches, consumers, oracles = [], [], []
        for candidate_batch, entry_batch in zip(
            candidate_batches, entry_batches, strict=True
        ):
            result = calculate_candidate_strategy_channels(
                candidate_batch=candidate_batch,
                entry_geometry_batch=entry_batch,
            )
            oracle = compare_with_independent_strategy_channel_oracle(
                candidate_batch=candidate_batch,
                entry_geometry_batch=entry_batch,
                actual=result,
            )
            if oracle.mismatch_count or not oracle.input_permutation_match:
                raise RuntimeError("strategy-channel Oracle or permutation gate failed")
            output_batches.append(result)
            consumers.append(build_candidate_strategy_channel_consumer(result))
            oracles.append(oracle)
        timings["calculation_and_oracle_seconds"] = time.perf_counter() - stage
        stage = time.perf_counter()
        manifest = write_candidate_strategy_channel_audit(
            output_dir=args.output_dir,
            candidate_audit_dir=args.candidate_audit,
            candidate_audit_manifest=candidate_evidence.manifest,
            entry_geometry_audit_dir=args.entry_geometry_audit,
            entry_geometry_audit_manifest=entry_manifest,
            batches=tuple(output_batches),
            consumers=tuple(consumers),
            oracle_reports=tuple(oracles),
            generated_at=datetime.now(UTC),
        )
        timings["audit_write_and_reread_seconds"] = time.perf_counter() - stage
    timings["total_seconds"] = time.perf_counter() - started
    print(
        json.dumps(
            {
                **_summary(manifest, args.output_dir),
                "timings": timings,
                "peak_memory_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def _read_records(path: Path) -> list[dict]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("strategy source record artifact is unsafe")
    payload = json.loads(path.read_bytes())
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not all(
        isinstance(item, dict) for item in records
    ):
        raise RuntimeError("strategy source record payload is malformed")
    return records


def _summary(manifest, output_dir):
    return {
        "status": (
            "completed"
            if manifest.get("oracle_mismatch_count") == 0
            else "oracle_mismatch"
        ),
        "as_of_session": manifest.get("as_of_session"),
        "universe_ids": manifest.get("universe_ids"),
        "output_dir": str(output_dir),
        "logical_content_fingerprint": manifest.get("logical_content_fingerprint"),
        "batch_fingerprints": manifest.get("batch_fingerprints"),
        "consumer_fingerprints": manifest.get("consumer_fingerprints"),
        "oracle_fingerprints": manifest.get("oracle_fingerprints"),
        "oracle_mismatch_count": manifest.get("oracle_mismatch_count"),
        "input_permutation_match": manifest.get("input_permutation_match"),
        "shadow_only": manifest.get("shadow_only"),
        "external_request_count": manifest.get("external_request_count"),
        "production_write_count": manifest.get("production_write_count"),
    }


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during strategy audit")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during strategy audit")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during strategy audit")

    socket.socket = GuardedSocket
    socket.create_connection = rejected
    socket.getaddrinfo = rejected
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create
        socket.getaddrinfo = original_getaddrinfo


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
