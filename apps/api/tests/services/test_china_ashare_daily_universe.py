from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareBoard,
    ChinaAshareDailyBarV1,
    ChinaAshareDailyTradingStateV1,
    ChinaAshareExchange,
    ChinaAshareListedLifecycleDecisionV1,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareSecurityForm,
    ChinaAshareTradingStatus,
    ChinaAshareUniverseDisposition,
    build_research_instrument_identity,
)
from tip_api.contracts.common import QualityStatus
from tip_api.persistence.china_ashare_daily_universe_package import (
    ChinaAshareDailyUniversePackageCorruptionError,
    publish_china_ashare_daily_universe_package,
    read_china_ashare_daily_universe_package,
)
from tip_api.services.china_ashare_daily_universe import (
    build_daily_universe_for_pilot,
)


NOW = datetime(2026, 9, 17, tzinfo=UTC)
INGESTED = datetime(2026, 9, 16, 23, 45, tzinfo=UTC)
DAILY_FP = "d" * 64
IDENTITY_PACKAGE_FP = "e" * 64


def test_daily_universe_partitions_every_instrument_session(tmp_path) -> None:
    identity = _identity()
    sessions = (date(2026, 9, 14), date(2026, 9, 15), date(2026, 9, 16))
    states = (
        _state(identity.instrument_id, sessions[0], ChinaAshareTradingStatus.TRADING),
        _state(identity.instrument_id, sessions[1], ChinaAshareTradingStatus.SUSPENDED),
        _state(
            identity.instrument_id,
            sessions[2],
            ChinaAshareTradingStatus.TRADING,
            ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED,
        ),
    )
    daily = SimpleNamespace(
        manifest=SimpleNamespace(logical_fingerprint=DAILY_FP),
        captured=SimpleNamespace(
            daily_batch=SimpleNamespace(
                trading_states=states,
                bars=(
                    _bar(identity.instrument_id, sessions[0]),
                    _bar(identity.instrument_id, sessions[2]),
                ),
            )
        ),
    )
    lifecycle = ChinaAshareListedLifecycleDecisionV1(
        instrument_id=identity.instrument_id,
        source_security_id=identity.source_security_id,
        interval_start=sessions[0],
        interval_end=sessions[-1],
        listing_date=identity.listing_date,
        current_list_observed_as_of=date(2026, 9, 17),
        expected_session_count=3,
        observed_state_count=3,
        trading_or_suspended_state_count=3,
        not_listed_state_count=0,
        unknown_state_count=0,
        security_termination_event_count=0,
        issuer_only_event_count=0,
        state_dates_complete=True,
        listed_interval_complete=True,
        quality_status=QualityStatus.VALID,
        evidence_fingerprints=("a" * 64,),
        reason_codes=("listed_interval_reconciled",),
    )
    identity_package = SimpleNamespace(
        manifest=SimpleNamespace(logical_fingerprint=IDENTITY_PACKAGE_FP),
        report=SimpleNamespace(
            daily_package_fingerprint=DAILY_FP,
            stable_identity_family_complete=True,
            lifecycle_family_complete=True,
        ),
        identities=(identity,),
        lifecycle_decisions=(lifecycle,),
    )

    decisions, report = build_daily_universe_for_pilot(
        daily_package=daily,
        identity_lifecycle_package=identity_package,
        evaluated_at=NOW,
    )

    assert [item.disposition for item in decisions] == [
        ChinaAshareUniverseDisposition.INCLUDED,
        ChinaAshareUniverseDisposition.INCLUDED,
        ChinaAshareUniverseDisposition.EXCLUDED,
    ]
    assert [item.performance_eligible for item in decisions] == [True, False, False]
    assert report.decision_count == 3
    assert report.quarantined_count == 0
    assert report.daily_universe_family_complete is True
    assert report.research_backtest_authorized is False

    result = publish_china_ashare_daily_universe_package(
        custody_root=tmp_path,
        decisions=decisions,
        report=report,
        created_at=NOW,
    )
    reread = read_china_ashare_daily_universe_package(
        package_path=result.package_path
    )
    assert reread.decisions == decisions
    assert reread.report == report
    assert reread.file_count == 3

    report_path = result.package_path / "daily-universe-report.json"
    report_path.write_bytes(b"changed")
    with pytest.raises(
        ChinaAshareDailyUniversePackageCorruptionError,
        match="report bytes changed",
    ):
        read_china_ashare_daily_universe_package(package_path=result.package_path)


def _identity():
    return build_research_instrument_identity(
        source_security_id="sh.600519",
        display_ticker="600519.SH",
        current_name="贵州茅台",
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        security_form=ChinaAshareSecurityForm.COMMON_STOCK,
        listing_date=date(2001, 8, 27),
        alias_valid_from=date(2001, 8, 27),
        official_observation_fingerprint="a" * 64,
        baostock_observation_fingerprint="b" * 64,
        pilot_decision_fingerprint="c" * 64,
        append_only=True,
        ticker_is_permanent_key=False,
        reason_codes=("listed_occurrence_keyed",),
        canonical_apply_authorized=False,
    )


def _state(
    instrument_id,
    session_date,
    trading_status,
    risk_warning_status=ChinaAshareRiskWarningStatus.NONE,
):
    return ChinaAshareDailyTradingStateV1(
        instrument_id=instrument_id,
        session_date=session_date,
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        trading_status=trading_status,
        risk_warning_status=risk_warning_status,
        price_limit_regime=ChinaAsharePriceLimitRegime.PERCENT_10,
        exact_limit_prices_source_observed=False,
        source="test",
        ingested_at=INGESTED,
        quality_status=QualityStatus.WARNING,
        reason_codes=("test_state",),
    )


def _bar(instrument_id, session_date):
    return ChinaAshareDailyBarV1(
        instrument_id=instrument_id,
        session_date=session_date,
        open=Decimal("10"),
        high=Decimal("10"),
        low=Decimal("10"),
        close=Decimal("10"),
        pre_close=Decimal("10"),
        volume_shares=Decimal("100"),
        turnover_amount_cny=Decimal("1000"),
        source="test",
        ingested_at=INGESTED,
        revision=1,
        quality_status=QualityStatus.VALID,
    )
