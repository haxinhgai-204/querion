# Phase 1 — Datasets CRUD + Upload

> Goal: User tạo dataset, upload documents, thấy document status trong UI.

> **Cross-cutting**: Tất cả UI components phải dùng theme-aware colors (dark/light) và translation keys (EN/VI). Thêm translations vào `locales/{en,vi}/datasets.json`.
> **RBAC**: API endpoints phải require auth (JWT). Datasets scoped by workspace_id. Super admin có thể access cross-workspace. Viewer chỉ xem, editor CRUD, owner full.
> **Responsive**: Datasets list = cards 1-col (mobile) / 2-col (tablet) / table (desktop). DocumentsTable = stacked cards (mobile) / table (desktop). UploadDropzone = full-width tap-to-upload (mobile). Modals → bottom sheet (mobile).

## Tasks

### Backend — DB Models & Migrations

- [ ] **P1.1** — Tạo SQLAlchemy models
  - `datasets` table (id, workspace_id, name, description, created_at, updated_at)
  - `documents` table (id, dataset_id, filename, content_type, size, storage_key, status, chunk_count, error_message, created_at, updated_at)
  - status enum: uploaded | indexing | ready | failed
  - **Spec**: DB_SCHEMA.md

- [ ] **P1.2** — Alembic migration cho datasets + documents tables

### Backend — MinIO Integration

- [ ] **P1.3** — MinIO client wrapper
  - `app/storage.py`: upload_file, get_presigned_url, delete_file
  - Storage key format: `workspaces/{workspace_id}/datasets/{dataset_id}/documents/{document_id}/{filename}`
  - **Spec**: DATASET_INDEXING_SPEC.md

### Backend — API Endpoints

- [ ] **P1.4** — `POST /v1/datasets` — tạo dataset
  - Body: { name, description? }
  - Tạm hardcode workspace_id (MVP, chưa có auth)
  - Return: dataset object
  - **Spec**: API_CONTRACT.md

- [ ] **P1.5** — `GET /v1/datasets` — list datasets
  - Scoped by workspace_id
  - Include document count per dataset
  - **Spec**: API_CONTRACT.md

- [ ] **P1.6** — `GET /v1/datasets/{dataset_id}` — dataset detail
  - Include documents list với status

- [ ] **P1.7** — `POST /v1/datasets/{dataset_id}/documents/upload`
  - Accept multipart/form-data (file field)
  - Validate file type (pdf, docx, txt)
  - Upload to MinIO
  - Create document record với status=uploaded
  - Return: document object
  - **Spec**: API_CONTRACT.md, DATASET_INDEXING_SPEC.md

- [ ] **P1.8** — `GET /v1/documents/{document_id}` — document detail
  - Return status, chunk_count, error_message
  - **Spec**: API_CONTRACT.md

### Backend — Pydantic Schemas

- [ ] **P1.9** — Request/Response schemas
  - DatasetCreate, DatasetResponse, DatasetListResponse
  - DocumentResponse, DocumentUploadResponse

### Frontend — Datasets List Page

- [ ] **P1.10** — `/datasets` page
  - Fetch & hiển thị list datasets
  - Responsive: cards 1-col (mobile) / 2-col (tablet) / table hoặc 3-col cards (desktop)
  - Button "New Dataset" → modal (desktop) / bottom sheet (mobile)
  - **Spec**: FRONTEND_SPEC.md

### Frontend — Dataset Detail Page

- [ ] **P1.11** — `/datasets/[datasetId]` page
  - Hiển thị dataset info (name, description, doc count)
  - **DocumentsTable** component: dùng `<ResponsiveTable>` — table (desktop) / stacked cards (mobile, mỗi doc = card với filename, status, actions)
  - Tablet: simplified table (ẩn size column)
  - **Spec**: FRONTEND_SPEC.md

- [ ] **P1.12** — **UploadDropzone** component
  - Desktop/tablet: drag & drop area + click to upload
  - Mobile: full-width tap-to-upload button (không hiện drag hint vì mobile không drag)
  - Support multiple files
  - Show upload progress
  - Accept: .pdf, .docx, .txt
  - **Spec**: FRONTEND_SPEC.md

- [ ] **P1.13** — Document status badge + polling
  - Hiển thị status badge (uploaded/indexing/ready/failed)
  - Poll status khi document đang indexing
  - **Spec**: FRONTEND_SPEC.md (UX rules)

### Frontend — API Client

- [ ] **P1.14** — API client functions cho datasets
  - `lib/api/datasets.ts`: createDataset, listDatasets, getDataset
  - `lib/api/documents.ts`: uploadDocument, getDocument

## Acceptance Criteria

- [ ] Tạo dataset qua UI → thấy trong list
- [ ] Upload file → document xuất hiện với status `uploaded`
- [ ] API trả đúng format theo API_CONTRACT.md
