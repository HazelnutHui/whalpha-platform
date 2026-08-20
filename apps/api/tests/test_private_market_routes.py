from __future__ import annotations

from fastapi.testclient import TestClient

from tip_api.config import AppConfig
from tip_api.main import create_app
from tests.services.test_eod_return_analytics import CURRENT, PREVIOUS, ID_A, ID_B, ID_C, analytics
from datetime import UTC, date, datetime
from uuid import UUID
from tip_api.contracts.market_data.v1.dashboard_universe_activation import DashboardUniverseActivationDatasetReferenceV1, DashboardUniverseActivationManifestV1, DashboardUniverseActivationRecordV1, SecurityTypeCountV1
from tip_api.persistence.parquet.dashboard_universe_activation import CompletedDashboardUniverseActivation, PUBLIC_SECONDARY_ID
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID

def fake_activation():
    at=datetime(2026,8,14,tzinfo=UTC); sha="a"*64
    def record(uid,universe,name,count,composition,default):
        return DashboardUniverseActivationRecordV1(activation_id=UUID(uid),analysis_session=CURRENT,membership_evidence_as_of=PREVIOUS,activated_at=at,universe_id=universe,display_name=name,long_display_name=name,description="fixture",is_default=default,member_count=count,security_type_composition=tuple(SecurityTypeCountV1(provider_type_code=k,count=v) for k,v in composition.items()),membership_fingerprint=sha,trailing_liquidity_source_fingerprint=sha,reviewed_override_source_fingerprint=sha,pre_activation_review_fingerprint=sha,current_eod_fingerprint=sha,previous_eod_fingerprint=sha,legacy_rollback_reference="fixture",limitations=("fixture",))
    records=(record("00000000-0000-5000-8000-400000000001",CANDIDATE_A_ID,"Common Shares",2,{"CS":2},True),record("00000000-0000-5000-8000-400000000002",PUBLIC_SECONDARY_ID,"Common Shares + ADRs",3,{"CS":2,"ADRC":1},False))
    manifest=DashboardUniverseActivationManifestV1(analysis_session=CURRENT,membership_evidence_as_of=PREVIOUS,trailing_window_start=date(2026,7,22),trailing_window_end=date(2026,8,18),trailing_window_session_count=20,reviewed_override_count=2,activated_at=at,default_universe_id=CANDIDATE_A_ID,available_universe_ids=(CANDIDATE_A_ID,PUBLIC_SECONDARY_ID),activation_dataset=DashboardUniverseActivationDatasetReferenceV1(dataset_path="fixture",record_count=2,content_fingerprint=sha,parquet_sha256=sha),pre_activation_review_path="fixture",pre_activation_review_fingerprint=sha,legacy_member_count=3,legacy_membership_fingerprint=sha,logical_content_fingerprint=sha)
    return CompletedDashboardUniverseActivation(manifest,records,{CANDIDATE_A_ID:frozenset({ID_A,ID_C}),PUBLIC_SECONDARY_ID:frozenset({ID_A,ID_B,ID_C})})


def enabled_client() -> TestClient:
    svc = analytics().query_service
    return TestClient(create_app(AppConfig(market_data_root=__import__('pathlib').Path('/tmp'), enable_private_market_data_routes=True), eod_query_service=svc,dashboard_activation=fake_activation()))


def test_private_market_routes_default_disabled_and_absent_from_openapi():
    client = TestClient(create_app())
    assert client.get('/api/v1/private/market/summary/latest').status_code == 404
    assert '/api/v1/private/market/summary/latest' not in client.get('/openapi.json').json()['paths']


def test_private_market_routes_enabled_and_openapi_visible():
    client = enabled_client()
    assert client.get('/api/v1/private/market/summary/latest').status_code == 200
    paths = client.get('/openapi.json').json()['paths']
    assert '/api/v1/private/market/summary/latest' in paths
    assert '/api/v1/private/market/overview/latest' in paths


def test_summary_movers_liquidity_map_and_returns_decimal_strings():
    client = enabled_client()
    summary = client.get('/api/v1/private/market/summary/latest').json()
    assert summary['current_session_date'] == CURRENT.isoformat()
    assert summary['previous_session_date'] == PREVIOUS.isoformat()
    assert isinstance(summary['equal_weight_return'], str)
    assert 'market_cap' not in str(summary).lower()

    movers = client.get('/api/v1/private/market/movers/latest?per_side=10').json()
    assert len(movers['top_gainers']) == 1
    assert isinstance(movers['top_gainers'][0]['close_to_close_return'], str)
    assert 'notional' not in str(movers).lower()
    assert 'flow' not in str(movers).lower()

    liquidity = client.get('/api/v1/private/market/liquidity-map/latest?limit=2').json()
    assert liquidity['map_type'] == 'trading_activity'
    assert liquidity['size_metric'] == 'close_times_volume_proxy'
    assert liquidity['is_market_cap_weighted'] is False
    assert liquidity['is_sector_grouped'] is False
    assert len(liquidity['nodes']) == 2

    overview = client.get('/api/v1/private/market/overview/latest').json()
    assert overview['default_universe_id'] == CANDIDATE_A_ID
    assert overview['universes'][0]['definition']['display_name'] == 'Common Shares'
    assert overview['governance_status'] == 'provisional_classification'
    assert isinstance(overview['universes'][0]['summary']['equal_weight_return'], str)
    secondary=client.get(f'/api/v1/private/market/overview/latest?universe_id={PUBLIC_SECONDARY_ID}').json()
    assert secondary['selected_universe_id']==PUBLIC_SECONDARY_ID
    assert client.get('/api/v1/private/market/overview/latest?universe_id=../../etc').status_code==422

    returns = client.get('/api/v1/private/market/returns/latest?limit=2').json()
    assert returns['total_count'] == 2
    assert isinstance(returns['items'][0]['current_dollar_volume_proxy'], str)


def test_invalid_route_queries_and_no_path_leakage():
    client = enabled_client()
    assert client.get('/api/v1/private/market/movers/latest?per_side=51').status_code == 422
    assert client.get('/api/v1/private/market/liquidity-map/latest?limit=501').status_code == 422
    payload = client.get('/api/v1/private/market/summary/latest').json()
    assert '/tmp' not in str(payload)
    assert 'manifest' not in str(payload).lower()
    assert 'raw' not in str(payload).lower()


def test_private_market_routes_do_not_open_network_sockets(monkeypatch):
    import socket
    def fail_network(*args, **kwargs):
        raise AssertionError('network access is forbidden')
    monkeypatch.setattr(socket, 'create_connection', fail_network)
    assert enabled_client().get('/api/v1/private/market/summary/latest').status_code == 200
