# Phase 4 — Workflow Canvas + Runtime

> Goal: User tạo workflow trên canvas, save JSON, test-run trả answer + citations.

> **Cross-cutting**: Tất cả UI components phải dùng theme-aware colors (dark/light) và translation keys (EN/VI). Thêm translations vào `locales/{en,vi}/workflows.json`.
> **RBAC**: Workflows scoped by workspace_id. Super admin có thể access cross-workspace. Viewer read-only.
> **Responsive**: Workflow list = cards (mobile) / table (desktop). Canvas = read-only + pinch-to-zoom trên mobile, show "Use desktop for editing" banner. NodePropertiesPanel = bottom sheet (mobile) / side panel (desktop).

## Tasks

### Backend — DB Models & Migrations

- [ ] **P4.1** — Tạo SQLAlchemy models
  - `workflows` table (id, workspace_id, name, graph_json, created_at, updated_at)
  - graph_json lưu dạng JSON (nodes + edges từ React Flow)
  - **Spec**: DB_SCHEMA.md

- [ ] **P4.2** — Alembic migration cho workflows table

### Backend — Workflows CRUD

- [ ] **P4.3** — `POST /v1/workflows` — tạo workflow
  - Body: { name, graph_json }
  - Validate graph_json theo rules
  - **Spec**: API_CONTRACT.md

- [ ] **P4.4** — `GET /v1/workflows` — list workflows
- [ ] **P4.5** — `GET /v1/workflows/{id}` — get workflow detail
- [ ] **P4.6** — `PATCH /v1/workflows/{id}` — update workflow (name, graph_json)

### Backend — Workflow Validation

- [ ] **P4.7** — Graph JSON validator
  - `app/services/workflow_validator.py`
  - Rules (WORKFLOW_SPEC.md):
    - Exactly 1 input node, exactly 1 output node
    - Graph phải là DAG (no cycles)
    - Phải có path từ input → output
    - Chỉ allow supported node types: input, retrieve, compose_prompt, llm_generate, output
    - MVP: enforce linear chain (mỗi node max 1 outgoing edge)

### Backend — LangGraph Runtime

- [ ] **P4.8** — LangGraph workflow executor
  - `app/services/workflow_runtime.py`
  - Parse graph_json → build LangGraph StateGraph
  - State schema theo WORKFLOW_SPEC.md:
    - query, inputs, retrieved_chunks, prompt_messages, answer, citations
  - **Ref**: https://github.com/langchain-ai/langgraph

- [ ] **P4.9** — Node implementations
  - **input node**: extract query + inputs từ request
  - **retrieve node**: gọi retrieval service (dataset_ids, top_k từ node config)
  - **compose_prompt node**: render template với variables (system_prompt, query, context)
  - **llm_generate node**: gọi OpenAI chat.completions (model, temperature, max_tokens từ config)
  - **output node**: package answer + citations
  - **Spec**: WORKFLOW_SPEC.md (Node configs)

- [ ] **P4.10** — `POST /v1/workflows/{id}/run` — test run
  - Body: { query, inputs? }
  - Execute workflow via LangGraph
  - Return: { answer, retriever_resources }
  - **Spec**: API_CONTRACT.md

### Frontend — Workflow List Page

- [ ] **P4.11** — `/workflows` page
  - Responsive: cards 1-col (mobile) / 2-col (tablet) / table (desktop)
  - Button "New Workflow"
  - Click → navigate to canvas

### Frontend — Workflow Canvas

- [ ] **P4.12** — `/workflows/[workflowId]` page layout
  - Desktop (≥1024px): canvas area (left) + properties panel (right) + top toolbar
  - Tablet (768-1023px): canvas full width, properties panel = bottom sheet khi select node, smaller node palette
  - Mobile (<768px): ⚠️ read-only view — pinch-to-zoom, no drag-drop editing. Show banner "Use desktop for full editing". Có thể view workflow + test run, nhưng không edit nodes/edges
  - Top: toolbar (save, test run, back)

- [ ] **P4.13** — **WorkflowCanvas** component (React Flow)
  - Render nodes + edges từ graph_json
  - Desktop/Tablet: drag & drop nodes từ palette/toolbar, connect nodes bằng edges
  - Mobile: read-only render, pinch-to-zoom, pan to navigate, tap node to view (not edit)
  - Custom node types với icons:
    - input (green), retrieve (blue), compose_prompt (yellow), llm_generate (purple), output (red)
  - **Spec**: FRONTEND_SPEC.md

- [ ] **P4.14** — **NodePropertiesPanel** component
  - Hiển thị khi click/select node
  - Desktop: side panel (right)
  - Tablet/Mobile: bottom sheet (slide up)
  - Dynamic form based on node type:
    - retrieve: dataset_ids (multi-select), top_k (number)
    - compose_prompt: template (textarea)
    - llm_generate: model (select), temperature (slider), max_tokens (number)
  - Mobile: read-only display (không edit) — consistent với canvas read-only
  - **Spec**: WORKFLOW_SPEC.md (Node configs)

- [ ] **P4.15** — Save workflow
  - Serialize React Flow state → graph_json
  - Call PATCH /v1/workflows/{id}
  - Feedback: success/error toast

- [ ] **P4.16** — Test run UI
  - Button "Test Run" → input modal (query field)
  - Call POST /v1/workflows/{id}/run
  - Show result: answer + retriever_resources
  - Hiển thị trong panel hoặc modal

### Frontend — API Client

- [ ] **P4.17** — API client functions cho workflows
  - `lib/api/workflows.ts`: createWorkflow, listWorkflows, getWorkflow, updateWorkflow, runWorkflow

## Acceptance Criteria

- [ ] Tạo workflow trên canvas với nodes + edges
- [ ] Save → reload → graph giữ nguyên
- [ ] Test run với query → nhận answer + citations
- [ ] Node configs ảnh hưởng output (thay đổi top_k, model, template)
- [ ] Invalid graph (no path, cycle) → validation error
