def test_answer_model_is_backed_up_by_the_router_model(monkeypatch):
    """Each Groq model has its own daily token quota: when the answer model runs out, the router model answers."""
    from app import config
    from app.agent import llm

    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "")
    monkeypatch.setattr(config, "LLM_LOCAL_FALLBACK", False)
    assert [m.model_name for m in llm._models("answer")] == [config.GROQ_ANSWER_MODEL, config.GROQ_ROUTER_MODEL]
    assert [m.model_name for m in llm._models("router")] == [config.GROQ_ROUTER_MODEL]


class RateLimitError(Exception):
    pass


def _flaky(failures: list[Exception]):
    """A stand-in model chain that raises the given errors in turn, then answers."""
    from langchain_core.runnables import RunnableLambda

    calls = []

    def run(_messages):
        calls.append(1)
        if failures:
            raise failures.pop(0)
        return "answer"

    return RunnableLambda(run), calls


def test_busy_models_are_waited_for_then_answer(monkeypatch):
    from app.agent import llm

    slept = []
    monkeypatch.setattr(llm.time, "sleep", slept.append)
    chain, calls = _flaky([RateLimitError("Error code: 429"), RateLimitError("Error code: 429")])
    assert llm._patient(chain).invoke([]) == "answer"
    assert slept == list(llm.BUSY_WAITS) and len(calls) == 3


def test_waiting_gives_up_after_the_last_wait(monkeypatch):
    import pytest

    from app.agent import llm

    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    chain, calls = _flaky([RateLimitError("429")] * 5)
    with pytest.raises(RateLimitError):
        llm._patient(chain).invoke([])
    assert len(calls) == len(llm.BUSY_WAITS) + 1


def test_real_errors_fail_at_once_without_waiting(monkeypatch):
    import pytest

    from app.agent import llm

    monkeypatch.setattr(llm.time, "sleep", lambda s: pytest.fail("should not wait"))
    chain, calls = _flaky([ValueError("bad prompt")])
    with pytest.raises(ValueError):
        llm._patient(chain).invoke([])
    assert len(calls) == 1
