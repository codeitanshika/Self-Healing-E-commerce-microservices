from shared import llm


def test_model_is_resolved_at_call_time(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "some/other-model")
    assert llm.current_model() == "some/other-model"
    monkeypatch.delenv("GROQ_MODEL")
    assert llm.current_model() == llm.DEFAULT_MODEL
