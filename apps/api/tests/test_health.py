from fastapi.testclient import TestClient

from tip_api.main import app


def test_health_endpoint_returns_expected_contract() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "status": "ok",
        "service": "trading-intelligence-api",
        "version": "0.1.0",
    }
