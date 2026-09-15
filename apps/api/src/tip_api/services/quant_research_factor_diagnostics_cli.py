"""Read-only Dell runner for Factor Catalog V1 outcome-blind diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import deque
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Mapping
from uuid import UUID

from tip_api.contracts.analytics.v1.quant_research_factor_catalog import (
    QUANT_RESEARCH_FACTOR_ORDER,
    QuantResearchFactorAvailability,
    QuantResearchFactorValueV1,
    build_quant_research_factor_observation,
    factor_definition_fingerprint,
    quant_research_factor_catalog_v1,
)
from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
    CorporateActionRecordStatus,
)
from tip_api.persistence.development_coverage_census import (
    read_development_coverage_census,
)
from tip_api.persistence.eod_read import EodHistorySessionRead
from tip_api.persistence.parquet.canonical_corporate_action import (
    read_canonical_split_action_publication,
)
from tip_api.persistence.parquet.canonical_split_adjustment import (
    read_canonical_split_adjustment_publication,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.quant_research_factor_diagnostics import (
    write_quant_research_factor_diagnostics,
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
from tip_api.services.quant_research_factor_diagnostics import (
    QuantResearchFactorDiagnosticsAccumulator,
)
from tip_api.services.quant_research_factor_values import (
    QuantResearchFactorBar,
    calculate_quant_research_factor_values,
)
from tip_api.services.strong_leader_pullback_diagnostics_cli import (
    _network_disabled,
    _read_membership,
    _split_path_status,
    _valid_bar,
    _validate_census_sources,
    _validate_launch_and_census,
)
from tip_api.services.strong_leader_pullback_method_engineering_launch_review import (
    read_strong_leader_pullback_method_engineering_launch_review,
)


LIMITATION_CODES = (
    "historical_classification_unavailable",
    "reconstructed_membership_not_as_operated",
    "split_neutral_absence_unproven",
    "temporal_coverage_limited_to_287_sessions",
)


class QuantResearchFactorDiagnosticsCliError(RuntimeError):
    """Raised when the frozen local qualification boundary cannot be proved."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build one private zero-outcome Factor Catalog V1 diagnostic."
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--membership-shadow-root", type=Path, required=True)
    parser.add_argument("--development-census-root", type=Path, required=True)
    parser.add_argument("--split-action-publication-root", type=Path, required=True)
    parser.add_argument("--split-adjustment-publication-root", type=Path, required=True)
    parser.add_argument("--method-launch-root", type=Path, required=True)
    parser.add_argument("--method-launch-custody-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output-custody-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        path, report = run_quant_research_factor_diagnostics(
            data_root=args.data_root,
            membership_shadow_root=args.membership_shadow_root,
            development_census_root=args.development_census_root,
            split_action_publication_root=args.split_action_publication_root,
            split_adjustment_publication_root=args.split_adjustment_publication_root,
            method_launch_root=args.method_launch_root,
            method_launch_custody_root=args.method_launch_custody_root,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "factor_diagnostics_rejected",
                    "error_type": type(exc).__name__,
                    "error_detail": str(exc)[:500],
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
                "status": "completed",
                "report_path": str(path),
                "logical_fingerprint": report.logical_fingerprint,
                "session_count": report.session_count,
                "expected_path_count": report.expected_path_count,
                "complete_factor_vector_count": report.complete_factor_vector_count,
                "available_factor_cell_count": report.available_factor_cell_count,
                "near_duplicate_group_count": len(report.near_duplicate_groups),
                "external_request_count": 0,
                "canonical_data_write_count": 0,
                "production_write_count": 0,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def run_quant_research_factor_diagnostics(
    *,
    data_root: Path,
    membership_shadow_root: Path,
    development_census_root: Path,
    split_action_publication_root: Path,
    split_adjustment_publication_root: Path,
    method_launch_root: Path,
    method_launch_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
):
    with _network_disabled():
        canonical_root = _validated_data_root(data_root)
        shadow_root = _validated_shadow_root(membership_shadow_root)
        launch = read_strong_leader_pullback_method_engineering_launch_review(
            output_root=method_launch_root,
            output_custody_root=method_launch_custody_root,
        ).report
        census = read_development_coverage_census(output_root=development_census_root)
        _validate_launch_and_census(launch=launch, census=census)
        action_source = read_canonical_split_action_publication(
            data_root=canonical_root,
            publication_root=split_action_publication_root,
        )
        adjustment_source = read_canonical_split_adjustment_publication(
            data_root=canonical_root,
            publication_root=split_adjustment_publication_root,
        )
        _validate_census_sources(
            census=census,
            action_fingerprint=action_source.publication.logical_fingerprint,
            adjustment_fingerprint=adjustment_source.publication.logical_fingerprint,
        )

        calendar = ExchangeCalendar()
        plan = build_candidate_strategy_chronological_plan(
            ordered_sessions=tuple(item.session_date for item in census.sessions),
            calendar=calendar,
        )
        partitions = _discover_membership_partitions(shadow_root)
        if tuple(sorted(partitions)) != plan.ordered_sessions:
            raise QuantResearchFactorDiagnosticsCliError(
                "Membership partitions do not exactly cover the frozen plan"
            )
        repository = CanonicalEodReadRepository(canonical_root)
        if not set(plan.ordered_sessions).issubset(repository.list_session_index()):
            raise QuantResearchFactorDiagnosticsCliError(
                "canonical EOD does not cover the frozen plan"
            )

        evidence_by_family = {item.family: item for item in census.dataset_evidence}
        eod_fingerprint = evidence_by_family["eod_price_bar"].logical_fingerprint
        if eod_fingerprint is None:
            raise QuantResearchFactorDiagnosticsCliError(
                "frozen EOD evidence lacks a logical fingerprint"
            )
        accumulator = QuantResearchFactorDiagnosticsAccumulator(
            chronological_plan_fingerprint=plan.logical_fingerprint,
            source_population_fingerprint=launch.logical_fingerprint,
            source_eod_fingerprint=eod_fingerprint,
            source_membership_fingerprint=census.logical_fingerprint,
            source_action_fingerprint=action_source.publication.logical_fingerprint,
            source_adjustment_fingerprint=adjustment_source.publication.logical_fingerprint,
            calculation_code_sha256=_calculation_code_sha256(),
            diagnostic_code_sha256=_diagnostic_code_sha256(),
            limitation_codes=LIMITATION_CODES,
        )
        _accumulate_population(
            accumulator=accumulator,
            repository=repository,
            shadow_root=shadow_root,
            partitions=partitions,
            census=census,
            plan=plan,
            action_source=action_source,
            adjustment_source=adjustment_source,
            eod_fingerprint=eod_fingerprint,
            calendar=calendar,
        )
        report = accumulator.build()
        if (
            report.expected_path_count != launch.included_path_count
            or report.session_count != launch.signal_session_count
            or report.first_session.isoformat() != launch.first_signal_session
            or report.last_session.isoformat() != launch.last_signal_session
        ):
            raise QuantResearchFactorDiagnosticsCliError(
                "factor diagnostic population does not reconcile to frozen launch"
            )
        report_path = write_quant_research_factor_diagnostics(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )
        return report_path, report


def _accumulate_population(
    *,
    accumulator: QuantResearchFactorDiagnosticsAccumulator,
    repository: CanonicalEodReadRepository,
    shadow_root: Path,
    partitions: Mapping[date, Path],
    census,
    plan,
    action_source,
    adjustment_source,
    eod_fingerprint: str,
    calendar: ExchangeCalendar,
) -> None:
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
    window: deque[object] = deque(maxlen=21)
    total_sessions = len(plan.ordered_sessions)
    for position, session in enumerate(plan.ordered_sessions, start=1):
        read = repository.read_history_sessions((session,))[0]
        window.append(read)
        membership, _ = _read_membership(
            shadow_root=shadow_root,
            partition=partitions[session],
            census_session=census_by_session[session],
        )
        member_ids = frozenset(item.instrument_id for item in membership)
        if not member_ids:
            observations = ()
        else:
            if len(window) != 21:
                raise QuantResearchFactorDiagnosticsCliError(
                    "included Membership appears before the complete factor window"
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
                source_eod_fingerprint=eod_fingerprint,
                source_adjustment_fingerprint=adjustment_source.publication.logical_fingerprint,
                calendar=calendar,
            )
        accumulator.add_session(as_of_session=session, observations=observations)
        if position % 10 == 0 or position == total_sessions:
            print(
                json.dumps(
                    {
                        "status": "running",
                        "completed_sessions": position,
                        "total_sessions": total_sessions,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
            )


def _build_session_observations(
    *,
    session: date,
    session_reads: tuple[EodHistorySessionRead, ...],
    member_ids: frozenset[UUID],
    active_action_keys: set[tuple[UUID, date]],
    quarantined_action_keys: set[tuple[UUID, date]],
    unresolved_impact_keys: set[tuple[UUID, date]],
    clear_adjustments: Mapping[tuple[UUID, date], AdjustmentLedgerEntryV1],
    quarantined_adjustment_keys: set[tuple[UUID, date]],
    action_start: date,
    adjustment_start: date,
    source_eod_fingerprint: str,
    source_adjustment_fingerprint: str,
    calendar: ExchangeCalendar,
):
    sessions = tuple(item.integrity.session_date for item in session_reads)
    if sessions != tuple((*calendar.sessions_before(session, 20), session)):
        raise QuantResearchFactorDiagnosticsCliError(
            "factor window is not the exact 21-session interval"
        )
    by_session = {
        item.integrity.session_date: {bar.instrument_id: bar for bar in item.bars}
        for item in session_reads
    }
    current = by_session[session]
    spy_id = _spy_instrument_id(by_session)
    required_ids = member_ids | ({spy_id} if spy_id is not None else set())
    missing_or_invalid = {
        instrument_id
        for instrument_id in required_ids
        if any(
            instrument_id not in by_session[source_session]
            or not _valid_factor_bar(by_session[source_session].get(instrument_id))
            for source_session in sessions
        )
    }
    hazard_ids, _ = _split_path_status(
        required_ids=frozenset(required_ids),
        sessions=sessions,
        active_action_keys=active_action_keys,
        quarantined_action_keys=quarantined_action_keys,
        unresolved_impact_keys=unresolved_impact_keys,
        clear_adjustments=clear_adjustments,
        quarantined_adjustment_keys=quarantined_adjustment_keys,
        action_start=action_start,
        adjustment_start=adjustment_start,
    )
    reasons = set()
    if spy_id is None:
        reasons.add("complete_cross_section_spy_unavailable")
    if missing_or_invalid:
        reasons.add("complete_cross_section_eod_unavailable")
    if hazard_ids:
        reasons.add("complete_cross_section_split_evidence_quarantined")
    if reasons:
        values = _unavailable_values(tuple(sorted(reasons)))
        return tuple(
            _observation(
                session=session,
                instrument_id=instrument_id,
                ticker=current[instrument_id].ticker if instrument_id in current else None,
                factor_values=values,
                source_eod_fingerprint=source_eod_fingerprint,
                source_adjustment_fingerprint=source_adjustment_fingerprint,
            )
            for instrument_id in sorted(member_ids, key=str)
        )

    assert spy_id is not None
    adjusted = {
        instrument_id: tuple(
            _adjusted_factor_bar(
                by_session[source_session][instrument_id],
                clear_adjustments.get((instrument_id, source_session)),
            )
            for source_session in sessions
        )
        for instrument_id in required_ids
    }
    benchmark = adjusted[spy_id]
    return tuple(
        _observation(
            session=session,
            instrument_id=instrument_id,
            ticker=current[instrument_id].ticker,
            factor_values=calculate_quant_research_factor_values(
                stock_series=adjusted[instrument_id],
                benchmark_series=benchmark,
            ),
            source_eod_fingerprint=source_eod_fingerprint,
            source_adjustment_fingerprint=source_adjustment_fingerprint,
        )
        for instrument_id in sorted(member_ids, key=str)
    )


def _observation(
    *,
    session: date,
    instrument_id: UUID,
    ticker: str | None,
    factor_values: tuple[QuantResearchFactorValueV1, ...],
    source_eod_fingerprint: str,
    source_adjustment_fingerprint: str,
):
    catalog = quant_research_factor_catalog_v1()
    return build_quant_research_factor_observation(
        catalog_fingerprint=catalog.logical_fingerprint,
        calculation_version=catalog.calculation_version,
        as_of_session=session,
        instrument_id=instrument_id,
        display_ticker=ticker,
        membership_tier="reconstructed_latest_vintage_research_only",
        source_max_session=session,
        source_eod_fingerprint=source_eod_fingerprint,
        source_adjustment_fingerprint=source_adjustment_fingerprint,
        factor_values=factor_values,
        contains_forward_outcomes=False,
        factor_screening_authorized=False,
        model_construction_authorized=False,
        candidate_activation_authorized=False,
    )


def _unavailable_values(reasons: tuple[str, ...]) -> tuple[QuantResearchFactorValueV1, ...]:
    return tuple(
        QuantResearchFactorValueV1(
            factor_id=factor_id,
            factor_definition_fingerprint=factor_definition_fingerprint(factor_id),
            availability=QuantResearchFactorAvailability.UNAVAILABLE,
            reason_codes=reasons,
        )
        for factor_id in QUANT_RESEARCH_FACTOR_ORDER
    )


def _spy_instrument_id(
    by_session: Mapping[date, Mapping[UUID, EodMarketBarReadModel]],
) -> UUID | None:
    matches = {
        item.instrument_id
        for current in by_session.values()
        for item in current.values()
        if item.ticker == "SPY" and item.instrument_type.value == "etf"
    }
    if len(matches) != 1:
        return None
    return next(iter(matches))


def _valid_factor_bar(bar: EodMarketBarReadModel | None) -> bool:
    return bool(
        _valid_bar(bar)
        and bar is not None
        and bar.low <= min(bar.open, bar.close)
        and bar.high >= max(bar.open, bar.close)
    )


def _adjusted_factor_bar(
    bar: EodMarketBarReadModel, adjustment: AdjustmentLedgerEntryV1 | None
) -> QuantResearchFactorBar:
    price = Decimal("1")
    volume = Decimal("1")
    if adjustment is not None:
        if (
            adjustment.split_price_multiplier_to_basis is None
            or adjustment.split_volume_multiplier_to_basis is None
        ):
            raise QuantResearchFactorDiagnosticsCliError(
                "clear split adjustment lacks factors"
            )
        price = adjustment.split_price_multiplier_to_basis
        volume = adjustment.split_volume_multiplier_to_basis
    return QuantResearchFactorBar(
        session=bar.session_date,
        open=bar.open * price,
        high=bar.high * price,
        low=bar.low * price,
        close=bar.close * price,
        volume=bar.volume * volume,
    )


def _calculation_code_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    return _combined_sha256(
        (
            root / "contracts/analytics/v1/quant_research_factor_catalog.py",
            root / "services/quant_research_factor_values.py",
        )
    )


def _diagnostic_code_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    return _combined_sha256(
        (
            root / "contracts/analytics/v1/quant_research_factor_diagnostics.py",
            root / "services/quant_research_factor_diagnostics.py",
            root / "services/quant_research_factor_diagnostics_cli.py",
        )
    )


def _combined_sha256(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.name):
        payload = path.read_bytes()
        digest.update(path.name.encode("utf-8"))
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
