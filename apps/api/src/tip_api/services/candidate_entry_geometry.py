"""Pure additive Candidate entry-location and chase-risk shadow calculation."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from uuid import UUID

from tip_api.contracts.analytics.v1 import (
    CandidateDataQualityStatus,
    CandidateEntryGeometryBatchV1,
    CandidateEntryGeometryMetricsV1,
    CandidateEntryGeometryV1,
    CandidateEntryReviewPosture,
    CandidateExtensionRisk,
    CandidateOpportunityStage,
    CandidateTechnicalSetup,
    EntryGeometryAvailability,
    OpportunityCandidateBatchV1,
    OpportunityCandidateStateRecordV1,
)
from tip_api.parameters.market_regime.candidate_entry_v1_0_0 import (
    BREAKOUT_MAX_DISTANCE_ATR,
    BREAKOUT_MAX_VOLUME_RATIO,
    BREAKOUT_MIN_CLOSE_LOCATION,
    BREAKOUT_MIN_VOLUME_RATIO,
    BREAKOUT_WATCH_MAX_DISTANCE_ATR,
    BREAKOUT_WATCH_MAX_VOLUME_RATIO,
    ENTRY_GEOMETRY_ATR_WINDOW,
    ENTRY_GEOMETRY_BREAKOUT_SCORE,
    ENTRY_GEOMETRY_COMPONENT_FLOOR,
    ENTRY_GEOMETRY_PANEL_SESSION_COUNT,
    ENTRY_GEOMETRY_PARAMETER_FINGERPRINT,
    ENTRY_GEOMETRY_PRIOR_BREAKOUT_WINDOW,
    ENTRY_GEOMETRY_RAW_DECIMAL_SCALE,
    ENTRY_GEOMETRY_SCORE_FLOOR,
    ENTRY_GEOMETRY_SMA_LONG_WINDOW,
    ENTRY_GEOMETRY_SMA_SHORT_WINDOW,
    ENTRY_GEOMETRY_STRONG_SCORE,
    ENTRY_GEOMETRY_TRAILING_UP_CAP,
    EXTREME_MOVE_5_VOLATILITY_UNITS,
    EXTREME_POSITIVE_GAP_ATR,
    EXTREME_SMA20_EXTENSION_ATR,
    HIGH_MOVE_5_VOLATILITY_UNITS,
    HIGH_SMA10_EXTENSION_ATR,
    HIGH_SMA20_EXTENSION_ATR,
    HIGH_TRAILING_UP_SESSIONS,
    MODERATE_MOVE_5_VOLATILITY_UNITS,
    MODERATE_POSITIVE_GAP_ATR,
    MODERATE_SMA10_EXTENSION_ATR,
    MODERATE_SMA20_EXTENSION_ATR,
    MODERATE_TRAILING_UP_SESSIONS,
    PULLBACK_FROM_HIGH_MAX_ATR,
    PULLBACK_FROM_HIGH_MIN_ATR,
    PULLBACK_MAX_VOLUME_RATIO,
    PULLBACK_MIN_CLOSE_LOCATION,
    PULLBACK_SMA10_DISTANCE_ATR,
    VOLUME_CLIMAX_CLOSE_LOCATION,
    VOLUME_CLIMAX_RANGE_ATR,
    VOLUME_CLIMAX_RATIO,
)
from tip_api.services.market_regime_sources import MarketRegimeBar, MarketRegimeInputPanel


ZERO = Decimal("0")
ONE = Decimal("1")
RAW_QUANTUM = Decimal(1).scaleb(-ENTRY_GEOMETRY_RAW_DECIMAL_SCALE)


class CandidateEntryGeometryCalculationError(RuntimeError):
    """Raised when the entry-geometry calculation cannot preserve custody."""


def calculate_candidate_entry_geometry(
    *,
    panel: MarketRegimeInputPanel,
    candidate_batch: OpportunityCandidateBatchV1,
    state_records: tuple[OpportunityCandidateStateRecordV1, ...],
) -> CandidateEntryGeometryBatchV1:
    """Assess entry location without changing Candidate score, state, or rank."""

    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        return _calculate(panel=panel, candidate_batch=candidate_batch, state_records=state_records)


def _calculate(
    *,
    panel: MarketRegimeInputPanel,
    candidate_batch: OpportunityCandidateBatchV1,
    state_records: tuple[OpportunityCandidateStateRecordV1, ...],
) -> CandidateEntryGeometryBatchV1:
    if len(panel.sessions) != ENTRY_GEOMETRY_PANEL_SESSION_COUNT or panel.sessions[-1] != panel.as_of_session:
        raise CandidateEntryGeometryCalculationError("entry geometry requires the exact 26-session panel")
    if candidate_batch.as_of_session != panel.as_of_session:
        raise CandidateEntryGeometryCalculationError("entry geometry and Candidate batch sessions differ")
    if candidate_batch.universe_id not in {item.universe_id for item in panel.universes}:
        raise CandidateEntryGeometryCalculationError("entry geometry cites an unknown Universe")
    if candidate_batch.history_source_fingerprint != panel.history_source_fingerprint:
        raise CandidateEntryGeometryCalculationError("entry geometry source history differs from Candidate batch")

    state_by_id: dict[UUID, OpportunityCandidateStateRecordV1] = {}
    for state in state_records:
        if state.as_of_session != panel.as_of_session or state.universe_id != candidate_batch.universe_id:
            raise CandidateEntryGeometryCalculationError("entry geometry state rows must match current batch identity")
        if state.instrument_id in state_by_id:
            raise CandidateEntryGeometryCalculationError("duplicate entry-geometry state row")
        state_by_id[state.instrument_id] = state
    candidate_ids = {item.instrument_id for item in candidate_batch.candidates}
    missing_ids = set(candidate_batch.missing_member_ids)
    if set(state_by_id) != candidate_ids | missing_ids or candidate_ids & missing_ids:
        raise CandidateEntryGeometryCalculationError(
            "entry geometry requires state coverage for scored and explicitly missing members"
        )

    bars_by_instrument: dict[UUID, dict[object, MarketRegimeBar]] = defaultdict(dict)
    session_set = set(panel.sessions)
    for bar in panel.bars:
        if bar.session_date not in session_set:
            continue
        if bar.session_date in bars_by_instrument[bar.instrument_id]:
            raise CandidateEntryGeometryCalculationError("duplicate entry-geometry instrument/session bar")
        bars_by_instrument[bar.instrument_id][bar.session_date] = bar

    records = tuple(
        _record(
            panel=panel,
            candidate=candidate,
            state=state_by_id[candidate.instrument_id],
            bars=bars_by_instrument[candidate.instrument_id],
        )
        for candidate in candidate_batch.candidates
    )
    assessed = sum(item.metrics.availability is EntryGeometryAvailability.AVAILABLE for item in records)
    extension_counts = Counter(item.extension_risk.value for item in records)
    setup_counts = Counter(item.technical_setup.value for item in records)
    posture_counts = Counter(item.review_posture.value for item in records)
    provisional = CandidateEntryGeometryBatchV1(
        parameter_fingerprint=ENTRY_GEOMETRY_PARAMETER_FINGERPRINT,
        as_of_session=panel.as_of_session,
        universe_id=candidate_batch.universe_id,
        source_candidate_batch_fingerprint=candidate_batch.logical_fingerprint,
        source_history_fingerprint=panel.history_source_fingerprint,
        assessed_count=assessed,
        unavailable_count=len(records) - assessed,
        extension_counts=dict(sorted(extension_counts.items())),
        setup_counts=dict(sorted(setup_counts.items())),
        posture_counts=dict(sorted(posture_counts.items())),
        records=records,
        warnings=(
            "shadow_only_not_candidate_rank_input",
            "technical_review_posture_not_order_instruction",
            "reference_support_not_stop_price",
            "no_outcome_validation_with_26_session_history",
            "underlying_stock_result_not_option_return",
        ),
        logical_fingerprint="0" * 64,
    )
    return provisional.model_copy(
        update={"logical_fingerprint": _fingerprint(provisional.model_dump(mode="json", exclude={"logical_fingerprint"}))}
    )


def _record(*, panel, candidate, state, bars) -> CandidateEntryGeometryV1:
    component_scores = {item.component_id: item.score for item in candidate.components}
    relative_strength = component_scores["stock_relative_strength"]
    trend = component_scores["trend_quality"]
    metrics = _metrics(panel=panel, candidate=candidate, bars=bars)
    if metrics.availability is EntryGeometryAvailability.UNAVAILABLE:
        return _finalize(
            candidate=candidate,
            state=state,
            relative_strength=relative_strength,
            trend=trend,
            metrics=metrics,
            climax=None,
            extension=CandidateExtensionRisk.UNAVAILABLE,
            setup=CandidateTechnicalSetup.UNAVAILABLE,
            posture=CandidateEntryReviewPosture.NOT_ASSESSABLE,
            rejection="entry_geometry_required_facts_unavailable",
            why_now=(),
            supporting=(),
            counterevidence=metrics.missing_reason_codes,
            reviewable=("restore_complete_contiguous_entry_geometry_history",),
        )

    values = _metric_decimals(metrics)
    climax = (
        values["current_volume_ratio"] >= Decimal(VOLUME_CLIMAX_RATIO)
        and values["current_range_atr"] >= Decimal(VOLUME_CLIMAX_RANGE_ATR)
        and values["current_close_location"] >= Decimal(VOLUME_CLIMAX_CLOSE_LOCATION)
    )
    extension = _extension_risk(values=values, consecutive=metrics.consecutive_up_sessions or 0, climax=climax)
    base = None if candidate.base_score is None else Decimal(candidate.base_score)
    relative = None if relative_strength is None else Decimal(relative_strength)
    trend_score = None if trend is None else Decimal(trend)
    strong = (
        base is not None
        and relative is not None
        and trend_score is not None
        and base >= Decimal(ENTRY_GEOMETRY_STRONG_SCORE)
        and relative >= Decimal(ENTRY_GEOMETRY_COMPONENT_FLOOR)
        and trend_score >= Decimal(ENTRY_GEOMETRY_COMPONENT_FLOOR)
    )
    high_extension = extension in {CandidateExtensionRisk.HIGH, CandidateExtensionRisk.EXTREME}
    invalidated = state.final_stage is CandidateOpportunityStage.INVALIDATED
    blocked_quality = candidate.data_quality_status in {
        CandidateDataQualityStatus.QUARANTINED,
        CandidateDataQualityStatus.FAILED,
    }

    setup = CandidateTechnicalSetup.NO_VIABLE_SETUP
    posture = CandidateEntryReviewPosture.MONITOR_FOR_TRIGGER
    rejection: str | None = "no_viable_entry_geometry"
    why_now: list[str] = []
    supporting: list[str] = []
    counter: list[str] = []
    reviewable: list[str] = []
    if base is not None and base >= Decimal(ENTRY_GEOMETRY_STRONG_SCORE):
        why_now.append("candidate_research_priority_strong")
    if state.final_stage in {CandidateOpportunityStage.PREPARE, CandidateOpportunityStage.ENTER}:
        why_now.append("candidate_state_advanced")
    if relative is not None and relative >= Decimal(ENTRY_GEOMETRY_COMPONENT_FLOOR):
        supporting.append("relative_strength_component_supportive")
    if trend_score is not None and trend_score >= Decimal(ENTRY_GEOMETRY_COMPONENT_FLOOR):
        supporting.append("trend_component_supportive")
    if extension is CandidateExtensionRisk.MODERATE:
        counter.append("extension_risk_moderate")
    if climax:
        counter.append("volume_range_climax_risk_candidate")

    if invalidated:
        posture = CandidateEntryReviewPosture.DEPRIORITIZED
        rejection = "candidate_state_invalidated"
        reviewable.append("candidate_state_must_requalify")
    elif blocked_quality:
        posture = CandidateEntryReviewPosture.DEPRIORITIZED
        rejection = "candidate_source_quality_blocked"
        reviewable.append("source_or_corporate_action_review_must_clear")
    elif base is None or base < Decimal(ENTRY_GEOMETRY_SCORE_FLOOR):
        posture = CandidateEntryReviewPosture.DEPRIORITIZED
        rejection = "candidate_score_below_research_floor"
        reviewable.append("candidate_score_must_requalify")
    elif high_extension:
        setup = CandidateTechnicalSetup.STRONG_BUT_EXTENDED if strong else CandidateTechnicalSetup.NO_VIABLE_SETUP
        posture = CandidateEntryReviewPosture.WAIT_FOR_RESET
        rejection = "extension_risk_extreme" if extension is CandidateExtensionRisk.EXTREME else "extension_risk_high"
        why_now.append("strong_but_extended" if strong else "price_extended_without_complete_setup")
        counter.append(rejection)
        reviewable.append("extension_must_reset_below_high_threshold")
    elif strong and base >= Decimal(ENTRY_GEOMETRY_BREAKOUT_SCORE) and _breakout_confirmed(values):
        setup = CandidateTechnicalSetup.BREAKOUT_CONFIRMED
        posture = CandidateEntryReviewPosture.TECHNICAL_REVIEW_READY
        rejection = None
        why_now.append("bounded_breakout_confirmed")
        supporting.extend(("prior_close_high_exceeded", "breakout_volume_confirmation"))
        reviewable.append("complete_company_event_options_and_execution_review")
    elif strong and _pullback(values):
        setup = CandidateTechnicalSetup.PULLBACK
        posture = CandidateEntryReviewPosture.TECHNICAL_REVIEW_READY
        rejection = None
        why_now.append("orderly_pullback_structure_present")
        supporting.extend(("price_above_sma20", "price_near_sma10", "pullback_volume_not_expanded"))
        reviewable.append("complete_company_event_options_and_execution_review")
    elif strong and _breakout_watch(values):
        setup = CandidateTechnicalSetup.BREAKOUT_WATCH
        posture = CandidateEntryReviewPosture.MONITOR_FOR_TRIGGER
        rejection = "breakout_not_confirmed"
        why_now.append("near_prior_five_session_close_high")
        reviewable.append("close_above_prior_high_with_volume_confirmation")
    else:
        if not strong:
            counter.append("strong_candidate_structure_not_confirmed")
            reviewable.append("candidate_strength_and_trend_gates_must_align")
        else:
            counter.append("breakout_or_pullback_structure_absent")
            reviewable.append("bounded_breakout_or_orderly_pullback_required")

    return _finalize(
        candidate=candidate,
        state=state,
        relative_strength=relative_strength,
        trend=trend,
        metrics=metrics,
        climax=climax,
        extension=extension,
        setup=setup,
        posture=posture,
        rejection=rejection,
        why_now=tuple(why_now),
        supporting=tuple(supporting),
        counterevidence=tuple(counter),
        reviewable=tuple(reviewable),
    )


def _metrics(*, panel, candidate, bars) -> CandidateEntryGeometryMetricsV1:
    required_sessions = panel.sessions[-ENTRY_GEOMETRY_SMA_LONG_WINDOW:]
    missing = tuple(session for session in required_sessions if session not in bars)
    if missing:
        return _unavailable_metrics(("missing_contiguous_twenty_session_history",))
    ordered = [bars[session] for session in required_sessions]
    if any(bar.close <= ZERO or bar.high < bar.low or bar.volume < ZERO for bar in ordered):
        return _unavailable_metrics(("invalid_entry_geometry_bar",))
    current = ordered[-1]
    sma10 = _mean(tuple(item.close for item in ordered[-ENTRY_GEOMETRY_SMA_SHORT_WINDOW:]))
    sma20 = _mean(tuple(item.close for item in ordered))
    ranges: list[Decimal] = []
    atr_bars = ordered[-ENTRY_GEOMETRY_ATR_WINDOW:]
    prior_close = ordered[-ENTRY_GEOMETRY_ATR_WINDOW - 1].close
    for bar in atr_bars:
        ranges.append(max(bar.high - bar.low, abs(bar.high - prior_close), abs(bar.low - prior_close)))
        prior_close = bar.close
    atr = _mean(tuple(ranges))
    if atr <= ZERO:
        return _unavailable_metrics(("nonpositive_atr14",))
    if candidate.annualized_volatility_10 is None or candidate.current_volume_ratio is None:
        return _unavailable_metrics(("candidate_volatility_or_volume_fact_unavailable",))
    annualized_volatility = Decimal(candidate.annualized_volatility_10)
    if annualized_volatility <= ZERO:
        return _unavailable_metrics(("nonpositive_realized_volatility",))
    daily_range = current.high - current.low
    if daily_range <= ZERO:
        return _unavailable_metrics(("nonpositive_current_session_range",))
    return3 = current.close / ordered[-4].close - ONE
    return5 = current.close / ordered[-6].close - ONE
    expected_move5 = annualized_volatility / Decimal(252).sqrt() * Decimal(5).sqrt()
    prior5 = ordered[-ENTRY_GEOMETRY_PRIOR_BREAKOUT_WINDOW - 1 : -1]
    prior_high = max(item.close for item in prior5)
    prior_low = min(item.close for item in prior5)
    consecutive = 0
    for index in range(len(ordered) - 1, max(0, len(ordered) - 1 - ENTRY_GEOMETRY_TRAILING_UP_CAP), -1):
        if ordered[index].close <= ordered[index - 1].close:
            break
        consecutive += 1
    support_candidates = (
        ("sma20", sma20, 0),
        ("prior_five_session_close_low", prior_low, 1),
    )
    below = [item for item in support_candidates if item[1] <= current.close]
    support = max(below, key=lambda item: (item[1], -item[2])) if below else None
    return CandidateEntryGeometryMetricsV1(
        availability=EntryGeometryAvailability.AVAILABLE,
        close=_raw(current.close),
        sma_10=_raw(sma10),
        sma_20=_raw(sma20),
        atr_14=_raw(atr),
        return_3=_raw(return3),
        return_5=_raw(return5),
        close_to_sma_10_atr=_raw((current.close - sma10) / atr),
        close_to_sma_20_atr=_raw((current.close - sma20) / atr),
        move_5_volatility_units=_raw(return5 / expected_move5),
        consecutive_up_sessions=consecutive,
        current_gap_atr=_raw((current.open - ordered[-2].close) / atr),
        current_range_atr=_raw(daily_range / atr),
        current_close_location=_raw((current.close - current.low) / daily_range),
        current_volume_ratio=_raw(Decimal(candidate.current_volume_ratio)),
        prior_five_session_close_high=_raw(prior_high),
        prior_five_session_close_low=_raw(prior_low),
        breakout_distance_atr=_raw((current.close - prior_high) / atr),
        pullback_from_prior_high_atr=_raw((current.close - prior_high) / atr),
        reference_support_kind=None if support is None else support[0],
        reference_support_value=None if support is None else _raw(support[1]),
        reference_support_distance_pct=(
            None if support is None else _raw((current.close - support[1]) / current.close)
        ),
        missing_reason_codes=(),
    )


def _unavailable_metrics(reasons: tuple[str, ...]) -> CandidateEntryGeometryMetricsV1:
    return CandidateEntryGeometryMetricsV1(
        availability=EntryGeometryAvailability.UNAVAILABLE,
        close=None,
        sma_10=None,
        sma_20=None,
        atr_14=None,
        return_3=None,
        return_5=None,
        close_to_sma_10_atr=None,
        close_to_sma_20_atr=None,
        move_5_volatility_units=None,
        consecutive_up_sessions=None,
        current_gap_atr=None,
        current_range_atr=None,
        current_close_location=None,
        current_volume_ratio=None,
        prior_five_session_close_high=None,
        prior_five_session_close_low=None,
        breakout_distance_atr=None,
        pullback_from_prior_high_atr=None,
        reference_support_kind=None,
        reference_support_value=None,
        reference_support_distance_pct=None,
        missing_reason_codes=reasons,
    )


def _extension_risk(*, values, consecutive, climax):
    if (
        values["close_to_sma_20_atr"] >= Decimal(EXTREME_SMA20_EXTENSION_ATR)
        or values["move_5_volatility_units"] >= Decimal(EXTREME_MOVE_5_VOLATILITY_UNITS)
        or (
            values["current_gap_atr"] >= Decimal(EXTREME_POSITIVE_GAP_ATR)
            and values["close_to_sma_20_atr"] >= Decimal(HIGH_SMA20_EXTENSION_ATR)
        )
    ):
        return CandidateExtensionRisk.EXTREME
    if (
        values["close_to_sma_20_atr"] >= Decimal(HIGH_SMA20_EXTENSION_ATR)
        or values["move_5_volatility_units"] >= Decimal(HIGH_MOVE_5_VOLATILITY_UNITS)
        or (consecutive >= HIGH_TRAILING_UP_SESSIONS and values["close_to_sma_10_atr"] >= Decimal(HIGH_SMA10_EXTENSION_ATR))
        or climax
    ):
        return CandidateExtensionRisk.HIGH
    if (
        values["close_to_sma_20_atr"] >= Decimal(MODERATE_SMA20_EXTENSION_ATR)
        or values["move_5_volatility_units"] >= Decimal(MODERATE_MOVE_5_VOLATILITY_UNITS)
        or (
            consecutive >= MODERATE_TRAILING_UP_SESSIONS
            and values["close_to_sma_10_atr"] >= Decimal(MODERATE_SMA10_EXTENSION_ATR)
        )
        or values["current_gap_atr"] >= Decimal(MODERATE_POSITIVE_GAP_ATR)
    ):
        return CandidateExtensionRisk.MODERATE
    return CandidateExtensionRisk.LOW


def _breakout_confirmed(values) -> bool:
    return (
        ZERO < values["breakout_distance_atr"] <= Decimal(BREAKOUT_MAX_DISTANCE_ATR)
        and Decimal(BREAKOUT_MIN_VOLUME_RATIO)
        <= values["current_volume_ratio"]
        <= Decimal(BREAKOUT_MAX_VOLUME_RATIO)
        and values["current_close_location"] >= Decimal(BREAKOUT_MIN_CLOSE_LOCATION)
    )


def _breakout_watch(values) -> bool:
    return (
        -Decimal(BREAKOUT_WATCH_MAX_DISTANCE_ATR) <= values["breakout_distance_atr"] <= ZERO
        and values["current_volume_ratio"] <= Decimal(BREAKOUT_WATCH_MAX_VOLUME_RATIO)
    )


def _pullback(values) -> bool:
    pullback_depth = -values["pullback_from_prior_high_atr"]
    return (
        values["close"] >= values["sma_20"]
        and abs(values["close_to_sma_10_atr"]) <= Decimal(PULLBACK_SMA10_DISTANCE_ATR)
        and Decimal(PULLBACK_FROM_HIGH_MIN_ATR) <= pullback_depth <= Decimal(PULLBACK_FROM_HIGH_MAX_ATR)
        and values["current_volume_ratio"] <= Decimal(PULLBACK_MAX_VOLUME_RATIO)
        and values["current_close_location"] >= Decimal(PULLBACK_MIN_CLOSE_LOCATION)
    )


def _finalize(*, candidate, state, relative_strength, trend, metrics, climax, extension, setup, posture,
              rejection, why_now, supporting, counterevidence, reviewable):
    invalidation = [
        "candidate_state_invalidated",
        "source_or_corporate_action_quarantine",
        "trend_component_below_50",
    ]
    if metrics.reference_support_value is not None:
        invalidation.append("close_below_reference_support_requires_reunderwrite")
    provisional = CandidateEntryGeometryV1(
        parameter_fingerprint=ENTRY_GEOMETRY_PARAMETER_FINGERPRINT,
        as_of_session=candidate.as_of_session,
        universe_id=state.universe_id,
        instrument_id=candidate.instrument_id,
        ticker=candidate.ticker,
        security_type=candidate.security_type,
        candidate_stage=state.final_stage,
        candidate_base_score=candidate.base_score,
        relative_strength_component_score=relative_strength,
        trend_component_score=trend,
        source_candidate_fingerprint=candidate.logical_fingerprint,
        source_state_fingerprint=state.logical_fingerprint,
        metrics=metrics,
        volume_climax_risk_candidate=climax,
        extension_risk=extension,
        technical_setup=setup,
        review_posture=posture,
        first_rejection_code=rejection,
        why_now_codes=tuple(dict.fromkeys(why_now)),
        supporting_fact_codes=tuple(dict.fromkeys(supporting)),
        counterevidence_codes=tuple(dict.fromkeys(counterevidence)),
        what_would_make_reviewable_codes=tuple(dict.fromkeys(reviewable)),
        technical_invalidation_codes=tuple(invalidation),
        required_manual_check_codes=(
            "company_event_and_earnings_timing",
            "corporate_action_status",
            "news_and_thesis_evidence",
            "option_liquidity_iv_greeks_and_spread",
            "position_risk_and_execution_quality",
        ),
        warnings=(
            "research_priority_not_recommendation",
            "technical_review_posture_not_order_instruction",
            "reference_support_not_stop_price",
            "price_volume_not_fund_flow",
            "underlying_stock_result_not_option_return",
        ),
        logical_fingerprint="0" * 64,
    )
    return provisional.model_copy(
        update={"logical_fingerprint": _fingerprint(provisional.model_dump(mode="json", exclude={"logical_fingerprint"}))}
    )


def _metric_decimals(metrics: CandidateEntryGeometryMetricsV1) -> dict[str, Decimal]:
    return {
        "close": Decimal(metrics.close),
        "sma_20": Decimal(metrics.sma_20),
        "close_to_sma_10_atr": Decimal(metrics.close_to_sma_10_atr),
        "close_to_sma_20_atr": Decimal(metrics.close_to_sma_20_atr),
        "move_5_volatility_units": Decimal(metrics.move_5_volatility_units),
        "current_gap_atr": Decimal(metrics.current_gap_atr),
        "current_range_atr": Decimal(metrics.current_range_atr),
        "current_close_location": Decimal(metrics.current_close_location),
        "current_volume_ratio": Decimal(metrics.current_volume_ratio),
        "breakout_distance_atr": Decimal(metrics.breakout_distance_atr),
        "pullback_from_prior_high_atr": Decimal(metrics.pullback_from_prior_high_atr),
    }


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    return sum(values, ZERO) / Decimal(len(values))


def _raw(value: Decimal) -> str:
    return format(value.quantize(RAW_QUANTUM), "f")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
