"""Dell-only builder for the reconstructed Strong-Leader Pullback development dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
from collections import defaultdict
from contextlib import contextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterator

from tip_api.contracts.analytics.v1 import (
    CandidateStrategyChronologicalPlanV1,
    StrategyEvaluationSplit,
    StrongLeaderPullbackObservationV1,
    StrongLeaderPullbackTerminalReferenceLedgerEntryV1,
)
from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import AdjustmentAvailabilityStatus
from tip_api.persistence.parquet.canonical_split_adjustment import (
    read_canonical_split_adjustment_publication,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.strong_leader_pullback_development_dataset import (
    write_strong_leader_pullback_development_dataset,
)
from tip_api.persistence.strong_leader_pullback_diagnostics import (
    REPORT_FILE as DIAGNOSTICS_FILE,
    read_strong_leader_pullback_diagnostics,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.strong_leader_pullback_development_labels import (
    ReconstructedOutcomeBarV1,
    build_reconstructed_development_label,
)
from tip_api.services.strong_leader_pullback_diagnostics_cli import (
    load_strong_leader_pullback_reconstructed_population,
)
from tip_api.services.strong_leader_pullback_fixed_cash_terminal_evidence import (
    read_strong_leader_pullback_fixed_cash_terminal_evidence,
)
from tip_api.services.strong_leader_pullback_listed_consideration_residual_terminal_evidence import (
    read_strong_leader_pullback_listed_consideration_residual_terminal_evidence,
)
from tip_api.services.strong_leader_pullback_listed_consideration_terminal_evidence import (
    read_strong_leader_pullback_listed_consideration_terminal_evidence,
)
from tip_api.services.strong_leader_pullback_research_admission_v2 import (
    ResearchAdmissionV2Status,
)
from tip_api.services.strong_leader_pullback_research_admission_v2_review import (
    read_strong_leader_pullback_research_admission_v2_review,
)
from tip_api.services.strong_leader_pullback_terminal_boundary_census import (
    read_strong_leader_pullback_terminal_boundary_census,
)
from tip_api.services.strong_leader_pullback_terminal_gap_census_v3 import (
    read_strong_leader_pullback_terminal_gap_census_v3,
)
from tip_api.services.strong_leader_pullback_terminal_gap_census_v4 import (
    read_strong_leader_pullback_terminal_gap_census_v4,
)
from tip_api.services.strong_leader_pullback_terminal_population_listed_reference import (
    read_strong_leader_pullback_terminal_population_listed_reference,
)
from tip_api.services.strong_leader_pullback_terminal_reference_final_review import (
    read_strong_leader_pullback_terminal_reference_final_review,
)
from tip_api.services.strong_leader_pullback_terminal_reference_ledger import (
    build_strong_leader_pullback_terminal_reference_ledger,
)


class StrongLeaderPullbackDevelopmentDatasetCliError(RuntimeError):
    """Raised when the real development dataset cannot be built safely."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build one immutable reconstructed development dataset on Dell."
    )
    for name in (
        "data-root",
        "membership-shadow-root",
        "development-census-root",
        "split-action-publication-root",
        "split-adjustment-publication-root",
        "method-launch-root",
        "method-launch-custody-root",
        "diagnostics-root",
        "diagnostics-custody-root",
        "admission-root",
        "admission-custody-root",
        "terminal-boundary-root",
        "terminal-boundary-custody-root",
        "terminal-gap-v3-root",
        "terminal-gap-v3-custody-root",
        "fixed-cash-root",
        "fixed-cash-custody-root",
        "listed-consideration-root",
        "listed-consideration-custody-root",
        "residual-listed-consideration-root",
        "residual-listed-consideration-custody-root",
        "terminal-population-listed-reference-root",
        "terminal-population-listed-reference-custody-root",
        "terminal-gap-v4-root",
        "terminal-gap-v4-custody-root",
        "final-terminal-root",
        "final-terminal-custody-root",
        "output-root",
        "output-custody-root",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--created-at", type=_datetime, required=True)
    parser.add_argument("--implementation-revision", required=True)
    args = parser.parse_args(argv)
    try:
        result = build_strong_leader_pullback_development_dataset(
            **vars(args)
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "reconstructed_development_dataset_rejected",
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
    print(
        json.dumps(
            {
                "status": result.status,
                "output_root": str(result.root),
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": result.manifest.logical_fingerprint,
                "development_signal_session_count": (
                    result.manifest.development_signal_session_count
                ),
                "observation_count": result.manifest.observation_count,
                "label_count": result.manifest.label_count,
                "label_state_counts": result.manifest.label_state_counts,
                "network_request_count": 0,
                "canonical_data_write_count": 0,
                "production_write_count": 0,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def build_strong_leader_pullback_development_dataset(
    *,
    data_root: Path,
    membership_shadow_root: Path,
    development_census_root: Path,
    split_action_publication_root: Path,
    split_adjustment_publication_root: Path,
    method_launch_root: Path,
    method_launch_custody_root: Path,
    diagnostics_root: Path,
    diagnostics_custody_root: Path,
    admission_root: Path,
    admission_custody_root: Path,
    terminal_boundary_root: Path,
    terminal_boundary_custody_root: Path,
    terminal_gap_v3_root: Path,
    terminal_gap_v3_custody_root: Path,
    fixed_cash_root: Path,
    fixed_cash_custody_root: Path,
    listed_consideration_root: Path,
    listed_consideration_custody_root: Path,
    residual_listed_consideration_root: Path,
    residual_listed_consideration_custody_root: Path,
    terminal_population_listed_reference_root: Path,
    terminal_population_listed_reference_custody_root: Path,
    terminal_gap_v4_root: Path,
    terminal_gap_v4_custody_root: Path,
    final_terminal_root: Path,
    final_terminal_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    created_at: datetime,
    implementation_revision: str,
):
    with _network_disabled():
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise StrongLeaderPullbackDevelopmentDatasetCliError(
                "dataset creation time must be timezone-aware"
            )
        if len(implementation_revision) != 40 or any(
            character not in "0123456789abcdef"
            for character in implementation_revision
        ):
            raise StrongLeaderPullbackDevelopmentDatasetCliError(
                "implementation revision must be one exact Git commit"
            )
        admission = read_strong_leader_pullback_research_admission_v2_review(
            output_root=admission_root,
            output_custody_root=admission_custody_root,
        )
        decision = admission.report.decision
        if (
            decision.status
            is not ResearchAdmissionV2Status.READY_FOR_RECONSTRUCTED_DEVELOPMENT
            or not decision.development_label_construction_authorized
            or not decision.development_parameter_selection_authorized
            or decision.validation_authorized
            or decision.holdout_access_authorized
            or decision.performance_claim_authorized
        ):
            raise StrongLeaderPullbackDevelopmentDatasetCliError(
                "reconstructed development admission is not open"
            )
        retained_diagnostics = read_strong_leader_pullback_diagnostics(
            output_root=diagnostics_root,
            output_custody_root=diagnostics_custody_root,
        )
        population = load_strong_leader_pullback_reconstructed_population(
            data_root=data_root,
            membership_shadow_root=membership_shadow_root,
            development_census_root=development_census_root,
            split_action_publication_root=split_action_publication_root,
            split_adjustment_publication_root=split_adjustment_publication_root,
            method_launch_root=method_launch_root,
            method_launch_custody_root=method_launch_custody_root,
        )
        if (
            population.report != retained_diagnostics
            or population.report.logical_fingerprint
            != admission.report.diagnostics_logical_fingerprint
            or _file_sha256(diagnostics_root / DIAGNOSTICS_FILE)
            != admission.report.diagnostics_report_sha256
        ):
            raise StrongLeaderPullbackDevelopmentDatasetCliError(
                "reproduced feature population differs from admitted diagnostics"
            )
        terminal_references = _read_terminal_references(
            terminal_boundary_root=terminal_boundary_root,
            terminal_boundary_custody_root=terminal_boundary_custody_root,
            terminal_gap_v3_root=terminal_gap_v3_root,
            terminal_gap_v3_custody_root=terminal_gap_v3_custody_root,
            fixed_cash_root=fixed_cash_root,
            fixed_cash_custody_root=fixed_cash_custody_root,
            listed_consideration_root=listed_consideration_root,
            listed_consideration_custody_root=listed_consideration_custody_root,
            residual_listed_consideration_root=residual_listed_consideration_root,
            residual_listed_consideration_custody_root=(
                residual_listed_consideration_custody_root
            ),
            terminal_population_listed_reference_root=(
                terminal_population_listed_reference_root
            ),
            terminal_population_listed_reference_custody_root=(
                terminal_population_listed_reference_custody_root
            ),
            terminal_gap_v4_root=terminal_gap_v4_root,
            terminal_gap_v4_custody_root=terminal_gap_v4_custody_root,
            final_terminal_root=final_terminal_root,
            final_terminal_custody_root=final_terminal_custody_root,
        )
        final_terminal = read_strong_leader_pullback_terminal_reference_final_review(
            output_root=final_terminal_root,
            output_custody_root=final_terminal_custody_root,
        )
        if (
            final_terminal.report_sha256 != admission.report.final_terminal_report_sha256
            or final_terminal.report.logical_fingerprint
            != admission.report.final_terminal_logical_fingerprint
        ):
            raise StrongLeaderPullbackDevelopmentDatasetCliError(
                "terminal ledger differs from admitted terminal evidence"
            )
        assignments = {item.session: item for item in population.plan.assignments}
        observations = tuple(
            item
            for item in population.observations
            if assignments[item.as_of_session].raw_split
            is StrategyEvaluationSplit.DEVELOPMENT
            and assignments[item.as_of_session].usable_for_signal_evaluation
        )
        if not observations:
            raise StrongLeaderPullbackDevelopmentDatasetCliError(
                "development observation population is empty"
            )
        labels = _build_labels(
            data_root=data_root,
            split_adjustment_publication_root=split_adjustment_publication_root,
            observations=observations,
            plan=population.plan,
            terminal_references=terminal_references,
            source_adjustment_fingerprint=population.source_adjustment_fingerprint,
            split_basis_session=population.split_basis_session,
        )
        sessions = tuple(sorted({item.as_of_session for item in observations}))
        return write_strong_leader_pullback_development_dataset(
            output_root=output_root,
            output_custody_root=output_custody_root,
            observations=observations,
            labels=labels,
            terminal_references=terminal_references,
            manifest_values={
                "implementation_revision": implementation_revision,
                "created_at": created_at.astimezone(UTC),
                "admission_report_sha256": admission.report_sha256,
                "admission_logical_fingerprint": admission.report.logical_fingerprint,
                "diagnostics_report_sha256": admission.report.diagnostics_report_sha256,
                "diagnostics_logical_fingerprint": (
                    admission.report.diagnostics_logical_fingerprint
                ),
                "chronological_plan_fingerprint": population.plan.logical_fingerprint,
                "source_eod_fingerprint": population.source_eod_fingerprint,
                "source_adjustment_fingerprint": (
                    population.source_adjustment_fingerprint
                ),
                "split_basis_session": population.split_basis_session,
                "first_development_signal_session": sessions[0],
                "last_development_signal_session": sessions[-1],
                "development_signal_session_count": len(sessions),
            },
        )


def _build_labels(
    *,
    data_root: Path,
    split_adjustment_publication_root: Path,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    plan: CandidateStrategyChronologicalPlanV1,
    terminal_references: tuple[
        StrongLeaderPullbackTerminalReferenceLedgerEntryV1, ...
    ],
    source_adjustment_fingerprint: str,
    split_basis_session: date,
):
    repository = CanonicalEodReadRepository(data_root)
    adjustment = read_canonical_split_adjustment_publication(
        data_root=data_root,
        publication_root=split_adjustment_publication_root,
    )
    if (
        adjustment.publication.logical_fingerprint
        != source_adjustment_fingerprint
        or adjustment.publication.basis_session != split_basis_session
    ):
        raise StrongLeaderPullbackDevelopmentDatasetCliError(
            "label split adjustment differs from the admitted source"
        )
    adjustment_by_key = {
        (item.instrument_id, item.source_session): item
        for item in adjustment.records
    }
    observations_by_session: dict[
        date, list[StrongLeaderPullbackObservationV1]
    ] = defaultdict(list)
    for item in observations:
        observations_by_session[item.as_of_session].append(item)
    required_ids_by_session: dict[date, set[object]] = defaultdict(set)
    path_by_signal: dict[date, tuple[date, ...]] = {}
    for signal_session, items in observations_by_session.items():
        index = plan.ordered_sessions.index(signal_session)
        path = plan.ordered_sessions[index + 1 : index + 6]
        if len(path) != 5:
            raise StrongLeaderPullbackDevelopmentDatasetCliError(
                "development path is not mature inside the plan"
            )
        path_by_signal[signal_session] = path
        ids = {item.instrument_id for item in items}
        for session in path:
            required_ids_by_session[session].update(ids)

    bars_by_session: dict[date, dict[object, EodMarketBarReadModel]] = {}
    integrity_by_session = {}
    spy_id_by_session = {}
    outcome_sessions = tuple(sorted(required_ids_by_session))
    available_sessions = set(repository.list_session_index())
    if not set(outcome_sessions).issubset(available_sessions):
        raise StrongLeaderPullbackDevelopmentDatasetCliError(
            "canonical EOD lacks a required development outcome session"
        )
    for index, session in enumerate(outcome_sessions, start=1):
        read = repository.read_history_sessions((session,))[0]
        spy = tuple(
            item.instrument_id
            for item in read.bars
            if item.ticker == "SPY" and item.instrument_type.value == "etf"
        )
        if len(spy) != 1:
            raise StrongLeaderPullbackDevelopmentDatasetCliError(
                "SPY is not unique in a development outcome session"
            )
        required = required_ids_by_session[session] | {spy[0]}
        bars_by_session[session] = {
            item.instrument_id: item
            for item in read.bars
            if item.instrument_id in required
        }
        integrity_by_session[session] = read.integrity
        spy_id_by_session[session] = spy[0]
        if index % 25 == 0 or index == len(outcome_sessions):
            print(
                json.dumps(
                    {
                        "status": "reading_development_outcomes",
                        "completed_sessions": index,
                        "total_sessions": len(outcome_sessions),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
            )

    terminal_by_id = {item.instrument_id: item for item in terminal_references}
    labels = []
    label_rejection_count = 0
    label_rejection_examples: list[str] = []
    for session_index, signal_session in enumerate(
        sorted(observations_by_session), start=1
    ):
        path5 = path_by_signal[signal_session]
        for observation in observations_by_session[signal_session]:
            terminal = terminal_by_id.get(observation.instrument_id)
            for horizon in (1, 3, 5):
                path = path5[:horizon]
                target_bars = tuple(
                    bars_by_session[source_session].get(observation.instrument_id)
                    for source_session in path
                )
                spy_bars = tuple(
                    bars_by_session[source_session].get(spy_id_by_session[source_session])
                    for source_session in path
                )
                if any(item is None or not _valid_bar(item) for item in spy_bars):
                    raise StrongLeaderPullbackDevelopmentDatasetCliError(
                        "SPY outcome path is incomplete or invalid"
                    )
                reasons = set()
                if target_bars[0] is None and terminal is None:
                    reasons.add(
                        "missing_next_session_eod_without_terminal_evidence"
                    )
                for source_session, bar in zip(path, target_bars, strict=True):
                    if bar is not None and not _valid_bar(bar):
                        reasons.add("invalid_target_eod_bar")
                    ledger = adjustment_by_key.get(
                        (observation.instrument_id, source_session)
                    )
                    if (
                        ledger is not None
                        and ledger.split_adjustment_status
                        is not AdjustmentAvailabilityStatus.CLEAR
                    ):
                        reasons.add("split_adjustment_evidence_quarantined")
                if target_bars[-1] is None and terminal is None:
                    reasons.add("missing_exit_without_terminal_reference")
                if terminal is not None and any(
                    bar is None and source_session <= terminal.last_observed_eod_session
                    for source_session, bar in zip(path, target_bars, strict=True)
                ):
                    reasons.add("missing_eod_before_terminal_boundary")
                adjusted_target = tuple(
                    _adjusted_target_bar(
                        bar,
                        adjustment_by_key.get((observation.instrument_id, source_session)),
                    )
                    for source_session, bar in zip(path, target_bars, strict=True)
                )
                adjusted_spy = tuple(
                    _adjusted_bar(
                        bar, adjustment_by_key.get((bar.instrument_id, source_session))
                    )
                    for source_session, bar in zip(path, spy_bars, strict=True)
                    if bar is not None
                )
                source_eod_fingerprint = _fingerprint(
                    {
                        "instrument_id": str(observation.instrument_id),
                        "sessions": [
                            integrity_by_session[item].model_dump(mode="json")
                            for item in path
                        ],
                    }
                )
                try:
                    label = build_reconstructed_development_label(
                        observation_fingerprint=observation.logical_fingerprint,
                        signal_session=signal_session,
                        instrument_id=observation.instrument_id,
                        ticker_locator=observation.ticker,
                        expected_path_sessions=path,
                        split_basis_session=split_basis_session,
                        instrument_bars=adjusted_target,
                        benchmark_bars=adjusted_spy,
                        source_eod_fingerprint=source_eod_fingerprint,
                        source_adjustment_fingerprint=(
                            source_adjustment_fingerprint
                        ),
                        terminal_reference=terminal,
                        unavailable_reason_codes=tuple(sorted(reasons)),
                    )
                except Exception as exc:
                    label_rejection_count += 1
                    if len(label_rejection_examples) < 10:
                        label_rejection_examples.append(
                            f"{signal_session.isoformat()}/"
                            f"{observation.instrument_id}/{horizon}/"
                            f"{type(exc).__name__}"
                        )
                    continue
                labels.append(label)
        if session_index % 25 == 0 or session_index == len(observations_by_session):
            print(
                json.dumps(
                    {
                        "status": "constructing_development_labels",
                        "completed_signal_sessions": session_index,
                        "total_signal_sessions": len(observations_by_session),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
            )
    if label_rejection_count:
        raise StrongLeaderPullbackDevelopmentDatasetCliError(
            f"{label_rejection_count} development labels were rejected; "
            f"examples={','.join(label_rejection_examples)}"
        )
    return tuple(
        sorted(
            labels,
            key=lambda item: (
                item.signal_session,
                str(item.instrument_id),
                item.horizon_sessions,
            ),
        )
    )


def _read_terminal_references(**roots: Path):
    def read(function, name: str):
        return function(
            output_root=roots[f"{name}_root"],
            output_custody_root=roots[f"{name}_custody_root"],
        ).report

    return build_strong_leader_pullback_terminal_reference_ledger(
        terminal_boundary=read(
            read_strong_leader_pullback_terminal_boundary_census,
            "terminal_boundary",
        ),
        terminal_gap_v3=read(
            read_strong_leader_pullback_terminal_gap_census_v3,
            "terminal_gap_v3",
        ),
        fixed_cash=read(
            read_strong_leader_pullback_fixed_cash_terminal_evidence,
            "fixed_cash",
        ),
        listed_consideration=read(
            read_strong_leader_pullback_listed_consideration_terminal_evidence,
            "listed_consideration",
        ),
        residual_listed_consideration=read(
            read_strong_leader_pullback_listed_consideration_residual_terminal_evidence,
            "residual_listed_consideration",
        ),
        terminal_population_listed_reference=read(
            read_strong_leader_pullback_terminal_population_listed_reference,
            "terminal_population_listed_reference",
        ),
        terminal_gap_v4=read(
            read_strong_leader_pullback_terminal_gap_census_v4,
            "terminal_gap_v4",
        ),
        final_terminal_bounds=read(
            read_strong_leader_pullback_terminal_reference_final_review,
            "final_terminal",
        ),
    )


def _adjusted_bar(bar: EodMarketBarReadModel, adjustment) -> ReconstructedOutcomeBarV1:
    multiplier = Decimal("1")
    if adjustment is not None:
        if (
            adjustment.split_adjustment_status
            is not AdjustmentAvailabilityStatus.CLEAR
            or adjustment.split_price_multiplier_to_basis is None
        ):
            raise StrongLeaderPullbackDevelopmentDatasetCliError(
                "non-clear adjustment reached numeric label construction"
            )
        multiplier = adjustment.split_price_multiplier_to_basis
    return ReconstructedOutcomeBarV1(
        session=bar.session_date,
        open=bar.open * multiplier,
        high=bar.high * multiplier,
        low=bar.low * multiplier,
        close=bar.close * multiplier,
    )


def _adjusted_target_bar(
    bar: EodMarketBarReadModel | None, adjustment
) -> ReconstructedOutcomeBarV1 | None:
    if bar is None or not _valid_bar(bar):
        return None
    if (
        adjustment is not None
        and adjustment.split_adjustment_status
        is not AdjustmentAvailabilityStatus.CLEAR
    ):
        return None
    return _adjusted_bar(bar, adjustment)


def _valid_bar(bar: EodMarketBarReadModel) -> bool:
    return bool(
        bar.quality_status is QualityStatus.VALID
        and bar.currency == "USD"
        and all(
            value.is_finite() for value in (bar.open, bar.high, bar.low, bar.close)
        )
        and min(bar.open, bar.high, bar.low, bar.close) > 0
        and bar.high >= max(bar.open, bar.close)
        and bar.low <= min(bar.open, bar.close)
    )


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        raise RuntimeError("network access is disabled for development dataset")

    socket.socket = blocked_socket  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
