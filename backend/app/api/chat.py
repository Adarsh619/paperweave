"""POST /api/chat: run the agent and stream its progress as Server-Sent Events.

Events, in order:
  step       {node, message}       one per agent step, for the timeline
  token      {text}                answer tokens as the LLM writes them
  answer     {text}                final answer with citations verified (replaces the tokens)
  citations  [{arxiv_id, title, year, abs_url, source}]
  subgraph   {nodes, links}        for the graph view
  error      {message}             then the stream ends
  done       {cached}
"""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app import config
from app.agent.graph import build
from app.cache import AnswerCache
from app.ratelimit import RateLimiter

router = APIRouter()
log = logging.getLogger(__name__)
cache = AnswerCache(config.CACHE_PATH, config.CACHE_TTL_S)
BUSY = ("PaperWeave is at its free-tier AI limit right now. Please try again in a minute, "
        "or pick an example question; those are always available.")
limiter = RateLimiter(config.RATE_LIMIT_PER_HOUR)


class Turn(BaseModel):
    question: str = Field(max_length=500)
    answer: str = Field(max_length=6000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    # Earlier turns, sent by the browser so follow-ups work without server-side sessions
    # (free-tier servers restart and sleep, which would wipe them).
    history: list[Turn] = Field(default_factory=list, max_length=3)


def client_ip(request: Request) -> str:
    # Render and Vercel put the real client first in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def agent_events(question: str, history: list[dict]) -> AsyncIterator[tuple[str, object]]:
    """Run the agent, yielding (event, data). Steps come from node updates; tokens from the
    answer node's LLM stream."""
    final: dict = {}
    async for mode, chunk in build().astream(
        {"question": question, "history": history}, {"recursion_limit": 20}, stream_mode=["updates", "messages"]
    ):
        if mode == "messages":
            message, meta = chunk
            if meta.get("langgraph_node") == "answer" and message.text:
                yield "token", {"text": message.text}
            continue
        for update in chunk.values():
            for step in (update or {}).get("steps", []):
                yield "step", step
            final.update({k: v for k, v in (update or {}).items() if k in ("answer", "citations", "subgraph")})
    yield "answer", {"text": final.get("answer", "")}
    yield "citations", final.get("citations", [])
    yield "subgraph", final.get("subgraph", {"nodes": [], "links": []})


@router.post("/api/chat")
async def chat(body: ChatRequest, request: Request):
    question = body.question.strip()
    history = [t.model_dump() for t in body.history]
    # A follow-up's meaning depends on the conversation, so only standalone questions are cached.
    cached = None if history else cache.get(question)
    if cached is None:
        allowed, retry_after = limiter.check(client_ip(request))
        if not allowed:
            return JSONResponse(
                {"error": f"Rate limit reached ({config.RATE_LIMIT_PER_HOUR} new questions per hour). "
                          "Try an example question; those are always available."},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

    async def stream() -> AsyncIterator[str]:
        if cached is not None:
            for e in cached:
                yield sse(e["event"], e["data"])
            yield sse("done", {"cached": True})
            return
        events = []
        try:
            async for event, data in agent_events(question, history):
                yield sse(event, data)
                if event != "token":  # tokens are replaced by the final answer event
                    events.append({"event": event, "data": data})
        except Exception as exc:
            log.exception("agent failed for question %r", question)
            busy = "RateLimit" in type(exc).__name__ or "429" in str(exc)  # free-tier LLM limits, not a bug
            yield sse("error", {"message": BUSY if busy else "Something went wrong while answering. Please try again."})
            return
        if not history:
            cache.put(question, events)
        yield sse("done", {"cached": False})

    # X-Accel-Buffering stops proxies from holding the stream back until it ends.
    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
