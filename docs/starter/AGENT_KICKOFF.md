# Agent Kickoff

You are implementing a mini-Dify monorepo.

## Non-goals
- Do not copy Dify source code. Implement from scratch based on public concepts.
- Keep scope MVP.

## Must-follow contracts
- Chat SSE endpoint: POST /v1/chat-messages supports response_mode=streaming and emits SSE events `message`, `message_end`, `error`, aligned with:
  https://docs.dify.ai/api-reference/chat/send-chat-message

## Architecture
- Web: Next.js pages per docs/FRONTEND_SPEC.md
- API: FastAPI endpoints per docs/API_CONTRACT.md
- Worker: indexing pipeline per docs/DATASET_INDEXING_SPEC.md
- Storage: MinIO + presigned urls
- Vector DB: Postgres + pgvector (docs/DB_SCHEMA.md)
- Workflow runtime: LangGraph (docs/WORKFLOW_SPEC.md)

## Work order (strict)
1) Implement infra/docker compose (postgres+pgvector, redis, minio).
2) Implement datasets upload + document status.
3) Implement worker indexing + retrieval query.
4) Implement chat SSE + sources panel.
5) Implement workflows CRUD + canvas + runtime.
6) Implement apps binding + minimal observability.

## Acceptance criteria
Use docs/TECH_PLAN.md DoD list.
