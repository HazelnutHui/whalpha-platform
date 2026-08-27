"""Independent raw-panel Oracle for Phase 5 opportunity candidates.

This module intentionally does not import either production candidate service.
It repeats the fixed calculations from typed source rows and frozen parameters.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date
from decimal import (
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)
from typing import Mapping, Sequence
from uuid import UUID

from tip_api.contracts.analytics.v1 import (
    CandidateComponentV1,
    CandidateConfidenceV1,
    CandidateDataQualityStatus,
    CandidateMetricAvailability,
    CandidateMetricV1,
    CandidateOpportunityStage,
    CandidateRiskAssessmentV1,
    CandidateRiskMode,
    CandidateRiskModeResultV1,
    CandidateStateObservationV1,
    CandidateStateTransitionStatus,
    OpportunityCandidateBatchV1,
    OpportunityCandidateScoreV1,
    OpportunityCandidateStateRecordV1,
    RegimeState,
)
from tip_api.parameters.market_regime import candidate_v1_1_1 as p
from tip_api.parameters.market_regime.relationship_v1_0_0 import ETF_BASKET
from tip_api.services.market_regime_sources import MarketRegimeBar, MarketRegimeInputPanel


ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")
SCORE_QUANTUM = Decimal(1).scaleb(-p.SCORE_DECIMAL_SCALE)
RAW_QUANTUM = Decimal(1).scaleb(-p.RAW_DECIMAL_SCALE)
LOW_RELATIONSHIP_SUPPORT = Decimal(dict(p.RELATIONSHIP_SUPPORT_LEVELS)["low"])
ORACLE_CONTEXT = Context(prec=p.CALCULATION_DECIMAL_PRECISION, rounding=ROUND_HALF_EVEN)
for _signal in (InvalidOperation, DivisionByZero, Overflow):
    ORACLE_CONTEXT.traps[_signal] = True


@dataclass(frozen=True, slots=True)
class CandidateRawFactOracleV1:
    """Universe-neutral security facts; contextual normalization is excluded."""

    as_of_session: date
    instrument_id: UUID
    ticker: str
    security_type: str
    history_count: int
    values: Mapping[str, Decimal | None]
    missing_reasons: Mapping[str, str]
    primary_driver_instrument_id: UUID | None
    primary_driver_ticker: str | None
    driver_correlation: Decimal | None
    corporate_action_review_required: bool
    corporate_action_review_reason_codes: tuple[str, ...]
    non_blocking_quality_flags: tuple[str, ...]
    logical_fingerprint: str


@dataclass(frozen=True, slots=True)
class CandidateStateOracleCase:
    observations: tuple[CandidateStateObservationV1, ...]
    expected_sessions: tuple[date, ...]
    universe_id: str
    instrument_id: UUID
    ticker: str
    security_type: str
    actual_records: tuple[OpportunityCandidateStateRecordV1, ...]


@dataclass(frozen=True, slots=True)
class CandidateIncrementalStateOracleCase:
    """One-session state append independently initialized from a verified row."""

    prior_record: OpportunityCandidateStateRecordV1
    observation: CandidateStateObservationV1 | None
    as_of_session: date
    universe_id: str
    instrument_id: UUID
    ticker: str
    security_type: str
    actual_record: OpportunityCandidateStateRecordV1


@dataclass(frozen=True, slots=True)
class CandidateOracleComparisonV1:
    candidate_count: int
    risk_result_count: int
    state_record_count: int
    raw_fact_count: int
    mismatch_count: int
    mismatches: tuple[str, ...]
    shared_raw_fact_match: bool
    input_permutation_match: bool
    oracle_fingerprint: str


@dataclass(frozen=True, slots=True)
class _Draft:
    component_id: str
    configured_weight: int
    score: Decimal | None
    cap: Decimal | None
    metrics: tuple[CandidateMetricV1, ...]
    reasons: tuple[str, ...]


@dataclass(slots=True)
class _StateRuntime:
    stage: CandidateOpportunityStage | None = None
    pending_target: CandidateOpportunityStage | None = None
    pending_rule: str | None = None
    pending_count: int = 0
    missing_count: int = 0
    stage_count: int = 0


@dataclass(frozen=True, slots=True)
class _Transition:
    rule: str
    target: CandidateOpportunityStage
    required: int
    reason: str


def compare_with_independent_candidate_oracle(
    *,
    panel: MarketRegimeInputPanel,
    batches: Sequence[OpportunityCandidateBatchV1],
    regime_context_by_universe: Mapping[str, tuple[Decimal | str | None, RegimeState | str | None]],
    risk_results: Sequence[CandidateRiskModeResultV1] = (),
    state_cases: Sequence[CandidateStateOracleCase] = (),
    incremental_state_cases: Sequence[CandidateIncrementalStateOracleCase] = (),
) -> CandidateOracleComparisonV1:
    """Recalculate facts, scores, rankings, and supplied state histories."""

    with localcontext(ORACLE_CONTEXT):
        expected_batches: dict[str, OpportunityCandidateBatchV1] = {}
        raw_by_universe: dict[str, dict[UUID, CandidateRawFactOracleV1]] = {}
        for actual in batches:
            regime_score, regime_state = regime_context_by_universe[actual.universe_id]
            expected, raw = _oracle_batch(
                panel=panel,
                actual=actual,
                regime_score=None if regime_score is None else Decimal(regime_score),
                regime_state=None if regime_state is None else RegimeState(regime_state),
            )
            expected_batches[actual.universe_id] = expected
            raw_by_universe[actual.universe_id] = raw

        mismatches: list[str] = []
        for actual in batches:
            expected = expected_batches[actual.universe_id]
            _compare_models("batch", actual.universe_id, actual, expected, mismatches)

        expected_risks: dict[tuple[str, str], CandidateRiskModeResultV1] = {}
        for actual in risk_results:
            batch = expected_batches.get(actual.universe_id)
            if batch is None:
                mismatches.append(f"risk:{actual.universe_id}:{actual.risk_mode.value}:missing_batch")
                continue
            expected = _oracle_risk(batch, actual.risk_mode)
            expected_risks[(actual.universe_id, actual.risk_mode.value)] = expected
            _compare_models(
                "risk",
                f"{actual.universe_id}:{actual.risk_mode.value}",
                actual,
                expected,
                mismatches,
            )

        state_count = 0
        state_fingerprints: list[str] = []
        for case in state_cases:
            expected = _oracle_state_history(case)
            state_count += len(expected)
            state_fingerprints.extend(item.logical_fingerprint for item in expected)
            if len(expected) != len(case.actual_records):
                mismatches.append(
                    f"state:{case.universe_id}:{case.instrument_id}:count:actual={len(case.actual_records)}:oracle={len(expected)}"
                )
            for index, (actual, wanted) in enumerate(zip(case.actual_records, expected)):
                _compare_models(
                    "state",
                    f"{case.universe_id}:{case.instrument_id}:{index}",
                    actual,
                    wanted,
                    mismatches,
                )

        for case in incremental_state_cases:
            expected = _oracle_incremental_state(case)
            state_count += 1
            state_fingerprints.append(expected.logical_fingerprint)
            _compare_models(
                "incremental_state",
                f"{case.universe_id}:{case.instrument_id}:{case.as_of_session.isoformat()}",
                case.actual_record,
                expected,
                mismatches,
            )

        shared_match = _shared_raw_match(raw_by_universe, mismatches)
        permuted_match = _permutation_match(
            panel=panel,
            batches=batches,
            regime_context_by_universe=regime_context_by_universe,
            expected=expected_batches,
        )
        if not permuted_match:
            mismatches.append("input_permutation:oracle_output_changed")

        raw_count = sum(len(item) for item in raw_by_universe.values())
        fingerprint = _fingerprint(
            {
                "batches": {key: value.logical_fingerprint for key, value in sorted(expected_batches.items())},
                "risks": {f"{key[0]}:{key[1]}": value.logical_fingerprint for key, value in sorted(expected_risks.items())},
                "states": state_fingerprints,
                "raw": {
                    universe: [facts[key].logical_fingerprint for key in sorted(facts, key=str)]
                    for universe, facts in sorted(raw_by_universe.items())
                },
            }
        )
    return CandidateOracleComparisonV1(
        candidate_count=sum(len(item.candidates) for item in expected_batches.values()),
        risk_result_count=len(expected_risks),
        state_record_count=state_count,
        raw_fact_count=raw_count,
        mismatch_count=len(mismatches),
        mismatches=tuple(mismatches),
        shared_raw_fact_match=shared_match,
        input_permutation_match=permuted_match,
        oracle_fingerprint=fingerprint,
    )


def _oracle_batch(
    *, panel: MarketRegimeInputPanel, actual: OpportunityCandidateBatchV1,
    regime_score: Decimal | None, regime_state: RegimeState | None,
) -> tuple[OpportunityCandidateBatchV1, dict[UUID, CandidateRawFactOracleV1]]:
    universe = panel.select_universe(actual.universe_id)
    primary, secondary = sorted(panel.universes, key=lambda item: item.catalog_order)[:2]
    if not primary.member_ids < secondary.member_ids:
        raise ValueError("Oracle requires Primary to be a strict subset of Secondary")
    by_id: dict[UUID, dict[date, MarketRegimeBar]] = defaultdict(dict)
    current: dict[UUID, MarketRegimeBar] = {}
    for bar in sorted(panel.bars, key=lambda item: (item.session_date, str(item.instrument_id))):
        if bar.session_date in by_id[bar.instrument_id]:
            raise ValueError("Oracle rejected duplicate instrument/session input")
        by_id[bar.instrument_id][bar.session_date] = bar
        if bar.session_date == panel.as_of_session:
            current[bar.instrument_id] = bar
    etfs = _etfs(current)
    if "SPY" not in etfs:
        raise ValueError("Oracle requires uniquely resolved SPY")
    returns5 = {ticker: _return(by_id[instrument_id], panel.sessions, 5) for ticker, instrument_id in etfs.items()}
    logs = {instrument_id: _log_map(by_id[instrument_id], panel.sessions) for instrument_id in universe.member_ids | frozenset(etfs.values())}
    spy5 = returns5["SPY"]
    spy20 = _return(by_id[etfs["SPY"]], panel.sessions, 20)
    raw: dict[UUID, CandidateRawFactOracleV1] = {}
    missing: list[UUID] = []
    for instrument_id in sorted(universe.member_ids, key=str):
        bar = current.get(instrument_id)
        if bar is None:
            missing.append(instrument_id)
            continue
        row = _raw_fact(
            panel, by_id[instrument_id], bar,
            "CS" if instrument_id in primary.member_ids else "ADRC",
            etfs, logs[instrument_id], logs, returns5, spy5, spy20,
        )
        raw[instrument_id] = row
    robust_ids = (
        "driver_relative_strength_5", "stock_relative_to_driver_5",
        "stock_relative_to_spy_5", "stock_relative_to_spy_20", "current_volume_ratio_log",
    )
    cross = {metric: _robust({key: row.values[metric] for key, row in raw.items() if row.values[metric] is not None}) for metric in robust_ids}
    percentiles = _ranks({key: row.values["return_20"] for key, row in raw.items() if row.values["return_20"] is not None})
    supports = {item.instrument_id: item for item in actual.prior_state_source.supports}
    candidates = tuple(
        _candidate(
            panel, actual.universe_id, row, regime_score, regime_state, cross, percentiles,
            supports[row.instrument_id].stage_confirmation_session_count if row.instrument_id in supports else 0,
            supports[row.instrument_id].source_state_record_fingerprint if row.instrument_id in supports else None,
        )
        for row in raw.values()
    )
    provisional = OpportunityCandidateBatchV1(
        parameter_fingerprint=p.CANDIDATE_PARAMETER_FINGERPRINT,
        as_of_session=panel.as_of_session,
        universe_id=actual.universe_id,
        universe_member_count=len(universe.member_ids),
        membership_fingerprint=universe.membership_fingerprint,
        regime_source_fingerprint=actual.regime_source_fingerprint,
        history_source_fingerprint=panel.history_source_fingerprint,
        prior_state_source=actual.prior_state_source,
        bar_covered_member_count=len(candidates),
        missing_member_ids=tuple(missing),
        candidates=candidates,
        warnings=("current_as_of_constituent_replay", "underlying_stock_opportunity_not_option_return")
        + (("as_of_member_bar_missingness_present",) if missing else ()),
        logical_fingerprint="0" * 64,
    )
    expected = provisional.model_copy(update={"logical_fingerprint": _model_fingerprint(provisional)})
    return expected, raw


def _raw_fact(
    panel, bars, current, security_type, etfs, stock_logs, etf_logs, etf_returns5, spy5, spy20,
) -> CandidateRawFactOracleV1:
    sessions = panel.sessions
    values: dict[str, Decimal | None] = {}
    reasons: dict[str, str] = {}
    values["return_1"] = _return(bars, sessions, 1)
    values["return_5"] = _return(bars, sessions, 5)
    values["return_20"] = _return(bars, sessions, 20)
    values["stock_relative_to_spy_5"] = _difference(values["return_5"], spy5)
    values["stock_relative_to_spy_20"] = _difference(values["return_20"], spy20)
    close10 = _series(bars, sessions[-p.SMA_SHORT_WINDOW:], "close", p.SMA_SHORT_WINDOW)
    close20 = _series(bars, sessions[-p.SMA_LONG_WINDOW:], "close", p.SMA_LONG_WINDOW)
    close6 = _series(bars, sessions[-p.MAXIMUM_DRAWDOWN_CLOSE_COUNT:], "close", p.MAXIMUM_DRAWDOWN_CLOSE_COUNT)
    values["close_above_sma10"] = None if close10 is None else HUNDRED if current.close > _mean(close10) else ZERO
    values["sma10_to_sma20"] = None if close10 is None or close20 is None else _mean(close10) / _mean(close20) - ONE
    values["maximum_drawdown_5"] = None if close6 is None else abs(_drawdown(close6))
    prior_volume = _series(bars, sessions[-p.PRIOR_VOLUME_WINDOW - 1:-1], "volume", p.PRIOR_VOLUME_MINIMUM_OBSERVATIONS)
    values["current_volume_ratio"] = None if prior_volume is None or _median(prior_volume) <= ZERO else current.volume / _median(prior_volume)
    values["current_volume_ratio_log"] = None if values["current_volume_ratio"] is None or values["current_volume_ratio"] <= ZERO else values["current_volume_ratio"].ln()
    if values["return_1"] is None or values["current_volume_ratio"] is None:
        values["up_session_participation"] = None
    else:
        positive, above = values["return_1"] > ZERO, values["current_volume_ratio"] > ONE
        values["up_session_participation"] = HUNDRED if positive and above else Decimal("50") if positive or above else ZERO
    persistence = []
    for index in range(len(sessions) - p.VOLUME_PERSISTENCE_SESSION_COUNT, len(sessions)):
        bar = bars.get(sessions[index])
        prior = _series(bars, sessions[max(0, index - p.PRIOR_VOLUME_WINDOW):index], "volume", p.PRIOR_VOLUME_MINIMUM_OBSERVATIONS)
        if bar is not None and prior is not None:
            persistence.append(ONE if bar.volume > _median(prior) else ZERO)
    values["volume_persistence_5"] = _mean(tuple(persistence)) if len(persistence) >= p.VOLUME_PERSISTENCE_MINIMUM_OBSERVATIONS else None
    logs10 = _log_returns(bars, sessions[-p.REALIZED_VOLATILITY_RETURN_COUNT - 1:])
    values["realized_volatility_10"] = None if logs10 is None else _stdev(logs10) * Decimal(p.ANNUALIZATION_SESSION_COUNT).sqrt()
    gaps = _gaps(bars, sessions[-p.OPEN_GAP_SESSION_COUNT - 1:])
    values["maximum_open_gap_5"] = None if len(gaps) < p.OPEN_GAP_MINIMUM_OBSERVATIONS else max(abs(item) for item in gaps)
    recent = _simple_returns(bars, sessions[-p.DOWNSIDE_TAIL_SESSION_COUNT - 1:])
    values["downside_tail_share_5"] = None if len(recent) < p.DOWNSIDE_TAIL_MINIMUM_OBSERVATIONS else Decimal(sum(item <= Decimal(p.DOWNSIDE_TAIL_RETURN_THRESHOLD) for item in recent)) / Decimal(len(recent))
    dollars = tuple(bars[s].close * bars[s].volume for s in sessions[-p.DOLLAR_VOLUME_WINDOW:] if s in bars)
    values["median_dollar_volume_20"] = _median(dollars) if len(dollars) >= p.DOLLAR_VOLUME_MINIMUM_OBSERVATIONS else None
    values["latest_price"] = current.close
    driver_ticker = None
    driver_id = None
    driver_corr = None
    for ticker in sorted(etfs):
        driver_return = etf_returns5.get(ticker)
        if driver_return is None or driver_return <= ZERO:
            continue
        corr, count = _correlation(stock_logs, etf_logs[etfs[ticker]], sessions[-p.DRIVER_CORRELATION_WINDOW:])
        if corr is None or count < p.CORRELATION_MINIMUM_OBSERVATIONS or corr < Decimal(p.CORRELATION_MINIMUM):
            continue
        if driver_corr is None or corr > driver_corr:
            driver_ticker, driver_id, driver_corr = ticker, etfs[ticker], corr
    if driver_ticker is None:
        for metric in ("driver_relative_strength_5", "stock_relative_to_driver_5", "driver_correlation_20"):
            values[metric] = None
            reasons[metric] = "no_qualifying_registered_etf_proxy"
    else:
        values["driver_relative_strength_5"] = _difference(etf_returns5[driver_ticker], spy5)
        values["stock_relative_to_driver_5"] = _difference(values["return_5"], etf_returns5[driver_ticker])
        values["driver_correlation_20"] = driver_corr
    for metric, value in values.items():
        if value is None and metric not in reasons:
            reasons[metric] = "insufficient_required_history"
    review = []
    if any(abs(item) >= Decimal(p.EXTREME_CLOSE_RETURN_REVIEW_THRESHOLD) for item in _simple_returns(bars, sessions)):
        review.append("extreme_close_return_review_threshold_reached")
    if any(abs(item) >= Decimal(p.EXTREME_OPEN_GAP_REVIEW_THRESHOLD) for item in _gaps(bars, sessions)):
        review.append("extreme_open_gap_review_threshold_reached")
    candidate_bars = tuple(bars[s] for s in sessions if s in bars)
    if any(factor != ONE for bar in candidate_bars for factor in (bar.split_adjustment_factor, bar.dividend_adjustment_factor, bar.total_return_adjustment_factor)):
        review.append("non_unit_adjustment_factor_review_required")
    if any(bar.quality_status != "valid" for bar in candidate_bars):
        review.append("source_quality_status_review_required")
    observed_quality_flags = {flag for bar in candidate_bars for flag in bar.quality_flags}
    allowed_quality_flags = set(p.CANDIDATE_NON_BLOCKING_QUALITY_FLAGS)
    if observed_quality_flags - allowed_quality_flags:
        review.append("unknown_source_quality_flag_review_required")
    non_blocking_quality_flags = tuple(
        flag for flag in p.CANDIDATE_NON_BLOCKING_QUALITY_FLAGS if flag in observed_quality_flags
    )
    raw_payload = {
        "as_of_session": panel.as_of_session.isoformat(), "instrument_id": str(current.instrument_id),
        "ticker": current.ticker, "security_type": security_type,
        "history_count": sum(s in bars for s in sessions[-p.CANDIDATE_REQUIRED_HISTORY_SESSION_COUNT:]),
        "values": {key: None if value is None else str(value) for key, value in sorted(values.items())},
        "missing_reasons": dict(sorted(reasons.items())),
        "primary_driver_instrument_id": None if driver_id is None else str(driver_id),
        "primary_driver_ticker": driver_ticker,
        "driver_correlation": None if driver_corr is None else str(driver_corr),
        "corporate_action_review_required": bool(review), "review_reasons": review,
        "non_blocking_quality_flags": list(non_blocking_quality_flags),
    }
    return CandidateRawFactOracleV1(
        panel.as_of_session, current.instrument_id, current.ticker, security_type,
        raw_payload["history_count"], values, reasons, driver_id, driver_ticker, driver_corr,
        bool(review), tuple(review), non_blocking_quality_flags, _fingerprint(raw_payload),
    )


def _candidate(panel, universe_id, raw, regime_score, regime_state, cross, percentiles, confirmation_count, prior_fp):
    normalized = {
        "regime_score": regime_score,
        "driver_relative_strength_5": cross["driver_relative_strength_5"].get(raw.instrument_id),
        "stock_relative_to_driver_5": cross["stock_relative_to_driver_5"].get(raw.instrument_id),
        "driver_correlation_20": _linear(raw.values["driver_correlation_20"], Decimal(p.CORRELATION_MINIMUM), Decimal(p.DRIVER_CORRELATION_NORMALIZER_HIGH)),
        "stock_relative_to_spy_5": cross["stock_relative_to_spy_5"].get(raw.instrument_id),
        "stock_relative_to_spy_20": cross["stock_relative_to_spy_20"].get(raw.instrument_id),
        "stock_return_percentile_20": percentiles.get(raw.instrument_id),
        "close_above_sma10": raw.values["close_above_sma10"],
        "sma10_to_sma20": _linear(raw.values["sma10_to_sma20"], Decimal(p.SMA_RATIO_NORMALIZER_LOW), Decimal(p.SMA_RATIO_NORMALIZER_HIGH)),
        "maximum_drawdown_5": _declining(raw.values["maximum_drawdown_5"], Decimal(p.MAXIMUM_DRAWDOWN_NORMALIZER_LOW), Decimal(p.MAXIMUM_DRAWDOWN_NORMALIZER_HIGH)),
        "current_volume_ratio": cross["current_volume_ratio_log"].get(raw.instrument_id),
        "up_session_participation": raw.values["up_session_participation"],
        "volume_persistence_5": None if raw.values["volume_persistence_5"] is None else raw.values["volume_persistence_5"] * HUNDRED,
        "realized_volatility_10": _declining(raw.values["realized_volatility_10"], Decimal(p.REALIZED_VOLATILITY_NORMALIZER_LOW), Decimal(p.REALIZED_VOLATILITY_NORMALIZER_HIGH)),
        "maximum_open_gap_5": _declining(raw.values["maximum_open_gap_5"], Decimal(p.OPEN_GAP_NORMALIZER_LOW), Decimal(p.OPEN_GAP_NORMALIZER_HIGH)),
        "downside_tail_share_5": _declining(raw.values["downside_tail_share_5"], Decimal(p.DOWNSIDE_TAIL_NORMALIZER_LOW), Decimal(p.DOWNSIDE_TAIL_NORMALIZER_HIGH)),
        "median_dollar_volume_20": _log_linear(raw.values["median_dollar_volume_20"], Decimal(p.LIQUIDITY_NORMALIZER_LOW), Decimal(p.LIQUIDITY_NORMALIZER_HIGH)),
        "latest_price": _linear(raw.values["latest_price"], Decimal(p.PRICE_NORMALIZER_LOW), Decimal(p.PRICE_NORMALIZER_HIGH)),
    }
    aliases = {"regime_score": regime_score, "current_volume_ratio": raw.values["current_volume_ratio"], "stock_return_percentile_20": raw.values["return_20"], **{key: value for key, value in raw.values.items() if key in normalized}}
    drafts = tuple(_draft(parameter, raw, aliases, normalized, panel.sessions) for parameter in p.COMPONENT_PARAMETERS)
    available = sum(Decimal(item.configured_weight) for item in drafts if item.score is not None)
    components = []
    for draft in drafts:
        effective = ZERO if draft.score is None or available == ZERO else Decimal(draft.configured_weight) * HUNDRED / available
        components.append(CandidateComponentV1(
            component_id=draft.component_id, configured_weight=_qs(Decimal(draft.configured_weight)), effective_weight=_qs(effective),
            score=None if draft.score is None else _qs(draft.score), contribution=None if draft.score is None else _qs(draft.score * effective / HUNDRED),
            availability=CandidateMetricAvailability.AVAILABLE if draft.score is not None else CandidateMetricAvailability.UNAVAILABLE,
            cap_applied=None if draft.cap is None else _qs(draft.cap), metrics=draft.metrics, reason_codes=draft.reasons,
        ))
    components_tuple = tuple(components)
    base = sum(Decimal(item.contribution) for item in components_tuple if item.contribution is not None) if available >= Decimal(p.MINIMUM_CONFIGURED_WEIGHT_AVAILABLE) else None
    source = (available / HUNDRED).quantize(SCORE_QUANTUM)
    history = min(Decimal(raw.history_count) / Decimal(p.CANDIDATE_REQUIRED_HISTORY_SESSION_COUNT), ONE).quantize(SCORE_QUANTUM)
    relationship = (LOW_RELATIONSHIP_SUPPORT if raw.primary_driver_ticker else ZERO).quantize(SCORE_QUANTUM)
    state = min(Decimal(confirmation_count) / Decimal(p.STATE_CONFIRMATION_SUPPORT_SESSION_CAP), ONE).quantize(SCORE_QUANTUM)
    confidence_value = Decimal(p.CONFIDENCE_SOURCE_WEIGHT) * source + Decimal(p.CONFIDENCE_HISTORY_WEIGHT) * history + Decimal(p.CONFIDENCE_RELATIONSHIP_WEIGHT) * relationship + Decimal(p.CONFIDENCE_STATE_WEIGHT) * state
    confidence = CandidateConfidenceV1(
        source_completeness=_qs(source), history_completeness=_qs(history), relationship_support=_qs(relationship), state_confirmation_support=_qs(state),
        confirmation_session_count=confirmation_count, prior_state_record_fingerprint=prior_fp, confidence=_qs(confidence_value),
    )
    positive = sorted((item for item in components_tuple if item.score is not None), key=lambda item: (-Decimal(item.contribution), item.component_id))
    unavailable = [item.component_id for item in components_tuple if item.score is None]
    adverse = sorted((item for item in components_tuple if item.score is not None), key=lambda item: (Decimal(item.score), item.component_id))
    warnings = ["current_as_of_constituent_replay", "corporate_action_adjustment_factor_not_formally_reconciled", "underlying_stock_score_not_option_return", "candidate_score_not_success_probability"]
    if raw.primary_driver_ticker: warnings.append("price_derived_exposure_proxy_not_sector_membership")
    if base is None: warnings.append("candidate_score_unavailable_due_to_component_missingness")
    if raw.corporate_action_review_required: warnings.extend((*raw.corporate_action_review_reason_codes, "corporate_action_review_required"))
    if raw.non_blocking_quality_flags:
        warnings.extend(f"non_blocking_source_quality_flag:{flag}" for flag in raw.non_blocking_quality_flags)
        warnings.append("non_blocking_source_quality_limitations_present")
    reasons = ["fixed_candidate_parameter_set", "regime_adjustment_fixed_zero", "candidate_score_available" if base is not None else "candidate_score_unavailable"]
    if regime_state is not None: reasons.append(f"regime_state_{regime_state.value}")
    if raw.primary_driver_ticker: reasons.append("registered_etf_price_proxy_selected")
    if raw.corporate_action_review_required: reasons.extend((*raw.corporate_action_review_reason_codes, "corporate_action_review_required"))
    quality = CandidateDataQualityStatus.QUARANTINED if raw.corporate_action_review_required else CandidateDataQualityStatus.DEGRADED if base is None or available < HUNDRED or raw.primary_driver_ticker or raw.non_blocking_quality_flags else CandidateDataQualityStatus.PASSED
    provisional = OpportunityCandidateScoreV1(
        parameter_fingerprint=p.CANDIDATE_PARAMETER_FINGERPRINT, as_of_session=panel.as_of_session, universe_id=universe_id,
        instrument_id=raw.instrument_id, ticker=raw.ticker, security_type=raw.security_type, latest_data_session=panel.as_of_session,
        base_score=None if base is None else _qs(base), adjusted_score=None if base is None else _qs(base), configured_weight_available=_qs(available), missingness_penalty=_qs(HUNDRED - available),
        components=components_tuple, confidence=confidence, latest_price=_qr(raw.values["latest_price"]), median_dollar_volume_20=_qro(raw.values["median_dollar_volume_20"]),
        annualized_volatility_10=_qro(raw.values["realized_volatility_10"]), maximum_absolute_open_gap_5=_qro(raw.values["maximum_open_gap_5"]), current_volume_ratio=_qro(raw.values["current_volume_ratio"]),
        primary_driver_instrument_id=raw.primary_driver_instrument_id, primary_driver_ticker=raw.primary_driver_ticker, driver_correlation_20=_qro(raw.driver_correlation),
        relationship_kind="price_derived_exposure_proxy" if raw.primary_driver_ticker else None, corporate_action_review_required=raw.corporate_action_review_required, data_quality_status=quality,
        supporting_evidence=tuple(f"positive_component:{item.component_id}:{item.contribution}" for item in positive[:3]),
        counterevidence=(tuple(f"missing_component:{item}" for item in unavailable) + tuple(f"weak_component:{item.component_id}:{item.score}" for item in adverse[:max(0, 2-len(unavailable))]))[:2],
        invalidation_conditions=("base_score_below_45", "latest_price_below_2", "median_dollar_volume_below_5000000", "corporate_action_or_source_integrity_review"),
        reason_codes=tuple(reasons), warnings=tuple(warnings), logical_fingerprint="0" * 64,
    )
    return provisional.model_copy(update={"logical_fingerprint": _model_fingerprint(provisional)})


def _draft(parameter, raw, aliases, normalized, sessions):
    metrics = []
    weighted = ZERO
    missing = False
    for metric, weight in parameter.submetric_weights:
        value, score = aliases.get(metric), normalized.get(metric)
        if value is None or score is None:
            missing = True
            reason = raw.missing_reasons.get(metric, "cross_sectional_normalization_unavailable")
            metrics.append(CandidateMetricV1(metric_id=metric, raw_value=None, raw_unit=_unit(metric), normalized_value=None, availability="unavailable", missing_reason=reason, evidence_type=_evidence(metric), source_sessions=tuple(sessions[-21:]), reason_codes=(reason,)))
        else:
            metrics.append(CandidateMetricV1(metric_id=metric, raw_value=_qr(value), raw_unit=_unit(metric), normalized_value=_qs(score), availability="available", missing_reason=None, evidence_type=_evidence(metric), source_sessions=tuple(sessions[-21:]), reason_codes=("fixed_v1_normalization",)))
            weighted += score * Decimal(weight) / HUNDRED
    if missing:
        return _Draft(parameter.component_id, parameter.configured_weight, None, None, tuple(metrics), ("required_submetric_missing",))
    cap = None
    if parameter.component_id == "etf_sector_alignment" and weighted > Decimal(p.ETF_ALIGNMENT_CAP):
        weighted, cap = Decimal(p.ETF_ALIGNMENT_CAP), Decimal(p.ETF_ALIGNMENT_CAP)
    reasons = ("fixed_component_formula",) + (("price_proxy_component_cap_applied",) if cap is not None else ())
    return _Draft(parameter.component_id, parameter.configured_weight, weighted, cap, tuple(metrics), reasons)


def _oracle_risk(batch, mode):
    mode = CandidateRiskMode(mode)
    parameter = next(item for item in p.RISK_MODE_PARAMETERS if item.risk_mode == mode.value)
    preliminary = {item.instrument_id: _risk_rejections(item, parameter) for item in batch.candidates}
    sortable = [item for item in batch.candidates if not preliminary[item.instrument_id]]
    sortable.sort(key=lambda item: (-Decimal(item.base_score), -Decimal(item.confidence.confidence), -Decimal(item.median_dollar_volume_20), item.ticker, str(item.instrument_id)))
    maximum = max(1, int((Decimal(parameter.candidate_display_cap) * Decimal(parameter.concentration_cap)).to_integral_value(rounding=ROUND_FLOOR)))
    retained, counts = [], defaultdict(int)
    for item in sortable:
        group = str(item.primary_driver_instrument_id) if item.primary_driver_instrument_id else "unclassified"
        if len(retained) >= parameter.candidate_display_cap:
            preliminary[item.instrument_id].append("risk_mode_display_cap_exceeded")
        elif counts[group] >= maximum:
            preliminary[item.instrument_id].append("risk_mode_concentration_cap_exceeded")
        else:
            counts[group] += 1; retained.append(item)
    ranks = {item.instrument_id: index for index, item in enumerate(retained, 1)}
    assessments = tuple(CandidateRiskAssessmentV1(
        instrument_id=item.instrument_id, ticker=item.ticker, risk_mode=mode, eligible=item.instrument_id in ranks,
        risk_adjusted_rank=ranks.get(item.instrument_id), concentration_key=str(item.primary_driver_instrument_id) if item.primary_driver_instrument_id else "unclassified",
        rejection_reason_codes=tuple(preliminary[item.instrument_id]),
    ) for item in batch.candidates)
    row = (("minimum_median_dollar_volume", parameter.minimum_median_dollar_volume), ("maximum_annualized_volatility", parameter.maximum_annualized_volatility), ("maximum_absolute_open_gap", parameter.maximum_absolute_open_gap), ("minimum_price", parameter.minimum_price), ("minimum_confidence", parameter.minimum_confidence), ("adrc_permitted", str(parameter.adrc_permitted).lower()), ("candidate_display_cap", str(parameter.candidate_display_cap)), ("concentration_cap", parameter.concentration_cap), ("maximum_candidates_per_concentration_key", str(maximum)))
    provisional = CandidateRiskModeResultV1(parameter_fingerprint=p.CANDIDATE_PARAMETER_FINGERPRINT, as_of_session=batch.as_of_session, universe_id=batch.universe_id, risk_mode=mode, parameter_row=row, assessments=assessments, eligible_count=len(retained), rejected_count=len(assessments)-len(retained), logical_fingerprint="0"*64)
    return provisional.model_copy(update={"logical_fingerprint": _model_fingerprint(provisional)})


def _risk_rejections(candidate, parameter):
    reasons = []
    if candidate.base_score is None: reasons.append("candidate_score_unavailable")
    elif Decimal(candidate.base_score) < Decimal(p.BASE_WATCH_SCORE): reasons.append("below_watch_score")
    if Decimal(candidate.latest_price) < Decimal(p.BASE_PRICE_FLOOR): reasons.append("base_price_floor_failed")
    if candidate.median_dollar_volume_20 is None or Decimal(candidate.median_dollar_volume_20) < Decimal(p.BASE_LIQUIDITY_FLOOR): reasons.append("base_liquidity_floor_failed")
    if Decimal(candidate.confidence.confidence) < Decimal(p.BASE_WATCH_CONFIDENCE): reasons.append("base_confidence_floor_failed")
    if candidate.corporate_action_review_required or candidate.data_quality_status in {CandidateDataQualityStatus.QUARANTINED, CandidateDataQualityStatus.FAILED}: reasons.append("candidate_quarantined")
    if Decimal(candidate.latest_price) < Decimal(parameter.minimum_price): reasons.append("risk_mode_price_floor_failed")
    if candidate.median_dollar_volume_20 is None or Decimal(candidate.median_dollar_volume_20) < Decimal(parameter.minimum_median_dollar_volume): reasons.append("risk_mode_liquidity_floor_failed")
    if candidate.annualized_volatility_10 is None or Decimal(candidate.annualized_volatility_10) > Decimal(parameter.maximum_annualized_volatility): reasons.append("risk_mode_volatility_ceiling_failed")
    if candidate.maximum_absolute_open_gap_5 is None or Decimal(candidate.maximum_absolute_open_gap_5) > Decimal(parameter.maximum_absolute_open_gap): reasons.append("risk_mode_gap_ceiling_failed")
    if Decimal(candidate.confidence.confidence) < Decimal(parameter.minimum_confidence): reasons.append("risk_mode_confidence_floor_failed")
    if candidate.security_type == "ADRC" and not parameter.adrc_permitted: reasons.append("risk_mode_adrc_not_permitted")
    return reasons


def _oracle_state_history(case):
    runtime = _StateRuntime()
    by_session = {item.candidate.as_of_session: item for item in case.observations}
    output = []
    for session in case.expected_sessions:
        observation = by_session.get(session)
        if observation is None or observation.candidate.base_score is None or observation.candidate.median_dollar_volume_20 is None:
            output.append(_state_missing(case, session, observation, runtime))
        else:
            output.append(_state_available(observation, runtime))
    return tuple(output)


def _oracle_incremental_state(case):
    prior = case.prior_record
    if (
        prior.universe_id != case.universe_id
        or prior.instrument_id != case.instrument_id
        or prior.security_type != case.security_type
        or prior.as_of_session >= case.as_of_session
    ):
        raise ValueError("incremental Oracle prior state is incompatible with append case")
    observation = case.observation
    if observation is not None and observation.candidate.as_of_session != case.as_of_session:
        raise ValueError("incremental Oracle observation session mismatch")
    runtime = _StateRuntime(
        stage=prior.final_stage,
        pending_target=prior.pending_target_stage,
        pending_rule=prior.transition_rule_id if prior.pending_target_stage is not None else None,
        pending_count=(prior.confirmation_count_after if prior.pending_target_stage is not None else 0),
        missing_count=prior.consecutive_missing_sessions,
        stage_count=prior.stage_confirmation_count_after,
    )
    if observation is None or observation.candidate.base_score is None or observation.candidate.median_dollar_volume_20 is None:
        return _state_missing(case, case.as_of_session, observation, runtime)
    return _state_available(observation, runtime)


def _state_available(observation, runtime):
    candidate, prior, stage_before = observation.candidate, runtime.stage, runtime.stage_count
    runtime.missing_count = 0
    gates = _state_gates(observation)
    transition = _state_transition(prior, {item.gate_id: item.passed for item in gates})
    count_before = count_after = 0
    proposed = transition.target if transition else prior
    reasons = ["candidate_state_input_available"]
    if transition is None:
        reversed_pending = runtime.pending_target is not None
        runtime.pending_target = None; runtime.pending_rule = None; runtime.pending_count = 0
        status = CandidateStateTransitionStatus.PENDING_REVERSED if reversed_pending else CandidateStateTransitionStatus.NOT_LISTED if prior is None else CandidateStateTransitionStatus.HELD
        rule = "pending_reversed" if reversed_pending else "not_listed_hold" if prior is None else "stage_hold"
        reasons.append("pending_confirmation_reversed" if reversed_pending else "candidate_not_listed" if prior is None else "candidate_stage_held")
    else:
        if runtime.pending_target is transition.target and runtime.pending_rule == transition.rule: count_before = runtime.pending_count
        runtime.pending_target, runtime.pending_rule, runtime.pending_count = transition.target, transition.rule, count_before + 1
        count_after, rule = runtime.pending_count, transition.rule
        reasons.append(transition.reason)
        if runtime.pending_count >= transition.required:
            runtime.stage = transition.target; runtime.pending_target = None; runtime.pending_rule = None; runtime.pending_count = 0
            status = CandidateStateTransitionStatus.LISTED if transition.rule == "not_listed_to_watch" else CandidateStateTransitionStatus.INVALIDATED if transition.target is CandidateOpportunityStage.INVALIDATED else CandidateStateTransitionStatus.SWITCHED
            if status is CandidateStateTransitionStatus.INVALIDATED: reasons.extend(("candidate_invalidated", "candidate_context_not_sale_action"))
            reasons.append(f"candidate_stage_switched_to_{transition.target.value}")
        else:
            status = CandidateStateTransitionStatus.PENDING; reasons.append("candidate_transition_confirmation_pending")
    required = transition.required if transition else 0
    stage_after = 0 if runtime.stage is None else min(stage_before + 1, p.STATE_CONFIRMATION_SUPPORT_SESSION_CAP) if runtime.stage is prior else 1
    runtime.stage_count = stage_after
    breakout = observation.breakout_fact.triggered if observation.breakout_fact.availability.value == "available" else None
    provisional = OpportunityCandidateStateRecordV1(
        parameter_fingerprint=p.CANDIDATE_STATE_PARAMETER_FINGERPRINT, as_of_session=candidate.as_of_session, universe_id=candidate.universe_id, instrument_id=candidate.instrument_id, ticker=candidate.ticker, security_type=candidate.security_type,
        prior_stage=prior, proposed_stage=proposed, final_stage=runtime.stage, transition_status=status, transition_rule_id=rule, pending_target_stage=runtime.pending_target,
        confirmation_count_before=count_before, confirmation_count_after=count_after, required_confirmation_sessions=required, confirmation_count_source="prior_candidate_state_history",
        input_confidence_confirmation_session_count=candidate.confidence.confirmation_session_count, stage_confirmation_count_before=stage_before, stage_confirmation_count_after=stage_after,
        regime_state=observation.regime_state, base_score=candidate.base_score, confidence=candidate.confidence.confidence, breakout_triggered=breakout, state_availability="available", stale_state=False,
        consecutive_missing_sessions=0, manual_review_required=runtime.stage is CandidateOpportunityStage.INVALIDATED, anomaly_or_quarantine=_anomaly(observation), gate_results=gates, reason_codes=tuple(reasons),
        human_explanation=_state_explanation(status, runtime.stage), source_candidate_fingerprint=candidate.logical_fingerprint, logical_fingerprint="0"*64,
    )
    return provisional.model_copy(update={"logical_fingerprint": _model_fingerprint(provisional)})


def _state_missing(case, session, observation, runtime):
    prior, stage_before = runtime.stage, runtime.stage_count
    runtime.missing_count += 1
    before = runtime.pending_count
    if runtime.missing_count <= p.MISSING_STATE_HOLD_SESSIONS:
        status, final, stale, manual = "unavailable_stale", runtime.stage, runtime.stage is not None, False
        after, stage_after, required, pending = runtime.pending_count, runtime.stage_count, _pending_required(runtime.pending_rule), runtime.pending_target
        rule = runtime.pending_rule or "missing_required_observation_hold"
        reasons = ("missing_required_history", "confirmation_count_paused", "prior_candidate_stage_held_one_session")
    else:
        status, final, stale, manual = "unavailable_null", None, False, True
        runtime.stage = None; runtime.pending_target = None; runtime.pending_rule = None; runtime.pending_count = 0; runtime.stage_count = 0
        after = stage_after = required = 0; pending = None; rule = "missing_required_observation_expired"
        reasons = ("missing_required_history", "stale_state_hold_expired", "candidate_stage_null_manual_review_required")
    provisional = OpportunityCandidateStateRecordV1(
        parameter_fingerprint=p.CANDIDATE_STATE_PARAMETER_FINGERPRINT, as_of_session=session, universe_id=case.universe_id, instrument_id=case.instrument_id, ticker=case.ticker, security_type=case.security_type,
        prior_stage=prior, proposed_stage=None, final_stage=final, transition_status=status, transition_rule_id=rule, pending_target_stage=pending, confirmation_count_before=before, confirmation_count_after=after,
        required_confirmation_sessions=required, confirmation_count_source="prior_candidate_state_history", input_confidence_confirmation_session_count=stage_before, stage_confirmation_count_before=stage_before,
        stage_confirmation_count_after=stage_after, regime_state=None, base_score=None, confidence=None, breakout_triggered=None, state_availability="unavailable", stale_state=stale,
        consecutive_missing_sessions=runtime.missing_count, manual_review_required=manual, anomaly_or_quarantine=False, gate_results=(), reason_codes=reasons,
        human_explanation="Required candidate facts are missing; the prior candidate stage is held stale for this session and confirmation is paused." if final is not None else "Required candidate facts remain missing; the candidate stage is null and requires manual review.",
        source_candidate_fingerprint=None, logical_fingerprint="0"*64,
    )
    return provisional.model_copy(update={"logical_fingerprint": _model_fingerprint(provisional)})


def _state_gates(observation):
    from tip_api.contracts.analytics.v1 import CandidateStateGateResultV1
    c = observation.candidate
    score, confidence, price, liquidity = Decimal(c.base_score), Decimal(c.confidence.confidence), Decimal(c.latest_price), Decimal(c.median_dollar_volume_20)
    component = {item.component_id: None if item.score is None else Decimal(item.score) for item in c.components}
    anomaly = _anomaly(observation)
    breakout = observation.breakout_fact.triggered if observation.breakout_fact.availability.value == "available" else None
    invalidation = score < Decimal(p.INVALIDATION_SCORE) or price < Decimal(p.BASE_PRICE_FLOOR) or liquidity < Decimal(p.BASE_LIQUIDITY_FLOOR) or anomaly or observation.declared_invalidation_fired
    def gate(name, passed, actual, threshold, operator):
        return CandidateStateGateResultV1(gate_id=name, passed=passed, actual_value=None if actual is None else str(actual), threshold=threshold, boundary_operator=operator, reason_codes=(f"{name}_{'unavailable' if passed is None else 'passed' if passed else 'failed'}",))
    return (
        gate("watch_score", score >= Decimal(p.BASE_WATCH_SCORE), score, p.BASE_WATCH_SCORE, ">="), gate("watch_confidence", confidence >= Decimal(p.BASE_WATCH_CONFIDENCE), confidence, p.BASE_WATCH_CONFIDENCE, ">="),
        gate("price_floor", price >= Decimal(p.BASE_PRICE_FLOOR), price, p.BASE_PRICE_FLOOR, ">="), gate("liquidity_floor", liquidity >= Decimal(p.BASE_LIQUIDITY_FLOOR), liquidity, p.BASE_LIQUIDITY_FLOOR, ">="),
        gate("prepare_score", score >= Decimal(p.PREPARE_SCORE), score, p.PREPARE_SCORE, ">="), gate("regime_not_stress", observation.regime_state is not None and observation.regime_state is not RegimeState.STRESS, None if observation.regime_state is None else observation.regime_state.value, "stress", "is_not"),
        gate("relative_strength_prepare", component["stock_relative_strength"] is not None and component["stock_relative_strength"] >= Decimal(p.PREPARE_RELATIVE_STRENGTH_SCORE), component["stock_relative_strength"], p.PREPARE_RELATIVE_STRENGTH_SCORE, ">="),
        gate("trend_prepare", component["trend_quality"] is not None and component["trend_quality"] >= Decimal(p.PREPARE_TREND_SCORE), component["trend_quality"], p.PREPARE_TREND_SCORE, ">="),
        gate("enter_score", score >= Decimal(p.ENTER_SCORE), score, p.ENTER_SCORE, ">="), gate("breakout_fact", breakout, observation.breakout_fact.current_volume_ratio, p.BREAKOUT_VOLUME_RATIO, ">="),
        gate("breakout_score", score >= Decimal(p.BREAKOUT_ENTER_SCORE), score, p.BREAKOUT_ENTER_SCORE, ">="),
        gate("enter_to_prepare", score < Decimal(p.ENTER_TO_PREPARE_SCORE) or (component["trend_quality"] is not None and component["trend_quality"] < Decimal(p.ENTER_TO_PREPARE_TREND_SCORE)), score, p.ENTER_TO_PREPARE_SCORE, "<"),
        gate("prepare_to_watch", score < Decimal(p.PREPARE_TO_WATCH_SCORE) or (component["market_alignment"] is not None and component["market_alignment"] < Decimal(p.PREPARE_TO_WATCH_MARKET_ALIGNMENT_SCORE)), score, p.PREPARE_TO_WATCH_SCORE, "<"),
        gate("invalidation", invalidation, score, p.INVALIDATION_SCORE, "<"), gate("reentry_score", score >= Decimal(p.REENTRY_WATCH_SCORE), score, p.REENTRY_WATCH_SCORE, ">="), gate("quarantine_clear", not anomaly, str(anomaly).lower(), "false", "is"),
    )


def _state_transition(stage, gates):
    if stage in {CandidateOpportunityStage.WATCH, CandidateOpportunityStage.PREPARE, CandidateOpportunityStage.ENTER} and gates["invalidation"]: return _Transition("active_to_invalidated", CandidateOpportunityStage.INVALIDATED, 1, "candidate_invalidation_condition_fired")
    if stage is None: return _Transition("not_listed_to_watch", CandidateOpportunityStage.WATCH, 1, "watch_entry_gate_passed") if all(gates[x] for x in ("watch_score", "watch_confidence", "price_floor", "liquidity_floor", "quarantine_clear")) else None
    if stage is CandidateOpportunityStage.WATCH: return _Transition("watch_to_prepare", CandidateOpportunityStage.PREPARE, 2, "score_prepare_confirmed") if all(gates[x] for x in ("prepare_score", "regime_not_stress", "relative_strength_prepare", "trend_prepare", "quarantine_clear")) else None
    if stage is CandidateOpportunityStage.PREPARE:
        if all(gates[x] for x in ("breakout_fact", "breakout_score", "regime_not_stress", "quarantine_clear")): return _Transition("prepare_to_enter_breakout", CandidateOpportunityStage.ENTER, 1, "breakout_participation_trigger")
        if all(gates[x] for x in ("enter_score", "price_floor", "liquidity_floor", "quarantine_clear")): return _Transition("prepare_to_enter", CandidateOpportunityStage.ENTER, 2, "score_enter_confirmed")
        if gates["prepare_to_watch"]: return _Transition("prepare_to_watch", CandidateOpportunityStage.WATCH, 2, "prepare_evidence_deteriorated")
    if stage is CandidateOpportunityStage.ENTER and gates["enter_to_prepare"]: return _Transition("enter_to_prepare", CandidateOpportunityStage.PREPARE, 2, "trend_deterioration")
    if stage is CandidateOpportunityStage.INVALIDATED and all(gates[x] for x in ("reentry_score", "price_floor", "liquidity_floor", "quarantine_clear")): return _Transition("invalidated_to_watch", CandidateOpportunityStage.WATCH, 3, "candidate_reentry_confirmation")
    return None


def _anomaly(observation):
    c = observation.candidate
    return c.corporate_action_review_required or c.data_quality_status in {CandidateDataQualityStatus.QUARANTINED, CandidateDataQualityStatus.FAILED} or observation.declared_invalidation_fired


def _pending_required(rule): return 2 if rule in {"watch_to_prepare", "prepare_to_enter", "enter_to_prepare", "prepare_to_watch"} else 3 if rule == "invalidated_to_watch" else 1 if rule else 0
def _state_explanation(status, stage):
    if status is CandidateStateTransitionStatus.INVALIDATED: return "The research candidate is invalidated for review; this is not a sell instruction or an order."
    if stage is CandidateOpportunityStage.ENTER: return "EOD conditions meet the Enter research-candidate gate; this is not an order instruction."
    if stage is CandidateOpportunityStage.PREPARE: return "Several candidate conditions are improving, but an execution trigger is not implied."
    if stage is CandidateOpportunityStage.WATCH: return "The instrument remains a research candidate with evidence still requiring confirmation."
    return "The instrument is not currently assigned an actionable candidate stage."


def _shared_raw_match(raw_by_universe, mismatches):
    universes = sorted(raw_by_universe)
    if len(universes) < 2: return True
    left, right = raw_by_universe[universes[0]], raw_by_universe[universes[1]]
    ok = True
    for instrument_id in sorted(set(left) & set(right), key=str):
        if left[instrument_id].logical_fingerprint != right[instrument_id].logical_fingerprint:
            ok = False; mismatches.append(f"shared_raw_fact:{instrument_id}:fingerprint_mismatch")
    return ok


def _permutation_match(*, panel, batches, regime_context_by_universe, expected):
    reversed_panel = replace(panel, bars=tuple(reversed(panel.bars)))
    for actual in batches:
        score, state = regime_context_by_universe[actual.universe_id]
        permuted, _ = _oracle_batch(panel=reversed_panel, actual=actual, regime_score=None if score is None else Decimal(score), regime_state=None if state is None else RegimeState(state))
        if permuted.logical_fingerprint != expected[actual.universe_id].logical_fingerprint: return False
    return True


def _compare_models(kind, key, actual, expected, mismatches):
    observed, wanted = actual.model_dump(mode="json"), expected.model_dump(mode="json")
    _compare_values(f"{kind}:{key}", observed, wanted, mismatches)


def _compare_values(path, observed, wanted, mismatches):
    if isinstance(observed, dict) and isinstance(wanted, dict):
        if set(observed) != set(wanted): mismatches.append(f"{path}:fields:actual={sorted(observed)}:oracle={sorted(wanted)}")
        for key in sorted(set(observed) & set(wanted)): _compare_values(f"{path}.{key}", observed[key], wanted[key], mismatches)
    elif isinstance(observed, list) and isinstance(wanted, list):
        if len(observed) != len(wanted): mismatches.append(f"{path}:length:actual={len(observed)}:oracle={len(wanted)}")
        for index, (left, right) in enumerate(zip(observed, wanted)): _compare_values(f"{path}[{index}]", left, right, mismatches)
    elif observed != wanted: mismatches.append(f"{path}:actual={observed}:oracle={wanted}")


def _etfs(current):
    registered = {item.ticker for item in ETF_BASKET}; found = defaultdict(list)
    for instrument_id, bar in current.items():
        if bar.instrument_type == "etf" and bar.ticker in registered: found[bar.ticker].append(instrument_id)
    if any(len(ids) != 1 for ids in found.values()): raise ValueError("Oracle rejected ambiguous registered ETF")
    return {ticker: ids[0] for ticker, ids in found.items()}


def _return(bars, sessions, window):
    left, right = bars.get(sessions[-window-1]), bars.get(sessions[-1])
    return None if left is None or right is None or left.close <= ZERO else right.close / left.close - ONE
def _series(bars, sessions, field, minimum):
    values = tuple(getattr(bars[s], field) for s in sessions if s in bars); return values if len(values) >= minimum else None
def _simple_returns(bars, sessions): return tuple(bars[b].close / bars[a].close - ONE for a, b in zip(sessions, sessions[1:]) if a in bars and b in bars and bars[a].close > ZERO)
def _log_returns(bars, sessions):
    values = _simple_returns(bars, sessions); return tuple((ONE+x).ln() for x in values) if len(values) == len(sessions)-1 else None
def _gaps(bars, sessions): return tuple(bars[b].open / bars[a].close - ONE for a, b in zip(sessions, sessions[1:]) if a in bars and b in bars and bars[a].close > ZERO)
def _log_map(bars, sessions): return {b: (bars[b].close / bars[a].close).ln() for a, b in zip(sessions, sessions[1:]) if a in bars and b in bars and bars[a].close > ZERO}
def _correlation(left, right, sessions):
    pairs = tuple((left[s], right[s]) for s in sessions if s in left and s in right); count = len(pairs)
    if count < p.CORRELATION_MINIMUM_OBSERVATIONS: return None, count
    a, b = tuple(x for x, _ in pairs), tuple(y for _, y in pairs); am, bm = _mean(a), _mean(b)
    av, bv = sum((x-am)**2 for x in a), sum((y-bm)**2 for y in b)
    return (None, count) if av == ZERO or bv == ZERO else (sum((x-am)*(y-bm) for x, y in pairs)/(av*bv).sqrt(), count)
def _mean(values): return sum(values, ZERO) / Decimal(len(values))
def _median(values):
    ordered = sorted(values); n = len(ordered); return ordered[n//2] if n%2 else (ordered[n//2-1]+ordered[n//2])/Decimal(2)
def _stdev(values):
    if len(values) < 2: return ZERO
    mean = _mean(values); return (sum((x-mean)**2 for x in values)/Decimal(len(values)-1)).sqrt()
def _drawdown(values):
    peak, worst = values[0], ZERO
    for value in values:
        peak = max(peak, value); worst = min(worst, value/peak-ONE)
    return worst
def _difference(left, right): return None if left is None or right is None else left-right
def _linear(value, low, high): return None if value is None else _clip((value-low)*HUNDRED/(high-low))
def _declining(value, low, high): return None if value is None else HUNDRED-_clip((value-low)*HUNDRED/(high-low))
def _log_linear(value, low, high): return None if value is None or value <= ZERO else _linear(value.log10(), low.log10(), high.log10())
def _clip(value): return min(HUNDRED, max(ZERO, value))
def _quantile(values, probability):
    ordered = tuple(sorted(values)); pos = Decimal(len(ordered)-1)*probability; lower = int(pos.to_integral_value(rounding=ROUND_FLOOR)); fraction = pos-Decimal(lower)
    return ordered[-1] if lower >= len(ordered)-1 else ordered[lower]+fraction*(ordered[lower+1]-ordered[lower])
def _robust(values):
    if not values: return {}
    low, high = _quantile(values.values(), Decimal(p.CROSS_SECTION_WINSOR_LOW)), _quantile(values.values(), Decimal(p.CROSS_SECTION_WINSOR_HIGH))
    wins = {key: min(high, max(low, value)) for key, value in values.items()}; center = _median(tuple(wins.values())); mad = _median(tuple(abs(x-center) for x in wins.values()))
    return _ranks(wins) if mad == ZERO else {key: _clip(Decimal("50")+Decimal(p.CROSS_SECTION_SCORE_SCALE)*Decimal(p.CROSS_SECTION_ROBUST_Z_SCALE)*(value-center)/mad) for key, value in wins.items()}
def _ranks(values):
    if not values: return {}
    if len(set(values.values())) == 1: return {key: Decimal("50") for key in values}
    groups = defaultdict(list)
    for key, value in values.items(): groups[value].append(key)
    output, start, denominator = {}, 1, Decimal(len(values)-1)
    for value in sorted(groups):
        keys = sorted(groups[value], key=str); end = start+len(keys)-1; percentile = HUNDRED*((Decimal(start)+Decimal(end))/Decimal(2)-ONE)/denominator
        for key in keys: output[key] = percentile
        start = end+1
    return output


def _unit(metric):
    if metric == "median_dollar_volume_20": return "usd_proxy"
    if metric == "latest_price": return "usd"
    if metric == "regime_score" or metric in {"close_above_sma10", "up_session_participation"}: return "score"
    return "ratio"
def _evidence(metric):
    if metric in {"current_volume_ratio", "median_dollar_volume_20", "volume_persistence_5", "up_session_participation"}: return "proxy"
    if metric in {"driver_relative_strength_5", "stock_relative_to_driver_5", "driver_correlation_20", "stock_relative_to_spy_5", "stock_relative_to_spy_20", "stock_return_percentile_20"}: return "statistical_inference"
    return "fact"
def _qs(value): return format(value.quantize(SCORE_QUANTUM), "f")
def _qr(value): return format(value.quantize(RAW_QUANTUM), "f")
def _qro(value): return None if value is None else _qr(value)
def _model_fingerprint(model): return _fingerprint(model.model_dump(mode="json", exclude={"logical_fingerprint"}))
def _fingerprint(value): return hashlib.sha256(json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
def _normalize(value):
    if isinstance(value, str): return unicodedata.normalize("NFC", value)
    if isinstance(value, (list, tuple)): return [_normalize(item) for item in value]
    if isinstance(value, dict): return {_normalize(str(key)): _normalize(item) for key, item in value.items()}
    return value
