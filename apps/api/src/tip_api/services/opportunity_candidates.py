"""Pure, deterministic Phase 5A candidate scoring and risk-mode ranking."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import (
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    localcontext,
)
from uuid import UUID

from tip_api.contracts.analytics.v1 import (
    CandidateComponentV1,
    CandidateConfidenceV1,
    CandidateDataQualityStatus,
    CandidateMetricAvailability,
    CandidateMetricV1,
    CandidatePriorStateSourceV1,
    CandidateRiskAssessmentV1,
    CandidateRiskMode,
    CandidateRiskModeResultV1,
    OpportunityCandidateBatchV1,
    OpportunityCandidateScoreV1,
    RegimeState,
)
from tip_api.parameters.market_regime.candidate_v1_1_1 import (
    ANNUALIZATION_SESSION_COUNT,
    BASE_LIQUIDITY_FLOOR,
    BASE_PRICE_FLOOR,
    BASE_WATCH_CONFIDENCE,
    BASE_WATCH_SCORE,
    CANDIDATE_NON_BLOCKING_QUALITY_FLAGS,
    CANDIDATE_PARAMETER_FINGERPRINT,
    CANDIDATE_PANEL_SESSION_COUNT,
    CANDIDATE_REQUIRED_HISTORY_SESSION_COUNT,
    CALCULATION_DECIMAL_PRECISION,
    COMPONENT_PARAMETERS,
    CONFIDENCE_HISTORY_WEIGHT,
    CONFIDENCE_RELATIONSHIP_WEIGHT,
    CONFIDENCE_SOURCE_WEIGHT,
    CONFIDENCE_STATE_WEIGHT,
    CORRELATION_MINIMUM,
    CORRELATION_MINIMUM_OBSERVATIONS,
    CROSS_SECTION_ROBUST_Z_SCALE,
    CROSS_SECTION_SCORE_CENTER,
    CROSS_SECTION_SCORE_SCALE,
    CROSS_SECTION_WINSOR_HIGH,
    CROSS_SECTION_WINSOR_LOW,
    DOLLAR_VOLUME_MINIMUM_OBSERVATIONS,
    DOLLAR_VOLUME_WINDOW,
    DOWNSIDE_TAIL_MINIMUM_OBSERVATIONS,
    DOWNSIDE_TAIL_NORMALIZER_HIGH,
    DOWNSIDE_TAIL_NORMALIZER_LOW,
    DOWNSIDE_TAIL_RETURN_THRESHOLD,
    DOWNSIDE_TAIL_SESSION_COUNT,
    DRIVER_CORRELATION_NORMALIZER_HIGH,
    DRIVER_CORRELATION_WINDOW,
    ETF_ALIGNMENT_CAP,
    EXTREME_CLOSE_RETURN_REVIEW_THRESHOLD,
    EXTREME_OPEN_GAP_REVIEW_THRESHOLD,
    LIQUIDITY_NORMALIZER_HIGH,
    LIQUIDITY_NORMALIZER_LOW,
    MAXIMUM_DRAWDOWN_CLOSE_COUNT,
    MAXIMUM_DRAWDOWN_NORMALIZER_HIGH,
    MAXIMUM_DRAWDOWN_NORMALIZER_LOW,
    MINIMUM_CONFIGURED_WEIGHT_AVAILABLE,
    OPEN_GAP_MINIMUM_OBSERVATIONS,
    OPEN_GAP_NORMALIZER_HIGH,
    OPEN_GAP_NORMALIZER_LOW,
    OPEN_GAP_SESSION_COUNT,
    PRICE_NORMALIZER_HIGH,
    PRICE_NORMALIZER_LOW,
    PRIOR_VOLUME_MINIMUM_OBSERVATIONS,
    PRIOR_VOLUME_WINDOW,
    RAW_DECIMAL_SCALE,
    REALIZED_VOLATILITY_NORMALIZER_HIGH,
    REALIZED_VOLATILITY_NORMALIZER_LOW,
    REALIZED_VOLATILITY_RETURN_COUNT,
    RELATIONSHIP_SUPPORT_LEVELS,
    RISK_MODE_PARAMETERS,
    SCORE_DECIMAL_SCALE,
    SMA_LONG_WINDOW,
    SMA_RATIO_NORMALIZER_HIGH,
    SMA_RATIO_NORMALIZER_LOW,
    SMA_SHORT_WINDOW,
    STATE_CONFIRMATION_SUPPORT_SESSION_CAP,
    VOLUME_PERSISTENCE_MINIMUM_OBSERVATIONS,
    VOLUME_PERSISTENCE_SESSION_COUNT,
    CandidateComponentParameter,
    CandidateRiskModeParameter,
)
from tip_api.parameters.market_regime.relationship_v1_0_0 import ETF_BASKET
from tip_api.persistence.parquet.dashboard_universe_activation import PUBLIC_SECONDARY_ID
from tip_api.services.market_regime_sources import MarketRegimeBar, MarketRegimeInputPanel
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID


ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")
ANNUALIZATION = Decimal(ANNUALIZATION_SESSION_COUNT)
SCORE_QUANTUM = Decimal(1).scaleb(-SCORE_DECIMAL_SCALE)
RAW_QUANTUM = Decimal(1).scaleb(-RAW_DECIMAL_SCALE)
MIN_DRIVER_CORRELATION = Decimal(CORRELATION_MINIMUM)
LOW_RELATIONSHIP_SUPPORT = Decimal(dict(RELATIONSHIP_SUPPORT_LEVELS)["low"])


class OpportunityCandidateCalculationError(RuntimeError):
    """Raised when a candidate calculation cannot preserve its formal boundary."""


@dataclass(frozen=True, slots=True)
class _RawCandidate:
    instrument_id: UUID
    ticker: str
    security_type: str
    latest_price: Decimal
    history_count: int
    values: dict[str, Decimal | None]
    missing_reasons: dict[str, str]
    primary_driver_instrument_id: UUID | None
    primary_driver_ticker: str | None
    driver_correlation: Decimal | None
    corporate_action_review_required: bool
    corporate_action_review_reason_codes: tuple[str, ...]
    non_blocking_quality_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ComponentDraft:
    parameter: CandidateComponentParameter
    score: Decimal | None
    cap_applied: Decimal | None
    metrics: tuple[CandidateMetricV1, ...]
    reason_codes: tuple[str, ...]


def calculate_opportunity_candidate_scores(
    *,
    panel: MarketRegimeInputPanel,
    universe_id: str,
    regime_score: Decimal | str | None,
    regime_state: RegimeState | str | None,
    regime_source_fingerprint: str,
    prior_state_source: CandidatePriorStateSourceV1,
) -> OpportunityCandidateBatchV1:
    """Calculate one source-bound fact ledger for every as-of bar-covered member."""

    with localcontext(_calculation_context()):
        return _calculate_scores(
            panel=panel,
            universe_id=universe_id,
            regime_score=None if regime_score is None else _decimal(regime_score, "regime_score"),
            regime_state=None if regime_state is None else RegimeState(regime_state),
            regime_source_fingerprint=regime_source_fingerprint,
            prior_state_source=prior_state_source,
        )


def rank_opportunity_candidates(
    *,
    batch: OpportunityCandidateBatchV1,
    risk_mode: CandidateRiskMode | str,
) -> CandidateRiskModeResultV1:
    """Apply visible risk gates and deterministic concentration-aware ranking."""

    with localcontext(_calculation_context()):
        mode = CandidateRiskMode(risk_mode)
        parameter = _risk_parameter(mode)
        preliminary: dict[UUID, list[str]] = {}
        sortable: list[OpportunityCandidateScoreV1] = []
        for candidate in batch.candidates:
            reasons = _risk_rejections(candidate, parameter)
            preliminary[candidate.instrument_id] = reasons
            if not reasons:
                sortable.append(candidate)
        sortable.sort(
            key=lambda item: (
                -_decimal(item.base_score, "base_score"),
                -_decimal(item.confidence.confidence, "confidence"),
                -_decimal(item.median_dollar_volume_20, "median_dollar_volume_20"),
                item.ticker,
                str(item.instrument_id),
            )
        )

        maximum_per_group = max(
            1,
            int(
                (Decimal(parameter.candidate_display_cap) * Decimal(parameter.concentration_cap)).to_integral_value(
                    rounding=ROUND_FLOOR
                )
            ),
        )
        retained: list[OpportunityCandidateScoreV1] = []
        group_counts: dict[str, int] = defaultdict(int)
        for candidate in sortable:
            group = str(candidate.primary_driver_instrument_id) if candidate.primary_driver_instrument_id else "unclassified"
            if len(retained) >= parameter.candidate_display_cap:
                preliminary[candidate.instrument_id].append("risk_mode_display_cap_exceeded")
                continue
            if group_counts[group] >= maximum_per_group:
                preliminary[candidate.instrument_id].append("risk_mode_concentration_cap_exceeded")
                continue
            group_counts[group] += 1
            retained.append(candidate)

        ranks = {item.instrument_id: index for index, item in enumerate(retained, start=1)}
        assessments = tuple(
            CandidateRiskAssessmentV1(
                instrument_id=candidate.instrument_id,
                ticker=candidate.ticker,
                risk_mode=mode,
                eligible=candidate.instrument_id in ranks,
                risk_adjusted_rank=ranks.get(candidate.instrument_id),
                concentration_key=(str(candidate.primary_driver_instrument_id) if candidate.primary_driver_instrument_id else "unclassified"),
                rejection_reason_codes=tuple(preliminary[candidate.instrument_id]),
            )
            for candidate in batch.candidates
        )
        parameter_row = (
            ("minimum_median_dollar_volume", parameter.minimum_median_dollar_volume),
            ("maximum_annualized_volatility", parameter.maximum_annualized_volatility),
            ("maximum_absolute_open_gap", parameter.maximum_absolute_open_gap),
            ("minimum_price", parameter.minimum_price),
            ("minimum_confidence", parameter.minimum_confidence),
            ("adrc_permitted", str(parameter.adrc_permitted).lower()),
            ("candidate_display_cap", str(parameter.candidate_display_cap)),
            ("concentration_cap", parameter.concentration_cap),
            ("maximum_candidates_per_concentration_key", str(maximum_per_group)),
        )
        provisional = CandidateRiskModeResultV1(
            parameter_fingerprint=CANDIDATE_PARAMETER_FINGERPRINT,
            as_of_session=batch.as_of_session,
            universe_id=batch.universe_id,
            risk_mode=mode,
            parameter_row=parameter_row,
            assessments=assessments,
            eligible_count=len(retained),
            rejected_count=len(assessments) - len(retained),
            logical_fingerprint="0" * 64,
        )
        return provisional.model_copy(
            update={"logical_fingerprint": _fingerprint(provisional.model_dump(mode="json", exclude={"logical_fingerprint"}))}
        )


def _calculate_scores(
    *,
    panel: MarketRegimeInputPanel,
    universe_id: str,
    regime_score: Decimal | None,
    regime_state: RegimeState | None,
    regime_source_fingerprint: str,
    prior_state_source: CandidatePriorStateSourceV1,
) -> OpportunityCandidateBatchV1:
    _validate_sha(regime_source_fingerprint, "regime_source_fingerprint")
    if len(panel.sessions) != CANDIDATE_PANEL_SESSION_COUNT or panel.sessions[-1] != panel.as_of_session:
        raise OpportunityCandidateCalculationError("candidate scoring requires the exact ordered session count ending at as-of")
    if tuple(sorted(panel.sessions)) != panel.sessions or len(set(panel.sessions)) != len(panel.sessions):
        raise OpportunityCandidateCalculationError("candidate sessions must be unique and ascending")
    if regime_score is not None and not ZERO <= regime_score <= HUNDRED:
        raise OpportunityCandidateCalculationError("regime score must be within 0 and 100")

    universe = panel.select_universe(universe_id)
    primary = panel.select_universe(CANDIDATE_A_ID)
    secondary = panel.select_universe(PUBLIC_SECONDARY_ID)
    if not primary.member_ids < secondary.member_ids:
        raise OpportunityCandidateCalculationError("Secondary must be a strict superset of Primary")
    if universe_id not in {CANDIDATE_A_ID, PUBLIC_SECONDARY_ID}:
        raise OpportunityCandidateCalculationError("candidate scoring permits only active public Universes")
    if prior_state_source.universe_id != universe_id or prior_state_source.as_of_session != panel.as_of_session:
        raise OpportunityCandidateCalculationError("typed prior candidate-state source does not match the score batch")

    by_instrument: dict[UUID, dict[object, MarketRegimeBar]] = defaultdict(dict)
    current: dict[UUID, MarketRegimeBar] = {}
    for bar in panel.bars:
        if bar.session_date not in set(panel.sessions) or bar.session_date > panel.as_of_session:
            raise OpportunityCandidateCalculationError("future or out-of-panel candidate input")
        if bar.session_date in by_instrument[bar.instrument_id]:
            raise OpportunityCandidateCalculationError("duplicate candidate instrument/session business key")
        _validate_bar(bar)
        by_instrument[bar.instrument_id][bar.session_date] = bar
        if bar.session_date == panel.as_of_session:
            current[bar.instrument_id] = bar

    etf_ids = _resolve_etfs(current)
    if "SPY" not in etf_ids:
        raise OpportunityCandidateCalculationError("SPY must be uniquely resolved for candidate scoring")
    etf_returns_5 = {
        ticker: _return(by_instrument[instrument_id], panel.sessions, 5)
        for ticker, instrument_id in etf_ids.items()
    }
    relevant_return_ids = universe.member_ids | frozenset(etf_ids.values())
    log_returns_by_instrument = {
        instrument_id: _log_return_map(by_instrument[instrument_id], panel.sessions)
        for instrument_id in relevant_return_ids
    }
    spy_return_5 = etf_returns_5["SPY"]
    spy_return_20 = _return(by_instrument[etf_ids["SPY"]], panel.sessions, 20)

    raw_candidates: list[_RawCandidate] = []
    missing_ids: list[UUID] = []
    for instrument_id in sorted(universe.member_ids, key=str):
        current_bar = current.get(instrument_id)
        if current_bar is None:
            missing_ids.append(instrument_id)
            continue
        security_type = "CS" if instrument_id in primary.member_ids else "ADRC"
        raw_candidates.append(
            _raw_candidate(
                panel=panel,
                bars=by_instrument[instrument_id],
                current_bar=current_bar,
                security_type=security_type,
                etf_ids=etf_ids,
                candidate_log_returns=log_returns_by_instrument[instrument_id],
                etf_log_returns=log_returns_by_instrument,
                etf_returns_5=etf_returns_5,
                spy_return_5=spy_return_5,
                spy_return_20=spy_return_20,
            )
        )

    candidate_ids = tuple(item.instrument_id for item in raw_candidates)
    if prior_state_source.bootstrap:
        confirmation_by_id: dict[UUID, tuple[int, str | None]] = {
            instrument_id: (0, None) for instrument_id in candidate_ids
        }
    else:
        if prior_state_source.source_state_session != panel.sessions[-2]:
            raise OpportunityCandidateCalculationError("prior candidate-state source must be the immediately preceding panel session")
        support_ids = tuple(item.instrument_id for item in prior_state_source.supports)
        if support_ids != candidate_ids:
            raise OpportunityCandidateCalculationError("prior candidate-state support must cover every current candidate exactly")
        confirmation_by_id = {
            item.instrument_id: (
                item.stage_confirmation_session_count,
                item.source_state_record_fingerprint,
            )
            for item in prior_state_source.supports
        }

    robust_metric_ids = (
        "driver_relative_strength_5",
        "stock_relative_to_driver_5",
        "stock_relative_to_spy_5",
        "stock_relative_to_spy_20",
        "current_volume_ratio_log",
    )
    cross_scores = {
        metric_id: _robust_cross_section(
            {
                item.instrument_id: item.values[metric_id]
                for item in raw_candidates
                if item.values.get(metric_id) is not None
            }
        )
        for metric_id in robust_metric_ids
    }
    return_percentiles = _average_rank_percentiles(
        {
            item.instrument_id: item.values["return_20"]
            for item in raw_candidates
            if item.values.get("return_20") is not None
        }
    )

    candidates = tuple(
        _candidate_record(
            panel=panel,
            universe_id=universe_id,
            raw=item,
            regime_score=regime_score,
            regime_state=regime_state,
            cross_scores=cross_scores,
            return_percentiles=return_percentiles,
            confirmation_count=confirmation_by_id[item.instrument_id][0],
            prior_state_record_fingerprint=confirmation_by_id[item.instrument_id][1],
        )
        for item in raw_candidates
    )
    warnings = ["current_as_of_constituent_replay", "underlying_stock_opportunity_not_option_return"]
    if missing_ids:
        warnings.append("as_of_member_bar_missingness_present")
    provisional = OpportunityCandidateBatchV1(
        parameter_fingerprint=CANDIDATE_PARAMETER_FINGERPRINT,
        as_of_session=panel.as_of_session,
        universe_id=universe_id,
        universe_member_count=len(universe.member_ids),
        membership_fingerprint=universe.membership_fingerprint,
        regime_source_fingerprint=regime_source_fingerprint,
        history_source_fingerprint=panel.history_source_fingerprint,
        prior_state_source=prior_state_source,
        bar_covered_member_count=len(candidates),
        missing_member_ids=tuple(missing_ids),
        candidates=candidates,
        warnings=tuple(warnings),
        logical_fingerprint="0" * 64,
    )
    return provisional.model_copy(
        update={"logical_fingerprint": _fingerprint(provisional.model_dump(mode="json", exclude={"logical_fingerprint"}))}
    )


def _raw_candidate(
    *,
    panel: MarketRegimeInputPanel,
    bars: dict[object, MarketRegimeBar],
    current_bar: MarketRegimeBar,
    security_type: str,
    etf_ids: dict[str, UUID],
    candidate_log_returns: dict[object, Decimal],
    etf_log_returns: dict[UUID, dict[object, Decimal]],
    etf_returns_5: dict[str, Decimal | None],
    spy_return_5: Decimal | None,
    spy_return_20: Decimal | None,
) -> _RawCandidate:
    sessions = panel.sessions
    values: dict[str, Decimal | None] = {}
    reasons: dict[str, str] = {}

    values["return_1"] = _return(bars, sessions, 1)
    values["return_5"] = _return(bars, sessions, 5)
    values["return_20"] = _return(bars, sessions, 20)
    values["stock_relative_to_spy_5"] = _difference(values["return_5"], spy_return_5)
    values["stock_relative_to_spy_20"] = _difference(values["return_20"], spy_return_20)

    closes10 = _series(bars, sessions[-SMA_SHORT_WINDOW:], "close", minimum=SMA_SHORT_WINDOW)
    closes20 = _series(bars, sessions[-SMA_LONG_WINDOW:], "close", minimum=SMA_LONG_WINDOW)
    closes6 = _series(
        bars,
        sessions[-MAXIMUM_DRAWDOWN_CLOSE_COUNT:],
        "close",
        minimum=MAXIMUM_DRAWDOWN_CLOSE_COUNT,
    )
    values["close_above_sma10"] = None if closes10 is None else (HUNDRED if current_bar.close > _mean(closes10) else ZERO)
    if closes10 is None or closes20 is None:
        values["sma10_to_sma20"] = None
    else:
        values["sma10_to_sma20"] = _mean(closes10) / _mean(closes20) - ONE
    values["maximum_drawdown_5"] = None if closes6 is None else abs(_maximum_drawdown(closes6))

    prior_volumes = _series(
        bars,
        sessions[-PRIOR_VOLUME_WINDOW - 1 : -1],
        "volume",
        minimum=PRIOR_VOLUME_MINIMUM_OBSERVATIONS,
    )
    values["current_volume_ratio"] = (
        None if prior_volumes is None or _median(prior_volumes) <= ZERO else current_bar.volume / _median(prior_volumes)
    )
    values["current_volume_ratio_log"] = (
        None if values["current_volume_ratio"] is None or values["current_volume_ratio"] <= ZERO else values["current_volume_ratio"].ln()
    )
    if values["return_1"] is None or values["current_volume_ratio"] is None:
        values["up_session_participation"] = None
    else:
        positive = values["return_1"] > ZERO
        above = values["current_volume_ratio"] > ONE
        values["up_session_participation"] = (
            HUNDRED if positive and above else Decimal(CROSS_SECTION_SCORE_CENTER) if positive or above else ZERO
        )
    persistence: list[Decimal] = []
    for index in range(len(sessions) - VOLUME_PERSISTENCE_SESSION_COUNT, len(sessions)):
        bar = bars.get(sessions[index])
        prior = _series(
            bars,
            sessions[max(0, index - PRIOR_VOLUME_WINDOW) : index],
            "volume",
            minimum=PRIOR_VOLUME_MINIMUM_OBSERVATIONS,
        )
        if bar is not None and prior is not None:
            persistence.append(ONE if bar.volume > _median(prior) else ZERO)
    values["volume_persistence_5"] = (
        _mean(tuple(persistence))
        if len(persistence) >= VOLUME_PERSISTENCE_MINIMUM_OBSERVATIONS
        else None
    )

    log_returns_10 = _log_returns(bars, sessions[-REALIZED_VOLATILITY_RETURN_COUNT - 1 :])
    values["realized_volatility_10"] = (
        None if log_returns_10 is None else _sample_standard_deviation(log_returns_10) * ANNUALIZATION.sqrt()
    )
    gaps = _open_gaps(bars, sessions[-OPEN_GAP_SESSION_COUNT - 1 :])
    values["maximum_open_gap_5"] = (
        None if len(gaps) < OPEN_GAP_MINIMUM_OBSERVATIONS else max(abs(item) for item in gaps)
    )
    recent_returns = _simple_returns(bars, sessions[-DOWNSIDE_TAIL_SESSION_COUNT - 1 :])
    values["downside_tail_share_5"] = (
        None
        if len(recent_returns) < DOWNSIDE_TAIL_MINIMUM_OBSERVATIONS
        else Decimal(sum(item <= Decimal(DOWNSIDE_TAIL_RETURN_THRESHOLD) for item in recent_returns))
        / Decimal(len(recent_returns))
    )
    dollar_volumes = tuple(
        bar.close * bar.volume
        for session in sessions[-DOLLAR_VOLUME_WINDOW:]
        if (bar := bars.get(session)) is not None
    )
    values["median_dollar_volume_20"] = (
        _median(dollar_volumes) if len(dollar_volumes) >= DOLLAR_VOLUME_MINIMUM_OBSERVATIONS else None
    )
    values["latest_price"] = current_bar.close

    driver_ticker = None
    driver_instrument_id = None
    driver_correlation = None
    for ticker in sorted(etf_ids):
        driver_return = etf_returns_5.get(ticker)
        if driver_return is None or driver_return <= ZERO:
            continue
        correlation, observations = _paired_correlation(
            candidate_log_returns,
            etf_log_returns[etf_ids[ticker]],
            sessions[-DRIVER_CORRELATION_WINDOW:],
        )
        if correlation is None or observations < CORRELATION_MINIMUM_OBSERVATIONS or correlation < MIN_DRIVER_CORRELATION:
            continue
        if driver_correlation is None or correlation > driver_correlation:
            driver_ticker = ticker
            driver_instrument_id = etf_ids[ticker]
            driver_correlation = correlation
    if driver_ticker is None:
        values["driver_relative_strength_5"] = None
        values["stock_relative_to_driver_5"] = None
        values["driver_correlation_20"] = None
        reasons["driver_relative_strength_5"] = "no_qualifying_registered_etf_proxy"
        reasons["stock_relative_to_driver_5"] = "no_qualifying_registered_etf_proxy"
        reasons["driver_correlation_20"] = "no_qualifying_registered_etf_proxy"
    else:
        driver_return = etf_returns_5[driver_ticker]
        values["driver_relative_strength_5"] = _difference(driver_return, spy_return_5)
        values["stock_relative_to_driver_5"] = _difference(values["return_5"], driver_return)
        values["driver_correlation_20"] = driver_correlation

    for metric_id, value in values.items():
        if value is None and metric_id not in reasons:
            reasons[metric_id] = "insufficient_required_history"
    all_returns = _simple_returns(bars, sessions)
    all_gaps = _open_gaps(bars, sessions)
    review_reasons: list[str] = []
    if any(abs(item) >= Decimal(EXTREME_CLOSE_RETURN_REVIEW_THRESHOLD) for item in all_returns):
        review_reasons.append("extreme_close_return_review_threshold_reached")
    if any(abs(item) >= Decimal(EXTREME_OPEN_GAP_REVIEW_THRESHOLD) for item in all_gaps):
        review_reasons.append("extreme_open_gap_review_threshold_reached")
    candidate_bars = tuple(bars[session] for session in sessions if session in bars)
    if any(
        factor != ONE
        for bar in candidate_bars
        for factor in (
            bar.split_adjustment_factor,
            bar.dividend_adjustment_factor,
            bar.total_return_adjustment_factor,
        )
    ):
        review_reasons.append("non_unit_adjustment_factor_review_required")
    if any(bar.quality_status != "valid" for bar in candidate_bars):
        review_reasons.append("source_quality_status_review_required")
    observed_quality_flags = {
        flag
        for bar in candidate_bars
        for flag in bar.quality_flags
    }
    allowed_quality_flags = set(CANDIDATE_NON_BLOCKING_QUALITY_FLAGS)
    if observed_quality_flags - allowed_quality_flags:
        review_reasons.append("unknown_source_quality_flag_review_required")
    non_blocking_quality_flags = tuple(
        flag for flag in CANDIDATE_NON_BLOCKING_QUALITY_FLAGS if flag in observed_quality_flags
    )
    return _RawCandidate(
        instrument_id=current_bar.instrument_id,
        ticker=current_bar.ticker,
        security_type=security_type,
        latest_price=current_bar.close,
        history_count=sum(session in bars for session in sessions[-CANDIDATE_REQUIRED_HISTORY_SESSION_COUNT:]),
        values=values,
        missing_reasons=reasons,
        primary_driver_instrument_id=driver_instrument_id,
        primary_driver_ticker=driver_ticker,
        driver_correlation=driver_correlation,
        corporate_action_review_required=bool(review_reasons),
        corporate_action_review_reason_codes=tuple(review_reasons),
        non_blocking_quality_flags=non_blocking_quality_flags,
    )


def _candidate_record(
    *,
    panel: MarketRegimeInputPanel,
    universe_id: str,
    raw: _RawCandidate,
    regime_score: Decimal | None,
    regime_state: RegimeState | None,
    cross_scores: dict[str, dict[UUID, Decimal]],
    return_percentiles: dict[UUID, Decimal],
    confirmation_count: int,
    prior_state_record_fingerprint: str | None,
) -> OpportunityCandidateScoreV1:
    normalized: dict[str, Decimal | None] = {
        "regime_score": regime_score,
        "driver_relative_strength_5": cross_scores["driver_relative_strength_5"].get(raw.instrument_id),
        "stock_relative_to_driver_5": cross_scores["stock_relative_to_driver_5"].get(raw.instrument_id),
        "driver_correlation_20": _linear(
            raw.values["driver_correlation_20"],
            Decimal(CORRELATION_MINIMUM),
            Decimal(DRIVER_CORRELATION_NORMALIZER_HIGH),
        ),
        "stock_relative_to_spy_5": cross_scores["stock_relative_to_spy_5"].get(raw.instrument_id),
        "stock_relative_to_spy_20": cross_scores["stock_relative_to_spy_20"].get(raw.instrument_id),
        "stock_return_percentile_20": return_percentiles.get(raw.instrument_id),
        "close_above_sma10": raw.values["close_above_sma10"],
        "sma10_to_sma20": _linear(
            raw.values["sma10_to_sma20"],
            Decimal(SMA_RATIO_NORMALIZER_LOW),
            Decimal(SMA_RATIO_NORMALIZER_HIGH),
        ),
        "maximum_drawdown_5": _declining(
            raw.values["maximum_drawdown_5"],
            Decimal(MAXIMUM_DRAWDOWN_NORMALIZER_LOW),
            Decimal(MAXIMUM_DRAWDOWN_NORMALIZER_HIGH),
        ),
        "current_volume_ratio": cross_scores["current_volume_ratio_log"].get(raw.instrument_id),
        "up_session_participation": raw.values["up_session_participation"],
        "volume_persistence_5": None if raw.values["volume_persistence_5"] is None else raw.values["volume_persistence_5"] * HUNDRED,
        "realized_volatility_10": _declining(
            raw.values["realized_volatility_10"],
            Decimal(REALIZED_VOLATILITY_NORMALIZER_LOW),
            Decimal(REALIZED_VOLATILITY_NORMALIZER_HIGH),
        ),
        "maximum_open_gap_5": _declining(
            raw.values["maximum_open_gap_5"],
            Decimal(OPEN_GAP_NORMALIZER_LOW),
            Decimal(OPEN_GAP_NORMALIZER_HIGH),
        ),
        "downside_tail_share_5": _declining(
            raw.values["downside_tail_share_5"],
            Decimal(DOWNSIDE_TAIL_NORMALIZER_LOW),
            Decimal(DOWNSIDE_TAIL_NORMALIZER_HIGH),
        ),
        "median_dollar_volume_20": _log_linear(
            raw.values["median_dollar_volume_20"],
            Decimal(LIQUIDITY_NORMALIZER_LOW),
            Decimal(LIQUIDITY_NORMALIZER_HIGH),
        ),
        "latest_price": _linear(
            raw.values["latest_price"],
            Decimal(PRICE_NORMALIZER_LOW),
            Decimal(PRICE_NORMALIZER_HIGH),
        ),
    }
    raw_aliases = {
        "regime_score": regime_score,
        "current_volume_ratio": raw.values["current_volume_ratio"],
        "stock_return_percentile_20": raw.values["return_20"],
        **{key: value for key, value in raw.values.items() if key in normalized},
    }
    drafts = tuple(
        _component_draft(parameter, raw, raw_aliases, normalized, panel.sessions)
        for parameter in COMPONENT_PARAMETERS
    )
    available_weight = sum(
        Decimal(item.parameter.configured_weight) for item in drafts if item.score is not None
    )
    effective_weights = {
        item.parameter.component_id: (
            ZERO if item.score is None or available_weight == ZERO else Decimal(item.parameter.configured_weight) * HUNDRED / available_weight
        )
        for item in drafts
    }
    components = tuple(
        CandidateComponentV1(
            component_id=item.parameter.component_id,
            configured_weight=_q_score(Decimal(item.parameter.configured_weight)),
            effective_weight=_q_score(effective_weights[item.parameter.component_id]),
            score=None if item.score is None else _q_score(item.score),
            contribution=None if item.score is None else _q_score(item.score * effective_weights[item.parameter.component_id] / HUNDRED),
            availability=(CandidateMetricAvailability.AVAILABLE if item.score is not None else CandidateMetricAvailability.UNAVAILABLE),
            cap_applied=None if item.cap_applied is None else _q_score(item.cap_applied),
            metrics=item.metrics,
            reason_codes=item.reason_codes,
        )
        for item in drafts
    )
    score_available = available_weight >= Decimal(MINIMUM_CONFIGURED_WEIGHT_AVAILABLE)
    base_score = (
        sum(_decimal(item.contribution, "component contribution") for item in components if item.contribution is not None)
        if score_available
        else None
    )
    source_completeness = available_weight / HUNDRED
    history_completeness = min(Decimal(raw.history_count) / Decimal(CANDIDATE_REQUIRED_HISTORY_SESSION_COUNT), ONE)
    relationship_support = LOW_RELATIONSHIP_SUPPORT if raw.primary_driver_ticker is not None else ZERO
    state_support = min(
        Decimal(confirmation_count) / Decimal(STATE_CONFIRMATION_SUPPORT_SESSION_CAP),
        ONE,
    )
    source_completeness = source_completeness.quantize(SCORE_QUANTUM)
    history_completeness = history_completeness.quantize(SCORE_QUANTUM)
    relationship_support = relationship_support.quantize(SCORE_QUANTUM)
    state_support = state_support.quantize(SCORE_QUANTUM)
    confidence_value = (
        Decimal(CONFIDENCE_SOURCE_WEIGHT) * source_completeness
        + Decimal(CONFIDENCE_HISTORY_WEIGHT) * history_completeness
        + Decimal(CONFIDENCE_RELATIONSHIP_WEIGHT) * relationship_support
        + Decimal(CONFIDENCE_STATE_WEIGHT) * state_support
    )
    confidence = CandidateConfidenceV1(
        source_completeness=_q_score(source_completeness),
        history_completeness=_q_score(history_completeness),
        relationship_support=_q_score(relationship_support),
        state_confirmation_support=_q_score(state_support),
        confirmation_session_count=confirmation_count,
        prior_state_record_fingerprint=prior_state_record_fingerprint,
        confidence=_q_score(confidence_value),
    )
    positive = sorted(
        (item for item in components if item.score is not None),
        key=lambda item: (-_decimal(item.contribution, "contribution"), item.component_id),
    )
    unavailable = [item.component_id for item in components if item.score is None]
    adverse = sorted(
        (item for item in components if item.score is not None),
        key=lambda item: (_decimal(item.score, "component score"), item.component_id),
    )
    supporting = tuple(f"positive_component:{item.component_id}:{item.contribution}" for item in positive[:3])
    counter = tuple(f"missing_component:{item}" for item in unavailable) + tuple(
        f"weak_component:{item.component_id}:{item.score}" for item in adverse[: max(0, 2 - len(unavailable))]
    )
    warnings = [
        "current_as_of_constituent_replay",
        "corporate_action_adjustment_factor_not_formally_reconciled",
        "underlying_stock_score_not_option_return",
        "candidate_score_not_success_probability",
    ]
    if raw.primary_driver_ticker is not None:
        warnings.append("price_derived_exposure_proxy_not_sector_membership")
    if base_score is None:
        warnings.append("candidate_score_unavailable_due_to_component_missingness")
    if raw.corporate_action_review_required:
        warnings.extend(raw.corporate_action_review_reason_codes)
        warnings.append("corporate_action_review_required")
    if raw.non_blocking_quality_flags:
        warnings.extend(
            f"non_blocking_source_quality_flag:{flag}"
            for flag in raw.non_blocking_quality_flags
        )
        warnings.append("non_blocking_source_quality_limitations_present")
    quality = (
        CandidateDataQualityStatus.QUARANTINED
        if raw.corporate_action_review_required
        else CandidateDataQualityStatus.DEGRADED
        if (
            base_score is None
            or available_weight < HUNDRED
            or raw.primary_driver_ticker is not None
            or raw.non_blocking_quality_flags
        )
        else CandidateDataQualityStatus.PASSED
    )
    reasons = ["fixed_candidate_parameter_set", "regime_adjustment_fixed_zero"]
    reasons.append("candidate_score_available" if base_score is not None else "candidate_score_unavailable")
    if regime_state is not None:
        reasons.append(f"regime_state_{regime_state.value}")
    if raw.primary_driver_ticker is not None:
        reasons.append("registered_etf_price_proxy_selected")
    if raw.corporate_action_review_required:
        reasons.extend(raw.corporate_action_review_reason_codes)
        reasons.append("corporate_action_review_required")
    provisional = OpportunityCandidateScoreV1(
        parameter_fingerprint=CANDIDATE_PARAMETER_FINGERPRINT,
        as_of_session=panel.as_of_session,
        universe_id=universe_id,
        instrument_id=raw.instrument_id,
        ticker=raw.ticker,
        security_type=raw.security_type,
        latest_data_session=panel.as_of_session,
        base_score=None if base_score is None else _q_score(base_score),
        adjusted_score=None if base_score is None else _q_score(base_score),
        configured_weight_available=_q_score(available_weight),
        missingness_penalty=_q_score(HUNDRED - available_weight),
        components=components,
        confidence=confidence,
        latest_price=_q_raw(raw.latest_price),
        median_dollar_volume_20=_q_optional_raw(raw.values["median_dollar_volume_20"]),
        annualized_volatility_10=_q_optional_raw(raw.values["realized_volatility_10"]),
        maximum_absolute_open_gap_5=_q_optional_raw(raw.values["maximum_open_gap_5"]),
        current_volume_ratio=_q_optional_raw(raw.values["current_volume_ratio"]),
        primary_driver_instrument_id=raw.primary_driver_instrument_id,
        primary_driver_ticker=raw.primary_driver_ticker,
        driver_correlation_20=_q_optional_raw(raw.driver_correlation),
        relationship_kind="price_derived_exposure_proxy" if raw.primary_driver_ticker else None,
        corporate_action_review_required=raw.corporate_action_review_required,
        data_quality_status=quality,
        supporting_evidence=supporting,
        counterevidence=counter[:2],
        invalidation_conditions=(
            "base_score_below_45",
            "latest_price_below_2",
            "median_dollar_volume_below_5000000",
            "corporate_action_or_source_integrity_review",
        ),
        reason_codes=tuple(reasons),
        warnings=tuple(warnings),
        logical_fingerprint="0" * 64,
    )
    return provisional.model_copy(
        update={"logical_fingerprint": _fingerprint(provisional.model_dump(mode="json", exclude={"logical_fingerprint"}))}
    )


def _component_draft(
    parameter: CandidateComponentParameter,
    raw: _RawCandidate,
    raw_values: dict[str, Decimal | None],
    normalized: dict[str, Decimal | None],
    sessions: tuple,
) -> _ComponentDraft:
    metrics: list[CandidateMetricV1] = []
    weighted = ZERO
    missing = False
    for metric_id, weight in parameter.submetric_weights:
        value = raw_values.get(metric_id)
        score = normalized.get(metric_id)
        if value is None or score is None:
            missing = True
            reason = raw.missing_reasons.get(metric_id, "cross_sectional_normalization_unavailable")
            metrics.append(
                CandidateMetricV1(
                    metric_id=metric_id,
                    raw_value=None,
                    raw_unit=_raw_unit(metric_id),
                    normalized_value=None,
                    availability=CandidateMetricAvailability.UNAVAILABLE,
                    missing_reason=reason,
                    evidence_type=_evidence_type(metric_id),
                    source_sessions=tuple(sessions[-CANDIDATE_REQUIRED_HISTORY_SESSION_COUNT:]),
                    reason_codes=(reason,),
                )
            )
            continue
        metrics.append(
            CandidateMetricV1(
                metric_id=metric_id,
                raw_value=_q_raw(value),
                raw_unit=_raw_unit(metric_id),
                normalized_value=_q_score(score),
                availability=CandidateMetricAvailability.AVAILABLE,
                missing_reason=None,
                evidence_type=_evidence_type(metric_id),
                source_sessions=tuple(sessions[-CANDIDATE_REQUIRED_HISTORY_SESSION_COUNT:]),
                reason_codes=("fixed_v1_normalization",),
            )
        )
        weighted += score * Decimal(weight) / HUNDRED
    if missing:
        return _ComponentDraft(parameter, None, None, tuple(metrics), ("required_submetric_missing",))
    cap = None
    if parameter.component_id == "etf_sector_alignment" and weighted > Decimal(ETF_ALIGNMENT_CAP):
        weighted = Decimal(ETF_ALIGNMENT_CAP)
        cap = Decimal(ETF_ALIGNMENT_CAP)
    reasons = ["fixed_component_formula"]
    if cap is not None:
        reasons.append("price_proxy_component_cap_applied")
    return _ComponentDraft(parameter, weighted, cap, tuple(metrics), tuple(reasons))


def _risk_rejections(candidate: OpportunityCandidateScoreV1, parameter: CandidateRiskModeParameter) -> list[str]:
    reasons: list[str] = []
    if candidate.base_score is None:
        reasons.append("candidate_score_unavailable")
    elif _decimal(candidate.base_score, "base_score") < Decimal(BASE_WATCH_SCORE):
        reasons.append("below_watch_score")
    if _decimal(candidate.latest_price, "latest_price") < Decimal(BASE_PRICE_FLOOR):
        reasons.append("base_price_floor_failed")
    if candidate.median_dollar_volume_20 is None or _decimal(candidate.median_dollar_volume_20, "liquidity") < Decimal(BASE_LIQUIDITY_FLOOR):
        reasons.append("base_liquidity_floor_failed")
    if _decimal(candidate.confidence.confidence, "confidence") < Decimal(BASE_WATCH_CONFIDENCE):
        reasons.append("base_confidence_floor_failed")
    if candidate.corporate_action_review_required or candidate.data_quality_status in {
        CandidateDataQualityStatus.QUARANTINED,
        CandidateDataQualityStatus.FAILED,
    }:
        reasons.append("candidate_quarantined")
    if _decimal(candidate.latest_price, "latest_price") < Decimal(parameter.minimum_price):
        reasons.append("risk_mode_price_floor_failed")
    if candidate.median_dollar_volume_20 is None or _decimal(candidate.median_dollar_volume_20, "liquidity") < Decimal(parameter.minimum_median_dollar_volume):
        reasons.append("risk_mode_liquidity_floor_failed")
    if candidate.annualized_volatility_10 is None or _decimal(candidate.annualized_volatility_10, "volatility") > Decimal(parameter.maximum_annualized_volatility):
        reasons.append("risk_mode_volatility_ceiling_failed")
    if candidate.maximum_absolute_open_gap_5 is None or _decimal(candidate.maximum_absolute_open_gap_5, "gap") > Decimal(parameter.maximum_absolute_open_gap):
        reasons.append("risk_mode_gap_ceiling_failed")
    if _decimal(candidate.confidence.confidence, "confidence") < Decimal(parameter.minimum_confidence):
        reasons.append("risk_mode_confidence_floor_failed")
    if candidate.security_type == "ADRC" and not parameter.adrc_permitted:
        reasons.append("risk_mode_adrc_not_permitted")
    return reasons


def _resolve_etfs(current: dict[UUID, MarketRegimeBar]) -> dict[str, UUID]:
    registered = {item.ticker for item in ETF_BASKET}
    candidates: dict[str, list[UUID]] = defaultdict(list)
    for instrument_id, bar in current.items():
        if bar.instrument_type == "etf" and bar.ticker in registered:
            candidates[bar.ticker].append(instrument_id)
    resolved: dict[str, UUID] = {}
    for ticker, ids in candidates.items():
        if len(ids) != 1:
            raise OpportunityCandidateCalculationError(f"registered ETF {ticker} is not uniquely resolved")
        resolved[ticker] = ids[0]
    return resolved


def _risk_parameter(mode: CandidateRiskMode) -> CandidateRiskModeParameter:
    return next(item for item in RISK_MODE_PARAMETERS if item.risk_mode == mode.value)


def _return(bars: dict[object, MarketRegimeBar], sessions: tuple, window: int) -> Decimal | None:
    left = bars.get(sessions[-window - 1])
    right = bars.get(sessions[-1])
    if left is None or right is None or left.close <= ZERO:
        return None
    return right.close / left.close - ONE


def _series(bars: dict[object, MarketRegimeBar], sessions, field: str, *, minimum: int) -> tuple[Decimal, ...] | None:
    values = tuple(getattr(bars[session], field) for session in sessions if session in bars)
    return values if len(values) >= minimum else None


def _simple_returns(bars: dict[object, MarketRegimeBar], sessions) -> tuple[Decimal, ...]:
    values: list[Decimal] = []
    for previous_session, session in zip(sessions, sessions[1:]):
        previous = bars.get(previous_session)
        current = bars.get(session)
        if previous is not None and current is not None and previous.close > ZERO:
            values.append(current.close / previous.close - ONE)
    return tuple(values)


def _log_returns(bars: dict[object, MarketRegimeBar], sessions) -> tuple[Decimal, ...] | None:
    simple = _simple_returns(bars, sessions)
    if len(simple) != len(tuple(sessions)) - 1:
        return None
    return tuple((ONE + item).ln() for item in simple)


def _open_gaps(bars: dict[object, MarketRegimeBar], sessions) -> tuple[Decimal, ...]:
    values: list[Decimal] = []
    for previous_session, session in zip(sessions, sessions[1:]):
        previous = bars.get(previous_session)
        current = bars.get(session)
        if previous is not None and current is not None and previous.close > ZERO:
            values.append(current.open / previous.close - ONE)
    return tuple(values)


def _log_return_map(
    bars: dict[object, MarketRegimeBar],
    sessions,
) -> dict[object, Decimal]:
    output: dict[object, Decimal] = {}
    for previous_session, session in zip(sessions, sessions[1:]):
        previous = bars.get(previous_session)
        current = bars.get(session)
        if previous is not None and current is not None and previous.close > ZERO:
            output[session] = (current.close / previous.close).ln()
    return output


def _paired_correlation(
    left: dict[object, Decimal],
    right: dict[object, Decimal],
    sessions,
) -> tuple[Decimal | None, int]:
    left_returns: list[Decimal] = []
    right_returns: list[Decimal] = []
    for session in sessions:
        left_return = left.get(session)
        right_return = right.get(session)
        if left_return is None or right_return is None:
            continue
        left_returns.append(left_return)
        right_returns.append(right_return)
    count = len(left_returns)
    if count < CORRELATION_MINIMUM_OBSERVATIONS:
        return None, count
    left_mean, right_mean = _mean(tuple(left_returns)), _mean(tuple(right_returns))
    covariance = sum((a - left_mean) * (b - right_mean) for a, b in zip(left_returns, right_returns))
    left_variance = sum((item - left_mean) ** 2 for item in left_returns)
    right_variance = sum((item - right_mean) ** 2 for item in right_returns)
    if left_variance == ZERO or right_variance == ZERO:
        return None, count
    return covariance / (left_variance * right_variance).sqrt(), count


def _robust_cross_section(values: dict[UUID, Decimal | None]) -> dict[UUID, Decimal]:
    clean = {key: value for key, value in values.items() if value is not None}
    if not clean:
        return {}
    ordered = tuple(sorted(clean.values()))
    low = _quantile(ordered, Decimal(CROSS_SECTION_WINSOR_LOW))
    high = _quantile(ordered, Decimal(CROSS_SECTION_WINSOR_HIGH))
    winsorized = {key: min(high, max(low, value)) for key, value in clean.items()}
    center = _median(tuple(winsorized.values()))
    mad = _median(tuple(abs(value - center) for value in winsorized.values()))
    if mad == ZERO:
        return _average_rank_percentiles(winsorized)
    return {
        key: _clip100(
            Decimal(CROSS_SECTION_SCORE_CENTER)
            + Decimal(CROSS_SECTION_SCORE_SCALE)
            * Decimal(CROSS_SECTION_ROBUST_Z_SCALE)
            * (value - center)
            / mad
        )
        for key, value in winsorized.items()
    }


def _average_rank_percentiles(values: dict[UUID, Decimal | None]) -> dict[UUID, Decimal]:
    clean = {key: value for key, value in values.items() if value is not None}
    if not clean:
        return {}
    if len(set(clean.values())) == 1:
        return {key: Decimal(CROSS_SECTION_SCORE_CENTER) for key in clean}
    groups: dict[Decimal, list[UUID]] = defaultdict(list)
    for key, value in clean.items():
        groups[value].append(key)
    output: dict[UUID, Decimal] = {}
    rank_start = 1
    denominator = Decimal(len(clean) - 1)
    for value in sorted(groups):
        keys = sorted(groups[value], key=str)
        rank_end = rank_start + len(keys) - 1
        average_rank = (Decimal(rank_start) + Decimal(rank_end)) / Decimal(2)
        percentile = HUNDRED * (average_rank - ONE) / denominator
        for key in keys:
            output[key] = percentile
        rank_start = rank_end + 1
    return output


def _quantile(ordered: tuple[Decimal, ...], probability: Decimal) -> Decimal:
    if not ordered:
        raise OpportunityCandidateCalculationError("quantile requires observations")
    if len(ordered) == 1:
        return ordered[0]
    position = Decimal(len(ordered) - 1) * probability
    lower = int(position.to_integral_value(rounding=ROUND_FLOOR))
    fraction = position - Decimal(lower)
    if lower >= len(ordered) - 1:
        return ordered[-1]
    return ordered[lower] + fraction * (ordered[lower + 1] - ordered[lower])


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise OpportunityCandidateCalculationError("mean requires observations")
    return sum(values, ZERO) / Decimal(len(values))


def _median(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise OpportunityCandidateCalculationError("median requires observations")
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def _sample_standard_deviation(values: tuple[Decimal, ...]) -> Decimal:
    if len(values) < 2:
        raise OpportunityCandidateCalculationError("sample standard deviation requires two observations")
    center = _mean(values)
    return (sum((item - center) ** 2 for item in values) / Decimal(len(values) - 1)).sqrt()


def _maximum_drawdown(values: tuple[Decimal, ...]) -> Decimal:
    peak = values[0]
    drawdown = ZERO
    for value in values:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - ONE)
    return drawdown


def _difference(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    return None if left is None or right is None else left - right


def _linear(value: Decimal | None, low: Decimal, high: Decimal) -> Decimal | None:
    return None if value is None else _clip100(HUNDRED * (value - low) / (high - low))


def _declining(value: Decimal | None, low: Decimal, high: Decimal) -> Decimal | None:
    score = _linear(value, low, high)
    return None if score is None else HUNDRED - score


def _log_linear(value: Decimal | None, low: Decimal, high: Decimal) -> Decimal | None:
    if value is None or value <= ZERO:
        return None
    return _linear(value.log10(), low.log10(), high.log10())


def _clip100(value: Decimal) -> Decimal:
    return min(HUNDRED, max(ZERO, value))


def _raw_unit(metric_id: str) -> str:
    if metric_id == "median_dollar_volume_20":
        return "usd_proxy"
    if metric_id == "latest_price":
        return "usd"
    if metric_id == "regime_score" or metric_id in {"close_above_sma10", "up_session_participation"}:
        return "score"
    return "ratio"


def _evidence_type(metric_id: str) -> str:
    if metric_id in {"median_dollar_volume_20", "current_volume_ratio", "volume_persistence_5", "up_session_participation"}:
        return "proxy"
    if metric_id in {
        "driver_relative_strength_5",
        "stock_relative_to_driver_5",
        "driver_correlation_20",
        "stock_relative_to_spy_5",
        "stock_relative_to_spy_20",
        "stock_return_percentile_20",
    }:
        return "statistical_inference"
    return "fact"


def _validate_bar(bar: MarketRegimeBar) -> None:
    values = (
        bar.open,
        bar.high,
        bar.low,
        bar.close,
        bar.volume,
        bar.split_adjustment_factor,
        bar.dividend_adjustment_factor,
        bar.total_return_adjustment_factor,
    )
    if any(not value.is_finite() for value in values):
        raise OpportunityCandidateCalculationError("non-finite candidate input")
    if min(bar.open, bar.high, bar.low, bar.close) <= ZERO or bar.volume < ZERO:
        raise OpportunityCandidateCalculationError("illegal candidate price or volume")
    if min(
        bar.split_adjustment_factor,
        bar.dividend_adjustment_factor,
        bar.total_return_adjustment_factor,
    ) <= ZERO:
        raise OpportunityCandidateCalculationError("candidate adjustment factors must be positive")
    if bar.quality_status not in {"valid", "warning", "rejected", "pending_review"}:
        raise OpportunityCandidateCalculationError("candidate source quality status is unknown")
    if bar.high < max(bar.open, bar.close, bar.low) or bar.low > min(bar.open, bar.close, bar.high):
        raise OpportunityCandidateCalculationError("invalid candidate OHLC")


def _validate_sha(value: str, field: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise OpportunityCandidateCalculationError(f"{field} must be lowercase SHA-256")


def _decimal(value: Decimal | str | None, field: str) -> Decimal:
    if value is None:
        raise OpportunityCandidateCalculationError(f"{field} is unavailable")
    parsed = value if isinstance(value, Decimal) else Decimal(value)
    if not parsed.is_finite():
        raise OpportunityCandidateCalculationError(f"{field} must be finite")
    return parsed


def _q_score(value: Decimal) -> str:
    return format(value.quantize(SCORE_QUANTUM), "f")


def _q_raw(value: Decimal) -> str:
    return format(value.quantize(RAW_QUANTUM), "f")


def _q_optional_raw(value: Decimal | None) -> str | None:
    return None if value is None else _q_raw(value)


def _calculation_context() -> Context:
    context = Context(prec=CALCULATION_DECIMAL_PRECISION, rounding=ROUND_HALF_EVEN)
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    context.traps[Inexact] = False
    context.traps[Rounded] = False
    return context


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
