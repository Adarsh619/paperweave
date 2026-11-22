"""Chat models with automatic fallback: Groq (answer model, then router model) -> Gemini -> local Ollama.

"router" is the fast model for planning; "answer" is the strong model for writing.
Providers without an API key are skipped, so local development runs on Ollama alone.

Free-tier providers retire models every few weeks, so configured names are checked against each
provider's live model list (every few hours) and a retired one is replaced by the best one on offer.
"""

import logging
import re
import time
from functools import lru_cache
from typing import Literal

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda

from app import config

Role = Literal["router", "answer"]
log = logging.getLogger(__name__)

# How often to re-read the providers' model lists, so a model retired mid-week is replaced without a deploy.
REFRESH_S = 6 * 3600
# Model ids that aren't general chat models (speech, safety classifiers, media, agents).
NOT_CHAT = ("whisper", "guard", "orpheus", "tts", "embed", "image", "imagen", "veo", "lyria", "audio", "live",
            "transcribe", "robot", "computer", "banana", "research", "antigravity", "genie", "aqa", "decision")
# Google's "-latest" aliases always point at a current model, so they never retire.
GEMINI_FALLBACKS = ("gemini-flash-lite-latest", "gemini-flash-latest")


@lru_cache
def _available(provider: str) -> tuple[str, ...] | None:
    """The model ids a provider offers right now, or None if the list can't be read (then trust config)."""
    try:
        if provider == "groq":
            r = httpx.get("https://api.groq.com/openai/v1/models",
                          headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"}, timeout=5)
            r.raise_for_status()
            return tuple(m["id"] for m in r.json()["data"])
        r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models", params={"pageSize": 1000},
                      headers={"x-goog-api-key": config.GOOGLE_API_KEY}, timeout=5)
        r.raise_for_status()
        return tuple(m["name"].removeprefix("models/") for m in r.json()["models"]
                     if "generateContent" in m.get("supportedGenerationMethods", []))
    except Exception as exc:  # noqa: BLE001 - never block startup on a model list
        log.warning("couldn't list %s models (%s); using configured names", provider, type(exc).__name__)
        return None


def _size(name: str) -> float:
    """Parameter count from the id ("gpt-oss-120b" -> 120): bigger usually writes better."""
    return max((float(n) for n in re.findall(r"(\d+(?:\.\d+)?)b(?![a-z])", name.lower())), default=0)


def _gemini_rank(name: str) -> tuple:
    # Flash-Lite is fast and has the most generous free limits; previews come and go.
    return ("flash-lite" in name, "flash" in name, "preview" not in name, name.endswith("-latest"))


def pick(preferred: list[str], available: tuple[str, ...] | None, exclude: tuple[str, ...] = (),
         rank=_size) -> str:
    """The first preferred model still on offer; if all are retired, the best-ranked chat model offered."""
    if available is None:
        return preferred[0]
    for name in preferred:
        if name in available and name not in exclude:
            return name
    chat_models = [m for m in available if m not in exclude and not any(x in m.lower() for x in NOT_CHAT)]
    best = max(chat_models, key=rank, default=preferred[0])
    log.warning("model %s is no longer offered; using %s", preferred[0], best)
    return best


def _groq_names(role: Role) -> list[str]:
    available = _available("groq")
    answer = pick([config.GROQ_ANSWER_MODEL], available)
    router = pick([config.GROQ_ROUTER_MODEL], available, exclude=(answer,))
    # Each Groq model has its own free daily token quota, so the router model backs up the answer model.
    return [router] if role == "router" else list(dict.fromkeys([answer, router]))


def _models(role: Role) -> list[BaseChatModel]:
    models: list[BaseChatModel] = []
    if config.GROQ_API_KEY:
        from langchain_groq import ChatGroq

        for name in _groq_names(role):
            models.append(ChatGroq(model=name, api_key=config.GROQ_API_KEY, temperature=0, max_retries=1, timeout=30))
    if config.GOOGLE_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI

        name = pick([config.GEMINI_MODEL, *GEMINI_FALLBACKS], _available("google"), rank=_gemini_rank)
        models.append(ChatGoogleGenerativeAI(
            model=name, google_api_key=config.GOOGLE_API_KEY, temperature=0, max_retries=1, timeout=30
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
def _chat(role: Role) -> Runnable:
    primary, *backups = _models(role)
    chain = primary.with_fallbacks(backups) if backups else primary
    # The planner has an instant keyword fallback, so only the answer is worth waiting for.
    return _patient(chain) if role == "answer" else chain


@lru_cache
def _structured_chain(role: Role, schema: type) -> Runnable:
    primary, *backups = (_structured(m, schema) for m in _models(role))
    return primary.with_fallbacks(backups) if backups else primary


_checked_at = time.monotonic()


def _refresh_if_stale() -> None:
    """Re-read the model lists every REFRESH_S, so retired models are swapped out while the server runs."""
    global _checked_at
    if time.monotonic() - _checked_at > REFRESH_S:
        _checked_at = time.monotonic()
        for cached in (_available, _chat, _structured_chain):
            cached.cache_clear()


def chat(role: Role) -> Runnable:
    _refresh_if_stale()
    return _chat(role)


def structured(role: Role, schema: type) -> Runnable:
    _refresh_if_stale()
    return _structured_chain(role, schema)


def provider_names() -> list[str]:
    return [f"{type(m).__name__}({getattr(m, 'model_name', None) or getattr(m, 'model', '')})" for m in _models("answer")]
