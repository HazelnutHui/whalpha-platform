"""Network-disabled real-data runner for market-state qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import deque
from datetime import date
from pathlib import Path
from uuid import UUID

from tip_api.contracts.analytics.v1.quant_research_market_state_qualification import (
    QUANT_RESEARCH_MARKET_STATE_REQUIRED_LIMITATIONS,
    QuantResearchMarketStateBenchmarkIdentityV1,
    QuantResearchMarketStateSessionV1,
    market_state_population_fingerprint,
    quant_research_market_state_qualification_protocol_v1,
)
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
from tip_api.persistence.quant_research_market_state_qualification import (
    read_quant_research_market_state_qualification_v1,
    report_bytes,
    write_quant_research_market_state_qualification_v1,
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
from tip_api.services.quant_research_factor_qualification_v2 import (
    combined_code_sha256,
)
from tip_api.services.quant_research_factor_qualification_v2_cli import (
    _adjusted_factor_bar_v2,
    _fingerprint,
    _validate_v2_census,
)
from tip_api.services.quant_research_historical_split_extension_v2 import (
    build_quant_research_historical_split_evidence_v2,
)
from tip_api.services.quant_research_market_state_qualification import (
    build_quant_research_market_state_qualification_v1,
)
from tip_api.services.quant_research_market_state_vector import (
    QuantResearchMarketStateBarV1,
    QuantResearchMarketStateMemberSeriesV1,
    QuantResearchMarketStateUnavailableMemberV1,
    calculate_quant_research_market_state_vector_v1,
)
from tip_api.services.strong_leader_pullback_diagnostics_cli import (
    _benchmark_ids,
    _network_disabled,
    _read_membership,
    _split_path_status,
    _valid_bar,
    _validate_census_sources,
)


class QuantResearchMarketStateQualificationCliError(RuntimeError):
    """Raised when the frozen local qualification boundary cannot be proved."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build one private outcome-blind market-state qualification."
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--membership-shadow-root", type=Path, required=True)
    parser.add_argument("--development-census-root", type=Path, required=True)
    parser.add_argument("--split-action-publication-root", type=Path, required=True)
    parser.add_argument("--split-adjustment-publication-root", type=Path, required=True)
    parser.add_argument("--historical-split-candidate-root", type=Path)
    parser.add_argument("--historical-split-candidate-custody-root", type=Path)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output-custody-root", type=Path, required=True)
    parser.add_argument("--reference-report-root", type=Path)
    args = parser.parse_args(argv)
    try:
        path, report, replay_match = run_quant_research_market_state_qualification_v1(
            data_root=args.data_root,
            membership_shadow_root=args.membership_shadow_root,
            development_census_root=args.development_census_root,
            split_action_publication_root=args.split_action_publication_root,
            split_adjustment_publication_root=(
                args.split_adjustment_publication_root
            ),
            historical_split_candidate_root=args.historical_split_candidate_root,
            historical_split_candidate_custody_root=(
                args.historical_split_candidate_custody_root
            ),
            source_revision=args.source_revision,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            reference_report_root=args.reference_report_root,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "market_state_qualification_rejected",
                    "error_type": type(exc).__name__,
                    "error_detail": str(exc)[:500],
                    "external_request_count": 0,
                    "development_outcome_read_count": 0,
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
                "reconstructed_joint_available_session_count": (
                    report.reconstructed_joint_available_session_count
                ),
                "replay_match": replay_match,
                "external_request_count": 0,
                "development_outcome_read_count": 0,
                "canonical_data_write_count": 0,
                "production_write_count": 0,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def run_quant_research_market_state_qualification_v1(
    *,
    data_root: Path,
    membership_shadow_root: Path,
    development_census_root: Path,
    split_action_publication_root: Path,
    split_adjustment_publication_root: Path,
    source_revision: str,
    output_root: Path,
    output_custody_root: Path,
    historical_split_candidate_root: Path | None = None,
    historical_split_candidate_custody_root: Path | None = None,
    reference_report_root: Path | None = None,
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
            raise QuantResearchMarketStateQualificationCliError(
                "historical split candidate root and custody must be supplied together"
            )

        calendar = ExchangeCalendar()
        ordered_sessions = tuple(item.session_date for item in census.sessions)
        protocol = quant_research_market_state_qualification_protocol_v1()
        if (
            len(ordered_sessions) != protocol.expected_signal_session_count
            or ordered_sessions[0] != protocol.first_signal_session
            or ordered_sessions[-1] != protocol.last_signal_session
            or _fingerprint([item.isoformat() for item in ordered_sessions])
            != protocol.expected_session_partition_fingerprint
        ):
            raise QuantResearchMarketStateQualificationCliError(
                "market-state signal-session partition differs"
            )
        partitions = _discover_membership_partitions(shadow_root)
        if tuple(sorted(partitions)) != ordered_sessions:
            raise QuantResearchMarketStateQualificationCliError(
                "Membership partitions do not exactly cover the frozen plan"
            )
        (
            memberships,
            membership_logical_fingerprints,
            membership_manifest_sha256,
        ) = _read_market_state_memberships(
            shadow_root=shadow_root,
            partitions=partitions,
            census=census,
            ordered_sessions=ordered_sessions,
        )

        repository = CanonicalEodReadRepository(canonical_root)
        source_sessions = (
            *calendar.sessions_before(ordered_sessions[0], 20),
            *ordered_sessions,
        )
        if not set(source_sessions).issubset(repository.list_session_index()):
            raise QuantResearchMarketStateQualificationCliError(
                "canonical EOD does not cover the exact market-state source interval"
            )
        first_read = repository.read_history_sessions((source_sessions[0],))[0]
        benchmark_ids = _benchmark_ids(
            {item.instrument_id: item for item in first_read.bars}
        )
        all_member_ids = frozenset(
            item.instrument_id
            for records in memberships.values()
            for item in records
        )
        required_ids = all_member_ids | frozenset(benchmark_ids.values())
        (
            source_action_fingerprint,
            source_adjustment_fingerprint,
            active_action_keys,
            quarantined_action_keys,
            unresolved_impact_keys,
            clear_adjustments,
            quarantined_adjustment_keys,
            action_start,
            adjustment_start,
        ) = _split_evidence(
            source_sessions=source_sessions,
            required_ids=required_ids,
            action_source=action_source,
            adjustment_source=adjustment_source,
            historical_split_candidate_root=historical_split_candidate_root,
            historical_split_candidate_custody_root=(
                historical_split_candidate_custody_root
            ),
        )
        evidence_by_family = {item.family: item for item in census.dataset_evidence}
        source_eod_fingerprint = evidence_by_family[
            "eod_price_bar"
        ].logical_fingerprint
        source_membership_fingerprint = evidence_by_family[
            "universe_membership"
        ].logical_fingerprint
        if source_eod_fingerprint is None or source_membership_fingerprint is None:
            raise QuantResearchMarketStateQualificationCliError(
                "frozen EOD or Membership evidence lacks a logical fingerprint"
            )
        sessions = _calculate_sessions(
            repository=repository,
            source_sessions=source_sessions,
            signal_sessions=frozenset(ordered_sessions),
            memberships=memberships,
            membership_logical_fingerprints=membership_logical_fingerprints,
            membership_manifest_sha256=membership_manifest_sha256,
            benchmark_ids=benchmark_ids,
            active_action_keys=active_action_keys,
            quarantined_action_keys=quarantined_action_keys,
            unresolved_impact_keys=unresolved_impact_keys,
            clear_adjustments=clear_adjustments,
            quarantined_adjustment_keys=quarantined_adjustment_keys,
            action_start=action_start,
            adjustment_start=adjustment_start,
            calendar=calendar,
        )
        report = build_quant_research_market_state_qualification_v1(
            source_revision=source_revision,
            source_eod_fingerprint=source_eod_fingerprint,
            source_membership_fingerprint=source_membership_fingerprint,
            source_action_fingerprint=source_action_fingerprint,
            source_adjustment_fingerprint=source_adjustment_fingerprint,
            source_census_fingerprint=census.logical_fingerprint,
            source_population_fingerprint=(
                market_state_population_fingerprint(sessions)
            ),
            calculation_code_sha256=_calculation_code_sha256(),
            sessions=sessions,
            limitation_codes=QUANT_RESEARCH_MARKET_STATE_REQUIRED_LIMITATIONS,
        )
        report_path = write_quant_research_market_state_qualification_v1(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )
        replay_match = None
        if reference_report_root is not None:
            reference = read_quant_research_market_state_qualification_v1(
                output_root=reference_report_root,
                output_custody_root=output_custody_root,
            )
            replay_match = (
                reference.logical_fingerprint == report.logical_fingerprint
                and report_bytes(reference) == report_bytes(report)
            )
            if not replay_match:
                raise QuantResearchMarketStateQualificationCliError(
                    "market-state qualification replay differs"
                )
        return report_path, report, replay_match


def _read_market_state_memberships(
    *, shadow_root, partitions, census, ordered_sessions
) -> tuple[
    dict[date, tuple[object, ...]],
    dict[date, str],
    dict[date, str],
]:
    census_by_session = {item.session_date: item for item in census.sessions}
    memberships = {}
    logical_fingerprints = {}
    manifest_hashes = {}
    for session in ordered_sessions:
        membership, membership_fingerprint = _read_membership(
            shadow_root=shadow_root,
            partition=partitions[session],
            census_session=census_by_session[session],
        )
        manifest_hash = hashlib.sha256(
            (partitions[session] / "manifest.json").read_bytes()
        ).hexdigest()
        memberships[session] = membership
        logical_fingerprints[session] = membership_fingerprint
        manifest_hashes[session] = manifest_hash
    return memberships, logical_fingerprints, manifest_hashes


def _split_evidence(
    *,
    source_sessions,
    required_ids,
    action_source,
    adjustment_source,
    historical_split_candidate_root,
    historical_split_candidate_custody_root,
):
    if historical_split_candidate_root is not None:
        candidate = read_historical_split_adjustment_candidate(
            output_root=historical_split_candidate_root,
            output_custody_root=historical_split_candidate_custody_root,
        )
        evidence = build_quant_research_historical_split_evidence_v2(
            candidate=candidate.candidate,
            candidate_file_sha256=candidate.file_sha256,
            canonical_action_source=action_source,
            canonical_adjustment_source=adjustment_source,
            source_sessions=source_sessions,
            required_ids=required_ids,
        )
        return (
            evidence.source_action_fingerprint,
            evidence.source_adjustment_fingerprint,
            set(evidence.active_action_keys),
            set(evidence.quarantined_action_keys),
            set(evidence.unresolved_impact_keys),
            evidence.clear_adjustments,
            set(evidence.quarantined_adjustment_keys),
            evidence.action_start,
            evidence.adjustment_start,
        )
    return (
        action_source.publication.logical_fingerprint,
        adjustment_source.publication.logical_fingerprint,
        {
            (item.instrument_id, item.effective_date)
            for item in action_source.actions
            if item.record_status is CorporateActionRecordStatus.ACTIVE
        },
        {
            (item.instrument_id, item.effective_date)
            for item in action_source.actions
            if item.record_status is not CorporateActionRecordStatus.ACTIVE
        },
        {
            (item.instrument_id, effective_date)
            for item in action_source.publication.possible_unresolved_impacts
            for effective_date in item.effective_dates
        },
        {
            (item.instrument_id, item.source_session): item
            for item in adjustment_source.records
            if item.split_adjustment_status is AdjustmentAvailabilityStatus.CLEAR
        },
        {
            (item.instrument_id, item.source_session)
            for item in adjustment_source.records
            if item.split_adjustment_status is not AdjustmentAvailabilityStatus.CLEAR
        },
        action_source.publication.start_date,
        adjustment_source.publication.first_source_session,
    )


def _calculate_sessions(
    *,
    repository,
    source_sessions,
    signal_sessions,
    memberships,
    membership_logical_fingerprints,
    membership_manifest_sha256,
    benchmark_ids,
    active_action_keys,
    quarantined_action_keys,
    unresolved_impact_keys,
    clear_adjustments,
    quarantined_adjustment_keys,
    action_start,
    adjustment_start,
    calendar,
):
    all_member_ids = frozenset(
        item.instrument_id for records in memberships.values() for item in records
    )
    retained_ids = all_member_ids | frozenset(benchmark_ids.values())
    window: deque[tuple[date, dict[UUID, EodMarketBarReadModel]]] = deque(maxlen=21)
    output = []
    completed = 0
    for source_session in source_sessions:
        session_read = repository.read_history_sessions((source_session,))[0]
        current = {item.instrument_id: item for item in session_read.bars}
        current_benchmarks = _benchmark_ids(current)
        if current_benchmarks != benchmark_ids:
            raise QuantResearchMarketStateQualificationCliError(
                "benchmark stable identities change inside source interval"
            )
        window.append(
            (
                source_session,
                {key: value for key, value in current.items() if key in retained_ids},
            )
        )
        if source_session not in signal_sessions:
            continue
        expected_sessions = (
            *calendar.sessions_before(source_session, 20),
            source_session,
        )
        if len(window) != 21 or tuple(item[0] for item in window) != expected_sessions:
            raise QuantResearchMarketStateQualificationCliError(
                "market-state rolling source window differs"
            )
        member_ids = tuple(
            sorted(
                (item.instrument_id for item in memberships[source_session]),
                key=str,
            )
        )
        output.append(
            _build_session(
                source_session=source_session,
                window=tuple(window),
                member_ids=member_ids,
                membership_logical_fingerprint=(
                    membership_logical_fingerprints[source_session]
                ),
                membership_manifest_sha256=membership_manifest_sha256[
                    source_session
                ],
                benchmark_ids=benchmark_ids,
                active_action_keys=active_action_keys,
                quarantined_action_keys=quarantined_action_keys,
                unresolved_impact_keys=unresolved_impact_keys,
                clear_adjustments=clear_adjustments,
                quarantined_adjustment_keys=quarantined_adjustment_keys,
                action_start=action_start,
                adjustment_start=adjustment_start,
            )
        )
        completed += 1
        if completed % 20 == 0 or completed == len(signal_sessions):
            print(
                json.dumps(
                    {
                        "status": "running",
                        "completed_signal_sessions": completed,
                        "total_signal_sessions": len(signal_sessions),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
            )
    return tuple(output)


def _build_session(
    *,
    source_session,
    window,
    member_ids,
    membership_logical_fingerprint,
    membership_manifest_sha256,
    benchmark_ids,
    active_action_keys,
    quarantined_action_keys,
    unresolved_impact_keys,
    clear_adjustments,
    quarantined_adjustment_keys,
    action_start,
    adjustment_start,
):
    source_sessions = tuple(item[0] for item in window)
    by_session = {session: values for session, values in window}
    required_ids = frozenset((*member_ids, *benchmark_ids.values()))
    missing_or_invalid = {
        instrument_id
        for instrument_id in required_ids
        if any(
            instrument_id not in by_session[session]
            or not _valid_bar(by_session[session].get(instrument_id))
            for session in source_sessions
        )
    }
    hazard_ids, _ = _split_path_status(
        required_ids=required_ids,
        sessions=source_sessions,
        active_action_keys=active_action_keys,
        quarantined_action_keys=quarantined_action_keys,
        unresolved_impact_keys=unresolved_impact_keys,
        clear_adjustments=clear_adjustments,
        quarantined_adjustment_keys=quarantined_adjustment_keys,
        action_start=action_start,
        adjustment_start=adjustment_start,
    )
    benchmark_series = {}
    benchmark_reasons = {}
    for ticker, instrument_id in benchmark_ids.items():
        reasons = []
        if instrument_id in missing_or_invalid:
            reasons.append(f"benchmark_{ticker.lower()}_eod_path_unavailable")
        if instrument_id in hazard_ids:
            reasons.append(f"benchmark_{ticker.lower()}_split_evidence_quarantined")
        if reasons:
            benchmark_series[ticker] = ()
            benchmark_reasons[ticker] = tuple(sorted(reasons))
        else:
            benchmark_series[ticker] = _market_state_series(
                instrument_id=instrument_id,
                source_sessions=source_sessions,
                by_session=by_session,
                clear_adjustments=clear_adjustments,
            )
    available_members = []
    unavailable_members = []
    for instrument_id in member_ids:
        reasons = []
        if instrument_id in missing_or_invalid:
            reasons.append("member_eod_path_unavailable")
        if instrument_id in hazard_ids:
            reasons.append("member_split_evidence_quarantined")
        if reasons:
            unavailable_members.append(
                QuantResearchMarketStateUnavailableMemberV1(
                    instrument_id=str(instrument_id),
                    reason_codes=tuple(sorted(reasons)),
                )
            )
        else:
            available_members.append(
                QuantResearchMarketStateMemberSeriesV1(
                    instrument_id=str(instrument_id),
                    bars=_market_state_series(
                        instrument_id=instrument_id,
                        source_sessions=source_sessions,
                        by_session=by_session,
                        clear_adjustments=clear_adjustments,
                    ),
                )
            )
    declared_ids = tuple(str(item) for item in member_ids)
    metrics = calculate_quant_research_market_state_vector_v1(
        expected_sessions=source_sessions,
        benchmark_series=benchmark_series,
        benchmark_unavailable_reasons=benchmark_reasons,
        declared_member_ids=declared_ids,
        member_series=tuple(available_members),
        unavailable_members=tuple(unavailable_members),
    )
    return QuantResearchMarketStateSessionV1(
        as_of_session=source_session,
        benchmark_identities=tuple(
            QuantResearchMarketStateBenchmarkIdentityV1(
                ticker=ticker,
                instrument_id=benchmark_ids[ticker],
            )
            for ticker in ("SPY", "QQQ", "IWM", "DIA")
        ),
        membership_logical_fingerprint=membership_logical_fingerprint,
        membership_manifest_sha256=membership_manifest_sha256,
        declared_member_ids_fingerprint=_fingerprint(declared_ids),
        declared_member_count=len(declared_ids),
        complete_member_count=len(available_members),
        metrics=metrics,
    )


def _market_state_series(
    *, instrument_id, source_sessions, by_session, clear_adjustments
):
    return tuple(
        QuantResearchMarketStateBarV1(
            session=session,
            close=_adjusted_factor_bar_v2(
                by_session[session][instrument_id],
                clear_adjustments.get((instrument_id, session)),
            ).close,
        )
        for session in source_sessions
    )


def _calculation_code_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    return combined_code_sha256(
        (
            root / "contracts/analytics/v1/quant_research_market_state_vector.py",
            root
            / "contracts/analytics/v1/quant_research_market_state_qualification.py",
            root / "services/quant_research_market_state_vector.py",
            root / "services/quant_research_market_state_qualification.py",
            root / "services/quant_research_market_state_qualification_cli.py",
            root / "services/quant_research_historical_split_extension_v2.py",
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
