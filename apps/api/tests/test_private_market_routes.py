from __future__ import annotations

from fastapi.testclient import TestClient

from tip_api.config import AppConfig
from tip_api.main import create_app
from tests.services.test_eod_return_analytics import CURRENT, FakeRepo, PREVIOUS, analytics


def enabled_client() -> TestClient:
    svc = analytics().query_service
    return TestClient(create_app(AppConfig(market_data_root=__import__('pathlib').Path('/tmp'), enable_private_market_data_routes=True), eod_query_service=svc))


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
    assert liquidity['map_type'] == 'liquidity'
    assert liquidity['size_metric'] == 'close_times_volume_proxy'
    assert liquidity['is_market_cap_weighted'] is False
    assert liquidity['is_sector_grouped'] is False
    assert len(liquidity['nodes']) == 2

    overview = client.get('/api/v1/private/market/overview/latest').json()
    assert overview['default_universe_id'] == 'tradable_us_listed_equities_v1'
    assert overview['universes'][0]['definition']['display_name'] == 'Legacy Liquid Screen (Provisional)'
    assert overview['governance_status'] == 'provisional_classification'
    assert overview['universes'][0]['summary']['equal_weight_return'] is None
    assert isinstance(overview['universes'][2]['summary']['equal_weight_return'], str)

    returns = client.get('/api/v1/private/market/returns/latest?limit=2').json()
    assert returns['total_count'] == 3
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
