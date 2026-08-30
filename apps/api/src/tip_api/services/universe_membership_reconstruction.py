"""Point-in-time Daily Universe Membership reconstruction from completed reviewed facts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Mapping
from uuid import UUID

from tip_api.contracts.common import QualityStatus, normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    FullBaseDecisionV1,
    FullBaseDisposition,
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipOrigin,
)
from tip_api.persistence.parquet.superseding_full_base import CompletedSupersedingFullBase
from tip_api.services.full_base_liquidity import FULL_BASE_A_ID, FULL_BASE_B_ID
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID

PUBLIC_SECONDARY_ID = "provider_classified_common_shares_plus_adrs_v1"
METHODOLOGY_VERSION = "provider-form-full-base-point-in-time-v1"
POLICY_TO_UNIVERSE = {
    FULL_BASE_A_ID: CANDIDATE_A_ID,
    FULL_BASE_B_ID: PUBLIC_SECONDARY_ID,
}

_QUARANTINE_DISPOSITIONS = frozenset(
    {
        FullBaseDisposition.MISSING_CURRENT_BAR,
        FullBaseDisposition.MISSING_PREVIOUS_BAR,
        FullBaseDisposition.INSUFFICIENT_HISTORY,
        FullBaseDisposition.OUTLIER_QUARANTINE,
        FullBaseDisposition.REVIEWED_QUARANTINE,
        FullBaseDisposition.INVALID_INPUT,
    }
)


@dataclass(frozen=True, slots=True)
class UniverseMembershipReconstruction:
    records: tuple[UniverseMembershipDecisionV1, ...]
    session_date: date
    methodology_version: str
    evaluated_base_count: int
    evaluated_base_fingerprint: str
    source_fingerprints: tuple[str, ...]
    included_counts: tuple[tuple[str, int], ...]
    excluded_counts: tuple[tuple[str, int], ...]
    quarantined_counts: tuple[tuple[str, int], ...]


def stable_instrument_set_fingerprint(instrument_ids: frozenset[UUID]) -> str:
    """Fingerprint an exact stable-ID set using its canonical sorted JSON representation."""

    payload = json.dumps(
        [str(item) for item in sorted(instrument_ids, key=str)],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def reconstruct_daily_universe_membership(
    *,
    session_date: date,
    source_decisions: tuple[FullBaseDecisionV1, ...],
    evaluated_base_ids: frozenset[UUID],
    source_policy_to_universe: Mapping[str, str],
    source_fingerprints: tuple[str, ...],
    source_data_cutoff: datetime,
    evaluated_at: datetime,
    methodology_version: str = METHODOLOGY_VERSION,
) -> UniverseMembershipReconstruction:
    """Create a complete daily ledger without projecting a current membership backward."""

    if not evaluated_base_ids:
        raise ValueError("evaluated base must not be empty")
    if not source_policy_to_universe:
        raise ValueError("at least one source policy is required")
    if len(set(source_policy_to_universe.values())) != len(source_policy_to_universe):
        raise ValueError("target universe IDs must be unique")
    source_fingerprints = tuple(sorted(set(source_fingerprints)))
    if not source_fingerprints:
        raise ValueError("source fingerprints must not be empty")
    source_data_cutoff = normalize_utc_datetime(source_data_cutoff)
    evaluated_at = normalize_utc_datetime(evaluated_at)
    if source_data_cutoff > evaluated_at:
        raise ValueError("source_data_cutoff must not follow evaluated_at")

    indexed: dict[tuple[str, UUID], FullBaseDecisionV1] = {}
    for decision in source_decisions:
        if decision.analysis_session != session_date:
            raise ValueError("source decision analysis session mismatch")
        if decision.membership_evidence_as_of_date > session_date:
            raise ValueError("future-dated membership evidence is forbidden")
        key = (decision.policy_id, decision.instrument_id)
        if key in indexed:
            raise ValueError("duplicate source policy/instrument decision")
        indexed[key] = decision

    expected_keys = {
        (policy_id, instrument_id)
        for policy_id in source_policy_to_universe
        for instrument_id in evaluated_base_ids
    }
    actual_keys = set(indexed)
    if actual_keys != expected_keys:
        missing = len(expected_keys - actual_keys)
        extra = len(actual_keys - expected_keys)
        raise ValueError(f"source decision ledger is incomplete or out of scope: missing={missing}, extra={extra}")

    base_fingerprint = stable_instrument_set_fingerprint(evaluated_base_ids)
    source_known_after_session = source_data_cutoff.date() > session_date
    records = []
    for source_policy, universe_id in sorted(source_policy_to_universe.items(), key=lambda item: item[1]):
        for instrument_id in sorted(evaluated_base_ids, key=str):
            source = indexed[(source_policy, instrument_id)]
            disposition = _membership_disposition(source)
            reasons = set(source.reason_codes) | {f"source_disposition:{source.disposition.value}"}
            if source_known_after_session:
                reasons.add("reconstruction_source_cutoff_after_session")
            reason_codes = tuple(sorted(reasons))
            records.append(
                UniverseMembershipDecisionV1(
                    universe_id=universe_id,
                    instrument_id=instrument_id,
                    session_date=session_date,
                    methodology_version=methodology_version,
                    origin=UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME,
                    disposition=disposition,
                    is_member={
                        UniverseMembershipDisposition.INCLUDED: True,
                        UniverseMembershipDisposition.EXCLUDED: False,
                        UniverseMembershipDisposition.QUARANTINED: None,
                    }[disposition],
                    reason_codes=reason_codes,
                    evaluated_base_fingerprint=base_fingerprint,
                    source_fingerprints=source_fingerprints,
                    source_data_cutoff=source_data_cutoff,
                    evaluated_at=evaluated_at,
                    quality_status=(
                        QualityStatus.PENDING_REVIEW
                        if disposition is UniverseMembershipDisposition.QUARANTINED
                        else QualityStatus.WARNING
                        if source_known_after_session
                        else QualityStatus.VALID
                    ),
                )
            )
    output = tuple(records)
    return UniverseMembershipReconstruction(
        records=output,
        session_date=session_date,
        methodology_version=methodology_version,
        evaluated_base_count=len(evaluated_base_ids),
        evaluated_base_fingerprint=base_fingerprint,
        source_fingerprints=source_fingerprints,
        included_counts=_counts(output, UniverseMembershipDisposition.INCLUDED),
        excluded_counts=_counts(output, UniverseMembershipDisposition.EXCLUDED),
        quarantined_counts=_counts(output, UniverseMembershipDisposition.QUARANTINED),
    )


def reconstruct_from_superseding_full_base(
    completed: CompletedSupersedingFullBase,
    *,
    evaluated_at: datetime,
) -> UniverseMembershipReconstruction:
    """Adapt one formally reread reviewed full-base snapshot to the daily contract."""

    manifest = completed.manifest
    if manifest.membership_evidence_as_of_date > manifest.analysis_session:
        raise ValueError("future-dated superseding membership evidence is forbidden")
    evaluated_base_ids = frozenset(item.instrument_id for item in completed.metrics)
    if len(evaluated_base_ids) != len(completed.metrics):
        raise ValueError("superseding metric base contains duplicate stable IDs")
    source_fingerprints = (
        manifest.source_full_base_logical_fingerprint,
        manifest.source_descriptor_fingerprint,
        manifest.reviewed_security_form_dataset.content_fingerprint,
        manifest.metric_dataset.content_fingerprint,
        manifest.decision_dataset.content_fingerprint,
        manifest.logical_content_fingerprint,
    )
    return reconstruct_daily_universe_membership(
        session_date=manifest.analysis_session,
        source_decisions=completed.decisions,
        evaluated_base_ids=evaluated_base_ids,
        source_policy_to_universe=POLICY_TO_UNIVERSE,
        source_fingerprints=source_fingerprints,
        source_data_cutoff=manifest.created_at.astimezone(UTC),
        evaluated_at=evaluated_at,
    )


def _membership_disposition(source: FullBaseDecisionV1) -> UniverseMembershipDisposition:
    if source.disposition is FullBaseDisposition.INCLUDED:
        return UniverseMembershipDisposition.INCLUDED
    if source.disposition in _QUARANTINE_DISPOSITIONS:
        return UniverseMembershipDisposition.QUARANTINED
    return UniverseMembershipDisposition.EXCLUDED


def _counts(
    records: tuple[UniverseMembershipDecisionV1, ...],
    disposition: UniverseMembershipDisposition,
) -> tuple[tuple[str, int], ...]:
    universes = sorted({record.universe_id for record in records})
    return tuple(
        (
            universe_id,
            sum(record.universe_id == universe_id and record.disposition is disposition for record in records),
        )
        for universe_id in universes
    )
