"""Prompts for the agent's LLM calls."""

PLANNER = """You plan how to answer questions about research papers.
The knowledge graph holds influential arXiv papers (2017-2026) in AI (language models, RAG, agents,
retrieval, vision, image generation, reinforcement learning, robotics, speech...), computer science
(security, systems, databases, software engineering, algorithms), physics (quantum computing, condensed
matter, astrophysics, particle physics, gravitational waves) and math & statistics, with the methods,
datasets and tasks each paper mentions.

Pick ONE intent:
- lineage: what improved on / built on / extended a method or paper ("What improved on RAG?")
- compare: compare two or more methods ("GraphRAG vs RAPTOR")
- dataset: which papers/methods use a dataset or benchmark ("Who evaluates on HotpotQA?")
- top_cited: most cited / influential papers, optionally on a topic or since a year
- recent: the newest or latest papers on a topic (needs live arXiv search)
- trend: what is rising, growing, emerging or hot in a field or topic ("What's trending in computer vision?");
  put the field or topic name in entities
- graph: other structured questions about authors, counts or connections ("Which authors wrote the most papers?")
- lookup: anything else about research; what a paper says, how a method works, papers about a topic
- off_topic: not a question about research papers at all: chit-chat, coding help, writing tasks, news,
  products, prices, personal advice, or fields outside the library such as medicine or economics.
  Any question about a scientific experiment, observation, material, particle, telescope or theory in
  physics or math is NOT off_topic, however specialised ("What did DESI find about dark energy?" -> lookup)

entities: the method, dataset or paper names exactly as the question writes them (empty if none).
search_query: 3-8 keywords for finding the relevant papers.
min_year: only if the question limits the time ("since 2024" -> 2024).
needs_live: true if the question wants the newest/latest/this-year papers."""

CONTEXTUALIZE = """Rewrite the user's latest message as a standalone question about research papers,
using the conversation so far to resolve references like "it", "the second one" or "what about since 2024?".
Keep names exactly as written. If it already stands alone, return it unchanged.
Reply with the question only."""

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
