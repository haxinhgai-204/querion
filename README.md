# Querion

> Mini-Dify: multi-workspace datasets/knowledge base, workflow canvas, SSE streaming chat with citations.

## Quick Start

### 1. Start infrastructure

```bash
cd infra/docker
cp .env.example .env      # adjust if needed
docker compose up -d       # postgres+pgvector, redis, minio
```

Wait until all services are healthy:

```bash
docker compose ps
```

### 2. Start API

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head       # run migrations
uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health`

### 3. Start Web

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Project Structure

```
querion/
├── apps/
│   ├── api/       # FastAPI backend
│   ├── web/       # Next.js frontend
│   └── worker/    # Background jobs (Phase 2)
├── infra/
│   └── docker/    # Docker Compose + init scripts
└── docs/          # Architecture & specs
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Web | Next.js + TypeScript + Tailwind CSS |
| API | FastAPI (Python) |
| Workflow Runtime | LangGraph |
| Vector Store | Postgres + pgvector |
| Object Storage | MinIO (S3-compatible) |
| Queue | Redis |
