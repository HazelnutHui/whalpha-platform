"""Build the outcome-blind Campaign Three input-qualification report."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_EVEN

from tip_api.contracts.analytics.v1.quant_research_campaign_three_hypotheses import (
    CampaignThreeHypothesisRole,
    quant_research_campaign_three_hypothesis_registry_v1,
)
from tip_api.contracts.analytics.v1.quant_research_campaign_three_input_qualification import (
    CampaignThreeFactorVariationEvidence,
    CampaignThreeInputDecision,
    CampaignThreeInputQualificationDecisionV1,
    CampaignThreeInputQualificationReportV1,
    CampaignThreeInputQualificationStatus,
    V1_FACTOR_DIAGNOSTICS_FINGERPRINT,
    V1_FACTOR_DIAGNOSTICS_SHA256,
    V2_FACTOR_QUALIFICATION_FINGERPRINT,
    V2_FACTOR_QUALIFICATION_SHA256,
    _input_rejection_reasons,
    input_qualification_fingerprint,
    quant_research_campaign_three_input_qualification_protocol_v1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_diagnostics import (
    QuantResearchFactorDiagnosticsV1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_qualification_v2 import (
    QuantResearchFactorQualificationReportV2,
    QuantResearchFactorQualificationV2Status,
)
from tip_api.contracts.analytics.v1.quant_research_market_state_qualification import (
    QuantResearchMarketStateQualificationReportV1,
    QuantResearchMarketStateQualificationStatus,
)
from tip_api.contracts.analytics.v1.quant_research_market_state_vector import (
    QuantResearchMarketStateAvailability,
)
from tip_api.contracts.analytics.v1.quant_research_reusable_artifacts_v2 import (
    MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT,
    MARKET_STATE_QUALIFICATION_REPORT_SHA256,
)


V1_DEVELOPMENT_REFERENCE_FACTOR_ID = "relative_return_spy_20s"
LIMITATION_CODES = (
    "development_membership_reconstructed_not_as_operated",
    "input_qualification_does_not_authorize_outcome_access",
    "market_state_close_only_daily",
    "v1_variation_proved_from_outcome_blind_pairwise_coverage",
)


class CampaignThreeInputQualificationError(ValueError):
    """Raised when outcome-blind Campaign Three inputs cannot be proved."""


@dataclass(frozen=True, slots=True)
class CampaignThreeFactorSessionEvidence:
    factor_id: str
    as_of_session: date
    available_instrument_count: int
    distinct_value_count: int
    tie_excess_count: int

    def __post_init__(self) -> None:
        if (
            self.available_instrument_count < 0
            or self.distinct_value_count < 0
            or self.distinct_value_count > self.available_instrument_count
            or self.tie_excess_count
            != self.available_instrument_count - self.distinct_value_count
        ):
            raise CampaignThreeInputQualificationError(
                "Campaign Three factor-session evidence differs"
            )


def build_campaign_three_input_qualification_report(
    *,
    v1_diagnostics: QuantResearchFactorDiagnosticsV1,
    v1_diagnostics_sha256: str,
    v2_qualification: QuantResearchFactorQualificationReportV2,
    v2_qualification_sha256: str,
    market_state: QuantResearchMarketStateQualificationReportV1,
    market_state_sha256: str,
    v2_factor_session_evidence: tuple[CampaignThreeFactorSessionEvidence, ...],
    source_revision: str,
    created_at: datetime,
) -> CampaignThreeInputQualificationReportV1:
    protocol = quant_research_campaign_three_input_qualification_protocol_v1()
    registry = quant_research_campaign_three_hypothesis_registry_v1()
    _validate_sources(
        v1_diagnostics=v1_diagnostics,
        v1_diagnostics_sha256=v1_diagnostics_sha256,
        v2_qualification=v2_qualification,
        v2_qualification_sha256=v2_qualification_sha256,
        market_state=market_state,
        market_state_sha256=market_state_sha256,
    )
    if (
        len(source_revision) != 40
        or any(item not in "0123456789abcdef" for item in source_revision)
        or created_at.tzinfo is None
        or created_at.utcoffset() is None
    ):
        raise CampaignThreeInputQualificationError(
            "Campaign Three implementation identity differs"
        )

    development_sessions = _development_sessions(v1_diagnostics)
    v2_evidence = _validated_v2_evidence(
        evidence=v2_factor_session_evidence,
        development_sessions=development_sessions,
    )
    market_state_by_session = {
        item.as_of_session: item for item in market_state.sessions
    }
    if not set(development_sessions).issubset(market_state_by_session):
        raise CampaignThreeInputQualificationError(
            "Campaign Three market-state chronology differs"
        )

    decisions = []
    for hypothesis in registry.proposals:
        if hypothesis.prospective_trial_count != 1:
            continue
        if hypothesis.source_factor_catalog == "v1":
            factor = _v1_factor_summary(
                report=v1_diagnostics,
                factor_id=hypothesis.source_factor_id,
                development_sessions=development_sessions,
            )
            variation_evidence = (
                CampaignThreeFactorVariationEvidence
                .V1_COMPLETE_SESSION_AND_PAIRWISE_ELIGIBILITY
            )
        else:
            factor = _v2_factor_summary(
                report=v2_qualification,
                factor_id=hypothesis.source_factor_id,
                evidence=v2_evidence[hypothesis.source_factor_id],
                development_sessions=development_sessions,
            )
            variation_evidence = (
                CampaignThreeFactorVariationEvidence.V2_EXACT_DEVELOPMENT_REPLAY
            )
        state = _state_summary(
            role=hypothesis.role,
            metric_id=hypothesis.state_metric_id,
            transform=hypothesis.state_transform,
            sessions=development_sessions,
            market_state_by_session=market_state_by_session,
        )
        common = {
            "hypothesis_id": hypothesis.hypothesis_id,
            "role": hypothesis.role,
            "source_factor_catalog": hypothesis.source_factor_catalog,
            "source_factor_id": hypothesis.source_factor_id,
            "state_metric_id": hypothesis.state_metric_id,
            "factor_variation_evidence": variation_evidence,
            **factor,
            **state,
        }
        provisional = CampaignThreeInputQualificationDecisionV1.model_construct(
            **common,
            decision=CampaignThreeInputDecision.QUALIFIED_FOR_PROTOCOL_FREEZE,
            reason_codes=(),
        )
        reasons = _input_rejection_reasons(provisional, protocol)
        decisions.append(
            CampaignThreeInputQualificationDecisionV1.model_validate(
                {
                    **common,
                    "decision": (
                        CampaignThreeInputDecision.REJECTED_INPUT_SUPPORT
                        if reasons
                        else CampaignThreeInputDecision.QUALIFIED_FOR_PROTOCOL_FREEZE
                    ),
                    "reason_codes": reasons,
                }
            )
        )
    typed_decisions = tuple(decisions)
    qualified_alpha = sum(
        item.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
        and item.decision is CampaignThreeInputDecision.QUALIFIED_FOR_PROTOCOL_FREEZE
        for item in typed_decisions
    )
    rejected_alpha = sum(
        item.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
        and item.decision is CampaignThreeInputDecision.REJECTED_INPUT_SUPPORT
        for item in typed_decisions
    )
    qualified_risk = sum(
        item.role is CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION
        and item.decision is CampaignThreeInputDecision.QUALIFIED_FOR_PROTOCOL_FREEZE
        for item in typed_decisions
    )
    rejected_risk = sum(
        item.role is CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION
        and item.decision is CampaignThreeInputDecision.REJECTED_INPUT_SUPPORT
        for item in typed_decisions
    )
    status = (
        CampaignThreeInputQualificationStatus.READY_FOR_PROTOCOL_FREEZE
        if qualified_alpha >= protocol.minimum_qualified_candidate_alpha_count
        and qualified_risk >= protocol.minimum_qualified_risk_guard_count
        else CampaignThreeInputQualificationStatus.REJECTED_INPUT_SUPPORT
    )
    payload = {
        "protocol_fingerprint": protocol.logical_fingerprint,
        "source_revision": source_revision,
        "created_at": created_at.astimezone(UTC),
        "source_hypothesis_registry_fingerprint": registry.logical_fingerprint,
        "development_session_partition_fingerprint": _fingerprint(
            [item.isoformat() for item in development_sessions]
        ),
        "decisions": typed_decisions,
        "qualified_candidate_alpha_count": qualified_alpha,
        "rejected_candidate_alpha_count": rejected_alpha,
        "qualified_risk_guard_count": qualified_risk,
        "rejected_risk_guard_count": rejected_risk,
        "status": status,
        "limitation_codes": LIMITATION_CODES,
    }
    provisional_report = CampaignThreeInputQualificationReportV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return CampaignThreeInputQualificationReportV1.model_validate(
        {
            **payload,
            "logical_fingerprint": input_qualification_fingerprint(
                provisional_report
            ),
        }
    )


def _validate_sources(
    *,
    v1_diagnostics: QuantResearchFactorDiagnosticsV1,
    v1_diagnostics_sha256: str,
    v2_qualification: QuantResearchFactorQualificationReportV2,
    v2_qualification_sha256: str,
    market_state: QuantResearchMarketStateQualificationReportV1,
    market_state_sha256: str,
) -> None:
    if (
        v1_diagnostics.logical_fingerprint != V1_FACTOR_DIAGNOSTICS_FINGERPRINT
        or v1_diagnostics_sha256 != V1_FACTOR_DIAGNOSTICS_SHA256
        or v1_diagnostics.contains_forward_outcomes
        or v1_diagnostics.contains_performance_metrics
        or v2_qualification.logical_fingerprint
        != V2_FACTOR_QUALIFICATION_FINGERPRINT
        or v2_qualification_sha256 != V2_FACTOR_QUALIFICATION_SHA256
        or v2_qualification.status
        is not QuantResearchFactorQualificationV2Status.READY_FOR_SCREENING_PROTOCOL_REVIEW
        or v2_qualification.contains_forward_outcomes
        or v2_qualification.contains_performance_metrics
        or v2_qualification.development_outcome_read_count
        or market_state.logical_fingerprint
        != MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
        or market_state_sha256 != MARKET_STATE_QUALIFICATION_REPORT_SHA256
        or market_state.status
        is not QuantResearchMarketStateQualificationStatus.READY_FOR_CAMPAIGN_PROTOCOL_DESIGN
        or market_state.contains_forward_outcomes
        or market_state.contains_performance_metrics
        or market_state.development_outcome_read_count
    ):
        raise CampaignThreeInputQualificationError(
            "Campaign Three outcome-blind source evidence differs"
        )


def _development_sessions(
    report: QuantResearchFactorDiagnosticsV1,
) -> tuple[date, ...]:
    protocol = quant_research_campaign_three_input_qualification_protocol_v1()
    sessions = tuple(
        item.as_of_session
        for item in report.session_availability
        if item.factor_id == V1_DEVELOPMENT_REFERENCE_FACTOR_ID
        and protocol.development_first_session
        <= item.as_of_session
        <= protocol.development_last_session
        and item.expected_count > 0
        and item.available_count == item.expected_count
    )
    if (
        sessions != tuple(sorted(set(sessions)))
        or len(sessions) != protocol.development_session_count
        or sessions[0] != protocol.development_first_session
        or sessions[-1] != protocol.development_last_session
    ):
        raise CampaignThreeInputQualificationError(
            "Campaign Three Development session partition differs"
        )
    return sessions


def _validated_v2_evidence(
    *,
    evidence: tuple[CampaignThreeFactorSessionEvidence, ...],
    development_sessions: tuple[date, ...],
) -> dict[str, dict[date, CampaignThreeFactorSessionEvidence]]:
    required = {
        item.source_factor_id
        for item in quant_research_campaign_three_hypothesis_registry_v1().proposals
        if item.prospective_trial_count == 1 and item.source_factor_catalog == "v2"
    }
    result = {factor_id: {} for factor_id in required}
    for item in evidence:
        if item.factor_id not in required or item.as_of_session not in development_sessions:
            raise CampaignThreeInputQualificationError(
                "Campaign Three V2 factor evidence scope differs"
            )
        if item.as_of_session in result[item.factor_id]:
            raise CampaignThreeInputQualificationError(
                "Campaign Three V2 factor evidence is duplicated"
            )
        result[item.factor_id][item.as_of_session] = item
    if any(tuple(sorted(values)) != development_sessions for values in result.values()):
        raise CampaignThreeInputQualificationError(
            "Campaign Three V2 factor evidence chronology differs"
        )
    return result


def _v1_factor_summary(
    *,
    report: QuantResearchFactorDiagnosticsV1,
    factor_id: str,
    development_sessions: tuple[date, ...],
) -> dict[str, object]:
    session_set = frozenset(development_sessions)
    rows = tuple(
        item
        for item in report.session_availability
        if item.factor_id == factor_id and item.as_of_session in session_set
    )
    complete_reference_count = sum(
        item.factor_id == V1_DEVELOPMENT_REFERENCE_FACTOR_ID
        and item.expected_count > 0
        and item.available_count == item.expected_count
        for item in report.session_availability
    )
    pairwise_variation_proved = max(
        (
            item.eligible_session_count
            for item in report.pairwise_same_session_spearman
            if factor_id in (item.left_factor_id, item.right_factor_id)
        ),
        default=0,
    ) == complete_reference_count
    eligible = tuple(
        item.available_count >= 100
        and item.available_count == item.expected_count
        and pairwise_variation_proved
        for item in rows
    )
    if len(rows) != len(development_sessions):
        raise CampaignThreeInputQualificationError(
            "Campaign Three V1 factor chronology differs"
        )
    distribution = next(
        item for item in report.distributions if item.factor_id == factor_id
    )
    return _factor_summary_payload(
        eligible=eligible,
        available_counts=tuple(item.available_count for item in rows),
        distinct_counts=tuple(2 if item else 0 for item in eligible),
        source_tie_rate=distribution.same_session_tie_excess_rate,
    )


def _v2_factor_summary(
    *,
    report: QuantResearchFactorQualificationReportV2,
    factor_id: str,
    evidence: dict[date, CampaignThreeFactorSessionEvidence],
    development_sessions: tuple[date, ...],
) -> dict[str, object]:
    ordered = tuple(evidence[item] for item in development_sessions)
    eligible = tuple(
        item.available_instrument_count >= 100 and item.distinct_value_count >= 2
        for item in ordered
    )
    distribution = next(
        item for item in report.distributions if item.factor_id == factor_id
    )
    return _factor_summary_payload(
        eligible=eligible,
        available_counts=tuple(item.available_instrument_count for item in ordered),
        distinct_counts=tuple(item.distinct_value_count for item in ordered),
        source_tie_rate=distribution.same_session_tie_excess_rate,
    )


def _factor_summary_payload(
    *,
    eligible: tuple[bool, ...],
    available_counts: tuple[int, ...],
    distinct_counts: tuple[int, ...],
    source_tie_rate: str,
) -> dict[str, object]:
    split = len(eligible) // 2
    eligible_available = tuple(
        count for count, is_eligible in zip(available_counts, eligible, strict=True)
        if is_eligible
    )
    eligible_distinct = tuple(
        count for count, is_eligible in zip(distinct_counts, eligible, strict=True)
        if is_eligible
    )
    return {
        "factor_eligible_session_count": sum(eligible),
        "factor_first_half_eligible_session_count": sum(eligible[:split]),
        "factor_second_half_eligible_session_count": sum(eligible[split:]),
        "factor_minimum_available_instruments": (
            min(eligible_available) if eligible_available else 0
        ),
        "factor_minimum_distinct_values": (
            min(eligible_distinct) if eligible_distinct else 0
        ),
        "source_same_session_tie_excess_rate": source_tie_rate,
    }


def _state_summary(
    *,
    role: CampaignThreeHypothesisRole,
    metric_id: str,
    transform: str,
    sessions: tuple[date, ...],
    market_state_by_session: dict[date, object],
) -> dict[str, object]:
    values: list[Decimal | None] = []
    for session in sessions:
        source = market_state_by_session[session]
        metric = next(item for item in source.metrics if item.metric_id == metric_id)
        if metric.availability is QuantResearchMarketStateAvailability.UNAVAILABLE:
            values.append(None)
        else:
            assert metric.value is not None
            values.append(_transform_state(Decimal(metric.value), transform))
    split = len(values) // 2
    first = tuple(item for item in values[:split] if item is not None)
    second = tuple(item for item in values[split:] if item is not None)
    available = (*first, *second)
    positive = sum(item > 0 for item in available)
    negative = sum(item < 0 for item in available)
    zero = len(available) - positive - negative
    common = {
        "state_available_session_count": len(available),
        "state_first_half_available_session_count": len(first),
        "state_second_half_available_session_count": len(second),
        "state_distinct_value_count": len(set(available)),
        "state_first_half_distinct_value_count": len(set(first)),
        "state_second_half_distinct_value_count": len(set(second)),
        "state_positive_session_count": positive,
        "state_negative_session_count": negative,
        "state_zero_session_count": zero,
        "state_first_half_positive_session_count": sum(item > 0 for item in first),
        "state_first_half_negative_session_count": sum(item < 0 for item in first),
        "state_second_half_positive_session_count": sum(item > 0 for item in second),
        "state_second_half_negative_session_count": sum(item < 0 for item in second),
    }
    if role is CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION:
        return {
            **common,
            "state_same_side_episode_count": None,
            "state_longest_same_side_run": None,
            "state_maximum_natural_zero_side_share": None,
        }
    episodes, longest = _same_side_diagnostics(available)
    nonzero = positive + negative
    return {
        **common,
        "state_same_side_episode_count": episodes,
        "state_longest_same_side_run": longest,
        "state_maximum_natural_zero_side_share": _ratio(
            max(positive, negative), nonzero
        ),
    }


def _transform_state(value: Decimal, transform: str) -> Decimal:
    if transform == "2*(share-0.5)":
        return Decimal(2) * (value - Decimal("0.5"))
    if transform == "-1*spy_log_return_20s":
        return -value
    if transform == "as_defined":
        return value
    raise CampaignThreeInputQualificationError(
        "Campaign Three state transform is not registered"
    )


def _same_side_diagnostics(values: tuple[Decimal, ...]) -> tuple[int, int]:
    if not values:
        return 0, 0
    signs = tuple(1 if item > 0 else -1 if item < 0 else 0 for item in values)
    episodes = 1
    current = 1
    longest = 1
    for previous, value in zip(signs, signs[1:]):
        if value == previous:
            current += 1
        else:
            episodes += 1
            current = 1
        longest = max(longest, current)
    return episodes, longest


def _ratio(numerator: int, denominator: int) -> str:
    value = Decimal(0) if denominator == 0 else Decimal(numerator) / Decimal(denominator)
    quantized = value.quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_EVEN)
    if quantized == 0:
        quantized = abs(quantized)
    return format(quantized, "f")


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
