# Final Plan: PaperWeave, an agentic GraphRAG research assistant

> **PaperWeave**: *"See how AI research connects."*
> Ask questions about AI/LLM research papers. An agent weaves together a knowledge graph, semantic search and live arXiv to answer with citations, and shows you the graph behind every answer.

---

## 1. Context: why this project

- **The need:** a new portfolio project in `D:\RAG Projects`, picked from 8 RAG ideas.
- **The goal:** **Full-stack + AI** roles.

**What we agreed:**
- **Free tiers only**: no paid APIs or hosting. Hugging Face Docker/Gradio Spaces are out ($9/mo).
- **2–3 weeks** to a **public live demo** that stays up 24/7.
- **Skills**: strong in React/Next.js. Comfortable with Python, FastAPI and Docker. New to LangChain/LlamaIndex, so this project teaches **LangGraph**.
- **Must be clearly different** from your existing **Groundwork** (`D:\Own Project Builds\RAG-Knowledge-Assistant`), a TypeScript Next.js + Supabase pgvector "chat with your PDFs" app.

**Which of the 8 ideas it covers:**
- **Core:** #2 GraphRAG, #6 Agentic RAG, #1 Multi-Document (500 papers).
- **Supporting:** #3 local open-source LLM (Ollama builds the graph offline).
- **Stretch:** #7 Multimodal (figures and tables from papers), #5 Multilingual questions.
- **Not used:** #4 and #8 (upload-and-chat). Groundwork already covers them.

---

## 2. What PaperWeave does

**The problem it solves:** questions like these need connections across many papers, and plain vector RAG answers them badly:
- *"Which methods improved on standard RAG retrieval since 2024, and what benchmarks did they report?"*
- *"Compare GraphRAG, RAPTOR and HippoRAG: approach, datasets, limitations."*
- *"Which influential papers built on 'Attention Is All You Need' for long context?"*

**How it answers.** A **LangGraph agent** plans the question and picks one or more tools:
1. **Semantic + keyword search** (Qdrant) over abstracts and sections, for "what does paper X say".
2. **Knowledge graph queries** (Neo4j) for lineage, comparison and "who used which dataset". The graph holds:
   - `Paper –CITES→ Paper`
   - `Paper –PROPOSES→ Method`
   - `Paper –EVALUATES_ON→ Dataset`
   - `Method –IMPROVES_ON→ Method`
   - `Author –WROTE→ Paper`
3. **Live arXiv search** for papers newer than the indexed corpus.

It then checks whether the evidence is enough, rewriting the query and retrying up to 2 times. Finally it writes a **cited answer**, plus a **comparison table** when you ask it to compare.

**The visitor's experience** (no login):
- Open the link and click an example question, or type your own.
- Watch the agent's steps stream in live.
- Read the cited answer.
- Explore the **interactive graph** of the papers and methods it used. Click a node to open a paper card that links to arXiv.

### How it differs from Groundwork

| | Groundwork | PaperWeave |
|---|---|---|
| Product | Private chat with your own PDFs | Public research assistant over curated AI papers |
| Retrieval | Vector-only (pgvector) | **GraphRAG**: knowledge graph + hybrid vector/BM25 + live arXiv |
| Reasoning | Single-shot RAG, fixed modes | **Agentic** (LangGraph): planning, multi-tool, multi-hop, self-check |
| Stack | TypeScript-only Next.js | **Python FastAPI + LangGraph** backend + Next.js frontend |
| Data | User uploads | Pipeline: arXiv + Semantic Scholar → LLM entity extraction → graph |
| LLM | Local Ollama / Transformers.js | Groq live (Gemini fallback), Ollama offline for graph build |
| Output | Text + source excerpts | Streaming answer, comparison tables, **interactive graph** |
| Quality | Unit tests | Unit tests + **RAGAS evals: GraphRAG vs vector-only** |
| Deploy | Local | **Public 24/7 URL** (Vercel + Render) |

---

## 3. Tech stack (all free; limits checked Oct 2026, confirm at signup)

| Layer | Choice | Free-tier notes |
|---|---|---|
| Frontend | **Next.js 15 + Tailwind + shadcn/ui + `react-force-graph`** on **Vercel Hobby** | Never sleeps |
| Backend | **FastAPI** in **Docker** on **Render free** | 512 MB / 0.1 CPU, 750 hrs/mo (24/7 uses about 744). Sleeps after 15 min idle unless pinged. Fallback host: Koyeb free |
| Agent | **LangGraph** + LangChain integrations (Neo4j, Qdrant, Groq) | |
| Graph DB | **Neo4j AuraDB Free** | About 200K nodes / 400K rels / 1 GB. **Pauses after 3 days idle** |
| Vector DB | **Qdrant Cloud Free** (1 GB) + **free Cloud Inference** (MiniLM dense + BM25) | Qdrant embeds the text, so no model runs in 512 MB. **Suspended after 1 week idle, deleted after 4 weeks** |
| Live LLM | **Groq**: `llama-3.3-70b-versatile` for answers, `llama-3.1-8b-instant` for routing. **Gemini Flash** free as fallback | About 30 RPM, 6–12K TPM |
| Offline graph build | **Ollama** on your PC (Qwen 7B/8B class) | One-time job, no cost |
| Data sources | **arXiv API**, **Semantic Scholar API** (citations; about 100 req/5 min without a key) | |
| Cache / rate limit | SQLite in the container (rebuilt on deploy) for v1 | No extra service that could pause |
| Evals / tracing | **RAGAS**, **Langfuse Cloud** free | |
| Uptime | **UptimeRobot** free (pings every 5–10 min, emails on downtime); GitHub Actions cron as backup | |
| CI/CD | GitHub Actions (lint, tests); Vercel and Render auto-deploy on push | |

---

## 4. Architecture

```
OFFLINE (your PC; run once, refresh when you like)
 Semantic Scholar ─► ~500 arXiv AI/LLM papers (2017–2026, most-cited per topic + landmark seed list)
 Semantic Scholar ─► citation edges between them
 Ollama ─► extract Methods / Datasets / Tasks / IMPROVES_ON (strict JSON schema, alias merging)
   ├─► data/ snapshot (JSON, committed to GitHub → used for rebuilds)
   ├─► Neo4j AuraDB
   └─► Qdrant Cloud (chunks + payload: paper_id, title, year)

ONLINE (24/7)
 Browser ─► Vercel (Next.js; also holds saved example answers)
              └─► Render (FastAPI, SSE stream)
                    └─ LangGraph agent: plan → tools [vector_search | graph_query | arxiv_live]
                         → evidence check (rewrite ≤2) → answer + citations + table + subgraph
                    └─ Groq → Gemini fallback · SQLite answer cache · per-IP rate limit
 UptimeRobot ─► /health every ~10 min (runs a tiny Neo4j query + Qdrant search)
```

---

## 5. 24/7 live deployment and upkeep (as agreed)

**How it stays awake automatically**
- UptimeRobot calls `/health` every 5–10 minutes. That keeps Render awake.
- `/health` does **real database work** (one Neo4j query and one Qdrant search), so neither database counts as idle and neither pauses.
- GitHub Actions cron is only a backup. GitHub disables schedules in repos with no activity for 60 days, and its timing is unreliable.

**Safety nets**
- **Saved example answers:** the 10 example questions and their answers are also stored in the frontend on Vercel, so the demo works even if the backend is down.
- **Waking state:** the UI shows "Waking up the server…" instead of an error.
- **Rebuild script:** `pipeline/rebuild.py` reloads Neo4j and Qdrant from the `data/` snapshot in GitHub within minutes, in case a free database is wiped.
- **Abuse protection:** no login and no uploads; per-IP rate limit of about 15 questions/hour; a guard that only allows read-only Cypher.

**Your routine**
- **Weekly:** open the bookmark and **type one new question**. Example questions are answered from saved copies, so clicking them doesn't wake the databases.
- **When an alert email arrives:** resume the paused service in its console, or run the rebuild script. **Act within a few days**, because Qdrant deletes a suspended cluster after 4 weeks.
- **At account signup:** mark Neo4j, Qdrant, Render and UptimeRobot emails as "not spam".
- **Monthly (2 min):** check the UptimeRobot dashboard and Render's usage page.

**Caveat:** free tiers are always on in practice, not guaranteed, and providers can change their rules. If that ever matters, Render's paid instance (about $7/mo) removes sleep and the hours limit.

---

## 6. Project layout (`D:\RAG Projects\paperweave\`)
```
pipeline/   fetch_papers.py, fetch_citations.py, extract_entities.py, normalize.py,
            load_neo4j.py, load_qdrant.py, rebuild.py, schema.cypher, config.py
data/       papers.jsonl, citations.jsonl, entities.jsonl   (snapshot for rebuilds)
backend/    app/main.py (incl. /health), config.py, ratelimit.py, cache.py
            app/agent/{graph.py, state.py, nodes.py, prompts.py, llm.py}
            app/tools/{vector_search.py, graph_query.py, cypher_templates.py, cypher_guard.py, arxiv_live.py}
            app/api/{chat.py (SSE), papers.py, graph.py}
            tests/, evals/{golden.jsonl, run_ragas.py}, Dockerfile, requirements.txt
frontend/   app/page.tsx (hero + example questions), app/ask/[id], app/paper/[id]
            components/{ChatStream, AgentSteps, CitationList, ComparisonTable, GraphView, PaperCard, WakingBanner}
            public/examples.json (saved example answers)
docker-compose.yml   (backend + local Neo4j + local Qdrant)
.github/workflows/{ci.yml, keep-warm.yml}
README.md
```

---

## 7. Build plan (3 weeks)

**Week 1: data pipeline and graph**
1. Scaffold the repo and docker-compose with local Neo4j and Qdrant. Build a toy LangGraph agent to learn the basics.
2. Fetch about 500 papers from arXiv, then get the citation edges between them from Semantic Scholar.
3. Extract entities with Ollama into a strict JSON schema, and merge aliases (for example, "RAG" = "Retrieval-Augmented Generation"). Save the snapshot to `data/`.
4. Load Neo4j and Qdrant. Sanity-check with hand-written Cypher queries.

**Week 2: agent and backend**
5. Build the tools:
   - hybrid vector search
   - Cypher templates for lineage, method comparison, datasets used and top-cited papers
   - text-to-Cypher behind the read-only guard
   - live arXiv search
6. Build the LangGraph agent: router/planner, tool calls, evidence check with the rewrite loop, answer composer (citations and tables), and subgraph extraction.
7. Add the FastAPI SSE endpoint, streaming `step`, `token`, `citations` and `subgraph` events. Add the cache, rate limiting and `/health`.

**Week 3: frontend, evals, launch**
8. Build the Next.js UI:
   - landing page with example questions
   - streaming answer
   - agent-steps timeline
   - comparison table
   - interactive graph and paper cards
   - waking banner
9. Run evals on 30 golden questions (lookup, multi-hop and comparison). Compare **vector-only vs the PaperWeave agent** using RAGAS plus hand-scoring, and put the table in the README.
10. Deploy, in this order:
    1. Load Neo4j Aura and Qdrant Cloud.
    2. Put the backend on Render.
    3. Put the frontend on Vercel.
    4. Set up UptimeRobot and the keep-warm workflow.
    5. Export the saved example answers.
    6. Test in an incognito window.
11. Write the README (architecture diagram, demo GIF, eval table, live link) and a LinkedIn post.

**Stretch (v2):** extract figures and tables from PDFs, export a literature review to Markdown, pull new arXiv papers in weekly, support multilingual questions.

---

## 8. Verification
- **Pipeline:** check node and edge counts, confirm there are no orphan Method nodes, and confirm known facts exist (for example, RAG → GraphRAG lineage).
- **`pytest`:**
  - the Cypher guard rejects write queries
  - tool outputs have the right shape
  - the rate limiter works
  - the cache hits
  - `/health` touches both databases
- **Local end-to-end** (`docker compose up`): ask a lookup, a multi-hop and a comparison question. Check that citations are real arXiv IDs and that the graph panel matches the evidence.
- **Evals:** `python evals/run_ragas.py` should show the agent beating vector-only on multi-hop and comparison questions.
- **Production:**
  - In incognito, open the site and run the example questions plus one new question.
  - Stop the backend and confirm the saved examples still show.
  - Confirm UptimeRobot reports up and sends a test alert email.
  - Confirm a cold start recovers in under 60 seconds.

## First step after approval
Scaffold `paperweave/` with docker-compose (Neo4j + Qdrant). Write `fetch_papers.py` and `fetch_citations.py`, then load a first 50-paper slice into the local graph to check the schema.
