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


def test_scenarios_listed_and_launchable(client):
    listing = client.get("/api/scenarios").json()["scenarios"]
    assert {"flash-sale", "checkout-cascade"} <= {s["id"] for s in listing}
    h = {"X-API-Key": "secret"}
    assert client.post("/api/scenarios/nope/run", headers=h).status_code == 404
    assert client.post("/api/scenarios/flash-sale/run").status_code == 401
    ok = client.post("/api/scenarios/slow-burn/run", headers=h)
    assert ok.status_code == 200 and ok.json()["status"] == "started"
    for svc in ("inventory", "notification"):
        client.post(f"/api/services/{svc}/heal", headers=h)


def test_reset_requires_key_and_confirmation_and_clears_data(client, monkeypatch):
    from sqlmodel import SQLModel, Session, create_engine, select
    from database import admin, models

    from sqlalchemy.pool import StaticPool
    # in-memory + one shared connection, so the request thread sees the same DB;
    # never touch the real incidents.db
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(admin, "engine", engine)
    with Session(engine) as s:
        s.add(models.Incident(service="cart", fault_type="crash", root_cause="service_crash", confidence=9,
                              business_impact="", explanation="", fix_applied="restart", retry_count=0,
                              result="RECOVERED", mttr_seconds=1.0, revenue_protected=1.0, timestamp=1.0))
        s.add(models.IncidentStage(incident_db_id=1, stage="DETECTED", ts=1.0))
        s.commit()

    h = {"X-API-Key": "secret"}
    assert client.post("/api/admin/reset?confirm=true").status_code == 401     # no key
    assert client.post("/api/admin/reset", headers=h).status_code == 400       # no confirmation
    with Session(engine) as s:
        assert len(s.exec(select(models.Incident)).all()) == 1                 # still there

    client.post("/api/services/auth/fault/crash", headers=h)
    r = client.post("/api/admin/reset?confirm=true", headers=h)
    assert r.status_code == 200 and r.json()["incidents_deleted"] == 1
    assert "auth" in r.json()["services_healed"]
    with Session(engine) as s:
        assert s.exec(select(models.Incident)).all() == []
        assert s.exec(select(models.IncidentStage)).all() == []
