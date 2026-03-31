# API Contract (mini)

Base URL: /v1

## Auth
- JWT login cho admin UI (super_admin + admin)
- API key (X-API-Key) cho chat endpoints

### POST /auth/login
Body:
- email: string
- password: string

Response:
- access_token (JWT)
- refresh_token
- user: { id, email, name, role, workspaces: [{ workspace_id, workspace_name, ws_role }] }

### POST /auth/refresh
Body:
- refresh_token: string

Response:
- access_token (new JWT)

### GET /auth/me
Headers: Authorization: Bearer {token}
Response: user object

---

## Users (super_admin only)
### POST /users
Body:
- email, password, name, role (admin)

### GET /users
Query: workspace_id? (optional filter)
Response: list users (with their workspace memberships)

### PATCH /users/{id}
Body: name?, is_active?

### DELETE /users/{id}
Deactivate user (soft delete)

---

## Workspaces (super_admin creates, owner manages)
### POST /workspaces (super_admin only)
Body:
- name: string
- owner_user_id: string (admin user to be assigned as owner)

### GET /workspaces
Response: list all workspaces (super_admin), hoặc chỉ workspaces mình là member (admin)

### PATCH /workspaces/{id} (super_admin or ws_role=owner)
Body: name?

### DELETE /workspaces/{id} (super_admin or ws_role=owner)

---

## Workspace Members (super_admin or ws_role=owner)
### POST /workspaces/{id}/members
Body:
- user_id: string
- ws_role: "owner" | "editor" | "viewer"

Note: super_admin can add anyone. Owner can add admin users to their workspace.

### GET /workspaces/{id}/members
Response: list members [{ user_id, email, name, ws_role, created_at }]
Access: any workspace member can view the member list

### PATCH /workspaces/{id}/members/{user_id}
Body:
- ws_role: "owner" | "editor" | "viewer"

Note: only super_admin or owner can change roles. Cannot demote the last owner.

### DELETE /workspaces/{id}/members/{user_id}
Remove member from workspace.
Note: cannot remove the last owner. Owner can remove editors/viewers.

---

## Datasets
### POST /datasets
Body:
- name: string
- description?: string

Response: dataset

### GET /datasets
Response: list datasets

### POST /datasets/{dataset_id}/documents/upload
Content-Type: multipart/form-data
Fields:
- file: (pdf/docx/txt)

Response:
- document_id
- status=uploaded
- filename

### POST /documents/{document_id}/index
Response:
- status=indexing
- job_id

### GET /documents/{document_id}
Response:
- status
- chunk_count
- error_message?

### GET /documents/{document_id}/chunks?limit=10
Response:
- chunks: [{chunk_id, chunk_index, content_preview}]

---

## Workflows
### POST /workflows
Body:
- name
- graph_json

### PATCH /workflows/{id}
Body:
- name?
- graph_json?

### POST /workflows/{id}/run
Body:
- query: string
- inputs?: object
Response:
- answer
- retriever_resources

---

## Apps
### POST /apps
Body:
- name
- workflow_id
- model_config: { provider, model, temperature, max_tokens }
- system_prompt

### PATCH /apps/{id}
Update config

---

## Chat (Dify-like)
### POST /chat-messages
Body:
- inputs: object (optional)
- query: string
- response_mode: "streaming" | "blocking"
- conversation_id: string | ""   (empty -> create)
- user: string (end-user identifier)
- app_id: string

Streaming behavior aligned with Dify API:
https://docs.dify.ai/api-reference/chat/send-chat-message

#### Streaming response (text/event-stream)
SSE events (minimum):
- event: message
  data: {
    task_id,
    message_id,
    conversation_id,
    answer: "partial text",
    metadata: {
      usage?: { prompt_tokens, completion_tokens, total_tokens },
      retriever_resources?: [
        {
          dataset_id,
          document_id,
          chunk_id,
          score,
          content_preview,
          source_url?: presigned_url
        }
      ]
    }
  }

- event: message_end
  data: {
    task_id,
    message_id,
    conversation_id,
    metadata: { usage? }
  }

- event: error
  data: { code, message }
