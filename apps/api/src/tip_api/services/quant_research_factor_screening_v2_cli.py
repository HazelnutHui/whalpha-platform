"""Dell-only runner for the frozen Factor Catalog V2 Development screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict, deque
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Mapping
from uuid import UUID

from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
    QuantResearchFactorAvailabilityV2,
    QuantResearchFactorValueV2,
    build_quant_research_factor_observation_v2,
    factor_definition_v2_fingerprint,
)
from tip_api.contracts.analytics.v1.quant_research_factor_qualification_v2 import (
    QuantResearchFactorQualificationV2Status,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening import (
    quant_research_factor_screening_protocol_v1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_v2 import (
    QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID,
    quant_research_factor_screening_protocol_v2,
)
from tip_api.contracts.analytics.v1 import StrategyEvaluationSplit
from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
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
from tip_api.persistence.quant_research_factor_diagnostics import (
    REPORT_FILE as COHORT_DIAGNOSTICS_REPORT_FILE,
    read_quant_research_factor_diagnostics,
)
from tip_api.persistence.quant_research_factor_qualification_v2 import (
    REPORT_FILE as QUALIFICATION_REPORT_FILE,
    read_quant_research_factor_qualification_v2,
)
from tip_api.persistence.quant_research_factor_screening_v2 import (
    write_quant_research_factor_screening_v2_report,
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
from tip_api.services.historical_split_adjustment_candidate import (
    read_historical_split_adjustment_candidate,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.quant_research_factor_qualification_v2 import (
    QuantResearchFactorQualificationAccumulatorV2,
    combined_code_sha256,
)
from tip_api.services.quant_research_factor_qualification_v2_cli import (
    _adjusted_factor_bar_v2,
    _build_signal_factor_payload,
    _calculation_code_sha256,
    _chronological_plan_fingerprint,
    _diagnostic_code_sha256,
    _read_signal_memberships,
    _spy_instrument_id,
    _valid_factor_bar,
    _validate_v2_census,
)
from tip_api.services.quant_research_factor_screening_control_v2 import (
    build_quant_research_factor_screening_control_v2,
)
from tip_api.services.quant_research_factor_screening_labels_v2 import (
    build_quant_research_factor_screening_label_v2,
)
from tip_api.services.quant_research_factor_screening_v2 import (
    build_quant_research_factor_screening_report_v2,
)
from tip_api.services.quant_research_factor_values import QuantResearchFactorBar
from tip_api.services.quant_research_historical_split_extension_v2 import (
    build_quant_research_historical_split_evidence_v2,
)
from tip_api.services.strong_leader_pullback_development_dataset_cli import (
    _read_terminal_references,
    _safe_error_detail,
)
from tip_api.services.strong_leader_pullback_development_labels import (
    ReconstructedOutcomeBarV1,
)
from tip_api.services.strong_leader_pullback_diagnostics_cli import (
    _network_disabled,
    _split_path_status,
    _validate_census_sources,
)


_QUANTUM = Decimal("0.0000000001")


class QuantResearchFactorScreeningV2CliError(RuntimeError):
    """Raised when the frozen V2 screen cannot be executed exactly."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the frozen owner-only Factor Catalog V2 Development screen."
    )
    for name in (
        "data-root",
        "membership-shadow-root",
        "development-census-root",
        "split-action-publication-root",
        "split-adjustment-publication-root",
        "historical-split-candidate-root",
        "historical-split-candidate-custody-root",
        "qualification-root",
        "qualification-custody-root",
        "cohort-diagnostics-root",
        "cohort-diagnostics-custody-root",
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
        path, sha256, persistence_status, report = run_factor_screening_v2(
            **vars(args)
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "factor_screening_v2_rejected",
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
                "control_count": report.control_count,
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


def run_factor_screening_v2(
    *,
    data_root: Path,
    membership_shadow_root: Path,
    development_census_root: Path,
    split_action_publication_root: Path,
    split_adjustment_publication_root: Path,
    historical_split_candidate_root: Path,
    historical_split_candidate_custody_root: Path,
    qualification_root: Path,
    qualification_custody_root: Path,
    cohort_diagnostics_root: Path,
    cohort_diagnostics_custody_root: Path,
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
        _validate_run_identity(created_at, implementation_revision)
        _validate_repository_revision(implementation_revision)
        protocol = quant_research_factor_screening_protocol_v2()
        canonical_root = _validated_data_root(data_root)
        shadow_root = _validated_shadow_root(membership_shadow_root)
        qualification = read_quant_research_factor_qualification_v2(
            output_root=qualification_root,
            output_custody_root=qualification_custody_root,
        )
        if (
            qualification.logical_fingerprint
            != protocol.source_qualification_fingerprint
            or _file_sha256(qualification_root / QUALIFICATION_REPORT_FILE)
            != protocol.source_qualification_sha256
            or qualification.status
            is not QuantResearchFactorQualificationV2Status.READY_FOR_SCREENING_PROTOCOL_REVIEW
            or qualification.calculation_code_sha256 != _calculation_code_sha256()
            or qualification.diagnostic_code_sha256 != _diagnostic_code_sha256()
        ):
            raise QuantResearchFactorScreeningV2CliError(
                "V2 source qualification or implementation identity differs"
            )

        census = read_development_coverage_census(
            output_root=development_census_root
        )
        _validate_v2_census(census)
        canonical_action = read_canonical_split_action_publication(
            data_root=canonical_root,
            publication_root=split_action_publication_root,
        )
        canonical_adjustment = read_canonical_split_adjustment_publication(
            data_root=canonical_root,
            publication_root=split_adjustment_publication_root,
        )
        _validate_census_sources(
            census=census,
            action_fingerprint=canonical_action.publication.logical_fingerprint,
            adjustment_fingerprint=canonical_adjustment.publication.logical_fingerprint,
        )
        cohort_protocol = quant_research_factor_screening_protocol_v1()
        cohort_diagnostics = read_quant_research_factor_diagnostics(
            output_root=cohort_diagnostics_root,
            output_custody_root=cohort_diagnostics_custody_root,
        )
        if (
            cohort_diagnostics.logical_fingerprint
            != cohort_protocol.source_diagnostics_fingerprint
            or _file_sha256(
                cohort_diagnostics_root / COHORT_DIAGNOSTICS_REPORT_FILE
            )
            != cohort_protocol.source_diagnostics_sha256
            or cohort_diagnostics.source_eod_fingerprint
            != qualification.source_eod_fingerprint
            or cohort_diagnostics.source_adjustment_fingerprint
            != canonical_adjustment.publication.logical_fingerprint
        ):
            raise QuantResearchFactorScreeningV2CliError(
                "V2 declared cohort diagnostics or lineage differs"
            )
        calendar = ExchangeCalendar()
        ordered_sessions = tuple(item.session_date for item in census.sessions)
        plan = build_candidate_strategy_chronological_plan(
            ordered_sessions=ordered_sessions,
            calendar=calendar,
        )
        if (
            plan.logical_fingerprint != protocol.chronological_plan_fingerprint
            or _chronological_plan_fingerprint(
                ordered_sessions=ordered_sessions,
                calendar=calendar,
            )
            != qualification.chronological_plan_fingerprint
        ):
            raise QuantResearchFactorScreeningV2CliError(
                "V2 screening chronology differs"
            )
        declared_development_sessions = _declared_development_sessions(
            diagnostics=cohort_diagnostics,
            plan=plan,
        )
        partitions = _discover_membership_partitions(shadow_root)
        if tuple(sorted(partitions)) != ordered_sessions:
            raise QuantResearchFactorScreeningV2CliError(
                "V2 Membership partitions differ from the frozen plan"
            )
        memberships, population_fingerprint = _read_signal_memberships(
            shadow_root=shadow_root,
            partitions=partitions,
            census=census,
            ordered_sessions=ordered_sessions,
        )
        if population_fingerprint != qualification.source_population_fingerprint:
            raise QuantResearchFactorScreeningV2CliError(
                "V2 screening population differs from qualification"
            )

        repository = CanonicalEodReadRepository(canonical_root)
        source_sessions = (
            *calendar.sessions_before(ordered_sessions[0], 126),
            *ordered_sessions,
        )
        available_sessions = repository.list_session_index()
        if not set(source_sessions).issubset(available_sessions):
            raise QuantResearchFactorScreeningV2CliError(
                "canonical EOD does not cover the V2 factor interval"
            )
        member_ids = frozenset(
            item.instrument_id
            for records in memberships.values()
            for item in records
        )
        first_read = repository.read_history_sessions((source_sessions[0],))[0]
        spy_id = _spy_instrument_id(first_read.bars)
        historical_candidate = read_historical_split_adjustment_candidate(
            output_root=historical_split_candidate_root,
            output_custody_root=historical_split_candidate_custody_root,
        )
        factor_split = build_quant_research_historical_split_evidence_v2(
            candidate=historical_candidate.candidate,
            candidate_file_sha256=historical_candidate.file_sha256,
            canonical_action_source=canonical_action,
            canonical_adjustment_source=canonical_adjustment,
            source_sessions=source_sessions,
            required_ids=member_ids | {spy_id},
        )
        if (
            factor_split.source_action_fingerprint
            != qualification.source_action_fingerprint
            or factor_split.source_adjustment_fingerprint
            != qualification.source_adjustment_fingerprint
        ):
            raise QuantResearchFactorScreeningV2CliError(
                "V2 private factor split evidence differs from qualification"
            )

        control_evidence = _canonical_split_evidence(
            canonical_action=canonical_action,
            canonical_adjustment=canonical_adjustment,
        )
        observations, controls, replayed_qualification = (
            _build_factor_observations_and_controls(
                repository=repository,
                source_sessions=source_sessions,
                memberships=memberships,
                plan=plan,
                qualification=qualification,
                factor_split=factor_split,
                control_evidence=control_evidence,
                spy_id=spy_id,
                calendar=calendar,
                declared_development_sessions=declared_development_sessions,
            )
        )
        if replayed_qualification != qualification:
            raise QuantResearchFactorScreeningV2CliError(
                "V2 factor observations do not exactly replay qualification"
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
        labels = _build_factor_labels_v2(
            repository=repository,
            observations=observations,
            plan=plan,
            terminal_references=terminal_references,
            canonical_action=canonical_action,
            canonical_adjustment=canonical_adjustment,
            canonical_evidence=control_evidence,
            spy_id=spy_id,
        )
        report = build_quant_research_factor_screening_report_v2(
            observations=observations,
            controls=controls,
            labels=labels,
            implementation_revision=implementation_revision,
            created_at=created_at.astimezone(UTC),
            source_eod_fingerprint=qualification.source_eod_fingerprint,
            source_membership_fingerprint=qualification.source_membership_fingerprint,
            source_cohort_diagnostics_fingerprint=(
                cohort_diagnostics.logical_fingerprint
            ),
            source_cohort_diagnostics_sha256=(
                cohort_protocol.source_diagnostics_sha256
            ),
            source_cohort_membership_fingerprint=(
                cohort_diagnostics.source_membership_fingerprint
            ),
            factor_source_action_fingerprint=qualification.source_action_fingerprint,
            factor_source_adjustment_fingerprint=(
                qualification.source_adjustment_fingerprint
            ),
            control_source_action_fingerprint=(
                canonical_action.publication.logical_fingerprint
            ),
            control_source_adjustment_fingerprint=(
                canonical_adjustment.publication.logical_fingerprint
            ),
            label_source_action_fingerprint=(
                canonical_action.publication.logical_fingerprint
            ),
            label_source_adjustment_fingerprint=(
                canonical_adjustment.publication.logical_fingerprint
            ),
            factor_calculation_code_sha256=_calculation_code_sha256(),
            control_calculation_code_sha256=_control_code_sha256(),
            label_code_sha256=_label_code_sha256(),
            screening_code_sha256=_screening_code_sha256(),
        )
        path, sha256, status = write_quant_research_factor_screening_v2_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )
        return path, sha256, status, report


def _canonical_split_evidence(*, canonical_action, canonical_adjustment) -> dict:
    return {
        "action_fingerprint": canonical_action.publication.logical_fingerprint,
        "adjustment_fingerprint": canonical_adjustment.publication.logical_fingerprint,
        "active_action_keys": {
            (item.instrument_id, item.effective_date)
            for item in canonical_action.actions
            if item.record_status is CorporateActionRecordStatus.ACTIVE
        },
        "quarantined_action_keys": {
            (item.instrument_id, item.effective_date)
            for item in canonical_action.actions
            if item.record_status is not CorporateActionRecordStatus.ACTIVE
        },
        "unresolved_impact_keys": {
            (item.instrument_id, effective_date)
            for item in canonical_action.publication.possible_unresolved_impacts
            for effective_date in item.effective_dates
        },
        "clear_adjustments": {
            (item.instrument_id, item.source_session): item
            for item in canonical_adjustment.records
            if item.split_adjustment_status is AdjustmentAvailabilityStatus.CLEAR
        },
        "quarantined_adjustment_keys": {
            (item.instrument_id, item.source_session)
            for item in canonical_adjustment.records
            if item.split_adjustment_status is not AdjustmentAvailabilityStatus.CLEAR
        },
        "action_start": canonical_action.publication.start_date,
        "adjustment_start": canonical_adjustment.publication.first_source_session,
    }


def _build_factor_observations_and_controls(
    *,
    repository,
    source_sessions,
    memberships,
    plan,
    qualification,
    factor_split,
    control_evidence,
    spy_id,
    calendar,
    declared_development_sessions,
):
    protocol = quant_research_factor_screening_protocol_v2()
    assignment_by_session = {item.session: item for item in plan.assignments}
    signal_sessions = frozenset(plan.ordered_sessions)
    all_member_ids = frozenset(
        item.instrument_id for records in memberships.values() for item in records
    )
    accumulator = QuantResearchFactorQualificationAccumulatorV2(
        chronological_plan_fingerprint=qualification.chronological_plan_fingerprint,
        source_population_fingerprint=qualification.source_population_fingerprint,
        source_eod_fingerprint=qualification.source_eod_fingerprint,
        source_membership_fingerprint=qualification.source_membership_fingerprint,
        source_action_fingerprint=qualification.source_action_fingerprint,
        source_adjustment_fingerprint=qualification.source_adjustment_fingerprint,
        calculation_code_sha256=qualification.calculation_code_sha256,
        diagnostic_code_sha256=qualification.diagnostic_code_sha256,
        first_source_session=qualification.first_source_session,
        limitation_codes=qualification.limitation_codes,
    )
    window = deque(maxlen=127)
    observations = []
    controls = []
    retained_sessions = 0
    for source_index, source_session in enumerate(source_sessions, start=1):
        session_read = repository.read_history_sessions((source_session,))[0]
        current_spy = _spy_instrument_id(session_read.bars)
        if current_spy != spy_id:
            raise QuantResearchFactorScreeningV2CliError(
                "SPY stable identity changes inside the V2 source interval"
            )
        retained_ids = all_member_ids | {spy_id}
        current = {
            item.instrument_id: item
            for item in session_read.bars
            if item.instrument_id in retained_ids
        }
        window.append((source_session, current))
        if source_session not in signal_sessions:
            continue
        if len(window) != 127 or tuple(item[0] for item in window) != tuple(
            (*calendar.sessions_before(source_session, 126), source_session)
        ):
            raise QuantResearchFactorScreeningV2CliError(
                "V2 factor source window differs"
            )
        ordered_members = tuple(
            sorted(
                (item.instrument_id for item in memberships[source_session]),
                key=str,
            )
        )
        values, reasons = _build_signal_factor_payload(
            source_session=source_session,
            window=tuple(window),
            member_ids=ordered_members,
            spy_id=spy_id,
            active_action_keys=set(factor_split.active_action_keys),
            quarantined_action_keys=set(factor_split.quarantined_action_keys),
            unresolved_impact_keys=set(factor_split.unresolved_impact_keys),
            clear_adjustments=factor_split.clear_adjustments,
            quarantined_adjustment_keys=set(
                factor_split.quarantined_adjustment_keys
            ),
            action_start=factor_split.action_start,
            adjustment_start=factor_split.adjustment_start,
        )
        accumulator.add_session(
            as_of_session=source_session,
            instrument_ids=tuple(str(item) for item in ordered_members),
            factor_values=values,
            reason_codes=reasons,
        )
        assignment = assignment_by_session[source_session]
        if _is_declared_development_session(
            assignment=assignment,
            source_session=source_session,
            declared_development_sessions=declared_development_sessions,
        ):
            retained_sessions += 1
            for position, instrument_id in enumerate(ordered_members):
                factor_values = tuple(
                    _factor_value(
                        factor_id=factor_id,
                        value=float(values[factor_id][position]),
                        reasons=reasons[factor_id][position],
                    )
                    for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
                )
                observation = build_quant_research_factor_observation_v2(
                    catalog_fingerprint=protocol.catalog_fingerprint,
                    as_of_session=source_session,
                    instrument_id=instrument_id,
                    display_ticker=(
                        current[instrument_id].ticker
                        if instrument_id in current
                        else None
                    ),
                    source_min_session=window[0][0],
                    source_max_session=source_session,
                    source_eod_fingerprint=qualification.source_eod_fingerprint,
                    source_adjustment_fingerprint=(
                        qualification.source_adjustment_fingerprint
                    ),
                    factor_values=factor_values,
                )
                observations.append(observation)
                controls.append(
                    _build_control(
                        observation=observation,
                        window=tuple(window),
                        instrument_id=instrument_id,
                        spy_id=spy_id,
                        evidence=control_evidence,
                        source_eod_fingerprint=qualification.source_eod_fingerprint,
                        source_action_fingerprint=(
                            _evidence_fingerprint(
                                control_evidence, "action"
                            )
                        ),
                        source_adjustment_fingerprint=(
                            _evidence_fingerprint(
                                control_evidence, "adjustment"
                            )
                        ),
                    )
                )
        if source_index % 25 == 0 or source_session == source_sessions[-1]:
            print(
                json.dumps(
                    {
                        "status": "replaying_v2_qualification_and_building_controls",
                        "completed_source_sessions": source_index,
                        "retained_signal_sessions": retained_sessions,
                        "retained_observation_count": len(observations),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
            )
    ordered_observations = tuple(
        sorted(observations, key=lambda item: (item.as_of_session, str(item.instrument_id)))
    )
    ordered_controls = tuple(
        sorted(controls, key=lambda item: (item.signal_session, str(item.instrument_id)))
    )
    if (
        retained_sessions != protocol.development_declared_session_count
        or len(ordered_observations) != protocol.development_declared_path_count
        or len(ordered_controls) != len(ordered_observations)
        or ordered_observations[0].as_of_session
        != protocol.first_development_signal_session
        or ordered_observations[-1].as_of_session
        != protocol.last_development_signal_session
    ):
        raise QuantResearchFactorScreeningV2CliError(
            "V2 Development cohort differs from the frozen protocol"
        )
    return ordered_observations, ordered_controls, accumulator.build()


def _declared_development_sessions(*, diagnostics, plan) -> frozenset[date]:
    """Reconstruct the exact V1-complete cohort reused by V2."""

    protocol = quant_research_factor_screening_protocol_v2()
    availability = {
        item.as_of_session: item
        for item in diagnostics.session_availability
        if item.factor_id == QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID
    }
    if set(availability) != set(plan.ordered_sessions):
        raise QuantResearchFactorScreeningV2CliError(
            "V2 cohort diagnostics do not cover the frozen chronology"
        )
    selected = tuple(
        assignment.session
        for assignment in plan.assignments
        if assignment.raw_split is StrategyEvaluationSplit.DEVELOPMENT
        and assignment.usable_for_signal_evaluation
        and availability[assignment.session].expected_count > 0
        and availability[assignment.session].available_count
        == availability[assignment.session].expected_count
    )
    if (
        len(selected) != protocol.development_declared_session_count
        or selected[0] != protocol.first_development_signal_session
        or selected[-1] != protocol.last_development_signal_session
    ):
        raise QuantResearchFactorScreeningV2CliError(
            "V2 cohort diagnostics do not reproduce the declared sessions"
        )
    return frozenset(selected)


def _is_declared_development_session(
    *, assignment, source_session, declared_development_sessions
) -> bool:
    """Retain only the exact preregistered V1-complete Development cohort."""

    return bool(
        assignment.raw_split is StrategyEvaluationSplit.DEVELOPMENT
        and assignment.usable_for_signal_evaluation
        and source_session in declared_development_sessions
    )


def _evidence_fingerprint(evidence: Mapping[str, object], family: str) -> str:
    key = f"{family}_fingerprint"
    value = evidence.get(key)
    if not isinstance(value, str):
        raise QuantResearchFactorScreeningV2CliError(
            f"canonical {family} fingerprint is absent"
        )
    return value


def _factor_value(*, factor_id: str, value: float, reasons: tuple[str, ...]):
    available = math.isfinite(value)
    return QuantResearchFactorValueV2(
        factor_id=factor_id,
        factor_definition_fingerprint=factor_definition_v2_fingerprint(factor_id),
        availability=(
            QuantResearchFactorAvailabilityV2.AVAILABLE
            if available
            else QuantResearchFactorAvailabilityV2.UNAVAILABLE
        ),
        value=_string(value) if available else None,
        reason_codes=tuple(sorted(set(reasons))),
    )


def _build_control(
    *,
    observation,
    window,
    instrument_id,
    spy_id,
    evidence,
    source_eod_fingerprint,
    source_action_fingerprint,
    source_adjustment_fingerprint,
):
    control_window = tuple(window[-21:])
    sessions = tuple(item[0] for item in control_window)
    by_session = {session: values for session, values in control_window}
    required = frozenset((instrument_id, spy_id))
    hazard, _ = _split_path_status(
        required_ids=required,
        sessions=sessions,
        active_action_keys=evidence["active_action_keys"],
        quarantined_action_keys=evidence["quarantined_action_keys"],
        unresolved_impact_keys=evidence["unresolved_impact_keys"],
        clear_adjustments=evidence["clear_adjustments"],
        quarantined_adjustment_keys=evidence["quarantined_adjustment_keys"],
        action_start=evidence["action_start"],
        adjustment_start=evidence["adjustment_start"],
    )
    reasons = []
    if any(
        instrument_id not in values
        or not _valid_factor_bar(values.get(instrument_id))
        for _, values in control_window
    ):
        reasons.append("control_instrument_eod_unavailable")
    if any(
        spy_id not in values or not _valid_factor_bar(values.get(spy_id))
        for _, values in control_window
    ):
        reasons.append("control_benchmark_eod_unavailable")
    if instrument_id in hazard:
        reasons.append("control_instrument_split_evidence_quarantined")
    if spy_id in hazard:
        reasons.append("control_benchmark_split_evidence_quarantined")
    common = {
        "observation_fingerprint": observation.logical_fingerprint,
        "signal_session": observation.as_of_session,
        "instrument_id": instrument_id,
        "source_min_session": sessions[0],
        "source_eod_fingerprint": source_eod_fingerprint,
        "source_action_fingerprint": source_action_fingerprint,
        "source_adjustment_fingerprint": source_adjustment_fingerprint,
    }
    if reasons:
        return build_quant_research_factor_screening_control_v2(
            **common,
            unavailable_reason_codes=tuple(sorted(reasons)),
        )
    stock = tuple(
        _control_bar(
            by_session[session][instrument_id],
            evidence["clear_adjustments"].get((instrument_id, session)),
        )
        for session in sessions
    )
    benchmark = tuple(
        _control_bar(
            by_session[session][spy_id],
            evidence["clear_adjustments"].get((spy_id, session)),
        )
        for session in sessions
    )
    return build_quant_research_factor_screening_control_v2(
        **common,
        stock_series=stock,
        benchmark_series=benchmark,
    )


def _control_bar(bar, adjustment) -> QuantResearchFactorBar:
    adjusted = _adjusted_factor_bar_v2(bar, adjustment)
    return QuantResearchFactorBar(
        session=adjusted.session,
        open=adjusted.open,
        high=adjusted.high,
        low=adjusted.low,
        close=adjusted.close,
        volume=adjusted.volume,
    )


def _build_factor_labels_v2(
    *,
    repository,
    observations,
    plan,
    terminal_references,
    canonical_action,
    canonical_adjustment,
    canonical_evidence,
    spy_id,
):
    by_signal = defaultdict(list)
    for observation in observations:
        by_signal[observation.as_of_session].append(observation)
    plan_index = {session: index for index, session in enumerate(plan.ordered_sessions)}
    path_by_signal = {}
    required_ids_by_session = defaultdict(set)
    for signal_session, items in by_signal.items():
        position = plan_index[signal_session]
        path = plan.ordered_sessions[position + 1 : position + 6]
        if len(path) != 5:
            raise QuantResearchFactorScreeningV2CliError(
                "V2 label path is not mature inside the frozen plan"
            )
        path_by_signal[signal_session] = path
        ids = {item.instrument_id for item in items}
        for session in path:
            required_ids_by_session[session].update(ids)
    outcome_sessions = tuple(sorted(required_ids_by_session))
    if not set(outcome_sessions).issubset(repository.list_session_index()):
        raise QuantResearchFactorScreeningV2CliError(
            "canonical EOD lacks a V2 outcome session"
        )
    bars_by_session = {}
    integrity_by_session = {}
    for index, session in enumerate(outcome_sessions, start=1):
        read = repository.read_history_sessions((session,))[0]
        current_spy = _spy_instrument_id(read.bars)
        if current_spy != spy_id:
            raise QuantResearchFactorScreeningV2CliError(
                "SPY identity differs in a V2 outcome session"
            )
        required = required_ids_by_session[session] | {spy_id}
        bars_by_session[session] = {
            item.instrument_id: item
            for item in read.bars
            if item.instrument_id in required
        }
        integrity_by_session[session] = read.integrity
        if index % 25 == 0 or index == len(outcome_sessions):
            print(
                json.dumps(
                    {
                        "status": "reading_v2_development_outcomes",
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
    for session_index, signal_session in enumerate(sorted(by_signal), start=1):
        path5 = path_by_signal[signal_session]
        for observation in by_signal[signal_session]:
            terminal = terminal_by_id.get(observation.instrument_id)
            for horizon in (1, 3, 5):
                path = path5[:horizon]
                target = tuple(
                    bars_by_session[session].get(observation.instrument_id)
                    for session in path
                )
                benchmark = tuple(
                    bars_by_session[session].get(spy_id) for session in path
                )
                if any(item is None or not _valid_screening_bar(item) for item in benchmark):
                    raise QuantResearchFactorScreeningV2CliError(
                        "SPY V2 outcome path is incomplete or invalid"
                    )
                hazard, _ = _split_path_status(
                    required_ids=frozenset((observation.instrument_id, spy_id)),
                    sessions=(signal_session, *path),
                    active_action_keys=canonical_evidence["active_action_keys"],
                    quarantined_action_keys=canonical_evidence[
                        "quarantined_action_keys"
                    ],
                    unresolved_impact_keys=canonical_evidence[
                        "unresolved_impact_keys"
                    ],
                    clear_adjustments=canonical_evidence["clear_adjustments"],
                    quarantined_adjustment_keys=canonical_evidence[
                        "quarantined_adjustment_keys"
                    ],
                    action_start=canonical_evidence["action_start"],
                    adjustment_start=canonical_evidence["adjustment_start"],
                )
                reasons = set()
                if observation.instrument_id in hazard:
                    reasons.add("target_split_evidence_quarantined")
                if spy_id in hazard:
                    reasons.add("benchmark_split_evidence_quarantined")
                no_next_open_terminal_supported = bool(
                    target[0] is None
                    and terminal is not None
                    and terminal.instrument_id == observation.instrument_id
                    and terminal.last_observed_eod_session < path[0]
                )
                if target[0] is None and not no_next_open_terminal_supported:
                    reasons.add("missing_next_session_eod_without_terminal_evidence")
                for source_session, bar in zip(path, target, strict=True):
                    if bar is not None and not _valid_screening_bar(bar):
                        reasons.add("invalid_target_eod_bar")
                if target[-1] is None and not no_next_open_terminal_supported and (
                    terminal is None
                    or terminal.instrument_id != observation.instrument_id
                    or path[-1] < terminal.first_absent_exchange_session
                    or path[0] > terminal.last_observed_eod_session
                ):
                    reasons.add("missing_exit_without_terminal_reference")
                if terminal is not None and any(
                    bar is None and source_session <= terminal.last_observed_eod_session
                    for source_session, bar in zip(path, target, strict=True)
                ):
                    reasons.add("missing_eod_before_terminal_boundary")
                adjusted_target = tuple(
                    _outcome_bar(
                        bar,
                        canonical_evidence["clear_adjustments"].get(
                            (observation.instrument_id, source_session)
                        ),
                    )
                    for source_session, bar in zip(path, target, strict=True)
                )
                adjusted_benchmark = tuple(
                    _outcome_bar(
                        bar,
                        canonical_evidence["clear_adjustments"].get(
                            (spy_id, source_session)
                        ),
                    )
                    for source_session, bar in zip(path, benchmark, strict=True)
                )
                labels.append(
                    build_quant_research_factor_screening_label_v2(
                        observation_fingerprint=observation.logical_fingerprint,
                        signal_session=signal_session,
                        instrument_id=observation.instrument_id,
                        display_ticker=observation.display_ticker,
                        expected_path_sessions=path,
                        split_basis_session=canonical_adjustment.publication.basis_session,
                        instrument_bars=adjusted_target,
                        benchmark_bars=tuple(
                            item for item in adjusted_benchmark if item is not None
                        ),
                        source_eod_fingerprint=_fingerprint(
                            {
                                "instrument_id": str(observation.instrument_id),
                                "sessions": [
                                    integrity_by_session[item].model_dump(mode="json")
                                    for item in path
                                ],
                            }
                        ),
                        source_action_fingerprint=(
                            canonical_action.publication.logical_fingerprint
                        ),
                        source_adjustment_fingerprint=(
                            canonical_adjustment.publication.logical_fingerprint
                        ),
                        terminal_reference=terminal,
                        unavailable_reason_codes=tuple(sorted(reasons)),
                    )
                )
        if session_index % 10 == 0 or session_index == len(by_signal):
            print(
                json.dumps(
                    {
                        "status": "constructing_v2_screening_labels",
                        "completed_signal_sessions": session_index,
                        "total_signal_sessions": len(by_signal),
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


def _outcome_bar(bar, adjustment) -> ReconstructedOutcomeBarV1 | None:
    if bar is None:
        return None
    price = Decimal("1")
    if adjustment is not None:
        price = adjustment.split_price_multiplier_to_basis
        if price is None:
            raise QuantResearchFactorScreeningV2CliError(
                "clear V2 outcome adjustment lacks a price factor"
            )
    return ReconstructedOutcomeBarV1(
        session=bar.session_date,
        open=bar.open * price,
        high=bar.high * price,
        low=bar.low * price,
        close=bar.close * price,
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
        raise QuantResearchFactorScreeningV2CliError(
            "V2 factor-screening creation time must be timezone-aware"
        )
    if len(implementation_revision) != 40 or any(
        character not in "0123456789abcdef" for character in implementation_revision
    ):
        raise QuantResearchFactorScreeningV2CliError(
            "V2 implementation revision must be one exact Git commit"
        )


def _validate_repository_revision(implementation_revision: str) -> None:
    repo_root = Path(__file__).resolve().parents[5]
    revision = subprocess.run(
        ("git", "-C", str(repo_root), "rev-parse", "HEAD"),
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        (
            "git",
            "-C",
            str(repo_root),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--ignore-submodules=none",
        ),
        check=False,
        capture_output=True,
        text=True,
    )
    if (
        revision.returncode != 0
        or status.returncode != 0
        or revision.stdout.strip() != implementation_revision
        or status.stdout.strip()
    ):
        raise QuantResearchFactorScreeningV2CliError(
            "V2 screen requires the exact clean committed implementation"
        )


def _control_code_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    return combined_code_sha256(
        (
            root / "contracts/analytics/v1/quant_research_factor_catalog.py",
            root
            / "contracts/analytics/v1/quant_research_factor_screening_result_v2.py",
            root / "services/quant_research_factor_values.py",
            root / "services/quant_research_factor_screening_control_v2.py",
        )
    )


def _label_code_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    return combined_code_sha256(
        (
            root
            / "contracts/analytics/v1/quant_research_factor_screening_result_v2.py",
            root / "services/quant_research_factor_screening_labels_v2.py",
        )
    )


def _screening_code_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    return combined_code_sha256(
        (
            root
            / "contracts/analytics/v1/quant_research_factor_screening_v2.py",
            root
            / "contracts/analytics/v1/quant_research_factor_screening_result_v2.py",
            root / "services/quant_research_factor_screening_v2.py",
            root / "services/quant_research_factor_screening_v2_cli.py",
        )
    )


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
        ).encode("utf-8")
    ).hexdigest()


def _string(value: float) -> str:
    parsed = Decimal(str(value)).quantize(_QUANTUM)
    if parsed == 0:
        parsed = Decimal("0").quantize(_QUANTUM)
    return format(parsed, "f")


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("created-at must be timezone-aware")
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    raise SystemExit(main())
