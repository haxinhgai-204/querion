# Student System + App Publishing + RAG Chat

## Overview

Hệ thống cho phép **admin** quản lý tài khoản sinh viên, publish app (RAG chat với dataset), và **sinh viên** đăng nhập để tương tác với các app đã publish. Bot chỉ trả lời dựa trên nội dung dataset đã bind.

---

## 1. Database Schema

### Migration `0009` — Students + App Publishing
- **Table `students`**: `id`, `email` (unique), `password_hash`, `name`, `student_id` (mã SV), `is_active`, `must_change_password`, `created_at`, `updated_at`
- **Table `apps`**: thêm `is_published` (bool), `description` (text)

### Migration `0010` — App Dataset Binding
- **Table `apps`**: thêm `dataset_id` (FK → `datasets.id`, SET NULL on delete)

### Model Files

| Model | File | Key Fields |
|-------|------|------------|
| Student | `app/models/student.py` | email, password_hash, name, student_id, must_change_password |
| App (updated) | `app/models/app.py` | +dataset_id, +is_published, +description |

---

## 2. Backend API Endpoints

### Student Auth — `app/routers/student_auth.py`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/student/login` | Login bằng email + password, trả JWT với `type: "student"` |
| POST | `/v1/student/refresh` | Refresh token |
| GET | `/v1/student/me` | Thông tin student hiện tại |
| POST | `/v1/student/change-password` | Đổi password (bắt buộc lần đầu) |
| GET | `/v1/student/apps` | Danh sách published apps, grouped by workspace name |
| POST | `/v1/student/apps/{app_id}/chat` | **RAG Chat** — retrieval từ dataset + LLM streaming (SSE) |

### Student Management — `app/routers/students.py`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/students` | admin/super_admin | Tạo student mới (default pwd: `querion123`) |
| GET | `/v1/students` | admin/super_admin | List tất cả students |
| POST | `/v1/students/import-csv` | admin/super_admin | Import từ CSV |
| DELETE | `/v1/students/{id}` | admin/super_admin | Deactivate student |

### App CRUD (updated) — `app/routers/apps.py`

Thêm fields trong create/update/response:
- `dataset_id` — bind dataset cho RAG
- `is_published` — toggle publish cho student
- `description` — mô tả hiện cho student

---

## 3. RAG Chat Flow

```
Student gửi message
    → POST /v1/student/apps/{app_id}/chat
    → Kiểm tra app.is_published && app.dataset_id
    → Query top-5 chunks từ pgvector (cosine similarity)
    → Build prompt = system_prompt + retrieved context + history
    → Stream LLM response (OpenAI/Gemini/Anthropic)
    → SSE: data: {"type":"token","content":"..."} token-by-token
    → Frontend render real-time
```

### Hỗ trợ LLM Providers:
- **OpenAI** (GPT-4, GPT-3.5, etc.)
- **Google Gemini**
- **Anthropic Claude**

### System Prompt:
- Nếu admin cấu hình `system_prompt` trong App → dùng prompt đó + inject context
- Nếu không → dùng default RAG prompt (friendly, cite sources `[#0]`, `[#1]`)

---

## 4. Frontend Pages

### Student Pages (dark theme, no sidebar)

| Route | Description |
|-------|-------------|
| `/student/login` | Login form → redirect change-password hoặc chat |
| `/student/change-password` | Bắt buộc đổi password lần đầu |
| `/student/chat` | Sidebar apps grouped by WS + chat UI (SSE streaming) |

### Admin Pages

| Route | Description |
|-------|-------------|
| `/admin/students` | Table, add modal, CSV import, deactivate |
| `/apps/[appId]` | +Dataset selector, +Description, +Publish toggle |

---

## 5. Authentication — Student vs Admin

| | Admin | Student |
|---|---|---|
| Table | `users` | `students` |
| Login URL | `/login` | `/student/login` |
| JWT type | `access` | `student` |
| LocalStorage keys | `querion-refresh-token` | `querion-student-token`, `querion-student-refresh` |
| After login | `/datasets` | `/student/chat` |

> Token hoàn toàn tách biệt — cùng 1 browser, admin + student có thể login đồng thời không conflict.

---

## 6. CSV Import Format

```csv
email,name,student_id
sv001@university.edu,Nguyễn Văn An,SV001
sv002@university.edu,Trần Thị Bình,SV002
sv003@university.edu,Lê Minh Cường,SV003
```

- `email` — bắt buộc, dùng để login
- `name` — bắt buộc
- `student_id` — optional (mã sinh viên)
- Default password: **querion123**
- `must_change_password = true` — bắt buộc đổi lần đầu
- Email trùng sẽ bị skip

---

## 7. Workspace Selector (Super Admin)

- Super admin thấy **tất cả workspaces** (fetch từ API)
- Admin thường chỉ thấy workspaces mình là member
- Khi đổi workspace → page auto re-mount để load data mới
- Workspace name được persist trong localStorage để không mất sau refresh

---

## 8. App Publishing Workflow

1. Admin vào `/apps/[appId]` → Config tab
2. Chọn **Bound Dataset** — dataset nào sẽ RAG search
3. Viết **System Prompt** — hướng dẫn bot trả lời
4. Viết **Description** — hiển thị cho student
5. Toggle **Publishing** → ON
6. Click **Save Changes**
7. Student login → thấy app trong sidebar → chat

> **Lưu ý**: Dataset phải có documents đã indexed (embeddings). Nếu chưa, upload documents vào dataset trước.
