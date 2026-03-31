# Database Schema (Postgres + pgvector)

pgvector repo:
https://github.com/pgvector/pgvector

## Extensions
- CREATE EXTENSION IF NOT EXISTS vector;

## Tables (MVP)
### users
- id (uuid)
- email (text, unique)
- password_hash (text)
- name (text)
- role (super_admin | admin)
- is_active (boolean, default true)
- created_at, updated_at

Note: super_admin được seed khi init DB (không có UI đăng ký).
super_admin tự động có quyền truy cập tất cả workspaces (không cần record trong user_workspaces).
admin được assign vào 1 hoặc nhiều workspaces thông qua bảng user_workspaces.

### workspaces
- id (uuid)
- name
- created_at

### user_workspaces (N-N join table)
- user_id (uuid, FK -> users.id)
- workspace_id (uuid, FK -> workspaces.id)
- ws_role (owner | editor | viewer)
- created_at
- PRIMARY KEY (user_id, workspace_id)

**ws_role permissions:**

| Permission | owner | editor | viewer |
|---|---|---|---|
| View datasets, documents, chunks | yes | yes | yes |
| View workflows | yes | yes | yes |
| View apps | yes | yes | yes |
| View runs/observability | yes | yes | yes |
| Use chat (send messages) | yes | yes | yes |
| Create/edit/delete datasets | yes | yes | no |
| Upload/delete documents | yes | yes | no |
| Trigger document indexing | yes | yes | no |
| Create/edit/delete workflows | yes | yes | no |
| Create/edit/delete apps | yes | yes | no |
| Invite/remove members to WS | yes | no | no |
| Change member ws_role | yes | no | no |
| Edit workspace settings (name) | yes | no | no |
| Delete workspace | yes | no | no |

Note:
- Chỉ dùng cho admin users. Super_admin không cần records ở đây vì có implicit access tất cả (god mode).
- Khi admin login, lấy list workspaces + ws_role từ bảng này.
- Admin chọn workspace để làm việc qua workspace switcher.
- Mỗi workspace phải có ít nhất 1 owner.
- Super_admin tạo workspace → chỉ định owner (1 admin user). Owner sau đó tự invite thêm editors/viewers.
- Super_admin cũng có thể trực tiếp add/remove members vào bất kỳ workspace.

### datasets
- id (uuid)
- workspace_id (uuid)
- name, description
- created_at, updated_at

### documents
- id (uuid)
- dataset_id (uuid)
- filename
- content_type
- size
- storage_key (text)
- status (uploaded|indexing|ready|failed)
- chunk_count (int)
- error_message (text)
- created_at, updated_at

### chunks
- id (uuid)
- dataset_id (uuid)
- document_id (uuid)
- chunk_index (int)
- content (text)
- created_at

### embeddings
- chunk_id (uuid, PK/FK -> chunks.id)
- embedding vector(N)   -- N from config
- model_name (text)
- created_at

### conversations / messages
- conversations: id, app_id, user, created_at
- messages: id, conversation_id, role, content, created_at

### runs / run_steps (mini observability)
- runs: id, app_id, workflow_id, conversation_id, status, started_at, ended_at, latency_ms
- run_steps: id, run_id, node_id, node_type, started_at, ended_at, input_json, output_json

## Index suggestions
- user_workspaces(user_id), user_workspaces(workspace_id)
- chunks(dataset_id, document_id)
- embeddings: vector index (choose one)
  - HNSW (fast query, more RAM)
  - IVFFlat (faster build, needs training-ish)
See pgvector docs in repo for index options.
