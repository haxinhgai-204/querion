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


# ---------- App Chat (admin preview) ----------

class AdminChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ConversationItem(BaseModel):
    id: str
    title: str
    message_count: int
    updated_at: str


@router.get("/apps/{app_id}/conversations", response_model=list[ConversationItem])
async def list_app_conversations(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
):
    """List conversations for an app (admin chat preview)."""
    from sqlalchemy import func
    from app.models.conversation import Conversation
    from app.models.message import Message

    app = await db.get(App, uuid.UUID(app_id))
    if not app or app.workspace_id != ws_ctx.workspace_id:
        raise HTTPException(status_code=404, detail="App not found")

    result = await db.execute(
        select(Conversation).where(
            Conversation.app_id == uuid.UUID(app_id),
            Conversation.student_id == None,  # admin conversations only
        ).order_by(Conversation.updated_at.desc())
    )
    convs = result.scalars().all()

    out = []
    for conv in convs:
        count = await db.execute(
            select(func.count()).select_from(Message).where(Message.conversation_id == conv.id)
        )
        out.append(ConversationItem(
            id=str(conv.id), title=conv.title,
            message_count=count.scalar() or 0,
            updated_at=conv.updated_at.isoformat(),
        ))
    return out


@router.post("/apps/{app_id}/chat")
async def admin_app_chat(
    app_id: str,
    body: AdminChatRequest,
    db: AsyncSession = Depends(get_db),
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
):
    """Admin chat preview for an app — streaming SSE."""
    import json
    from datetime import datetime, timezone
    from fastapi.responses import StreamingResponse
    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.services.chat import chat_stream, get_active_llm_provider, generate_title
    from app.services.retrieval import retrieve
    from app.services.encryption import decrypt_key
    from sqlalchemy import func

    app = await db.get(App, uuid.UUID(app_id))
    if not app or app.workspace_id != ws_ctx.workspace_id:
        raise HTTPException(status_code=404, detail="App not found")

    # Get or create conversation
    if body.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == uuid.UUID(body.conversation_id),
                Conversation.app_id == uuid.UUID(app_id),
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = Conversation(
            workspace_id=ws_ctx.workspace_id,
            dataset_id=app.dataset_id,
            app_id=app.id,
            title="New Chat",
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

    # Save user message
    user_msg = Message(conversation_id=conv.id, role="user", content=body.message)
    db.add(user_msg)
    await db.commit()

    # Check if first
    msg_count_result = await db.execute(
        select(func.count()).select_from(Message).where(Message.conversation_id == conv.id)
    )
    is_first = (msg_count_result.scalar() or 0) == 1

    # History
    history_result = await db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in history_result.scalars().all()
        if m.id != user_msg.id
    ]

    async def generate():
        yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': str(conv.id)})}\n\n"

        full_response = ""
        sources = []

        if app.workflow_id:
            from app.models.workflow import Workflow
            from app.services.workflow_runtime import run_workflow

            wf = await db.get(Workflow, app.workflow_id)
            if not wf or not wf.graph_json:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Workflow not found or empty.'})}\n\n"
                yield "data: [DONE]\n\n"
                return

            try:
                result = await run_workflow(db=db, graph_json=wf.graph_json, query=body.message, history=history, app_system_prompt=app.system_prompt or None)
                full_response = result.get("answer", "")
                sources = result.get("retriever_resources", [])
                if sources:
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
                if full_response:
                    yield f"data: {json.dumps({'type': 'token', 'content': full_response})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        else:
            if app.dataset_id:
                sources = await retrieve(db=db, query=body.message, dataset_ids=[app.dataset_id], top_k=15)
                if sources:
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

            provider = await get_active_llm_provider(db)
            if not provider:
                yield f"data: {json.dumps({'type': 'error', 'content': 'No active LLM provider configured.'})}\n\n"
                yield "data: [DONE]\n\n"
                return

            system = app.system_prompt or "You are a helpful assistant."
            if app.dataset_id:
                context = "\n\n".join(f"[#{i}] {s['content']}" for i, s in enumerate(sources)) if sources else "No relevant context found."
                system += f"\n\nDocument Context:\n{context}"
                system += "\n\nCRITICAL INSTRUCTION: You must answer using ONLY the provided 'Document Context' above. If the context is empty or does not contain the answer, you MUST apologize politely and state that you cannot find this information in the documents. Do NOT use your own external knowledge to answer."

            messages = [{"role": "system", "content": system}]
            for msg in history[-10:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": body.message})

            api_key = decrypt_key(provider.api_key_encrypted)

            try:
                from app.services.chat import _stream_openai, _stream_google, _stream_anthropic, PROVIDER_BASE_URLS
                base_url = PROVIDER_BASE_URLS.get(provider.provider_name)
                if base_url:  # openrouter, vilao, etc.
                    async for chunk in _stream_openai(api_key, provider.model_name, messages, base_url=base_url):
                        yield chunk
                        try:
                            data = json.loads(chunk[6:])
                            if data.get("type") == "token":
                                full_response += data["content"]
                        except: pass
                elif provider.provider_name == "google":
                    async for chunk in _stream_google(api_key, provider.model_name, messages):
                        yield chunk
                        try:
                            data = json.loads(chunk[6:])
                            if data.get("type") == "token":
                                full_response += data["content"]
                        except: pass
                elif provider.provider_name == "anthropic":
                    async for chunk in _stream_anthropic(api_key, provider.model_name, messages):
                        yield chunk
                        try:
                            data = json.loads(chunk[6:])
                            if data.get("type") == "token":
                                full_response += data["content"]
                        except: pass
                else:
                    async for chunk in _stream_openai(api_key, provider.model_name, messages):
                        yield chunk
                        try:
                            data = json.loads(chunk[6:])
                            if data.get("type") == "token":
                                full_response += data["content"]
                        except: pass
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

        if full_response:
            assistant_msg = Message(
                conversation_id=conv.id, role="assistant",
                content=full_response, sources=sources[:3] if sources else None,
            )
            db.add(assistant_msg)
            conv.updated_at = datetime.now(timezone.utc)
            await db.commit()

            if is_first:
                try:
                    title = await generate_title(db, body.message, full_response)
                    if title:
                        conv.title = title
                        await db.commit()
                        yield f"data: {json.dumps({'type': 'title', 'title': title})}\n\n"
                except: pass

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no",
    })
