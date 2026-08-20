"""Full classified-base trailing-liquidity calculation and scope audit."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from typing import Mapping
from uuid import UUID

from tip_api.contracts.market_data.v1 import EodHistoryWindowDescriptorV1
from tip_api.contracts.market_data.v1.full_base_liquidity import (
    FullBaseDecisionV1,
    FullBaseDisposition,
    FullBaseFunnelStageV1,
    FullBaseMembershipV1,
    FullBaseMetricV1,
    FullBasePolicySummaryV1,
    FullBaseSetDiffV1,
)
from tip_api.contracts.security_classification.v1 import ProviderInstrumentSecurityEvidenceV1
from tip_api.contracts.security_classification.v1.universe_review import ReviewedEligibilityDecision, ReviewedEligibilityOverrideV1, validate_override_intervals
from tip_api.persistence.eod_read import EodReadRepository
from tip_api.services.eod_history import (
    CANONICAL_DECIMAL_SCALE,
    MEDIAN_DOLLAR_VOLUME_THRESHOLD,
    PREVIOUS_CLOSE_THRESHOLD,
    audit_trailing_liquidity,
    exact_dollar_volume_proxy,
    fixed_scale_coefficient,
)
from tip_api.services.security_classification import SUPPORTED_EXCHANGES
from tip_api.services.universe_pre_activation import membership_fingerprint

FULL_BASE_A_ID = "full_base_provider_classified_common_shares_v1"
FULL_BASE_B_ID = "full_base_provider_classified_common_shares_plus_adrs_v1"
CANONICAL_DECIMAL_PRECISION = 38
ANALYTICS_CALCULATION_PRECISION = CANONICAL_DECIMAL_PRECISION * 2 + 2


@dataclass(frozen=True, slots=True)
class FullBaseScopeBundle:
    metrics: tuple[FullBaseMetricV1, ...]
    decisions: tuple[FullBaseDecisionV1, ...]
    memberships: tuple[FullBaseMembershipV1, ...]
    diffs: tuple[FullBaseSetDiffV1, ...]
    funnels: tuple[FullBaseFunnelStageV1, ...]
    summaries: tuple[FullBasePolicySummaryV1, ...]
    final_memberships: dict[str, frozenset[UUID]]
    analytics: dict[str, dict[str, object]]
    overlapping_exclusions: dict[str, dict[str, int]]


def build_full_base_scope_review(
    *,
    descriptor: EodHistoryWindowDescriptorV1,
    repository: EodReadRepository,
    evidence: tuple[ProviderInstrumentSecurityEvidenceV1, ...],
    instruments: Mapping[UUID, Mapping[str, object]],
    current_bars: tuple[object, ...],
    membership_evidence_as_of_date: date,
    reviewed_overrides: tuple[ReviewedEligibilityOverrideV1, ...],
    old_memberships: Mapping[str, frozenset[UUID]],
    calculated_at: datetime,
) -> FullBaseScopeBundle:
    """Calculate A/B from complete point-in-time provider evidence, never Legacy."""
    if descriptor.readiness_status.value != "ready" or len(descriptor.completed_sessions) != 20:
        raise ValueError("a ready 20-session descriptor is required")
    if descriptor.analysis_session in descriptor.expected_sessions:
        raise ValueError("analysis session must not enter its own trailing window")
    if calculated_at.tzinfo is None or calculated_at.utcoffset() is None:
        raise ValueError("calculated_at must be timezone-aware")
    calculated_at = calculated_at.astimezone(UTC)
    validate_override_intervals(reviewed_overrides)
    evidence_by_id: dict[UUID, ProviderInstrumentSecurityEvidenceV1] = {}
    for item in evidence:
        if item.instrument_id in evidence_by_id:
            raise ValueError("duplicate canonical security evidence")
        evidence_by_id[item.instrument_id] = item
    a_base = frozenset(item.instrument_id for item in evidence if item.provider_type_code == "CS")
    b_base = frozenset(item.instrument_id for item in evidence if item.provider_type_code in {"CS", "ADRC"})
    if not a_base <= b_base:
        raise ValueError("full-base Primary is not a subset of Secondary")

    reads = repository.read_history_sessions(descriptor.completed_sessions)
    bars_by_id: dict[UUID, dict[date, object]] = {}
    for session_read in reads:
        session = session_read.integrity.session_date
        for bar in session_read.bars:
            if bar.instrument_id not in b_base:
                continue
            by_session = bars_by_id.setdefault(bar.instrument_id, {})
            if session in by_session:
                raise ValueError("duplicate stable instrument/session")
            by_session[session] = bar
    current_by_id = _unique_bars(current_bars)
    previous_by_id = {instrument_id: sessions[descriptor.previous_session] for instrument_id, sessions in bars_by_id.items() if descriptor.previous_session in sessions}
    supported = frozenset(
        instrument_id for instrument_id in b_base
        if instrument_id in instruments and instruments[instrument_id].get("primary_exchange") in SUPPORTED_EXCHANGES
    )
    comparable = supported & frozenset(current_by_id) & frozenset(previous_by_id)
    price_eligible = frozenset(instrument_id for instrument_id in comparable if previous_by_id[instrument_id].close >= PREVIOUS_CLOSE_THRESHOLD)
    audit = audit_trailing_liquidity(descriptor=descriptor, repository=repository, instrument_ids=price_eligible)
    audit_by_id = {item.instrument_id: item for item in audit.results}
    if len(audit_by_id) != len(price_eligible):
        raise ValueError("trailing audit lost or duplicated a stable ID")
    active_overrides = {}
    for item in reviewed_overrides:
        if item.is_effective_on(descriptor.analysis_session):
            if item.instrument_id in active_overrides:
                raise ValueError("multiple active reviewed overrides")
            active_overrides[item.instrument_id] = item

    metrics = tuple(
        _metric(
            instrument_id=instrument_id,
            source=evidence_by_id[instrument_id],
            instrument=instruments.get(instrument_id),
            current=current_by_id.get(instrument_id),
            previous=previous_by_id.get(instrument_id),
            bars=bars_by_id.get(instrument_id, {}),
            audit_result=audit_by_id.get(instrument_id),
            descriptor=descriptor,
            membership_evidence_as_of_date=membership_evidence_as_of_date,
            calculated_at=calculated_at,
        )
        for instrument_id in sorted(b_base, key=str)
    )
    metric_by_id = {item.instrument_id: item for item in metrics}
    decisions: list[FullBaseDecisionV1] = []
    final: dict[str, frozenset[UUID]] = {}
    funnels: list[FullBaseFunnelStageV1] = []
    overlap: dict[str, dict[str, int]] = {}
    for policy_id, base in ((FULL_BASE_A_ID, a_base), (FULL_BASE_B_ID, b_base)):
        policy_decisions = tuple(
            _decision(
                policy_id=policy_id,
                metric=metric_by_id[instrument_id],
                active_override=active_overrides.get(instrument_id),
                calculated_at=calculated_at,
            )
            for instrument_id in sorted(base, key=str)
        )
        decisions.extend(policy_decisions)
        included = frozenset(item.instrument_id for item in policy_decisions if item.included)
        final[policy_id] = included
        funnels.extend(_funnel(policy_id, policy_decisions, descriptor, membership_evidence_as_of_date))
        overlap[policy_id] = dict(sorted(Counter(reason for item in policy_decisions for reason in item.reason_codes).items()))
    if not final[FULL_BASE_A_ID] <= final[FULL_BASE_B_ID]:
        raise ValueError("corrected Primary is not a subset of corrected Secondary")
    if any(evidence_by_id[item].provider_type_code != "ADRC" for item in final[FULL_BASE_B_ID] - final[FULL_BASE_A_ID]):
        raise ValueError("Secondary minus Primary contains a non-ADRC instrument")

    memberships = tuple(
        FullBaseMembershipV1(
            analysis_session=descriptor.analysis_session,
            policy_id=policy_id,
            instrument_id=instrument_id,
            provider_type_code=evidence_by_id[instrument_id].provider_type_code,
        )
        for policy_id in (FULL_BASE_A_ID, FULL_BASE_B_ID)
        for instrument_id in sorted(final[policy_id], key=str)
    )
    diffs: list[FullBaseSetDiffV1] = []
    summaries = []
    old_key = {
        FULL_BASE_A_ID: "provider_classified_common_shares_v1",
        FULL_BASE_B_ID: "provider_classified_common_shares_plus_adrs_v1",
    }
    for policy_id in (FULL_BASE_A_ID, FULL_BASE_B_ID):
        old = old_memberships[old_key[policy_id]]
        corrected = final[policy_id]
        for instrument_id in sorted(old | corrected, key=str):
            if instrument_id in old and instrument_id in corrected:
                direction, reason = "old_retained", "frozen_formula_reproduced"
            elif instrument_id in old:
                direction, reason = "old_removed", _decision_by_key(decisions, policy_id, instrument_id).disposition.value
            else:
                metric = metric_by_id[instrument_id]
                rescued = metric.previous_dollar_volume_below_threshold is True
                direction, reason = "corrected_added", ("rescued_from_previous_session_dollar_volume_scope" if rescued else "full_base_not_in_legacy_scope")
            metric = metric_by_id[instrument_id]
            diffs.append(FullBaseSetDiffV1(
                analysis_session=descriptor.analysis_session, policy_id=policy_id, instrument_id=instrument_id,
                provider_type_code=evidence_by_id[instrument_id].provider_type_code, direction=direction, reason_code=reason,
                rescued_from_previous_session_scope=(direction == "corrected_added" and metric.previous_dollar_volume_below_threshold is True),
                median_dollar_volume_proxy_20s=metric.median_dollar_volume_proxy_20s,
            ))
        types = Counter(evidence_by_id[item].provider_type_code for item in corrected)
        summaries.append(FullBasePolicySummaryV1(
            policy_id=policy_id, base_count=len(a_base if policy_id == FULL_BASE_A_ID else b_base), final_count=len(corrected),
            cs_count=types["CS"], adrc_count=types["ADRC"], membership_fingerprint=membership_fingerprint(corrected),
            old_count=len(old), retained_count=len(old & corrected), removed_count=len(old - corrected), added_count=len(corrected - old),
            rescued_previous_day_below_threshold_count=sum(
                metric_by_id[item].previous_dollar_volume_below_threshold is True
                for item in corrected - old
            ),
        ))
    analytics = {
        policy_id: calculate_membership_analytics(final[policy_id], current_by_id, previous_by_id)
        for policy_id in (FULL_BASE_A_ID, FULL_BASE_B_ID)
    }
    return FullBaseScopeBundle(
        metrics=metrics,
        decisions=tuple(decisions),
        memberships=memberships,
        diffs=tuple(diffs),
        funnels=tuple(funnels),
        summaries=tuple(summaries),
        final_memberships=final,
        analytics=analytics,
        overlapping_exclusions=overlap,
    )


def _unique_bars(bars: tuple[object, ...]) -> dict[UUID, object]:
    result = {}
    for bar in bars:
        if bar.instrument_id in result:
            raise ValueError("duplicate current stable instrument")
        result[bar.instrument_id] = bar
    return result


def _metric(*, instrument_id, source, instrument, current, previous, bars, audit_result, descriptor, membership_evidence_as_of_date, calculated_at):
    current_present = current is not None
    previous_close = None if previous is None else previous.close
    previous_below = None if previous is None else exact_dollar_volume_proxy(previous.close, previous.volume) < MEDIAN_DOLLAR_VOLUME_THRESHOLD
    if instrument is None:
        status, flags = "invalid_input", ("orphan_instrument_reference",)
    elif instrument.get("primary_exchange") not in SUPPORTED_EXCHANGES:
        status, flags = "unsupported_exchange", ("unsupported_exchange",)
    elif not current_present:
        status, flags = "missing_current_bar", ("missing_current_bar",)
    elif previous is None:
        status, flags = "missing_previous_bar", ("missing_previous_bar",)
    elif previous_close < PREVIOUS_CLOSE_THRESHOLD:
        status, flags = "below_previous_close", ("below_previous_close",)
    elif audit_result is None:
        status, flags = "invalid_input", ("trailing_audit_missing",)
    else:
        status, flags = audit_result.eligibility_status.value, audit_result.reason_codes
    flags = set(flags)
    if current is not None and previous is not None:
        current_close_coefficient = fixed_scale_coefficient(current.close, scale=CANONICAL_DECIMAL_SCALE)
        previous_close_coefficient = fixed_scale_coefficient(previous.close, scale=CANONICAL_DECIMAL_SCALE)
        if current_close_coefficient >= 2 * previous_close_coefficient or 2 * current_close_coefficient <= previous_close_coefficient:
            flags.add("material_return_outlier_review")
    return FullBaseMetricV1(
        analysis_session=descriptor.analysis_session, membership_evidence_as_of_date=membership_evidence_as_of_date,
        instrument_id=instrument_id, display_ticker=source.provider_ticker, provider_type_code=source.provider_type_code,
        primary_exchange=None if instrument is None else instrument.get("primary_exchange"),
        supported_exchange=instrument is not None and instrument.get("primary_exchange") in SUPPORTED_EXCHANGES,
        current_bar_present=current_present, previous_bar_present=previous is not None,
        previous_close=previous_close, previous_dollar_volume_below_threshold=previous_below,
        observation_count=len(bars), median_dollar_volume_proxy_20s=None if audit_result is None else audit_result.median_dollar_volume_proxy,
        metric_status=status, quality_flags=tuple(flags), source_window_fingerprint=descriptor.fingerprint, calculated_at=calculated_at,
    )


def _decision(*, policy_id, metric, active_override, calculated_at):
    status = {
        "unsupported_exchange": FullBaseDisposition.UNSUPPORTED_EXCHANGE,
        "missing_current_bar": FullBaseDisposition.MISSING_CURRENT_BAR,
        "missing_previous_bar": FullBaseDisposition.MISSING_PREVIOUS_BAR,
        "below_previous_close": FullBaseDisposition.BELOW_PREVIOUS_CLOSE,
        "below_price_threshold": FullBaseDisposition.BELOW_PREVIOUS_CLOSE,
        "insufficient_history": FullBaseDisposition.INSUFFICIENT_HISTORY,
        "below_liquidity_threshold": FullBaseDisposition.BELOW_TRAILING_LIQUIDITY,
        "identity_reference_failure": FullBaseDisposition.INVALID_INPUT,
        "data_quality_failure": FullBaseDisposition.INVALID_INPUT,
        "invalid_input": FullBaseDisposition.INVALID_INPUT,
        "passed": FullBaseDisposition.INCLUDED,
    }.get(metric.metric_status, FullBaseDisposition.INVALID_INPUT)
    stage = {
        FullBaseDisposition.UNSUPPORTED_EXCHANGE: "supported_exchange",
        FullBaseDisposition.MISSING_CURRENT_BAR: "comparable_bars",
        FullBaseDisposition.MISSING_PREVIOUS_BAR: "comparable_bars",
        FullBaseDisposition.BELOW_PREVIOUS_CLOSE: "previous_close",
        FullBaseDisposition.INSUFFICIENT_HISTORY: "history_completeness",
        FullBaseDisposition.BELOW_TRAILING_LIQUIDITY: "trailing_liquidity",
        FullBaseDisposition.INVALID_INPUT: "input_quality",
        FullBaseDisposition.INCLUDED: "final_membership",
    }[status]
    override_value = None
    reasons = set(metric.quality_flags)
    if active_override is not None:
        override_value = active_override.decision.value
        if status is FullBaseDisposition.INCLUDED and active_override.decision is ReviewedEligibilityDecision.EXCLUDE:
            status, stage = FullBaseDisposition.REVIEWED_EXCLUSION, "reviewed_overlay"
            reasons.add(active_override.reason_code)
        elif status is FullBaseDisposition.INCLUDED and active_override.decision is ReviewedEligibilityDecision.QUARANTINE:
            status, stage = FullBaseDisposition.REVIEWED_QUARANTINE, "reviewed_overlay"
            reasons.add(active_override.reason_code)
        elif active_override.decision is ReviewedEligibilityDecision.ALLOW:
            reasons.add("reviewed_allow_does_not_bypass_quantitative_gates")
        elif status is not FullBaseDisposition.INCLUDED:
            reasons.add("reviewed_exclusion_not_reached_due_prior_gate")
    if status is FullBaseDisposition.INCLUDED:
        reasons.add("full_base_trailing_liquidity_passed")
    return FullBaseDecisionV1(
        analysis_session=metric.analysis_session, membership_evidence_as_of_date=metric.membership_evidence_as_of_date,
        policy_id=policy_id, instrument_id=metric.instrument_id, provider_type_code=metric.provider_type_code,
        disposition=status, included=status is FullBaseDisposition.INCLUDED, stage_id=stage,
        reason_codes=tuple(reasons), reviewed_override_decision=override_value, calculated_at=calculated_at,
    )


def _funnel(policy_id, decisions, descriptor, evidence_date):
    stages = (
        ("provider_evidence_base", "Point-in-time canonical provider evidence", ()),
        ("target_security_form", "Target security form", ()),
        ("supported_exchange", "Supported exchange", (FullBaseDisposition.UNSUPPORTED_EXCHANGE, FullBaseDisposition.INVALID_INPUT)),
        ("comparable_bars", "Current and previous canonical bars", (FullBaseDisposition.MISSING_CURRENT_BAR, FullBaseDisposition.MISSING_PREVIOUS_BAR)),
        ("previous_close", "Previous close at least USD 5", (FullBaseDisposition.BELOW_PREVIOUS_CLOSE,)),
        ("history_completeness", "Complete 20-session history", (FullBaseDisposition.INSUFFICIENT_HISTORY,)),
        ("trailing_liquidity", "20-session median dollar-volume proxy at least USD 20M", (FullBaseDisposition.BELOW_TRAILING_LIQUIDITY,)),
        ("outlier_quarantine", "Material outlier quarantine policy", (FullBaseDisposition.OUTLIER_QUARANTINE,)),
        ("reviewed_overlay", "Reviewed eligibility overlay", (FullBaseDisposition.REVIEWED_EXCLUSION, FullBaseDisposition.REVIEWED_QUARANTINE)),
        ("final_membership", "Final selected shadow membership", ()),
    )
    remaining = len(decisions)
    output = []
    for index, (stage_id, label, excluded_statuses) in enumerate(stages, 1):
        input_count = remaining
        excluded = sum(item.disposition in excluded_statuses for item in decisions)
        remaining -= excluded
        output.append(FullBaseFunnelStageV1(
            analysis_session=descriptor.analysis_session, membership_evidence_as_of_date=evidence_date,
            policy_id=policy_id, stage_order=index, stage_id=stage_id, stage_label=label, stage_kind="sequential",
            input_count=input_count, excluded_count=excluded, remaining_count=remaining,
            exclusion_reason_codes=tuple(item.value for item in excluded_statuses),
            source_fingerprints=(descriptor.fingerprint,),
        ))
    if remaining != sum(item.included for item in decisions):
        raise ValueError("sequential funnel does not close to final membership")
    return output


def _decision_by_key(decisions, policy_id, instrument_id):
    matches = [item for item in decisions if item.policy_id == policy_id and item.instrument_id == instrument_id]
    if len(matches) != 1:
        raise ValueError("decision ledger key is unavailable")
    return matches[0]


def calculate_membership_analytics(ids, current_by_id, previous_by_id):
    # Dashboard-comparison analytics may require non-terminating division.  Give
    # them an explicit local policy derived from the two decimal128(38,10)
    # inputs; they must never inherit a process-global Decimal context.
    with localcontext() as context:
        context.prec = ANALYTICS_CALCULATION_PRECISION
        context.rounding = ROUND_HALF_EVEN
        returns = []
        eligible_map = []
        advancer_volume = Decimal("0")
        decliner_volume = Decimal("0")
        for instrument_id in ids:
            current, previous = current_by_id[instrument_id], previous_by_id[instrument_id]
            value = current.close / previous.close - Decimal("1")
            returns.append(value)
            current_proxy = exact_dollar_volume_proxy(current.close, current.volume)
            current_close_coefficient = fixed_scale_coefficient(current.close, scale=CANONICAL_DECIMAL_SCALE)
            previous_close_coefficient = fixed_scale_coefficient(previous.close, scale=CANONICAL_DECIMAL_SCALE)
            if (
                current_proxy >= Decimal("5000000")
                and previous_close_coefficient < 2 * current_close_coefficient
                and current_close_coefficient < 2 * previous_close_coefficient
            ):
                eligible_map.append(value)
            if value > 0:
                advancer_volume += current.volume
            elif value < 0:
                decliner_volume += current.volume
        ordered = sorted(returns)
        count = len(ordered)
        median = None if not ordered else (ordered[count // 2] if count % 2 else (ordered[count // 2 - 1] + ordered[count // 2]) / Decimal("2"))
        advancers = sum(value > 0 for value in ordered)
        decliners = sum(value < 0 for value in ordered)
        return {
            "member_count": count,
            "equal_weight_return": str(sum(ordered, Decimal("0")) / Decimal(count)) if count else None,
            "median_return": None if median is None else str(median),
            "advancers": advancers, "decliners": decliners, "unchanged": count - advancers - decliners,
            "positive_share": str(Decimal(advancers) / Decimal(count)) if count else None,
            "advance_decline_net": advancers - decliners,
            "advancer_volume": str(advancer_volume), "decliner_volume": str(decliner_volume),
            "up_down_volume_ratio": None if decliner_volume == 0 else str(advancer_volume / decliner_volume),
            "mover_gainer_count": min(10, sum(value > 0 for value in eligible_map)),
            "mover_loser_count": min(10, sum(value < 0 for value in eligible_map)),
            "activity_map_node_count": min(300, len(eligible_map)),
            "fingerprint": hashlib.sha256(json.dumps([str(item) for item in ordered], separators=(",", ":")).encode()).hexdigest(),
        }
