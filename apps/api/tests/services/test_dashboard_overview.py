from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from tip_api.contracts.market_data.v1 import InstrumentType, QualityStatus
from tip_api.persistence.eod_read import EodReadRepository, EodSessionNotFoundError
from tip_api.read_models.eod import EodMarketBarReadModel, EodSessionDescriptor
from tip_api.services.dashboard_overview import DashboardOverviewService
from tip_api.services.eod_market_data import EodMarketDataQueryService
from tip_api.contracts.market_data.v1.dashboard_universe_activation import DashboardUniverseActivationDatasetReferenceV1, DashboardUniverseActivationManifestV1, DashboardUniverseActivationRecordV1, SecurityTypeCountV1
from tip_api.persistence.parquet.dashboard_universe_activation import CompletedDashboardUniverseActivation, PUBLIC_SECONDARY_ID
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID

CURRENT = date(2026, 8, 13)
PREVIOUS = date(2026, 8, 12)
CREATED = datetime(2026, 8, 14, tzinfo=UTC)


def uid(n: int) -> UUID:
    return UUID(f"00000000-0000-5000-8000-3000000000{n:02d}")


def bar(n: int, ticker: str, close: str, volume: str, session: date, *, instrument_type=InstrumentType.COMMON_STOCK, exchange="XNYS", flags=()):
    value = Decimal(close)
    return EodMarketBarReadModel(
        instrument_id=uid(n),
        ticker=ticker,
        name=f"{ticker} Synthetic Corp",
        instrument_type=instrument_type,
        primary_exchange=exchange,
        session_date=session,
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Decimal(volume),
        vwap=None,
        trade_count=None,
        currency="USD",
        source="fixture",
        quality_status=QualityStatus.VALID,
        quality_flags=flags,
    )


class FakeRepo(EodReadRepository):
    def __init__(self, sessions):
        self.sessions = sessions

    def list_sessions(self):
        return tuple(EodSessionDescriptor("1.0", session, len(rows), "completed", session, CREATED, 0) for session, rows in sorted(self.sessions.items()))

    def read_bars(self, session_date):
        try:
            return self.sessions[session_date]
        except KeyError as exc:
            raise EodSessionNotFoundError("missing") from exc


def service(current, previous):
    activated=datetime(2026,8,15,tzinfo=UTC); sha="a"*64
    records=(
        DashboardUniverseActivationRecordV1(activation_id=uid(90),analysis_session=CURRENT,membership_evidence_as_of=PREVIOUS,activated_at=activated,universe_id=CANDIDATE_A_ID,display_name="Common Shares",long_display_name="Provider-Classified Common Shares (Provisional)",description="Fixture common shares",is_default=True,member_count=2,security_type_composition=(SecurityTypeCountV1(provider_type_code="CS",count=2),),membership_fingerprint=sha,trailing_liquidity_source_fingerprint=sha,reviewed_override_source_fingerprint=sha,pre_activation_review_fingerprint=sha,current_eod_fingerprint=sha,previous_eod_fingerprint=sha,legacy_rollback_reference="market-data/snapshots/legacy",limitations=("fixture",)),
        DashboardUniverseActivationRecordV1(activation_id=uid(91),analysis_session=CURRENT,membership_evidence_as_of=PREVIOUS,activated_at=activated,universe_id=PUBLIC_SECONDARY_ID,display_name="Common Shares + ADRs",long_display_name="Provider-Classified Common Shares + ADRs",description="Fixture ADR view",is_default=False,member_count=3,security_type_composition=(SecurityTypeCountV1(provider_type_code="CS",count=2),SecurityTypeCountV1(provider_type_code="ADRC",count=1)),membership_fingerprint=sha,trailing_liquidity_source_fingerprint=sha,reviewed_override_source_fingerprint=sha,pre_activation_review_fingerprint=sha,current_eod_fingerprint=sha,previous_eod_fingerprint=sha,legacy_rollback_reference="market-data/snapshots/legacy",limitations=("fixture",)),
    )
    manifest=DashboardUniverseActivationManifestV1(policy_version="dashboard-universe-v1",analysis_session=CURRENT,membership_evidence_as_of=PREVIOUS,trailing_window_start=date(2026,7,22),trailing_window_end=date(2026,8,18),trailing_window_session_count=20,reviewed_override_count=2,activated_at=activated,default_universe_id=CANDIDATE_A_ID,available_universe_ids=(CANDIDATE_A_ID,PUBLIC_SECONDARY_ID),activation_dataset=DashboardUniverseActivationDatasetReferenceV1(dataset_path="fixture",record_count=2,content_fingerprint=sha,parquet_sha256=sha),pre_activation_review_path="fixture",pre_activation_review_fingerprint=sha,legacy_member_count=3,legacy_membership_fingerprint=sha,logical_content_fingerprint=sha)
    activation=CompletedDashboardUniverseActivation(manifest,records,{CANDIDATE_A_ID:frozenset({uid(1),uid(6)}),PUBLIC_SECONDARY_ID:frozenset({uid(1),uid(3),uid(6)})})
    return DashboardOverviewService(
        EodMarketDataQueryService(FakeRepo({PREVIOUS: previous, CURRENT: current})),
        activation,
        clock=lambda: datetime(2026, 8, 15, 18, tzinfo=UTC),
    )


def base_rows():
    previous = (
        bar(1, "TESTA", "20", "2000000", PREVIOUS),
        bar(2, "TESTB", "4.99", "10000000", PREVIOUS),
        bar(3, "TESTC", "30", "100000", PREVIOUS),
        bar(4, "TESTD", "25", "2000000", PREVIOUS, exchange="OTCM"),
        bar(5, "TESTE", "50", "1000000", PREVIOUS, instrument_type=InstrumentType.ETF),
        bar(6, "TESTF", "10", "3000000", PREVIOUS),
        bar(7, "XLC", "80", "1000000", PREVIOUS, instrument_type=InstrumentType.ETF),
        bar(8, "SPY", "100", "1000000", PREVIOUS, instrument_type=InstrumentType.ETF),
        bar(9, "QQQ", "200", "1000000", PREVIOUS, instrument_type=InstrumentType.ETF),
        bar(10, "IWM", "50", "1000000", PREVIOUS, instrument_type=InstrumentType.ETF),
        bar(11, "DIA", "150", "1000000", PREVIOUS, instrument_type=InstrumentType.ETF),
    )
    current = (
        bar(1, "TESTA", "22", "2100000", CURRENT),
        bar(2, "TESTB", "6", "10000000", CURRENT),
        bar(3, "TESTC", "33", "5000000", CURRENT),
        bar(4, "TESTD", "26", "2000000", CURRENT, exchange="OTCM"),
        bar(5, "TESTE", "49", "1000000", CURRENT, instrument_type=InstrumentType.ETF),
        bar(6, "TESTF", "25", "3000000", CURRENT),
        bar(7, "XLC", "84", "1000000", CURRENT, instrument_type=InstrumentType.ETF),
        bar(8, "SPY", "101", "1000000", CURRENT, instrument_type=InstrumentType.ETF),
        bar(9, "QQQ", "204", "1000000", CURRENT, instrument_type=InstrumentType.ETF),
        bar(10, "IWM", "49", "1000000", CURRENT, instrument_type=InstrumentType.ETF),
        bar(11, "DIA", "151.5", "1000000", CURRENT, instrument_type=InstrumentType.ETF),
    )
    return current, previous


def test_tradable_universe_uses_previous_session_price_and_liquidity_gates():
    current, previous = base_rows()
    overview = service(current, previous).get_latest_overview()
    tradable = next(item for item in overview.universes if item.definition.universe_id == overview.default_universe_id)
    assert tradable.definition.display_name == "Common Shares"
    assert overview.governance_status == "provisional_classification"
    assert overview.evidence_coverage_status == "provider_form_complete_issuer_structure_provisional"
    assert tradable.audit.raw_comparable_count == 11
    assert tradable.audit.etf_count == 6
    assert tradable.audit.price_gate_count == 2
    assert tradable.audit.final_count == 2
    assert {row.ticker for row in tradable.movers.top_gainers} == {"TESTA"}
    assert all(node.ticker != "TESTE" for node in tradable.trading_activity_map.nodes)


def test_current_day_volume_does_not_make_security_universe_eligible():
    current, previous = base_rows()
    overview = service(current, previous).get_latest_overview()
    tradable = next(item for item in overview.universes if item.definition.universe_id == overview.default_universe_id)
    # TESTC has large current volume but failed the previous-session liquidity gate.
    assert "TESTC" not in {node.ticker for node in tradable.trading_activity_map.nodes}


def test_price_discontinuity_is_reviewed_and_excluded_from_movers_and_map():
    current, previous = base_rows()
    overview = service(current, previous).get_latest_overview()
    tradable = next(item for item in overview.universes if item.definition.universe_id == overview.default_universe_id)
    assert tradable.outlier_review_count == 1
    assert "TESTF" not in {row.ticker for row in tradable.movers.top_gainers}
    assert "TESTF" not in {node.ticker for node in tradable.trading_activity_map.nodes}
    assert tradable.quality_flag_counts["unverified_price_discontinuity"] == 1


def test_only_activated_primary_and_secondary_are_available():
    current, previous = base_rows()
    overview = service(current, previous).get_latest_overview()
    universes = {item.definition.universe_id: item for item in overview.universes}
    assert set(universes) == {CANDIDATE_A_ID, PUBLIC_SECONDARY_ID}
    assert universes[CANDIDATE_A_ID].audit.final_count == 2
    assert universes[PUBLIC_SECONDARY_ID].audit.final_count == 3


def test_sector_benchmarks_are_fixed_and_do_not_fabricate_missing_data():
    current, previous = base_rows()
    overview = service(current, previous).get_latest_overview()
    assert len(overview.sector_benchmarks) == 11
    xlc = next(item for item in overview.sector_benchmarks if item.ticker == "XLC")
    xly = next(item for item in overview.sector_benchmarks if item.ticker == "XLY")
    assert xlc.available is True
    assert xlc.close_to_close_return == Decimal("0.05")
    assert xlc.relative_to_spy_return == Decimal("0.04")
    assert xly.available is False
    assert xly.relative_to_spy_return is None
    assert xly.quality_flags == ("benchmark_unavailable",)


def test_market_benchmark_strip_contains_core_etfs_and_equal_weight_universe():
    current, previous = base_rows()
    overview = service(current, previous).get_latest_overview()
    benchmarks = {item.benchmark_id: item for item in overview.market_benchmarks}
    assert set(benchmarks) == {"spy", "qqq", "iwm", "dia"}
    assert benchmarks["spy"].ticker == "SPY"
    assert benchmarks["spy"].available is True
    assert benchmarks["spy"].close_to_close_return == Decimal("0.01")
    equal_weight=overview.universes[0].equal_weight_benchmark
    assert equal_weight.ticker is None
    assert equal_weight.close_to_close_return is not None
    assert equal_weight.quality_flags == ("equal_weight_not_index_return",)


def test_overview_separates_calendar_freshness_from_file_validation():
    current, previous = base_rows()
    overview = service(current, previous).get_latest_overview()
    assert overview.snapshot_validation_status == "file_schema_consistency_checks_passed"
    assert overview.freshness_status == "stale"
    assert overview.expected_latest_completed_session == date(2026, 8, 14)
    assert overview.actual_latest_completed_session == date(2026, 8, 13)
    assert overview.session_lag == 1
    assert overview.calendar_id == "XNYS"
    assert overview.freshness_checked_at == datetime(2026, 8, 15, 18, tzinfo=UTC)
    assert overview.data_status == "file_schema_consistency_checks_passed"
    assert overview.snapshot_generated_at is None
