import pytest

from app.agent.nodes import heuristic_plan


@pytest.mark.parametrize("question,intent", [
    ("Compare GraphRAG vs RAPTOR", "compare"),
    ("What improved on RAG?", "lineage"),
    ("What are the latest papers on agent memory?", "recent"),
    ("Most cited papers on dense retrieval", "top_cited"),
    ("Which benchmarks are used for multi-hop QA?", "dataset"),
    ("How does HyDE work?", "lookup"),
])
def test_keyword_fallback_intents(question, intent):
    assert heuristic_plan(question).intent == intent


def test_keyword_fallback_reads_year():
    plan = heuristic_plan("Papers on hallucination since 2024")
    assert plan.min_year == 2024
