import time

import pytest
from sqlmodel import SQLModel, Session, create_engine

from database import models, queries


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(queries, "engine", engine)
    return engine


def add(engine, **kw):
    base = dict(service="cart", fault_type="crash", root_cause="service_crash", confidence=90,
                business_impact="", explanation="", fix_applied="restart", retry_count=0,
                result="RECOVERED", mttr_seconds=10.0, revenue_protected=100.0, timestamp=time.time())
    base.update(kw)
    with Session(engine) as s:
        s.add(models.Incident(**base))
        s.commit()


def test_empty_stats_have_stable_shape(db):
    stats = queries.get_stats()
    assert stats["total_incidents"] == 0 and stats["diagnosis_accuracy"] == 0.0


def test_stats_accuracy_rates_and_percentiles(db):
    add(db, mttr_seconds=10)
    add(db, mttr_seconds=20, fault_type="slow", root_cause="cpu_overload", retry_count=1)
    add(db, mttr_seconds=30, fault_type="memory", root_cause="service_crash")     # wrong diagnosis
    add(db, result="ESCALATED", mttr_seconds=99, revenue_protected=0)
    s = queries.get_stats()
    assert s["total_incidents"] == 4 and s["incidents_resolved"] == 3 and s["incidents_escalated"] == 1
    assert s["avg_mttr_seconds"] == 20.0 and s["p50_mttr_seconds"] == 20.0
    assert s["diagnosis_accuracy"] == 0.75
    assert s["recovery_rate"] == 0.75
    assert s["first_try_rate"] == 0.5
    assert s["speedup_vs_baseline"] == 45.0


def test_revenue_series_is_cumulative_and_ordered(db):
    add(db, timestamp=2, revenue_protected=50)
    add(db, timestamp=1, revenue_protected=100)
    pts = queries.get_revenue_series()
    assert [p["cumulative"] for p in pts] == [100, 150]


def test_breakdown_groups(db):
    add(db, service="cart")
    add(db, service="cart", mttr_seconds=20)
    add(db, service="auth", result="ESCALATED")
    b = queries.get_breakdown()
    cart = next(x for x in b["by_service"] if x["name"] == "cart")
    assert cart["count"] == 2 and cart["avg_mttr"] == 15.0
    assert {x["name"] for x in b["by_result"]} == {"RECOVERED", "ESCALATED"}


def test_percentile_helper():
    assert queries._percentile([], 50) == 0.0
    assert queries._percentile([1, 2, 3, 4], 50) == 2.5
    assert queries._percentile([5], 95) == 5
