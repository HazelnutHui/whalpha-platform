"""Network-disabled runner for Campaign Three outcome-blind input qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, deque
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np

from tip_api.contracts.analytics.v1.quant_research_campaign_three_hypotheses import (
    quant_research_campaign_three_hypothesis_registry_v1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_qualification_v2 import (
    QuantResearchFactorQualificationV2Status,
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
from tip_api.persistence.quant_research_campaign_three_input_qualification import (
    write_campaign_three_input_qualification_report_v1,
)
from tip_api.persistence.quant_research_factor_diagnostics import (
    REPORT_FILE as V1_DIAGNOSTICS_REPORT_FILE,
    read_quant_research_factor_diagnostics,
)
from tip_api.persistence.quant_research_factor_qualification_v2 import (
    REPORT_FILE as V2_QUALIFICATION_REPORT_FILE,
    read_quant_research_factor_qualification_v2,
)
from tip_api.persistence.quant_research_market_state_qualification import (
    REPORT_FILE as MARKET_STATE_REPORT_FILE,
    read_quant_research_market_state_qualification_v1,
)
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
from tip_api.services.quant_research_campaign_three_input_qualification import (
    CampaignThreeFactorSessionEvidence,
    _development_sessions,
    build_campaign_three_input_qualification_report,
)
from tip_api.services.quant_research_factor_qualification_v2_cli import (
    _build_signal_factor_payload,
    _calculation_code_sha256,
    _chronological_plan_fingerprint,
    _diagnostic_code_sha256,
    _read_signal_memberships,
    _spy_instrument_id,
    _validate_v2_census,
)
from tip_api.services.quant_research_factor_screening_v2_cli import (
    _file_sha256,
    _validate_repository_revision,
    _validate_run_identity,
)
from tip_api.services.quant_research_historical_split_extension_v2 import (
    build_quant_research_historical_split_evidence_v2,
)
from tip_api.services.strong_leader_pullback_development_dataset_cli import (
    _safe_error_detail,
)
from tip_api.services.strong_leader_pullback_diagnostics_cli import (
    _network_disabled,
    _validate_census_sources,
)


class CampaignThreeInputQualificationCliError(RuntimeError):
    """Raised when Campaign Three input qualification cannot be reproduced."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build one private zero-outcome Campaign Three input report."
    )
    for name in (
        "data-root",
        "membership-shadow-root",
        "development-census-root",
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
    parser.add_argument("--created-at", type=_datetime, required=True)
    parser.add_argument("--implementation-revision", required=True)
    args = parser.parse_args(argv)
    try:
        path, sha256, report = run_campaign_three_input_qualification(
            **vars(args)
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "campaign_three_input_qualification_rejected",
                    "error_type": type(exc).__name__,
                    "error_detail": _safe_error_detail(exc),
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
                "report_sha256": sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "qualified_candidate_alpha_count": (
                    report.qualified_candidate_alpha_count
                ),
                "rejected_candidate_alpha_count": (
                    report.rejected_candidate_alpha_count
                ),
                "qualified_risk_guard_count": report.qualified_risk_guard_count,
                "decision_status_counts": dict(
                    sorted(Counter(item.decision.value for item in report.decisions).items())
                ),
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


def run_campaign_three_input_qualification(
    *,
    data_root: Path,
    membership_shadow_root: Path,
    development_census_root: Path,
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
    created_at: datetime,
    implementation_revision: str,
):
    with _network_disabled():
        _validate_run_identity(created_at, implementation_revision)
        _validate_repository_revision(implementation_revision)
        canonical_root = _validated_data_root(data_root)
        shadow_root = _validated_shadow_root(membership_shadow_root)
        v1_diagnostics = read_quant_research_factor_diagnostics(
            output_root=v1_diagnostics_root,
            output_custody_root=v1_diagnostics_custody_root,
        )
        v2_qualification = read_quant_research_factor_qualification_v2(
            output_root=v2_qualification_root,
            output_custody_root=v2_qualification_custody_root,
        )
        market_state = read_quant_research_market_state_qualification_v1(
            output_root=market_state_root,
            output_custody_root=market_state_custody_root,
        )
        if (
            v2_qualification.status
            is not QuantResearchFactorQualificationV2Status.READY_FOR_SCREENING_PROTOCOL_REVIEW
            or v2_qualification.calculation_code_sha256
            != _calculation_code_sha256()
            or v2_qualification.diagnostic_code_sha256 != _diagnostic_code_sha256()
        ):
            raise CampaignThreeInputQualificationCliError(
                "Campaign Three V2 source qualification differs"
            )
        development_sessions = _development_sessions(v1_diagnostics)

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
            adjustment_fingerprint=adjustment_source.publication.logical_fingerprint,
        )
        calendar = ExchangeCalendar()
        ordered_sessions = tuple(item.session_date for item in census.sessions)
        plan = build_candidate_strategy_chronological_plan(
            ordered_sessions=ordered_sessions,
            calendar=calendar,
        )
        if (
            _chronological_plan_fingerprint(
                ordered_sessions=ordered_sessions,
                calendar=calendar,
            )
            != v2_qualification.chronological_plan_fingerprint
        ):
            raise CampaignThreeInputQualificationCliError(
                "Campaign Three chronology differs from V2 qualification"
            )
        partitions = _discover_membership_partitions(shadow_root)
        if tuple(sorted(partitions)) != ordered_sessions:
            raise CampaignThreeInputQualificationCliError(
                "Campaign Three Membership partitions differ"
            )
        memberships, population_fingerprint = _read_signal_memberships(
            shadow_root=shadow_root,
            partitions=partitions,
            census=census,
            ordered_sessions=ordered_sessions,
        )
        if population_fingerprint != v2_qualification.source_population_fingerprint:
            raise CampaignThreeInputQualificationCliError(
                "Campaign Three V2 population differs"
            )

        repository = CanonicalEodReadRepository(canonical_root)
        source_sessions = (
            *calendar.sessions_before(ordered_sessions[0], 126),
            *ordered_sessions,
        )
        if not set(source_sessions).issubset(repository.list_session_index()):
            raise CampaignThreeInputQualificationCliError(
                "Campaign Three V2 source interval is incomplete"
            )
        all_member_ids = frozenset(
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
        split_evidence = build_quant_research_historical_split_evidence_v2(
            candidate=historical_candidate.candidate,
            candidate_file_sha256=historical_candidate.file_sha256,
            canonical_action_source=action_source,
            canonical_adjustment_source=adjustment_source,
            source_sessions=source_sessions,
            required_ids=all_member_ids | {spy_id},
        )
        if (
            split_evidence.source_action_fingerprint
            != v2_qualification.source_action_fingerprint
            or split_evidence.source_adjustment_fingerprint
            != v2_qualification.source_adjustment_fingerprint
        ):
            raise CampaignThreeInputQualificationCliError(
                "Campaign Three V2 split evidence differs"
            )
        evidence = _replay_v2_factor_sessions(
            repository=repository,
            source_sessions=source_sessions,
            memberships=memberships,
            development_sessions=frozenset(development_sessions),
            split_evidence=split_evidence,
            spy_id=spy_id,
            all_member_ids=all_member_ids,
            calendar=calendar,
        )
        report = build_campaign_three_input_qualification_report(
            v1_diagnostics=v1_diagnostics,
            v1_diagnostics_sha256=_file_sha256(
                v1_diagnostics_root / V1_DIAGNOSTICS_REPORT_FILE
            ),
            v2_qualification=v2_qualification,
            v2_qualification_sha256=_file_sha256(
                v2_qualification_root / V2_QUALIFICATION_REPORT_FILE
            ),
            market_state=market_state,
            market_state_sha256=_file_sha256(
                market_state_root / MARKET_STATE_REPORT_FILE
            ),
            v2_factor_session_evidence=evidence,
            source_revision=implementation_revision,
            created_at=created_at,
        )
        path = write_campaign_three_input_qualification_report_v1(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )
        return path, _file_sha256(path), report


def _replay_v2_factor_sessions(
    *,
    repository,
    source_sessions: tuple[date, ...],
    memberships,
    development_sessions: frozenset[date],
    split_evidence,
    spy_id,
    all_member_ids,
    calendar: ExchangeCalendar,
) -> tuple[CampaignThreeFactorSessionEvidence, ...]:
    selected = tuple(
        item.source_factor_id
        for item in quant_research_campaign_three_hypothesis_registry_v1().proposals
        if item.prospective_trial_count == 1 and item.source_factor_catalog == "v2"
    )
    window = deque(maxlen=127)
    output = []
    completed = 0
    for source_session in source_sessions:
        session_read = repository.read_history_sessions((source_session,))[0]
        if _spy_instrument_id(session_read.bars) != spy_id:
            raise CampaignThreeInputQualificationCliError(
                "Campaign Three SPY identity changes inside V2 replay"
            )
        retained_ids = all_member_ids | {spy_id}
        current = {
            item.instrument_id: item
            for item in session_read.bars
            if item.instrument_id in retained_ids
        }
        window.append((source_session, current))
        if source_session not in development_sessions:
            continue
        if len(window) != 127 or tuple(item[0] for item in window) != tuple(
            (*calendar.sessions_before(source_session, 126), source_session)
        ):
            raise CampaignThreeInputQualificationCliError(
                "Campaign Three V2 replay window differs"
            )
        member_ids = tuple(
            sorted(
                (item.instrument_id for item in memberships[source_session]),
                key=str,
            )
        )
        values, _ = _build_signal_factor_payload(
            source_session=source_session,
            window=tuple(window),
            member_ids=member_ids,
            spy_id=spy_id,
            active_action_keys=set(split_evidence.active_action_keys),
            quarantined_action_keys=set(split_evidence.quarantined_action_keys),
            unresolved_impact_keys=set(split_evidence.unresolved_impact_keys),
            clear_adjustments=split_evidence.clear_adjustments,
            quarantined_adjustment_keys=set(
                split_evidence.quarantined_adjustment_keys
            ),
            action_start=split_evidence.action_start,
            adjustment_start=split_evidence.adjustment_start,
        )
        for factor_id in selected:
            factor_values = values[factor_id]
            available = factor_values[np.isfinite(factor_values)]
            available_count = int(available.size)
            distinct_count = int(np.unique(available).size)
            output.append(
                CampaignThreeFactorSessionEvidence(
                    factor_id=factor_id,
                    as_of_session=source_session,
                    available_instrument_count=available_count,
                    distinct_value_count=distinct_count,
                    tie_excess_count=available_count - distinct_count,
                )
            )
        completed += 1
        if completed % 10 == 0 or completed == len(development_sessions):
            print(
                json.dumps(
                    {
                        "status": "replaying_outcome_blind_v2_inputs",
                        "completed_development_sessions": completed,
                        "total_development_sessions": len(development_sessions),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
            )
    return tuple(output)


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    raise SystemExit(main())
