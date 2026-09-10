"""Outcome-blind coverage census for Strong-Leader Pullback development."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable
from uuid import UUID

from tip_api.contracts.analytics.v1.candidate_strategy_development_coverage import (
    STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY,
    STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE,
    STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT,
    DevelopmentCoverageDatasetEvidenceV1,
    DevelopmentCoverageEvidenceStatus,
    DevelopmentCoverageReasonCountV1,
    StrongLeaderPullbackDevelopmentCoverageCensusV1,
    StrongLeaderPullbackDevelopmentInstrumentCoverageV1,
    StrongLeaderPullbackDevelopmentSessionCoverageV1,
    coverage_census_fingerprint,
)
from tip_api.contracts.common import QualityStatus, normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
    CanonicalSplitActionPublicationV1,
    CanonicalSplitActionV1,
    CanonicalSplitAdjustmentPublicationV1,
    CorporateActionRecordStatus,
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipOrigin,
    UniverseMembershipPartitionManifestV1,
)
from tip_api.services.market_calendar import MarketSessionCalendar


class StrongLeaderPullbackDevelopmentCoverageError(RuntimeError):
    """Raised when the census input cannot prove its bounded claims."""


@dataclass(frozen=True, slots=True)
class ReconstructedMembershipSessionEvidence:
    """Formally reread evidence for one reconstructed Membership partition."""

    manifest: UniverseMembershipPartitionManifestV1
    manifest_sha256: str
    records: tuple[UniverseMembershipDecisionV1, ...]
    identity_source_logical_fingerprint: str
    identity_source_record_count: int
    identity_source_content_fingerprint: str
    identity_source_manifest_sha256: str
    identity_source_parquet_sha256: str
    identity_source_materialized_at: datetime


@dataclass(slots=True)
class _InstrumentAccumulator:
    evaluated_session_count: int = 0
    included_session_count: int = 0
    excluded_session_count: int = 0
    quarantined_session_count: int = 0
    raw_feature_path_complete_count: int = 0
    sparse_clear_split_exposure_count: int = 0
    split_quarantined_path_count: int = 0
    absent_row_neutrality_unproven_path_count: int = 0
    lifecycle_unavailable_path_count: int = 0
    first_evaluated_session: date | None = None
    last_evaluated_session: date | None = None
    first_included_session: date | None = None
    last_included_session: date | None = None
    reason_counts: Counter[str] = field(default_factory=Counter)


def build_strong_leader_pullback_development_coverage_census(
    *,
    membership_sessions: Iterable[ReconstructedMembershipSessionEvidence],
    split_action_publication: CanonicalSplitActionPublicationV1,
    split_actions: tuple[CanonicalSplitActionV1, ...],
    split_action_manifest_sha256: str,
    split_adjustment_publication: CanonicalSplitAdjustmentPublicationV1,
    split_adjustments: tuple[AdjustmentLedgerEntryV1, ...],
    split_adjustment_manifest_sha256: str,
    source_revision: str,
    calculated_at: datetime,
    calendar: MarketSessionCalendar,
) -> StrongLeaderPullbackDevelopmentCoverageCensusV1:
    """Build the fixed, outcome-blind census without opening strategy outcomes."""

    calculated_at = normalize_utc_datetime(calculated_at)
    expected_sessions = _expected_sessions(calendar)
    _validate_shared_inputs(
        expected_sessions=expected_sessions,
        split_action_publication=split_action_publication,
        split_actions=split_actions,
        split_action_manifest_sha256=split_action_manifest_sha256,
        split_adjustment_publication=split_adjustment_publication,
        split_adjustments=split_adjustments,
        split_adjustment_manifest_sha256=split_adjustment_manifest_sha256,
        calculated_at=calculated_at,
    )

    clear_adjustment_keys = {
        (item.instrument_id, item.source_session)
        for item in split_adjustments
        if item.split_adjustment_status is AdjustmentAvailabilityStatus.CLEAR
    }
    active_action_keys = {
        (item.instrument_id, item.effective_date)
        for item in split_actions
        if item.record_status is CorporateActionRecordStatus.ACTIVE
    }
    quarantined_adjustment_keys = {
        (item.instrument_id, item.source_session)
        for item in split_adjustments
        if item.split_adjustment_status
        is not AdjustmentAvailabilityStatus.CLEAR
    }
    quarantined_action_keys = {
        (item.instrument_id, item.effective_date)
        for item in split_actions
        if item.record_status is not CorporateActionRecordStatus.ACTIVE
    }
    unresolved_impact_keys = {
        (impact.instrument_id, effective_date)
        for impact in split_action_publication.possible_unresolved_impacts
        for effective_date in impact.effective_dates
    }

    session_rows: list[StrongLeaderPullbackDevelopmentSessionCoverageV1] = []
    instruments: dict[UUID, _InstrumentAccumulator] = {}
    identity_record_count = 0
    membership_record_count = 0
    identity_logical_bindings: list[dict[str, object]] = []
    identity_physical_bindings: list[dict[str, object]] = []
    membership_logical_bindings: list[dict[str, object]] = []
    membership_physical_bindings: list[dict[str, object]] = []

    membership_iterator = iter(membership_sessions)
    for expected_session in expected_sessions:
        try:
            evidence = next(membership_iterator)
        except StopIteration as exc:
            raise StrongLeaderPullbackDevelopmentCoverageError(
                "Membership evidence does not exactly cover the fixed census interval"
            ) from exc
        session_date = evidence.manifest.session_date
        if session_date != expected_session:
            raise StrongLeaderPullbackDevelopmentCoverageError(
                "Membership evidence does not exactly cover the fixed census interval"
            )
        window = frozenset((*calendar.sessions_before(session_date, 20), session_date))
        action_window_coverage_incomplete = (
            min(window) < split_action_publication.start_date
        )
        adjustment_window_coverage_incomplete = (
            min(window) < split_adjustment_publication.first_source_session
        )
        primary = _validate_membership_session(
            evidence, calculated_at=calculated_at
        )
        identity_record_count += evidence.identity_source_record_count
        membership_record_count += evidence.manifest.record_count
        identity_logical_bindings.append(
            {
                "session_date": session_date.isoformat(),
                "logical_fingerprint": evidence.identity_source_logical_fingerprint,
                "content_fingerprint": evidence.identity_source_content_fingerprint,
            }
        )
        identity_physical_bindings.append(
            {
                "session_date": session_date.isoformat(),
                "manifest_sha256": evidence.identity_source_manifest_sha256,
                "parquet_sha256": evidence.identity_source_parquet_sha256,
            }
        )
        membership_logical_bindings.append(
            {
                "session_date": session_date.isoformat(),
                "logical_fingerprint": evidence.manifest.logical_fingerprint,
            }
        )
        membership_physical_bindings.append(
            {
                "session_date": session_date.isoformat(),
                "manifest_sha256": evidence.manifest_sha256,
                "parquet_sha256": evidence.manifest.physical_sha256,
            }
        )

        disposition_counts = Counter(item.disposition for item in primary)
        session_reasons: Counter[str] = Counter()
        clear_exposures = 0
        quarantined_paths = 0
        for decision in primary:
            accumulator = instruments.setdefault(
                decision.instrument_id, _InstrumentAccumulator()
            )
            _record_membership_decision(accumulator, decision)
            session_reasons.update(decision.reason_codes)
            if decision.disposition is not UniverseMembershipDisposition.INCLUDED:
                continue

            path_keys = {(decision.instrument_id, item) for item in window}
            event_window_keys = {
                (decision.instrument_id, item)
                for item in window
                if item > min(window)
            }
            active_event_in_window = bool(event_window_keys & active_action_keys)
            clear_adjustment_in_window = bool(
                path_keys & clear_adjustment_keys
            )
            clear_exposure = (
                active_event_in_window and clear_adjustment_in_window
            )
            quarantined_path = bool(
                event_window_keys
                & (quarantined_action_keys | unresolved_impact_keys)
            ) or (
                active_event_in_window
                and (
                    not clear_adjustment_in_window
                    or bool(path_keys & quarantined_adjustment_keys)
                )
            ) or action_window_coverage_incomplete or (
                adjustment_window_coverage_incomplete
            )
            accumulator.raw_feature_path_complete_count += 1
            accumulator.absent_row_neutrality_unproven_path_count += 1
            accumulator.lifecycle_unavailable_path_count += 1
            accumulator.reason_counts.update(
                (
                    "raw_feature_path_complete",
                    "absent_row_neutrality_unproven",
                    "instrument_lifecycle_unavailable",
                )
            )
            session_reasons.update(
                (
                    "raw_feature_path_complete",
                    "absent_row_neutrality_unproven",
                    "instrument_lifecycle_unavailable",
                )
            )
            if clear_exposure:
                clear_exposures += 1
                accumulator.sparse_clear_split_exposure_count += 1
                accumulator.reason_counts["sparse_clear_split_exposure"] += 1
                session_reasons["sparse_clear_split_exposure"] += 1
            if quarantined_path:
                quarantined_paths += 1
                accumulator.split_quarantined_path_count += 1
                accumulator.reason_counts["split_path_quarantined"] += 1
                session_reasons["split_path_quarantined"] += 1
                if action_window_coverage_incomplete:
                    accumulator.reason_counts[
                        "split_action_window_coverage_incomplete"
                    ] += 1
                    session_reasons[
                        "split_action_window_coverage_incomplete"
                    ] += 1
                if adjustment_window_coverage_incomplete:
                    accumulator.reason_counts[
                        "split_adjustment_window_coverage_incomplete"
                    ] += 1
                    session_reasons[
                        "split_adjustment_window_coverage_incomplete"
                    ] += 1

        session_rows.append(
            StrongLeaderPullbackDevelopmentSessionCoverageV1(
                session_date=session_date,
                membership_logical_fingerprint=(
                    evidence.manifest.logical_fingerprint
                ),
                membership_physical_sha256=evidence.manifest.physical_sha256,
                membership_manifest_sha256=evidence.manifest_sha256,
                identity_source_logical_fingerprint=(
                    evidence.identity_source_logical_fingerprint
                ),
                evaluated_base_count=evidence.manifest.evaluated_base_count,
                primary_included_count=disposition_counts[
                    UniverseMembershipDisposition.INCLUDED
                ],
                primary_excluded_count=disposition_counts[
                    UniverseMembershipDisposition.EXCLUDED
                ],
                primary_quarantined_count=disposition_counts[
                    UniverseMembershipDisposition.QUARANTINED
                ],
                raw_feature_path_complete_count=disposition_counts[
                    UniverseMembershipDisposition.INCLUDED
                ],
                sparse_clear_split_exposure_count=clear_exposures,
                split_quarantined_path_count=quarantined_paths,
                absent_row_neutrality_unproven_path_count=disposition_counts[
                    UniverseMembershipDisposition.INCLUDED
                ],
                lifecycle_unavailable_path_count=disposition_counts[
                    UniverseMembershipDisposition.INCLUDED
                ],
                reason_counts=_reason_counts(session_reasons),
            )
        )
    try:
        next(membership_iterator)
    except StopIteration:
        pass
    else:
        raise StrongLeaderPullbackDevelopmentCoverageError(
            "Membership evidence does not exactly cover the fixed census interval"
        )

    instrument_rows = tuple(
        _instrument_coverage(instrument_id, accumulator)
        for instrument_id, accumulator in sorted(
            instruments.items(), key=lambda item: str(item[0])
        )
    )
    dataset_evidence = _dataset_evidence(
        session_count=len(expected_sessions),
        identity_record_count=identity_record_count,
        membership_record_count=membership_record_count,
        identity_logical_fingerprint=_fingerprint(identity_logical_bindings),
        identity_physical_fingerprint=_fingerprint(identity_physical_bindings),
        membership_logical_fingerprint=_fingerprint(
            membership_logical_bindings
        ),
        membership_physical_fingerprint=_fingerprint(
            membership_physical_bindings
        ),
        split_action_publication=split_action_publication,
        split_action_manifest_sha256=split_action_manifest_sha256,
        split_adjustment_publication=split_adjustment_publication,
        split_adjustment_manifest_sha256=split_adjustment_manifest_sha256,
    )
    totals = _aggregate_session_rows(tuple(session_rows))
    values = {
        "source_revision": source_revision,
        "calculated_at": calculated_at,
        "calendar_version": calendar.calendar_version,
        "dataset_evidence": dataset_evidence,
        "instrument_count": len(instrument_rows),
        "primary_decision_count": sum(totals[:3]),
        "primary_included_count": totals[0],
        "primary_excluded_count": totals[1],
        "primary_quarantined_count": totals[2],
        "raw_feature_path_complete_count": totals[3],
        "sparse_clear_split_exposure_count": totals[4],
        "split_quarantined_path_count": totals[5],
        "absent_row_neutrality_unproven_path_count": totals[6],
        "lifecycle_unavailable_path_count": totals[7],
        "sessions": tuple(session_rows),
        "instruments": instrument_rows,
    }
    provisional = StrongLeaderPullbackDevelopmentCoverageCensusV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackDevelopmentCoverageCensusV1.model_validate(
        {
            **values,
            "logical_fingerprint": coverage_census_fingerprint(provisional),
        }
    )


def _expected_sessions(calendar: MarketSessionCalendar) -> tuple[date, ...]:
    values = [STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION]
    while len(values) < STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT:
        values.append(calendar.next_session(values[-1]))
    result = tuple(values)
    if result[-1] != STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION:
        raise StrongLeaderPullbackDevelopmentCoverageError(
            "fixed census interval differs from the bound calendar"
        )
    return result


def _validate_shared_inputs(
    *,
    expected_sessions: tuple[date, ...],
    split_action_publication: CanonicalSplitActionPublicationV1,
    split_actions: tuple[CanonicalSplitActionV1, ...],
    split_action_manifest_sha256: str,
    split_adjustment_publication: CanonicalSplitAdjustmentPublicationV1,
    split_adjustments: tuple[AdjustmentLedgerEntryV1, ...],
    split_adjustment_manifest_sha256: str,
    calculated_at: datetime,
) -> None:
    _require_sha256(split_action_manifest_sha256, "split-action manifest")
    _require_sha256(split_adjustment_manifest_sha256, "split-adjustment manifest")
    action_status_counts = Counter(item.record_status for item in split_actions)
    if (
        len(split_actions) != split_action_publication.action_record_count
        or action_status_counts[CorporateActionRecordStatus.ACTIVE]
        != split_action_publication.active_action_record_count
        or sum(
            count
            for status, count in action_status_counts.items()
            if status is not CorporateActionRecordStatus.ACTIVE
        )
        != split_action_publication.quarantined_action_record_count
        or split_action_publication.start_date > expected_sessions[0]
        or split_action_publication.end_date < expected_sessions[-1]
        or split_action_publication.point_in_time_eligibility
        != "outcome_reconciliation_only"
        or split_action_publication.neutral_factor_inference_authorized
        or split_action_publication.historical_coverage_authorized
        or split_action_publication.research_performance_authorized
        or calculated_at < split_action_publication.created_at
    ):
        raise StrongLeaderPullbackDevelopmentCoverageError(
            "split-action evidence scope or authority differs"
        )
    adjustment_status_counts = Counter(
        item.split_adjustment_status for item in split_adjustments
    )
    if (
        len(split_adjustments) != split_adjustment_publication.record_count
        or adjustment_status_counts[AdjustmentAvailabilityStatus.CLEAR]
        != split_adjustment_publication.clear_record_count
        or sum(
            count
            for status, count in adjustment_status_counts.items()
            if status is not AdjustmentAvailabilityStatus.CLEAR
        )
        != split_adjustment_publication.quarantined_record_count
        or split_adjustment_publication.first_source_session
        > expected_sessions[0]
        or split_adjustment_publication.basis_session < expected_sessions[-1]
        or split_adjustment_publication.canonical_action_publication_fingerprint
        != split_action_publication.logical_fingerprint
        or split_adjustment_publication.canonical_action_publication_sha256
        != split_action_manifest_sha256
        or split_adjustment_publication.point_in_time_eligibility
        != "outcome_reconciliation_only"
        or split_adjustment_publication.absent_row_neutrality_authorized
        or split_adjustment_publication.full_adjustment_coverage_authorized
        or split_adjustment_publication.historical_coverage_authorized
        or split_adjustment_publication.research_performance_authorized
        or calculated_at < split_adjustment_publication.calculated_at
    ):
        raise StrongLeaderPullbackDevelopmentCoverageError(
            "split-adjustment evidence scope or authority differs"
        )


def _validate_membership_session(
    evidence: ReconstructedMembershipSessionEvidence,
    *,
    calculated_at: datetime,
) -> tuple[UniverseMembershipDecisionV1, ...]:
    manifest = evidence.manifest
    _require_sha256(evidence.manifest_sha256, "Membership manifest")
    _require_sha256(
        evidence.identity_source_logical_fingerprint, "Identity source logical"
    )
    _require_sha256(
        evidence.identity_source_content_fingerprint, "Identity source content"
    )
    _require_sha256(
        evidence.identity_source_manifest_sha256, "Identity source manifest"
    )
    _require_sha256(
        evidence.identity_source_parquet_sha256, "Identity source Parquet"
    )
    materialized_at = normalize_utc_datetime(evidence.identity_source_materialized_at)
    if (
        manifest.methodology_version
        != STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY
        or manifest.origin is not UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME
        or STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE
        not in manifest.universe_ids
        or manifest.record_count != len(evidence.records)
        or evidence.identity_source_record_count < 1
        or evidence.identity_source_logical_fingerprint
        not in manifest.source_fingerprints
        or materialized_at > manifest.evaluated_at
        or manifest.created_at > calculated_at
    ):
        raise StrongLeaderPullbackDevelopmentCoverageError(
            "Membership session evidence or lineage differs"
        )
    keys: set[tuple[str, UUID]] = set()
    by_universe: dict[str, set[UUID]] = {
        universe_id: set() for universe_id in manifest.universe_ids
    }
    primary: list[UniverseMembershipDecisionV1] = []
    for item in evidence.records:
        key = (item.universe_id, item.instrument_id)
        if (
            key in keys
            or item.session_date != manifest.session_date
            or item.methodology_version != manifest.methodology_version
            or item.origin is not manifest.origin
            or item.evaluated_base_fingerprint
            != manifest.evaluated_base_fingerprint
            or item.source_fingerprints != manifest.source_fingerprints
            or item.source_data_cutoff != manifest.source_data_cutoff
            or item.evaluated_at != manifest.evaluated_at
            or item.universe_id not in by_universe
        ):
            raise StrongLeaderPullbackDevelopmentCoverageError(
                "Membership row binding differs"
            )
        keys.add(key)
        by_universe[item.universe_id].add(item.instrument_id)
        if item.universe_id == STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE:
            primary.append(item)
    bases = tuple(frozenset(by_universe[item]) for item in manifest.universe_ids)
    if (
        not bases
        or any(item != bases[0] for item in bases[1:])
        or len(bases[0]) != manifest.evaluated_base_count
        or len(primary) != manifest.evaluated_base_count
    ):
        raise StrongLeaderPullbackDevelopmentCoverageError(
            "Membership complete evaluated-base proof differs"
        )
    summary = next(
        item
        for item in manifest.disposition_summaries
        if item.universe_id == STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE
    )
    counts = Counter(item.disposition for item in primary)
    if (
        counts[UniverseMembershipDisposition.INCLUDED] != summary.included_count
        or counts[UniverseMembershipDisposition.EXCLUDED]
        != summary.excluded_count
        or counts[UniverseMembershipDisposition.QUARANTINED]
        != summary.quarantined_count
    ):
        raise StrongLeaderPullbackDevelopmentCoverageError(
            "Membership Primary disposition summary differs"
        )
    for item in primary:
        if item.disposition is UniverseMembershipDisposition.INCLUDED and (
            "full_base_trailing_liquidity_passed" not in item.reason_codes
            or "provisional_provider_security_form_policy" not in item.reason_codes
            or item.quality_status not in {QualityStatus.VALID, QualityStatus.WARNING}
        ):
            raise StrongLeaderPullbackDevelopmentCoverageError(
                "included Membership row does not prove the raw feature window"
            )
    return tuple(primary)


def _record_membership_decision(
    accumulator: _InstrumentAccumulator,
    decision: UniverseMembershipDecisionV1,
) -> None:
    accumulator.evaluated_session_count += 1
    accumulator.reason_counts.update(decision.reason_codes)
    accumulator.first_evaluated_session = (
        decision.session_date
        if accumulator.first_evaluated_session is None
        else min(accumulator.first_evaluated_session, decision.session_date)
    )
    accumulator.last_evaluated_session = (
        decision.session_date
        if accumulator.last_evaluated_session is None
        else max(accumulator.last_evaluated_session, decision.session_date)
    )
    if decision.disposition is UniverseMembershipDisposition.INCLUDED:
        accumulator.included_session_count += 1
        accumulator.first_included_session = (
            decision.session_date
            if accumulator.first_included_session is None
            else min(accumulator.first_included_session, decision.session_date)
        )
        accumulator.last_included_session = (
            decision.session_date
            if accumulator.last_included_session is None
            else max(accumulator.last_included_session, decision.session_date)
        )
    elif decision.disposition is UniverseMembershipDisposition.EXCLUDED:
        accumulator.excluded_session_count += 1
    else:
        accumulator.quarantined_session_count += 1


def _instrument_coverage(
    instrument_id: UUID,
    accumulator: _InstrumentAccumulator,
) -> StrongLeaderPullbackDevelopmentInstrumentCoverageV1:
    if (
        accumulator.first_evaluated_session is None
        or accumulator.last_evaluated_session is None
    ):
        raise StrongLeaderPullbackDevelopmentCoverageError(
            "instrument accumulator lacks evaluated-session bounds"
        )
    return StrongLeaderPullbackDevelopmentInstrumentCoverageV1(
        instrument_id=instrument_id,
        evaluated_session_count=accumulator.evaluated_session_count,
        absent_from_evaluated_base_count=(
            STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT
            - accumulator.evaluated_session_count
        ),
        included_session_count=accumulator.included_session_count,
        excluded_session_count=accumulator.excluded_session_count,
        quarantined_session_count=accumulator.quarantined_session_count,
        raw_feature_path_complete_count=(
            accumulator.raw_feature_path_complete_count
        ),
        sparse_clear_split_exposure_count=(
            accumulator.sparse_clear_split_exposure_count
        ),
        split_quarantined_path_count=(
            accumulator.split_quarantined_path_count
        ),
        absent_row_neutrality_unproven_path_count=(
            accumulator.absent_row_neutrality_unproven_path_count
        ),
        lifecycle_unavailable_path_count=(
            accumulator.lifecycle_unavailable_path_count
        ),
        first_evaluated_session=accumulator.first_evaluated_session,
        last_evaluated_session=accumulator.last_evaluated_session,
        first_included_session=accumulator.first_included_session,
        last_included_session=accumulator.last_included_session,
        reason_counts=_reason_counts(accumulator.reason_counts),
    )


def _dataset_evidence(
    *,
    session_count: int,
    identity_record_count: int,
    membership_record_count: int,
    identity_logical_fingerprint: str,
    identity_physical_fingerprint: str,
    membership_logical_fingerprint: str,
    membership_physical_fingerprint: str,
    split_action_publication: CanonicalSplitActionPublicationV1,
    split_action_manifest_sha256: str,
    split_adjustment_publication: CanonicalSplitAdjustmentPublicationV1,
    split_adjustment_manifest_sha256: str,
) -> tuple[DevelopmentCoverageDatasetEvidenceV1, ...]:
    complete = DevelopmentCoverageEvidenceStatus.COMPLETE_RECONSTRUCTION_INPUT
    partial = (
        DevelopmentCoverageEvidenceStatus.PARTIAL_OUTCOME_RECONCILIATION_ONLY
    )
    unavailable = DevelopmentCoverageEvidenceStatus.UNAVAILABLE
    return (
        DevelopmentCoverageDatasetEvidenceV1(
            family="adjustment_ledger",
            status=partial,
            session_count=split_adjustment_publication.source_session_count,
            record_count=split_adjustment_publication.record_count,
            logical_fingerprint=split_adjustment_publication.logical_fingerprint,
            physical_fingerprint=split_adjustment_manifest_sha256,
            reason_codes=(
                "absent_row_neutrality_unproven",
                "affected_paths_only",
                "outcome_reconciliation_only",
            ),
        ),
        DevelopmentCoverageDatasetEvidenceV1(
            family="corporate_action",
            status=partial,
            session_count=split_adjustment_publication.source_session_count,
            record_count=split_action_publication.action_record_count,
            logical_fingerprint=split_action_publication.logical_fingerprint,
            physical_fingerprint=split_action_manifest_sha256,
            reason_codes=(
                "bounded_query_snapshot_only",
                "outcome_reconciliation_only",
                "split_only",
            ),
        ),
        DevelopmentCoverageDatasetEvidenceV1(
            family="eod_price_bar",
            status=complete,
            session_count=session_count,
            record_count=None,
            logical_fingerprint=membership_logical_fingerprint,
            physical_fingerprint=membership_physical_fingerprint,
            reason_codes=(
                "complete_21_session_feature_window_for_included_rows",
                "transitively_bound_by_formal_membership_reread",
            ),
        ),
        DevelopmentCoverageDatasetEvidenceV1(
            family="instrument_lifecycle",
            status=unavailable,
            session_count=0,
            reason_codes=("canonical_lifecycle_family_unavailable",),
        ),
        DevelopmentCoverageDatasetEvidenceV1(
            family="point_in_time_identity",
            status=complete,
            session_count=session_count,
            record_count=identity_record_count,
            logical_fingerprint=identity_logical_fingerprint,
            physical_fingerprint=identity_physical_fingerprint,
            reason_codes=(
                "canonical_normalized_source_custody",
                "latest_vintage_reconstruction_only",
            ),
        ),
        DevelopmentCoverageDatasetEvidenceV1(
            family="universe_membership",
            status=complete,
            session_count=session_count,
            record_count=membership_record_count,
            logical_fingerprint=membership_logical_fingerprint,
            physical_fingerprint=membership_physical_fingerprint,
            reason_codes=(
                "complete_three_state_evaluated_base",
                "latest_vintage_reconstruction_only",
            ),
        ),
    )


def _aggregate_session_rows(
    values: tuple[StrongLeaderPullbackDevelopmentSessionCoverageV1, ...],
) -> tuple[int, ...]:
    return (
        sum(item.primary_included_count for item in values),
        sum(item.primary_excluded_count for item in values),
        sum(item.primary_quarantined_count for item in values),
        sum(item.raw_feature_path_complete_count for item in values),
        sum(item.sparse_clear_split_exposure_count for item in values),
        sum(item.split_quarantined_path_count for item in values),
        sum(item.absent_row_neutrality_unproven_path_count for item in values),
        sum(item.lifecycle_unavailable_path_count for item in values),
    )


def _reason_counts(values: Counter[str]) -> tuple[DevelopmentCoverageReasonCountV1, ...]:
    return tuple(
        DevelopmentCoverageReasonCountV1(reason_code=reason, count=count)
        for reason, count in sorted(values.items())
        if count > 0
    )


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_sha256(value: str, name: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise StrongLeaderPullbackDevelopmentCoverageError(
            f"{name} fingerprint differs"
        )
