"""Dell-only runner for the frozen Factor Catalog V1 Development screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict, deque
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.contracts.analytics.v1 import (
    QuantResearchFactorAvailability,
    QuantResearchFactorObservationV1,
    StrategyEvaluationSplit,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening import (
    quant_research_factor_screening_protocol_v1,
)
from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import AdjustmentAvailabilityStatus
from tip_api.persistence.development_coverage_census import (
    read_development_coverage_census,
)
from tip_api.persistence.parquet.canonical_corporate_action import (
    read_canonical_split_action_publication,
)
from tip_api.persistence.parquet.canonical_split_adjustment import (
    read_canonical_split_adjustment_publication,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.quant_research_factor_diagnostics import (
    REPORT_FILE as DIAGNOSTICS_REPORT_FILE,
    read_quant_research_factor_diagnostics,
)
from tip_api.persistence.quant_research_factor_screening import (
    write_quant_research_factor_screening_report,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.candidate_strategy_development_coverage_cli import (
    _discover_membership_partitions,
    _validated_data_root,
    _validated_shadow_root,
)
from tip_api.services.candidate_strategy_research_execution import (
    build_candidate_strategy_chronological_plan,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.quant_research_factor_diagnostics_cli import (
    _build_session_observations,
    _calculation_code_sha256,
    _network_disabled,
)
from tip_api.services.quant_research_factor_screening import (
    build_quant_research_factor_screening_report,
)
from tip_api.services.quant_research_factor_screening_labels import (
    build_quant_research_factor_screening_label,
)
from tip_api.services.strong_leader_pullback_development_dataset_cli import (
    _adjusted_bar,
    _adjusted_target_bar,
    _read_terminal_references,
    _safe_error_detail,
    _valid_bar,
)
from tip_api.services.strong_leader_pullback_diagnostics_cli import (
    _read_membership,
)
from tip_api.services.strong_leader_pullback_method_engineering_launch_review import (
    read_strong_leader_pullback_method_engineering_launch_review,
)


class QuantResearchFactorScreeningCliError(RuntimeError):
    """Raised when the frozen real screen cannot be executed safely."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the frozen owner-only Factor Catalog V1 Development screen."
    )
    for name in (
        "data-root",
        "membership-shadow-root",
        "development-census-root",
        "split-action-publication-root",
        "split-adjustment-publication-root",
        "method-launch-root",
        "method-launch-custody-root",
        "factor-diagnostics-root",
        "factor-diagnostics-custody-root",
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
        path, sha256, persistence_status, report = run_factor_screening(**vars(args))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "factor_screening_rejected",
                    "error_type": type(exc).__name__,
                    "error_detail": _safe_error_detail(exc),
                    "external_request_count": 0,
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
                "status": persistence_status,
                "report_path": str(path),
                "report_sha256": sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "screening_status": report.status.value,
                "signal_session_count": report.signal_session_count,
                "observation_count": report.observation_count,
                "label_count": report.label_count,
                "selected_factor_ids": report.selected_factor_ids,
                "decision_status_counts": dict(
                    sorted(Counter(item.status.value for item in report.decisions).items())
                ),
                "external_request_count": 0,
                "canonical_data_write_count": 0,
                "production_write_count": 0,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def run_factor_screening(
    *,
    data_root: Path,
    membership_shadow_root: Path,
    development_census_root: Path,
    split_action_publication_root: Path,
    split_adjustment_publication_root: Path,
    method_launch_root: Path,
    method_launch_custody_root: Path,
    factor_diagnostics_root: Path,
    factor_diagnostics_custody_root: Path,
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
        protocol = quant_research_factor_screening_protocol_v1()
        _validate_run_identity(created_at, implementation_revision)
        canonical_root = _validated_data_root(data_root)
        shadow_root = _validated_shadow_root(membership_shadow_root)
        diagnostics = read_quant_research_factor_diagnostics(
            output_root=factor_diagnostics_root,
            output_custody_root=factor_diagnostics_custody_root,
        )
        if (
            diagnostics.logical_fingerprint != protocol.source_diagnostics_fingerprint
            or _file_sha256(factor_diagnostics_root / DIAGNOSTICS_REPORT_FILE)
            != protocol.source_diagnostics_sha256
            or _calculation_code_sha256() != diagnostics.calculation_code_sha256
        ):
            raise QuantResearchFactorScreeningCliError(
                "factor qualification identity or calculation code differs"
            )
        launch = read_strong_leader_pullback_method_engineering_launch_review(
            output_root=method_launch_root,
            output_custody_root=method_launch_custody_root,
        ).report
        census = read_development_coverage_census(output_root=development_census_root)
        action_source = read_canonical_split_action_publication(
            data_root=canonical_root,
            publication_root=split_action_publication_root,
        )
        adjustment_source = read_canonical_split_adjustment_publication(
            data_root=canonical_root,
            publication_root=split_adjustment_publication_root,
        )
        plan = build_candidate_strategy_chronological_plan(
            ordered_sessions=tuple(item.session_date for item in census.sessions),
            calendar=ExchangeCalendar(),
        )
        if (
            plan.logical_fingerprint != protocol.chronological_plan_fingerprint
            or launch.logical_fingerprint != diagnostics.source_population_fingerprint
            or census.logical_fingerprint != diagnostics.source_membership_fingerprint
            or action_source.publication.logical_fingerprint
            != diagnostics.source_action_fingerprint
            or adjustment_source.publication.logical_fingerprint
            != diagnostics.source_adjustment_fingerprint
        ):
            raise QuantResearchFactorScreeningCliError(
                "screening source lineage differs from qualification"
            )
        observations = _build_development_factor_observations(
            repository=CanonicalEodReadRepository(canonical_root),
            shadow_root=shadow_root,
            census=census,
            plan=plan,
            action_source=action_source,
            adjustment_source=adjustment_source,
            diagnostics=diagnostics,
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
        labels = _build_factor_labels(
            data_root=canonical_root,
            split_adjustment_publication_root=split_adjustment_publication_root,
            observations=observations,
            plan=plan,
            terminal_references=terminal_references,
            source_adjustment_fingerprint=diagnostics.source_adjustment_fingerprint,
            split_basis_session=adjustment_source.publication.basis_session,
        )
        report = build_quant_research_factor_screening_report(
            observations=observations,
            labels=labels,
            implementation_revision=implementation_revision,
            created_at=created_at.astimezone(UTC),
            source_eod_fingerprint=diagnostics.source_eod_fingerprint,
            source_membership_fingerprint=diagnostics.source_membership_fingerprint,
            source_action_fingerprint=diagnostics.source_action_fingerprint,
            source_adjustment_fingerprint=diagnostics.source_adjustment_fingerprint,
            factor_calculation_code_sha256=_calculation_code_sha256(),
            label_code_sha256=_label_code_sha256(),
            screening_code_sha256=_screening_code_sha256(),
        )
        path, sha256, status = write_quant_research_factor_screening_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )
        return path, sha256, status, report


def _build_development_factor_observations(
    *, repository, shadow_root, census, plan, action_source, adjustment_source, diagnostics
):
    from tip_api.contracts.market_data.v1 import CorporateActionRecordStatus

    protocol = quant_research_factor_screening_protocol_v1()
    partitions = _discover_membership_partitions(shadow_root)
    if tuple(sorted(partitions)) != plan.ordered_sessions:
        raise QuantResearchFactorScreeningCliError(
            "Membership partitions do not exactly cover the frozen plan"
        )
    available_sessions = set(repository.list_session_index())
    if not set(plan.ordered_sessions).issubset(available_sessions):
        raise QuantResearchFactorScreeningCliError("canonical EOD does not cover plan")
    active_action_keys = {
        (item.instrument_id, item.effective_date)
        for item in action_source.actions
        if item.record_status is CorporateActionRecordStatus.ACTIVE
    }
    quarantined_action_keys = {
        (item.instrument_id, item.effective_date)
        for item in action_source.actions
        if item.record_status is not CorporateActionRecordStatus.ACTIVE
    }
    unresolved_impact_keys = {
        (item.instrument_id, effective_date)
        for item in action_source.publication.possible_unresolved_impacts
        for effective_date in item.effective_dates
    }
    clear_adjustments = {
        (item.instrument_id, item.source_session): item
        for item in adjustment_source.records
        if item.split_adjustment_status is AdjustmentAvailabilityStatus.CLEAR
    }
    quarantined_adjustment_keys = {
        (item.instrument_id, item.source_session)
        for item in adjustment_source.records
        if item.split_adjustment_status is not AdjustmentAvailabilityStatus.CLEAR
    }
    census_by_session = {item.session_date: item for item in census.sessions}
    diagnostics_by_session = {
        item.as_of_session: item
        for item in diagnostics.session_availability
        if item.factor_id == "relative_return_spy_20s"
    }
    assignments = {item.session: item for item in plan.assignments}
    calendar = ExchangeCalendar()
    window = deque(maxlen=21)
    retained = []
    for position, session in enumerate(plan.ordered_sessions, start=1):
        if session > plan.development_last_session:
            break
        read = repository.read_history_sessions((session,))[0]
        window.append(read)
        membership, _ = _read_membership(
            shadow_root=shadow_root,
            partition=partitions[session],
            census_session=census_by_session[session],
        )
        member_ids = frozenset(item.instrument_id for item in membership)
        observations = ()
        if member_ids:
            if len(window) != 21:
                raise QuantResearchFactorScreeningCliError(
                    "included Membership precedes the complete factor window"
                )
            observations = _build_session_observations(
                session=session,
                session_reads=tuple(window),
                member_ids=member_ids,
                active_action_keys=active_action_keys,
                quarantined_action_keys=quarantined_action_keys,
                unresolved_impact_keys=unresolved_impact_keys,
                clear_adjustments=clear_adjustments,
                quarantined_adjustment_keys=quarantined_adjustment_keys,
                action_start=action_source.publication.start_date,
                adjustment_start=adjustment_source.publication.first_source_session,
                source_eod_fingerprint=diagnostics.source_eod_fingerprint,
                source_adjustment_fingerprint=diagnostics.source_adjustment_fingerprint,
                calendar=calendar,
            )
        assignment = assignments[session]
        availability = diagnostics_by_session[session]
        qualified = (
            assignment.raw_split is StrategyEvaluationSplit.DEVELOPMENT
            and assignment.usable_for_signal_evaluation
            and availability.expected_count > 0
            and availability.available_count == availability.expected_count
        )
        if qualified:
            if (
                len(observations) != availability.available_count
                or any(
                    value.availability is not QuantResearchFactorAvailability.AVAILABLE
                    for observation in observations
                    for value in observation.factor_values
                )
            ):
                raise QuantResearchFactorScreeningCliError(
                    "recomputed complete factor session differs from qualification"
                )
            retained.extend(observations)
        if position % 10 == 0 or session == plan.development_last_session:
            print(
                json.dumps(
                    {
                        "status": "recomputing_factor_development_cohort",
                        "completed_source_sessions": position,
                        "retained_observation_count": len(retained),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
            )
    result = tuple(
        sorted(retained, key=lambda item: (item.as_of_session, str(item.instrument_id)))
    )
    if (
        len(result) != protocol.development_expected_path_count
        or len({item.as_of_session for item in result})
        != protocol.development_eligible_session_count
        or result[0].as_of_session != protocol.first_development_signal_session
        or result[-1].as_of_session != protocol.last_development_signal_session
    ):
        raise QuantResearchFactorScreeningCliError(
            "recomputed Development cohort differs from frozen protocol"
        )
    return result


def _build_factor_labels(
    *,
    data_root: Path,
    split_adjustment_publication_root: Path,
    observations: tuple[QuantResearchFactorObservationV1, ...],
    plan,
    terminal_references,
    source_adjustment_fingerprint: str,
    split_basis_session: date,
):
    repository = CanonicalEodReadRepository(data_root)
    adjustment = read_canonical_split_adjustment_publication(
        data_root=data_root,
        publication_root=split_adjustment_publication_root,
    )
    if (
        adjustment.publication.logical_fingerprint != source_adjustment_fingerprint
        or adjustment.publication.basis_session != split_basis_session
    ):
        raise QuantResearchFactorScreeningCliError(
            "screening-label adjustment source differs"
        )
    adjustment_by_key = {
        (item.instrument_id, item.source_session): item for item in adjustment.records
    }
    observations_by_session = defaultdict(list)
    for item in observations:
        observations_by_session[item.as_of_session].append(item)
    required_ids_by_session = defaultdict(set)
    path_by_signal = {}
    plan_index = {session: index for index, session in enumerate(plan.ordered_sessions)}
    for signal_session, items in observations_by_session.items():
        index = plan_index[signal_session]
        path = plan.ordered_sessions[index + 1 : index + 6]
        if len(path) != 5:
            raise QuantResearchFactorScreeningCliError(
                "screening-label path is not mature inside the plan"
            )
        path_by_signal[signal_session] = path
        ids = {item.instrument_id for item in items}
        for session in path:
            required_ids_by_session[session].update(ids)
    bars_by_session = {}
    integrity_by_session = {}
    spy_id_by_session = {}
    outcome_sessions = tuple(sorted(required_ids_by_session))
    if not set(outcome_sessions).issubset(repository.list_session_index()):
        raise QuantResearchFactorScreeningCliError(
            "canonical EOD lacks a screening outcome session"
        )
    for index, session in enumerate(outcome_sessions, start=1):
        read = repository.read_history_sessions((session,))[0]
        spy = tuple(
            item.instrument_id
            for item in read.bars
            if item.ticker == "SPY" and item.instrument_type.value == "etf"
        )
        if len(spy) != 1:
            raise QuantResearchFactorScreeningCliError(
                "SPY is not unique in a screening outcome session"
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
                        "status": "reading_factor_screening_outcomes",
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
    for session_index, signal_session in enumerate(sorted(observations_by_session), start=1):
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
                    raise QuantResearchFactorScreeningCliError(
                        "SPY screening path is incomplete or invalid"
                    )
                reasons = set()
                if target_bars[0] is None and terminal is None:
                    reasons.add("missing_next_session_eod_without_terminal_evidence")
                for source_session, bar in zip(path, target_bars, strict=True):
                    if bar is not None and not _valid_screening_bar(bar):
                        reasons.add("invalid_target_eod_bar")
                    ledger = adjustment_by_key.get((observation.instrument_id, source_session))
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
                        bar,
                        adjustment_by_key.get((bar.instrument_id, source_session)),
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
                labels.append(
                    build_quant_research_factor_screening_label(
                        observation_fingerprint=observation.logical_fingerprint,
                        signal_session=signal_session,
                        instrument_id=observation.instrument_id,
                        display_ticker=observation.display_ticker,
                        expected_path_sessions=path,
                        split_basis_session=split_basis_session,
                        instrument_bars=adjusted_target,
                        benchmark_bars=adjusted_spy,
                        source_eod_fingerprint=source_eod_fingerprint,
                        source_adjustment_fingerprint=source_adjustment_fingerprint,
                        terminal_reference=terminal,
                        unavailable_reason_codes=tuple(sorted(reasons)),
                    )
                )
        if session_index % 10 == 0 or session_index == len(observations_by_session):
            print(
                json.dumps(
                    {
                        "status": "constructing_factor_screening_labels",
                        "completed_signal_sessions": session_index,
                        "total_signal_sessions": len(observations_by_session),
                        "label_count": len(labels),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
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


def _valid_screening_bar(bar: EodMarketBarReadModel) -> bool:
    return bool(
        bar.quality_status is QualityStatus.VALID
        and bar.currency == "USD"
        and all(value.is_finite() for value in (bar.open, bar.high, bar.low, bar.close))
        and min(bar.open, bar.high, bar.low, bar.close) > 0
        and bar.high >= max(bar.open, bar.close)
        and bar.low <= min(bar.open, bar.close)
    )


def _validate_run_identity(created_at: datetime, implementation_revision: str) -> None:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise QuantResearchFactorScreeningCliError(
            "factor-screening creation time must be timezone-aware"
        )
    if len(implementation_revision) != 40 or any(
        character not in "0123456789abcdef" for character in implementation_revision
    ):
        raise QuantResearchFactorScreeningCliError(
            "implementation revision must be one exact Git commit"
        )


def _label_code_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    return _combined_sha256(
        (
            root / "contracts/analytics/v1/quant_research_factor_screening_result.py",
            root / "services/quant_research_factor_screening_labels.py",
        )
    )


def _screening_code_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    return _combined_sha256(
        (
            root / "contracts/analytics/v1/quant_research_factor_screening.py",
            root / "contracts/analytics/v1/quant_research_factor_screening_result.py",
            root / "services/quant_research_factor_screening.py",
            root / "services/quant_research_factor_screening_cli.py",
        )
    )


def _combined_sha256(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.name):
        payload = path.read_bytes()
        digest.update(path.name.encode())
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("created-at must be timezone-aware")
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    raise SystemExit(main())
