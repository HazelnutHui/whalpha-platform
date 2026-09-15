"""Dell-only runner for the one registered replacement selection."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from tip_api.contracts.analytics.v1 import (
    strong_leader_pullback_replacement_selection_protocol_v1,
)
from tip_api.persistence.strong_leader_pullback_development_statistics import (
    read_strong_leader_pullback_development_statistics,
)
from tip_api.persistence.strong_leader_pullback_replacement_selection import (
    write_strong_leader_pullback_replacement_selection,
)
from tip_api.services.strong_leader_pullback_replacement_selection import (
    evaluate_strong_leader_pullback_replacement_selection,
)


class StrongLeaderPullbackReplacementSelectionCliError(RuntimeError):
    """Raised when the one-run replacement result cannot be retained safely."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the one registered Strong-Leader Pullback replacement."
    )
    for name in (
        "development-statistics-root",
        "development-statistics-custody-root",
        "output-root",
        "output-custody-root",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--created-at", type=_datetime, required=True)
    parser.add_argument("--implementation-revision", required=True)
    args = parser.parse_args(argv)
    try:
        result = build_strong_leader_pullback_replacement_selection(**vars(args))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "replacement_selection_rejected",
                    "error_type": type(exc).__name__,
                    "error_detail": _safe_error_detail(exc),
                    "network_request_count": 0,
                    "canonical_data_write_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    report = result.report
    print(
        json.dumps(
            {
                "status": result.status,
                "output_root": str(result.root),
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "selection_status": report.selection_status.value,
                "common_eligible_parameter_count": (
                    report.common_eligible_parameter_count
                ),
                "provisional_winner_id": report.provisional_winner_id,
                "selected_parameter_combination_id": (
                    report.selected_parameter_combination_id
                ),
                "gate_passes": {
                    item.gate_id: item.passed for item in report.gate_results
                },
                "validation_transition_authorized": (
                    report.validation_transition_authorized
                ),
                "holdout_data_accessed": report.holdout_data_accessed,
                "performance_claim_authorized": report.performance_claim_authorized,
                "candidate_activation_authorized": (
                    report.candidate_activation_authorized
                ),
                "publication_authorized": report.publication_authorized,
                "network_request_count": report.network_request_count,
                "canonical_data_write_count": report.canonical_data_write_count,
                "production_write_count": report.production_write_count,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def build_strong_leader_pullback_replacement_selection(
    *,
    development_statistics_root: Path,
    development_statistics_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    created_at: datetime,
    implementation_revision: str,
):
    with _network_disabled():
        source = read_strong_leader_pullback_development_statistics(
            output_root=development_statistics_root,
            output_custody_root=development_statistics_custody_root,
        )
        report = evaluate_strong_leader_pullback_replacement_selection(
            source_report=source.report,
            source_report_sha256=source.report_sha256,
            protocol=strong_leader_pullback_replacement_selection_protocol_v1(),
            implementation_revision=implementation_revision,
            created_at=created_at,
        )
        return write_strong_leader_pullback_replacement_selection(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def _safe_error_detail(exc: Exception) -> object:
    if hasattr(exc, "errors"):
        return tuple(
            {
                "location": ".".join(str(item) for item in error.get("loc", ())),
                "type": str(error.get("type", "unknown")),
                "message": str(error.get("msg", "validation failed")),
            }
            for error in exc.errors(include_url=False, include_input=False)[:10]
        )
    return str(exc)[:500]


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("created-at must be timezone-aware")
    return parsed.astimezone(UTC)


@contextmanager
def _network_disabled() -> Iterator[None]:
    original_socket = socket.socket

    def blocked_socket(*_args: object, **_kwargs: object):
        raise RuntimeError("network access is disabled for replacement selection")

    socket.socket = blocked_socket  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
