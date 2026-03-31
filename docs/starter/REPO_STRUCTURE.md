# Monorepo structure

## Root
- apps/
  - web/      Next.js UI
  - api/      FastAPI service
  - worker/   background jobs
- packages/
  - shared/   shared types + generated client (optional)
- infra/
  - docker/   compose + init scripts
- docs/       specs

## Ownership / boundaries
- apps/web: no direct DB/MinIO access; only talks to API
- apps/api: owns contracts, tenancy checks, presigned URLs, SSE streaming
- apps/worker: owns indexing pipeline only; no user-facing auth

## Environments
- dev: docker-compose
- demo: same compose but with env pinned and seeded dataset
