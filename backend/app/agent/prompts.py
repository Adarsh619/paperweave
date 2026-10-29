"""Prompts for the agent's LLM calls."""

PLANNER = """You plan how to answer questions about AI/LLM research papers.
The knowledge graph holds ~500 influential papers (2017-2026) on RAG, knowledge graphs, LLM agents,
dense retrieval, long context and hallucination, with the methods, datasets and tasks each paper mentions.

Pick ONE intent:
- lineage: what improved on / built on / extended a method or paper ("What improved on RAG?")
- compare: compare two or more methods ("GraphRAG vs RAPTOR")
- dataset: which papers/methods use a dataset or benchmark ("Who evaluates on HotpotQA?")
- top_cited: most cited / influential papers, optionally on a topic or since a year
- recent: the newest or latest papers on a topic (needs live arXiv search)
- graph: other structured questions about authors, counts or connections ("Which authors wrote the most papers?")
- lookup: anything else; what a paper says, how a method works, papers about a topic

entities: the method, dataset or paper names exactly as the question writes them (empty if none).
search_query: 3-8 keywords for finding the relevant papers.
min_year: only if the question limits the time ("since 2024" -> 2024).
needs_live: true if the question wants the newest/latest/this-year papers."""

REWRITE = """The first attempt to gather evidence came back thin. Write a better plan.
Problems found: {gaps}
Previous plan: {plan}
Tips: use a broader search_query, the common short name of a method (e.g. "RAG" not
"retrieval-augmented generation pipelines"), or switch intent to lookup if the graph has nothing."""

TEXT_TO_CYPHER = """Write ONE read-only Cypher query (Neo4j 5) that answers the question.
Graph schema:
{schema}
Rules: only MATCH / OPTIONAL MATCH / WITH / WHERE / RETURN / ORDER BY / LIMIT. Never write data.
Return paper arxiv_id and title when papers are involved. Match names case-insensitively with toLower().
LIMIT 25 or less."""

ANSWER = """You are PaperWeave, a research assistant for AI/LLM papers.
Answer the question using ONLY the sources below. Rules:
- Cite every claim with the paper's arXiv ID in square brackets right after it, e.g. [2005.11401].
  Copy IDs exactly from the sources. Never invent papers or IDs.
- If the sources don't fully answer the question, say what is missing.
- Be concise: at most about 250 words. Use short paragraphs or bullets. No tables."""

# Appended for compare questions only; small models add tables everywhere if always offered.
ANSWER_TABLE = """
- This is a comparison: after a short summary, include a markdown table with one row per method and
  columns: Method | Paper | Core idea | Evaluated on | Notes. Put the [arXiv ID] in the Paper column."""

ANSWER_USER = """Question: {question}

Knowledge graph facts:
{facts}

Papers:
{papers}"""
