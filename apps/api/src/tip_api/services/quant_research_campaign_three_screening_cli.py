"""Network-disabled runner for the frozen Campaign Three Development screen."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from tip_api.contracts.analytics.v1.quant_research_campaign_three_development_access import (
    CampaignThreeDevelopmentExecutionKind,
    validate_campaign_three_development_grant,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_input_qualification import (
    CampaignThreeInputQualificationStatus,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_screening import (
    CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT,
    CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256,
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
from tip_api.persistence.quant_research_campaign_three_development_access import (
    complete_campaign_three_development_execution,
    read_campaign_three_development_access_grant,
    read_campaign_three_development_access_request,
    reserve_campaign_three_development_execution,
)
from tip_api.persistence.quant_research_campaign_three_input_qualification import (
    REPORT_FILE as INPUT_QUALIFICATION_REPORT_FILE,
    read_campaign_three_input_qualification_report_v1,
)
from tip_api.persistence.quant_research_campaign_three_screening import (
    validate_campaign_three_screening_output,
    write_campaign_three_screening_report,
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
from tip_api.services.quant_research_campaign_three_screening import (
    build_campaign_three_screening_report,
)
from tip_api.services.quant_research_factor_qualification_v2 import (
    combined_code_sha256,
)
from tip_api.services.quant_research_factor_qualification_v2_cli import (
    _calculation_code_sha256,
    _chronological_plan_fingerprint,
    _diagnostic_code_sha256,
    _read_signal_memberships,
    _spy_instrument_id,
    _validate_v2_census,
)
from tip_api.services.quant_research_factor_screening_cli import (
    _build_development_factor_observations,
)
from tip_api.services.quant_research_factor_screening_v2_cli import (
    _build_factor_labels_v2,
    _build_factor_observations_and_controls,
    _canonical_split_evidence,
    _declared_development_sessions,
    _file_sha256,
    _validate_repository_revision,
)
from tip_api.services.quant_research_historical_split_extension_v2 import (
    build_quant_research_historical_split_evidence_v2,
)
from tip_api.services.strong_leader_pullback_development_dataset_cli import (
    _read_terminal_references,
    _safe_error_detail,
)
from tip_api.services.strong_leader_pullback_diagnostics_cli import (
    _network_disabled,
    _validate_census_sources,
)


class CampaignThreeScreeningCliError(RuntimeError):
    """Raised when the frozen Campaign Three execution boundary differs."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one formal or exact-replay Campaign Three screen."
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
        "input-qualification-root",
        "input-qualification-custody-root",
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
        "access-request-root",
        "access-request-custody-root",
        "access-grant-root",
        "access-grant-custody-root",
        "execution-root",
        "execution-custody-root",
        "output-root",
        "output-custody-root",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument(
        "--execution-kind",
        choices=tuple(item.value for item in CampaignThreeDevelopmentExecutionKind),
        required=True,
    )
    parser.add_argument("--created-at", type=_datetime, required=True)
    parser.add_argument("--implementation-revision", required=True)
    args = parser.parse_args(argv)
    try:
        path, sha256, status, report = run_campaign_three_screening(
            **vars(args)
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "campaign_three_screening_rejected",
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
                "status": status,
                "report_path": str(path),
                "report_sha256": sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "screening_status": report.status.value,
                "selected_candidate_alpha_ids": report.selected_candidate_alpha_ids,
                "selected_risk_guard_ids": report.selected_risk_guard_ids,
                "decision_status_counts": dict(
                    sorted(
                        Counter(item.status.value for item in report.decisions).items()
                    )
                ),
                "validation_access_authorized": False,
                "holdout_access_authorized": False,
                "publication_authorized": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def run_campaign_three_screening(
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
    input_qualification_root: Path,
    input_qualification_custody_root: Path,
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
    access_request_root: Path,
    access_request_custody_root: Path,
    access_grant_root: Path,
    access_grant_custody_root: Path,
    execution_root: Path,
    execution_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    execution_kind: str,
    created_at: datetime,
    implementation_revision: str,
):
    with _network_disabled():
        _validate_run_identity(created_at, implementation_revision)
        _validate_repository_revision(implementation_revision)
        kind = CampaignThreeDevelopmentExecutionKind(execution_kind)
        request, _ = read_campaign_three_development_access_request(
            output_root=access_request_root,
            output_custody_root=access_request_custody_root,
        )
        grant, _ = read_campaign_three_development_access_grant(
            output_root=access_grant_root,
            output_custody_root=access_grant_custody_root,
        )
        validate_campaign_three_development_grant(request=request, grant=grant)
        if (
            request.implementation_revision != implementation_revision
            or created_at < grant.granted_at
        ):
            raise CampaignThreeScreeningCliError(
                "Campaign Three access revision or chronology differs"
            )

        input_qualification = read_campaign_three_input_qualification_report_v1(
            output_root=input_qualification_root,
            output_custody_root=input_qualification_custody_root,
        )
        if (
            input_qualification.logical_fingerprint
            != CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT
            or _file_sha256(
                input_qualification_root / INPUT_QUALIFICATION_REPORT_FILE
            )
            != CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256
            or input_qualification.status
            is not CampaignThreeInputQualificationStatus.READY_FOR_PROTOCOL_FREEZE
            or input_qualification.contains_forward_outcomes
            or input_qualification.development_outcome_read_count
        ):
            raise CampaignThreeScreeningCliError(
                "Campaign Three frozen input qualification differs"
            )
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
            v1_diagnostics.logical_fingerprint
            != input_qualification.source_v1_factor_diagnostics_fingerprint
            or _file_sha256(v1_diagnostics_root / V1_DIAGNOSTICS_REPORT_FILE)
            != input_qualification.source_v1_factor_diagnostics_sha256
            or v2_qualification.logical_fingerprint
            != input_qualification.source_v2_factor_qualification_fingerprint
            or _file_sha256(v2_qualification_root / V2_QUALIFICATION_REPORT_FILE)
            != input_qualification.source_v2_factor_qualification_sha256
            or market_state.logical_fingerprint
            != input_qualification.source_market_state_qualification_fingerprint
            or _file_sha256(market_state_root / MARKET_STATE_REPORT_FILE)
            != input_qualification.source_market_state_qualification_sha256
            or v2_qualification.status
            is not QuantResearchFactorQualificationV2Status.READY_FOR_SCREENING_PROTOCOL_REVIEW
            or v2_qualification.calculation_code_sha256
            != _calculation_code_sha256()
            or v2_qualification.diagnostic_code_sha256
            != _diagnostic_code_sha256()
        ):
            raise CampaignThreeScreeningCliError(
                "Campaign Three frozen feature sources differ"
            )

        census = read_development_coverage_census(output_root=development_census_root)
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
            raise CampaignThreeScreeningCliError(
                "Campaign Three frozen chronology differs"
            )
        declared_sessions = _declared_development_sessions(
            diagnostics=v1_diagnostics,
            plan=plan,
        )
        partitions = _discover_membership_partitions(shadow_root)
        if tuple(sorted(partitions)) != ordered_sessions:
            raise CampaignThreeScreeningCliError(
                "Campaign Three Membership partitions differ"
            )
        memberships, population_fingerprint = _read_signal_memberships(
            shadow_root=shadow_root,
            partitions=partitions,
            census=census,
            ordered_sessions=ordered_sessions,
        )
        if population_fingerprint != v2_qualification.source_population_fingerprint:
            raise CampaignThreeScreeningCliError(
                "Campaign Three Membership population differs"
            )
        repository = CanonicalEodReadRepository(canonical_root)
        source_sessions = (
            *calendar.sessions_before(ordered_sessions[0], 126),
            *ordered_sessions,
        )
        if not set(source_sessions).issubset(repository.list_session_index()):
            raise CampaignThreeScreeningCliError(
                "Campaign Three feature source interval is incomplete"
            )
        member_ids = frozenset(
            item.instrument_id for records in memberships.values() for item in records
        )
        spy_id = _spy_instrument_id(
            repository.read_history_sessions((source_sessions[0],))[0].bars
        )
        historical_candidate = read_historical_split_adjustment_candidate(
            output_root=historical_split_candidate_root,
            output_custody_root=historical_split_candidate_custody_root,
        )
        factor_split = build_quant_research_historical_split_evidence_v2(
            candidate=historical_candidate.candidate,
            candidate_file_sha256=historical_candidate.file_sha256,
            canonical_action_source=action_source,
            canonical_adjustment_source=adjustment_source,
            source_sessions=source_sessions,
            required_ids=member_ids | {spy_id},
        )
        if (
            factor_split.source_action_fingerprint
            != v2_qualification.source_action_fingerprint
            or factor_split.source_adjustment_fingerprint
            != v2_qualification.source_adjustment_fingerprint
        ):
            raise CampaignThreeScreeningCliError(
                "Campaign Three private factor split evidence differs"
            )
        canonical_evidence = _canonical_split_evidence(
            canonical_action=action_source,
            canonical_adjustment=adjustment_source,
        )
        v1_observations = _build_development_factor_observations(
            repository=repository,
            shadow_root=shadow_root,
            census=census,
            plan=plan,
            action_source=action_source,
            adjustment_source=adjustment_source,
            diagnostics=v1_diagnostics,
        )
        v2_observations, _, replayed_v2_qualification = (
            _build_factor_observations_and_controls(
                repository=repository,
                source_sessions=source_sessions,
                memberships=memberships,
                plan=plan,
                qualification=v2_qualification,
                factor_split=factor_split,
                control_evidence=canonical_evidence,
                spy_id=spy_id,
                calendar=calendar,
                declared_development_sessions=declared_sessions,
            )
        )
        if replayed_v2_qualification != v2_qualification:
            raise CampaignThreeScreeningCliError(
                "Campaign Three V2 feature replay differs"
            )
        validate_campaign_three_screening_output(
            output_root=output_root,
            output_custody_root=output_custody_root,
        )

        # This reservation is the one-way boundary. Every operation above is
        # outcome-blind; terminal evidence and future EOD are read only below.
        reserve_campaign_three_development_execution(
            execution_root=execution_root,
            execution_custody_root=execution_custody_root,
            request=request,
            grant=grant,
            execution_kind=kind,
            run_created_at=created_at,
            reserved_at=datetime.now(UTC),
            report_output_root=output_root,
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
            observations=v2_observations,
            plan=plan,
            terminal_references=terminal_references,
            canonical_action=action_source,
            canonical_adjustment=adjustment_source,
            canonical_evidence=canonical_evidence,
            spy_id=spy_id,
        )
        report = build_campaign_three_screening_report(
            v1_observations=v1_observations,
            v2_observations=v2_observations,
            labels=labels,
            market_state=market_state,
            market_state_sha256=_file_sha256(
                market_state_root / MARKET_STATE_REPORT_FILE
            ),
            access_request=request,
            access_grant=grant,
            implementation_revision=implementation_revision,
            evaluator_code_sha256=_evaluator_code_sha256(),
            created_at=created_at,
        )
        path, sha256, status = write_campaign_three_screening_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )
        complete_campaign_three_development_execution(
            execution_root=execution_root,
            execution_custody_root=execution_custody_root,
            execution_kind=kind,
            report_sha256=sha256,
            report_fingerprint=report.logical_fingerprint,
            completed_at=datetime.now(UTC),
        )
        return path, sha256, status, report


def _validate_run_identity(created_at: datetime, implementation_revision: str) -> None:
    if (
        created_at.tzinfo is None
        or created_at.utcoffset() is None
        or created_at.utcoffset().total_seconds() != 0
    ):
        raise CampaignThreeScreeningCliError(
            "Campaign Three report creation time must use UTC"
        )
    if len(implementation_revision) != 40 or any(
        character not in "0123456789abcdef" for character in implementation_revision
    ):
        raise CampaignThreeScreeningCliError(
            "Campaign Three implementation revision must be one exact Git commit"
        )


def _evaluator_code_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    return combined_code_sha256(
        (
            root
            / "contracts/analytics/v1/quant_research_campaign_three_development_access.py",
            root
            / "contracts/analytics/v1/quant_research_campaign_three_screening.py",
            root
            / "contracts/analytics/v1/quant_research_campaign_three_screening_result.py",
            root / "services/quant_research_campaign_three_screening.py",
            root / "services/quant_research_campaign_three_screening_cli.py",
        )
    )


def _datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must be timezone-aware")
    return parsed


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
