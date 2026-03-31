# Phase 3 — Chat SSE + Citations

> Goal: User chat, nhận streaming response qua SSE, thấy sources/citations.

> **Cross-cutting**: Tất cả UI components phải dùng theme-aware colors (dark/light) và translation keys (EN/VI). Thêm translations vào `locales/{en,vi}/chat.json`.
> **RBAC**: Chat endpoints protected by JWT (admin UI) hoặc API key (end-user). Conversations scoped by workspace.
> **Responsive**: Chat page — mobile: full-screen chat, sources = bottom sheet. Tablet: 2-col (chat + collapsible sources). Desktop: 3-col (conversations + chat + sources). ChatComposer = fixed bottom bar (mobile/tablet) / inline (desktop).

## Tasks

### Backend — DB Models & Migrations

- [ ] **P3.1** — Tạo SQLAlchemy models
  - `conversations` table (id, app_id, user, created_at)
  - `messages` table (id, conversation_id, role, content, metadata_json, created_at)
  - **Spec**: DB_SCHEMA.md

- [ ] **P3.2** — Alembic migration cho conversations + messages

### Backend — Chat SSE Endpoint

- [ ] **P3.3** — `POST /v1/chat-messages` endpoint
  - Body: { query, response_mode, conversation_id, user, app_id, inputs? }
  - Nếu response_mode = "blocking": return JSON response
  - Nếu response_mode = "streaming": return StreamingResponse (text/event-stream)
  - **Spec**: API_CONTRACT.md

- [ ] **P3.4** — SSE event format (Dify-aligned)
  - `event: message` — partial answer + metadata
  - `event: message_end` — final metadata (usage, retriever_resources)
  - `event: error` — error code + message
  - Format theo API_CONTRACT.md SSE section
  - **Ref**: https://docs.dify.ai/api-reference/chat/send-chat-message

- [ ] **P3.5** — Chat service logic
  - `app/services/chat.py`
  - Flow:
    1. Tạo/get conversation
    2. Save user message
    3. Retrieve relevant chunks (gọi retrieval service từ Phase 2)
    4. Compose prompt (system_prompt + context + query)
    5. Call OpenAI chat.completions (stream=True)
    6. Yield SSE events khi nhận tokens
    7. Save assistant message khi complete
  - Tạm hardcode app config (model, system_prompt, dataset_ids) — Phase 5 sẽ bind qua App

- [ ] **P3.6** — Presigned URLs cho sources
  - Khi trả retriever_resources, generate presigned URL cho source documents
  - **Spec**: SECURITY_AND_TENANCY.md

### Backend — Conversation History

- [ ] **P3.7** — `GET /v1/conversations` — list conversations
- [ ] **P3.8** — `GET /v1/messages?conversation_id=xxx` — list messages trong conversation

### Frontend — Chat UI

- [ ] **P3.9** — `/chat` page layout
  - Desktop (≥1024px): 3-column — conversation list + chat area + sources panel
  - Tablet (768-1023px): 2-column — chat area + collapsible sources panel. Conversations = dropdown hoặc slide-over
  - Mobile (<768px): full-screen chat only. Conversations = top dropdown/back navigation. Sources = bottom sheet khi tap source icon

- [ ] **P3.10** — **ChatComposer** component
  - Text input + send button
  - Disable khi đang streaming
  - Enter to send, Shift+Enter for newline
  - Mobile/Tablet: fixed bottom bar, full width input
  - Desktop: inline within chat area
  - **Spec**: FRONTEND_SPEC.md

- [ ] **P3.11** — **ChatStreamViewer** component
  - SSE client: POST /v1/chat-messages { response_mode: "streaming" }
  - Parse `data:` lines
  - Update message content incrementally per `message` event
  - Finalize on `message_end`
  - Handle `error` event
  - **Spec**: FRONTEND_SPEC.md (SSE client behavior)

- [ ] **P3.12** — **SourcesPanel** component
  - Hiển thị retriever_resources từ message_end event
  - Mỗi source: dataset name, document filename, score, content preview
  - Click → open presigned URL (view source document)
  - Mobile: bottom sheet, swipe up to expand
  - Tablet: collapsible side panel
  - Desktop: always visible side panel
  - **Spec**: FRONTEND_SPEC.md

- [ ] **P3.13** — Message rendering
  - Render markdown trong assistant messages
  - User message styling khác assistant
  - Loading indicator khi streaming

### Frontend — API Client

- [ ] **P3.14** — SSE client utility
  - `lib/api/chat.ts`: sendChatMessage (streaming mode)
  - Parse EventSource / fetch ReadableStream
  - Callback pattern: onMessage, onMessageEnd, onError

## Acceptance Criteria

- [ ] Gửi query → nhận streaming response (từng token hiện ra)
- [ ] Không bị buffering (check nginx/proxy headers nếu có)
- [ ] message_end event chứa retriever_resources
- [ ] Sources panel hiển thị top_k chunks với score
- [ ] Click source → mở document (presigned URL)
