from shared.config import (
    EFFECTIVE_FIXES, FIX_MAP, FIX_TYPES, FAULT_TYPES, MAX_RETRIES, next_retry_fix,
)
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


def _attempts(cause: str, first: str) -> list[str]:
    tried = [first]
    for _ in range(MAX_RETRIES):
        tried.append(next_retry_fix(cause, tried))
    return tried


def test_distinct_policy_never_repeats_a_fix(monkeypatch):
    monkeypatch.delenv("RETRY_POLICY", raising=False)       # the default
    for cause in FIX_MAP:
        for first in FIX_TYPES:
            tried = _attempts(cause, first)
            assert len(set(tried)) == len(tried), (cause, first, tried)


def test_distinct_policy_treats_an_invalid_fix_name_as_the_restart_it_runs_as(monkeypatch):
    monkeypatch.delenv("RETRY_POLICY", raising=False)
    assert "restart" not in _attempts("unknown", "does_not_exist")[1:]


def test_distinct_policy_covers_every_fault_after_a_mapped_first_fix(monkeypatch):
    """
    If the first fix is the diagnosed cause's primary, some attempt cures any
    fault, so even a wrong cause recovers. (An off-map first fix can still miss
    and escalate.)
    """
    monkeypatch.delenv("RETRY_POLICY", raising=False)
    for cause, fixes in FIX_MAP.items():
        for fault, cures in EFFECTIVE_FIXES.items():
            assert cures & set(_attempts(cause, fixes["primary"])), (cause, fault)


def test_repeat_policy_reuses_the_mapped_retry(monkeypatch):
    monkeypatch.setenv("RETRY_POLICY", "repeat")
    assert _attempts("cpu_overload", "reduce_load") == ["reduce_load", "restart", "restart"]


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
