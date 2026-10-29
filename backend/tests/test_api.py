"""API tests with the databases and agent replaced by fakes, so they run without Docker or an LLM."""

import json

import pytest
from fastapi.testclient import TestClient

from app import main
from app.api import chat
from app.cache import AnswerCache
from app.ratelimit import RateLimiter


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(chat, "cache", AnswerCache(tmp_path / "c.sqlite", ttl_s=60))
    monkeypatch.setattr(chat, "limiter", RateLimiter(limit=2))
    return TestClient(main.app)


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_health_ok_touches_both_databases(client, monkeypatch):
    monkeypatch.setattr(main, "check_databases", lambda: {"papers": 500, "vectors_ok": True})
    resp = client.get("/health")
    assert resp.status_code == 200 and resp.json()["status"] == "ok"


def test_health_degraded_when_a_database_fails(client, monkeypatch):
    monkeypatch.setattr(main, "check_databases", lambda: {"papers": 500, "qdrant_error": "ConnectError"})
    resp = client.get("/health")
    assert resp.status_code == 503 and resp.json()["status"] == "degraded"


def fake_agent(calls):
    async def agent_events(question):
        calls.append(question)
        yield "step", {"node": "plan", "message": "Planned"}
        yield "token", {"text": "Hel"}
        yield "answer", {"text": "Hello [2005.11401]"}
        yield "citations", [{"arxiv_id": "2005.11401"}]
        yield "subgraph", {"nodes": [], "links": []}
    return agent_events


def test_chat_streams_events_then_replays_from_cache(client, monkeypatch):
    calls = []
    monkeypatch.setattr(chat, "agent_events", fake_agent(calls))

    first = parse_sse(client.post("/api/chat", json={"question": "What is RAG?"}).text)
    assert [e for e, _ in first] == ["step", "token", "answer", "citations", "subgraph", "done"]
    assert first[-1][1] == {"cached": False}

    second = parse_sse(client.post("/api/chat", json={"question": "what is rag"}).text)
    assert calls == ["What is RAG?"]  # agent not run again
    assert "token" not in [e for e, _ in second]
    assert second[-1][1] == {"cached": True}


def test_rate_limit_applies_to_new_questions_only(client, monkeypatch):
    monkeypatch.setattr(chat, "agent_events", fake_agent([]))
    for q in ("question one", "question two"):
        assert client.post("/api/chat", json={"question": q}).status_code == 200
    assert client.post("/api/chat", json={"question": "question three"}).status_code == 429
    assert client.post("/api/chat", json={"question": "question one"}).status_code == 200  # cached


def test_chat_validates_input(client):
    assert client.post("/api/chat", json={"question": "x"}).status_code == 422
    assert client.post("/api/chat", json={"question": "x" * 501}).status_code == 422


def test_agent_failure_becomes_error_event_and_is_not_cached(client, monkeypatch):
    async def broken(question):
        yield "step", {"node": "plan", "message": "Planned"}
        raise RuntimeError("LLM down")

    monkeypatch.setattr(chat, "agent_events", broken)
    events = parse_sse(client.post("/api/chat", json={"question": "Will this fail?"}).text)
    assert events[-1][0] == "error"
    assert chat.cache.get("Will this fail?") is None


def test_paper_id_is_validated(client):
    assert client.get("/api/papers/not-an-id").status_code == 422
