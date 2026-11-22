import pytest

from app.agent.nodes import heuristic_plan


@pytest.mark.parametrize("question,intent", [
    ("Compare GraphRAG vs RAPTOR", "compare"),
    ("What improved on RAG?", "lineage"),
    ("What are the latest papers on agent memory?", "recent"),
    ("Most cited papers on dense retrieval", "top_cited"),
    ("Which benchmarks are used for multi-hop QA?", "dataset"),
    ("How does HyDE work?", "lookup"),
    ("What's the weather in Delhi?", "off_topic"),
    ("What is trending in computer vision?", "trend"),
    ("Write me an email to my landlord", "off_topic"),
])
def test_keyword_fallback_intents(question, intent):
    assert heuristic_plan(question).intent == intent


def test_keyword_fallback_reads_year():
    plan = heuristic_plan("Papers on hallucination since 2024")
    assert plan.min_year == 2024


def test_off_topic_routes_to_decline_without_retrieval(monkeypatch):
    """An off-topic plan goes straight to the fixed decline answer; no tool is ever called."""
    from app.agent import graph, nodes

    monkeypatch.setattr(nodes.llm, "structured", lambda *a: (_ for _ in ()).throw(RuntimeError("no LLM in tests")))
    for tool in ("retrieve", "answer", "subgraph"):
        monkeypatch.setattr(nodes, tool, lambda state, _t=tool: pytest.fail(f"{_t} should not run"))
    graph.build.cache_clear()
    try:
        final = graph.run("Tell me a joke about cats")
    finally:
        graph.build.cache_clear()
    assert final["plan"]["intent"] == "off_topic"
    assert final["answer"] == nodes.DECLINE
    assert final["citations"] == [] and final["subgraph"] == {"nodes": [], "links": []}


@pytest.mark.parametrize("score,intent", [(0.75, "lookup"), (0.30, "off_topic")])
def test_planner_off_topic_is_overruled_when_the_library_has_close_papers(monkeypatch, score, intent):
    """Small planners decline specialist physics questions; a close library match overrules that."""
    from app.agent import nodes
    from app.agent.state import Plan

    class Planner:
        def invoke(self, _messages):
            return Plan(intent="off_topic", search_query="")

    monkeypatch.setattr(nodes.llm, "structured", lambda *a: Planner())
    monkeypatch.setattr(nodes.vector_search, "best_match", lambda q: score)
    out = nodes.plan({"question": "What charge order was found in the kagome superconductor KV3Sb5?"})
    assert out["plan"]["intent"] == intent
    assert intent == "off_topic" or out["plan"]["search_query"]


@pytest.mark.parametrize("attempts,first", [(0, "the question as asked"), (1, "planner keywords")])
def test_search_puts_the_question_first_and_rewrites_first_after_a_retry(monkeypatch, attempts, first):
    """The question as asked is the strongest first signal; after a rewrite, the new keywords lead."""
    from app.agent import nodes

    seen = []
    monkeypatch.setattr(nodes.vector_search, "search", lambda q, **kw: seen.append(q) or [])
    plan = {"intent": "lookup", "entities": [], "search_query": "planner keywords", "min_year": None, "needs_live": False}
    nodes.retrieve({"question": "the question as asked", "plan": plan, "attempts": attempts})
    assert seen[0] == first and len(seen) == 2
