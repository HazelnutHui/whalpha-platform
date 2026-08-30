"""Independent raw-source checks for Candidate Visual Context 1.0."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from decimal import Decimal

from tip_api.contracts.analytics.v1 import (
    CandidateEntryGeometryBatchV1,
    CandidateStateAvailability,
    CandidateVisualContextBatchV1,
    OpportunityCandidateBatchV1,
    OpportunityCandidateStateRecordV1,
    VISUAL_CONTEXT_CALCULATION_VERSION,
    VISUAL_CONTEXT_CONTRACT_VERSION,
    VISUAL_CONTEXT_PATH_SESSION_COUNT,
    VisualContextAvailability,
)
from tip_api.services.market_regime_sources import MarketRegimeInputPanel


@dataclass(frozen=True, slots=True)
class CandidateVisualContextOracleComparisonV1:
    as_of_session: str
    universe_id: str
    record_count: int
    mismatch_count: int
    mismatches: tuple[str, ...]
    input_permutation_match: bool
    production_calculator_imported: bool
    oracle_fingerprint: str


def compare_with_independent_candidate_visual_context_oracle(
    *,
    panel: MarketRegimeInputPanel,
    candidate_batch: OpportunityCandidateBatchV1,
    entry_geometry_batch: CandidateEntryGeometryBatchV1,
    state_history: tuple[OpportunityCandidateStateRecordV1, ...],
    actual: CandidateVisualContextBatchV1,
) -> CandidateVisualContextOracleComparisonV1:
    """Validate every path/age output directly from raw inputs."""

    mismatches: list[str] = []
    if actual.contract_version != VISUAL_CONTEXT_CONTRACT_VERSION:
        mismatches.append("contract_version_mismatch")
    if actual.calculation_version != VISUAL_CONTEXT_CALCULATION_VERSION:
        mismatches.append("calculation_version_mismatch")
    if actual.as_of_session != panel.as_of_session or actual.universe_id != candidate_batch.universe_id:
        mismatches.append("batch_identity_mismatch")
    expected_state_history_fingerprint = _fingerprint(
        {
            "universe_id": candidate_batch.universe_id,
            "records": [
                {
                    "as_of_session": row.as_of_session.isoformat(),
                    "instrument_id": str(row.instrument_id),
                    "logical_fingerprint": row.logical_fingerprint,
                }
                for row in sorted(
                    state_history,
                    key=lambda item: (item.as_of_session, str(item.instrument_id)),
                )
            ],
        }
    )
    if (
        actual.source_candidate_batch_fingerprint != candidate_batch.logical_fingerprint
        or actual.source_entry_geometry_batch_fingerprint
        != entry_geometry_batch.logical_fingerprint
        or actual.source_history_fingerprint != panel.history_source_fingerprint
        or actual.source_state_history_fingerprint != expected_state_history_fingerprint
    ):
        mismatches.append("batch_source_lineage_mismatch")
    entries = {row.instrument_id: row for row in entry_geometry_batch.records}
    states = {(row.instrument_id, row.as_of_session): row for row in state_history}
    sessions = tuple(sorted({row.as_of_session for row in state_history}))
    path_sessions = set(panel.sessions[-VISUAL_CONTEXT_PATH_SESSION_COUNT:])
    candidate_ids = {row.instrument_id for row in candidate_batch.candidates}
    bars = {
        (row.instrument_id, row.session_date): row
        for row in panel.bars
        if row.session_date in path_sessions and row.instrument_id in candidate_ids
    }
    actual_by_id = {row.instrument_id: row for row in actual.records}
    candidate_by_id = {row.instrument_id: row for row in candidate_batch.candidates}
    if set(actual_by_id) != set(candidate_by_id):
        mismatches.append("record_coverage_mismatch")
    for instrument_id in sorted(set(actual_by_id) & set(candidate_by_id), key=str):
        row = actual_by_id[instrument_id]
        entry = entries.get(instrument_id)
        current = states.get((instrument_id, panel.as_of_session))
        label = str(instrument_id)
        if entry is None or current is None:
            mismatches.append(f"{label}:source_row_missing")
            continue
        candidate = candidate_by_id[instrument_id]
        if (
            row.source_candidate_fingerprint != candidate.logical_fingerprint
            or row.source_entry_geometry_fingerprint != entry.logical_fingerprint
            or entry.source_state_fingerprint != current.logical_fingerprint
        ):
            mismatches.append(f"{label}:record_source_lineage_mismatch")
        expected_sessions = panel.sessions[-VISUAL_CONTEXT_PATH_SESSION_COUNT:]
        expected_bars = [bars.get((instrument_id, session)) for session in expected_sessions]
        if all(item is not None and item.close > 0 for item in expected_bars) and entry.metrics.availability.value == "available":
            expected_points = tuple(
                (session.isoformat(), _decimal(item.close))
                for session, item in zip(expected_sessions, expected_bars, strict=True)
            )
            actual_points = tuple(
                (point.session_date.isoformat(), point.close) for point in row.price_path
            )
            if row.price_path_availability is not VisualContextAvailability.AVAILABLE or actual_points != expected_points:
                mismatches.append(f"{label}:price_path_mismatch")
            metrics = entry.metrics
            expected_levels = (
                metrics.close,
                metrics.sma_10,
                metrics.sma_20,
                metrics.prior_five_session_close_high,
                metrics.prior_five_session_close_low,
                metrics.reference_support_kind,
                metrics.reference_support_value,
            )
            levels = row.reference_levels
            actual_levels = None if levels is None else (
                levels.current_close,
                levels.sma_10,
                levels.sma_20,
                levels.prior_five_session_close_high,
                levels.prior_five_session_close_low,
                levels.reference_support_kind,
                levels.reference_support_value,
            )
            if actual_levels != expected_levels:
                mismatches.append(f"{label}:reference_level_mismatch")
        elif row.price_path_availability is not VisualContextAvailability.UNAVAILABLE or row.price_path:
            mismatches.append(f"{label}:unavailable_path_mismatch")

        expected_age = _age(instrument_id=instrument_id, sessions=sessions, states=states, current=current)
        if expected_age is None:
            if row.state_age_availability is not VisualContextAvailability.UNAVAILABLE or row.observed_state_age is not None:
                mismatches.append(f"{label}:unavailable_state_age_mismatch")
        else:
            age = row.observed_state_age
            actual_age = None if age is None else (
                age.final_stage.value,
                age.first_observed_session.isoformat(),
                age.observed_age_sessions,
                age.left_censored,
                age.current_state_fingerprint,
            )
            if row.state_age_availability is not VisualContextAvailability.AVAILABLE or actual_age != expected_age:
                mismatches.append(f"{label}:observed_state_age_mismatch")

    permutation_match = _source_projection(
        panel=panel,
        candidate_batch=candidate_batch,
        entry_geometry_batch=entry_geometry_batch,
        state_history=state_history,
    ) == _source_projection(
        panel=replace(panel, bars=tuple(reversed(panel.bars))),
        candidate_batch=candidate_batch.model_copy(
            update={"candidates": tuple(reversed(candidate_batch.candidates))}
        ),
        entry_geometry_batch=entry_geometry_batch.model_copy(
            update={"records": tuple(reversed(entry_geometry_batch.records))}
        ),
        state_history=tuple(reversed(state_history)),
    )
    base = {
        "as_of_session": panel.as_of_session.isoformat(),
        "universe_id": candidate_batch.universe_id,
        "record_count": len(actual.records),
        "mismatches": sorted(mismatches),
        "input_permutation_match": permutation_match,
        "production_calculator_imported": False,
    }
    return CandidateVisualContextOracleComparisonV1(
        as_of_session=base["as_of_session"],
        universe_id=base["universe_id"],
        record_count=base["record_count"],
        mismatch_count=len(mismatches),
        mismatches=tuple(sorted(mismatches)),
        input_permutation_match=permutation_match,
        production_calculator_imported=False,
        oracle_fingerprint=_fingerprint(base),
    )


def _age(*, instrument_id, sessions, states, current):
    if (
        current.state_availability is not CandidateStateAvailability.AVAILABLE
        or current.stale_state
        or current.final_stage is None
    ):
        return None
    count = 0
    first = current.as_of_session
    left_censored = True
    for session in reversed(sessions):
        row = states.get((instrument_id, session))
        if row is None or row.state_availability is not CandidateStateAvailability.AVAILABLE or row.stale_state or row.final_stage is not current.final_stage:
            left_censored = False
            break
        count += 1
        first = session
    return (
        current.final_stage.value,
        first.isoformat(),
        count,
        left_censored,
        current.logical_fingerprint,
    )


def _source_projection(*, panel, candidate_batch, entry_geometry_batch, state_history):
    candidate_ids = {row.instrument_id for row in candidate_batch.candidates}
    path_sessions = set(panel.sessions[-VISUAL_CONTEXT_PATH_SESSION_COUNT:])
    return _fingerprint(
        {
            "bars": sorted(
                (str(row.instrument_id), row.session_date.isoformat(), str(row.close))
                for row in panel.bars
                if row.instrument_id in candidate_ids and row.session_date in path_sessions
            ),
            "candidates": sorted(
                (str(row.instrument_id), row.logical_fingerprint)
                for row in candidate_batch.candidates
            ),
            "entries": sorted(
                (str(row.instrument_id), row.logical_fingerprint)
                for row in entry_geometry_batch.records
            ),
            "states": sorted(
                (str(row.instrument_id), row.as_of_session.isoformat(), row.logical_fingerprint)
                for row in state_history
            ),
        }
    )


def _decimal(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.0000000001")), "f")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
