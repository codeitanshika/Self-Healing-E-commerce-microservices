import pytest

from services.service_manager import ServiceManager
from shared.config import EFFECTIVE_FIXES, FIX_MAP, FAULT_TYPES


@pytest.fixture()
def strict(monkeypatch):
    monkeypatch.setenv("STRICT_HEALING", "1")


def test_default_mode_any_fix_heals():
    m = ServiceManager()
    m.inject_fault("cart", "crash")
    m.heal_service("cart", "reduce_load")        # nonsense for a crash...
    assert m.is_service_healthy("cart")          # ...but legacy mode accepts it


def test_strict_mode_ineffective_fix_leaves_service_broken(strict):
    m = ServiceManager()
    m.inject_fault("cart", "crash")
    result = m.heal_service("cart", "reduce_load")
    assert result["effective"] is False
    assert m.get_service_health("cart")["status"] == "down"


def test_strict_mode_effective_fix_heals(strict):
    m = ServiceManager()
    for fault, fixes in EFFECTIVE_FIXES.items():
        for fix in fixes:
            m.inject_fault("auth", fault)
            assert m.heal_service("auth", fix)["effective"] is True
            assert m.is_service_healthy("auth")


def test_every_correct_primary_fix_is_effective():
    """If diagnosis is right, the documented primary fix must work."""
    expected = {"crash": "service_crash", "memory": "memory_leak", "slow": "cpu_overload", "error": "error_spike"}
    for fault in FAULT_TYPES:
        assert FIX_MAP[expected[fault]]["primary"] in EFFECTIVE_FIXES[fault], fault
