# CLAUDE.md

Guidance for Claude Code working in this repository.

## Project

PaperWeave is an agentic GraphRAG research assistant over arXiv papers in AI, computer science, physics and math (30 topics in `pipeline/config.py` `TOPICS`, 9,153 papers in the v2 snapshot; v1 was 500 AI/LLM papers).
- **Offline pipeline** (`pipeline/`): builds a Neo4j knowledge graph and a Qdrant hybrid index from a committed `data/` snapshot.
- **Backend** (`backend/`): a LangGraph agent behind a streaming FastAPI API.
- **Frontend** (`frontend/`): Next.js.

Everything is designed for free tiers (Render, Vercel, AuraDB, Qdrant Cloud, Groq). See `README.md` for features and `docs/DEPLOY.md` for deployment.

## Git rules (from the owner)

- **Never commit, push or stage unless the user explicitly asks in the current request.** Approval for one commit does not carry over to the next.
- Leave changes uncommitted so the user can review them in VS Code Source Control.
- Never commit `.env`, `.env.local`, `backend/.cache/` or any API keys.

## Environment

- Windows. Use the repo venv: `.venv/Scripts/python`. Local Python is 3.14; the Docker image uses 3.12.
- `docker compose up -d` starts Neo4j (`localhost:7474`/`7687`, `neo4j` / `paperweave-dev`) and Qdrant (`localhost:6333`). Docker Desktop may need starting first.
- Ollama (`qwen3:4b-instruct`) runs locally for entity extraction, and for the agent when no `GROQ_API_KEY`/`GOOGLE_API_KEY` is set. Local answers take 1–2 minutes. **Models live in `D:\Ollama Storage`** (set in the Ollama app; drive C is nearly full). Don't download models to C:.
- Semantic Scholar is slow without `S2_API_KEY` (rate limits); `fetch_papers.py` caches each topic-year in `data/.s2_cache/`, so re-runs resume.
- **Port 8000 is used by another project.** Run the API on **8010**. The frontend runs on 3000, which matches the default `CORS_ORIGINS`.
- Config comes from the repo-root `.env` (template: `.env.example`). The frontend uses `frontend/.env.local` with `NEXT_PUBLIC_API_URL`.

## Commands

Pipeline (run from the repo root):

```bash
.venv/Scripts/python pipeline/rebuild.py [--fresh]   # load Neo4j + Qdrant from data/ (no API calls)
.venv/Scripts/python pipeline/check_graph.py         # graph sanity checks
.venv/Scripts/python pipeline/check_search.py        # search sanity checks (expects 7/7 in hybrid top 5)
.venv/Scripts/python pipeline/export_stats.py        # frontend/public/stats.json (coverage on the site)
# Full rebuild of the snapshot, unattended and resumable (hours: S2 rate limits + ~18 h of Ollama for 10K):
bash pipeline/build_all.sh   # fetch -> citations -> extract -> normalize -> rebuild --fresh -> stats -> checks
```

Backend (run from `backend/`):

```bash
../.venv/Scripts/python -m pytest -q                                  # 58 tests, no DB/LLM needed
../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8010
../.venv/Scripts/python -m app.agent.graph "Compare GraphRAG and RAPTOR"   # CLI run of the agent
../.venv/Scripts/python -m evals.run_eval [--answers] [--only C01,M02]
../.venv/Scripts/python scripts/export_examples.py                    # regenerates frontend/public/examples.json
```

Frontend (run from `frontend/`): `npm run dev`, `npm run lint`, `npm run build`.

## Architecture notes

- **Agent** (`backend/app/agent/`): `plan → retrieve → check → (rewrite ≤2) → answer → subgraph`; `plan → decline → END` for off-topic questions.
  - The LLM only fills a JSON `Plan` (intent and entities). Plain code in `nodes.retrieve` picks the tools. Keep it that way: small models are unreliable at free-form tool calling.
  - Intents: lookup, lineage, compare, dataset, top_cited, recent, graph, trend, off_topic. `heuristic_plan` is the keyword fallback when the planner LLM fails.
  - Follow-ups: the browser sends the last ≤3 turns as `history`; `plan` rewrites the question to stand alone (`CONTEXTUALIZE` prompt). No server-side sessions (free tiers restart). Follow-ups are never cached.
- **Trends** (`graph_query.trends`, `/api/trends`, `frontend/app/trends`): topic growth from Semantic Scholar volume on `Topic.years/counts`, method share change, breakout papers. Measurements only, never forecasts. Equal per-(topic, year) quotas in `fetch_papers.py` are what make per-year shares comparable; keep them.
- **Tools** (`backend/app/tools/`):
  - Cypher templates in `cypher_templates.py`
  - `graph_query.py`: entity resolution with a `prefer` kind, and a title-match fallback for a method's origin paper
  - `vector_search.py`: hybrid MiniLM + BM25 search with RRF
  - `arxiv_live.py`: live arXiv search with a Semantic Scholar fallback
- **Safety:**
  - Every Cypher query goes through `stores.read()`, which runs a READ transaction with a 10 s timeout.
  - LLM-written Cypher must also pass `cypher_guard.check()`.
  - Answers pass through `citations.validate()`, which repairs or drops arXiv IDs not in the evidence.
- **API** (`backend/app/api/chat.py`): SSE events `step`, `token`, `answer`, `citations`, `subgraph`, `error`, `done`.
  - The frontend types for these events live in `frontend/lib/types.ts`. Change both together.
  - There is a SQLite answer cache and a per-IP rate limit; cached questions don't count toward the limit.
- **Qdrant:** the index layout is shared by `pipeline/qdrant_store.py` and `backend/app/tools/vector_search.py`.
  - Locally, fastembed embeds the text. On Qdrant Cloud, set `QDRANT_CLOUD_INFERENCE=true`.
  - Model names are overridable with `QDRANT_DENSE_MODEL` and `QDRANT_SPARSE_MODEL`.
- **Example questions:** `EXAMPLE_QUESTIONS` in `frontend/lib/examples.ts` and `QUESTIONS` in `backend/scripts/export_examples.py` must stay identical.
- **Data quality:** entities come from a 4B model and are noisy. Fix entity-name problems in `pipeline/normalize.py`, which handles aliases, generic names and abbreviation rules. Then re-run `normalize.py` and `rebuild.py`. Don't patch individual graph nodes.

## Frontend

- Next.js 16 with Cache Components enabled. **Read `frontend/AGENTS.md`** and the docs in `frontend/node_modules/next/dist/docs/` before writing Next.js code; the APIs differ from older versions.
- Client components that use `useSearchParams` or `useParams` must render inside `<Suspense>` (see `app/ask/page.tsx` and `app/paper/[id]/page.tsx`).
- The ESLint rule `react-hooks/set-state-in-effect` is enforced. Reset state by remounting with a `key`, not by calling setState at the top of an effect.
- The force graph needs `window`. `ForceGraphCanvas` is loaded with `dynamic(..., { ssr: false })` from `GraphView`.
- Design: "paper & ink" editorial look. Colors are tokens in `app/globals.css` (light + dark); serif headings use `font-serif` (Fraunces). Don't hardcode colors; use tokens like `bg-accent text-on-accent`.
- `components/reactbits/` is vendored from reactbits.dev (Threads, SpotlightCard, BlurText, CountUp), kept as published; `eslint.config.mjs` relaxes two React Compiler rules for that folder only. Site-specific wrappers live in `components/Motion.tsx`. Use animation sparingly; motion respects the OS reduce-motion setting.
- `public/stats.json` (coverage) is generated by `pipeline/export_stats.py`; `public/examples.json` by `backend/scripts/export_examples.py`.

## Style

- Match the existing code: short docstrings explaining *why*, comments only where intent isn't obvious, and type hints throughout the Python.
- Run `pytest` (backend) and `npm run lint && npm run build` (frontend) before saying work is done.
