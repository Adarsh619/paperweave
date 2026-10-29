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
limiter = RateLimiter(config.RATE_LIMIT_PER_HOUR)


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


def client_ip(request: Request) -> str:
    # Render and Vercel put the real client first in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def agent_events(question: str) -> AsyncIterator[tuple[str, object]]:
    """Run the agent, yielding (event, data). Steps come from node updates; tokens from the
    answer node's LLM stream."""
    final: dict = {}
    async for mode, chunk in build().astream(
        {"question": question}, {"recursion_limit": 20}, stream_mode=["updates", "messages"]
    ):
        if mode == "messages":
            message, meta = chunk
            if meta.get("langgraph_node") == "answer" and message.content:
                yield "token", {"text": message.content}
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
    cached = cache.get(question)
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
            async for event, data in agent_events(question):
                yield sse(event, data)
                if event != "token":  # tokens are replaced by the final answer event
                    events.append({"event": event, "data": data})
        except Exception:
            log.exception("agent failed for question %r", question)
            yield sse("error", {"message": "Something went wrong while answering. Please try again."})
            return
        cache.put(question, events)
        yield sse("done", {"cached": False})

    # X-Accel-Buffering stops proxies from holding the stream back until it ends.
    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
