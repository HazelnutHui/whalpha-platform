"""Outcome-blind five-year split evidence adapter for Factor Catalog V2."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from pydantic_core import to_jsonable_python

from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    CorporateActionRecordStatus,
)
from tip_api.services.historical_split_adjustment_candidate import (
    HistoricalSplitAdjustmentCandidateV1,
    SplitAdjustmentEventCandidateV1,
)
from tip_api.services.historical_adjustment_invariants import (
    calculate_composed_split_adjustment_multipliers,
)


CONTRACT_VERSION = "quant-research-historical-split-extension/1.0"
ADJUSTMENT_METHODOLOGY = "resolved-event-ratio-to-qualification-basis-v1"


class QuantResearchHistoricalSplitExtensionV2Error(RuntimeError):
    """Raised when the private split extension cannot preserve its boundaries."""


@dataclass(frozen=True, slots=True)
class QuantResearchSplitAdjustmentV2:
    split_price_multiplier_to_basis: Decimal
    split_volume_multiplier_to_basis: Decimal


@dataclass(frozen=True, slots=True)
class QuantResearchHistoricalSplitEvidenceV2:
    source_action_fingerprint: str
    source_adjustment_fingerprint: str
    action_start: date
    adjustment_start: date
    active_action_keys: frozenset[tuple[UUID, date]]
    quarantined_action_keys: frozenset[tuple[UUID, date]]
    unresolved_impact_keys: frozenset[tuple[UUID, date]]
    clear_adjustments: dict[
        tuple[UUID, date], QuantResearchSplitAdjustmentV2
    ]
    quarantined_adjustment_keys: frozenset[tuple[UUID, date]]
    conflict_event_count: int
    conflict_adjustment_count: int


def build_quant_research_historical_split_evidence_v2(
    *,
    candidate: HistoricalSplitAdjustmentCandidateV1,
    candidate_file_sha256: str,
    canonical_action_source,
    canonical_adjustment_source,
    source_sessions: tuple[date, ...],
    required_ids: frozenset[UUID],
) -> QuantResearchHistoricalSplitEvidenceV2:
    """Reconcile a private five-year candidate with prior canonical evidence.

    This adapter is intentionally limited to outcome-blind factor qualification.
    It does not publish canonical facts or infer neutral actions from missing rows.
    """

    if (
        not source_sessions
        or source_sessions != tuple(sorted(set(source_sessions)))
        or candidate.start_date > source_sessions[0]
        or candidate.basis_session < source_sessions[-1]
        or candidate.point_in_time_eligibility != "outcome_reconciliation_only"
        or candidate.ledger_projection_status != "not_built"
        or candidate.total_return_adjustment_status != "unavailable"
        or re.fullmatch(r"[0-9a-f]{64}", candidate_file_sha256) is None
    ):
        raise QuantResearchHistoricalSplitExtensionV2Error(
            "historical split extension source boundary differs"
        )

    canonical_actions = canonical_action_source.actions
    action_publication = canonical_action_source.publication
    adjustment_publication = canonical_adjustment_source.publication
    if (
        action_publication.point_in_time_eligibility
        != "outcome_reconciliation_only"
        or action_publication.full_corporate_action_coverage_authorized
        or action_publication.research_performance_authorized
        or adjustment_publication.total_return_adjustment_authorized
        or adjustment_publication.absent_row_neutrality_authorized
        or adjustment_publication.historical_coverage_authorized
        or adjustment_publication.research_performance_authorized
    ):
        raise QuantResearchHistoricalSplitExtensionV2Error(
            "canonical split evidence authority differs"
        )

    candidate_by_key = {
        (item.instrument_id, item.effective_date): item
        for item in candidate.resolved_events
    }
    canonical_by_key = defaultdict(list)
    for item in canonical_actions:
        canonical_by_key[(item.instrument_id, item.effective_date)].append(item)

    conflict_event_keys: set[tuple[UUID, date]] = set()
    for key, rows in canonical_by_key.items():
        event = candidate_by_key.get(key)
        if event is None or _economic_rows(rows) != _candidate_economic_rows(event):
            conflict_event_keys.add(key)

    clear_events: dict[UUID, list[SplitAdjustmentEventCandidateV1]] = defaultdict(
        list
    )
    active_action_keys: set[tuple[UUID, date]] = set()
    quarantined_action_keys: set[tuple[UUID, date]] = set(conflict_event_keys)
    for key, event in candidate_by_key.items():
        if event.quality_flags or key in conflict_event_keys:
            quarantined_action_keys.add(key)
            continue
        active_action_keys.add(key)
        clear_events[event.instrument_id].append(event)
    for item in canonical_actions:
        key = (item.instrument_id, item.effective_date)
        if item.record_status is not CorporateActionRecordStatus.ACTIVE:
            quarantined_action_keys.add(key)

    unresolved_impact_keys = {
        (item.instrument_id, effective_date)
        for item in candidate.possible_unresolved_impacts
        for effective_date in item.effective_dates
    }
    unresolved_impact_keys.update(
        (item.instrument_id, effective_date)
        for item in action_publication.possible_unresolved_impacts
        for effective_date in item.effective_dates
    )

    qualification_basis = source_sessions[-1]
    clear_adjustments = _project_adjustments(
        clear_events=clear_events,
        required_ids=required_ids,
        source_sessions=source_sessions,
        basis_session=qualification_basis,
    )
    canonical_basis_adjustments = _project_canonical_adjustments(
        canonical_actions=canonical_actions,
        required_ids=required_ids,
        source_sessions=tuple(
            sorted(
                {
                    item.source_session
                    for item in canonical_adjustment_source.records
                    if item.instrument_id in required_ids
                }
            )
        ),
        basis_session=adjustment_publication.basis_session,
    )
    quarantined_adjustment_keys = {
        (item.instrument_id, item.source_session)
        for item in canonical_adjustment_source.records
        if item.instrument_id in required_ids
        and item.split_adjustment_status is not AdjustmentAvailabilityStatus.CLEAR
    }
    conflict_adjustment_keys: set[tuple[UUID, date]] = set()
    for item in canonical_adjustment_source.records:
        if (
            item.instrument_id not in required_ids
            or item.split_adjustment_status is not AdjustmentAvailabilityStatus.CLEAR
        ):
            continue
        key = (item.instrument_id, item.source_session)
        projected = canonical_basis_adjustments.get(key)
        if (
            projected is None
            or projected.split_price_multiplier_to_basis
            != item.split_price_multiplier_to_basis
            or projected.split_volume_multiplier_to_basis
            != item.split_volume_multiplier_to_basis
        ):
            conflict_adjustment_keys.add(key)
    quarantined_adjustment_keys.update(conflict_adjustment_keys)

    active_action_keys &= {
        key for key in active_action_keys if key[0] in required_ids
    }
    quarantined_action_keys = {
        key for key in quarantined_action_keys if key[0] in required_ids
    }
    unresolved_impact_keys = {
        key for key in unresolved_impact_keys if key[0] in required_ids
    }
    action_fingerprint = _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "evidence_role": "outcome_blind_factor_qualification_only",
            "canonical_action_fingerprint": action_publication.logical_fingerprint,
            "historical_candidate_file_sha256": candidate_file_sha256,
            "historical_candidate_fingerprint": candidate.logical_fingerprint,
            "active_action_keys": _key_rows(active_action_keys),
            "quarantined_action_keys": _key_rows(quarantined_action_keys),
            "unresolved_impact_keys": _key_rows(unresolved_impact_keys),
            "neutral_absence_inferred": False,
        }
    )
    adjustment_fingerprint = _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "methodology": ADJUSTMENT_METHODOLOGY,
            "source_action_fingerprint": action_fingerprint,
            "canonical_adjustment_fingerprint": (
                adjustment_publication.logical_fingerprint
            ),
            "qualification_basis_session": qualification_basis,
            "source_sessions": source_sessions,
            "clear_adjustments": tuple(
                {
                    "instrument_id": str(instrument_id),
                    "source_session": source_session.isoformat(),
                    "price": str(value.split_price_multiplier_to_basis),
                    "volume": str(value.split_volume_multiplier_to_basis),
                }
                for (instrument_id, source_session), value in sorted(
                    clear_adjustments.items(),
                    key=lambda item: (str(item[0][0]), item[0][1]),
                )
            ),
            "quarantined_adjustment_keys": _key_rows(
                quarantined_adjustment_keys
            ),
            "neutral_absence_inferred": False,
            "total_return_adjustment_available": False,
        }
    )
    return QuantResearchHistoricalSplitEvidenceV2(
        source_action_fingerprint=action_fingerprint,
        source_adjustment_fingerprint=adjustment_fingerprint,
        action_start=candidate.start_date,
        adjustment_start=source_sessions[0],
        active_action_keys=frozenset(active_action_keys),
        quarantined_action_keys=frozenset(quarantined_action_keys),
        unresolved_impact_keys=frozenset(unresolved_impact_keys),
        clear_adjustments=clear_adjustments,
        quarantined_adjustment_keys=frozenset(quarantined_adjustment_keys),
        conflict_event_count=len(conflict_event_keys),
        conflict_adjustment_count=len(conflict_adjustment_keys),
    )


def _project_adjustments(
    *,
    clear_events: dict[UUID, list[SplitAdjustmentEventCandidateV1]],
    required_ids: frozenset[UUID],
    source_sessions: tuple[date, ...],
    basis_session: date,
) -> dict[tuple[UUID, date], QuantResearchSplitAdjustmentV2]:
    output = {}
    for instrument_id in sorted(required_ids & clear_events.keys(), key=str):
        events = tuple(
            sorted(
                (
                    item
                    for item in clear_events[instrument_id]
                    if item.effective_date <= basis_session
                ),
                key=lambda item: item.effective_date,
            )
        )
        for source_session in source_sessions:
            applicable = tuple(
                item for item in events if source_session < item.effective_date
            )
            if not applicable:
                continue
            factors = calculate_composed_split_adjustment_multipliers(
                (action.split_ratio_from, action.split_ratio_to)
                for event in applicable
                for action in event.source_actions
            )
            output[(instrument_id, source_session)] = (
                QuantResearchSplitAdjustmentV2(
                    split_price_multiplier_to_basis=(
                        factors.price_multiplier_to_post_event_basis
                    ),
                    split_volume_multiplier_to_basis=(
                        factors.volume_multiplier_to_post_event_basis
                    ),
                )
            )
    return output


def _project_canonical_adjustments(
    *,
    canonical_actions: tuple[object, ...],
    required_ids: frozenset[UUID],
    source_sessions: tuple[date, ...],
    basis_session: date,
) -> dict[tuple[UUID, date], QuantResearchSplitAdjustmentV2]:
    active_by_id = defaultdict(list)
    for item in canonical_actions:
        if (
            item.instrument_id in required_ids
            and item.record_status is CorporateActionRecordStatus.ACTIVE
            and item.effective_date <= basis_session
        ):
            active_by_id[item.instrument_id].append(item)
    output = {}
    for instrument_id in sorted(active_by_id, key=str):
        actions = tuple(
            sorted(active_by_id[instrument_id], key=lambda item: item.effective_date)
        )
        for source_session in source_sessions:
            applicable = tuple(
                item for item in actions if source_session < item.effective_date
            )
            if not applicable:
                continue
            factors = calculate_composed_split_adjustment_multipliers(
                (item.split_ratio_from, item.split_ratio_to) for item in applicable
            )
            output[(instrument_id, source_session)] = (
                QuantResearchSplitAdjustmentV2(
                    split_price_multiplier_to_basis=(
                        factors.price_multiplier_to_post_event_basis
                    ),
                    split_volume_multiplier_to_basis=(
                        factors.volume_multiplier_to_post_event_basis
                    ),
                )
            )
    return output


def _economic_rows(rows: Iterable[object]) -> Counter[tuple[str, str, str]]:
    return Counter(
        (
            item.action_type.value,
            str(item.split_ratio_from),
            str(item.split_ratio_to),
        )
        for item in rows
    )


def _candidate_economic_rows(
    event: SplitAdjustmentEventCandidateV1,
) -> Counter[tuple[str, str, str]]:
    return Counter(
        (
            item.action_type.value,
            str(item.split_ratio_from),
            str(item.split_ratio_to),
        )
        for item in event.source_actions
    )


def _key_rows(values: Iterable[tuple[UUID, date]]) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "instrument_id": str(instrument_id),
            "date": value_date.isoformat(),
        }
        for instrument_id, value_date in sorted(
            set(values), key=lambda item: (str(item[0]), item[1])
        )
    )


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
