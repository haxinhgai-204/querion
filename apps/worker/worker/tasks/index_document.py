"""Index document task — orchestrates the full pipeline."""

import os
import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from worker.db import get_db
from worker.pipeline.downloader import download
from worker.pipeline.parser import parse
from worker.pipeline.chunker import chunk_text
from worker.pipeline.embedder import embed_texts

logger = logging.getLogger(__name__)


def index_document(document_id: str) -> None:
    """Full indexing pipeline for a single document.

    Steps:
    1. Fetch document + active AI provider from DB
    2. Download file from MinIO
    3. Parse text
    4. Chunk text
    5. Embed chunks (OpenAI)
    6. Store chunks + embeddings in DB
    7. Update document status → ready
    """
    db = get_db()
    doc_id = uuid.UUID(document_id)

    try:
        # --- 1. Fetch document ---
        from sqlalchemy import text as sql_text

        row = db.execute(
            sql_text(
                "SELECT id, dataset_id, filename, content_type, storage_key, status "
                "FROM documents WHERE id = :id"
            ),
            {"id": doc_id},
        ).fetchone()

        if not row:
            logger.error(f"Document {document_id} not found")
            return

        dataset_id = row.dataset_id
        filename = row.filename
        content_type = row.content_type
        storage_key = row.storage_key

        logger.info(f"Indexing document: {filename} ({document_id})")

        # --- Fetch active embedding provider ---
        provider_row = db.execute(
            sql_text(
                "SELECT provider_name, api_key_encrypted, model_name FROM ai_providers "
                "WHERE is_active = true AND purpose = 'embedding' ORDER BY created_at LIMIT 1"
            )
        ).fetchone()

        if not provider_row:
            _mark_failed(db, doc_id, "No active embedding provider configured")
            return

        provider_name = provider_row.provider_name
        api_key_encrypted = provider_row.api_key_encrypted
        model_name = provider_row.model_name

        # --- 2. Download ---
        logger.info(f"Downloading from MinIO: {storage_key}")
        file_path = download(storage_key)

        try:
            # --- 3. Parse ---
            logger.info(f"Parsing: {filename}")
            text = parse(file_path, content_type)

            if not text.strip():
                _mark_failed(db, doc_id, "No text content extracted from document")
                return

            logger.info(f"Extracted {len(text)} chars")

            # --- 4. Chunk ---
            chunks = chunk_text(text)
            logger.info(f"Created {len(chunks)} chunks")

            if not chunks:
                _mark_failed(db, doc_id, "No chunks created from text")
                return

            # --- 5. Embed ---
            logger.info(f"Embedding {len(chunks)} chunks with {model_name}")
            texts = [c.content for c in chunks]
            embeddings = embed_texts(texts, api_key_encrypted, model_name, provider_name)

            # --- 6. Store chunks + embeddings ---
            logger.info("Storing chunks and embeddings in DB")

            # Clear old chunks/embeddings for this document
            db.execute(
                sql_text("DELETE FROM chunks WHERE document_id = :doc_id"),
                {"doc_id": doc_id},
            )

            for chunk, embedding_vec in zip(chunks, embeddings):
                chunk_id = uuid.uuid4()
                db.execute(
                    sql_text("""
                        INSERT INTO chunks (id, dataset_id, document_id, chunk_index, content, created_at)
                        VALUES (:id, :dataset_id, :document_id, :chunk_index, :content, :created_at)
                    """),
                    {
                        "id": chunk_id,
                        "dataset_id": dataset_id,
                        "document_id": doc_id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "created_at": datetime.now(timezone.utc),
                    },
                )

                # Store embedding as pgvector format string
                vec_str = "[" + ",".join(str(v) for v in embedding_vec) + "]"
                db.execute(
                    sql_text("""
                        INSERT INTO embeddings (chunk_id, embedding, model_name, created_at)
                        VALUES (:chunk_id, :embedding, :model_name, :created_at)
                    """),
                    {
                        "chunk_id": chunk_id,
                        "embedding": vec_str,
                        "model_name": model_name,
                        "created_at": datetime.now(timezone.utc),
                    },
                )

            # --- 7. Update document status ---
            db.execute(
                sql_text("""
                    UPDATE documents
                    SET status = 'ready', chunk_count = :count, error_message = NULL,
                        updated_at = :now
                    WHERE id = :id
                """),
                {
                    "count": len(chunks),
                    "now": datetime.now(timezone.utc),
                    "id": doc_id,
                },
            )
            db.commit()
            logger.info(f"Document {document_id} indexed successfully: {len(chunks)} chunks")

        finally:
            # Clean up temp file
            if os.path.exists(file_path):
                os.unlink(file_path)

    except Exception as e:
        logger.exception(f"Failed to index document {document_id}")
        _mark_failed(db, doc_id, str(e))
    finally:
        db.close()


def _mark_failed(db, doc_id: uuid.UUID, error: str) -> None:
    """Mark document as failed with error message."""
    from sqlalchemy import text as sql_text

    db.execute(
        sql_text("""
            UPDATE documents
            SET status = 'failed', error_message = :error, updated_at = :now
            WHERE id = :id
        """),
        {"error": error[:500], "now": datetime.now(timezone.utc), "id": doc_id},
    )
    db.commit()
    logger.error(f"Document {doc_id} marked as failed: {error}")
