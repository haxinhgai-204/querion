# Tech Plan (6 sprints)

## MVP Definition of Done
1) Dataset created -> document uploaded -> indexed -> chunk preview visible.
2) Workflow created in canvas -> saved JSON -> test-run produces answer + citations.
3) App binds workflow -> Chat streams via SSE -> Sources panel shows top retrieved chunks.
4) Minimal observability: run logs + node timings.

---

## Sprint 0 — Bootstrap (0.5–1 week)
### Goals
- Docker compose infra up
- API skeleton + Web skeleton
- Shared env + config

### Deliverables
- infra/docker/docker-compose.yml (postgres+pgvector, redis, minio)
- apps/api: /health
- apps/web: basic layout scaffold

### Acceptance checks
- `docker compose up -d` -> all healthy
- API `/health` returns ok

---

## Sprint 1 — Datasets CRUD + Upload (1 week)
### Backend
- POST /v1/datasets
- GET /v1/datasets
- POST /v1/datasets/{id}/documents/upload (multipart -> MinIO)
- GET /v1/datasets/{id} (include docs count)

### Frontend
- Datasets list
- Dataset detail: upload dropzone + documents table

### Acceptance
- Upload doc -> appears with status `uploaded`

---

## Sprint 2 — Worker Indexing + pgvector Retrieval (1 week)
### Worker pipeline
- Fetch from MinIO
- Parse text (pdf/docx)
- Chunking
- OpenAI embeddings
- Store chunks + embeddings
- Mark document status `ready`

### Acceptance
- Index -> status `ready`, chunk_count > 0
- Query embedding -> top_k chunks returned

---

## Sprint 3 — Chat SSE + Citations (1 week)
### Backend
- POST /v1/chat-messages (blocking + streaming)
- Streaming SSE events aligned with Dify-style `message`, `message_end`, `error`
  https://docs.dify.ai/api-reference/chat/send-chat-message

### Frontend
- Chat UI reading `text/event-stream`
- Sources panel from `retriever_resources`

### Acceptance
- Streaming works locally (no buffering)
- Answer includes citations

---

## Sprint 4 — Workflow Canvas + Runtime (1 week)
### Backend
- Workflows CRUD
- POST /v1/workflows/{id}/run (test run)
- Workflow runtime: LangGraph

### Frontend
- React Flow canvas with preset nodes
- Right-side properties panel
- Save and Test run

### Acceptance
- Workflow JSON saved and runnable
- Node configs affect output (top_k, dataset_ids, model)

---

## Sprint 5 — Apps + Observability mini + Demo (1 week)
### Backend
- Apps CRUD
- Bind app -> workflow_id
- Runs/steps logging

### Frontend
- Apps page (model config + workflow select)
- Observability minimal (list last N runs)
- Demo script

### Acceptance
- App chat uses its workflow config
- Run logs visible
