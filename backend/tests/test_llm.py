def test_answer_model_is_backed_up_by_the_router_model(monkeypatch):
    """Each Groq model has its own daily token quota: when the answer model runs out, the router model answers."""
    from app import config
    from app.agent import llm

    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "")
    monkeypatch.setattr(config, "LLM_LOCAL_FALLBACK", False)
    monkeypatch.setattr(llm, "_available", lambda provider: None)  # no network: trust config
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


GROQ_TODAY = ("whisper-large-v3", "openai/gpt-oss-safeguard-20b", "openai/gpt-oss-120b", "openai/gpt-oss-20b",
              "qwen/qwen3.8-27b", "meta-llama/llama-prompt-guard-2-86m", "canopylabs/orpheus-v1-english")


def test_configured_model_is_kept_while_it_is_offered():
    from app.agent import llm

    assert llm.pick(["openai/gpt-oss-120b"], GROQ_TODAY) == "openai/gpt-oss-120b"


def test_retired_model_is_replaced_by_the_largest_chat_model_on_offer():
    """Like Groq retiring llama-3.3-70b: pick a real chat model, never speech or a safety classifier."""
    from app.agent import llm

    answer = llm.pick(["llama-3.3-70b-versatile"], GROQ_TODAY)
    router = llm.pick(["llama-3.1-8b-instant"], GROQ_TODAY, exclude=(answer,))
    assert answer == "openai/gpt-oss-120b" and router == "qwen/qwen3.8-27b"


def test_retired_gemini_model_falls_back_to_a_latest_alias():
    from app.agent import llm

    offered = ("gemini-3.8-flash", "gemini-flash-lite-latest", "gemini-4-hydrogen", "gemini-3.5-transcribe")
    assert llm.pick(["gemini-2.5-flash", *llm.GEMINI_FALLBACKS], offered, rank=llm._gemini_rank) == "gemini-flash-lite-latest"
    # No alias either: still prefer the flash-lite family.
    offered = ("gemini-4-hydrogen", "gemini-9-flash", "gemini-9-flash-lite", "gemini-9-live")
    assert llm.pick(["gemini-2.5-flash", *llm.GEMINI_FALLBACKS], offered, rank=llm._gemini_rank) == "gemini-9-flash-lite"


def test_unreadable_model_list_keeps_the_configured_name():
    from app.agent import llm

    assert llm.pick(["openai/gpt-oss-120b"], None) == "openai/gpt-oss-120b"


def test_model_lists_are_re_read_after_the_refresh_interval(monkeypatch):
    from app.agent import llm

    cleared = []
    for name in ("_available", "_chat", "_structured_chain"):
        monkeypatch.setattr(getattr(llm, name), "cache_clear", lambda n=name: cleared.append(n))
    monkeypatch.setattr(llm, "_checked_at", llm.time.monotonic() - llm.REFRESH_S - 1)
    llm._refresh_if_stale()
    assert cleared == ["_available", "_chat", "_structured_chain"]
    llm._refresh_if_stale()  # just refreshed: nothing more to clear
    assert len(cleared) == 3
