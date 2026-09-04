"""Pure source-bound Candidate price-path and observed-state context."""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from uuid import UUID

from tip_api.contracts.analytics.v1 import (
    CandidateEntryGeometryBatchV1,
    CandidateEntryGeometryV1,
    CandidateObservedStateAgeV1,
    CandidatePricePathPointV1,
    CandidateStateAvailability,
    CandidateVisualContextBatchV1,
    CandidateVisualContextV1,
    CandidateVisualReferenceLevelsV1,
    EntryGeometryAvailability,
    OpportunityCandidateBatchV1,
    OpportunityCandidateStateRecordV1,
    VISUAL_CONTEXT_PATH_SESSION_COUNT,
    VisualContextAvailability,
    visual_context_fingerprint,
)
from tip_api.services.market_regime_sources import MarketRegimeBar, MarketRegimeInputPanel


RAW_QUANTUM = Decimal("0.0000000001")


class CandidateVisualContextCalculationError(RuntimeError):
    """Raised when Candidate visual context cannot preserve exact source custody."""


def calculate_candidate_visual_context(
    *,
    panel: MarketRegimeInputPanel,
    candidate_batch: OpportunityCandidateBatchV1,
    entry_geometry_batch: CandidateEntryGeometryBatchV1,
    state_history: tuple[OpportunityCandidateStateRecordV1, ...],
) -> CandidateVisualContextBatchV1:
    """Describe real price history and observed state age without changing results."""

    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        return _calculate(
            panel=panel,
            candidate_batch=candidate_batch,
            entry_geometry_batch=entry_geometry_batch,
            state_history=state_history,
        )


def _calculate(*, panel, candidate_batch, entry_geometry_batch, state_history):
    if len(panel.sessions) != 26 or panel.sessions[-1] != panel.as_of_session:
        raise CandidateVisualContextCalculationError(
            "Candidate visual context requires the exact 26-session panel"
        )
    if (
        candidate_batch.as_of_session != panel.as_of_session
        or entry_geometry_batch.as_of_session != panel.as_of_session
        or candidate_batch.universe_id != entry_geometry_batch.universe_id
    ):
        raise CandidateVisualContextCalculationError(
            "Candidate visual-context source identities differ"
        )
    if (
        candidate_batch.history_source_fingerprint != panel.history_source_fingerprint
        or entry_geometry_batch.source_candidate_batch_fingerprint
        != candidate_batch.logical_fingerprint
        or entry_geometry_batch.source_history_fingerprint
        != panel.history_source_fingerprint
    ):
        raise CandidateVisualContextCalculationError(
            "Candidate visual-context source lineage differs"
        )
    universe = panel.select_universe(candidate_batch.universe_id)
    if (
        candidate_batch.membership_fingerprint != universe.membership_fingerprint
        or candidate_batch.universe_member_count != len(universe.member_ids)
    ):
        raise CandidateVisualContextCalculationError(
            "Candidate visual-context Universe custody differs"
        )

    candidates = {row.instrument_id: row for row in candidate_batch.candidates}
    entries = {row.instrument_id: row for row in entry_geometry_batch.records}
    if (
        len(candidates) != len(candidate_batch.candidates)
        or len(entries) != len(entry_geometry_batch.records)
        or set(candidates) != set(entries)
    ):
        raise CandidateVisualContextCalculationError(
            "Candidate visual context requires exact Candidate and Entry coverage"
        )

    if not state_history or any(row.universe_id != candidate_batch.universe_id for row in state_history):
        raise CandidateVisualContextCalculationError(
            "Candidate visual-context state history must contain exactly one Universe"
        )
    state_by_key: dict[tuple[UUID, object], OpportunityCandidateStateRecordV1] = {}
    for row in state_history:
        key = (row.instrument_id, row.as_of_session)
        if key in state_by_key:
            raise CandidateVisualContextCalculationError(
                "duplicate Candidate visual-context state-history row"
            )
        state_by_key[key] = row
    history_sessions = tuple(sorted({row.as_of_session for row in state_history}))
    if not history_sessions or history_sessions[-1] != panel.as_of_session:
        raise CandidateVisualContextCalculationError(
            "Candidate visual-context state history lacks the current session"
        )
    current_states = {
        row.instrument_id: row
        for row in state_history
        if row.as_of_session == panel.as_of_session
    }
    expected_current_ids = set(candidates) | set(candidate_batch.missing_member_ids)
    if set(current_states) != expected_current_ids:
        raise CandidateVisualContextCalculationError(
            "Candidate visual-context current state coverage differs"
        )

    bars_by_id: dict[UUID, dict[object, MarketRegimeBar]] = defaultdict(dict)
    required_sessions = panel.sessions[-VISUAL_CONTEXT_PATH_SESSION_COUNT:]
    required_set = set(required_sessions)
    for bar in panel.bars:
        if bar.session_date not in required_set:
            continue
        if bar.session_date in bars_by_id[bar.instrument_id]:
            raise CandidateVisualContextCalculationError(
                "duplicate Candidate visual-context instrument/session bar"
            )
        bars_by_id[bar.instrument_id][bar.session_date] = bar

    state_history_fingerprint = visual_context_fingerprint(
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
    records = []
    for instrument_id in sorted(candidates, key=str):
        candidate = candidates[instrument_id]
        entry = entries[instrument_id]
        current_state = current_states[instrument_id]
        if (
            entry.source_candidate_fingerprint != candidate.logical_fingerprint
            or entry.source_state_fingerprint != current_state.logical_fingerprint
            or current_state.source_candidate_fingerprint
            != (
                candidate.logical_fingerprint
                if current_state.state_availability
                is CandidateStateAvailability.AVAILABLE
                else None
            )
            or entry.ticker != candidate.ticker
            or current_state.ticker != candidate.ticker
            or entry.security_type != candidate.security_type
            or current_state.security_type != candidate.security_type
        ):
            raise CandidateVisualContextCalculationError(
                "Candidate visual-context current source rows differ"
            )
        path, levels, path_reasons = _price_path(
            sessions=required_sessions,
            bars=bars_by_id[instrument_id],
            entry=entry,
        )
        state_age, state_reasons = _observed_state_age(
            instrument_id=instrument_id,
            sessions=history_sessions,
            states=state_by_key,
            current=current_state,
        )
        base = {
            "schema_version": "1.0",
            "contract_version": "candidate-visual-context/1.0",
            "calculation_version": "candidate-visual-context-v1.0.0",
            "as_of_session": panel.as_of_session.isoformat(),
            "universe_id": candidate_batch.universe_id,
            "instrument_id": str(instrument_id),
            "ticker": candidate.ticker,
            "security_type": candidate.security_type,
            "source_candidate_fingerprint": candidate.logical_fingerprint,
            "source_entry_geometry_fingerprint": entry.logical_fingerprint,
            "price_path_availability": (
                VisualContextAvailability.AVAILABLE.value
                if path
                else VisualContextAvailability.UNAVAILABLE.value
            ),
            "price_path": [point.model_dump(mode="json") for point in path],
            "reference_levels": None if levels is None else levels.model_dump(mode="json"),
            "price_path_missing_reason_codes": path_reasons,
            "state_age_availability": (
                VisualContextAvailability.AVAILABLE.value
                if state_age is not None
                else VisualContextAvailability.UNAVAILABLE.value
            ),
            "observed_state_age": (
                None if state_age is None else state_age.model_dump(mode="json")
            ),
            "state_age_missing_reason_codes": state_reasons,
            "warnings": (
                "descriptive_visual_context_not_strategy_score_or_status",
                "reference_support_not_stop_price",
                "observed_state_age_not_success_probability",
                "left_censored_age_is_minimum_not_true_start",
                "underlying_stock_path_not_option_return",
            ),
        }
        base["logical_fingerprint"] = visual_context_fingerprint(base)
        records.append(CandidateVisualContextV1.model_validate(base))

    batch_base = {
        "schema_version": "1.0",
        "contract_version": "candidate-visual-context/1.0",
        "calculation_version": "candidate-visual-context-v1.0.0",
        "as_of_session": panel.as_of_session.isoformat(),
        "universe_id": candidate_batch.universe_id,
        "source_candidate_batch_fingerprint": candidate_batch.logical_fingerprint,
        "source_entry_geometry_batch_fingerprint": entry_geometry_batch.logical_fingerprint,
        "source_history_fingerprint": panel.history_source_fingerprint,
        "source_state_history_fingerprint": state_history_fingerprint,
        "record_count": len(records),
        "price_path_availability_counts": dict(
            Counter(row.price_path_availability.value for row in records)
        ),
        "state_age_availability_counts": dict(
            Counter(row.state_age_availability.value for row in records)
        ),
        "records": [row.model_dump(mode="json") for row in records],
        "strategy_score_input": False,
        "outcome_or_performance_claim": False,
        "warnings": (
            "shadow_only_not_strategy_rank_input",
            "real_close_path_not_forward_return",
            "observed_state_age_may_be_left_censored",
            "no_browser_inference_or_threshold_fitting",
            "underlying_stock_path_not_option_return",
        ),
    }
    batch_base["logical_fingerprint"] = visual_context_fingerprint(batch_base)
    return CandidateVisualContextBatchV1.model_validate(batch_base)


def _price_path(*, sessions, bars, entry):
    if entry.metrics.availability is EntryGeometryAvailability.UNAVAILABLE:
        return (), None, ("entry_geometry_unavailable",)
    if any(session not in bars for session in sessions):
        return (), None, ("missing_contiguous_twenty_session_close_history",)
    ordered = [bars[session] for session in sessions]
    if any(row.close <= 0 for row in ordered):
        return (), None, ("invalid_price_path_close",)
    path = tuple(
        CandidatePricePathPointV1(
            session_date=row.session_date,
            close=_decimal(row.close),
        )
        for row in ordered
    )
    metrics = entry.metrics
    if path[-1].close != metrics.close:
        raise CandidateVisualContextCalculationError(
            "Candidate visual path current close differs from Entry Geometry"
        )
    levels = CandidateVisualReferenceLevelsV1(
        current_close=metrics.close,
        sma_10=metrics.sma_10,
        sma_20=metrics.sma_20,
        prior_five_session_close_high=metrics.prior_five_session_close_high,
        prior_five_session_close_low=metrics.prior_five_session_close_low,
        reference_support_kind=metrics.reference_support_kind,
        reference_support_value=metrics.reference_support_value,
    )
    return path, levels, ()


def _observed_state_age(*, instrument_id, sessions, states, current):
    if (
        current.state_availability is not CandidateStateAvailability.AVAILABLE
        or current.stale_state
        or current.final_stage is None
    ):
        return None, ("current_candidate_state_unavailable_or_stale",)
    count = 0
    first = current.as_of_session
    reached_start = True
    for session in reversed(sessions):
        row = states.get((instrument_id, session))
        if row is None:
            reached_start = False
            break
        if (
            row.state_availability is not CandidateStateAvailability.AVAILABLE
            or row.stale_state
            or row.final_stage is not current.final_stage
        ):
            reached_start = False
            break
        count += 1
        first = session
    if count < 1:
        return None, ("current_candidate_state_history_unusable",)
    return CandidateObservedStateAgeV1(
        final_stage=current.final_stage,
        first_observed_session=first,
        observed_age_sessions=count,
        left_censored=reached_start,
        current_state_fingerprint=current.logical_fingerprint,
    ), ()


def _decimal(value: Decimal) -> str:
    return format(value.quantize(RAW_QUANTUM), "f")
