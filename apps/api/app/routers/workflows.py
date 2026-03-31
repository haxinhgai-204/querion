"""Workflows router — CRUD + test run."""

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.auth.deps import require_ws_role, WorkspaceContext
from app.models.user_workspace import WsRole
from app.models.workflow import Workflow
from app.services.workflow_validator import validate_graph, ValidationError
from app.services.workflow_runtime import run_workflow

router = APIRouter(prefix="/v1", tags=["workflows"])


# ---------- Schemas ----------

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    type: str = "chatflow"  # chatflow | workflow
    description: str | None = ""
    dataset_id: str | None = None
    graph_json: dict[str, Any] = Field(default_factory=lambda: {"nodes": [], "edges": []})


class WorkflowUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    description: str | None = None
    dataset_id: str | None = None
    graph_json: dict[str, Any] | None = None


class WorkflowResponse(BaseModel):
    id: str
    type: str
    name: str
    description: str | None
    dataset_id: str | None
    graph_json: dict[str, Any]
    node_count: int
    created_at: str
    updated_at: str


class RunRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    inputs: dict[str, Any] | None = None


class RunResponse(BaseModel):
    answer: str
    extracted_params: dict[str, Any] = {}
    retriever_resources: list[dict[str, Any]]


def _to_response(wf: Workflow) -> WorkflowResponse:
    graph = wf.graph_json or {}
    return WorkflowResponse(
        id=str(wf.id),
        type=wf.type,
        name=wf.name,
        description=wf.description,
        dataset_id=str(wf.dataset_id) if wf.dataset_id else None,
        graph_json=graph,
        node_count=len(graph.get("nodes", [])),
        created_at=wf.created_at.isoformat(),
        updated_at=wf.updated_at.isoformat(),
    )


# ---------- CRUD ----------

@router.post("/workflows", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    body: WorkflowCreate,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow."""
    # Validate graph if provided
    if body.graph_json.get("nodes"):
        try:
            validate_graph(body.graph_json)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    wf = Workflow(
        workspace_id=ws_ctx.workspace_id,
        type=body.type,
        name=body.name,
        description=body.description,
        dataset_id=uuid.UUID(body.dataset_id) if body.dataset_id else None,
        graph_json=body.graph_json,
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return _to_response(wf)


@router.get("/workflows", response_model=list[WorkflowResponse])
async def list_workflows(
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
    db: AsyncSession = Depends(get_db),
):
    """List workflows for the current workspace."""
    result = await db.execute(
        select(Workflow)
        .where(Workflow.workspace_id == ws_ctx.workspace_id)
        .order_by(Workflow.updated_at.desc())
    )
    return [_to_response(wf) for wf in result.scalars().all()]


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
    db: AsyncSession = Depends(get_db),
):
    """Get a workflow by ID."""
    wf = await _get_workflow(db, workflow_id, ws_ctx.workspace_id)
    return _to_response(wf)


@router.patch("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    body: WorkflowUpdate,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
    db: AsyncSession = Depends(get_db),
):
    """Update a workflow."""
    wf = await _get_workflow(db, workflow_id, ws_ctx.workspace_id)

    if body.name is not None:
        wf.name = body.name
    if body.type is not None:
        wf.type = body.type
    if body.description is not None:
        wf.description = body.description
    if body.dataset_id is not None:
        wf.dataset_id = uuid.UUID(body.dataset_id) if body.dataset_id else None
    if body.graph_json is not None:
        # Validate new graph
        if body.graph_json.get("nodes"):
            try:
                validate_graph(body.graph_json)
            except ValidationError as e:
                raise HTTPException(status_code=400, detail=str(e))
        wf.graph_json = body.graph_json

    wf.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(wf)
    return _to_response(wf)


@router.delete("/workflows/{workflow_id}", status_code=200)
async def delete_workflow(
    workflow_id: str,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a workflow."""
    wf = await _get_workflow(db, workflow_id, ws_ctx.workspace_id)
    await db.delete(wf)
    await db.commit()
    return {"detail": "Workflow deleted"}


# ---------- Run ----------

@router.post("/workflows/{workflow_id}/run", response_model=RunResponse)
async def run_workflow_endpoint(
    workflow_id: str,
    body: RunRequest,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
    db: AsyncSession = Depends(get_db),
):
    """Test run a workflow with a query."""
    wf = await _get_workflow(db, workflow_id, ws_ctx.workspace_id)

    # Validate before running
    try:
        validate_graph(wf.graph_json)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid workflow graph: {e}")

    try:
        result = await run_workflow(db, wf.graph_json, body.query, body.inputs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {e}")

    return RunResponse(
        answer=result["answer"],
        extracted_params=result.get("extracted_params", {}),
        retriever_resources=result["retriever_resources"],
    )


# ---------- Helpers ----------

async def _get_workflow(db: AsyncSession, workflow_id: str, workspace_id: uuid.UUID) -> Workflow:
    wf_uuid = uuid.UUID(workflow_id)
    result = await db.execute(
        select(Workflow).where(
            Workflow.id == wf_uuid,
            Workflow.workspace_id == workspace_id,
        )
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf
