"""Datasets CRUD router."""

import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)
from pydantic import BaseModel
from sqlalchemy import select, func, text as sql_text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.auth.deps import get_workspace_context, require_ws_role, WorkspaceContext
from app.models.user_workspace import WsRole
from app.models.dataset import Dataset
from app.models.document import Document
from app.models.app import App
from app.schemas.datasets import (
    DatasetCreate,
    DatasetResponse,
    DatasetDetailResponse,
    DocumentResponse,
)

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])


class DatasetUsageResponse(BaseModel):
    dataset_id: str
    document_count: int
    apps: List[dict]  # [{id, name}]


# -- Helpers --
def _dataset_to_response(ds: Dataset, doc_count: int = 0) -> DatasetResponse:
    return DatasetResponse(
        id=str(ds.id),
        workspace_id=str(ds.workspace_id),
        name=ds.name,
        description=ds.description,
        document_count=doc_count,
        created_at=ds.created_at.isoformat(),
        updated_at=ds.updated_at.isoformat(),
    )


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


# -- Endpoints --
@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    body: DatasetCreate,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new dataset in the current workspace."""
    dataset = Dataset(
        workspace_id=ws_ctx.workspace_id,
        name=body.name,
        description=body.description,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return _dataset_to_response(dataset)


@router.get("", response_model=list[DatasetResponse])
async def list_datasets(
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
    db: AsyncSession = Depends(get_db),
):
    """List all datasets in the current workspace."""
    stmt = (
        select(Dataset, func.count(Document.id).label("doc_count"))
        .outerjoin(Document, Document.dataset_id == Dataset.id)
        .where(Dataset.workspace_id == ws_ctx.workspace_id)
        .group_by(Dataset.id)
        .order_by(Dataset.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [_dataset_to_response(ds, doc_count) for ds, doc_count in rows]


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
async def get_dataset(
    dataset_id: str,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
    db: AsyncSession = Depends(get_db),
):
    """Get dataset detail with list of documents."""
    ds_uuid = uuid.UUID(dataset_id)
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == ds_uuid,
            Dataset.workspace_id == ws_ctx.workspace_id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    docs_result = await db.execute(
        select(Document)
        .where(Document.dataset_id == ds_uuid)
        .order_by(Document.created_at.desc())
    )
    documents = docs_result.scalars().all()

    return DatasetDetailResponse(
        id=str(dataset.id),
        workspace_id=str(dataset.workspace_id),
        name=dataset.name,
        description=dataset.description,
        document_count=len(documents),
        created_at=dataset.created_at.isoformat(),
        updated_at=dataset.updated_at.isoformat(),
        documents=[_doc_to_response(doc) for doc in documents],
    )


@router.get("/{dataset_id}/usage", response_model=DatasetUsageResponse)
async def get_dataset_usage(
    dataset_id: str,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
    db: AsyncSession = Depends(get_db),
):
    """Check how many documents and which apps are using this dataset."""
    ds_uuid = uuid.UUID(dataset_id)
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == ds_uuid,
            Dataset.workspace_id == ws_ctx.workspace_id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    doc_count_result = await db.execute(
        select(func.count(Document.id)).where(Document.dataset_id == ds_uuid)
    )
    doc_count = doc_count_result.scalar() or 0

    apps_result = await db.execute(
        select(App).where(
            App.dataset_id == ds_uuid,
            App.workspace_id == ws_ctx.workspace_id,
        )
    )
    linked_apps = [{"id": str(a.id), "name": a.name} for a in apps_result.scalars().all()]

    return DatasetUsageResponse(
        dataset_id=dataset_id,
        document_count=doc_count,
        apps=linked_apps,
    )


@router.delete("/{dataset_id}", status_code=status.HTTP_200_OK)
async def delete_dataset(
    dataset_id: str,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a dataset and all its documents."""
    ds_uuid = uuid.UUID(dataset_id)
    logger.info("DELETE dataset request: id=%s workspace=%s", dataset_id, ws_ctx.workspace_id)

    # Load dataset with documents eagerly to avoid lazy-load issues in async session
    result = await db.execute(
        select(Dataset)
        .options(selectinload(Dataset.documents))
        .where(
            Dataset.id == ds_uuid,
            Dataset.workspace_id == ws_ctx.workspace_id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        logger.warning("DELETE dataset not found: id=%s", dataset_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    logger.info("Deleting dataset %r with %d docs", dataset.name, len(dataset.documents))

    # Collect storage keys before deleting from DB
    storage_keys = [doc.storage_key for doc in dataset.documents]

    try:
        # Delete dataset (cascade="all, delete-orphan" will remove child documents)
        await db.execute(
            sql_text(
                "DELETE FROM embeddings "
                "WHERE chunk_id IN (SELECT id FROM chunks WHERE dataset_id = :dataset_id)"
            ),
            {"dataset_id": ds_uuid},
        )
        await db.execute(
            sql_text("DELETE FROM chunks WHERE dataset_id = :dataset_id"),
            {"dataset_id": ds_uuid},
        )
        await db.execute(
            sql_text("DELETE FROM documents WHERE dataset_id = :dataset_id"),
            {"dataset_id": ds_uuid},
        )
        await db.execute(
            sql_text("UPDATE apps SET dataset_id = NULL WHERE dataset_id = :dataset_id"),
            {"dataset_id": ds_uuid},
        )
        await db.execute(
            sql_text(
                "DELETE FROM datasets "
                "WHERE id = :dataset_id AND workspace_id = :workspace_id"
            ),
            {"dataset_id": ds_uuid, "workspace_id": ws_ctx.workspace_id},
        )
        await db.commit()
        logger.info("Dataset %s deleted from DB successfully", dataset_id)
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to delete dataset %s: %s", dataset_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Delete failed: {exc}",
        )

    # Best-effort: clean up MinIO files after DB deletion succeeds
    from app.storage import delete_file
    for key in storage_keys:
        try:
            delete_file(key)
        except Exception as exc:
            logger.warning("Failed to delete MinIO file %s: %s", key, exc)

    return {"detail": "Dataset deleted"}
