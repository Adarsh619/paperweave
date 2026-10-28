# PaperWeave

> **See how AI research connects.**

PaperWeave is an agentic GraphRAG research assistant for AI/LLM papers. Ask a research question and a LangGraph agent combines a knowledge graph of papers, methods and datasets with semantic search and live arXiv search. It answers with citations and shows you the graph behind every answer.

**Status:** 🚧 In development. Week 1 is the data pipeline and graph. Papers, authors, citations and LLM-extracted methods, datasets and tasks load into Neo4j, and papers are indexed in Qdrant for hybrid (dense + BM25) search. The rebuild script and the full 500-paper run are next.

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
.venv/Scripts/python pipeline/extract_entities.py               # → data/entities_raw.jsonl (needs Ollama)
.venv/Scripts/python pipeline/normalize.py                      # → data/entities.jsonl + entity_index.jsonl
.venv/Scripts/python pipeline/load_neo4j.py                     # idempotent upsert
.venv/Scripts/python pipeline/check_graph.py                    # sanity checks
.venv/Scripts/python pipeline/load_qdrant.py                    # hybrid vector index (idempotent)
.venv/Scripts/python pipeline/check_search.py                   # dense vs BM25 vs hybrid results
```

Entity extraction runs a local LLM through [Ollama](https://ollama.com) (`qwen3:4b-instruct` by default; change `OLLAMA_MODEL` in `.env`). It takes about 15 seconds per paper on a 4 GB laptop GPU and is resumable: re-running skips papers already done. `normalize.py` merges spellings of the same entity (for example "Hotpot QA" and "HotpotQA", or "NQ" and "Natural Questions") and drops vague names. Review `data/entity_index.jsonl` to see what was merged.

`load_qdrant.py` stores each paper's title and abstract as one point with two vectors: a MiniLM embedding (meaning) and a BM25 sparse vector (exact terms such as "HotpotQA"). Search runs both and merges the rankings with Reciprocal Rank Fusion. Locally, `fastembed` computes the vectors on your CPU; the first run downloads about 100 MB of models. On Qdrant Cloud, set `QDRANT_CLOUD_INFERENCE=true` and the server embeds the text instead, so the backend never loads a model.

Paper metadata and citations come from the [Semantic Scholar API](https://api.semanticscholar.org). Topic searches are sorted by citation count, and every paper keeps its arXiv ID and links. Without an API key, Semantic Scholar allows about 100 requests per 5 minutes, which the scripts pace for automatically.

See [docs/PLAN.md](docs/PLAN.md) for the full plan.
