"""Toy LangGraph agent: the smallest version of the Week 2 agent, for learning.

A two-node graph with a loop:

    START -> agent --(asks for a tool?)--> tools -> agent -> ... -> END

- agent: the LLM reads the conversation and either answers or calls a tool
- tools: runs the tool calls and appends the results as messages
The real agent adds a planner, an evidence check and an answer composer, but the
pattern (state + nodes + conditional edges) is the same.

Runs on local Ollama (no API key) against the local Neo4j + Qdrant.

    python playground/toy_agent.py "What improved on RAG, and which papers proposed it?"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402
from langchain_core.tools import tool  # noqa: E402
from langchain_ollama import ChatOllama  # noqa: E402
from langgraph.graph import START, MessagesState, StateGraph  # noqa: E402
from langgraph.prebuilt import ToolNode, tools_condition  # noqa: E402
from neo4j import GraphDatabase  # noqa: E402

import qdrant_store  # noqa: E402
from config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, OLLAMA_MODEL, OLLAMA_URL  # noqa: E402

neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
qdrant = qdrant_store.client()


@tool
def search_papers(query: str, min_year: int | None = None) -> str:
    """Find papers whose title or abstract matches the query (semantic + keyword search).
    Use for "what does paper X say", "papers about Y". min_year limits to newer papers."""
    points = qdrant_store.search(qdrant, query, limit=5, min_year=min_year)
    return "\n".join(
        f"[{p.payload['arxiv_id']}] {p.payload['title']} ({p.payload['year']}): {p.payload['abstract'][:300]}"
        for p in points
    ) or "No papers found."


@tool
def methods_improving_on(method: str) -> str:
    """List methods that improve on or extend the given method (e.g. "RAG", "BERT"),
    with the papers that proposed them and the datasets they evaluated on."""
    records = neo4j_driver.execute_query(
        """
        MATCH (old:Method) WHERE toLower(old.name) = toLower($name)
           OR any(a IN coalesce(old.aliases, []) WHERE toLower(a) = toLower($name))
        MATCH (new:Method)-[:IMPROVES_ON]->(old)
        MATCH (p:Paper)-[:PROPOSES]->(new)
        OPTIONAL MATCH (p)-[:EVALUATES_ON]->(d:Dataset)
        RETURN new.name AS method, p.arxiv_id AS arxiv_id, p.title AS title, p.year AS year,
               collect(DISTINCT d.name) AS datasets
        ORDER BY year DESC LIMIT 15
        """,
        name=method,
    ).records
    return "\n".join(
        f"{r['method']}: [{r['arxiv_id']}] {r['title']} ({r['year']}); datasets: {', '.join(r['datasets']) or 'none'}"
        for r in records
    ) or f"No methods in the graph improve on '{method}'."


TOOLS = [search_papers, methods_improving_on]
SYSTEM = SystemMessage(
    "You answer questions about AI research papers using the tools. "
    "Use methods_improving_on for lineage questions and search_papers for everything else. "
    "Cite papers as [arxiv_id]. Only use facts from tool results."
)
llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_URL, temperature=0).bind_tools(TOOLS)


def agent(state: MessagesState) -> dict:
    return {"messages": [llm.invoke([SYSTEM, *state["messages"]])]}


def build_graph():
    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    # tools_condition routes to "tools" if the LLM asked for a tool, else to END.
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


def main() -> None:
    question = " ".join(sys.argv[1:]) or "What improved on RAG, and which datasets did those papers use?"
    print(f"Q: {question}\n")
    app = build_graph()
    # stream_mode="updates" yields each node's output as it finishes: the agent's steps.
    for update in app.stream({"messages": [HumanMessage(question)]}, {"recursion_limit": 8}, stream_mode="updates"):
        for node, output in update.items():
            message = output["messages"][-1]
            if node == "agent" and message.tool_calls:
                for call in message.tool_calls:
                    print(f"[agent] calls {call['name']}({call['args']})")
            elif node == "tools":
                for m in output["messages"]:
                    print(f"[tools] {m.name} returned {len(m.content.splitlines())} lines")
            else:
                print(f"\n[answer]\n{message.content}")
    neo4j_driver.close()


if __name__ == "__main__":
    main()
