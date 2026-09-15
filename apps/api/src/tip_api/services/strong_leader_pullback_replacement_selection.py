"""One-run replacement selection over the immutable V1 development report."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from tip_api.contracts.analytics.v1 import (
    DEVELOPMENT_STATISTICS_ENDPOINT_SCENARIOS,
    DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT,
    REPLACEMENT_SELECTION_COST_BPS_PER_SIDE,
    REPLACEMENT_SELECTION_GATE_IDS,
    REPLACEMENT_SELECTION_MAXIMUM_SESSION_CONCENTRATION,
    REPLACEMENT_SELECTION_MINIMUM_POSITIVE_SESSION_RATIO,
    REPLACEMENT_SELECTION_POLICY_FINGERPRINT,
    REPLACEMENT_SELECTION_PRIMARY_HORIZON,
    REPLACEMENT_SELECTION_SOURCE_REPORT_FINGERPRINT,
    REPLACEMENT_SELECTION_SOURCE_REPORT_SHA256,
    DevelopmentEndpointScenario,
    DevelopmentSelectionStatus,
    ReplacementParameterEligibilityV1,
    ReplacementSelectionGateV1,
    ReplacementSelectionStatus,
    StrongLeaderPullbackReplacementParameterLockV1,
    StrongLeaderPullbackReplacementSelectionProtocolV1,
    StrongLeaderPullbackReplacementSelectionReportV1,
    StrongLeaderPullbackDevelopmentParameterSummaryV1,
    StrongLeaderPullbackDevelopmentStatisticsReportV1,
    replacement_selection_fingerprint,
    strong_leader_pullback_replacement_selection_protocol_v1,
)


_ZERO_RETURN = "0.0000000000"


class StrongLeaderPullbackReplacementSelectionError(RuntimeError):
    """Raised when the one-run replacement selection cannot be trusted."""


@dataclass(frozen=True, slots=True)
class ReplacementSelectionDecision:
    eligibility: tuple[ReplacementParameterEligibilityV1, ...]
    common_eligible_parameter_count: int
    endpoint_winner_ids: dict[str, str | None]
    provisional_winner_id: str | None
    gate_results: tuple[ReplacementSelectionGateV1, ...]
    selection_status: ReplacementSelectionStatus
    selected_parameter_combination_id: str | None
    reason_codes: tuple[str, ...]


def evaluate_strong_leader_pullback_replacement_selection(
    *,
    source_report: StrongLeaderPullbackDevelopmentStatisticsReportV1,
    source_report_sha256: str,
    protocol: StrongLeaderPullbackReplacementSelectionProtocolV1,
    implementation_revision: str,
    created_at: datetime,
) -> StrongLeaderPullbackReplacementSelectionReportV1:
    """Apply the committed replacement policy to its one exact source report."""

    checked_source = StrongLeaderPullbackDevelopmentStatisticsReportV1.model_validate(
        source_report.model_dump(mode="json")
    )
    checked_protocol = (
        StrongLeaderPullbackReplacementSelectionProtocolV1.model_validate(
            protocol.model_dump(mode="json")
        )
    )
    canonical_protocol = strong_leader_pullback_replacement_selection_protocol_v1()
    if (
        source_report_sha256 != REPLACEMENT_SELECTION_SOURCE_REPORT_SHA256
        or checked_source.logical_fingerprint
        != REPLACEMENT_SELECTION_SOURCE_REPORT_FINGERPRINT
        or checked_source.policy_fingerprint
        != DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT
        or checked_source.selection_status
        is not DevelopmentSelectionStatus.INCONCLUSIVE_EVIDENCE_FLOOR
        or checked_source.selected_parameter_combination_id is not None
        or checked_source.parameter_lock is not None
        or checked_source.validation_data_accessed
        or checked_source.holdout_data_accessed
        or checked_source.validation_transition_authorized
        or checked_source.performance_claim_authorized
        or checked_source.candidate_activation_authorized
        or checked_source.publication_authorized
    ):
        raise StrongLeaderPullbackReplacementSelectionError(
            "replacement source report differs from the registered V1 result"
        )
    if checked_protocol != canonical_protocol:
        raise StrongLeaderPullbackReplacementSelectionError(
            "replacement protocol differs from the registered policy"
        )
    checked_at = _aware_utc(created_at)
    if len(implementation_revision) != 40 or any(
        item not in "0123456789abcdef" for item in implementation_revision
    ):
        raise StrongLeaderPullbackReplacementSelectionError(
            "replacement implementation revision differs"
        )

    decision = apply_replacement_selection_policy(checked_source.summaries)
    return _build_selection_report(
        decision=decision,
        protocol=checked_protocol,
        implementation_revision=implementation_revision,
        created_at=checked_at,
    )


def _build_selection_report(
    *,
    decision: ReplacementSelectionDecision,
    protocol: StrongLeaderPullbackReplacementSelectionProtocolV1,
    implementation_revision: str,
    created_at: datetime,
) -> StrongLeaderPullbackReplacementSelectionReportV1:
    parameter_lock = None
    if decision.selection_status is ReplacementSelectionStatus.LOCKED:
        parameter_lock = _build_parameter_lock(decision)
    payload = {
        "implementation_revision": implementation_revision,
        "created_at": created_at,
        "protocol_fingerprint": REPLACEMENT_SELECTION_POLICY_FINGERPRINT,
        "protocol_logical_fingerprint": protocol.logical_fingerprint,
        "source_report_sha256": REPLACEMENT_SELECTION_SOURCE_REPORT_SHA256,
        "source_report_fingerprint": REPLACEMENT_SELECTION_SOURCE_REPORT_FINGERPRINT,
        "source_selection_status": "inconclusive_evidence_floor",
        "source_summary_count": 216,
        "parameter_combination_count": 24,
        "eligibility": decision.eligibility,
        "common_eligible_parameter_count": (
            decision.common_eligible_parameter_count
        ),
        "endpoint_winner_ids": decision.endpoint_winner_ids,
        "provisional_winner_id": decision.provisional_winner_id,
        "gate_results": decision.gate_results,
        "selection_status": decision.selection_status,
        "selected_parameter_combination_id": (
            decision.selected_parameter_combination_id
        ),
        "parameter_lock": parameter_lock,
        "reason_codes": decision.reason_codes,
    }
    provisional = StrongLeaderPullbackReplacementSelectionReportV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return StrongLeaderPullbackReplacementSelectionReportV1.model_validate(
        {
            **payload,
            "logical_fingerprint": replacement_selection_fingerprint(provisional),
        }
    )


def apply_replacement_selection_policy(
    summaries: tuple[StrongLeaderPullbackDevelopmentParameterSummaryV1, ...],
) -> ReplacementSelectionDecision:
    """Apply only the already-registered selection rules to summary rows."""

    primary = tuple(
        item
        for item in summaries
        if item.horizon_sessions == REPLACEMENT_SELECTION_PRIMARY_HORIZON
    )
    keys = {
        (item.parameter_combination_id, item.endpoint_scenario) for item in primary
    }
    parameter_ids = tuple(sorted({item.parameter_combination_id for item in primary}))
    if len(primary) != 72 or len(keys) != 72 or len(parameter_ids) != 24:
        raise StrongLeaderPullbackReplacementSelectionError(
            "replacement primary summary family differs"
        )
    by_key = {
        (item.parameter_combination_id, item.endpoint_scenario): item
        for item in primary
    }
    global_unavailable = any(
        item.signal_disposition.unavailable_evidence_count
        or item.control_disposition.unavailable_evidence_count
        for item in primary
    )
    eligibility = tuple(
        _parameter_eligibility(parameter_id, by_key)
        for parameter_id in parameter_ids
    )
    common_eligible = tuple(
        item.parameter_combination_id
        for item in eligibility
        if item.eligible_in_all_endpoint_scenarios
    )
    empty_winners = {item: None for item in DEVELOPMENT_STATISTICS_ENDPOINT_SCENARIOS}
    if global_unavailable:
        return ReplacementSelectionDecision(
            eligibility=eligibility,
            common_eligible_parameter_count=len(common_eligible),
            endpoint_winner_ids=empty_winners,
            provisional_winner_id=None,
            gate_results=(),
            selection_status=ReplacementSelectionStatus.BLOCKED_SOURCE_EVIDENCE,
            selected_parameter_combination_id=None,
            reason_codes=("primary_family_contains_unavailable_source_evidence",),
        )
    if not common_eligible:
        return ReplacementSelectionDecision(
            eligibility=eligibility,
            common_eligible_parameter_count=0,
            endpoint_winner_ids=empty_winners,
            provisional_winner_id=None,
            gate_results=(),
            selection_status=ReplacementSelectionStatus.REJECTED_NO_COMMON_ELIGIBLE,
            selected_parameter_combination_id=None,
            reason_codes=("no_parameter_is_eligible_in_every_endpoint_scenario",),
        )

    endpoint_winners = {
        scenario.value: _endpoint_winner(
            scenario=scenario,
            parameter_ids=common_eligible,
            by_key=by_key,
        )
        for scenario in DevelopmentEndpointScenario
    }
    winner_values = tuple(endpoint_winners.values())
    if len(set(winner_values)) != 1:
        return ReplacementSelectionDecision(
            eligibility=eligibility,
            common_eligible_parameter_count=len(common_eligible),
            endpoint_winner_ids=endpoint_winners,
            provisional_winner_id=None,
            gate_results=(),
            selection_status=ReplacementSelectionStatus.REJECTED_ENDPOINT_INSTABILITY,
            selected_parameter_combination_id=None,
            reason_codes=("endpoint_scenarios_select_different_parameters",),
        )

    provisional_winner = winner_values[0]
    if provisional_winner is None:
        raise StrongLeaderPullbackReplacementSelectionError(
            "eligible endpoint winner is missing"
        )
    adverse = by_key[
        (provisional_winner, DevelopmentEndpointScenario.CONTRAST_ADVERSE)
    ]
    gates = _robustness_gates(adverse)
    passed = all(item.passed for item in gates)
    failed = tuple(item.gate_id for item in gates if not item.passed)
    return ReplacementSelectionDecision(
        eligibility=eligibility,
        common_eligible_parameter_count=len(common_eligible),
        endpoint_winner_ids=endpoint_winners,
        provisional_winner_id=provisional_winner,
        gate_results=gates,
        selection_status=(
            ReplacementSelectionStatus.LOCKED
            if passed
            else ReplacementSelectionStatus.REJECTED_ROBUSTNESS_GATES
        ),
        selected_parameter_combination_id=(provisional_winner if passed else None),
        reason_codes=(
            ("parameter_locked_formal_validation_review_required",)
            if passed
            else tuple(sorted(f"failed_{item}" for item in failed))
        ),
    )


def _parameter_eligibility(parameter_id, by_key):
    eligible_scenarios = []
    reasons = []
    for scenario in DevelopmentEndpointScenario:
        summary = by_key[(parameter_id, scenario)]
        scenario_reasons = []
        if not summary.inference_available:
            scenario_reasons.append("inference_unavailable")
        if summary.signal_disposition.numeric_count < 60:
            scenario_reasons.append("signal_floor_not_met")
        if summary.control_disposition.numeric_count < 60:
            scenario_reasons.append("control_floor_not_met")
        if summary.paired_session_count < 20:
            scenario_reasons.append("comparable_session_floor_not_met")
        if (
            summary.signal_disposition.unavailable_evidence_count
            or summary.control_disposition.unavailable_evidence_count
        ):
            scenario_reasons.append("unavailable_source_evidence")
        if not scenario_reasons:
            eligible_scenarios.append(scenario.value)
        reasons.extend(f"{scenario.value}:{item}" for item in scenario_reasons)
    return ReplacementParameterEligibilityV1(
        parameter_combination_id=parameter_id,
        eligible_in_all_endpoint_scenarios=len(eligible_scenarios) == 3,
        eligible_endpoint_scenarios=tuple(sorted(eligible_scenarios)),
        reason_codes=tuple(sorted(set(reasons))),
    )


def _endpoint_winner(*, scenario, parameter_ids, by_key):
    candidates = tuple(by_key[(item, scenario)] for item in parameter_ids)
    return sorted(
        candidates,
        key=lambda item: (
            -Decimal(_required(item.contrast_lower_90pct, "contrast lower bound")),
            -Decimal(
                _required(item.session_balanced_mean_contrast, "mean contrast")
            ),
            -item.signal_disposition.numeric_count,
            item.parameter_combination_id,
        ),
    )[0].parameter_combination_id


def _robustness_gates(summary):
    cost = next(
        (
            item
            for item in summary.cost_metrics
            if item.basis_points_per_side
            == REPLACEMENT_SELECTION_COST_BPS_PER_SIDE
        ),
        None,
    )
    first = next(
        (
            item
            for item in summary.stability_slices
            if item.slice_type == "chronological_half"
            and item.slice_code == "first_half"
        ),
        None,
    )
    second = next(
        (
            item
            for item in summary.stability_slices
            if item.slice_type == "chronological_half"
            and item.slice_code == "second_half"
        ),
        None,
    )
    values = (
        summary.contrast_lower_90pct,
        None if cost is None else cost.signal_median_spy_relative_return_net,
        None if first is None else first.session_balanced_mean_contrast,
        None if second is None else second.session_balanced_mean_contrast,
        summary.positive_paired_session_ratio,
        summary.largest_absolute_session_contrast_share,
    )
    comparisons = (
        "strictly_greater_than",
        "strictly_greater_than",
        "strictly_greater_than",
        "strictly_greater_than",
        "strictly_greater_than",
        "less_than_or_equal_to",
    )
    thresholds = (
        _ZERO_RETURN,
        _ZERO_RETURN,
        _ZERO_RETURN,
        _ZERO_RETURN,
        REPLACEMENT_SELECTION_MINIMUM_POSITIVE_SESSION_RATIO,
        REPLACEMENT_SELECTION_MAXIMUM_SESSION_CONCENTRATION,
    )
    return tuple(
        ReplacementSelectionGateV1(
            gate_id=gate_id,
            observed_value=value,
            comparison=comparison,
            threshold=threshold,
            passed=(
                False
                if value is None
                else (
                    Decimal(value) > Decimal(threshold)
                    if comparison == "strictly_greater_than"
                    else Decimal(value) <= Decimal(threshold)
                )
            ),
        )
        for gate_id, value, comparison, threshold in zip(
            REPLACEMENT_SELECTION_GATE_IDS,
            values,
            comparisons,
            thresholds,
            strict=True,
        )
    )


def _build_parameter_lock(decision):
    if decision.selected_parameter_combination_id is None:
        raise StrongLeaderPullbackReplacementSelectionError(
            "replacement lock requires a selected parameter"
        )
    gate_fingerprint = replacement_selection_fingerprint(
        {
            "gate_results": [
                item.model_dump(mode="json") for item in decision.gate_results
            ]
        },
        exclude=set(),
    )
    payload = {
        "parameter_combination_id": decision.selected_parameter_combination_id,
        "endpoint_winner_ids": decision.endpoint_winner_ids,
        "gate_results_fingerprint": gate_fingerprint,
    }
    provisional = StrongLeaderPullbackReplacementParameterLockV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return StrongLeaderPullbackReplacementParameterLockV1.model_validate(
        {
            **payload,
            "logical_fingerprint": replacement_selection_fingerprint(provisional),
        }
    )


def _required(value: str | None, field: str) -> str:
    if value is None:
        raise StrongLeaderPullbackReplacementSelectionError(
            f"eligible replacement summary lacks {field}"
        )
    return value


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise StrongLeaderPullbackReplacementSelectionError(
            "replacement selection time must be timezone-aware"
        )
    return value.astimezone(UTC)
