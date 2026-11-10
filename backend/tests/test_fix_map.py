from shared.config import FIX_MAP, FAULT_TYPES, MAX_RETRIES
from agents.fix_agent import FixAgent
from services.service_manager import ServiceManager


def test_every_root_cause_has_primary_and_retry():
    for cause, fixes in FIX_MAP.items():
        assert set(fixes) == {"primary", "retry"}, cause


def test_retry_fix_differs_from_primary_except_unknown():
    for cause, fixes in FIX_MAP.items():
        if cause != "unknown":
            assert fixes["primary"] != fixes["retry"], cause


def test_all_mapped_fixes_are_executable_by_fix_agent():
    agent = FixAgent(ServiceManager())
    for fixes in FIX_MAP.values():
        assert fixes["primary"] in agent.valid_fixes
        assert fixes["retry"] in agent.valid_fixes


def test_fault_types_and_retry_budget():
    assert set(FAULT_TYPES) >= {"crash", "slow", "memory", "error"}
    assert MAX_RETRIES >= 1


def test_fix_agent_heals_and_rejects_unknown_service():
    m = ServiceManager()
    agent = FixAgent(m)
    m.inject_fault("cart", "crash")
    assert agent.apply_fix("cart", "restart")["success"] is True
    assert m.is_service_healthy("cart")
    assert agent.apply_fix("ghost", "restart")["success"] is False


def test_unknown_fix_falls_back_to_restart():
    m = ServiceManager()
    agent = FixAgent(m)
    m.inject_fault("auth", "crash")
    assert agent.apply_fix("auth", "does_not_exist")["success"] is True
