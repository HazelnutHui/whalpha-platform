"""Dell-only runner for bounded Strong-Leader Pullback development statistics."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from tip_api.persistence.strong_leader_pullback_development_dataset import (
    read_strong_leader_pullback_development_dataset,
)
from tip_api.persistence.strong_leader_pullback_development_statistics import (
    write_strong_leader_pullback_development_statistics,
)
from tip_api.services.strong_leader_pullback_development_statistics import (
    evaluate_strong_leader_pullback_development_statistics,
)


class StrongLeaderPullbackDevelopmentStatisticsCliError(RuntimeError):
    """Raised when the private development report cannot be built safely."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build one immutable Strong-Leader Pullback development report."
    )
    for name in (
        "development-dataset-root",
        "development-dataset-custody-root",
        "output-root",
        "output-custody-root",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--created-at", type=_datetime, required=True)
    parser.add_argument("--implementation-revision", required=True)
    args = parser.parse_args(argv)
    try:
        result = build_strong_leader_pullback_development_statistics(**vars(args))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "development_statistics_rejected",
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
                "selected_parameter_combination_id": (
                    report.selected_parameter_combination_id
                ),
                "parameter_combination_count": report.parameter_combination_count,
                "summary_count": report.summary_count,
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


def build_strong_leader_pullback_development_statistics(
    *,
    development_dataset_root: Path,
    development_dataset_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    created_at: datetime,
    implementation_revision: str,
):
    with _network_disabled():
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise StrongLeaderPullbackDevelopmentStatisticsCliError(
                "development report creation time must be timezone-aware"
            )
        if len(implementation_revision) != 40 or any(
            character not in "0123456789abcdef"
            for character in implementation_revision
        ):
            raise StrongLeaderPullbackDevelopmentStatisticsCliError(
                "implementation revision must be one exact Git commit"
            )
        source = read_strong_leader_pullback_development_dataset(
            output_root=development_dataset_root,
            output_custody_root=development_dataset_custody_root,
        )
        if (
            source.manifest.validation_observation_count
            or source.manifest.validation_label_count
            or source.manifest.holdout_observation_count
            or source.manifest.holdout_label_count
            or not source.manifest.development_only
        ):
            raise StrongLeaderPullbackDevelopmentStatisticsCliError(
                "source dataset crosses the development-only boundary"
            )
        report = evaluate_strong_leader_pullback_development_statistics(
            observations=source.observations,
            labels=source.labels,
            source_dataset_manifest_sha256=source.manifest_sha256,
            source_dataset_logical_fingerprint=source.manifest.logical_fingerprint,
            implementation_revision=implementation_revision,
            created_at=created_at.astimezone(UTC),
        )
        return write_strong_leader_pullback_development_statistics(
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
        raise RuntimeError("network access is disabled for development statistics")

    socket.socket = blocked_socket  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
