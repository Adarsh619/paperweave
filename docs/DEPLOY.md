# Deploying PaperWeave (free tiers, 24/7)

The whole stack runs on free tiers. Each step needs an account you create yourself. Do them in this order; it takes about an hour.

| Part | Service | What runs there |
|---|---|---|
| Graph database | Neo4j AuraDB Free | the knowledge graph |
| Vector database | Qdrant Cloud Free | paper vectors; Qdrant embeds the text |
| Backend | Render free web service (Docker) | FastAPI + LangGraph agent |
| Frontend | Vercel Hobby | Next.js app |
| LLM | Groq (Gemini as a backup) | planning and answers |
| Uptime | UptimeRobot free | keeps everything awake |

## 1. LLM keys

1. Create a Groq API key at https://console.groq.com/keys.
2. Optionally, create a Gemini key at https://aistudio.google.com/apikey as a backup provider.
3. Put them in your local `.env` as `GROQ_API_KEY` and `GOOGLE_API_KEY`.
4. Regenerate the saved example answers with the better model:

   ```bash
   cd backend
   ../.venv/Scripts/python scripts/export_examples.py
   ```

## 2. Neo4j AuraDB Free

1. Create a free instance at https://console.neo4j.io.
2. Save the generated password: it is shown only once.
3. Note the connection URI, which looks like `neo4j+s://xxxx.databases.neo4j.io`.

## 3. Qdrant Cloud Free

1. Create a free cluster at https://cloud.qdrant.io.
2. Copy the cluster URL and create an API key.
3. Open the cluster's **Inference** tab and check the names of the MiniLM and BM25 models.
   - The code expects `sentence-transformers/all-MiniLM-L6-v2` and `Qdrant/bm25`.
   - If the console lists them differently, set `QDRANT_DENSE_MODEL` and `QDRANT_SPARSE_MODEL` to the listed names, both in `.env` and on Render.

## 4. Load both databases from the snapshot

1. Point your local `.env` at production:

   ```bash
   NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=...
   QDRANT_URL=https://xxxx.cloud.qdrant.io
   QDRANT_API_KEY=...
   QDRANT_CLOUD_INFERENCE=true
   ```

2. Rebuild both databases from the committed `data/` folder:

   ```bash
   .venv/Scripts/python pipeline/rebuild.py --fresh
   .venv/Scripts/python pipeline/check_graph.py
   .venv/Scripts/python pipeline/check_search.py
   ```

3. Switch `.env` back to the local values afterwards.

This step needs no Semantic Scholar or Ollama calls. Run it again any time a free database is wiped.

## 5. Backend on Render

1. On https://dashboard.render.com, choose **New → Blueprint** and pick the GitHub repo. Render reads [`render.yaml`](../render.yaml).
2. Fill in the secret environment variables:
   - `NEO4J_URI`, `NEO4J_PASSWORD`
   - `QDRANT_URL`, `QDRANT_API_KEY`
   - `GROQ_API_KEY`, `GOOGLE_API_KEY`
   - `CORS_ORIGINS`: the Vercel URL from step 6. Set it to `*` for now and fix it after.
3. After the deploy, open `https://<service>.onrender.com/health`. It should return `{"status": "ok", "papers": 500, ...}`.

## 6. Frontend on Vercel

1. On https://vercel.com/new, import the repo and set **Root Directory** to `frontend`.
2. Add the environment variable `NEXT_PUBLIC_API_URL=https://<service>.onrender.com`.
3. Deploy, then set `CORS_ORIGINS` on Render to the Vercel URL, for example `https://paperweave.vercel.app`, and redeploy the backend.

## 7. Keep it awake

1. In UptimeRobot (https://uptimerobot.com), add an **HTTP(s)** monitor for `https://<service>.onrender.com/health` with a 5-minute interval, and turn on email alerts.

   `/health` makes a real read on both databases. That keeps Render from sleeping, AuraDB from pausing (3 idle days) and Qdrant Cloud from suspending (1 idle week).
2. Optionally, in GitHub, add the repository variable `BACKEND_URL` (Settings → Secrets and variables → Actions → Variables) to turn on the backup [keep-warm workflow](../.github/workflows/keep-warm.yml).
3. Mark emails from Neo4j, Qdrant, Render and UptimeRobot as "not spam".

## 8. Check the live site

1. Open the site in a private window and click a few example questions. They load from the saved answers, without the backend.
2. Ask one new question and watch the steps stream in.
3. Open a citation and the paper graph.
4. Stop the Render service briefly and confirm the example questions still work.

## Routine upkeep

- **Weekly:** ask one new question on the live site. Example questions don't touch the backend.
- **On an alert email:** resume the paused service, or run `rebuild.py --fresh` against production. Act within a few days: Qdrant deletes suspended free clusters after 4 weeks.
- **Monthly:** check UptimeRobot and Render's usage page. A month of 24/7 uptime is about 744 of the 750 free hours.
