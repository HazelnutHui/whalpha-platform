"""Network-disabled Dell runner for Factor Catalog V2 qualification."""

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

import numpy as np

from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
)
from tip_api.contracts.analytics.v1.quant_research_factor_qualification_v2 import (
    quant_research_factor_qualification_protocol_v2,
)
from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
    CorporateActionRecordStatus,
)
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
from tip_api.persistence.quant_research_factor_qualification_v2 import (
    write_quant_research_factor_qualification_v2,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.candidate_strategy_development_coverage_cli import (
    _discover_membership_partitions,
    _validated_data_root,
    _validated_shadow_root,
)
from tip_api.services.historical_split_adjustment_candidate import (
    read_historical_split_adjustment_candidate,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.quant_research_factor_matrix_v2 import (
    QuantResearchFactorMatrixV2,
    calculate_quant_research_factor_matrix_v2,
)
from tip_api.services.quant_research_factor_qualification_v2 import (
    QuantResearchFactorQualificationAccumulatorV2,
    combined_code_sha256,
)
from tip_api.services.quant_research_factor_values_v2 import (
    QuantResearchFactorBarV2,
)
from tip_api.services.quant_research_historical_split_extension_v2 import (
    QuantResearchSplitAdjustmentV2,
    build_quant_research_historical_split_evidence_v2,
)
from tip_api.services.strong_leader_pullback_diagnostics_cli import (
    _network_disabled,
    _read_membership,
    _split_path_status,
    _valid_bar,
    _validate_census_sources,
)


LIMITATION_CODES = (
    "daily_bars_do_not_observe_spread_or_signed_order_flow",
    "historical_classification_unavailable",
    "historical_regime_diversity_unproven",
    "reconstructed_membership_not_as_operated",
    "split_neutral_absence_unproven",
)


class QuantResearchFactorQualificationV2CliError(RuntimeError):
    """Raised when the frozen local V2 qualification boundary cannot be proved."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build one private zero-outcome Factor Catalog V2 qualification."
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--membership-shadow-root", type=Path, required=True)
    parser.add_argument("--development-census-root", type=Path, required=True)
    parser.add_argument("--split-action-publication-root", type=Path, required=True)
    parser.add_argument("--split-adjustment-publication-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output-custody-root", type=Path, required=True)
    parser.add_argument("--historical-split-candidate-root", type=Path)
    parser.add_argument("--historical-split-candidate-custody-root", type=Path)
    args = parser.parse_args(argv)
    try:
        path, report = run_quant_research_factor_qualification_v2(
            data_root=args.data_root,
            membership_shadow_root=args.membership_shadow_root,
            development_census_root=args.development_census_root,
            split_action_publication_root=args.split_action_publication_root,
            split_adjustment_publication_root=(
                args.split_adjustment_publication_root
            ),
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            historical_split_candidate_root=(
                args.historical_split_candidate_root
            ),
            historical_split_candidate_custody_root=(
                args.historical_split_candidate_custody_root
            ),
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "factor_qualification_v2_rejected",
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
                "status": report.status.value,
                "report_path": str(path),
                "logical_fingerprint": report.logical_fingerprint,
                "signal_session_count": report.signal_session_count,
                "expected_path_count": report.expected_path_count,
                "complete_factor_vector_count": (
                    report.complete_factor_vector_count
                ),
                "eligible_candidate_alpha_count": (
                    report.eligible_candidate_alpha_count
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


def run_quant_research_factor_qualification_v2(
    *,
    data_root: Path,
    membership_shadow_root: Path,
    development_census_root: Path,
    split_action_publication_root: Path,
    split_adjustment_publication_root: Path,
    output_root: Path,
    output_custody_root: Path,
    historical_split_candidate_root: Path | None = None,
    historical_split_candidate_custody_root: Path | None = None,
):
    with _network_disabled():
        canonical_root = _validated_data_root(data_root)
        shadow_root = _validated_shadow_root(membership_shadow_root)
        census = read_development_coverage_census(
            output_root=development_census_root
        )
        _validate_v2_census(census)
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
            adjustment_fingerprint=(
                adjustment_source.publication.logical_fingerprint
            ),
        )
        if (historical_split_candidate_root is None) != (
            historical_split_candidate_custody_root is None
        ):
            raise QuantResearchFactorQualificationV2CliError(
                "historical split candidate root and custody must be supplied together"
            )

        calendar = ExchangeCalendar()
        ordered_sessions = tuple(item.session_date for item in census.sessions)
        chronological_plan_fingerprint = _chronological_plan_fingerprint(
            ordered_sessions=ordered_sessions,
            calendar=calendar,
        )
        partitions = _discover_membership_partitions(shadow_root)
        if tuple(sorted(partitions)) != ordered_sessions:
            raise QuantResearchFactorQualificationV2CliError(
                "Membership partitions do not exactly cover the frozen plan"
            )
        memberships, source_population_fingerprint = _read_signal_memberships(
            shadow_root=shadow_root,
            partitions=partitions,
            census=census,
            ordered_sessions=ordered_sessions,
        )
        protocol = quant_research_factor_qualification_protocol_v2()
        if (
            sum(len(items) for items in memberships.values())
            != protocol.expected_signal_path_count
        ):
            raise QuantResearchFactorQualificationV2CliError(
                "V2 Membership paths do not reconcile to the frozen population"
            )

        repository = CanonicalEodReadRepository(canonical_root)
        source_sessions = (
            *calendar.sessions_before(ordered_sessions[0], 126),
            *ordered_sessions,
        )
        available_sessions = repository.list_session_index()
        if not set(source_sessions).issubset(available_sessions):
            raise QuantResearchFactorQualificationV2CliError(
                "canonical EOD does not cover the exact V2 source interval"
            )

        all_member_ids = frozenset(
            item.instrument_id
            for records in memberships.values()
            for item in records
        )
        first_source_read = repository.read_history_sessions((source_sessions[0],))[0]
        spy_id = _spy_instrument_id(first_source_read.bars)
        if historical_split_candidate_root is not None:
            historical_candidate = read_historical_split_adjustment_candidate(
                output_root=historical_split_candidate_root,
                output_custody_root=(
                    historical_split_candidate_custody_root
                ),
            )
            split_evidence = build_quant_research_historical_split_evidence_v2(
                candidate=historical_candidate.candidate,
                candidate_file_sha256=historical_candidate.file_sha256,
                canonical_action_source=action_source,
                canonical_adjustment_source=adjustment_source,
                source_sessions=source_sessions,
                required_ids=all_member_ids | {spy_id},
            )
            source_action_fingerprint = split_evidence.source_action_fingerprint
            source_adjustment_fingerprint = (
                split_evidence.source_adjustment_fingerprint
            )
            active_action_keys = set(split_evidence.active_action_keys)
            quarantined_action_keys = set(
                split_evidence.quarantined_action_keys
            )
            unresolved_impact_keys = set(split_evidence.unresolved_impact_keys)
            clear_adjustments = split_evidence.clear_adjustments
            quarantined_adjustment_keys = set(
                split_evidence.quarantined_adjustment_keys
            )
            action_start = split_evidence.action_start
            adjustment_start = split_evidence.adjustment_start
        else:
            source_action_fingerprint = action_source.publication.logical_fingerprint
            source_adjustment_fingerprint = (
                adjustment_source.publication.logical_fingerprint
            )
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
            action_start = action_source.publication.start_date
            adjustment_start = adjustment_source.publication.first_source_session

        evidence_by_family = {item.family: item for item in census.dataset_evidence}
        eod_fingerprint = evidence_by_family["eod_price_bar"].logical_fingerprint
        membership_fingerprint = evidence_by_family[
            "universe_membership"
        ].logical_fingerprint
        if eod_fingerprint is None or membership_fingerprint is None:
            raise QuantResearchFactorQualificationV2CliError(
                "frozen EOD or Membership evidence lacks a logical fingerprint"
            )
        accumulator = QuantResearchFactorQualificationAccumulatorV2(
            chronological_plan_fingerprint=chronological_plan_fingerprint,
            source_population_fingerprint=source_population_fingerprint,
            source_eod_fingerprint=eod_fingerprint,
            source_membership_fingerprint=membership_fingerprint,
            source_action_fingerprint=source_action_fingerprint,
            source_adjustment_fingerprint=source_adjustment_fingerprint,
            calculation_code_sha256=_calculation_code_sha256(),
            diagnostic_code_sha256=_diagnostic_code_sha256(),
            first_source_session=source_sessions[0],
            limitation_codes=LIMITATION_CODES,
        )
        _accumulate_source_interval(
            accumulator=accumulator,
            repository=repository,
            source_sessions=source_sessions,
            signal_sessions=frozenset(ordered_sessions),
            memberships=memberships,
            active_action_keys=active_action_keys,
            quarantined_action_keys=quarantined_action_keys,
            unresolved_impact_keys=unresolved_impact_keys,
            clear_adjustments=clear_adjustments,
            quarantined_adjustment_keys=quarantined_adjustment_keys,
            action_start=action_start,
            adjustment_start=adjustment_start,
            calendar=calendar,
        )
        report = accumulator.build()
        report_path = write_quant_research_factor_qualification_v2(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )
        return report_path, report


def _read_signal_memberships(
    *,
    shadow_root: Path,
    partitions: Mapping[date, Path],
    census,
    ordered_sessions: tuple[date, ...],
) -> tuple[dict[date, tuple[object, ...]], str]:
    census_by_session = {item.session_date: item for item in census.sessions}
    result = {}
    population_records = []
    for session in ordered_sessions:
        membership, membership_fingerprint = _read_membership(
            shadow_root=shadow_root,
            partition=partitions[session],
            census_session=census_by_session[session],
        )
        result[session] = membership
        population_records.append(
            {
                "session": session.isoformat(),
                "membership_fingerprint": membership_fingerprint,
                "instrument_ids": [
                    str(item.instrument_id) for item in membership
                ],
            }
        )
    return result, _fingerprint(population_records)


def _validate_v2_census(census) -> None:
    protocol = quant_research_factor_qualification_protocol_v2()
    calendar = ExchangeCalendar()
    sessions = tuple(item.session_date for item in census.sessions)
    if (
        len(sessions) != protocol.expected_signal_session_count
        or sessions != tuple(sorted(set(sessions)))
        or any(not calendar.is_session(item) for item in sessions)
        or any(
            calendar.next_session(left) != right
            for left, right in zip(sessions, sessions[1:])
        )
        or census.primary_included_count != protocol.expected_signal_path_count
        or census.contains_forward_outcomes
        or census.contains_performance_metrics
        or census.development_authorized
        or census.validation_authorized
        or census.holdout_access_authorized
        or census.candidate_activation_authorized
    ):
        raise QuantResearchFactorQualificationV2CliError(
            "V2 development census boundary differs"
        )


def _chronological_plan_fingerprint(
    *, ordered_sessions: tuple[date, ...], calendar: ExchangeCalendar
) -> str:
    return _fingerprint(
        {
            "contract": "quant-research-factor-qualification-chronology/2.0",
            "calendar_id": "XNYS",
            "calendar_version": calendar.calendar_version,
            "ordered_sessions": [item.isoformat() for item in ordered_sessions],
            "contains_forward_outcomes": False,
        }
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


def _accumulate_source_interval(
    *,
    accumulator: QuantResearchFactorQualificationAccumulatorV2,
    repository: CanonicalEodReadRepository,
    source_sessions: tuple[date, ...],
    signal_sessions: frozenset[date],
    memberships: Mapping[date, tuple[object, ...]],
    active_action_keys: set[tuple[UUID, date]],
    quarantined_action_keys: set[tuple[UUID, date]],
    unresolved_impact_keys: set[tuple[UUID, date]],
    clear_adjustments: Mapping[
        tuple[UUID, date], AdjustmentLedgerEntryV1 | QuantResearchSplitAdjustmentV2
    ],
    quarantined_adjustment_keys: set[tuple[UUID, date]],
    action_start: date,
    adjustment_start: date,
    calendar: ExchangeCalendar,
) -> None:
    all_member_ids = frozenset(
        item.instrument_id
        for records in memberships.values()
        for item in records
    )
    window: deque[tuple[date, dict[UUID, EodMarketBarReadModel]]] = deque(
        maxlen=127
    )
    spy_id: UUID | None = None
    completed = 0
    total = len(signal_sessions)
    for source_session in source_sessions:
        session_read = repository.read_history_sessions((source_session,))[0]
        current_spy = _spy_instrument_id(session_read.bars)
        if spy_id is None:
            spy_id = current_spy
        elif current_spy != spy_id:
            raise QuantResearchFactorQualificationV2CliError(
                "SPY stable instrument identity changes inside V2 source interval"
            )
        retained_ids = all_member_ids | {spy_id}
        filtered = {
            item.instrument_id: item
            for item in session_read.bars
            if item.instrument_id in retained_ids
        }
        window.append((source_session, filtered))
        if source_session not in signal_sessions:
            continue
        if len(window) != 127 or tuple(item[0] for item in window) != tuple(
            (*calendar.sessions_before(source_session, 126), source_session)
        ):
            raise QuantResearchFactorQualificationV2CliError(
                "Factor Catalog V2 source window differs"
            )
        member_ids = tuple(
            sorted(
                (item.instrument_id for item in memberships[source_session]),
                key=str,
            )
        )
        factor_values, reasons = _build_signal_factor_payload(
            source_session=source_session,
            window=tuple(window),
            member_ids=member_ids,
            spy_id=spy_id,
            active_action_keys=active_action_keys,
            quarantined_action_keys=quarantined_action_keys,
            unresolved_impact_keys=unresolved_impact_keys,
            clear_adjustments=clear_adjustments,
            quarantined_adjustment_keys=quarantined_adjustment_keys,
            action_start=action_start,
            adjustment_start=adjustment_start,
        )
        accumulator.add_session(
            as_of_session=source_session,
            instrument_ids=tuple(str(item) for item in member_ids),
            factor_values=factor_values,
            reason_codes=reasons,
        )
        completed += 1
        if completed % 10 == 0 or completed == total:
            print(
                json.dumps(
                    {
                        "status": "running",
                        "completed_signal_sessions": completed,
                        "total_signal_sessions": total,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
            )


def _build_signal_factor_payload(
    *,
    source_session: date,
    window: tuple[tuple[date, dict[UUID, EodMarketBarReadModel]], ...],
    member_ids: tuple[UUID, ...],
    spy_id: UUID,
    active_action_keys: set[tuple[UUID, date]],
    quarantined_action_keys: set[tuple[UUID, date]],
    unresolved_impact_keys: set[tuple[UUID, date]],
    clear_adjustments: Mapping[
        tuple[UUID, date], AdjustmentLedgerEntryV1 | QuantResearchSplitAdjustmentV2
    ],
    quarantined_adjustment_keys: set[tuple[UUID, date]],
    action_start: date,
    adjustment_start: date,
) -> tuple[
    dict[str, np.ndarray],
    dict[str, tuple[tuple[str, ...], ...]],
]:
    sessions = tuple(item[0] for item in window)
    by_session = {session: values for session, values in window}
    required_ids = frozenset((*member_ids, spy_id))
    missing_or_invalid = {
        instrument_id
        for instrument_id in required_ids
        if any(
            instrument_id not in by_session[session]
            or not _valid_factor_bar(by_session[session].get(instrument_id))
            for session in sessions
        )
    }
    hazard_ids, _ = _split_path_status(
        required_ids=required_ids,
        sessions=sessions,
        active_action_keys=active_action_keys,
        quarantined_action_keys=quarantined_action_keys,
        unresolved_impact_keys=unresolved_impact_keys,
        clear_adjustments=clear_adjustments,
        quarantined_adjustment_keys=quarantined_adjustment_keys,
        action_start=action_start,
        adjustment_start=adjustment_start,
    )
    benchmark_reasons = []
    if spy_id in missing_or_invalid:
        benchmark_reasons.append("benchmark_eod_unavailable")
    if spy_id in hazard_ids:
        benchmark_reasons.append("benchmark_split_evidence_quarantined")
    if benchmark_reasons:
        return _all_unavailable_payload(
            member_count=len(member_ids),
            reasons=tuple(sorted(benchmark_reasons)),
        )
    if not member_ids:
        return _all_unavailable_payload(member_count=0, reasons=())

    invalid_reasons: dict[UUID, tuple[str, ...]] = {}
    for instrument_id in member_ids:
        reasons = []
        if instrument_id in missing_or_invalid:
            reasons.append("instrument_eod_unavailable")
        if instrument_id in hazard_ids:
            reasons.append("instrument_split_evidence_quarantined")
        if reasons:
            invalid_reasons[instrument_id] = tuple(sorted(reasons))
    valid_ids = tuple(item for item in member_ids if item not in invalid_reasons)
    benchmark = tuple(
        _adjusted_factor_bar_v2(
            by_session[session][spy_id],
            clear_adjustments.get((spy_id, session)),
        )
        for session in sessions
    )
    matrix = calculate_quant_research_factor_matrix_v2(
        stock_series=tuple(
            tuple(
                _adjusted_factor_bar_v2(
                    by_session[session][instrument_id],
                    clear_adjustments.get((instrument_id, session)),
                )
                for session in sessions
            )
            for instrument_id in valid_ids
        ),
        benchmark_series=benchmark,
    )
    return _merge_matrix_with_quarantines(
        member_ids=member_ids,
        valid_ids=valid_ids,
        invalid_reasons=invalid_reasons,
        matrix=matrix,
    )


def _merge_matrix_with_quarantines(
    *,
    member_ids: tuple[UUID, ...],
    valid_ids: tuple[UUID, ...],
    invalid_reasons: Mapping[UUID, tuple[str, ...]],
    matrix: QuantResearchFactorMatrixV2,
) -> tuple[
    dict[str, np.ndarray],
    dict[str, tuple[tuple[str, ...], ...]],
]:
    if matrix.instrument_count != len(valid_ids):
        raise QuantResearchFactorQualificationV2CliError(
            "Factor Catalog V2 valid matrix count differs"
        )
    member_position = {item: index for index, item in enumerate(member_ids)}
    valid_position = {item: index for index, item in enumerate(valid_ids)}
    values = {}
    reasons = {}
    for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER:
        current = np.full(len(member_ids), np.nan, dtype=np.float64)
        current_reasons: list[tuple[str, ...]] = [()] * len(member_ids)
        for instrument_id in member_ids:
            destination = member_position[instrument_id]
            if instrument_id in invalid_reasons:
                current_reasons[destination] = invalid_reasons[instrument_id]
                continue
            source = valid_position[instrument_id]
            current[destination] = matrix.factor_values[factor_id][source]
            current_reasons[destination] = matrix.reason_codes[factor_id][source]
        values[factor_id] = current
        reasons[factor_id] = tuple(current_reasons)
    return values, reasons


def _all_unavailable_payload(
    *, member_count: int, reasons: tuple[str, ...]
) -> tuple[
    dict[str, np.ndarray],
    dict[str, tuple[tuple[str, ...], ...]],
]:
    if member_count and not reasons:
        raise QuantResearchFactorQualificationV2CliError(
            "unavailable V2 payload lacks reasons"
        )
    return (
        {
            factor_id: np.full(member_count, np.nan, dtype=np.float64)
            for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
        },
        {
            factor_id: tuple(reasons for _ in range(member_count))
            for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
        },
    )


def _spy_instrument_id(bars: tuple[EodMarketBarReadModel, ...]) -> UUID:
    matches = {
        item.instrument_id
        for item in bars
        if item.ticker == "SPY" and item.instrument_type.value == "etf"
    }
    if len(matches) != 1:
        raise QuantResearchFactorQualificationV2CliError(
            "SPY is not uniquely available in the V2 source session"
        )
    return next(iter(matches))


def _valid_factor_bar(bar: EodMarketBarReadModel | None) -> bool:
    return bool(
        _valid_bar(bar)
        and bar is not None
        and bar.low <= min(bar.open, bar.close)
        and bar.high >= max(bar.open, bar.close)
    )


def _adjusted_factor_bar_v2(
    bar: EodMarketBarReadModel,
    adjustment: AdjustmentLedgerEntryV1 | QuantResearchSplitAdjustmentV2 | None,
) -> QuantResearchFactorBarV2:
    price = Decimal("1")
    volume = Decimal("1")
    if adjustment is not None:
        if (
            adjustment.split_price_multiplier_to_basis is None
            or adjustment.split_volume_multiplier_to_basis is None
        ):
            raise QuantResearchFactorQualificationV2CliError(
                "clear split adjustment lacks factors"
            )
        price = adjustment.split_price_multiplier_to_basis
        volume = adjustment.split_volume_multiplier_to_basis
    return QuantResearchFactorBarV2(
        session=bar.session_date,
        open=bar.open * price,
        high=bar.high * price,
        low=bar.low * price,
        close=bar.close * price,
        volume=bar.volume * volume,
    )


def _calculation_code_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    return combined_code_sha256(
        (
            root / "contracts/analytics/v1/quant_research_factor_catalog_v2.py",
            root / "services/quant_research_factor_values_v2.py",
            root / "services/quant_research_factor_matrix_v2.py",
        )
    )


def _diagnostic_code_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    return combined_code_sha256(
        (
            root
            / "contracts/analytics/v1/quant_research_factor_qualification_v2.py",
            root / "services/quant_research_factor_qualification_v2.py",
            root / "services/quant_research_factor_qualification_v2_cli.py",
            root / "services/quant_research_historical_split_extension_v2.py",
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
