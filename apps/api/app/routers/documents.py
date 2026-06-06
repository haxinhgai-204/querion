"""Documents router — upload, detail, delete, index, chunks."""

import uuid

import redis
import sys
import multiprocessing

# Patch multiprocessing for Windows — rq internally uses fork context
if sys.platform == "win32":
    _original_get_context = multiprocessing.get_context
    def _patched_get_context(method=None):
        if method == "fork":
            return _original_get_context("spawn")
        return _original_get_context(method)
    multiprocessing.get_context = _patched_get_context

from rq import Queue
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.auth.deps import get_workspace_context, require_ws_role, WorkspaceContext
from app.models.user_workspace import WsRole
from app.models.dataset import Dataset
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.schemas.datasets import DocumentResponse
from app.storage import upload_file, make_storage_key, delete_file
from app.config import settings

router = APIRouter(prefix="/v1", tags=["documents"])

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def _doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc.id),
        dataset_id=str(doc.dataset_id),
        filename=doc.filename,
        content_type=doc.content_type,
        size=doc.size,
        status=doc.status.value,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
    )


@router.post(
    "/datasets/{dataset_id}/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    dataset_id: str,
    file: UploadFile = File(...),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document to a dataset."""
    ds_uuid = uuid.UUID(dataset_id)

    # Verify dataset belongs to workspace
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == ds_uuid,
            Dataset.workspace_id == ws_ctx.workspace_id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    # Validate file extension
    filename = file.filename or "unnamed"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB",
        )

    content_type = file.content_type or "application/octet-stream"
    doc_id = uuid.uuid4()
    storage_key = make_storage_key(
        str(ws_ctx.workspace_id), str(ds_uuid), str(doc_id), filename
    )

    # Upload to MinIO
    upload_file(storage_key, data, content_type)

    # Create DB record
    document = Document(
        id=doc_id,
        dataset_id=ds_uuid,
        filename=filename,
        content_type=content_type,
        size=len(data),
        storage_key=storage_key,
        status=DocumentStatus.uploaded,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Auto-trigger indexing
    try:
        document.status = DocumentStatus.indexing
        await db.commit()

        if Queue is not None:
            conn = redis.from_url(settings.REDIS_URL)
            q = Queue("querion-indexing", connection=conn)
            q.enqueue("worker.tasks.index_document.index_document", str(doc_id))
    except Exception:
        # If queue fails, keep as "uploaded" so user can retry manually
        document.status = DocumentStatus.uploaded
        await db.commit()

    return _doc_to_response(document)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
    db: AsyncSession = Depends(get_db),
):
    """Get document detail."""
    doc_uuid = uuid.UUID(document_id)
    result = await db.execute(
        select(Document)
        .join(Dataset, Dataset.id == Document.dataset_id)
        .where(
            Document.id == doc_uuid,
            Dataset.workspace_id == ws_ctx.workspace_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _doc_to_response(document)


@router.delete("/documents/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: str,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its MinIO file."""
    doc_uuid = uuid.UUID(document_id)
    result = await db.execute(
        select(Document)
        .join(Dataset, Dataset.id == Document.dataset_id)
        .where(
            Document.id == doc_uuid,
            Dataset.workspace_id == ws_ctx.workspace_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Delete from MinIO
    try:
        delete_file(document.storage_key)
    except Exception:
        pass  # best-effort

    # Explicitly delete chunks + embeddings to avoid cascade issues with orphan rows
    from sqlalchemy import text as sql_text
    await db.execute(
        sql_text("DELETE FROM embeddings WHERE chunk_id IN (SELECT id FROM chunks WHERE document_id = :doc_id)"),
        {"doc_id": doc_uuid},
    )
    await db.execute(
        sql_text("DELETE FROM chunks WHERE document_id = :doc_id"),
        {"doc_id": doc_uuid},
    )

    await db.delete(document)
    await db.commit()
    return {"detail": "Document deleted"}


# ---------- Index endpoint ----------

@router.post("/documents/{document_id}/index", status_code=status.HTTP_202_ACCEPTED)
async def index_document(
    document_id: str,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
    db: AsyncSession = Depends(get_db),
):
    """Trigger indexing for a document. Enqueues an RQ job."""
    doc_uuid = uuid.UUID(document_id)
    result = await db.execute(
        select(Document)
        .join(Dataset, Dataset.id == Document.dataset_id)
        .where(
            Document.id == doc_uuid,
            Dataset.workspace_id == ws_ctx.workspace_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status == DocumentStatus.indexing:
        raise HTTPException(status_code=400, detail="Document is already being indexed")

    # Update status to indexing
    document.status = DocumentStatus.indexing
    document.error_message = None
    await db.commit()

    # Enqueue RQ job
    if Queue is not None:
        conn = redis.from_url(settings.REDIS_URL)
        q = Queue("querion-indexing", connection=conn)
        job = q.enqueue("worker.tasks.index_document.index_document", str(doc_uuid))
        return {"status": "indexing", "job_id": job.id}
    else:
        return {"status": "indexing", "job_id": None}


# ---------- Chunks endpoint ----------

@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
    db: AsyncSession = Depends(get_db),
):
    """List chunks of a document with pagination."""
    doc_uuid = uuid.UUID(document_id)

    # Verify document access
    result = await db.execute(
        select(Document)
        .join(Dataset, Dataset.id == Document.dataset_id)
        .where(
            Document.id == doc_uuid,
            Dataset.workspace_id == ws_ctx.workspace_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == doc_uuid)
    )
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    chunks_result = await db.execute(
        select(Chunk)
        .where(Chunk.document_id == doc_uuid)
        .order_by(Chunk.chunk_index)
        .offset(offset)
        .limit(page_size)
    )
    chunks = chunks_result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "chunks": [
            {
                "id": str(c.id),
                "chunk_index": c.chunk_index,
                "content": c.content,
                "content_preview": c.content[:200] if c.content else "",
            }
            for c in chunks
        ],
    }


# ---------- Update chunk endpoint ----------

from pydantic import BaseModel


class ChunkUpdateBody(BaseModel):
    content: str


@router.patch("/chunks/{chunk_id}", status_code=status.HTTP_200_OK)
async def update_chunk(
    chunk_id: str,
    body: ChunkUpdateBody,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
    db: AsyncSession = Depends(get_db),
):
    """Update chunk content and re-embed it."""
    from sqlalchemy import text as sql_text
    from app.models.ai_provider import AiProvider
    from app.services.encryption import decrypt_key

    chunk_uuid = uuid.UUID(chunk_id)

    # Verify chunk access through workspace
    result = await db.execute(
        select(Chunk)
        .join(Document, Document.id == Chunk.document_id)
        .join(Dataset, Dataset.id == Document.dataset_id)
        .where(
            Chunk.id == chunk_uuid,
            Dataset.workspace_id == ws_ctx.workspace_id,
        )
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    # Update content
    chunk.content = body.content.strip()
    await db.commit()

    # Re-embed: find active embedding provider
    provider_result = await db.execute(
        select(AiProvider).where(
            AiProvider.is_active == True,
            AiProvider.purpose == "embedding",
        ).order_by(AiProvider.created_at).limit(1)
    )
    provider = provider_result.scalar_one_or_none()

    if provider:
        try:
            import openai as openai_mod

            api_key = decrypt_key(provider.api_key_encrypted)
            model_name = provider.model_name

            if provider.provider_name == "google":
                from google import genai
                client = genai.Client(api_key=api_key)
                gmodel = model_name if model_name.startswith("models/") else f"models/{model_name}"
                result_emb = client.models.embed_content(model=gmodel, contents=[chunk.content])
                vec = result_emb.embeddings[0].values
            else:
                client = openai_mod.OpenAI(api_key=api_key)
                resp = client.embeddings.create(input=[chunk.content], model=model_name)
                vec = resp.data[0].embedding

            # Pad/truncate to 1536
            if len(vec) < 1536:
                vec = list(vec) + [0.0] * (1536 - len(vec))
            vec = vec[:1536]

            vec_str = "[" + ",".join(str(v) for v in vec) + "]"
            await db.execute(
                sql_text("""
                    INSERT INTO embeddings (chunk_id, embedding, model_name, created_at)
                    VALUES (:chunk_id, :embedding, :model_name, now())
                    ON CONFLICT (chunk_id) DO UPDATE
                    SET embedding = :embedding, model_name = :model_name, created_at = now()
                """),
                {"chunk_id": chunk_uuid, "embedding": vec_str, "model_name": model_name},
            )
            await db.commit()
        except Exception as e:
            # Don't fail the update if re-embedding fails
            pass

    return {
        "id": str(chunk.id),
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "re_embedded": provider is not None,
    }

