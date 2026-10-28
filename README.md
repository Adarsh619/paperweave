# PaperWeave

> **See how AI research connects.**

PaperWeave is an agentic GraphRAG research assistant for AI/LLM papers. Ask a research question and a LangGraph agent combines a knowledge graph of papers, methods and datasets with semantic search and live arXiv search. It answers with citations and shows you the graph behind every answer.

**Status:** 🚧 In development. Week 1 is the data pipeline and graph.

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

See [docs/PLAN.md](docs/PLAN.md) for the full plan.
