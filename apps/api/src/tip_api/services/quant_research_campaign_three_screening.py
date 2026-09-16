"""Deterministic Development-only evaluator for Campaign Three interactions."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_EVEN
from random import Random
from statistics import mean

from tip_api.contracts.analytics.v1.quant_research_campaign_three_development_access import (
    CampaignThreeDevelopmentAccessGrantV1,
    CampaignThreeDevelopmentAccessRequestV1,
    validate_campaign_three_development_grant,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_hypotheses import (
    MARKET_STATE_ARTIFACT_CONTENT_SHA256,
    MARKET_STATE_ARTIFACT_IDENTITY_FINGERPRINT,
    CampaignThreeHypothesisRole,
    quant_research_campaign_three_hypothesis_registry_v1,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_input_qualification import (
    V1_FACTOR_DIAGNOSTICS_FINGERPRINT,
    V1_FACTOR_DIAGNOSTICS_SHA256,
    V2_FACTOR_QUALIFICATION_FINGERPRINT,
    V2_FACTOR_QUALIFICATION_SHA256,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_screening import (
    CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT,
    CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256,
    quant_research_campaign_three_screening_protocol_v1,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_screening_result import (
    CampaignThreeInteractionSummaryV1,
    CampaignThreeScreeningDecisionV1,
    CampaignThreeScreeningReportV1,
    CampaignThreeSessionEvidenceV1,
    build_campaign_three_screening_report_v1,
    screening_result_fingerprint,
)
from tip_api.contracts.analytics.v1.quant_research_discovery_trial_ledger_v4 import (
    quant_research_discovery_trial_ledger_v4,
)
from tip_api.contracts.analytics.v1.quant_research_factor_catalog import (
    QuantResearchFactorAvailability,
    QuantResearchFactorObservationV1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QuantResearchFactorAvailabilityV2,
    QuantResearchFactorObservationV2,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_result import (
    QuantResearchFactorScreeningDecisionStatus,
    QuantResearchFactorScreeningEndpoint,
    QuantResearchFactorScreeningLabelState,
    QuantResearchFactorScreeningReportStatus,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_result_v2 import (
    QuantResearchFactorScreeningLabelV2,
)
from tip_api.contracts.analytics.v1.quant_research_market_state_qualification import (
    QuantResearchMarketStateAvailability,
    QuantResearchMarketStateQualificationReportV1,
)
from tip_api.contracts.analytics.v1.quant_research_reusable_artifacts_v2 import (
    MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT,
    MARKET_STATE_QUALIFICATION_REPORT_SHA256,
)
from tip_api.services.quant_research_factor_screening import (
    QuantResearchFactorScreeningError,
    calculate_holm_adjustment,
    calculate_spearman,
)


_QUANTUM = Decimal("0.0000000001")
_NUMERIC_ALPHA_STATES = {
    QuantResearchFactorScreeningLabelState.OBSERVED_EOD_EXACT,
    QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_EXACT,
    QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_INTERVAL,
}
_INCONCLUSIVE_CODES = {
    "eligible_session_floor_not_met",
    "first_half_session_floor_not_met",
    "regression_unavailable",
    "second_half_session_floor_not_met",
}


class CampaignThreeScreeningError(ValueError):
    """Raised when the frozen Campaign Three evaluation boundary differs."""


def build_campaign_three_screening_report(
    *,
    v1_observations: tuple[QuantResearchFactorObservationV1, ...],
    v2_observations: tuple[QuantResearchFactorObservationV2, ...],
    labels: tuple[QuantResearchFactorScreeningLabelV2, ...],
    market_state: QuantResearchMarketStateQualificationReportV1,
    market_state_sha256: str,
    access_request: CampaignThreeDevelopmentAccessRequestV1,
    access_grant: CampaignThreeDevelopmentAccessGrantV1,
    implementation_revision: str,
    evaluator_code_sha256: str,
    created_at: datetime,
) -> CampaignThreeScreeningReportV1:
    """Evaluate exactly three preregistered trials without downstream authority."""

    protocol = quant_research_campaign_three_screening_protocol_v1()
    ledger = quant_research_discovery_trial_ledger_v4()
    _validate_authority(
        request=access_request,
        grant=access_grant,
        implementation_revision=implementation_revision,
        created_at=created_at,
    )
    (
        ordered_v1,
        ordered_v2,
        ordered_labels,
        labels_by_key,
        state_by_session,
        development_sessions,
    ) = _validated_inputs(
        v1_observations=v1_observations,
        v2_observations=v2_observations,
        labels=labels,
        market_state=market_state,
        market_state_sha256=market_state_sha256,
    )
    v1_by_key = {
        (item.as_of_session, item.instrument_id): item for item in ordered_v1
    }
    v2_by_key = {
        (item.as_of_session, item.instrument_id): item for item in ordered_v2
    }
    first_half = frozenset(development_sessions[:53])
    second_half = frozenset(development_sessions[53:])
    all_evidence: list[CampaignThreeSessionEvidenceV1] = []
    summaries: list[CampaignThreeInteractionSummaryV1] = []
    for hypothesis in protocol.formal_hypotheses:
        for horizon in (1, 3, 5):
            endpoints = (
                (
                    QuantResearchFactorScreeningEndpoint.LOWER,
                    QuantResearchFactorScreeningEndpoint.UPPER,
                )
                if hypothesis.role
                is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
                else (QuantResearchFactorScreeningEndpoint.COMPLETE_PATH,)
            )
            for endpoint in endpoints:
                evidence = _session_evidence(
                    hypothesis=hypothesis,
                    horizon=horizon,
                    endpoint=endpoint,
                    development_sessions=development_sessions,
                    v1_by_key=v1_by_key,
                    v2_by_key=v2_by_key,
                    labels_by_key=labels_by_key,
                    state_by_session=state_by_session,
                )
                all_evidence.extend(evidence)
                summaries.append(
                    _summarize(
                        hypothesis=hypothesis,
                        horizon=horizon,
                        endpoint=endpoint,
                        evidence=evidence,
                        first_half=first_half,
                        second_half=second_half,
                    )
                )
    typed_summaries = tuple(summaries)
    decisions, selected_alpha, selected_risk = _decisions(typed_summaries)
    any_inconclusive_alpha = any(
        item.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
        and item.status is QuantResearchFactorScreeningDecisionStatus.INCONCLUSIVE_DATA
        for item in decisions
    )
    if selected_alpha:
        status = QuantResearchFactorScreeningReportStatus.READY_FOR_MODEL_PROTOCOL_REVIEW
        reasons = ("at_least_one_candidate_alpha_selected",)
    elif any_inconclusive_alpha:
        status = QuantResearchFactorScreeningReportStatus.INCONCLUSIVE_DATA
        reasons = ("candidate_alpha_screen_has_inconclusive_data",)
    else:
        status = QuantResearchFactorScreeningReportStatus.CLOSED_NO_CANDIDATE_ALPHA
        reasons = ("no_candidate_alpha_passed_frozen_screen",)
    evidence_tuple = tuple(all_evidence)
    payload = {
        "protocol_fingerprint": protocol.logical_fingerprint,
        "registered_ledger_fingerprint": ledger.logical_fingerprint,
        "access_request_fingerprint": access_request.logical_fingerprint,
        "access_grant_fingerprint": access_grant.logical_fingerprint,
        "implementation_revision": implementation_revision,
        "evaluator_code_sha256": evaluator_code_sha256,
        "created_at": created_at.astimezone(UTC),
        "source_input_qualification_fingerprint": (
            CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT
        ),
        "source_input_qualification_sha256": CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256,
        "source_v1_diagnostics_fingerprint": V1_FACTOR_DIAGNOSTICS_FINGERPRINT,
        "source_v1_diagnostics_sha256": V1_FACTOR_DIAGNOSTICS_SHA256,
        "source_v2_qualification_fingerprint": V2_FACTOR_QUALIFICATION_FINGERPRINT,
        "source_v2_qualification_sha256": V2_FACTOR_QUALIFICATION_SHA256,
        "source_market_state_fingerprint": market_state.logical_fingerprint,
        "source_market_state_sha256": market_state_sha256,
        "source_market_state_artifact_identity_fingerprint": (
            MARKET_STATE_ARTIFACT_IDENTITY_FINGERPRINT
        ),
        "source_market_state_artifact_content_sha256": (
            MARKET_STATE_ARTIFACT_CONTENT_SHA256
        ),
        "source_v1_observation_collection_fingerprint": _collection_fingerprint(
            ordered_v1
        ),
        "source_v2_observation_collection_fingerprint": _collection_fingerprint(
            ordered_v2
        ),
        "source_label_collection_fingerprint": _collection_fingerprint(ordered_labels),
        "source_v1_eod_fingerprint": _single_value(
            item.source_eod_fingerprint for item in ordered_v1
        ),
        "source_v1_adjustment_fingerprint": _single_value(
            item.source_adjustment_fingerprint for item in ordered_v1
        ),
        "source_v2_eod_fingerprint": _single_value(
            item.source_eod_fingerprint for item in ordered_v2
        ),
        "source_v2_adjustment_fingerprint": _single_value(
            item.source_adjustment_fingerprint for item in ordered_v2
        ),
        "source_label_action_fingerprint": _single_value(
            item.source_action_fingerprint for item in ordered_labels
        ),
        "source_label_adjustment_fingerprint": _single_value(
            item.source_adjustment_fingerprint for item in ordered_labels
        ),
        "source_terminal_reference_collection_fingerprint": _fingerprint(
            sorted(
                item.terminal_reference_fingerprint
                for item in ordered_labels
                if item.terminal_reference_fingerprint is not None
            )
        ),
        "session_evidence_collection_fingerprint": _collection_fingerprint(
            evidence_tuple
        ),
        "aligned_observation_count": len(ordered_v1),
        "label_count": len(ordered_labels),
        "label_state_counts": {
            state.value: sum(item.state is state for item in ordered_labels)
            for state in QuantResearchFactorScreeningLabelState
        },
        "session_evidence": evidence_tuple,
        "summaries": typed_summaries,
        "decisions": decisions,
        "selected_candidate_alpha_ids": selected_alpha,
        "selected_risk_guard_ids": selected_risk,
        "status": status,
        "reason_codes": reasons,
        "limitation_codes": (
            "cost_scenarios_declared_but_no_strategy_expression_exists",
            "development_selection_evidence_not_validated_alpha",
            "historical_classification_unavailable",
            "reconstructed_membership_not_as_operated",
            "split_neutral_absence_unproven",
            "temporal_coverage_limited_to_106_development_sessions",
        ),
    }
    return build_campaign_three_screening_report_v1(**payload)


def calculate_interaction_regression(
    state_values: tuple[float, ...], rank_ics: tuple[float, ...]
) -> tuple[float, float]:
    if (
        len(state_values) != len(rank_ics)
        or len(state_values) < 2
        or any(not math.isfinite(item) for item in (*state_values, *rank_ics))
    ):
        raise CampaignThreeScreeningError("interaction regression inputs differ")
    state_mean = mean(state_values)
    rank_mean = mean(rank_ics)
    denominator = sum((item - state_mean) ** 2 for item in state_values)
    if denominator <= 0:
        raise CampaignThreeScreeningError("interaction state has zero variance")
    beta = sum(
        (state - state_mean) * (rank_ic - rank_mean)
        for state, rank_ic in zip(state_values, rank_ics, strict=True)
    ) / denominator
    return rank_mean - beta * state_mean, beta


def calculate_circular_block_interaction_bootstrap(
    *,
    state_values: tuple[float, ...],
    rank_ics: tuple[float, ...],
    block_sessions: int,
    replicates: int,
    seed_material: str,
) -> tuple[float, float]:
    if block_sessions < 1 or replicates < 1 or not seed_material:
        raise CampaignThreeScreeningError("interaction bootstrap settings differ")
    _, observed_beta = calculate_interaction_regression(state_values, rank_ics)
    count = len(state_values)
    block = min(block_sessions, count)
    seed = int.from_bytes(
        hashlib.sha256(
            (
                seed_material
                + ":"
                + ",".join(_string(item) for item in state_values)
                + ":"
                + ",".join(_string(item) for item in rank_ics)
            ).encode("utf-8")
        ).digest()[:8],
        "big",
    )
    generator = Random(seed)
    slopes = []
    null_exceedances = 0
    for _ in range(replicates):
        indices: list[int] = []
        while len(indices) < count:
            start = generator.randrange(count)
            indices.extend((start + offset) % count for offset in range(block))
        indices = indices[:count]
        sampled_state = tuple(state_values[index] for index in indices)
        sampled_rank = tuple(rank_ics[index] for index in indices)
        try:
            _, slope = calculate_interaction_regression(sampled_state, sampled_rank)
        except CampaignThreeScreeningError as exc:
            raise CampaignThreeScreeningError(
                "interaction bootstrap produced a degenerate state sample"
            ) from exc
        slopes.append(slope)
        if slope - observed_beta >= observed_beta:
            null_exceedances += 1
    slopes.sort()
    lower = _quantile(tuple(slopes), 0.10)
    probability = (null_exceedances + 1) / (replicates + 1)
    if not math.isfinite(observed_beta):
        raise CampaignThreeScreeningError("interaction beta is not finite")
    return lower, probability


def _validate_authority(
    *, request, grant, implementation_revision, created_at
) -> None:
    protocol = quant_research_campaign_three_screening_protocol_v1()
    ledger = quant_research_discovery_trial_ledger_v4()
    try:
        validate_campaign_three_development_grant(
            request=request,
            grant=grant,
        )
    except ValueError as exc:
        raise CampaignThreeScreeningError(
            "Campaign Three Development request or grant differs"
        ) from exc
    if (
        request.implementation_revision != implementation_revision
        or grant.protocol_fingerprint != protocol.logical_fingerprint
        or grant.ledger_fingerprint != ledger.logical_fingerprint
        or grant.implementation_revision != implementation_revision
        or not grant.development_outcome_access_authorized
        or created_at.tzinfo is None
        or created_at.utcoffset() is None
        or created_at.utcoffset().total_seconds() != 0
        or created_at < grant.granted_at
    ):
        raise CampaignThreeScreeningError("Campaign Three Development grant differs")


def _validated_inputs(
    *, v1_observations, v2_observations, labels, market_state, market_state_sha256
):
    protocol = quant_research_campaign_three_screening_protocol_v1()
    if (
        market_state.logical_fingerprint != MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
        or market_state_sha256 != MARKET_STATE_QUALIFICATION_REPORT_SHA256
        or market_state.contains_forward_outcomes
        or market_state.development_outcome_read_count
    ):
        raise CampaignThreeScreeningError("Campaign Three market-state source differs")
    ordered_v1 = tuple(
        sorted(v1_observations, key=lambda item: (item.as_of_session, str(item.instrument_id)))
    )
    ordered_v2 = tuple(
        sorted(v2_observations, key=lambda item: (item.as_of_session, str(item.instrument_id)))
    )
    if ordered_v1 != v1_observations or ordered_v2 != v2_observations:
        raise CampaignThreeScreeningError("Campaign Three observations are not ordered")
    v1_keys = tuple((item.as_of_session, item.instrument_id) for item in ordered_v1)
    v2_keys = tuple((item.as_of_session, item.instrument_id) for item in ordered_v2)
    v1_key_set = set(v1_keys)
    v2_by_key = {
        (item.as_of_session, item.instrument_id): item for item in ordered_v2
    }
    sessions = tuple(sorted({item.as_of_session for item in ordered_v1}))
    if (
        not ordered_v1
        or len(ordered_v1) != 167860
        or len(ordered_v2) != 167860
        or v1_keys != v2_keys
        or len(set(v1_keys)) != len(v1_keys)
        or len(sessions) != protocol.development_session_count
        or sessions[0] != protocol.development_first_session
        or sessions[-1] != protocol.development_last_session
        or any(item.contains_forward_outcomes for item in (*ordered_v1, *ordered_v2))
    ):
        raise CampaignThreeScreeningError("Campaign Three observation population differs")
    ordered_labels = tuple(
        sorted(
            labels,
            key=lambda item: (
                item.signal_session,
                str(item.instrument_id),
                item.horizon_sessions,
            ),
        )
    )
    if ordered_labels != labels:
        raise CampaignThreeScreeningError("Campaign Three labels are not ordered")
    label_map = {}
    for label in ordered_labels:
        key = (label.signal_session, label.instrument_id, label.horizon_sessions)
        observation_key = (label.signal_session, label.instrument_id)
        if (
            key in label_map
            or observation_key not in v1_key_set
            or label.observation_fingerprint
            != v2_by_key[observation_key].logical_fingerprint
        ):
            raise CampaignThreeScreeningError("Campaign Three label binding differs")
        label_map[key] = label
    if len(ordered_labels) != 503580 or any(
        (session, instrument_id, horizon) not in label_map
        for session, instrument_id in v1_keys
        for horizon in (1, 3, 5)
    ):
        raise CampaignThreeScreeningError("Campaign Three label population differs")
    state_by_session = {item.as_of_session: item for item in market_state.sessions}
    if not set(sessions).issubset(state_by_session):
        raise CampaignThreeScreeningError("Campaign Three state chronology differs")
    return (
        ordered_v1,
        ordered_v2,
        ordered_labels,
        label_map,
        state_by_session,
        sessions,
    )


def _session_evidence(
    *, hypothesis, horizon, endpoint, development_sessions, v1_by_key, v2_by_key,
    labels_by_key, state_by_session
):
    registry = quant_research_campaign_three_hypothesis_registry_v1()
    source_card = next(
        item
        for item in registry.proposals
        if item.hypothesis_id == hypothesis.hypothesis_id
    )
    rows_by_session = defaultdict(list)
    for key, v1_observation in v1_by_key.items():
        session, instrument_id = key
        source = (
            v1_observation
            if source_card.source_factor_catalog == "v1"
            else v2_by_key[key]
        )
        factor = next(
            item for item in source.factor_values if item.factor_id == hypothesis.source_factor_id
        )
        if (
            factor.factor_definition_fingerprint
            != hypothesis.source_factor_definition_fingerprint
        ):
            raise CampaignThreeScreeningError(
                "Campaign Three factor definition differs"
            )
        available = (
            factor.availability is QuantResearchFactorAvailability.AVAILABLE
            if isinstance(source, QuantResearchFactorObservationV1)
            else factor.availability is QuantResearchFactorAvailabilityV2.AVAILABLE
        )
        if not available or factor.value is None:
            continue
        label = labels_by_key[(session, instrument_id, horizon)]
        target = _target(label=label, role=hypothesis.role, endpoint=endpoint)
        if target is None:
            continue
        oriented = float(factor.value)
        if hypothesis.source_factor_orientation == "sign_reversed_lower_is_safer":
            oriented = -oriented
        rows_by_session[session].append((str(instrument_id), oriented, target))
    evidence = []
    for session in development_sessions:
        rows = tuple(sorted(rows_by_session[session]))
        if len(rows) < 100:
            continue
        state = _state_value(
            state_by_session[session],
            metric_id=hypothesis.state_metric_id,
            transform=hypothesis.state_transform,
        )
        if state is None:
            continue
        try:
            rank_ic = calculate_spearman(
                tuple(item[1] for item in rows), tuple(item[2] for item in rows)
            )
        except QuantResearchFactorScreeningError:
            continue
        evidence.append(
            CampaignThreeSessionEvidenceV1(
                hypothesis_id=hypothesis.hypothesis_id,
                role=hypothesis.role,
                horizon_sessions=horizon,
                endpoint=endpoint,
                signal_session=session,
                instrument_count=len(rows),
                state_value=_string(state),
                session_rank_ic=_string(rank_ic),
            )
        )
    return tuple(evidence)


def _target(*, label, role, endpoint):
    if role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION:
        if label.state not in _NUMERIC_ALPHA_STATES:
            return None
        value = (
            label.relative_to_benchmark_return_lower
            if endpoint is QuantResearchFactorScreeningEndpoint.LOWER
            else label.relative_to_benchmark_return_upper
        )
        return float(value) if value is not None else None
    if (
        endpoint is not QuantResearchFactorScreeningEndpoint.COMPLETE_PATH
        or label.state is not QuantResearchFactorScreeningLabelState.OBSERVED_EOD_EXACT
        or label.maximum_adverse_excursion is None
    ):
        return None
    return float(label.maximum_adverse_excursion)


def _state_value(session, *, metric_id, transform):
    metric = next(item for item in session.metrics if item.metric_id == metric_id)
    if metric.availability is QuantResearchMarketStateAvailability.UNAVAILABLE:
        return None
    assert metric.value is not None
    value = float(metric.value)
    if transform == "2*(share-0.5)":
        return 2 * (value - 0.5)
    if transform == "as_defined":
        return value
    if transform == "-1*spy_log_return_20s":
        return -value
    raise CampaignThreeScreeningError("Campaign Three state transform differs")


def _summarize(*, hypothesis, horizon, endpoint, evidence, first_half, second_half):
    protocol = quant_research_campaign_three_screening_protocol_v1()
    first = tuple(item for item in evidence if item.signal_session in first_half)
    second = tuple(item for item in evidence if item.signal_session in second_half)
    reasons = []
    if len(evidence) < protocol.minimum_primary_sessions:
        reasons.append("eligible_session_floor_not_met")
    if len(first) < protocol.minimum_chronological_half_sessions:
        reasons.append("first_half_session_floor_not_met")
    if len(second) < protocol.minimum_chronological_half_sessions:
        reasons.append("second_half_session_floor_not_met")
    common = {
        "hypothesis_id": hypothesis.hypothesis_id,
        "role": hypothesis.role,
        "horizon_sessions": horizon,
        "endpoint": endpoint,
        "eligible_session_count": len(evidence),
        "first_half_session_count": len(first),
        "second_half_session_count": len(second),
        "evidence_collection_fingerprint": _collection_fingerprint(evidence),
        "favorable_state_session_count": (
            sum(float(item.state_value) > 0 for item in evidence)
            if hypothesis.role
            is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
            else None
        ),
        "favorable_state_mean_rank_ic": None,
    }
    if len(evidence) < 2:
        return CampaignThreeInteractionSummaryV1(
            **common,
            reason_codes=tuple(sorted(set((*reasons, "regression_unavailable")))),
        )
    state = tuple(float(item.state_value) for item in evidence)
    q_values = tuple(float(item.session_rank_ic) for item in evidence)
    try:
        alpha, beta = calculate_interaction_regression(state, q_values)
        primary_lower, primary_p = calculate_circular_block_interaction_bootstrap(
            state_values=state,
            rank_ics=q_values,
            block_sessions=protocol.primary_bootstrap_block_sessions,
            replicates=protocol.bootstrap_replicates,
            seed_material=(
                f"{protocol.logical_fingerprint}:{hypothesis.trial_id}:{horizon}:"
                f"{endpoint.value}:block-{protocol.primary_bootstrap_block_sessions}"
            ),
        )
        sensitivity_lower, sensitivity_p = (
            calculate_circular_block_interaction_bootstrap(
                state_values=state,
                rank_ics=q_values,
                block_sessions=protocol.sensitivity_bootstrap_block_sessions,
                replicates=protocol.bootstrap_replicates,
                seed_material=(
                    f"{protocol.logical_fingerprint}:{hypothesis.trial_id}:{horizon}:"
                    f"{endpoint.value}:block-{protocol.sensitivity_bootstrap_block_sessions}"
                ),
            )
        )
        _, first_beta = calculate_interaction_regression(
            tuple(float(item.state_value) for item in first),
            tuple(float(item.session_rank_ic) for item in first),
        )
        _, second_beta = calculate_interaction_regression(
            tuple(float(item.state_value) for item in second),
            tuple(float(item.session_rank_ic) for item in second),
        )
    except CampaignThreeScreeningError:
        return CampaignThreeInteractionSummaryV1(
            **common,
            reason_codes=tuple(sorted(set((*reasons, "regression_unavailable")))),
        )
    favorable = tuple(
        float(item.session_rank_ic)
        for item in evidence
        if float(item.state_value) > 0
    )
    return CampaignThreeInteractionSummaryV1(
        **{
            **common,
            "favorable_state_mean_rank_ic": (
                _string(mean(favorable))
                if favorable
                and hypothesis.role
                is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
                else None
            ),
        },
        regression_alpha=_string(alpha),
        interaction_beta=_string(beta),
        primary_block_lower_90pct=_string(primary_lower),
        primary_block_one_sided_p_value=_string(primary_p),
        sensitivity_block_lower_90pct=_string(sensitivity_lower),
        sensitivity_block_one_sided_p_value=_string(sensitivity_p),
        first_half_beta=_string(first_beta),
        second_half_beta=_string(second_beta),
        reason_codes=tuple(sorted(set(reasons))),
    )


def _decisions(summaries):
    protocol = quant_research_campaign_three_screening_protocol_v1()
    primary_by_id = defaultdict(list)
    for summary in summaries:
        if summary.horizon_sessions == protocol.primary_horizon_sessions:
            primary_by_id[summary.hypothesis_id].append(summary)
    raw_by_role = defaultdict(dict)
    provisional = {}
    for hypothesis in protocol.formal_hypotheses:
        primary = tuple(primary_by_id[hypothesis.hypothesis_id])
        probabilities = tuple(
            float(value)
            for item in primary
            for value in (
                item.primary_block_one_sided_p_value,
                item.sensitivity_block_one_sided_p_value,
            )
            if value is not None
        )
        raw = max(probabilities) if len(probabilities) == len(primary) * 2 else 1.0
        raw_by_role[hypothesis.role.value][hypothesis.hypothesis_id] = raw
        provisional[hypothesis.hypothesis_id] = (hypothesis, primary, raw)
    adjusted = {
        role: calculate_holm_adjustment(values) if values else {}
        for role, values in raw_by_role.items()
    }
    decision_payloads = []
    for hypothesis in protocol.formal_hypotheses:
        _, primary, raw = provisional[hypothesis.hypothesis_id]
        holm = adjusted[hypothesis.role.value].get(hypothesis.hypothesis_id)
        failures = set()
        if any(item.reason_codes for item in primary):
            failures.update(code for item in primary for code in item.reason_codes)
        for item in primary:
            if item.interaction_beta is None or float(item.interaction_beta) <= 0:
                failures.add("interaction_beta_not_positive")
            if (
                item.primary_block_lower_90pct is None
                or float(item.primary_block_lower_90pct) <= 0
            ):
                failures.add("primary_block_lower_bound_not_positive")
            if (
                item.sensitivity_block_lower_90pct is None
                or float(item.sensitivity_block_lower_90pct) <= 0
            ):
                failures.add("sensitivity_block_lower_bound_not_positive")
            if item.first_half_beta is None or float(item.first_half_beta) <= 0:
                failures.add("first_half_beta_not_positive")
            if item.second_half_beta is None or float(item.second_half_beta) <= 0:
                failures.add("second_half_beta_not_positive")
            if (
                hypothesis.role
                is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
            ):
                if (
                    item.favorable_state_session_count is None
                    or item.favorable_state_session_count
                    < protocol.alpha_favorable_state_minimum_sessions
                ):
                    failures.add("alpha_favorable_state_session_floor_not_met")
                if (
                    item.favorable_state_mean_rank_ic is None
                    or float(item.favorable_state_mean_rank_ic) <= 0
                ):
                    failures.add("alpha_favorable_state_mean_rank_ic_not_positive")
        if holm is None or holm > float(protocol.one_sided_familywise_alpha):
            failures.add("holm_familywise_gate_failed")
        betas = tuple(
            float(item.interaction_beta)
            for item in primary
            if item.interaction_beta is not None
        )
        lowers = tuple(
            min(
                float(item.primary_block_lower_90pct),
                float(item.sensitivity_block_lower_90pct),
            )
            for item in primary
            if item.primary_block_lower_90pct is not None
            and item.sensitivity_block_lower_90pct is not None
        )
        inconclusive = any(code in _INCONCLUSIVE_CODES for code in failures)
        decision_payloads.append(
            {
                "hypothesis": hypothesis,
                "raw": raw,
                "holm": holm,
                "beta": min(betas) if len(betas) == len(primary) else None,
                "lower": min(lowers) if len(lowers) == len(primary) else None,
                "failures": tuple(sorted(failures)),
                "inconclusive": inconclusive,
            }
        )
    passing_alpha = _ranked(
        item
        for item in decision_payloads
        if not item["failures"]
        and item["hypothesis"].role
        is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
    )
    selected_alpha_payload = tuple(passing_alpha[: protocol.maximum_selected_candidate_alpha])
    passing_risk = _ranked(
        item
        for item in decision_payloads
        if not item["failures"]
        and item["hypothesis"].role
        is CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION
    )
    selected_risk_payload = (
        tuple(passing_risk[: protocol.maximum_selected_risk_guard])
        if selected_alpha_payload
        else ()
    )
    selected_ids = {
        item["hypothesis"].hypothesis_id
        for item in (*selected_alpha_payload, *selected_risk_payload)
    }
    decisions = []
    for item in decision_payloads:
        selected = item["hypothesis"].hypothesis_id in selected_ids
        passed = not item["failures"]
        if selected:
            status = QuantResearchFactorScreeningDecisionStatus.SELECTED_MODEL_CANDIDATE
        elif passed:
            status = QuantResearchFactorScreeningDecisionStatus.QUALIFIED_NOT_SELECTED_CAP
        elif item["inconclusive"]:
            status = QuantResearchFactorScreeningDecisionStatus.INCONCLUSIVE_DATA
        else:
            status = QuantResearchFactorScreeningDecisionStatus.REJECTED_SCREEN
        decisions.append(
            CampaignThreeScreeningDecisionV1(
                trial_id=item["hypothesis"].trial_id,
                hypothesis_id=item["hypothesis"].hypothesis_id,
                role=item["hypothesis"].role,
                related_hypothesis_family=item["hypothesis"].related_hypothesis_family,
                primary_endpoint_count=(
                    2
                    if item["hypothesis"].role
                    is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
                    else 1
                ),
                raw_family_p_value=_string(item["raw"]) if item["raw"] is not None else None,
                holm_adjusted_p_value=(
                    _string(item["holm"]) if item["holm"] is not None else None
                ),
                worst_case_primary_beta=(
                    _string(item["beta"]) if item["beta"] is not None else None
                ),
                worst_case_registered_lower_bound=(
                    _string(item["lower"]) if item["lower"] is not None else None
                ),
                status=status,
                passed_all_frozen_gates=passed,
                selected_for_model_candidate_set=selected,
                failed_gate_codes=item["failures"],
            )
        )
    return (
        tuple(decisions),
        tuple(item["hypothesis"].hypothesis_id for item in selected_alpha_payload),
        tuple(item["hypothesis"].hypothesis_id for item in selected_risk_payload),
    )


def _ranked(items):
    return sorted(
        items,
        key=lambda item: (
            -float(item["beta"]),
            -float(item["lower"]),
            item["hypothesis"].hypothesis_id,
        ),
    )


def _collection_fingerprint(values) -> str:
    payload = [
        item.model_dump(mode="json") if hasattr(item, "model_dump") else item
        for item in values
    ]
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _single_value(values) -> str:
    unique = set(values)
    if len(unique) != 1:
        raise CampaignThreeScreeningError("Campaign Three source lineage differs")
    return next(iter(unique))


def _quantile(values: tuple[float, ...], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise CampaignThreeScreeningError("interaction quantile input differs")
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _string(value: float | Decimal) -> str:
    return format(
        Decimal(str(value)).quantize(_QUANTUM, rounding=ROUND_HALF_EVEN), "f"
    )
