"""Student authentication — login, me, change-password, published apps."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.deps import get_db
from app.auth.security import verify_password, hash_password, create_access_token, create_refresh_token, decode_token
from app.models.student import Student
from app.models.app import App
from app.models.workspace import Workspace

router = APIRouter(prefix="/v1/student", tags=["student-auth"])


# -- Schemas --
class StudentLoginRequest(BaseModel):
    email: str
    password: str


class StudentResponse(BaseModel):
    id: str
    email: str
    name: str
    student_id: str | None
    must_change_password: bool


class StudentLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    student: StudentResponse


class ChangePasswordRequest(BaseModel):
    new_password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str


class PublishedAppItem(BaseModel):
    id: str
    name: str
    description: str | None


class WorkspaceAppsGroup(BaseModel):
    workspace_name: str
    apps: list[PublishedAppItem]


# -- Dependency --
async def require_student(request: Request, db: AsyncSession = Depends(get_db)) -> Student:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    payload = decode_token(auth[7:])
    if not payload or payload.get("type") != "access" or payload.get("role") != "student":
        raise HTTPException(status_code=401, detail="Invalid student token")

    student = await db.get(Student, uuid.UUID(payload["sub"]))
    if not student or not student.is_active:
        raise HTTPException(status_code=401, detail="Student not found or inactive")
    return student


# -- Endpoints --
@router.post("/login", response_model=StudentLoginResponse)
async def student_login(body: StudentLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.email == body.email))
    student = result.scalar_one_or_none()

    if not student or not verify_password(body.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not student.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    access_token = create_access_token(str(student.id), "student")
    refresh_token = create_refresh_token(str(student.id))

    return StudentLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        student=StudentResponse(
            id=str(student.id), email=student.email, name=student.name,
            student_id=student.student_id, must_change_password=student.must_change_password,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def student_refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    student = await db.get(Student, uuid.UUID(payload["sub"]))
    if not student or not student.is_active:
        raise HTTPException(status_code=401, detail="Student not found")

    return TokenResponse(access_token=create_access_token(str(student.id), "student"))


@router.get("/me", response_model=StudentResponse)
async def student_me(student: Student = Depends(require_student)):
    return StudentResponse(
        id=str(student.id), email=student.email, name=student.name,
        student_id=student.student_id, must_change_password=student.must_change_password,
    )


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    student: Student = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    student.password_hash = hash_password(body.new_password)
    student.must_change_password = False
    await db.commit()
    return {"detail": "Password changed successfully"}


@router.get("/apps", response_model=list[WorkspaceAppsGroup])
async def list_published_apps(
    student: Student = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """List all published apps, grouped by workspace name."""
    result = await db.execute(
        select(App, Workspace.name.label("ws_name"))
        .join(Workspace, App.workspace_id == Workspace.id)
        .where(App.is_published == True)
        .order_by(Workspace.name, App.name)
    )

    groups: dict[str, list[PublishedAppItem]] = {}
    for row in result.all():
        app = row[0]
        ws_name = row[1]
        if ws_name not in groups:
            groups[ws_name] = []
        groups[ws_name].append(PublishedAppItem(
            id=str(app.id), name=app.name, description=app.description,
        ))

    return [WorkspaceAppsGroup(workspace_name=k, apps=v) for k, v in groups.items()]


# ---------- Student App Chat — Conversations ----------

class StudentChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None  # if None, creates new conversation


class StudentConversationResponse(BaseModel):
    id: str
    app_id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class StudentMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: list | None
    created_at: str


@router.get("/apps/{app_id}/conversations")
async def list_student_conversations(
    app_id: str,
    student: Student = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """List student's conversations for an app."""
    from sqlalchemy import func
    from app.models.conversation import Conversation
    from app.models.message import Message

    result = await db.execute(
        select(Conversation).where(
            Conversation.student_id == student.id,
            Conversation.app_id == uuid.UUID(app_id),
        ).order_by(Conversation.updated_at.desc())
    )
    convs = result.scalars().all()

    out = []
    for conv in convs:
        count = await db.execute(
            select(func.count()).select_from(Message).where(Message.conversation_id == conv.id)
        )
        out.append(StudentConversationResponse(
            id=str(conv.id), app_id=str(conv.app_id), title=conv.title,
            message_count=count.scalar() or 0,
            created_at=conv.created_at.isoformat(), updated_at=conv.updated_at.isoformat(),
        ))
    return out


@router.get("/conversations/{conversation_id}/messages")
async def get_student_messages(
    conversation_id: str,
    student: Student = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a student conversation."""
    from app.models.conversation import Conversation
    from app.models.message import Message

    conv = await db.execute(
        select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.student_id == student.id,
        )
    )
    if not conv.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = await db.execute(
        select(Message).where(Message.conversation_id == uuid.UUID(conversation_id))
        .order_by(Message.created_at)
    )
    return [
        StudentMessageResponse(
            id=str(m.id), role=m.role, content=m.content,
            sources=m.sources, created_at=m.created_at.isoformat(),
        )
        for m in msgs.scalars().all()
    ]


@router.delete("/conversations/{conversation_id}")
async def delete_student_conversation(
    conversation_id: str,
    student: Student = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """Delete a student conversation."""
    from app.models.conversation import Conversation

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.student_id == student.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()
    return {"detail": "Conversation deleted"}


@router.post("/apps/{app_id}/chat")
async def student_app_chat(
    app_id: str,
    body: StudentChatRequest,
    student: Student = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """Chat with a published app — RAG retrieval + LLM streaming + conversation persistence."""
    from datetime import datetime, timezone
    from fastapi.responses import StreamingResponse
    from sqlalchemy import func
    from app.services.chat import chat_stream, get_active_llm_provider, generate_title
    from app.services.retrieval import retrieve
    from app.services.encryption import decrypt_key
    from app.models.conversation import Conversation
    from app.models.message import Message
    import json

    # Verify app
    app = await db.get(App, uuid.UUID(app_id))
    if not app or not app.is_published:
        raise HTTPException(status_code=404, detail="App not found or not published")

    # Get or create conversation
    if body.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == uuid.UUID(body.conversation_id),
                Conversation.student_id == student.id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = Conversation(
            workspace_id=app.workspace_id,
            dataset_id=app.dataset_id,  # None for pure chat apps
            student_id=student.id,
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

    # Check if first message (for auto-title)
    msg_count_result = await db.execute(
        select(func.count()).select_from(Message).where(Message.conversation_id == conv.id)
    )
    is_first = (msg_count_result.scalar() or 0) == 1

    # Get history from DB
    history_result = await db.execute(
        select(Message).where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in history_result.scalars().all()
        if m.id != user_msg.id
    ]

    # Build streaming response
    async def generate():
        # Always yield conversation_id first
        yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': str(conv.id)})}\n\n"

        full_response = ""
        sources = []

        # ===== MODE 1: Workflow execution =====
        if app.workflow_id:
            from app.models.workflow import Workflow
            from app.services.workflow_runtime import run_workflow

            wf = await db.get(Workflow, app.workflow_id)
            if not wf or not wf.graph_json:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Workflow not found or has no graph.'})}\n\n"
                yield "data: [DONE]\n\n"
                return

            try:
                result = await run_workflow(
                    db=db,
                    graph_json=wf.graph_json,
                    query=body.message,
                    history=history,
                )
                full_response = result.get("answer", "")
                sources = result.get("retriever_resources", [])

                if sources:
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

                # Yield full answer as tokens for frontend compatibility
                if full_response:
                    yield f"data: {json.dumps({'type': 'token', 'content': full_response})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'content': 'Workflow returned empty response.'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': f'Workflow error: {str(e)}'})}\n\n"

        # ===== MODE 2 & 3: RAG or Pure Chat (streaming) =====
        else:
            # RAG retrieval only if dataset is bound
            if app.dataset_id:
                sources = await retrieve(db=db, query=body.message, dataset_ids=[app.dataset_id], top_k=5)
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

            provider = await get_active_llm_provider(db)
            if not provider:
                yield f"data: {json.dumps({'type': 'error', 'content': 'No active LLM provider configured.'})}\n\n"
                yield "data: [DONE]\n\n"
                return

            # Build system prompt — with or without RAG context
            system = app.system_prompt or "You are a helpful assistant."
            if sources:
                context_parts = [f"[#{i}] {src['content']}" for i, src in enumerate(sources)]
                context = "\n\n".join(context_parts)
                system += f"\n\nDocument Context:\n{context}"
            messages = [{"role": "system", "content": system}]
            for msg in history[-10:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": body.message})

            api_key = decrypt_key(provider.api_key_encrypted)

            try:
                if provider.provider_name == "google":
                    from app.services.chat import _stream_google
                    async for chunk in _stream_google(api_key, provider.model_name, messages):
                        yield chunk
                        if "token" in chunk:
                            try:
                                data = json.loads(chunk[6:])
                                if data.get("type") == "token":
                                    full_response += data["content"]
                            except:
                                pass
                elif provider.provider_name == "anthropic":
                    from app.services.chat import _stream_anthropic
                    async for chunk in _stream_anthropic(api_key, provider.model_name, messages):
                        yield chunk
                        if "token" in chunk:
                            try:
                                data = json.loads(chunk[6:])
                                if data.get("type") == "token":
                                    full_response += data["content"]
                            except:
                                pass
                else:
                    from app.services.chat import _stream_openai
                    async for chunk in _stream_openai(api_key, provider.model_name, messages):
                        yield chunk
                        if "token" in chunk:
                            try:
                                data = json.loads(chunk[6:])
                                if data.get("type") == "token":
                                    full_response += data["content"]
                            except:
                                pass
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

        # Save assistant message
        if full_response:
            assistant_msg = Message(
                conversation_id=conv.id, role="assistant",
                content=full_response, sources=sources[:3] if sources else None,
            )
            db.add(assistant_msg)
            conv.updated_at = datetime.now(timezone.utc)
            await db.commit()

            # Auto-title on first exchange
            if is_first:
                try:
                    title = await generate_title(db, body.message, full_response)
                    if title:
                        conv.title = title
                        await db.commit()
                        yield f"data: {json.dumps({'type': 'title', 'title': title})}\n\n"
                except:
                    pass

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no",
    })

