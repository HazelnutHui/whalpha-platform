"""Bounded builder for a non-as-operated reconstructed A-share lane."""

from __future__ import annotations

from datetime import date

from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.china_ashare.v1.full_population_gaps import (
    ChinaAshareFullPopulationGapChecklistV1,
)
from tip_api.contracts.china_ashare.v1.reconstructed_lane import (
    ChinaAshareReconstructedDisposition,
    ChinaAshareReconstructedLanePlanV1,
    ChinaAshareReconstructedPartitionAggregateV1,
    ChinaAshareReconstructedUniverseDecisionV1,
    build_reconstructed_lane_plan,
    build_reconstructed_partition_aggregate,
    build_reconstructed_universe_decision,
    reconstructed_decision_set_fingerprint,
    target_session_set_fingerprint,
)
from tip_api.persistence.china_ashare_full_population_diagnostic_package import (
    ChinaAshareFullPopulationDiagnosticAggregateResultV1,
)
from tip_api.persistence.china_ashare_normalized_expansion_package import (
    ChinaAshareNormalizedExpansionPartitionResultV1,
)


class ChinaAshareReconstructedLaneError(RuntimeError):
    pass


def plan_china_ashare_reconstructed_lane(
    *,
    diagnostic: ChinaAshareFullPopulationDiagnosticAggregateResultV1,
    gap_checklist: ChinaAshareFullPopulationGapChecklistV1,
    target_sessions: tuple[date, ...],
) -> ChinaAshareReconstructedLanePlanV1:
    if (
        gap_checklist.diagnostic_plan_fingerprint
        != diagnostic.plan.logical_fingerprint
        or gap_checklist.diagnostic_package_fingerprint
        != diagnostic.manifest.logical_fingerprint
        or gap_checklist.streaming_aggregate_fingerprint
        != diagnostic.streaming.logical_fingerprint
    ):
        raise ChinaAshareReconstructedLaneError(
            "reconstructed lane gap bindings differ"
        )
    sessions = tuple(target_sessions)
    if len(sessions) != diagnostic.plan.target_session_count:
        raise ChinaAshareReconstructedLaneError(
            "reconstructed lane session count differs"
        )
    return build_reconstructed_lane_plan(
        diagnostic_plan_fingerprint=diagnostic.plan.logical_fingerprint,
        diagnostic_package_fingerprint=diagnostic.manifest.logical_fingerprint,
        gap_checklist_fingerprint=gap_checklist.logical_fingerprint,
        normalized_run_fingerprint=diagnostic.plan.normalized_run_fingerprint,
        normalized_partition_manifest_fingerprints=(
            diagnostic.plan.normalized_partition_manifest_fingerprints
        ),
        target_sessions=sessions,
        target_session_set_fingerprint=target_session_set_fingerprint(sessions),
        locally_deterministic_steps=tuple(
            sorted(
                (
                    "factor_change_candidate_detection",
                    "next_observed_session_date_mapping",
                    "provider_state_conservative_partition",
                    "resolved_identity_state_keys",
                )
            )
        ),
        free_official_evidence_required=tuple(
            sorted(
                (
                    "cninfo_corporate_action_terms",
                    "exchange_effective_dated_price_limit_rules",
                    "exchange_effective_dated_warning_changes",
                    "exchange_listed_security_terminal_notices",
                    "official_sse_szse_session_calendar_binding",
                    "official_board_evidence_for_quarantined_identities",
                )
            )
        ),
        isolate_or_exclude_rules=tuple(
            sorted(
                (
                    "factor_change_candidate_window_quarantine",
                    "last_session_without_next_clock_quarantine",
                    "quarantined_identity_target_isolation",
                    "risk_warning_candidate_exclusion",
                    "terminal_boundary_candidate_quarantine",
                    "unknown_price_limit_quarantine",
                )
            )
        ),
        knowledge_clock_policy="next_observed_session_date_only",
        source_clock_fabrication_authorized=False,
        as_operated_claim_authorized=False,
        corporate_action_candidate_windows_fail_closed=True,
        unknown_price_limit_fail_closed=True,
        terminal_boundary_candidates_fail_closed=True,
        future_return_read_count=0,
        historical_coverage_authorized=False,
        research_backtest_authorized=False,
        factor_discovery_authorized=False,
        product_publication_authorized=False,
    )


def build_china_ashare_reconstructed_partition(
    *,
    plan: ChinaAshareReconstructedLanePlanV1,
    partition: ChinaAshareNormalizedExpansionPartitionResultV1,
) -> tuple[
    tuple[ChinaAshareReconstructedUniverseDecisionV1, ...],
    ChinaAshareReconstructedPartitionAggregateV1,
]:
    index = partition.manifest.partition_index
    if (
        index >= len(plan.normalized_partition_manifest_fingerprints)
        or plan.normalized_partition_manifest_fingerprints[index]
        != partition.manifest.logical_fingerprint
    ):
        raise ChinaAshareReconstructedLaneError(
            "reconstructed partition binding differs"
        )
    states = partition.normalized.states
    if any(item.source_available_at is not None for item in states):
        raise ChinaAshareReconstructedLaneError(
            "reconstructed lane cannot replace observed source clocks"
        )
    next_session = {
        current: following
        for current, following in zip(plan.target_sessions, plan.target_sessions[1:])
    }
    factor_changes = _factor_change_keys(partition)
    last_state_by_instrument = {}
    for state in states:
        last_state_by_instrument[state.instrument_id] = max(
            state.session_date,
            last_state_by_instrument.get(state.instrument_id, state.session_date),
        )
    decisions = []
    final_target_session = plan.target_sessions[-1]
    for state in states:
        knowledge_session = next_session.get(state.session_date)
        action_candidate = (state.instrument_id, state.session_date) in factor_changes
        terminal_candidate = (
            state.session_date == last_state_by_instrument[state.instrument_id]
            and state.session_date < final_target_session
        )
        disposition = ChinaAshareReconstructedDisposition.CANDIDATE_INCLUDED
        reasons = {
            "not_as_operated",
            "source_available_at_unobserved",
        }
        if knowledge_session is None:
            disposition = ChinaAshareReconstructedDisposition.QUARANTINED
            reasons.add("next_session_knowledge_clock_unavailable")
        else:
            reasons.add("next_session_reconstructed_knowledge_clock")
        if state.trading_status is ChinaAshareTradingStatus.NOT_LISTED:
            disposition = ChinaAshareReconstructedDisposition.CANDIDATE_EXCLUDED
            reasons.add("not_listed_state_exclusion_candidate")
        elif state.trading_status is ChinaAshareTradingStatus.UNKNOWN:
            disposition = ChinaAshareReconstructedDisposition.QUARANTINED
            reasons.add("trading_status_unknown")
        elif state.trading_status is ChinaAshareTradingStatus.SUSPENDED:
            reasons.add("suspension_observed_reconstructed")
        if state.risk_warning_status is ChinaAshareRiskWarningStatus.UNKNOWN:
            disposition = ChinaAshareReconstructedDisposition.QUARANTINED
            reasons.add("risk_warning_status_unknown")
        elif state.risk_warning_status is not ChinaAshareRiskWarningStatus.NONE:
            disposition = ChinaAshareReconstructedDisposition.CANDIDATE_EXCLUDED
            reasons.add("risk_warning_exclusion_candidate")
        if state.price_limit_regime is ChinaAsharePriceLimitRegime.UNKNOWN:
            disposition = ChinaAshareReconstructedDisposition.QUARANTINED
            reasons.add("price_limit_regime_unknown")
        if action_candidate:
            disposition = ChinaAshareReconstructedDisposition.QUARANTINED
            reasons.add("factor_change_candidate_window")
        if terminal_candidate:
            disposition = ChinaAshareReconstructedDisposition.QUARANTINED
            reasons.add("terminal_boundary_not_adjudicated")
        decisions.append(
            build_reconstructed_universe_decision(
                instrument_id=state.instrument_id,
                evidence_session_date=state.session_date,
                knowledge_session_date=knowledge_session,
                trading_status=state.trading_status,
                risk_warning_status=state.risk_warning_status,
                price_limit_regime=state.price_limit_regime,
                factor_change_candidate_window=action_candidate,
                terminal_boundary_candidate=terminal_candidate,
                disposition=disposition,
                reason_codes=tuple(sorted(reasons)),
                source_available_at=None,
                knowledge_clock_basis="next_observed_session_date_only",
                as_operated=False,
                research_eligible=False,
                input_partition_manifest_fingerprint=(
                    partition.manifest.logical_fingerprint
                ),
            )
        )
    ordered = tuple(decisions)
    aggregate = build_reconstructed_partition_aggregate(
        plan_fingerprint=plan.logical_fingerprint,
        partition_index=index,
        normalized_partition_manifest_fingerprint=(
            partition.manifest.logical_fingerprint
        ),
        decision_count=len(ordered),
        next_session_mapped_count=sum(
            item.knowledge_session_date is not None for item in ordered
        ),
        no_next_session_count=sum(
            item.knowledge_session_date is None for item in ordered
        ),
        candidate_included_count=_disposition_count(
            ordered, ChinaAshareReconstructedDisposition.CANDIDATE_INCLUDED
        ),
        candidate_excluded_count=_disposition_count(
            ordered, ChinaAshareReconstructedDisposition.CANDIDATE_EXCLUDED
        ),
        quarantined_count=_disposition_count(
            ordered, ChinaAshareReconstructedDisposition.QUARANTINED
        ),
        unknown_price_limit_count=sum(
            item.price_limit_regime is ChinaAsharePriceLimitRegime.UNKNOWN
            for item in ordered
        ),
        risk_warning_exclusion_candidate_count=sum(
            item.risk_warning_status
            not in {
                ChinaAshareRiskWarningStatus.NONE,
                ChinaAshareRiskWarningStatus.UNKNOWN,
            }
            for item in ordered
        ),
        factor_change_candidate_window_count=sum(
            item.factor_change_candidate_window for item in ordered
        ),
        terminal_boundary_candidate_count=sum(
            item.terminal_boundary_candidate for item in ordered
        ),
        decision_set_fingerprint=reconstructed_decision_set_fingerprint(ordered),
        future_return_read_count=0,
        as_operated_claim_authorized=False,
        research_backtest_authorized=False,
    )
    return ordered, aggregate


def _factor_change_keys(partition):
    changed = set()
    previous_instrument = None
    previous_factors = None
    for item in partition.normalized.adjustments:
        factors = (
            item.provider_factor,
            item.fore_adjust_factor,
            item.back_adjust_factor,
        )
        if item.instrument_id == previous_instrument and factors != previous_factors:
            changed.add((item.instrument_id, item.session_date))
        previous_instrument = item.instrument_id
        previous_factors = factors
    return changed


def _disposition_count(decisions, disposition):
    return sum(item.disposition is disposition for item in decisions)
