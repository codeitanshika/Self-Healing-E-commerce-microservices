import pytest
from fastapi.testclient import TestClient

from shared import security


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    security.reset_rate_limits()
    import main
    return TestClient(main.app)


def test_read_endpoints_are_open(client):
    assert client.get("/api/services").status_code == 200
    assert client.get("/api/stats").status_code == 200


def test_fault_injection_requires_api_key(client):
    assert client.post("/api/services/cart/fault/crash").status_code == 401
    bad = client.post("/api/services/cart/fault/crash", headers={"X-API-Key": "nope"})
    assert bad.status_code == 401
    ok = client.post("/api/services/cart/fault/crash", headers={"X-API-Key": "secret"})
    assert ok.status_code == 200
    client.post("/api/services/cart/heal", headers={"X-API-Key": "secret"})


def test_auth_disabled_when_no_key(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    assert client.post("/api/services/cart/fault/slow").status_code == 200
    client.post("/api/services/cart/heal")


def test_rate_limit_kicks_in(client, monkeypatch):
    monkeypatch.setattr(security, "RATE_LIMIT_MAX", 3)
    h = {"X-API-Key": "secret"}
    codes = [client.post("/api/services/cart/heal", headers=h).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert 429 in codes[3:]
