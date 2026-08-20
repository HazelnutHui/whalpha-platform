"""Build deterministic trailing-liquidity metric facts and shadow decisions."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Mapping
from uuid import UUID

from tip_api.contracts.market_data.v1 import (
    EodHistoryWindowDescriptorV1,
    ShadowEligibilityStatus,
    TrailingLiquidityCandidateSummaryV1,
    TrailingLiquidityEligibilityStatus,
    TrailingLiquidityMetricStatus,
    TrailingLiquidityMetricV1,
    TrailingLiquidityShadowDecisionV1,
)
from tip_api.contracts.security_classification.v1 import ProviderInstrumentSecurityEvidenceV1
from tip_api.persistence.eod_read import EodReadRepository
from tip_api.services.eod_history import (
    TrailingLiquidityCoverageAudit,
    audit_trailing_liquidity,
)
from tip_api.services.provider_classified_universe import (
    CANDIDATE_A_ID,
    CANDIDATE_B_ID,
    ProviderClassifiedUniverseAudit,
)


@dataclass(frozen=True, slots=True)
class HistoricalGapAudit:
    universe_id: str
    instrument_id: UUID
    display_ticker: str
    provider_type_code: str
    first_bar_session: date | None
    last_bar_session: date | None
    observation_count: int
    missing_sessions: tuple[date, ...]
    same_day_identity_present: tuple[tuple[date, bool], ...]
    previous_bar_present: bool
    primary_reason: str


@dataclass(frozen=True, slots=True)
class TrailingLiquidityPublicationBundle:
    metrics: tuple[TrailingLiquidityMetricV1, ...]
    decisions: tuple[TrailingLiquidityShadowDecisionV1, ...]
    candidates: tuple[TrailingLiquidityCandidateSummaryV1, ...]
    gap_audits: tuple[HistoricalGapAudit, ...]
    candidate_a_audit_fingerprint: str
    candidate_b_audit_fingerprint: str


def build_trailing_liquidity_publication(
    *,
    descriptor: EodHistoryWindowDescriptorV1,
    repository: EodReadRepository,
    provider_audit: ProviderClassifiedUniverseAudit,
    evidence: tuple[ProviderInstrumentSecurityEvidenceV1, ...],
    membership_evidence_as_of_date: date,
    calculated_at: datetime,
    identity_presence: Mapping[date, frozenset[UUID]] | None = None,
) -> TrailingLiquidityPublicationBundle:
    """Build one metric fact per B member and separate A/B decisions."""

    if descriptor.readiness_status.value != "ready" or len(descriptor.completed_sessions) != 20:
        raise ValueError("a complete ready 20-session descriptor is required")
    if provider_audit.analysis_date != membership_evidence_as_of_date:
        raise ValueError("membership evidence date does not match provider audit")
    if calculated_at.tzinfo is None or calculated_at.utcoffset() is None:
        raise ValueError("calculated_at must be timezone-aware")
    calculated_at = calculated_at.astimezone(UTC)
    evidence_by_id: dict[UUID, ProviderInstrumentSecurityEvidenceV1] = {}
    for item in evidence:
        if item.instrument_id in evidence_by_id:
            raise ValueError("duplicate canonical security-form evidence")
        evidence_by_id[item.instrument_id] = item
    b_ids = provider_audit.candidate_b.member_ids
    if not provider_audit.candidate_a.member_ids <= b_ids:
        raise ValueError("Candidate A must be a subset of Candidate B")
    if set(evidence_by_id).isdisjoint(b_ids) or any(item not in evidence_by_id for item in b_ids):
        raise ValueError("shadow member has no canonical security-form evidence")

    audit_a = audit_trailing_liquidity(
        descriptor=descriptor,
        repository=repository,
        instrument_ids=provider_audit.candidate_a.member_ids,
    )
    audit_b = audit_trailing_liquidity(
        descriptor=descriptor,
        repository=repository,
        instrument_ids=b_ids,
    )
    result_b = {item.instrument_id: item for item in audit_b.results}
    if len(result_b) != len(b_ids):
        raise ValueError("metric business keys are not unique")

    reads = repository.read_history_sessions(descriptor.completed_sessions)
    bars_by_id: dict[UUID, dict[date, object]] = {}
    for session_read in reads:
        session = session_read.integrity.session_date
        for bar in session_read.bars:
            if bar.instrument_id not in b_ids:
                continue
            instrument = bars_by_id.setdefault(bar.instrument_id, {})
            if session in instrument:
                raise ValueError("duplicate instrument/session in metric input")
            instrument[session] = bar

    metrics: list[TrailingLiquidityMetricV1] = []
    for instrument_id in sorted(b_ids, key=str):
        result = result_b[instrument_id]
        source = evidence_by_id[instrument_id]
        previous = bars_by_id.get(instrument_id, {}).get(descriptor.previous_session)
        metric_status = _metric_status(result.eligibility_status)
        metrics.append(
            TrailingLiquidityMetricV1(
                analysis_session=descriptor.analysis_session,
                window_start=descriptor.window_start,
                window_end=descriptor.window_end,
                instrument_id=instrument_id,
                display_ticker=source.provider_ticker,
                provider_type_code=source.provider_type_code,
                observation_count=result.observed_observation_count,
                previous_session=descriptor.previous_session,
                previous_close=None if previous is None else previous.close,
                median_dollar_volume_proxy_20s=result.median_dollar_volume_proxy,
                metric_status=metric_status,
                quality_flags=result.reason_codes,
                source_window_fingerprint=descriptor.fingerprint,
                calculated_at=calculated_at,
            )
        )

    decisions = tuple(
        _decision(
            universe_id=universe_id,
            membership_evidence_as_of_date=membership_evidence_as_of_date,
            result=result_b[instrument_id],
            provider_type_code=evidence_by_id[instrument_id].provider_type_code,
            calculated_at=calculated_at,
        )
        for universe_id, member_ids in (
            (CANDIDATE_A_ID, provider_audit.candidate_a.member_ids),
            (CANDIDATE_B_ID, provider_audit.candidate_b.member_ids),
        )
        for instrument_id in sorted(member_ids, key=str)
    )
    if len({(item.universe_id, item.instrument_id) for item in decisions}) != len(decisions):
        raise ValueError("duplicate decision business key")
    _validate_security_form_gates(decisions)

    summaries = (
        _candidate_summary(CANDIDATE_A_ID, audit_a),
        _candidate_summary(CANDIDATE_B_ID, audit_b),
    )
    gaps = _gap_audits(
        descriptor=descriptor,
        audit_a=audit_a,
        audit_b=audit_b,
        evidence_by_id=evidence_by_id,
        bars_by_id=bars_by_id,
        identity_presence=identity_presence or {},
    )
    return TrailingLiquidityPublicationBundle(
        metrics=tuple(metrics),
        decisions=decisions,
        candidates=summaries,
        gap_audits=gaps,
        candidate_a_audit_fingerprint=audit_a.fingerprint,
        candidate_b_audit_fingerprint=audit_b.fingerprint,
    )


def _metric_status(status: TrailingLiquidityEligibilityStatus) -> TrailingLiquidityMetricStatus:
    return {
        TrailingLiquidityEligibilityStatus.PASSED: TrailingLiquidityMetricStatus.AVAILABLE,
        TrailingLiquidityEligibilityStatus.BELOW_LIQUIDITY_THRESHOLD: TrailingLiquidityMetricStatus.AVAILABLE,
        TrailingLiquidityEligibilityStatus.BELOW_PRICE_THRESHOLD: TrailingLiquidityMetricStatus.NOT_CALCULATED_BELOW_PRICE,
        TrailingLiquidityEligibilityStatus.INSUFFICIENT_HISTORY: TrailingLiquidityMetricStatus.INSUFFICIENT_HISTORY,
        TrailingLiquidityEligibilityStatus.MISSING_PREVIOUS_BAR: TrailingLiquidityMetricStatus.MISSING_PREVIOUS_BAR,
        TrailingLiquidityEligibilityStatus.IDENTITY_REFERENCE_FAILURE: TrailingLiquidityMetricStatus.INVALID_INPUT,
        TrailingLiquidityEligibilityStatus.DATA_QUALITY_FAILURE: TrailingLiquidityMetricStatus.INVALID_INPUT,
    }[status]


def _shadow_status(status: TrailingLiquidityEligibilityStatus) -> ShadowEligibilityStatus:
    return {
        TrailingLiquidityEligibilityStatus.PASSED: ShadowEligibilityStatus.PASSED,
        TrailingLiquidityEligibilityStatus.BELOW_LIQUIDITY_THRESHOLD: ShadowEligibilityStatus.BELOW_LIQUIDITY,
        TrailingLiquidityEligibilityStatus.BELOW_PRICE_THRESHOLD: ShadowEligibilityStatus.BELOW_PRICE,
        TrailingLiquidityEligibilityStatus.INSUFFICIENT_HISTORY: ShadowEligibilityStatus.INSUFFICIENT_HISTORY,
        TrailingLiquidityEligibilityStatus.MISSING_PREVIOUS_BAR: ShadowEligibilityStatus.MISSING_PREVIOUS_BAR,
        TrailingLiquidityEligibilityStatus.IDENTITY_REFERENCE_FAILURE: ShadowEligibilityStatus.QUARANTINED_OR_INVALID_INPUT,
        TrailingLiquidityEligibilityStatus.DATA_QUALITY_FAILURE: ShadowEligibilityStatus.QUARANTINED_OR_INVALID_INPUT,
    }[status]


def _decision(
    *,
    universe_id: str,
    membership_evidence_as_of_date: date,
    result: object,
    provider_type_code: str,
    calculated_at: datetime,
) -> TrailingLiquidityShadowDecisionV1:
    status = _shadow_status(result.eligibility_status)
    price = None if result.price_gate_status == "unavailable" else result.price_gate_status == "passed"
    liquidity = None if result.liquidity_gate_status == "unavailable" else result.liquidity_gate_status == "passed"
    return TrailingLiquidityShadowDecisionV1(
        analysis_session=result.analysis_session,
        universe_id=universe_id,
        membership_evidence_as_of_date=membership_evidence_as_of_date,
        instrument_id=result.instrument_id,
        provider_type_code=provider_type_code,
        eligibility_status=status,
        price_gate_passed=price,
        liquidity_gate_passed=liquidity,
        included=status is ShadowEligibilityStatus.PASSED,
        primary_reason=status.value,
        quality_flags=result.reason_codes,
        decision_reasons=tuple(sorted(set(result.reason_codes) | {status.value})),
        calculated_at=calculated_at,
    )


def _candidate_summary(universe_id: str, audit: TrailingLiquidityCoverageAudit) -> TrailingLiquidityCandidateSummaryV1:
    counts = Counter(item.eligibility_status.value for item in audit.results)
    return TrailingLiquidityCandidateSummaryV1(
        universe_id=universe_id,
        requested_count=audit.requested_instrument_count,
        passed_count=counts["passed"],
        below_liquidity_count=counts["below_liquidity_threshold"],
        below_price_count=counts["below_price_threshold"],
        missing_previous_bar_count=counts["missing_previous_bar"],
        insufficient_history_count=counts["insufficient_history"],
        full_history_count=audit.full_20_of_20_count,
        non_null_median_count=sum(item.median_dollar_volume_proxy is not None for item in audit.results),
        audit_fingerprint=audit.fingerprint,
    )


def _validate_security_form_gates(decisions: tuple[TrailingLiquidityShadowDecisionV1, ...]) -> None:
    for item in decisions:
        if item.universe_id not in {CANDIDATE_A_ID, CANDIDATE_B_ID}:
            raise ValueError("unknown shadow universe identifier")
        allowed = {"CS"} if item.universe_id == CANDIDATE_A_ID else {"CS", "ADRC"}
        if item.provider_type_code not in allowed:
            raise ValueError("shadow decision contains a disallowed provider security type")


def _gap_audits(
    *,
    descriptor: EodHistoryWindowDescriptorV1,
    audit_a: TrailingLiquidityCoverageAudit,
    audit_b: TrailingLiquidityCoverageAudit,
    evidence_by_id: Mapping[UUID, ProviderInstrumentSecurityEvidenceV1],
    bars_by_id: Mapping[UUID, Mapping[date, object]],
    identity_presence: Mapping[date, frozenset[UUID]],
) -> tuple[HistoricalGapAudit, ...]:
    output: list[HistoricalGapAudit] = []
    for universe_id, audit in ((CANDIDATE_A_ID, audit_a), (CANDIDATE_B_ID, audit_b)):
        for result in audit.results:
            if result.eligibility_status not in {
                TrailingLiquidityEligibilityStatus.INSUFFICIENT_HISTORY,
                TrailingLiquidityEligibilityStatus.MISSING_PREVIOUS_BAR,
            }:
                continue
            sessions = tuple(sorted(bars_by_id.get(result.instrument_id, {})))
            missing = tuple(item for item in descriptor.expected_sessions if item not in sessions)
            presence = tuple((item, result.instrument_id in identity_presence.get(item, frozenset())) for item in missing)
            if result.eligibility_status is TrailingLiquidityEligibilityStatus.MISSING_PREVIOUS_BAR:
                reason = "no_previous_session_bar"
            elif presence and any(present for _, present in presence):
                reason = "missing_canonical_bar"
            elif presence and identity_presence and any(not present for _, present in presence):
                reason = "identity_not_resolved_for_session"
            elif sessions and sessions[0] > descriptor.window_start and all(item < sessions[0] for item in missing):
                reason = "listed_or_first_observed_during_window"
            else:
                reason = "insufficient_local_evidence"
            evidence = evidence_by_id[result.instrument_id]
            output.append(
                HistoricalGapAudit(
                    universe_id=universe_id,
                    instrument_id=result.instrument_id,
                    display_ticker=evidence.provider_ticker,
                    provider_type_code=evidence.provider_type_code,
                    first_bar_session=sessions[0] if sessions else None,
                    last_bar_session=sessions[-1] if sessions else None,
                    observation_count=len(sessions),
                    missing_sessions=missing,
                    same_day_identity_present=presence,
                    previous_bar_present=descriptor.previous_session in sessions,
                    primary_reason=reason,
                )
            )
    return tuple(sorted(output, key=lambda item: (item.universe_id, str(item.instrument_id))))
