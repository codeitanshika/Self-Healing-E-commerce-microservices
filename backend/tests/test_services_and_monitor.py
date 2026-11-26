import asyncio

from agents.monitor_agent import MonitorAgent
from agents.rule_based_diagnosis import rule_based_diagnose
from agents.validation_agent import ValidationAgent
from services.service_manager import ServiceManager
from shared.events import ANOMALY_DETECTED
from orchestrator.event_bus import bus


def test_fault_injection_changes_status_and_heal_restores():
    m = ServiceManager()
    assert m.is_service_healthy("payment")
    m.inject_fault("payment", "crash")
    assert m.get_service_health("payment")["status"] == "down"
    m.heal_service("payment", "restart")
    assert m.is_service_healthy("payment")


def test_invalid_fault_and_service_are_rejected():
    m = ServiceManager()
    assert "error" in m.inject_fault("payment", "meteor")
    assert "error" in m.inject_fault("ghost", "crash")


def test_monitor_detects_each_fault_type():
    for fault in ("crash", "slow", "error", "memory"):
        m = ServiceManager()
        m.inject_fault("cart", fault)
        assert MonitorAgent(m)._detect_anomaly(m.get_service_health("cart")) == fault
    healthy_mgr = ServiceManager()
    mon = MonitorAgent(healthy_mgr)
    assert mon._detect_anomaly(healthy_mgr.get_service_health("cart")) is None


def test_monitor_reports_each_anomaly_once():
    m = ServiceManager()
    mon = MonitorAgent(m)
    got = []

    async def h(p):
        got.append(p["service"])

    bus.subscribe(ANOMALY_DETECTED, h)
    m.inject_fault("auth", "crash")

    async def go():
        await mon._check_all_services()
        await mon._check_all_services()

    asyncio.run(go())
    assert got == ["auth"]


def test_validation_reports_recovered_and_still_broken():
    m = ServiceManager()
    v = ValidationAgent(m)
    m.inject_fault("cart", "crash")
    assert v.validate("cart", 0)[0] == "STILL_BROKEN"
    m.heal_service("cart")
    assert v.validate("cart", 0)[0] == "RECOVERED"


def test_rule_based_diagnosis_covers_all_faults():
    cases = [
        ({"status": "down"}, "service_crash"),
        ({"status": "degraded", "memory_percent": 90}, "memory_leak"),
        ({"status": "degraded", "response_time_ms": 5000, "cpu_percent": 95}, "cpu_overload"),
        ({"status": "degraded", "error_rate": 0.5, "response_time_ms": 300}, "error_spike"),
    ]
    for metrics, cause in cases:
        assert rule_based_diagnose("x", metrics)["root_cause"] == cause


def test_monitor_keeps_bounded_metric_history():
    m = ServiceManager()
    mon = MonitorAgent(m)

    async def go():
        for _ in range(MonitorAgent.HISTORY_SIZE + 5):
            await mon._check_all_services()

    asyncio.run(go())
    hist = mon.get_history()
    assert set(hist) == set(m.services)
    assert len(hist["cart"]) == MonitorAgent.HISTORY_SIZE
    assert {"t", "rt", "err", "mem", "cpu", "status"} <= set(hist["cart"][0])
