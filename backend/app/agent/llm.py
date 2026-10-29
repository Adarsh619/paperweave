"""Chat models with automatic fallback: Groq -> Gemini -> local Ollama.

"router" is the fast model for planning; "answer" is the strong model for writing.
Providers without an API key are skipped, so local development runs on Ollama alone.
"""

from functools import lru_cache
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from app import config

Role = Literal["router", "answer"]


def _models(role: Role) -> list[BaseChatModel]:
    models: list[BaseChatModel] = []
    if config.GROQ_API_KEY:
        from langchain_groq import ChatGroq

        name = config.GROQ_ROUTER_MODEL if role == "router" else config.GROQ_ANSWER_MODEL
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


@lru_cache
def chat(role: Role) -> Runnable:
    primary, *backups = _models(role)
    return primary.with_fallbacks(backups) if backups else primary


@lru_cache
def structured(role: Role, schema: type) -> Runnable:
    primary, *backups = (_structured(m, schema) for m in _models(role))
    return primary.with_fallbacks(backups) if backups else primary


def provider_names() -> list[str]:
    return [type(m).__name__ for m in _models("answer")]
