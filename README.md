# PaperWeave

> **See how AI research connects.**

PaperWeave is an agentic GraphRAG research assistant for AI/LLM papers. Ask a research question and a LangGraph agent combines a knowledge graph of papers, methods and datasets with semantic search and live arXiv search. It answers with citations and shows you the graph behind every answer.

**Status:** 🚧 In development. Week 1 is the data pipeline and graph. Papers, authors and citations are loading into Neo4j; entity extraction and vector indexing are next.

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

## Project structure (planned)

```
pipeline/   offline ingestion: fetch → extract entities → load graph + vectors
data/       snapshot used to rebuild the databases
backend/    FastAPI + LangGraph agent and tools
frontend/   Next.js app
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
.venv/Scripts/python pipeline/load_neo4j.py                     # idempotent upsert
.venv/Scripts/python pipeline/check_graph.py                    # sanity checks
```

Paper metadata and citations come from the [Semantic Scholar API](https://api.semanticscholar.org). Topic searches are sorted by citation count, and every paper keeps its arXiv ID and links. Without an API key, Semantic Scholar allows about 100 requests per 5 minutes, which the scripts pace for automatically.

See [docs/PLAN.md](docs/PLAN.md) for the full plan.
