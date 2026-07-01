# Deployment, Security & Monitoring

## 1. Topology

| Component      | Recommended host        | Notes                                        |
| -------------- | ----------------------- | -------------------------------------------- |
| Frontend       | Vercel                  | Next.js; set `BACKEND_URL` to the API host.  |
| Backend API    | Render / AWS ECS / Fly  | `uvicorn` behind `gunicorn` workers.         |
| Ingestion      | Same image / worker     | Long PDF + KG jobs; scale separately if busy.|
| PostgreSQL     | Supabase / RDS          | Set `DATABASE_URL` (asyncpg).                |
| Vector DB      | Qdrant Cloud            | Set `QDRANT_URL` + `QDRANT_API_KEY`.        |
| Graph DB       | Neo4j Aura              | Set `NEO4J_URI` (`neo4j+s://…`) + creds.     |
| File storage   | AWS S3                  | `STORAGE_BACKEND=s3` + bucket/creds.         |
| LLM            | OpenAI                  | `OPENAI_API_KEY`.                            |

See the deployment mermaid diagram in [ARCHITECTURE.md](ARCHITECTURE.md#8-deployment-topology).

## 2. Backend deploy (container)

```bash
docker build -t researchmate-backend ./backend

docker run -p 8000:8000 --env-file .env \
  -e ENVIRONMENT=production \
  researchmate-backend \
  gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
```

In production the app does **not** auto-create tables. Run migrations first:

```bash
# Generate the initial migration from the ORM models (once):
alembic revision --autogenerate -m "initial schema"
# Apply migrations:
alembic upgrade head
```

Model weights (embeddings + reranker) download on first use — bake them into the image
or mount a persistent `HF_HOME` volume to avoid cold-start latency.

## 3. Frontend deploy (Vercel)

- Import the `frontend/` directory.
- Set env `BACKEND_URL=https://api.your-domain.com`.
- `next.config.js` rewrites `/api/*` to that backend, so the browser only talks to the
  same origin (tokens travel via the `Authorization` header).

## 4. Security checklist

- [x] **Auth** — JWT access/refresh, bcrypt password hashing.
- [x] **User data isolation** — every document/chunk/conversation query is filtered by
      `user_id`; Qdrant searches include a `user_id` payload filter.
- [x] **File validation** — content-type, size cap (`MAX_UPLOAD_MB`), and `%PDF` magic
      byte check before anything touches disk.
- [x] **Rate limiting** — `slowapi`, `RATE_LIMIT_PER_MINUTE` (enabled in production).
- [x] **CORS** — locked to `BACKEND_CORS_ORIGINS`.
- [ ] **Secrets** — set a strong `SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(64))"`);
      never commit `.env`.
- [ ] **TLS** — terminate HTTPS at the platform/load balancer.
- [ ] **Token revocation** — logout is stateless; add a Redis JTI denylist if you need
      server-side invalidation.

## 5. Monitoring

- `GET /health` — liveness (status, version, env).
- `GET /api/v1/system/metrics` — RAG query count, answer success rate, token usage,
  p50/p95 latency (in-process; export to Prometheus/OTel in production).
- Every request logs method, path, status, and `latency_ms` via `structlog`
  (JSON in production). The `X-Process-Time-ms` response header exposes per-request time.

Signals worth alerting on: p95 latency, `answer_success_rate` drop (retrieval quality
regression), token spend, and ingestion failures (`document.status == failed`).

## 6. Scaling notes

- **Ingestion** is CPU-bound (PDF parse + embeddings). Move `_ingest_in_background` onto
  a real task queue (Celery/RQ/Arq) and scale workers independently of the API.
- **BM25** currently builds an in-memory index over the candidate chunk pool (capped).
  At large scale, switch keyword search to Qdrant's native sparse vectors or Postgres
  full-text (`tsvector` + GIN) to avoid per-query index builds.
- **Embeddings/reranker** load once per process; run a dedicated GPU inference service
  if throughput demands it.
