# mini-dify (Graduation Project)

Mini clone of Dify concepts (not code): multi-workspace, datasets/knowledge base, workflow canvas, and SSE streaming chat with citations.

## Core stack
- Web: Next.js (TypeScript)
- API: FastAPI
- Workflow runtime: LangGraph (Python) https://github.com/langchain-ai/langgraph
- Vector store: Postgres + pgvector https://github.com/pgvector/pgvector
- Object storage: MinIO (S3 compatible)
- Streaming: Server-Sent Events (SSE) using `text/event-stream` aligned with Dify streaming mode:
  https://docs.dify.ai/api-reference/chat/send-chat-message

## Monorepo structure (high level)
- apps/web: Next.js UI (Datasets, Workflows, Apps, Chat)
- apps/api: FastAPI (REST + SSE)
- apps/worker: background indexing jobs (RQ/Celery)
- infra/docker: docker-compose + init scripts
- docs: architecture + specs

## Local dev (expected)
1. Start infra: postgres+pgvector, redis, minio
2. Start API + Worker
3. Start Web

See `docs/TECH_PLAN.md` and `docs/ARCHITECTURE.md`.
