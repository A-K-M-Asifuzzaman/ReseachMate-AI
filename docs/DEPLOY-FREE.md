# Deploy ResearchMate for (almost) free — OpenAI-only

A student-friendly guide to putting ResearchMate online **using only your OpenAI key**.
Everything else runs on free tiers. Your only real cost is OpenAI usage, which for a
demo is **cents** (see the cost note at the end).

The trick: we switch embeddings from the local model to **OpenAI embeddings**. That
removes `torch` from the backend, so it becomes small and fits free hosting.

---

## What you need (all free except OpenAI)

| Service | Used for | Free tier | You give me / set |
| --- | --- | --- | --- |
| **OpenAI** | LLM + embeddings | pay-as-you-go (you have this) | `OPENAI_API_KEY` |
| **GitHub** | host the code | free | push this repo |
| **Neon** *or* **Supabase** | PostgreSQL | free (0.5 GB) | `DATABASE_URL` |
| **Qdrant Cloud** | vector DB | free (1 GB cluster) | `QDRANT_URL`, `QDRANT_API_KEY` |
| **Neo4j Aura** *(optional)* | knowledge graph | free (1 instance) | `NEO4J_URI`, `NEO4J_PASSWORD` |
| **Render** | backend (FastAPI) | free web service | deploy via `render.yaml` |
| **Vercel** | frontend (Next.js) | free (Hobby) | deploy `frontend/` |

> Skip Neo4j if you don't want the Knowledge Graph page — everything else still works.

---

## Step 0 — Push to GitHub

```bash
cd "ResearchMate AI"
git init && git add -A && git commit -m "ResearchMate AI"
git branch -M main
git remote add origin https://github.com/<you>/researchmate-ai.git
git push -u origin main
```

`.env` files are gitignored, so no secrets are pushed.

---

## Step 1 — PostgreSQL (Neon, free)

1. Create a project at **neon.tech** → copy the connection string.
2. Convert it to the async driver form ResearchMate needs — replace the scheme:

   ```
   postgresql://user:pass@host/db      ❌
   postgresql+asyncpg://user:pass@host/db   ✅   (drop any ?sslmode=... query)
   ```

   That value is your **`DATABASE_URL`**.

*(Supabase works too: Project → Settings → Database → Connection string → URI, then
swap the scheme to `postgresql+asyncpg://` and use the direct connection host.)*

---

## Step 2 — Qdrant Cloud (free)

1. **cloud.qdrant.io** → create a **Free** cluster.
2. Copy the **cluster URL** → `QDRANT_URL`
   (e.g. `https://xxxx.aws.cloud.qdrant.io:6333`).
3. Create an **API key** → `QDRANT_API_KEY`.

---

## Step 3 — Neo4j Aura (free, optional)

1. **neo4j.com/cloud/aura** → create a **Free** instance.
2. Save the generated password. You get:
   - `NEO4J_URI` = `neo4j+s://xxxx.databases.neo4j.io`
   - `NEO4J_USER` = `neo4j`
   - `NEO4J_PASSWORD` = the saved password

---

## Step 4 — Backend on Render (free)

This repo ships a [`render.yaml`](../render.yaml) blueprint.

1. **render.com** → **New → Blueprint** → connect your GitHub repo.
2. Render reads `render.yaml` and creates the `researchmate-api` web service.
3. In the service **Environment**, fill the secrets marked "you paste":
   - `OPENAI_API_KEY`
   - `DATABASE_URL` (from Step 1)
   - `QDRANT_URL`, `QDRANT_API_KEY` (Step 2)
   - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` (Step 3, or leave blank to skip KG)
   - `BACKEND_CORS_ORIGINS` = your Vercel URL (fill after Step 5, then redeploy)
4. Deploy. When it's live, open `https://researchmate-api.onrender.com/health` →
   should return `{"status":"ok",...}`.

The blueprint already sets `EMBEDDING_PROVIDER=openai`, `RERANKER_ENABLED=false`, and
`AUTO_CREATE_TABLES=true`, so tables are created on first boot and no torch is installed.

---

## Step 5 — Frontend on Vercel (free)

1. **vercel.com** → **Add New → Project** → import the repo.
2. Set **Root Directory** = `frontend`.
3. Add an Environment Variable:
   - `BACKEND_URL` = your Render URL (e.g. `https://researchmate-api.onrender.com`)
4. Deploy. `frontend/next.config.js` proxies `/api/*` to `BACKEND_URL`, so the browser
   only ever talks to your Vercel domain.

Then go back to **Render** and set `BACKEND_CORS_ORIGINS` to your Vercel URL
(e.g. `https://researchmate-ai.vercel.app`) and redeploy the backend.

---

## Step 6 — Try it

Open your Vercel URL → **Register** → **Upload** a PDF → **Chat**. 🎉

---

## Cost note (why this is cheap)

With `gpt-4o-mini` + `text-embedding-3-small`:

- Embedding a ~15-page paper: **< $0.001**.
- One chat answer (retrieval + generation): **~$0.001–0.003**.
- Knowledge-graph extraction per paper: **~$0.005** (uses a bit more).

A whole demo/portfolio month is typically **well under $1**. To shrink further:
set `EMBEDDING_DIM=512` (smaller vectors) and keep `LLM_MODEL_HEAVY=gpt-4o-mini`.

---

## Free-tier gotchas

- **Render free spins down** after ~15 min idle → the first request then takes ~50s
  (cold start). Keep it warm by pinging `/health` every 10 min with a free scheduler
  like **cron-job.org**.
- **Neon/Supabase free** databases pause when idle — the first query wakes them (a few
  seconds).
- **Neo4j Aura free** pauses after 3 days idle; resume it from the Aura console.
- **Uploads on Render free** use ephemeral disk — files vanish on redeploy, but the
  extracted chunks + vectors persist in Postgres/Qdrant, so chat still works. For
  permanent file storage use S3 (`STORAGE_BACKEND=s3`).

---

## Prefer the local (BGE) embedding model instead?

Then the backend needs `torch` and ~1 GB RAM. Render free (512 MB) is too small — use
**Hugging Face Spaces** (free, Docker SDK, 16 GB RAM) or **Railway**. Keep
`requirements.txt` (not `requirements-deploy.txt`) and set `EMBEDDING_PROVIDER=sentence_transformers`,
`EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`, `EMBEDDING_DIM=384`.
