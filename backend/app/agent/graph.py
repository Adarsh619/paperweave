"""Wire the nodes into a LangGraph state machine."""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import AgentState


@lru_cache
def build():
    g = StateGraph(AgentState)
    for name in ("plan", "retrieve", "check", "rewrite", "answer", "subgraph"):
        g.add_node(name, getattr(nodes, name))
    g.add_edge(START, "plan")
    g.add_edge("plan", "retrieve")
    g.add_edge("retrieve", "check")
    g.add_conditional_edges("check", nodes.route_after_check, {"rewrite": "rewrite", "answer": "answer"})
    g.add_edge("rewrite", "retrieve")
    g.add_edge("answer", "subgraph")
    g.add_edge("subgraph", END)
    return g.compile()


def run(question: str) -> AgentState:
    """Run the whole agent synchronously (CLI and tests). The API streams instead."""
    return build().invoke({"question": question}, {"recursion_limit": 20})


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    final = run(" ".join(sys.argv[1:]) or "What improved on RAG, and which datasets did those papers use?")
    for step in final["steps"]:
        print(f"[{step['node']}] {step['message']}")
    print(f"\n{final['answer']}\n")
    for c in final["citations"]:
        print(f"  [{c['arxiv_id']}] {c['title']} ({c['year']})")
