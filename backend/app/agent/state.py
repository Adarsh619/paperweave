"""The agent's state: what each node reads and writes as the graph runs."""

import operator
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field

Intent = Literal["lookup", "lineage", "compare", "dataset", "top_cited", "recent", "graph"]


class Plan(BaseModel):
    """What the planner LLM decides. Code (not the LLM) then picks and runs the tools."""

    intent: Intent = Field(description="the kind of question")
    entities: list[str] = Field(
        default_factory=list, description="method, dataset or paper names in the question, as written"
    )
    search_query: str = Field(description="a short search query for finding relevant papers")
    min_year: int | None = Field(default=None, description="only papers from this year on, if the question says so")
    needs_live: bool = Field(default=False, description="true if the question asks for the newest/latest papers")


class CypherQuery(BaseModel):
    cypher: str = Field(description="one read-only Cypher query")


class AgentState(TypedDict, total=False):
    question: str
    plan: dict
    papers: dict[str, dict]  # arxiv_id -> paper shown to the answer LLM (insertion order = priority)
    facts: list[str]  # graph facts, each citing papers as [arxiv_id]
    gaps: list[str]  # what the evidence check found missing; drives the rewrite
    attempts: int
    answer: str
    citations: list[dict]
    subgraph: dict
    # Appended by every node; the API streams each one to the UI as a "step" event.
    steps: Annotated[list[dict], operator.add]
