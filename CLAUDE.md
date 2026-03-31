# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Querion is a mini-Dify platform for multi-workspace knowledge management with datasets, workflow canvas, and streaming chat with citations. It uses FastAPI (Python) for the backend, Next.js (TypeScript) for the frontend, with Postgres+pgvector for vector search, MinIO for S3-compatible object storage, and Redis for queueing.

## Development Commands

### Infrastructure (Docker)
```bash
cd infra/docker
docker compose up -d       # Start postgres, redis, minio
docker compose ps          # Check service health
docker compose down        # Stop all services
```

### API (FastAPI)
```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head       # Run migrations
uvicorn app.main:app --reload --port 8000

# Run a single test (once tests exist)
pytest tests/test_specific.py::test_function_name -v

# Linting
ruff check app/
```

### Web (Next.js)
```bash
cd apps/web
npm install
npm run dev                # Start dev server on port 3000
npm run build              # Production build
npm run lint               # ESLint
```

## Architecture

### Multi-tenancy & Authentication

**Two-tier role system:**
1. **super_admin** (god mode): Seeded on init (admin@querion.io / admin123), has access to all workspaces, manages admin users and workspaces
2. **admin**: Created by super_admin, assigned to specific workspaces via `user_workspaces` table with workspace role (owner/editor/viewer)

**Workspace roles:**
- **owner**: Full control, can invite/remove members, manage workspace settings
- **editor**: CRUD datasets/documents/workflows/apps, cannot manage members
- **viewer**: Read-only + chat access, no write operations

**Important tenancy rules:**
- Every resource (dataset, workflow, app) has a `workspace_id`
- API queries MUST scope by workspace_id for admin users
- super_admin bypasses workspace scoping
- Check 2 layers: (1) workspace membership, (2) ws_role permissions
- Active workspace selected via `X-Workspace-Id` header or query param

### Request Flow Patterns

**Upload + Index:**
1. User uploads file → API stores in MinIO → creates document row (status=uploaded)
2. User triggers indexing → API enqueues job to Redis
3. Worker fetches from MinIO → parses/chunks/embeds → stores in Postgres (status=ready)

**Streaming Chat:**
1. Web → API POST /v1/chat-messages (response_mode=streaming)
2. API executes workflow via LangGraph runtime
3. Retrieve node → pgvector search → retrieves chunks
4. LLM node → streams tokens from OpenAI/Anthropic/Google
5. API → Web via SSE events (message, message_end)
6. Web renders streaming answer + citation sources

### Workflow Runtime (LangGraph-based)

**Supported node types (MVP):**
- `input`: Entry point
- `retrieve`: pgvector semantic search
- `compose_prompt`: Template with {{query}}, {{context}}, {{system_prompt}}
- `llm_generate`: Calls LLM (OpenAI/Anthropic/Google)
- `parameter_extract`: Extracts structured params using LLM
- `if_else`: Conditional branching based on state variables
- `http_request`: External API calls with template substitution
- `code_execute`: Python sandbox for custom logic
- `answer`/`output`: Output nodes

**Workflow execution:**
- Graph stored as JSON (React Flow format) in `workflows.graph_json`
- Runtime traverses DAG from input node, executing each node sequentially
- Supports linear chains + if_else branching (multi-outgoing edges)
- State dict carries query, retrieved_chunks, prompt_messages, answer, citations, extracted_params
- See apps/api/app/services/workflow_runtime.py for implementation

### Key Database Tables

- `users`: id, email, password_hash, role (super_admin | admin)
- `workspaces`: id, name
- `user_workspaces`: user_id, workspace_id, ws_role (owner/editor/viewer) — N:N join table
- `datasets`: id, workspace_id, name, description
- `documents`: id, dataset_id, filename, storage_key, status, chunk_count
- `chunks`: id, dataset_id, document_id, chunk_index, content
- `embeddings`: chunk_id (PK), embedding vector(N), model_name
- `conversations`, `messages`: For chat history
- `workflows`: id, workspace_id, name, graph_json, workflow_type (workflow | chatflow)
- `ai_providers`: Provider config with encrypted API keys

### API Contract Alignment

**SSE streaming aligned with Dify API:**
- Event: `message` → partial answer + metadata (usage, retriever_resources)
- Event: `message_end` → final metadata
- Event: `error` → error details
- Retriever resources include chunk_id, document_id, dataset_id, score, content_preview, filename

### Code Organization

**API (FastAPI):**
- `app/main.py`: FastAPI app with CORS, router registration, lifespan hooks
- `app/routers/`: REST endpoints (auth, users, workspaces, datasets, documents, workflows, chat)
- `app/models/`: SQLAlchemy ORM models
- `app/services/`: Business logic (retrieval, chat, workflow_runtime, workflow_validator, encryption)
- `app/auth/`: JWT security, password hashing, dependencies for auth
- `app/config.py`: Settings from environment variables (Pydantic)
- `app/deps.py`: Dependency injection (DB session, Redis client)
- `alembic/versions/`: Database migrations (numbered sequentially)

**Web (Next.js):**
- `src/app/`: App router pages (login, datasets, workflows, chat, admin)
- `src/components/`: Reusable UI components (layout, providers, datasets, workspace)
- `src/components/providers/`: Context providers (ThemeProvider, I18nProvider, AuthProvider)
- `src/components/layout/`: AppShell, Sidebar, Topbar with workspace switcher
- Uses Tailwind CSS v4, Next.js 16, React 19, @xyflow/react for workflow canvas

## Important Notes

- Super admin credentials are seeded on startup (see app/config.py and app/seed.py)
- API keys for LLM providers stored encrypted in database (see app/services/encryption.py)
- Alembic migrations must be run before starting API
- MinIO presigned URLs used for document preview/download (never public by default)
- Workflow validation ensures DAG structure, exactly one input/output node, and supported node types
- Vector embeddings use pgvector extension (HNSW or IVFFlat indexes recommended)
- Chat endpoints support both streaming (SSE) and blocking modes
- Chatflow type workflows include conversation history for multi-turn dialogue
