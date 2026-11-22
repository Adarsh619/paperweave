"""Chat models with automatic fallback: Groq (answer model, then router model) -> Gemini -> local Ollama.

"router" is the fast model for planning; "answer" is the strong model for writing.
Providers without an API key are skipped, so local development runs on Ollama alone.
"""

import logging
import time
from functools import lru_cache
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda

from app import config

Role = Literal["router", "answer"]
log = logging.getLogger(__name__)


def _models(role: Role) -> list[BaseChatModel]:
    models: list[BaseChatModel] = []
    if config.GROQ_API_KEY:
        from langchain_groq import ChatGroq

        names = [config.GROQ_ROUTER_MODEL] if role == "router" else [config.GROQ_ANSWER_MODEL, config.GROQ_ROUTER_MODEL]
        # Each Groq model has its own free daily token quota, so the router model backs up the answer model.
        for name in dict.fromkeys(names):
            models.append(ChatGroq(model=name, api_key=config.GROQ_API_KEY, temperature=0, max_retries=1, timeout=30))
    if config.GOOGLE_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI

        models.append(ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL, google_api_key=config.GOOGLE_API_KEY, temperature=0, max_retries=1, timeout=30
        ))
    if not models or config.LLM_LOCAL_FALLBACK:
        from langchain_ollama import ChatOllama

        models.append(ChatOllama(model=config.OLLAMA_MODEL, base_url=config.OLLAMA_URL, temperature=0))
    return models


def _structured(model: BaseChatModel, schema: type) -> Runnable:
    # Ollama follows a JSON schema natively; cloud models use tool calling.
    if type(model).__name__ == "ChatOllama":
        return model.with_structured_output(schema, method="json_schema")
    return model.with_structured_output(schema)


def is_busy(exc: BaseException) -> bool:
    """Free-tier rate limits or an overloaded model: worth waiting for, not a bug."""
    text = f"{type(exc).__name__} {exc}"
    return any(s in text for s in ("RateLimit", "429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "high demand"))


# Groq's per-minute token budget refills continuously: one answer's worth (~2.5K of 8K/min) frees up in ~20 s.
BUSY_WAITS = (8, 15)


def _patient(runnable: Runnable) -> Runnable:
    """When every model is busy, wait and try the whole chain again instead of failing the question."""

    def run(messages, config: RunnableConfig | None = None):
        for wait in (*BUSY_WAITS, None):
            try:
                return runnable.invoke(messages, config)
            except Exception as exc:
                if wait is None or not is_busy(exc):
                    raise
                log.warning("all models busy (%s); retrying in %ss", type(exc).__name__, wait)
                time.sleep(wait)

    return RunnableLambda(run)


@lru_cache
def chat(role: Role) -> Runnable:
    primary, *backups = _models(role)
    chain = primary.with_fallbacks(backups) if backups else primary
    # The planner has an instant keyword fallback, so only the answer is worth waiting for.
    return _patient(chain) if role == "answer" else chain


@lru_cache
def structured(role: Role, schema: type) -> Runnable:
    primary, *backups = (_structured(m, schema) for m in _models(role))
    return primary.with_fallbacks(backups) if backups else primary


def provider_names() -> list[str]:
    return [f"{type(m).__name__}({getattr(m, 'model_name', None) or getattr(m, 'model', '')})" for m in _models("answer")]
