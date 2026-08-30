"""Offline, tmp-only Market Regime Phase 1a administrator CLI."""

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
from tip_api.services.market_regime import calculate_market_regime
from tip_api.services.market_regime_audit import (
    read_market_regime_audit,
    validate_tmp_output_dir,
    write_market_regime_audit,
)
from tip_api.services.market_regime_oracle import compare_with_independent_oracle
from tip_api.services.market_regime_panel_cache import write_market_regime_panel_cache
from tip_api.services.market_regime_sources import load_formal_market_regime_panel
from tip_api.services.sector_etf_rotation import calculate_sector_etf_rotation
from tip_api.services.sector_etf_rotation_audit import (
    read_sector_etf_rotation_audit,
    validate_sector_etf_rotation_audit_output,
    write_sector_etf_rotation_audit,
)
from tip_api.services.sector_etf_rotation_oracle import (
    compare_with_independent_sector_rotation_oracle,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate Market Regime V1 Phase 1a and Sector ETF Rotation "
            "offline from one panel, then write canonical /tmp audit ledgers."
        )
    )
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--universe-id",
        action="append",
        required=True,
        choices=PUBLIC_UNIVERSE_ORDER,
        help="Repeat to calculate both public Universes in fixed catalog order.",
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--sector-rotation-output-dir",
        required=True,
        type=Path,
        help="Distinct direct-child /tmp audit written from the same in-memory panel.",
    )
    parser.add_argument(
        "--panel-cache-root",
        type=Path,
        help="Optional owner-controlled Dell-local content-addressed panel cache.",
    )
    parser.add_argument("--verify-output", action="store_true", help="Reread an existing completed audit only.")
    args = parser.parse_args(argv)
    if not args.data_root.is_absolute():
        parser.error("--data-root must be absolute")
    if not args.output_dir.is_absolute():
        parser.error("--output-dir must be absolute")
    if not args.sector_rotation_output_dir.is_absolute():
        parser.error("--sector-rotation-output-dir must be absolute")
    if args.sector_rotation_output_dir == args.output_dir:
        parser.error("Phase 1a and Sector Rotation outputs must be distinct")
    if args.panel_cache_root is not None and not args.panel_cache_root.is_absolute():
        parser.error("--panel-cache-root must be absolute")
    if tuple(args.universe_id) != tuple(dict.fromkeys(args.universe_id)):
        parser.error("duplicate --universe-id is not allowed")
    ordered = tuple(item for item in PUBLIC_UNIVERSE_ORDER if item in args.universe_id)
    if tuple(args.universe_id) != ordered:
        parser.error("--universe-id values must use Primary-first catalog order")
    if args.verify_output:
        manifest = read_market_regime_audit(args.output_dir)
        sector_manifest = read_sector_etf_rotation_audit(
            args.sector_rotation_output_dir
        )
        print(
            json.dumps(
                _summary(
                    manifest,
                    args.output_dir,
                    sector_manifest=sector_manifest,
                    sector_output_dir=args.sector_rotation_output_dir,
                ),
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0

    validate_tmp_output_dir(args.output_dir)
    validate_sector_etf_rotation_audit_output(args.sector_rotation_output_dir)
    started = time.monotonic()
    with _offline_socket_guard():
        panel = load_formal_market_regime_panel(data_root=args.data_root, as_of_session=args.as_of_session)
        cache_manifest = None
        if args.panel_cache_root is not None:
            cache_manifest = write_market_regime_panel_cache(
                cache_root=args.panel_cache_root,
                panel=panel,
            )
        composites = []
        explanations = []
        oracle_reports = []
        for universe_id in ordered:
            composite, entries = calculate_market_regime(panel=panel, universe_id=universe_id)
            oracle = compare_with_independent_oracle(panel=panel, result=composite)
            composites.append(composite)
            explanations.extend(entries)
            oracle_reports.append(oracle)
        elapsed = format(DecimalTime(time.monotonic() - started), ".6f")
        manifest = write_market_regime_audit(
            output_dir=args.output_dir,
            panel=panel,
            composites=tuple(composites),
            explanations=tuple(explanations),
            oracle_reports=tuple(oracle_reports),
            generated_at=datetime.now(UTC),
            elapsed_seconds=elapsed,
            peak_memory_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        )
        sector_calculation_started = time.monotonic()
        sector_product = calculate_sector_etf_rotation(panel=panel)
        sector_calculation_seconds = format(
            DecimalTime(time.monotonic() - sector_calculation_started), ".6f"
        )
        sector_oracle_started = time.monotonic()
        sector_oracle = compare_with_independent_sector_rotation_oracle(
            panel=panel,
            product=sector_product,
        )
        sector_oracle_seconds = format(
            DecimalTime(time.monotonic() - sector_oracle_started), ".6f"
        )
        sector_manifest = write_sector_etf_rotation_audit(
            output_dir=args.sector_rotation_output_dir,
            phase1a_audit_dir=args.output_dir,
            panel=panel,
            product=sector_product,
            oracle_report=sector_oracle,
            generated_at=datetime.now(UTC),
            timings={
                "calculation_seconds": sector_calculation_seconds,
                "oracle_seconds": sector_oracle_seconds,
            },
        )
    summary = _summary(
        manifest,
        args.output_dir,
        sector_manifest=sector_manifest,
        sector_output_dir=args.sector_rotation_output_dir,
    )
    if cache_manifest is not None:
        summary["panel_cache_key"] = cache_manifest["cache_key"]
        summary["panel_cache_logical_fingerprint"] = cache_manifest[
            "logical_content_fingerprint"
        ]
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 1 if manifest["oracle_mismatch_count"] else 0


class DecimalTime(float):
    """Formatting marker; runtime is physical audit metadata, never fingerprint input."""


def _summary(
    manifest: dict[str, object],
    output_dir: Path,
    *,
    sector_manifest: dict[str, object],
    sector_output_dir: Path,
) -> dict[str, object]:
    return {
        "status": "completed" if manifest.get("oracle_mismatch_count") == 0 else "oracle_mismatch",
        "as_of_session": manifest.get("as_of_session"),
        "universe_ids": manifest.get("universe_ids"),
        "output_dir": str(output_dir),
        "logical_content_fingerprint": manifest.get("logical_content_fingerprint"),
        "composite_fingerprints": manifest.get("composite_fingerprints"),
        "oracle_mismatch_count": manifest.get("oracle_mismatch_count"),
        "sector_rotation_output_dir": str(sector_output_dir),
        "sector_rotation_logical_fingerprint": sector_manifest.get(
            "logical_content_fingerprint"
        ),
        "sector_rotation_product_fingerprint": sector_manifest.get(
            "product_logical_fingerprint"
        ),
        "sector_rotation_oracle_mismatch_count": sector_manifest.get(
            "oracle_mismatch_count"
        ),
        "source_panel_load_count": 1,
        "external_request_count": 0,
        "production_write_count": 0,
    }


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during offline Market Regime calculation")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during offline Market Regime calculation")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during offline Market Regime calculation")

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
