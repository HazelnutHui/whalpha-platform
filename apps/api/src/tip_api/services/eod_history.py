"""Offline EOD history planning and 20-session trailing-liquidity audit."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from tip_api.contracts.market_data.v1 import (
    EodHistoryMethodologyMode,
    EodHistoryReadinessStatus,
    EodHistoryWindowDescriptorV1,
    EodSessionIntegrityV1,
    HistoricalEodBackfillPlanV1,
    TrailingLiquidityEligibilityStatus,
    TrailingLiquidityResultV1,
)
from tip_api.persistence.eod_read import (
    EodDatasetUnavailableError,
    EodHistorySessionRead,
    EodReadRepository,
    EodSessionNotFoundError,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.market_calendar import MarketSessionCalendar

HISTORY_SESSION_COUNT = 20
CANONICAL_DECIMAL_SCALE = 10
DOLLAR_VOLUME_PRODUCT_SCALE = CANONICAL_DECIMAL_SCALE * 2
PREVIOUS_CLOSE_THRESHOLD = Decimal("5")
MEDIAN_DOLLAR_VOLUME_THRESHOLD = Decimal("20000000")
TRAILING_LIQUIDITY_POLICY_VERSION = "20-session-median-dollar-volume-proxy-v1"
METHODOLOGY_MODE = EodHistoryMethodologyMode.CURRENT_AS_OF_CONSTITUENT_LIQUIDITY
MATERIAL_QUALITY_FLAGS = frozenset({"identity_conflict", "canonical_validation_failure"})


@dataclass(frozen=True, slots=True)
class TrailingLiquidityCoverageAudit:
    requested_instrument_count: int
    observation_count_distribution: tuple[tuple[int, int], ...]
    full_20_of_20_count: int
    nineteen_of_20_count: int
    missing_previous_bar_count: int
    previous_price_gate_pass_count: int
    previous_price_gate_fail_count: int
    insufficient_history_count: int
    zero_volume_observation_count: int
    fractional_volume_observation_count: int
    eligibility_distribution: tuple[tuple[str, int], ...]
    results: tuple[TrailingLiquidityResultV1, ...]
    fingerprint: str


def plan_eod_history_window(
    *,
    analysis_session: date,
    calendar: MarketSessionCalendar,
    repository: EodReadRepository,
) -> tuple[EodHistoryWindowDescriptorV1, tuple[EodSessionIntegrityV1, ...]]:
    expected = calendar.sessions_before(analysis_session, HISTORY_SESSION_COUNT)
    completed: list[date] = []
    missing: list[date] = []
    corrupt: list[date] = []
    integrity: list[EodSessionIntegrityV1] = []
    for session in expected:
        try:
            item = repository.inspect_session(session)
        except EodSessionNotFoundError:
            missing.append(session)
        except EodDatasetUnavailableError:
            corrupt.append(session)
        else:
            completed.append(session)
            integrity.append(item)
    status = (
        EodHistoryReadinessStatus.CORRUPT_OR_UNAVAILABLE if corrupt
        else EodHistoryReadinessStatus.INSUFFICIENT_HISTORY if missing
        else EodHistoryReadinessStatus.READY
    )
    payload = {
        "calendar_name": calendar.calendar_id,
        "calendar_version": calendar.calendar_version,
        "analysis_session": analysis_session.isoformat(),
        "expected_sessions": [item.isoformat() for item in expected],
        "completed_sessions": [item.isoformat() for item in completed],
        "missing_sessions": [item.isoformat() for item in missing],
        "corrupt_sessions": [item.isoformat() for item in corrupt],
        "methodology_mode": METHODOLOGY_MODE.value,
    }
    return (
        EodHistoryWindowDescriptorV1(
            calendar_name=calendar.calendar_id,
            calendar_version=calendar.calendar_version,
            analysis_session=analysis_session,
            previous_session=expected[-1],
            window_start=expected[0],
            window_end=expected[-1],
            expected_session_count=HISTORY_SESSION_COUNT,
            expected_sessions=expected,
            completed_sessions=tuple(completed),
            missing_sessions=tuple(missing),
            corrupt_or_unavailable_sessions=tuple(corrupt),
            readiness_status=status,
            methodology_mode=METHODOLOGY_MODE,
            fingerprint=_fingerprint(payload),
        ),
        tuple(integrity),
    )


def audit_trailing_liquidity(
    *,
    descriptor: EodHistoryWindowDescriptorV1,
    repository: EodReadRepository,
    instrument_ids: frozenset[UUID],
) -> TrailingLiquidityCoverageAudit:
    if descriptor.methodology_mode is not METHODOLOGY_MODE:
        raise ValueError("point-in-time historical panel is defined but not implemented")
    if descriptor.corrupt_or_unavailable_sessions:
        raise EodDatasetUnavailableError("corrupt history window cannot be audited")
    reads = repository.read_history_sessions(descriptor.completed_sessions)
    by_instrument: dict[UUID, dict[date, EodMarketBarReadModel]] = defaultdict(dict)
    source_fingerprints: dict[date, str] = {}
    for session_read in reads:
        session = session_read.integrity.session_date
        source_fingerprints[session] = session_read.integrity.content_fingerprint
        for bar in session_read.bars:
            if bar.instrument_id in by_instrument and session in by_instrument[bar.instrument_id]:
                raise EodDatasetUnavailableError("duplicate instrument/session across history reads")
            by_instrument[bar.instrument_id][session] = bar

    results = tuple(
        _instrument_result(
            instrument_id=instrument_id,
            descriptor=descriptor,
            observations=by_instrument.get(instrument_id, {}),
            source_fingerprints=source_fingerprints,
        )
        for instrument_id in sorted(instrument_ids, key=str)
    )
    observation_distribution = Counter(item.observed_observation_count for item in results)
    eligibility = Counter(item.eligibility_status.value for item in results)
    zero_count = 0
    fractional_count = 0
    for instrument_id in instrument_ids:
        for bar in by_instrument.get(instrument_id, {}).values():
            if bar.volume == 0:
                zero_count += 1
            if bar.volume != bar.volume.to_integral_value():
                fractional_count += 1
    payload = {
        "descriptor": descriptor.fingerprint,
        "instrument_ids": [str(item) for item in sorted(instrument_ids, key=str)],
        "results": [item.fingerprint for item in results],
    }
    return TrailingLiquidityCoverageAudit(
        requested_instrument_count=len(instrument_ids),
        observation_count_distribution=tuple(sorted(observation_distribution.items())),
        full_20_of_20_count=observation_distribution.get(20, 0),
        nineteen_of_20_count=observation_distribution.get(19, 0),
        missing_previous_bar_count=sum(item.price_gate_status == "unavailable" for item in results),
        previous_price_gate_pass_count=sum(item.price_gate_status == "passed" for item in results),
        previous_price_gate_fail_count=sum(item.price_gate_status == "failed" for item in results),
        insufficient_history_count=sum(item.eligibility_status is TrailingLiquidityEligibilityStatus.INSUFFICIENT_HISTORY for item in results),
        zero_volume_observation_count=zero_count,
        fractional_volume_observation_count=fractional_count,
        eligibility_distribution=tuple(sorted(eligibility.items())),
        results=results,
        fingerprint=_fingerprint(payload),
    )


def build_historical_backfill_plan(
    *,
    descriptor: EodHistoryWindowDescriptorV1,
    same_day_identity_resolver_sessions: frozenset[date],
    maximum_batch_size: int = 3,
) -> HistoricalEodBackfillPlanV1:
    """Build a deterministic plan only; this function has no transport boundary."""

    if maximum_batch_size <= 0 or maximum_batch_size > 3:
        raise ValueError("backfill batch size must be between one and three")
    required = descriptor.expected_sessions
    existing = descriptor.completed_sessions
    missing = descriptor.missing_sessions
    corrupt = descriptor.corrupt_or_unavailable_sessions
    same_day = tuple(item for item in required if item in same_day_identity_resolver_sessions)
    identity_needed = tuple(item for item in missing if item not in same_day_identity_resolver_sessions)
    grouped_needed = tuple(missing)
    batches = tuple(
        tuple(grouped_needed[index : index + maximum_batch_size])
        for index in range(0, len(grouped_needed), maximum_batch_size)
    )
    conservative = len(grouped_needed) * 21
    estimated = len(grouped_needed) * 15
    payload = {
        "descriptor": descriptor.fingerprint,
        "same_day_identity": [item.isoformat() for item in same_day],
        "identity_needed": [item.isoformat() for item in identity_needed],
        "grouped_needed": [item.isoformat() for item in grouped_needed],
        "batches": [[item.isoformat() for item in batch] for batch in batches],
        "retry_count": 0,
        "serial_rate_limit_seconds": 15,
    }
    return HistoricalEodBackfillPlanV1(
        analysis_session=descriptor.analysis_session,
        required_eod_sessions=required,
        existing_eod_sessions=existing,
        missing_eod_sessions=missing,
        corrupt_eod_sessions=corrupt,
        same_day_identity_resolver_available=same_day,
        sessions_requiring_identity_acquisition=identity_needed,
        sessions_requiring_grouped_daily_acquisition=grouped_needed,
        per_session_request_ceiling=21,
        conservative_request_ceiling=conservative,
        estimated_request_range=(estimated, conservative),
        chronological_batch_plan=batches,
        resume_idempotency_policy=(
            "reuse completed same-day identity and EOD partitions; never overwrite completed targets; "
            "resume at the first missing component after manifest and fingerprint validation"
        ),
        methodology_mode=METHODOLOGY_MODE,
        plan_fingerprint=_fingerprint(payload),
        status="planning_only_not_authorized" if not corrupt else "blocked_by_corrupt_partition",
    )


def fixed_scale_coefficient(value: Decimal, *, scale: int) -> int:
    """Return an exact integer coefficient without consulting Decimal context."""

    if not value.is_finite():
        raise ValueError("a finite Decimal is required")
    sign, digits, exponent = value.as_tuple()
    coefficient = 0
    for digit in digits:
        coefficient = coefficient * 10 + digit
    if sign:
        coefficient = -coefficient
    shift = exponent + scale
    if shift >= 0:
        return coefficient * (10 ** shift)
    divisor = 10 ** (-shift)
    quotient, remainder = divmod(abs(coefficient), divisor)
    if remainder:
        raise ValueError(f"Decimal cannot be represented exactly at scale {scale}")
    return -quotient if coefficient < 0 else quotient


def decimal_coefficient_and_scale(value: Decimal) -> tuple[int, int]:
    """Return an exact coefficient/scale pair without Decimal arithmetic."""

    if not value.is_finite():
        raise ValueError("a finite Decimal is required")
    sign, digits, exponent = value.as_tuple()
    coefficient = 0
    for digit in digits:
        coefficient = coefficient * 10 + digit
    if sign:
        coefficient = -coefficient
    if exponent >= 0:
        return coefficient * (10 ** exponent), 0
    return coefficient, -exponent


def decimal_from_scaled_coefficient(coefficient: int, *, scale: int) -> Decimal:
    """Rebuild Decimal from an integer tuple, independent of global context."""

    if scale < 0:
        raise ValueError("scale must not be negative")
    sign = 1 if coefficient < 0 else 0
    digits = tuple(int(character) for character in str(abs(coefficient)))
    return Decimal((sign, digits, -scale))


def exact_dollar_volume_proxy(close: Decimal, volume: Decimal) -> Decimal:
    """Multiply Decimal values with arbitrary-size integers and exact scale."""

    close_coefficient, close_scale = decimal_coefficient_and_scale(close)
    volume_coefficient, volume_scale = decimal_coefficient_and_scale(volume)
    return decimal_from_scaled_coefficient(
        close_coefficient * volume_coefficient,
        scale=close_scale + volume_scale,
    )


def exact_even_median(values: Iterable[Decimal]) -> Decimal:
    coefficient_scales = tuple(decimal_coefficient_and_scale(value) for value in values)
    if len(coefficient_scales) != HISTORY_SESSION_COUNT:
        raise ValueError("20 observations are required for the 20-session median")
    common_scale = max(scale for _, scale in coefficient_scales)
    coefficients = sorted(
        coefficient * (10 ** (common_scale - scale))
        for coefficient, scale in coefficient_scales
    )
    middle_sum = coefficients[9] + coefficients[10]
    if middle_sum % 2 == 0:
        return decimal_from_scaled_coefficient(middle_sum // 2, scale=common_scale)
    return decimal_from_scaled_coefficient(middle_sum * 5, scale=common_scale + 1)


def _instrument_result(
    *,
    instrument_id: UUID,
    descriptor: EodHistoryWindowDescriptorV1,
    observations: dict[date, EodMarketBarReadModel],
    source_fingerprints: dict[date, str],
) -> TrailingLiquidityResultV1:
    ordered_bars = [observations[item] for item in descriptor.expected_sessions if item in observations]
    previous = observations.get(descriptor.previous_session)
    reason_codes = {"adjustment_factors_unverified"}
    quality_failure = any(MATERIAL_QUALITY_FLAGS.intersection(bar.quality_flags) for bar in ordered_bars)
    if previous is None:
        price_status = "unavailable"
        eligibility = TrailingLiquidityEligibilityStatus.MISSING_PREVIOUS_BAR
        reason_codes.add("missing_previous_bar")
    elif previous.close < PREVIOUS_CLOSE_THRESHOLD:
        price_status = "failed"
        eligibility = TrailingLiquidityEligibilityStatus.INSUFFICIENT_HISTORY
        reason_codes.add("previous_close_below_5")
    else:
        price_status = "passed"
        eligibility = TrailingLiquidityEligibilityStatus.INSUFFICIENT_HISTORY

    median: Decimal | None = None
    liquidity_status = "unavailable"
    if quality_failure:
        eligibility = TrailingLiquidityEligibilityStatus.DATA_QUALITY_FAILURE
        reason_codes.add("material_data_quality_flag")
    elif len(ordered_bars) < HISTORY_SESSION_COUNT:
        if previous is not None:
            eligibility = TrailingLiquidityEligibilityStatus.INSUFFICIENT_HISTORY
        reason_codes.add("insufficient_20_session_history")
    elif previous is not None and previous.close < PREVIOUS_CLOSE_THRESHOLD:
        eligibility = TrailingLiquidityEligibilityStatus.BELOW_PRICE_THRESHOLD
    elif previous is not None:
        median = exact_even_median(exact_dollar_volume_proxy(bar.close, bar.volume) for bar in ordered_bars)
        if median >= MEDIAN_DOLLAR_VOLUME_THRESHOLD:
            liquidity_status = "passed"
            eligibility = TrailingLiquidityEligibilityStatus.PASSED
        else:
            liquidity_status = "failed"
            eligibility = TrailingLiquidityEligibilityStatus.BELOW_LIQUIDITY_THRESHOLD
            reason_codes.add("median_dollar_volume_below_20m")
    source = tuple(
        (session, source_fingerprints[session])
        for session in descriptor.expected_sessions
        if session in observations and session in source_fingerprints
    )
    payload = {
        "instrument_id": str(instrument_id),
        "analysis_session": descriptor.analysis_session.isoformat(),
        "window": [descriptor.window_start.isoformat(), descriptor.window_end.isoformat()],
        "observed": len(ordered_bars),
        "median": str(median) if median is not None else None,
        "price": price_status,
        "liquidity": liquidity_status,
        "eligibility": eligibility.value,
        "reasons": sorted(reason_codes),
        "source": [(item.isoformat(), fingerprint) for item, fingerprint in source],
        "policy": TRAILING_LIQUIDITY_POLICY_VERSION,
    }
    return TrailingLiquidityResultV1(
        instrument_id=instrument_id,
        analysis_session=descriptor.analysis_session,
        window_start=descriptor.window_start,
        window_end=descriptor.window_end,
        observed_observation_count=len(ordered_bars),
        missing_observation_count=HISTORY_SESSION_COUNT - len(ordered_bars),
        median_dollar_volume_proxy=median,
        threshold=MEDIAN_DOLLAR_VOLUME_THRESHOLD,
        price_gate_status=price_status,
        liquidity_gate_status=liquidity_status,
        eligibility_status=eligibility,
        reason_codes=tuple(sorted(reason_codes)),
        source_session_fingerprints=source,
        methodology_mode=METHODOLOGY_MODE,
        policy_version=TRAILING_LIQUIDITY_POLICY_VERSION,
        fingerprint=_fingerprint(payload),
    )


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
