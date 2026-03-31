# Phase 5 — Apps + Observability + Demo

> Goal: App binds workflow, chat dùng app config, run logs visible, sẵn sàng demo.

> **Cross-cutting**: Tất cả UI components phải dùng theme-aware colors (dark/light) và translation keys (EN/VI). Thêm translations vào `locales/{en,vi}/apps.json`.
> **RBAC**: Apps scoped by workspace_id. Runs/observability visible theo workspace. Super admin thấy tất cả.
> **Responsive**: Apps list = cards (mobile) / table (desktop). Runs table = stacked cards (mobile). Run detail modal = bottom sheet (mobile).

## Tasks

### Backend — DB Models & Migrations

- [ ] **P5.1** — Tạo SQLAlchemy models
  - `apps` table (id, workspace_id, name, workflow_id FK, model_config JSON, system_prompt, api_key, created_at, updated_at)
  - `runs` table (id, app_id, workflow_id, conversation_id, status, started_at, ended_at, latency_ms)
  - `run_steps` table (id, run_id, node_id, node_type, started_at, ended_at, input_json, output_json)
  - **Spec**: DB_SCHEMA.md

- [ ] **P5.2** — Alembic migration cho apps, runs, run_steps

### Backend — Apps CRUD

- [ ] **P5.3** — `POST /v1/apps` — tạo app
  - Body: { name, workflow_id, model_config, system_prompt }
  - Generate API key cho app
  - **Spec**: API_CONTRACT.md

- [ ] **P5.4** — `GET /v1/apps` — list apps
- [ ] **P5.5** — `GET /v1/apps/{id}` — app detail
- [ ] **P5.6** — `PATCH /v1/apps/{id}` — update app config

### Backend — Bind Chat to App

- [ ] **P5.7** — Refactor chat service
  - POST /v1/chat-messages nhận app_id
  - Load app config (workflow_id, model_config, system_prompt)
  - Execute workflow bound to app
  - Thay thế hardcoded config từ Phase 3

### Backend — Observability Logging

- [ ] **P5.8** — Run logging service
  - `app/services/observability.py`
  - Tạo run record khi chat bắt đầu
  - Log từng node step (started/finished + input/output)
  - Update run status + latency khi hoàn thành
  - Optional: log token usage
  - **Spec**: OBSERVABILITY_SPEC.md

- [ ] **P5.9** — `GET /v1/runs?app_id=xxx` — list runs
  - Return: last N runs với status, latency, timestamps

- [ ] **P5.10** — `GET /v1/runs/{id}/steps` — run steps detail
  - Return: steps[] với node_id, node_type, timing, input/output

### Backend — App API Key Auth

- [ ] **P5.11** — API key authentication cho chat endpoints
  - Middleware check `X-API-Key` header cho POST /v1/chat-messages
  - Validate key against apps table (app.api_key)
  - Tách biệt với JWT auth (JWT cho admin UI, API key cho end-user chat)
  - **Spec**: SECURITY_AND_TENANCY.md
  - **Note**: JWT auth + RBAC (super_admin/admin) đã setup ở Phase 0 (P0.16, P0.17)

### Frontend — Apps Page

- [ ] **P5.12** — `/apps` page
  - List apps (card view)
  - Button "New App" → form:
    - Name
    - Workflow (dropdown select từ workflows list)
    - Model config: provider, model, temperature, max_tokens
    - System prompt (textarea)

- [ ] **P5.13** — `/apps/[appId]` page
  - App config editor (update form)
  - API key display (copy button)
  - Link to chat with this app

### Frontend — Refactor Chat

- [ ] **P5.14** — Chat page nhận app context
  - Select app trước khi chat (hoặc từ app detail page)
  - Pass app_id trong chat-messages request

### Frontend — Observability UI

- [ ] **P5.15** — Runs list component
  - Hiển thị trong app detail page hoặc separate tab
  - Table: run_id, status, latency, started_at
  - **Spec**: OBSERVABILITY_SPEC.md

- [ ] **P5.16** — Run detail modal/panel
  - Click run → show steps timing table
  - Columns: node_id, node_type, duration_ms
  - Optional: expandable input/output JSON

### Demo & Polish

- [ ] **P5.17** — Seed data script
  - Script tạo sample workspace, dataset, upload & index sample docs
  - Tạo sample workflow + app
  - Mục đích: demo nhanh không cần setup thủ công

- [ ] **P5.18** — Demo walkthrough
  - Document demo flow step-by-step
  - Screenshots hoặc recording script
  - Cover full flow: create dataset → upload → index → create workflow → test → create app → chat

## Acceptance Criteria

- [ ] Tạo app, bind workflow → chat dùng đúng workflow + config
- [ ] Thay đổi model/temperature trong app → output thay đổi
- [ ] Run logs hiển thị: list runs + step timing
- [ ] API key auth hoạt động cho chat endpoint
- [ ] Demo flow chạy end-to-end không lỗi
