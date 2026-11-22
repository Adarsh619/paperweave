def test_answer_model_is_backed_up_by_the_router_model(monkeypatch):
    """Each Groq model has its own daily token quota: when the answer model runs out, the router model answers."""
    from app import config
    from app.agent import llm

    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "")
    monkeypatch.setattr(config, "LLM_LOCAL_FALLBACK", False)
    assert [m.model_name for m in llm._models("answer")] == [config.GROQ_ANSWER_MODEL, config.GROQ_ROUTER_MODEL]
    assert [m.model_name for m in llm._models("router")] == [config.GROQ_ROUTER_MODEL]
