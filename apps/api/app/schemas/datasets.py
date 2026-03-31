"""Pydantic schemas for datasets and documents."""

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------
class DatasetCreate(BaseModel):
    name: str
    description: str | None = None


class DatasetResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None
    document_count: int = 0
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
class DocumentResponse(BaseModel):
    id: str
    dataset_id: str
    filename: str
    content_type: str
    size: int
    status: str
    chunk_count: int
    error_message: str | None
    created_at: str
    updated_at: str


class DatasetDetailResponse(DatasetResponse):
    """Dataset with embedded documents list."""
    documents: list[DocumentResponse] = []
