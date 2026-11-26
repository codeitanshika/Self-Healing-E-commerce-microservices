import asyncio

import pytest

from shared import llm
from shared.config import FIX_MAP, EFFECTIVE_FIXES


def test_model_is_resolved_at_call_time(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "some/other-model")
    assert llm.current_model() == "some/other-model"
    monkeypatch.delenv("GROQ_MODEL")
    assert llm.current_model() == llm.DEFAULT_MODEL


def test_parse_json_object_tolerates_fences_and_prose():
    assert llm.parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm.parse_json_object('Sure! {"a": 1} hope that helps') == {"a": 1}


@pytest.mark.parametrize("bad", ["", "no json here", '{"root_cause": "x", "conf', "[1, 2]"])
def test_parse_json_object_rejects_truncated_or_non_objects(bad):
    with pytest.raises(ValueError):
        llm.parse_json_object(bad)


class _Resp:
    def __init__(self, text):
        self.choices = [type("C", (), {"message": type("M", (), {"content": text})()})()]


def _fake_client(replies):
    calls = {"n": 0}

    class Completions:
        def create(self, **kw):
            i = min(calls["n"], len(replies) - 1)
            calls["n"] += 1
            r = replies[i]
            if isinstance(r, Exception):
                raise r
            return _Resp(r)

    client = type("Cl", (), {"chat": type("Ch", (), {"completions": Completions()})()})()
    return client, calls


def test_ask_llm_retries_once_after_truncated_reply(monkeypatch):
    client, calls = _fake_client(['{"root_cause": "x", "conf', '{"root_cause": "service_crash"}'])
    monkeypatch.setattr(llm, "client", client)
    assert asyncio.run(llm.ask_llm("p")) == {"root_cause": "service_crash"}
    assert calls["n"] == 2


def test_ask_llm_falls_back_to_safe_default_after_two_failures(monkeypatch):
    client, calls = _fake_client([RuntimeError("429"), "garbage"])
    monkeypatch.setattr(llm, "client", client)
    out = asyncio.run(llm.ask_llm("p"))
    assert out["root_cause"] == "unknown" and calls["n"] == llm.MAX_ATTEMPTS


def test_unknown_diagnosis_can_recover_every_fault_within_the_retry_budget():
    """A failed diagnosis must try two DIFFERENT fixes that together cover every fault class."""
    u = FIX_MAP["unknown"]
    assert u["primary"] != u["retry"]
    for fault, fixes in EFFECTIVE_FIXES.items():
        assert {u["primary"], u["retry"]} & fixes, fault
