# Phase 2 — Worker Indexing + pgvector Retrieval

> Goal: Document được index thành chunks + embeddings, query trả về top_k relevant chunks.

> **Cross-cutting**: Tất cả UI components phải dùng theme-aware colors (dark/light) và translation keys (EN/VI). Thêm translations vào `locales/{en,vi}/datasets.json`.
> **RBAC**: Worker jobs inherit workspace context. Retrieval scoped by workspace_id. Viewer không thể trigger indexing.
> **Responsive**: ChunksPreviewModal = full-screen bottom sheet (mobile) / centered modal 80% (tablet) / centered modal 60% (desktop).

## Tasks

### Backend — DB Models & Migrations

- [ ] **P2.1** — Tạo SQLAlchemy models
  - `chunks` table (id, dataset_id, document_id, chunk_index, content, created_at)
  - `embeddings` table (chunk_id PK/FK, embedding vector(N), model_name, created_at)
  - **Spec**: DB_SCHEMA.md

- [ ] **P2.2** — Alembic migration cho chunks + embeddings
  - Tạo vector index (HNSW hoặc IVFFlat) trên embeddings.embedding
  - Index trên chunks(dataset_id, document_id)

### Worker — Scaffold

- [ ] **P2.3** — Scaffold `apps/worker/`
  - Structure:
    ```
    apps/worker/
    ├── worker/
    │   ├── main.py           # worker entry point (RQ/Celery)
    │   ├── config.py         # shared config
    │   ├── tasks/
    │   │   └── index_document.py
    │   └── pipeline/
    │       ├── downloader.py   # fetch from MinIO
    │       ├── parser.py       # extract text (pdf/docx)
    │       ├── chunker.py      # split into chunks
    │       └── embedder.py     # OpenAI embeddings
    ├── requirements.txt
    └── Dockerfile
    ```

### Worker — Pipeline Steps

- [ ] **P2.4** — **Downloader**: fetch file từ MinIO
  - Input: storage_key
  - Output: file bytes hoặc temp file path

- [ ] **P2.5** — **Parser**: extract text
  - PDF: sử dụng PyPDF2 hoặc pdfplumber
  - DOCX: sử dụng python-docx
  - TXT: read trực tiếp
  - Output: raw text string
  - **Spec**: DATASET_INDEXING_SPEC.md

- [ ] **P2.6** — **Chunker**: split text thành chunks
  - chunk_size: 800-1200 chars (MVP dùng chars, sau upgrade tokens)
  - overlap: 100-200 chars
  - Normalize text (remove repeated whitespace) trước khi chunk
  - Output: list of {chunk_index, content}
  - **Spec**: DATASET_INDEXING_SPEC.md

- [ ] **P2.7** — **Embedder**: tạo embeddings
  - Gọi OpenAI embeddings API (text-embedding-3-small hoặc ada-002)
  - Batch embedding (nhiều chunks 1 lần)
  - Output: list of vectors
  - **Spec**: DATASET_INDEXING_SPEC.md

- [ ] **P2.8** — **Index task orchestrator**
  - Kết hợp download → parse → chunk → embed → store
  - Update document status: indexing → ready (hoặc failed + error_message)
  - Update chunk_count
  - Error handling: catch exceptions, mark failed

### Backend — Queue Integration

- [ ] **P2.9** — `POST /v1/documents/{document_id}/index` endpoint
  - Enqueue index job vào Redis queue
  - Return: { status: "indexing", job_id }
  - **Spec**: API_CONTRACT.md

- [ ] **P2.10** — Redis queue setup
  - Chọn RQ (simpler) hoặc Celery
  - Config trong docker-compose (worker service)

### Backend — Retrieval

- [ ] **P2.11** — Retrieval service
  - `app/services/retrieval.py`
  - Input: query string, dataset_ids, top_k
  - Steps: embed query → pgvector similarity search (cosine) → return chunks
  - Filter by dataset_ids
  - Return: [{chunk_id, content, score, document_id, dataset_id}]
  - **Spec**: DATASET_INDEXING_SPEC.md

- [ ] **P2.12** — `GET /v1/documents/{document_id}/chunks` endpoint
  - List chunks of a document (với pagination)
  - Return: chunks[]{chunk_id, chunk_index, content_preview}
  - **Spec**: API_CONTRACT.md

### Frontend — Index & Chunks

- [ ] **P2.13** — "Index" button trên DocumentsTable
  - Gọi POST /documents/{id}/index
  - Start polling document status
  - Disable button khi đang indexing

- [ ] **P2.14** — **ChunksPreviewModal** component
  - Click document → modal hiển thị chunks
  - Show chunk_index, content preview (truncated)
  - Paginate nếu nhiều chunks
  - Responsive: dùng `<ResponsiveModal>` — full-screen bottom sheet (mobile) / centered modal 80% (tablet) / centered modal 60% (desktop)
  - **Spec**: FRONTEND_SPEC.md

## Acceptance Criteria

- [ ] Upload doc → click Index → status chuyển indexing → ready
- [ ] Document ready: chunk_count > 0
- [ ] Chunks preview hiển thị nội dung đúng
- [ ] Retrieval query trả về relevant chunks (test qua API)
