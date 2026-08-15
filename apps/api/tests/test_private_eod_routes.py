from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tip_api.config import AppConfig
from tip_api.main import create_app
from tests.support.eod_read_dataset import SESSION_DATE, publish_completed_eod_dataset


def enabled_client(tmp_path: Path) -> TestClient:
    publish_completed_eod_dataset(tmp_path)
    app = create_app(AppConfig(market_data_root=tmp_path, enable_private_market_data_routes=True))
    return TestClient(app)


def test_private_routes_default_disabled_and_absent_from_openapi() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/private/market-data/eod/sessions")
    assert response.status_code == 404
    openapi = client.get("/openapi.json").json()
    assert "/api/v1/private/market-data/eod/sessions" not in openapi["paths"]


def test_private_routes_enabled_and_openapi_visible(tmp_path: Path) -> None:
    client = enabled_client(tmp_path)
    assert client.get("/api/v1/private/market-data/eod/sessions").status_code == 200
    openapi = client.get("/openapi.json").json()
    assert "/api/v1/private/market-data/eod/sessions" in openapi["paths"]


def test_health_unchanged_with_private_routes_enabled(tmp_path: Path) -> None:
    response = enabled_client(tmp_path).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_session_endpoints(tmp_path: Path) -> None:
    client = enabled_client(tmp_path)
    assert client.get("/api/v1/private/market-data/eod/sessions/latest").json()["session_date"] == SESSION_DATE.isoformat()
    summary = client.get(f"/api/v1/private/market-data/eod/sessions/{SESSION_DATE.isoformat()}/summary").json()
    assert summary["total_records"] == 3
    assert "daily_return" not in summary
    assert "breadth" not in summary


def test_bars_endpoint_pagination_filters_and_decimal_strings(tmp_path: Path) -> None:
    client = enabled_client(tmp_path)
    response = client.get(f"/api/v1/private/market-data/eod/sessions/{SESSION_DATE.isoformat()}/bars", params={"limit": 2})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 3
    assert len(payload["items"]) == 2
    first = payload["items"][0]
    assert first["ticker"] == "TESTA"
    assert first["volume"] == "100.25"
    assert isinstance(first["open"], str)
    assert "path" not in first
    assert "manifest" not in first

    filtered = client.get(f"/api/v1/private/market-data/eod/sessions/{SESSION_DATE.isoformat()}/bars", params={"ticker": "testb", "instrument_type": "etf"}).json()
    assert filtered["total_count"] == 1
    assert filtered["items"][0]["vwap"] is None
    assert filtered["items"][0]["trade_count"] is None
    assert "zero_volume" in filtered["items"][0]["quality_flags"]


def test_invalid_queries_return_422(tmp_path: Path) -> None:
    client = enabled_client(tmp_path)
    assert client.get(f"/api/v1/private/market-data/eod/sessions/{SESSION_DATE.isoformat()}/bars", params={"limit": 201}).status_code == 422
    assert client.get(f"/api/v1/private/market-data/eod/sessions/{SESSION_DATE.isoformat()}/bars", params={"offset": -1}).status_code == 422
    assert client.get(f"/api/v1/private/market-data/eod/sessions/{SESSION_DATE.isoformat()}/bars", params={"ticker": "bad/ticker"}).status_code == 422
    assert client.get(f"/api/v1/private/market-data/eod/sessions/{SESSION_DATE.isoformat()}/bars", params={"instrument_type": "bond"}).status_code == 422
    assert client.get("/api/v1/private/market-data/eod/sessions/not-a-date/summary").status_code == 422


def test_unknown_session_404_and_corruption_503(tmp_path: Path) -> None:
    client = enabled_client(tmp_path)
    assert client.get("/api/v1/private/market-data/eod/sessions/2026-08-12/summary").status_code == 404

    manifest = tmp_path / "market-data" / "eod-price-bars" / "schema_version=1" / f"session_date={SESSION_DATE.isoformat()}" / "manifest.json"
    manifest.write_text("[]\n", encoding="utf-8")
    response = client.get(f"/api/v1/private/market-data/eod/sessions/{SESSION_DATE.isoformat()}/summary")
    assert response.status_code == 503
    assert response.json() == {"detail": "market data unavailable"}


def test_no_filesystem_path_or_raw_manifest_in_responses(tmp_path: Path) -> None:
    client = enabled_client(tmp_path)
    payload = client.get(f"/api/v1/private/market-data/eod/sessions/{SESSION_DATE.isoformat()}/bars").json()
    text = str(payload)
    assert str(tmp_path) not in text
    assert "content_sha256" not in text
    assert "raw" not in text.lower()


def test_private_routes_do_not_open_network_sockets(tmp_path: Path, monkeypatch) -> None:
    import socket

    def fail_network(*args, **kwargs):  # pragma: no cover - failure path only
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    client = enabled_client(tmp_path)
    response = client.get(f"/api/v1/private/market-data/eod/sessions/{SESSION_DATE.isoformat()}/bars", params={"limit": 1})
    assert response.status_code == 200
    assert response.json()["items"][0]["ticker"] == "TESTA"
