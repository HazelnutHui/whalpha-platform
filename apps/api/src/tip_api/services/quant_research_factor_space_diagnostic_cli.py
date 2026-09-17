"""Network-disabled workstation runner for the U.S. factor-space diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import deque
from datetime import date
from pathlib import Path

import numpy as np

from tip_api.contracts.analytics.v1.candidate_strategy_development_coverage import (
    STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY,
    STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE,
)
from tip_api.contracts.analytics.v1.quant_research_factor_catalog import (
    QUANT_RESEARCH_FACTOR_ORDER,
    quant_research_factor_catalog_v1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
    quant_research_factor_catalog_v2,
)
from tip_api.contracts.analytics.v1.quant_research_factor_space_diagnostic import (
    FactorSpacePanelKind,
    FactorSpaceSourceBindingV1,
)
from tip_api.contracts.analytics.v1.quant_research_market_state_vector import (
    QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER,
    quant_research_market_state_vector_definition_v1,
)
from tip_api.contracts.market_data.v1 import UniverseMembershipDisposition
from tip_api.persistence.parquet.canonical_corporate_action import (
    read_canonical_split_action_publication,
)
from tip_api.persistence.parquet.canonical_split_adjustment import (
    read_canonical_split_adjustment_publication,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.quant_research_factor_diagnostics import (
    REPORT_FILE as V1_REPORT_FILE,
    read_quant_research_factor_diagnostics,
)
from tip_api.persistence.quant_research_factor_qualification_v2 import (
    REPORT_FILE as V2_REPORT_FILE,
    read_quant_research_factor_qualification_v2,
)
from tip_api.persistence.quant_research_factor_space_diagnostic import (
    write_factor_space_diagnostic,
)
from tip_api.persistence.quant_research_market_state_qualification import (
    REPORT_FILE as STATE_REPORT_FILE,
    read_quant_research_market_state_qualification_v1,
)
from tip_api.services.historical_split_adjustment_candidate import (
    read_historical_split_adjustment_candidate,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.quant_research_campaign_three_input_qualification import (
    _development_sessions,
)
from tip_api.services.quant_research_factor_diagnostics_cli import (
    _build_session_observations,
)
from tip_api.services.quant_research_factor_qualification_v2_cli import (
    _build_signal_factor_payload,
    _spy_instrument_id,
)
from tip_api.services.quant_research_factor_space_diagnostic import (
    build_factor_space_diagnostic_report,
    build_factor_space_panel,
)
from tip_api.services.quant_research_historical_split_extension_v2 import (
    build_quant_research_historical_split_evidence_v2,
)
from tip_api.services.research_universe_membership_canonical import (
    read_canonical_research_universe_membership,
)
from tip_api.services.strong_leader_pullback_diagnostics_cli import _network_disabled


class FactorSpaceDiagnosticCliError(RuntimeError):
    """Raised when frozen outcome-blind sources cannot be reconciled."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "data-root",
        "split-action-publication-root",
        "split-adjustment-publication-root",
        "historical-split-candidate-root",
        "historical-split-candidate-custody-root",
        "v1-diagnostics-root",
        "v1-diagnostics-custody-root",
        "v2-qualification-root",
        "v2-qualification-custody-root",
        "market-state-root",
        "market-state-custody-root",
        "output-root",
        "output-custody-root",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        path, report = run_factor_space_diagnostic(**vars(args))
    except Exception as exc:
        print(json.dumps({
            "status": "rejected",
            "reason_code": "factor_space_diagnostic_rejected",
            "error_type": type(exc).__name__,
            "error_detail": str(exc)[:500],
            "external_request_count": 0,
            "development_outcome_read_count": 0,
            "validation_read_count": 0,
            "holdout_read_count": 0,
            "canonical_data_write_count": 0,
            "production_write_count": 0,
        }, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps({
        "status": "completed",
        "report_path": str(path),
        "logical_fingerprint": report.logical_fingerprint,
        "security_rows": report.panels[0].row_count,
        "security_complete_cases": report.panels[0].complete_case_count,
        "security_effective_dimension": report.panels[0].dimension.participation_ratio,
        "market_state_rows": report.panels[1].row_count,
        "market_state_complete_cases": report.panels[1].complete_case_count,
        "market_state_effective_dimension": report.panels[1].dimension.participation_ratio,
        "external_request_count": 0,
        "development_outcome_read_count": 0,
        "validation_read_count": 0,
        "holdout_read_count": 0,
        "canonical_data_write_count": 0,
        "production_write_count": 0,
    }, sort_keys=True, separators=(",", ":")))
    return 0


def run_factor_space_diagnostic(
    *,
    data_root: Path,
    split_action_publication_root: Path,
    split_adjustment_publication_root: Path,
    historical_split_candidate_root: Path,
    historical_split_candidate_custody_root: Path,
    v1_diagnostics_root: Path,
    v1_diagnostics_custody_root: Path,
    v2_qualification_root: Path,
    v2_qualification_custody_root: Path,
    market_state_root: Path,
    market_state_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
):
    with _network_disabled():
        v1 = read_quant_research_factor_diagnostics(
            output_root=v1_diagnostics_root,
            output_custody_root=v1_diagnostics_custody_root,
        )
        v2 = read_quant_research_factor_qualification_v2(
            output_root=v2_qualification_root,
            output_custody_root=v2_qualification_custody_root,
        )
        state = read_quant_research_market_state_qualification_v1(
            output_root=market_state_root,
            output_custody_root=market_state_custody_root,
        )
        _validate_source_reports(v1, v2, state)
        development_sessions = _development_sessions(v1)
        memberships = _read_memberships(data_root, development_sessions, state)
        all_member_ids = frozenset(
            record.instrument_id
            for records in memberships.values()
            for record in records
        )

        calendar = ExchangeCalendar()
        source_sessions = (
            *calendar.sessions_before(development_sessions[0], 126),
            *calendar.sessions_in_range(
                development_sessions[0], development_sessions[-1]
            ),
        )
        repository = CanonicalEodReadRepository(data_root)
        if not set(source_sessions).issubset(repository.list_session_index()):
            raise FactorSpaceDiagnosticCliError("factor source interval is incomplete")
        spy_id = _spy_instrument_id(
            repository.read_history_sessions((source_sessions[0],))[0].bars
        )
        historical_candidate = read_historical_split_adjustment_candidate(
            output_root=historical_split_candidate_root,
            output_custody_root=historical_split_candidate_custody_root,
        )
        action_source = read_canonical_split_action_publication(
            data_root=data_root,
            publication_root=split_action_publication_root,
        )
        adjustment_source = read_canonical_split_adjustment_publication(
            data_root=data_root,
            publication_root=split_adjustment_publication_root,
        )
        if (
            action_source.publication.logical_fingerprint
            != v1.source_action_fingerprint
            or adjustment_source.publication.logical_fingerprint
            != v1.source_adjustment_fingerprint
        ):
            raise FactorSpaceDiagnosticCliError(
                "canonical split publications differ from V1 qualification"
            )
        split = build_quant_research_historical_split_evidence_v2(
            candidate=historical_candidate.candidate,
            candidate_file_sha256=historical_candidate.file_sha256,
            canonical_action_source=action_source,
            canonical_adjustment_source=adjustment_source,
            source_sessions=source_sessions,
            required_ids=all_member_ids | {spy_id},
        )
        stock_values, group_keys = _stock_panel(
            repository=repository,
            source_sessions=source_sessions,
            development_sessions=frozenset(development_sessions),
            memberships=memberships,
            split=split,
            spy_id=spy_id,
            all_member_ids=all_member_ids,
            calendar=calendar,
            v1=v1,
        )
        stock_catalog = quant_research_factor_catalog_v1()
        stock_catalog_v2 = quant_research_factor_catalog_v2()
        stock_ids = (*QUANT_RESEARCH_FACTOR_ORDER, *QUANT_RESEARCH_FACTOR_V2_ORDER)
        stock_families = tuple(
            definition.family.value
            for definition in (*stock_catalog.definitions, *stock_catalog_v2.definitions)
        )
        security_panel = build_factor_space_panel(
            panel=FactorSpacePanelKind.SECURITY_CROSS_SECTION,
            input_ids=stock_ids,
            economic_families=stock_families,
            values=stock_values,
            group_keys=group_keys,
        )
        state_values = _state_panel(state, development_sessions)
        state_definition = quant_research_market_state_vector_definition_v1()
        market_state_panel = build_factor_space_panel(
            panel=FactorSpacePanelKind.MARKET_STATE_TIME_SERIES,
            input_ids=QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER,
            economic_families=tuple(
                definition.evidence_tier.value for definition in state_definition.definitions
            ),
            values=state_values,
        )
        report = build_factor_space_diagnostic_report(
            source_bindings=tuple(sorted((
                _binding("factor_catalog_v1_diagnostics", v1.logical_fingerprint, v1_diagnostics_root / V1_REPORT_FILE),
                _binding("factor_catalog_v2_qualification", v2.logical_fingerprint, v2_qualification_root / V2_REPORT_FILE),
                FactorSpaceSourceBindingV1(
                    source_name="historical_split_extension",
                    logical_fingerprint=historical_candidate.candidate.logical_fingerprint,
                    file_sha256=historical_candidate.file_sha256,
                ),
                FactorSpaceSourceBindingV1(
                    source_name="factor_space_split_actions",
                    logical_fingerprint=split.source_action_fingerprint,
                ),
                FactorSpaceSourceBindingV1(
                    source_name="factor_space_split_adjustments",
                    logical_fingerprint=split.source_adjustment_fingerprint,
                ),
                _binding("market_state_qualification", state.logical_fingerprint, market_state_root / STATE_REPORT_FILE),
            ), key=lambda item: item.source_name)),
            security_panel=security_panel,
            market_state_panel=market_state_panel,
        )
        path = write_factor_space_diagnostic(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )
        return path, report


def _validate_source_reports(v1, v2, state) -> None:
    catalog_v1 = quant_research_factor_catalog_v1()
    catalog_v2 = quant_research_factor_catalog_v2()
    if (
        v1.catalog_fingerprint != catalog_v1.logical_fingerprint
        or v2.catalog_fingerprint != catalog_v2.logical_fingerprint
        or state.vector_definition_fingerprint
        != quant_research_market_state_vector_definition_v1().logical_fingerprint
        or v1.contains_forward_outcomes
        or v1.contains_performance_metrics
        or v2.contains_forward_outcomes
        or v2.contains_performance_metrics
        or v2.development_outcome_read_count
        or state.contains_forward_outcomes
        or state.contains_performance_metrics
        or state.development_outcome_read_count
        or len({v1.source_eod_fingerprint, v2.source_eod_fingerprint, state.source_eod_fingerprint}) != 1
        or v2.source_membership_fingerprint != state.source_membership_fingerprint
    ):
        raise FactorSpaceDiagnosticCliError("outcome-blind source reports differ")


def _read_memberships(data_root: Path, sessions: tuple[date, ...], state):
    state_by_session = {item.as_of_session: item for item in state.sessions}
    output = {}
    for session in sessions:
        result = read_canonical_research_universe_membership(
            data_root=data_root,
            methodology_version=STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY,
            session_date=session,
        )
        source_state = state_by_session[session]
        if (
            result.membership_manifest.logical_fingerprint
            != source_state.membership_logical_fingerprint
            or result.custody.membership_manifest_sha256
            != source_state.membership_manifest_sha256
        ):
            raise FactorSpaceDiagnosticCliError("membership differs from market-state evidence")
        included = tuple(sorted((
            item for item in result.records
            if item.universe_id == STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE
            and item.disposition is UniverseMembershipDisposition.INCLUDED
        ), key=lambda item: str(item.instrument_id)))
        if len(included) != source_state.declared_member_count:
            raise FactorSpaceDiagnosticCliError("membership count differs")
        output[session] = included
    return output


def _stock_panel(*, repository, source_sessions, development_sessions, memberships, split, spy_id, all_member_ids, calendar, v1):
    rows: list[list[float]] = []
    groups: list[str] = []
    window = deque(maxlen=127)
    for source_session in source_sessions:
        session_read = repository.read_history_sessions((source_session,))[0]
        if _spy_instrument_id(session_read.bars) != spy_id:
            raise FactorSpaceDiagnosticCliError("SPY identity changed")
        current = {
            item.instrument_id: item
            for item in session_read.bars
            if item.instrument_id in all_member_ids or item.instrument_id == spy_id
        }
        window.append((session_read, current))
        if source_session not in development_sessions:
            continue
        if len(window) != 127:
            raise FactorSpaceDiagnosticCliError("factor window is incomplete")
        member_ids = tuple(item.instrument_id for item in memberships[source_session])
        v2_values, _ = _build_signal_factor_payload(
            source_session=source_session,
            window=tuple((item.integrity.session_date, values) for item, values in window),
            member_ids=member_ids,
            spy_id=spy_id,
            active_action_keys=set(split.active_action_keys),
            quarantined_action_keys=set(split.quarantined_action_keys),
            unresolved_impact_keys=set(split.unresolved_impact_keys),
            clear_adjustments=split.clear_adjustments,
            quarantined_adjustment_keys=set(split.quarantined_adjustment_keys),
            action_start=split.action_start,
            adjustment_start=split.adjustment_start,
        )
        v1_observations = _build_session_observations(
            session=source_session,
            session_reads=tuple(item for item, _ in tuple(window)[-21:]),
            member_ids=frozenset(member_ids),
            active_action_keys=set(split.active_action_keys),
            quarantined_action_keys=set(split.quarantined_action_keys),
            unresolved_impact_keys=set(split.unresolved_impact_keys),
            clear_adjustments=split.clear_adjustments,
            quarantined_adjustment_keys=set(split.quarantined_adjustment_keys),
            action_start=split.action_start,
            adjustment_start=split.adjustment_start,
            source_eod_fingerprint=v1.source_eod_fingerprint,
            source_adjustment_fingerprint=v1.source_adjustment_fingerprint,
            calendar=calendar,
        )
        v1_by_id = {item.instrument_id: item for item in v1_observations}
        for position, instrument_id in enumerate(member_ids):
            observation = v1_by_id[instrument_id]
            row = [
                float(item.value) if item.value is not None else np.nan
                for item in observation.factor_values
            ]
            row.extend(float(v2_values[factor_id][position]) for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER)
            rows.append(row)
            groups.append(source_session.isoformat())
        print(json.dumps({"status": "building_factor_space_input", "completed_session": source_session.isoformat(), "row_count": len(rows)}, sort_keys=True, separators=(",", ":")), file=sys.stderr, flush=True)
    return np.asarray(rows, dtype=np.float64), tuple(groups)


def _state_panel(state, sessions: tuple[date, ...]) -> np.ndarray:
    by_session = {item.as_of_session: item for item in state.sessions}
    rows = []
    for session in sessions:
        metrics = by_session[session].metrics
        if tuple(item.metric_id for item in metrics) != QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER:
            raise FactorSpaceDiagnosticCliError("market-state order differs")
        rows.append([float(item.value) if item.value is not None else np.nan for item in metrics])
    return np.asarray(rows, dtype=np.float64)


def _binding(name: str, fingerprint: str, path: Path) -> FactorSpaceSourceBindingV1:
    return FactorSpaceSourceBindingV1(
        source_name=name,
        logical_fingerprint=fingerprint,
        file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
