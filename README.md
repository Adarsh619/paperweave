# PaperWeave

> **See how AI research connects.**

PaperWeave is an agentic GraphRAG research assistant for AI/LLM papers. Ask a research question and a LangGraph agent combines a knowledge graph of papers, methods and datasets with semantic search and live arXiv search. It answers with citations and shows you the graph behind every answer.

**Status:** 🚧 In development. Week 1 (data pipeline) is done. The graph holds 500 papers, 4,829 authors, 4,172 citations and 2,653 LLM-extracted methods, datasets and tasks in Neo4j. Papers are indexed in Qdrant for hybrid (dense + BM25) search, and `rebuild.py` restores both databases from the `data/` snapshot. Week 2 (agent + backend) is built: a LangGraph agent with graph, search and live arXiv tools behind a streaming FastAPI API. Week 3 is the Next.js frontend, evals and deployment.

## Planned features

- An agent that plans each question and picks its tools: hybrid vector search, knowledge-graph queries and live arXiv search.
- A knowledge graph of about 500 AI/LLM papers, with citations, methods, datasets and "improves on" links.
- Streaming answers with arXiv citations, plus comparison tables for "compare X vs Y" questions.
- An interactive graph view of the papers and methods used in each answer.
- Evals comparing the GraphRAG agent against vector-only RAG.
- A public demo with no login, running 24/7 on free tiers.

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Next.js, Tailwind, shadcn/ui, react-force-graph (Vercel) |
| Backend | FastAPI, LangGraph, Docker (Render) |
| Graph DB | Neo4j AuraDB |
| Vector DB | Qdrant Cloud (hybrid dense + BM25) |
| LLM | Groq (Llama 3.3 70B), Gemini Flash fallback; Ollama for the offline graph build |
| Data | arXiv API, Semantic Scholar API |
| Evals | RAGAS, Langfuse |

## Project structure

```
pipeline/   offline ingestion: fetch → extract entities → load graph + vectors
data/       snapshot used to rebuild the databases
playground/ toy LangGraph agent (learning step before the real backend)
backend/    FastAPI + LangGraph agent
  app/agent/  plan → retrieve → check → rewrite → answer → subgraph
  app/tools/  hybrid search, Cypher templates + read-only guard, live arXiv
  app/api/    /api/chat (SSE), /api/papers, /api/graph
  tests/      pytest
frontend/   Next.js app (Week 3)
docs/       plan and architecture notes
```

## Run the pipeline locally

You need Docker and Python 3.11 or newer.

```bash
cp .env.example .env
docker compose up -d                      # Neo4j (localhost:7474) + Qdrant (localhost:6333)
python -m venv .venv
.venv/Scripts/pip install -r pipeline/requirements.txt   # macOS/Linux: .venv/bin/pip

.venv/Scripts/python pipeline/fetch_papers.py --max-papers 50   # → data/papers.jsonl
.venv/Scripts/python pipeline/fetch_citations.py                # → data/citations.jsonl
.venv/Scripts/python pipeline/extract_entities.py               # → data/entities_raw.jsonl (needs Ollama)
.venv/Scripts/python pipeline/normalize.py                      # → data/entities.jsonl + entity_index.jsonl
.venv/Scripts/python pipeline/load_neo4j.py                     # idempotent upsert
.venv/Scripts/python pipeline/check_graph.py                    # sanity checks
.venv/Scripts/python pipeline/load_qdrant.py                    # hybrid vector index (idempotent)
.venv/Scripts/python pipeline/check_search.py                   # dense vs BM25 vs hybrid results
```

### Rebuild the databases from the snapshot

`data/` holds the full pipeline output, so you can restore both databases without calling Semantic Scholar or Ollama. This is the recovery path if a free-tier database is wiped. Set `NEO4J_*` and `QDRANT_*` in `.env` to point it at production.

```bash
.venv/Scripts/python pipeline/rebuild.py            # upsert into Neo4j + Qdrant
.venv/Scripts/python pipeline/rebuild.py --fresh    # wipe both first
```

### Toy agent

[`playground/toy_agent.py`](playground/toy_agent.py) is a minimal LangGraph agent: an LLM node and a tool node in a loop. It has two tools, hybrid paper search and a graph lineage query, and runs on local Ollama. It's the starting point for the Week 2 agent.

```bash
.venv/Scripts/pip install -r playground/requirements.txt
.venv/Scripts/python playground/toy_agent.py "What improved on RAG, and which datasets did those papers use?"
```

## Backend: agent + API

The backend is a LangGraph agent behind a FastAPI app that streams Server-Sent Events.

```
plan → retrieve → check ──(evidence thin, max 2 retries)──► rewrite → retrieve
                       └──(enough)──► answer → subgraph
```

- **plan**: a fast LLM classifies the question (lineage, compare, dataset, top-cited, recent, graph or lookup) and pulls out the names it mentions. If the LLM fails, a keyword fallback takes over.
- **retrieve**: code, not the LLM, runs the tools that fit the plan:
  - Cypher templates for lineage, comparisons, dataset users and top-cited papers
  - LLM-written Cypher for other graph questions, behind a read-only guard
  - hybrid vector search
  - live arXiv search for "latest" questions, with Semantic Scholar as a fallback
- **check**: if the evidence is thin, the planner rewrites the query and tries again, up to 2 times.
- **answer**: the strong LLM writes a cited answer, with a table for comparisons. Every `[arXiv ID]` is then checked against the evidence: garbled IDs are repaired and invented ones removed.
- **subgraph**: returns the papers, methods and datasets behind the answer for the graph view.

Safety and free-tier limits:
- Every Cypher query runs in a read-only transaction with a 10-second timeout.
- New questions are limited to 15 per hour per IP.
- Repeat questions are served from a SQLite cache.
- `/health` makes a real read on both databases, so uptime pings keep them from pausing.

| Endpoint | What it returns |
|---|---|
| `POST /api/chat` `{"question": "..."}` | SSE stream: `step`, `token`, `answer`, `citations`, `subgraph`, `done` (or `error`) |
| `GET /api/papers/{arxiv_id}` | Paper card: metadata, authors, methods, datasets, citation counts |
| `GET /api/graph/paper/{arxiv_id}` | The paper's neighborhood as graph nodes and links |
| `GET /health` | `200` when Neo4j and Qdrant both answer, else `503` |

```bash
.venv/Scripts/pip install -r backend/requirements-dev.txt
cd backend
../.venv/Scripts/python -m pytest                                   # 41 tests, no databases needed
../.venv/Scripts/python -m app.agent.graph "Compare GraphRAG, RAPTOR and HippoRAG"   # CLI run
../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8010              # API + docs at /docs
```

LLMs are tried in order: Groq, then Gemini, then local Ollama. Put `GROQ_API_KEY` and/or `GOOGLE_API_KEY` in `.env`; with neither, everything runs on Ollama. That works, but takes 1–2 minutes per answer on a laptop GPU, compared with a few seconds on Groq. The production image (`backend/Dockerfile`) uses about 150 MB of RAM, within Render's 512 MB free tier.

## Notes on the pipeline

Entity extraction runs a local LLM through [Ollama](https://ollama.com) (`qwen3:4b-instruct` by default; change `OLLAMA_MODEL` in `.env`). It takes about 6–11 seconds per paper on a 4 GB laptop GPU (about 50 minutes for 500 papers) and is resumable: re-running skips papers already done. `normalize.py` merges spellings of the same entity (for example "Hotpot QA" and "HotpotQA", or "NQ" and "Natural Questions") and drops vague names. Review `data/entity_index.jsonl` to see what was merged.

`load_qdrant.py` stores each paper's title and abstract as one point with two vectors: a MiniLM embedding (meaning) and a BM25 sparse vector (exact terms such as "HotpotQA"). Search runs both and merges the rankings with Reciprocal Rank Fusion. Locally, `fastembed` computes the vectors on your CPU; the first run downloads about 100 MB of models. On Qdrant Cloud, set `QDRANT_CLOUD_INFERENCE=true` and the server embeds the text instead, so the backend never loads a model.

Paper metadata and citations come from the [Semantic Scholar API](https://api.semanticscholar.org). Topic searches are sorted by citation count, and every paper keeps its arXiv ID and links. Without an API key, Semantic Scholar allows about 100 requests per 5 minutes, which the scripts pace for automatically.

See [docs/PLAN.md](docs/PLAN.md) for the full plan.
