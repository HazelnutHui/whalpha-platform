"""Deterministic reviewed-override overlay and stable-ID Universe comparison."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Iterable
from uuid import NAMESPACE_URL, UUID, uuid5

from tip_api.contracts.security_classification.v1 import EvidenceGrade
from tip_api.contracts.security_classification.v1.universe_review import (
    ReviewedEligibilityDecision,
    ReviewedEligibilityOverrideV1,
    UniverseReviewDecisionV1,
    UniverseSetSummaryV1,
    validate_override_intervals,
)
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID, CANDIDATE_B_ID
from tip_api.services.security_classification import reviewed_overrides


@dataclass(frozen=True, slots=True)
class StableSetComparison:
    left_count: int
    right_count: int
    retained: int
    removed: int
    added: int
    left_fingerprint: str
    right_fingerprint: str


@dataclass(frozen=True, slots=True)
class UniverseReviewBundle:
    overrides: tuple[ReviewedEligibilityOverrideV1, ...]
    decisions: tuple[UniverseReviewDecisionV1, ...]
    summaries: tuple[UniverseSetSummaryV1, ...]
    final_memberships: dict[str, frozenset[UUID]]
    override_fingerprint: str


def repository_reviewed_overrides(*, created_at: datetime) -> tuple[ReviewedEligibilityOverrideV1, ...]:
    """Convert only the repository's explicitly reviewed authoritative registry."""
    created_at = created_at.astimezone(UTC)
    output = []
    for item in reviewed_overrides():
        decision = (
            ReviewedEligibilityDecision.EXCLUDE
            if item.universe_disposition.value == "excluded"
            else ReviewedEligibilityDecision.ALLOW
        )
        effective_from = max(item.effective_from, item.source_document_date)
        output.append(
            ReviewedEligibilityOverrideV1(
                override_id=uuid5(
                    NAMESPACE_URL,
                    f"tip:reviewed-eligibility:{item.instrument_id}:{effective_from}:{decision.value}",
                ),
                instrument_id=item.instrument_id,
                effective_from=effective_from,
                effective_to=item.effective_to,
                decision=decision,
                asserted_security_form=item.security_form,
                asserted_issuer_structure=item.issuer_structure,
                evidence_grade=EvidenceGrade.AUTHORITATIVE,
                source_reference=item.source_url,
                source_document_date=item.source_document_date,
                reviewer_identifier=item.reviewer,
                reason_code=("reviewed_closed_end_fund_exclusion" if decision is ReviewedEligibilityDecision.EXCLUDE else "reviewed_operating_ordinary_share_allow"),
                reason=item.reason,
                created_at=created_at,
            )
        )
    result = tuple(sorted(output, key=lambda item: (str(item.instrument_id), item.effective_from)))
    validate_override_intervals(result)
    return result


def build_universe_review(
    *,
    analysis_session: date,
    passed_by_universe: dict[str, frozenset[UUID]],
    provider_type_by_id: dict[UUID, str],
    trailing_decision_fingerprint: str,
    overrides: tuple[ReviewedEligibilityOverrideV1, ...],
    created_at: datetime,
) -> UniverseReviewBundle:
    validate_override_intervals(overrides)
    if set(passed_by_universe) != {CANDIDATE_A_ID, CANDIDATE_B_ID}:
        raise ValueError("exact Candidate A/B passed sets are required")
    if not passed_by_universe[CANDIDATE_A_ID] <= passed_by_universe[CANDIDATE_B_ID]:
        raise ValueError("Candidate A passed members must be a subset of Candidate B")
    active = {}
    for item in overrides:
        if item.is_effective_on(analysis_session):
            if item.instrument_id in active:
                raise ValueError("multiple active override decisions")
            active[item.instrument_id] = item
    override_fingerprint = records_fingerprint(overrides)
    decisions = []
    final = {}
    summaries = []
    for universe_id in (CANDIDATE_A_ID, CANDIDATE_B_ID):
        members = passed_by_universe[universe_id]
        final_ids = set()
        exclusion_count = 0
        quarantine_count = 0
        for instrument_id in sorted(members, key=str):
            if instrument_id not in provider_type_by_id:
                raise ValueError("passed member has no provider type evidence")
            provider_type = provider_type_by_id[instrument_id]
            allowed = {"CS"} if universe_id == CANDIDATE_A_ID else {"CS", "ADRC"}
            if provider_type not in allowed:
                raise ValueError("passed member has disallowed provider security type")
            override = active.get(instrument_id)
            excluded = override is not None and override.decision in {
                ReviewedEligibilityDecision.EXCLUDE,
                ReviewedEligibilityDecision.QUARANTINE,
            }
            if excluded:
                exclusion_count += 1
                if override.decision is ReviewedEligibilityDecision.QUARANTINE:
                    exclusion_count -= 1
                    quarantine_count += 1
            else:
                final_ids.add(instrument_id)
            decisions.append(
                UniverseReviewDecisionV1(
                    analysis_session=analysis_session,
                    universe_id=universe_id,
                    instrument_id=instrument_id,
                    provider_type_code=provider_type,
                    override_decision=None if override is None else override.decision,
                    final_included=not excluded,
                    primary_reason=(override.reason_code if excluded else "trailing_liquidity_passed"),
                    source_trailing_decision_fingerprint=trailing_decision_fingerprint,
                    reviewed_override_fingerprint=override_fingerprint,
                    created_at=created_at,
                )
            )
        frozen = frozenset(final_ids)
        final[universe_id] = frozen
        summaries.append(
            UniverseSetSummaryV1(
                universe_id=universe_id,
                base_passed_count=len(members),
                final_count=len(frozen),
                reviewed_exclusion_count=exclusion_count,
                reviewed_quarantine_count=quarantine_count,
                membership_fingerprint=membership_fingerprint(frozen),
            )
        )
    if len({(item.universe_id, item.instrument_id) for item in decisions}) != len(decisions):
        raise ValueError("duplicate Universe review business key")
    return UniverseReviewBundle(overrides, tuple(decisions), tuple(summaries), final, override_fingerprint)


def compare_stable_sets(left: Iterable[UUID], right: Iterable[UUID]) -> StableSetComparison:
    left, right = frozenset(left), frozenset(right)
    return StableSetComparison(len(left), len(right), len(left & right), len(left - right), len(right - left), membership_fingerprint(left), membership_fingerprint(right))


def membership_fingerprint(ids: Iterable[UUID]) -> str:
    return _fingerprint([str(item) for item in sorted(set(ids), key=str)])


def records_fingerprint(records: Iterable[ReviewedEligibilityOverrideV1]) -> str:
    rows = [
        item.model_dump(mode="json", exclude={"created_at"})
        for item in sorted(records, key=lambda item: (str(item.instrument_id), item.effective_from))
    ]
    return _fingerprint(rows)


def reason_distribution(decision_status_by_id: dict[UUID, str], *, legacy: frozenset[UUID], candidate: frozenset[UUID], adrc_ids: frozenset[UUID]) -> dict[str, int]:
    reasons = Counter()
    for instrument_id in legacy - candidate:
        reasons["ADRC" if instrument_id in adrc_ids else decision_status_by_id.get(instrument_id, "other")] += 1
    return dict(sorted(reasons.items()))


def _fingerprint(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
