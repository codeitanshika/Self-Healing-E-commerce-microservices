"""Drive the Orchestrator purely through bus events and observe what it asks for."""
import asyncio

import pytest

from orchestrator.event_bus import bus
from orchestrator.orchestrator import Orchestrator
from shared.config import FIX_MAP, MAX_RETRIES
from shared.events import (
    ANOMALY_DETECTED, DIAGNOSE_REQUEST, DIAGNOSIS_READY, FIX_REQUEST,
    FIX_APPLIED, VALIDATE_REQUEST, VALIDATION_RESULT,
)


def make():
    orch = Orchestrator()
    sent = {DIAGNOSE_REQUEST: [], FIX_REQUEST: [], VALIDATE_REQUEST: [], VALIDATION_RESULT: []}

    def spy(topic):
        async def h(p):
            sent[topic].append(dict(p))
        h.__name__ = f"spy_{topic}"
        bus.subscribe(topic, h)

    for t in sent:
        spy(t)
    return orch, sent


async def start_incident(orch, sent, root="service_crash"):
    await bus.publish(ANOMALY_DETECTED, {"service": "payment", "fault_type": "crash", "metrics": {}})
    iid = sent[DIAGNOSE_REQUEST][-1]["incident_id"]
    await bus.publish(DIAGNOSIS_READY, {
        "incident_id": iid, "service": "payment", "root_cause": root, "confidence": 90,
        "business_impact": "x", "explanation": "y", "fix": FIX_MAP[root]["primary"],
    })
    return iid


def test_anomaly_creates_incident_and_requests_diagnosis():
    orch, sent = make()
    asyncio.run(bus.publish(ANOMALY_DETECTED, {"service": "cart", "fault_type": "slow", "metrics": {"a": 1}}))
    assert len(sent[DIAGNOSE_REQUEST]) == 1
    iid = sent[DIAGNOSE_REQUEST][0]["incident_id"]
    assert orch.incident_cache[iid]["status"] == "IN_PROGRESS"
    assert orch.get_active_incident()["incident_id"] == iid


def test_diagnosis_triggers_primary_fix_then_validation():
    orch, sent = make()

    async def go():
        iid = await start_incident(orch, sent)
        assert sent[FIX_REQUEST][-1]["fix"] == "restart"
        await bus.publish(FIX_APPLIED, {"incident_id": iid, "service": "payment"})
        return iid

    iid = asyncio.run(go())
    assert sent[VALIDATE_REQUEST][-1]["incident_id"] == iid


def test_recovered_closes_incident():
    orch, sent = make()

    async def go():
        iid = await start_incident(orch, sent)
        await bus.publish(VALIDATION_RESULT, {"incident_id": iid, "service": "payment", "result": "RECOVERED"})
        return iid

    iid = asyncio.run(go())
    assert orch.incident_cache[iid]["status"] == "RECOVERED"
    assert orch.get_active_incident() is None


@pytest.mark.parametrize("policy, expected", [
    ("distinct", ["restart", "reduce_load", "clear_memory"]),
    ("repeat",   ["restart"] + [FIX_MAP["service_crash"]["retry"]] * MAX_RETRIES),
])
def test_still_broken_retries_then_escalates(monkeypatch, policy, expected):
    monkeypatch.setenv("RETRY_POLICY", policy)
    orch, sent = make()

    async def go():
        iid = await start_incident(orch, sent)
        for _ in range(MAX_RETRIES):
            await bus.publish(VALIDATION_RESULT, {"incident_id": iid, "service": "payment", "result": "STILL_BROKEN"})
        # budget now spent: next failure must escalate, not retry
        await bus.publish(VALIDATION_RESULT, {"incident_id": iid, "service": "payment", "result": "STILL_BROKEN"})
        return iid

    iid = asyncio.run(go())
    fixes = [r["fix"] for r in sent[FIX_REQUEST]]
    assert fixes == expected
    assert orch.incident_cache[iid]["retry_count"] == MAX_RETRIES
    assert orch.incident_cache[iid]["status"] == "ESCALATED"
    assert any(r["result"] == "ESCALATED" for r in sent[VALIDATION_RESULT])


def test_orchestrator_ignores_its_own_escalation_event():
    orch, sent = make()

    async def go():
        iid = await start_incident(orch, sent)
        before = len(sent[FIX_REQUEST])
        await bus.publish(VALIDATION_RESULT, {"incident_id": iid, "service": "payment", "result": "ESCALATED"})
        return before

    before = asyncio.run(go())
    assert len(sent[FIX_REQUEST]) == before


def test_unknown_incident_ids_are_ignored():
    orch, sent = make()
    asyncio.run(bus.publish(DIAGNOSIS_READY, {
        "incident_id": "nope", "root_cause": "x", "confidence": 1,
        "business_impact": "", "explanation": "", "fix": "restart",
    }))
    assert sent[FIX_REQUEST] == []


def test_timeline_and_stage_follow_the_pipeline():
    orch, sent = make()

    async def go():
        iid = await start_incident(orch, sent)
        cached = orch.incident_cache[iid]
        assert cached["stage"] == "fixing"
        await bus.publish(FIX_APPLIED, {"incident_id": iid, "service": "payment", "fix_applied": "restart"})
        assert cached["stage"] == "validating"
        await bus.publish(VALIDATION_RESULT, {"incident_id": iid, "service": "payment",
                                              "result": "STILL_BROKEN"})
        assert cached["stage"] == "fixing"
        await bus.publish(VALIDATION_RESULT, {"incident_id": iid, "service": "payment",
                                              "result": "RECOVERED", "mttr_seconds": 4})
        return cached

    cached = asyncio.run(go())
    assert [e["stage"] for e in cached["timeline"]] == [
        "DETECTED", "DIAGNOSED", "FIX_APPLIED", "RETRY", "RECOVERED"]
    assert cached["stage"] == "recovered"


def test_multiple_active_incidents_are_listed():
    orch, sent = make()

    async def go():
        await bus.publish(ANOMALY_DETECTED, {"service": "a", "fault_type": "crash", "metrics": {}})
        await bus.publish(ANOMALY_DETECTED, {"service": "b", "fault_type": "slow", "metrics": {}})

    asyncio.run(go())
    assert {i["service"] for i in orch.get_active_incidents()} == {"a", "b"}
