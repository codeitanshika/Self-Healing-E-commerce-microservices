import asyncio

from experiments import run_pipeline as rp
from services.service_manager import ServiceManager
from agents import validation_agent


def test_end_to_end_pipeline_on_simulated_service(monkeypatch):
    # speed the 2 s validation wait up so the test stays quick
    monkeypatch.setattr(validation_agent.ValidationAgent, "VALIDATION_DELAY_SECONDS", 0.2)
    manager = ServiceManager()
    rows = asyncio.run(rp.run_pipeline_experiment(
        manager, "cart", ["crash", "memory"], trials=1, mode="rule", poll=0.2, timeout=20))
    assert len(rows) == 2
    for r in rows:
        assert r["result"] == "RECOVERED"
        assert r["diagnosis_correct"] is True
        assert float(r["mttr_s"]) >= float(r["detect_s"]) > 0
        assert r["retries"] == 0
    s = rp.summarize(rows)
    assert s["recovery_rate"] == 1.0 and s["first_try"] == 1.0 and s["mean_mttr"] > 0


def test_summarize_trial_handles_missing_events():
    row = rp.summarize_trial([], 0.0, "crash")
    assert row["result"] == "TIMEOUT" and row["mttr_s"] == ""


def test_unknown_fault_is_skipped_not_crashing(monkeypatch):
    monkeypatch.setattr(validation_agent.ValidationAgent, "VALIDATION_DELAY_SECONDS", 0.1)
    rows = asyncio.run(rp.run_pipeline_experiment(
        ServiceManager(), "cart", ["meteor"], trials=1, mode="rule", poll=0.2, timeout=2))
    assert rows == []


def test_csv_roundtrip(tmp_path):
    p = tmp_path / "x.csv"
    rp.write_csv([{"trial": 1, "service": "a", "fault_type": "crash", "mode": "rule", "detect_s": 1,
                   "diagnose_s": 0, "fix_s": 0, "validate_s": 2, "mttr_s": 3, "result": "RECOVERED",
                   "retries": 0, "root_cause": "service_crash", "diagnosis_correct": True}], str(p))
    assert "mttr_s" in p.read_text().splitlines()[0]


def test_concurrent_scenario_recovers_every_incident(monkeypatch):
    monkeypatch.setattr(validation_agent.ValidationAgent, "VALIDATION_DELAY_SECONDS", 0.2)
    rows = asyncio.run(rp.run_scenario_experiment(
        ServiceManager(), "flash-sale", trials=1, mode="rule", poll=0.2, timeout=30))
    assert {r["service"] for r in rows} == {"payment", "cart", "auth"}
    assert all(r["result"] == "RECOVERED" and r["concurrency"] == 3 for r in rows)
