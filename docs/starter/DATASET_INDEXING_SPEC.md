# Dataset Indexing Spec

## Storage: MinIO
- Put file to bucket with key:
  workspaces/{workspace_id}/datasets/{dataset_id}/documents/{document_id}/{filename}

MinIO is S3-compatible; using MinIO in self-hosted Dify-like stacks is common.
(Reference discussions: https://github.com/langgenius/dify/discussions/5300)

## Index pipeline (Worker)
1) Download file from MinIO
2) Extract text
   - PDF: text extraction
   - DOCX: paragraph extraction
3) Normalize text (remove repeated whitespace)
4) Chunking
   - chunk_size: 800–1200 tokens (or chars MVP)
   - overlap: 100–200 tokens
5) Embeddings (OpenAI)
6) Store:
   - chunks table
   - embeddings table (pgvector)
7) Mark document status = ready; store chunk_count

## Retrieval (API)
- Embed query
- Similarity search in pgvector limited to dataset_ids
- Return top_k chunks + score + source_url (presigned)
