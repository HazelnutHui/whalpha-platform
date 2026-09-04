from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, Rounded, localcontext
import socket
from uuid import UUID, uuid5

import pytest

from tip_api.contracts.market_data.v1 import (
    EodHistoryMethodologyMode,
    EodHistoryReadinessStatus,
    EodSessionIntegrityV1,
    InstrumentType,
    QualityStatus,
    TrailingLiquidityEligibilityStatus,
)
from tip_api.persistence.eod_read import EodDatasetUnavailableError, EodHistorySessionRead, EodSessionNotFoundError
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.eod_history import (
    audit_trailing_liquidity,
    build_historical_backfill_plan,
    describe_eod_history_window,
    exact_dollar_volume_proxy,
    exact_even_median,
    plan_eod_history_window,
)
from tip_api.services.market_calendar import ExchangeCalendar

ANALYSIS = date(2026, 8, 14)
NS = UUID("00000000-0000-4000-8000-000000000188")


def iid(value: str) -> UUID:
    return uuid5(NS, value)


def integrity(session: date, fingerprint: str | None = None) -> EodSessionIntegrityV1:
    return EodSessionIntegrityV1(
        session_date=session, record_count=1, content_fingerprint=fingerprint or f"{session.day:064x}",
        parquet_sha256="a" * 64, identity_snapshot_date=session,
        identity_snapshot_fingerprint="b" * 64, duplicate_instrument_session_count=0,
        multiple_latest_revision_count=0, future_identity_reference_count=0,
    )


def bar(instrument: UUID, session: date, *, ticker: str = "TEST", close: str = "5", volume: str = "4000000", flags: tuple[str, ...] = ("adjustment_factors_unverified",)) -> EodMarketBarReadModel:
    price = Decimal(close)
    return EodMarketBarReadModel(
        instrument_id=instrument, ticker=ticker, name=ticker, instrument_type=InstrumentType.COMMON_STOCK,
        primary_exchange="XNYS", session_date=session, open=price, high=price, low=price, close=price,
        volume=Decimal(volume), vwap=None, trade_count=None, currency="USD", source="fixture",
        quality_status=QualityStatus.WARNING if flags else QualityStatus.VALID, quality_flags=flags,
    )


@dataclass
class FakeRepository:
    sessions: dict[date, tuple[EodMarketBarReadModel, ...]]
    corrupt: frozenset[date] = frozenset()
    requested: tuple[date, ...] = ()

    def inspect_session(self, session: date):
        if session in self.corrupt:
            raise EodDatasetUnavailableError("corrupt")
        if session not in self.sessions:
            raise EodSessionNotFoundError("missing")
        return integrity(session)

    def read_history_sessions(self, dates: tuple[date, ...]):
        self.requested = dates
        return tuple(EodHistorySessionRead(integrity(day), self.sessions[day]) for day in dates)

    def list_sessions(self):
        raise AssertionError("window planner must not scan unrelated partitions")

    def read_bars(self, session_date: date):
        raise AssertionError("history audit must use the multi-session boundary")


@pytest.fixture(scope="module")
def calendar() -> ExchangeCalendar:
    return ExchangeCalendar()


def test_xnys_20_session_window_excludes_analysis_day(calendar: ExchangeCalendar) -> None:
    sessions = calendar.sessions_before(ANALYSIS, 20)
    assert sessions[0] == date(2026, 7, 17)
    assert sessions[-1] == date(2026, 8, 13)
    assert ANALYSIS not in sessions
    assert len(sessions) == 20
    assert date(2026, 7, 19) not in sessions


def test_current_window_has_two_completed_and_eighteen_missing(calendar: ExchangeCalendar) -> None:
    repository = FakeRepository({date(2026, 8, 12): (), date(2026, 8, 13): (), date(2026, 8, 14): ()})
    descriptor, session_integrity = plan_eod_history_window(analysis_session=ANALYSIS, calendar=calendar, repository=repository)
    assert descriptor.completed_sessions == (date(2026, 8, 12), date(2026, 8, 13))
    assert len(descriptor.missing_sessions) == 18
    assert descriptor.readiness_status is EodHistoryReadinessStatus.INSUFFICIENT_HISTORY
    assert len(session_integrity) == 2


def test_preloaded_descriptor_exactly_matches_repository_planning(
    calendar: ExchangeCalendar,
) -> None:
    sessions = calendar.sessions_before(ANALYSIS, 20)
    repository = FakeRepository({item: () for item in sessions})
    planned, planned_integrity = plan_eod_history_window(
        analysis_session=ANALYSIS,
        calendar=calendar,
        repository=repository,
    )

    described, described_integrity = describe_eod_history_window(
        analysis_session=ANALYSIS,
        calendar=calendar,
        completed_integrity=tuple(reversed(planned_integrity)),
    )

    assert described == planned
    assert described_integrity == planned_integrity


def test_preloaded_descriptor_rejects_incomplete_evidence_partition(
    calendar: ExchangeCalendar,
) -> None:
    sessions = calendar.sessions_before(ANALYSIS, 20)
    with pytest.raises(ValueError, match="exactly partition"):
        describe_eod_history_window(
            analysis_session=ANALYSIS,
            calendar=calendar,
            completed_integrity=tuple(integrity(item) for item in sessions[:-1]),
        )


def test_present_corrupt_partition_is_distinct_and_blocks_audit(calendar: ExchangeCalendar) -> None:
    repository = FakeRepository({}, frozenset({date(2026, 8, 13)}))
    descriptor, _ = plan_eod_history_window(analysis_session=ANALYSIS, calendar=calendar, repository=repository)
    assert descriptor.corrupt_or_unavailable_sessions == (date(2026, 8, 13),)
    assert descriptor.readiness_status is EodHistoryReadinessStatus.CORRUPT_OR_UNAVAILABLE
    with pytest.raises(EodDatasetUnavailableError):
        audit_trailing_liquidity(descriptor=descriptor, repository=repository, instrument_ids=frozenset({iid("A")}))


def complete_repository(calendar: ExchangeCalendar, instrument: UUID, *, close: str = "5", volumes: tuple[str, ...] | None = None, ticker_prefix: str = "T"):
    sessions = calendar.sessions_before(ANALYSIS, 20)
    volumes = volumes or tuple("4000000" for _ in sessions)
    return FakeRepository({day: (bar(instrument, day, ticker=f"{ticker_prefix}{index}", close=close, volume=volumes[index]),) for index, day in enumerate(sessions)})


def descriptor_for(repository: FakeRepository, calendar: ExchangeCalendar):
    return plan_eod_history_window(analysis_session=ANALYSIS, calendar=calendar, repository=repository)[0]


def test_exact_even_decimal_median_and_threshold_boundaries(calendar: ExchangeCalendar) -> None:
    assert exact_even_median(tuple(Decimal(index) for index in range(1, 21))) == Decimal("10.5")
    instrument = iid("EDGE")
    repository = complete_repository(calendar, instrument)
    result = audit_trailing_liquidity(descriptor=descriptor_for(repository, calendar), repository=repository, instrument_ids=frozenset({instrument})).results[0]
    assert result.median_dollar_volume_proxy == Decimal("20000000.0000000000")
    assert result.price_gate_status == "passed"
    assert result.eligibility_status is TrailingLiquidityEligibilityStatus.PASSED


@pytest.mark.parametrize("precision", (9, 28, 50))
@pytest.mark.parametrize("rounding", (ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP))
def test_dollar_volume_and_median_ignore_global_decimal_context(precision: int, rounding: str) -> None:
    close = Decimal("1234567890123456789012345678.1234567890")
    volume = Decimal("8765432109876543210987654321.9876543210")
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        product = exact_dollar_volume_proxy(close, volume)
        median = exact_even_median((product,) * 20)
    expected_coefficient = 12345678901234567890123456781234567890 * 87654321098765432109876543219876543210
    assert product.as_tuple() == Decimal((0, tuple(map(int, str(expected_coefficient))), -20)).as_tuple()
    assert median.as_tuple() == product.as_tuple()


def test_odd_middle_coefficient_adds_scale_without_rounding() -> None:
    values = tuple(Decimal(index).scaleb(-20) for index in range(1, 21))
    with localcontext() as context:
        context.prec = 9
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        result = exact_even_median(values)
    assert result.as_tuple() == Decimal("0.000000000000000000105").as_tuple()


def test_smallest_scale20_units_straddle_liquidity_threshold() -> None:
    threshold = Decimal("20000000.00000000000000000000")
    below = Decimal("19999999.99999999999999999999")
    above = Decimal("20000000.00000000000000000001")
    assert threshold >= Decimal("20000000")
    assert below < Decimal("20000000")
    assert above > Decimal("20000000")


def test_nineteen_of_twenty_is_insufficient_and_never_filled(calendar: ExchangeCalendar) -> None:
    instrument = iid("NINETEEN")
    repository = complete_repository(calendar, instrument)
    missing_day = calendar.sessions_before(ANALYSIS, 20)[0]
    repository.sessions.pop(missing_day)
    descriptor = descriptor_for(repository, calendar)
    audit = audit_trailing_liquidity(descriptor=descriptor, repository=repository, instrument_ids=frozenset({instrument}))
    result = audit.results[0]
    assert result.observed_observation_count == 19 and result.missing_observation_count == 1
    assert result.median_dollar_volume_proxy is None
    assert result.eligibility_status is TrailingLiquidityEligibilityStatus.INSUFFICIENT_HISTORY


def test_missing_previous_bar_differs_from_real_zero_volume(calendar: ExchangeCalendar) -> None:
    instrument = iid("MISSING")
    repository = complete_repository(calendar, instrument)
    repository.sessions.pop(date(2026, 8, 13))
    missing = audit_trailing_liquidity(descriptor=descriptor_for(repository, calendar), repository=repository, instrument_ids=frozenset({instrument}))
    assert missing.results[0].eligibility_status is TrailingLiquidityEligibilityStatus.MISSING_PREVIOUS_BAR

    zero = complete_repository(calendar, instrument, volumes=tuple("0" for _ in range(20)))
    zero_audit = audit_trailing_liquidity(descriptor=descriptor_for(zero, calendar), repository=zero, instrument_ids=frozenset({instrument}))
    assert zero_audit.zero_volume_observation_count == 20
    assert zero_audit.results[0].median_dollar_volume_proxy == Decimal(0)
    assert zero_audit.results[0].eligibility_status is TrailingLiquidityEligibilityStatus.BELOW_LIQUIDITY_THRESHOLD


def test_fractional_volume_and_large_decimal_precision_are_preserved(calendar: ExchangeCalendar) -> None:
    instrument = iid("FRACTION")
    values = tuple("4000000.0000000001" for _ in range(20))
    repository = complete_repository(calendar, instrument, volumes=values)
    audit = audit_trailing_liquidity(descriptor=descriptor_for(repository, calendar), repository=repository, instrument_ids=frozenset({instrument}))
    assert audit.fractional_volume_observation_count == 20
    assert audit.results[0].median_dollar_volume_proxy == Decimal("20000000.00000000050000000000")


def test_below_exact_price_and_liquidity_boundaries(calendar: ExchangeCalendar) -> None:
    low_price = iid("LOWPRICE")
    price_repository = complete_repository(calendar, low_price, close="4.9999999999")
    price = audit_trailing_liquidity(descriptor=descriptor_for(price_repository, calendar), repository=price_repository, instrument_ids=frozenset({low_price})).results[0]
    assert price.eligibility_status is TrailingLiquidityEligibilityStatus.BELOW_PRICE_THRESHOLD

    illiquid = iid("ILLIQUID")
    liquid_repository = complete_repository(calendar, illiquid, volumes=tuple("3999999.9999999999" for _ in range(20)))
    liquidity = audit_trailing_liquidity(descriptor=descriptor_for(liquid_repository, calendar), repository=liquid_repository, instrument_ids=frozenset({illiquid})).results[0]
    assert liquidity.eligibility_status is TrailingLiquidityEligibilityStatus.BELOW_LIQUIDITY_THRESHOLD


def test_analysis_day_volume_never_affects_eligibility(calendar: ExchangeCalendar) -> None:
    instrument = iid("NOLOOKAHEAD")
    repository = complete_repository(calendar, instrument)
    repository.sessions[ANALYSIS] = (bar(instrument, ANALYSIS, volume="999999999999999999"),)
    descriptor = descriptor_for(repository, calendar)
    first = audit_trailing_liquidity(descriptor=descriptor, repository=repository, instrument_ids=frozenset({instrument}))
    repository.sessions[ANALYSIS] = (bar(instrument, ANALYSIS, volume="0"),)
    second = audit_trailing_liquidity(descriptor=descriptor, repository=repository, instrument_ids=frozenset({instrument}))
    assert repository.requested == descriptor.completed_sessions
    assert first.fingerprint == second.fingerprint


def test_stable_id_survives_ticker_change_and_ticker_reuse_does_not_merge(calendar: ExchangeCalendar) -> None:
    first, second = iid("FIRST"), iid("SECOND")
    sessions = calendar.sessions_before(ANALYSIS, 20)
    repository = FakeRepository({
        day: (
            bar(first, day, ticker="OLD" if index < 10 else "NEW"),
            bar(second, day, ticker="OLD"),
        )
        for index, day in enumerate(sessions)
    })
    audit = audit_trailing_liquidity(descriptor=descriptor_for(repository, calendar), repository=repository, instrument_ids=frozenset({first, second}))
    assert {item.instrument_id for item in audit.results} == {first, second}
    assert all(item.observed_observation_count == 20 for item in audit.results)


def test_permutation_is_deterministic_for_candidate_coverage(calendar: ExchangeCalendar) -> None:
    ids = (iid("A"), iid("B"))
    sessions = calendar.sessions_before(ANALYSIS, 20)
    rows = {day: tuple(bar(item, day) for item in ids) for day in sessions}
    first_repo = FakeRepository(rows)
    second_repo = FakeRepository({day: tuple(reversed(values)) for day, values in reversed(tuple(rows.items()))})
    first = audit_trailing_liquidity(descriptor=descriptor_for(first_repo, calendar), repository=first_repo, instrument_ids=frozenset(ids))
    second = audit_trailing_liquidity(descriptor=descriptor_for(second_repo, calendar), repository=second_repo, instrument_ids=frozenset(reversed(ids)))
    assert first.fingerprint == second.fingerprint


def test_preloaded_formal_reads_avoid_duplicate_partition_reads(calendar: ExchangeCalendar) -> None:
    instrument = iid("PRELOADED")
    repository = complete_repository(calendar, instrument)
    descriptor = descriptor_for(repository, calendar)
    reads = tuple(
        EodHistorySessionRead(integrity(day), repository.sessions[day])
        for day in descriptor.completed_sessions
    )

    audit = audit_trailing_liquidity(
        descriptor=descriptor,
        repository=repository,
        instrument_ids=frozenset({instrument}),
        session_reads=reads,
    )

    assert repository.requested == ()
    assert audit.results[0].eligibility_status is TrailingLiquidityEligibilityStatus.PASSED


def test_backfill_plan_is_chronological_batched_and_never_uses_latest_resolver(calendar: ExchangeCalendar) -> None:
    repository = FakeRepository({date(2026, 8, 12): (), date(2026, 8, 13): ()})
    descriptor = descriptor_for(repository, calendar)
    plan = build_historical_backfill_plan(
        descriptor=descriptor,
        same_day_identity_resolver_sessions=frozenset({date(2026, 8, 12), date(2026, 8, 13), date(2026, 8, 14)}),
    )
    assert len(plan.sessions_requiring_identity_acquisition) == 18
    assert len(plan.sessions_requiring_grouped_daily_acquisition) == 18
    assert plan.estimated_request_range == (270, 378)
    assert plan.conservative_request_ceiling == 378 and plan.per_session_request_ceiling == 21
    assert len(plan.chronological_batch_plan) == 6 and all(len(batch) <= 3 for batch in plan.chronological_batch_plan)
    assert date(2026, 8, 14) not in plan.same_day_identity_resolver_available
    assert "latest" not in plan.resume_idempotency_policy
    assert plan.status == "planning_only_not_authorized"


def test_point_in_time_mode_is_distinct_but_not_implemented() -> None:
    assert EodHistoryMethodologyMode.POINT_IN_TIME_HISTORICAL_PANEL.value == "point_in_time_historical_panel"
    assert EodHistoryMethodologyMode.CURRENT_AS_OF_CONSTITUENT_LIQUIDITY.value == "current_as_of_constituent_liquidity"


def test_planner_and_audit_never_use_network_or_credentials(calendar: ExchangeCalendar, monkeypatch: pytest.MonkeyPatch) -> None:
    import tip_api.providers.massive.credential as credential

    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: pytest.fail("network attempted"))
    monkeypatch.setattr(credential, "load_massive_provider_config_from_file", lambda *args, **kwargs: pytest.fail("credential called"))
    instrument = iid("OFFLINE")
    repository = complete_repository(calendar, instrument)
    descriptor = descriptor_for(repository, calendar)
    audit = audit_trailing_liquidity(descriptor=descriptor, repository=repository, instrument_ids=frozenset({instrument}))
    plan = build_historical_backfill_plan(descriptor=descriptor, same_day_identity_resolver_sessions=frozenset(descriptor.expected_sessions))
    assert audit.results[0].eligibility_status is TrailingLiquidityEligibilityStatus.PASSED
    assert not plan.sessions_requiring_grouped_daily_acquisition
