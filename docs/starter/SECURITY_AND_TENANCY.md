# Security & Tenancy

## User Roles

### super_admin
- Tự tạo (seed) khi init DB, không có đăng ký qua UI
- Có quyền truy cập **tất cả workspaces** (cross-workspace access)
- Manage tất cả resources: datasets, workflows, apps, users, runs
- Có thể tạo/xóa/sửa workspace
- Có thể tạo/xóa/sửa admin users
- Có thể assign admin vào workspace
- Nhìn thấy tất cả data trong hệ thống (god mode)

### admin
- Được super_admin tạo
- Có thể được assign vào **1 hoặc nhiều workspaces** (thông qua bảng user_workspaces)
- Mỗi workspace membership có 1 **ws_role**: owner | editor | viewer
- Chỉ thấy resources trong workspaces mà mình là member
- Không thể tạo workspace mới (chỉ super_admin)
- Không thể truy cập data workspace mà mình không phải member

### Workspace Roles (ws_role)

#### owner
- Full control trong workspace
- **Invite/remove members**: thêm admin users khác vào workspace, gán ws_role (editor/viewer)
- **Change member roles**: upgrade/downgrade editor ↔ viewer, hoặc transfer ownership
- CRUD tất cả resources: datasets, documents, workflows, apps
- Edit workspace settings (name)
- Delete workspace
- Mỗi workspace phải có ít nhất 1 owner

#### editor
- CRUD datasets, documents (upload/delete/index), workflows, apps
- Use chat, view runs/observability
- **Không thể** invite/remove members
- **Không thể** edit workspace settings
- **Không thể** delete workspace

#### viewer
- **Read-only**: xem datasets, documents, chunks, workflows, apps, runs
- Use chat (send messages)
- **Không thể** tạo/sửa/xóa bất kỳ resource nào
- **Không thể** upload/delete documents
- **Không thể** trigger indexing

## Tenancy rules (MVP)
- Every dataset/workflow/app belongs to a workspace_id
- API must scope queries by workspace_id to prevent cross-tenant access
- super_admin: bypass workspace scoping (can query any workspace, full CRUD)
- admin: strict workspace scoping — chỉ access workspaces mà mình là member
- Within a workspace, permission check dựa trên ws_role (owner/editor/viewer)
- API phải check 2 layers: (1) user có phải member của workspace không, (2) ws_role có đủ quyền cho action không

## Auth
- JWT-based authentication cho admin UI
- Login: POST /v1/auth/login → JWT access token + refresh token
- JWT payload: { user_id, role } (không chứa workspace_id vì admin có thể thuộc nhiều WS)
- Active workspace được chọn qua header `X-Workspace-Id` hoặc query param
- Protected routes: middleware check JWT → extract user → check workspace membership + ws_role
- super_admin routes: additional role check (bypass workspace membership)
- API key (X-API-Key) cho chat endpoints (end-user facing)

## File access
- MinIO objects never public by default
- API generates presigned URLs for admin preview / sources panel

## SSE
- Ensure SSE endpoint is protected by API key (app_id + key)
- Avoid leaking internal keys in `retriever_resources`
