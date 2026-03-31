"""Apps CRUD router + embedded Runs read endpoints."""

import uuid
import secrets
from typing import Any

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.auth.deps import require_ws_role, WorkspaceContext
from app.models.user_workspace import WsRole
from app.models.app import App
from app.models.run import Run, RunStep

router = APIRouter(prefix="/v1", tags=["apps"])


# ---------- Schemas ----------

class AppCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    workflow_id: str | None = None
    dataset_id: str | None = None
    model_config_json: dict[str, Any] | None = None
    system_prompt: str | None = ""


class AppUpdate(BaseModel):
    name: str | None = None
    workflow_id: str | None = None
    dataset_id: str | None = None
    model_config_json: dict[str, Any] | None = None
    system_prompt: str | None = None
    description: str | None = None
    is_published: bool | None = None


class AppResponse(BaseModel):
    id: str
    name: str
    workflow_id: str | None
    dataset_id: str | None
    model_config_json: dict[str, Any] | None
    system_prompt: str | None
    api_key: str
    description: str | None
    is_published: bool
    created_at: str
    updated_at: str


class RunResponse(BaseModel):
    id: str
    app_id: str | None
    workflow_id: str | None
    conversation_id: str | None
    status: str
    started_at: str
    ended_at: str | None
    latency_ms: int | None


class RunStepResponse(BaseModel):
    id: str
    node_id: str
    node_type: str
    started_at: str
    ended_at: str | None
    duration_ms: int | None
    input_json: dict[str, Any] | None
    output_json: dict[str, Any] | None


# ---------- Helpers ----------

def _to_response(app: App) -> AppResponse:
    return AppResponse(
        id=str(app.id),
        name=app.name,
        workflow_id=str(app.workflow_id) if app.workflow_id else None,
        dataset_id=str(app.dataset_id) if app.dataset_id else None,
        model_config_json=app.model_config_json,
        system_prompt=app.system_prompt,
        api_key=app.api_key,
        description=app.description,
        is_published=app.is_published,
        created_at=app.created_at.isoformat(),
        updated_at=app.updated_at.isoformat(),
    )


def _run_to_response(run: Run) -> RunResponse:
    return RunResponse(
        id=str(run.id),
        app_id=str(run.app_id) if run.app_id else None,
        workflow_id=str(run.workflow_id) if run.workflow_id else None,
        conversation_id=str(run.conversation_id) if run.conversation_id else None,
        status=run.status,
        started_at=run.started_at.isoformat(),
        ended_at=run.ended_at.isoformat() if run.ended_at else None,
        latency_ms=run.latency_ms,
    )


def _step_to_response(step: RunStep) -> RunStepResponse:
    duration = None
    if step.started_at and step.ended_at:
        duration = int((step.ended_at - step.started_at).total_seconds() * 1000)
    return RunStepResponse(
        id=str(step.id),
        node_id=step.node_id,
        node_type=step.node_type,
        started_at=step.started_at.isoformat(),
        ended_at=step.ended_at.isoformat() if step.ended_at else None,
        duration_ms=duration,
        input_json=step.input_json,
        output_json=step.output_json,
    )


# ---------- App CRUD ----------

@router.post("/apps", response_model=AppResponse, status_code=201)
async def create_app(
    body: AppCreate,
    db: AsyncSession = Depends(get_db),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
):
    app = App(
        workspace_id=ws_ctx.workspace_id,
        name=body.name,
        workflow_id=uuid.UUID(body.workflow_id) if body.workflow_id else None,
        dataset_id=uuid.UUID(body.dataset_id) if body.dataset_id else None,
        model_config_json=body.model_config_json or {},
        system_prompt=body.system_prompt or "",
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return _to_response(app)


@router.get("/apps", response_model=list[AppResponse])
async def list_apps(
    db: AsyncSession = Depends(get_db),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
):
    result = await db.execute(
        select(App)
        .where(App.workspace_id == ws_ctx.workspace_id)
        .order_by(App.created_at.desc())
    )
    return [_to_response(a) for a in result.scalars().all()]


@router.get("/apps/{app_id}", response_model=AppResponse)
async def get_app(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
):
    app = await db.get(App, uuid.UUID(app_id))
    if not app or app.workspace_id != ws_ctx.workspace_id:
        raise HTTPException(status_code=404, detail="App not found")
    return _to_response(app)


@router.patch("/apps/{app_id}", response_model=AppResponse)
async def update_app(
    app_id: str,
    body: AppUpdate,
    db: AsyncSession = Depends(get_db),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
):
    app = await db.get(App, uuid.UUID(app_id))
    if not app or app.workspace_id != ws_ctx.workspace_id:
        raise HTTPException(status_code=404, detail="App not found")

    if body.name is not None:
        app.name = body.name
    if body.workflow_id is not None:
        app.workflow_id = uuid.UUID(body.workflow_id) if body.workflow_id else None
    if body.dataset_id is not None:
        app.dataset_id = uuid.UUID(body.dataset_id) if body.dataset_id else None
    if body.model_config_json is not None:
        app.model_config_json = body.model_config_json
    if body.system_prompt is not None:
        app.system_prompt = body.system_prompt
    if body.description is not None:
        app.description = body.description
    if body.is_published is not None:
        app.is_published = body.is_published

    await db.commit()
    await db.refresh(app)
    return _to_response(app)


@router.delete("/apps/{app_id}", status_code=204)
async def delete_app(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
):
    app = await db.get(App, uuid.UUID(app_id))
    if not app or app.workspace_id != ws_ctx.workspace_id:
        raise HTTPException(status_code=404, detail="App not found")
    await db.delete(app)
    await db.commit()


@router.post("/apps/{app_id}/regenerate-key", response_model=AppResponse)
async def regenerate_api_key(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
):
    app = await db.get(App, uuid.UUID(app_id))
    if not app or app.workspace_id != ws_ctx.workspace_id:
        raise HTTPException(status_code=404, detail="App not found")
    app.api_key = f"app-{secrets.token_urlsafe(32)}"
    await db.commit()
    await db.refresh(app)
    return _to_response(app)


# ---------- Runs (read-only, nested under app) ----------

@router.get("/apps/{app_id}/runs", response_model=list[RunResponse])
async def list_runs(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
):
    # Verify app belongs to workspace
    app = await db.get(App, uuid.UUID(app_id))
    if not app or app.workspace_id != ws_ctx.workspace_id:
        raise HTTPException(status_code=404, detail="App not found")

    result = await db.execute(
        select(Run)
        .where(Run.app_id == uuid.UUID(app_id))
        .order_by(Run.started_at.desc())
        .limit(50)
    )
    return [_run_to_response(r) for r in result.scalars().all()]


@router.get("/runs/{run_id}/steps", response_model=list[RunStepResponse])
async def get_run_steps(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
):
    result = await db.execute(
        select(RunStep)
        .where(RunStep.run_id == uuid.UUID(run_id))
        .order_by(RunStep.started_at)
    )
    return [_step_to_response(s) for s in result.scalars().all()]
