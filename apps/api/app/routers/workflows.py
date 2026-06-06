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


# NOTE: /workflows/templates and /workflows/from-template/{id} MUST be registered
# before /workflows/{workflow_id} so FastAPI doesn't greedily match "templates" as a UUID.

@router.get("/workflows/templates")
async def list_workflow_templates(
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.viewer)),
):
    """List all available workflow templates."""
    # WORKFLOW_TEMPLATES is defined later in this module — resolved at call time.
    from app.routers.workflows import WORKFLOW_TEMPLATES  # noqa: PLC0415
    return [
        {k: t[k] for k in ("id", "name", "description", "type", "icon", "tags")}
        for t in WORKFLOW_TEMPLATES
    ]


@router.post("/workflows/from-template/{template_id}", response_model=WorkflowResponse, status_code=201)
async def create_workflow_from_template(
    template_id: str,
    ws_ctx: WorkspaceContext = Depends(require_ws_role(WsRole.editor)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow pre-populated from a template."""
    from app.routers.workflows import WORKFLOW_TEMPLATES  # noqa: PLC0415
    tmpl = next((t for t in WORKFLOW_TEMPLATES if t["id"] == template_id), None)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    wf = Workflow(
        workspace_id=ws_ctx.workspace_id,
        type=tmpl["type"],
        name=tmpl["name"],
        description=tmpl["description"],
        graph_json=tmpl["graph_json"],
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return _to_response(wf)


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


# ---------- Templates ----------

def _survey_nodes(fields: dict[str, str], label_prefix: str = "", compose_prompt_text: str = ""):
    """Build survey chatflow nodes using native google_sheets node type.

    Graph layout (10 nodes):
        n1 (input)
        → n_check  (google_sheets: find_row — check duplicate)
        → n_if_done (if_else: google_sheets_found == "true" ?)
            TRUE  → n_already (answer: already done)         → n_out
            FALSE → n_extract (parameter_extract)
                  → n_if_all (if_else: last field not_empty?)
                      TRUE  → n_submit (google_sheets: append_row) → n_thanks → n_out
                      FALSE → n_prompt (compose_prompt) → n_llm     → n_out

    Credentials: stored in App.model_config_json["google_service_account"].
    Spreadsheet: set in each node's spreadsheet_id field (auto-filled with placeholder).
    """
    schema_list = "\n".join(f"{i+1}. {v}" for i, v in enumerate(fields.values()))
    last_field = list(fields.keys())[-1]

    # Build row_mapping: Vietnamese header → {{field_key}} template
    # Using Vietnamese labels as column headers makes the Sheet readable for admins
    row_mapping: dict[str, str] = {
        "Thời gian":    "NOW()",
        "Mã sinh viên": "{{student_id}}",
        "Họ tên":       "{{student_name}}",
        "Email":        "{{student_email}}",
    }
    for k, v in fields.items():
        # Shorten label: "Điểm đánh giá phòng học (1-5)" → "Điểm phòng học"
        label = v.split("(")[0].strip() if "(" in v else v
        row_mapping[label] = f"{{{{{k}}}}}"

    return {
        "nodes": [
            # ── 1. Start ──────────────────────────────────────────────────────
            {"id": "n1", "type": "input", "position": {"x": 300, "y": 0},
             "data": {"label": "Bắt đầu"}},

            # ── 2. Check duplicate via Google Sheets API ──────────────────────
            {"id": "n_check", "type": "google_sheets", "position": {"x": 300, "y": 130},
             "data": {
                 "label": "📊 Kiểm tra đã nộp chưa",
                 "operation": "find_row",
                 "spreadsheet_id": "REPLACE_WITH_YOUR_SPREADSHEET_ID",
                 "sheet_name": "Sheet1",
                 "search_column_name": "Mã sinh viên",  # find by header name, not index
                 "search_value": "{{student_id}}",
             }},

            # ── 3. Already submitted? (output of find_row is google_sheets_found) ─
            {"id": "n_if_done", "type": "if_else", "position": {"x": 300, "y": 280},
             "data": {
                 "label": "Đã nộp khảo sát?",
                 "variable": "google_sheets_found",
                 "operator": "equals",
                 "value": "true",
             }},

            # ── 3a. Already done → block ──────────────────────────────────────
            {"id": "n_already", "type": "answer", "position": {"x": 620, "y": 410},
             "data": {
                 "label": "Đã hoàn thành rồi",
                 "template": "✅ Bạn đã tham gia khảo sát này rồi. Cảm ơn bạn!\n\nMỗi sinh viên chỉ được tham gia một lần. Nếu có thắc mắc, vui lòng liên hệ bộ phận hỗ trợ.",
             }},

            # ── 4. Extract answers from conversation ──────────────────────────
            {"id": "n_extract", "type": "parameter_extract", "position": {"x": -20, "y": 410},
             "data": {
                 "label": "📋 Trích xuất câu trả lời",
                 "schema": fields,
             }},

            # ── 5. All fields collected? ──────────────────────────────────────
            {"id": "n_if_all", "type": "if_else", "position": {"x": -20, "y": 560},
             "data": {
                 "label": "Đã thu thập đủ?",
                 "variable": f"extracted_params.{last_field}",
                 "operator": "not_empty",
                 "value": "",
             }},

            # ── 5a. Write to Google Sheets (append_row) ───────────────────────
            {"id": "n_submit", "type": "google_sheets", "position": {"x": 300, "y": 690},
             "data": {
                 "label": "📊 Ghi vào Google Sheets",
                 "operation": "append_row",
                 "spreadsheet_id": "REPLACE_WITH_YOUR_SPREADSHEET_ID",
                 "sheet_name": "Sheet1",
                 "row_mapping": row_mapping,
             }},

            # ── 5b. Thank you ─────────────────────────────────────────────────
            {"id": "n_thanks", "type": "answer", "position": {"x": 300, "y": 840},
             "data": {
                 "label": "Cảm ơn",
                 "template": (
                     "🎉 Cảm ơn bạn đã hoàn thành khảo sát!\n\n"
                     "📊 **Kết quả đã ghi nhận:**\n"
                     + "".join(f"- {v}: {{{{{k}}}}}\n" for k, v in fields.items())
                     + "\nPhản hồi của bạn sẽ giúp nhà trường cải thiện chất lượng. Trân trọng! 🙏"
                 ),
             }},

            # ── 6. Compose prompt (ask next question) ─────────────────────────
            {"id": "n_prompt", "type": "compose_prompt", "position": {"x": -340, "y": 690},
             "data": {
                 "label": "💬 Tạo câu hỏi tiếp theo",
                 "template": (
                     f"Bạn là trợ lý AI thực hiện khảo sát {label_prefix}.\n"
                     f"Nhiệm vụ: thu thập đủ các thông tin sau từ sinh viên, mỗi lần chỉ hỏi MỘT câu:\n\n"
                     f"{schema_list}\n\n"
                     "Thông tin đã thu thập được:\n{{extracted_params}}\n\n"
                     "Dựa vào lịch sử hội thoại và thông tin đã có, hãy hỏi câu tiếp theo "
                     "một cách tự nhiên, thân thiện bằng tiếng Việt. "
                     "Nếu đây là lượt đầu tiên, hãy chào hỏi và giới thiệu mục đích khảo sát trước."
                 ),
             }},

            # ── 7. LLM ────────────────────────────────────────────────────────
            {"id": "n_llm", "type": "llm_generate", "position": {"x": -340, "y": 840},
             "data": {"label": "🤖 Hỏi câu tiếp theo", "temperature": 0.7, "max_tokens": 512}},

            # ── 8. End ────────────────────────────────────────────────────────
            {"id": "n_out", "type": "output", "position": {"x": 300, "y": 1000},
             "data": {"label": "Kết thúc"}},
        ],
        "edges": [
            {"id": "e1",   "source": "n1",       "target": "n_check"},
            {"id": "e2",   "source": "n_check",   "target": "n_if_done"},
            {"id": "e3t",  "source": "n_if_done", "target": "n_already",  "sourceHandle": "true"},
            {"id": "e3t2", "source": "n_already", "target": "n_out"},
            {"id": "e3f",  "source": "n_if_done", "target": "n_extract",  "sourceHandle": "false"},
            {"id": "e4",   "source": "n_extract",  "target": "n_if_all"},
            {"id": "e5t",  "source": "n_if_all",  "target": "n_submit",   "sourceHandle": "true"},
            {"id": "e5t2", "source": "n_submit",   "target": "n_thanks"},
            {"id": "e5t3", "source": "n_thanks",   "target": "n_out"},
            {"id": "e5f",  "source": "n_if_all",  "target": "n_prompt",   "sourceHandle": "false"},
            {"id": "e6",   "source": "n_prompt",   "target": "n_llm"},
            {"id": "e7",   "source": "n_llm",      "target": "n_out"},
        ],
    }


    """Build the common node set for a survey chatflow using Google Apps Script.

    Graph layout (9 nodes):
        n1 (input)
        → n_check (http GET → Apps Script: check if student submitted)
        → n_if_done (if_else: already submitted?)
            TRUE  → n_already (answer: already done)     → n_out
            FALSE → n_extract (parameter_extract)
                  → n_if_all (if_else: all fields filled?)
                      TRUE  → n_submit (http POST → Apps Script: save row) → n_thanks → n_out
                      FALSE → n_prompt (compose_prompt) → n_llm → n_out
    """
    schema_list = "\n".join(f"{i+1}. {v}" for i, v in enumerate(fields.values()))
    fields_json = ", ".join(f'"{k}": "{v}"' for k, v in fields.items())
    last_field = list(fields.keys())[-1]  # used for if_else completeness check
    body_fields = "".join(f',"{k}":"{{{{ {k} }}}}"' for k in fields)[1:]  # strip leading comma

    return {
        "nodes": [
            # ── 1. Start ──────────────────────────────────────────────────────
            {"id": "n1", "type": "input", "position": {"x": 300, "y": 0},
             "data": {"label": "Bắt đầu"}},

            # ── 2. Check if already submitted (GET Apps Script) ───────────────
            {"id": "n_check", "type": "http_request", "position": {"x": 300, "y": 130},
             "data": {
                 "label": "🔍 Kiểm tra đã nộp chưa",
                 "method": "GET",
                 "url": "REPLACE_WITH_YOUR_APPS_SCRIPT_URL?action=check&student_id={{student_id}}",
                 "headers": {},
                 "body_template": "",
             }},

            # ── 3. Already submitted? ──────────────────────────────────────────
            {"id": "n_if_done", "type": "if_else", "position": {"x": 300, "y": 270},
             "data": {
                 "label": "Đã nộp khảo sát?",
                 "variable": "http_response.body",
                 "operator": "contains",
                 "value": '"submitted":true',
             }},

            # ── 3a. Already done → block ───────────────────────────────────────
            {"id": "n_already", "type": "answer", "position": {"x": 620, "y": 400},
             "data": {
                 "label": "Đã hoàn thành rồi",
                 "template": "✅ Bạn đã tham gia khảo sát này rồi. Cảm ơn bạn!\n\nMỗi sinh viên chỉ được tham gia một lần. Nếu có thắc mắc, vui lòng liên hệ bộ phận hỗ trợ.",
             }},

            # ── 4. Extract answers from conversation ───────────────────────────
            {"id": "n_extract", "type": "parameter_extract", "position": {"x": -20, "y": 400},
             "data": {
                 "label": "📋 Trích xuất câu trả lời",
                 "schema": fields,
             }},

            # ── 5. All fields collected? ───────────────────────────────────────
            {"id": "n_if_all", "type": "if_else", "position": {"x": -20, "y": 540},
             "data": {
                 "label": "Đã thu thập đủ?",
                 "variable": f"extracted_params.{last_field}",
                 "operator": "not_empty",
                 "value": "",
             }},

            # ── 5a. Submit to Google Sheets (POST Apps Script) ─────────────────
            {"id": "n_submit", "type": "http_request", "position": {"x": 300, "y": 670},
             "data": {
                 "label": "📊 Ghi vào Google Sheets",
                 "method": "POST",
                 "url": "REPLACE_WITH_YOUR_APPS_SCRIPT_URL",
                 "headers": {"Content-Type": "application/json"},
                 "body_template": (
                     '{"action":"submit",'
                     '"student_id":"{{student_id}}",'
                     '"student_name":"{{student_name}}",'
                     '"student_email":"{{student_email}}",'
                     + "".join(f'"{k}":"{{{{' + k + '}}}}",' for k in fields)[:-1]
                     + "}"
                 ),
             }},

            # ── 5b. Thank you ─────────────────────────────────────────────────
            {"id": "n_thanks", "type": "answer", "position": {"x": 300, "y": 820},
             "data": {
                 "label": "Cảm ơn",
                 "template": (
                     "🎉 Cảm ơn bạn đã hoàn thành khảo sát!\n\n"
                     "📊 **Kết quả đã ghi nhận:**\n"
                     + "".join(f"- {v}: {{{{{k}}}}}\n" for k, v in fields.items())
                     + "\nPhản hồi của bạn sẽ giúp nhà trường cải thiện chất lượng. Trân trọng! 🙏"
                 ),
             }},

            # ── 6. Compose prompt (ask next question) ─────────────────────────
            {"id": "n_prompt", "type": "compose_prompt", "position": {"x": -340, "y": 670},
             "data": {
                 "label": "💬 Tạo câu hỏi tiếp theo",
                 "template": (
                     f"Bạn là trợ lý AI thực hiện khảo sát {label_prefix}.\n"
                     f"Nhiệm vụ: thu thập đủ các thông tin sau từ sinh viên, mỗi lần chỉ hỏi MỘT câu:\n\n"
                     f"{schema_list}\n\n"
                     "Thông tin đã thu thập được:\n{{extracted_params}}\n\n"
                     "Dựa vào lịch sử hội thoại và thông tin đã có, hãy hỏi câu tiếp theo "
                     "một cách tự nhiên, thân thiện bằng tiếng Việt. "
                     "Nếu đây là lượt đầu tiên, hãy chào hỏi và giới thiệu mục đích khảo sát trước."
                 ),
             }},

            # ── 7. LLM generates next question ────────────────────────────────
            {"id": "n_llm", "type": "llm_generate", "position": {"x": -340, "y": 820},
             "data": {"label": "🤖 Hỏi câu tiếp theo", "temperature": 0.7, "max_tokens": 512}},

            # ── 8. End ────────────────────────────────────────────────────────
            {"id": "n_out", "type": "output", "position": {"x": 300, "y": 980},
             "data": {"label": "Kết thúc"}},
        ],
        "edges": [
            {"id": "e1",    "source": "n1",       "target": "n_check"},
            {"id": "e2",    "source": "n_check",   "target": "n_if_done"},
            # if_done TRUE (already submitted) → block message
            {"id": "e3t",   "source": "n_if_done", "target": "n_already",  "sourceHandle": "true"},
            {"id": "e3t2",  "source": "n_already", "target": "n_out"},
            # if_done FALSE (not yet) → extract answers
            {"id": "e3f",   "source": "n_if_done", "target": "n_extract",  "sourceHandle": "false"},
            {"id": "e4",    "source": "n_extract",  "target": "n_if_all"},
            # if_all TRUE (complete) → submit → thanks
            {"id": "e5t",   "source": "n_if_all",  "target": "n_submit",   "sourceHandle": "true"},
            {"id": "e5t2",  "source": "n_submit",   "target": "n_thanks"},
            {"id": "e5t3",  "source": "n_thanks",   "target": "n_out"},
            # if_all FALSE (still collecting) → compose prompt → llm
            {"id": "e5f",   "source": "n_if_all",  "target": "n_prompt",   "sourceHandle": "false"},
            {"id": "e6",    "source": "n_prompt",   "target": "n_llm"},
            {"id": "e7",    "source": "n_llm",      "target": "n_out"},
        ],
    }


WORKFLOW_TEMPLATES = [
    # ═══════════════════════════════════════════════════════════════════
    # Template 1: Khảo sát trang thiết bị nhà trường
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "survey_facilities",
        "name": "Khảo sát trang thiết bị nhà trường",
        "description": (
            "Chatflow khảo sát đánh giá trang thiết bị, cơ sở vật chất của nhà trường. "
            "Kiểm tra trùng lặp và lưu kết quả trực tiếp lên Google Sheets qua Apps Script. "
            "Không phụ thuộc hệ thống nội bộ."
        ),
        "type": "chatflow",
        "icon": "🏫",
        "tags": ["khảo sát", "trang thiết bị", "google sheets", "apps script"],
        "graph_json": _survey_nodes(
            fields={
                "diem_phong_hoc":    "Điểm đánh giá phòng học (1–5, trong đó 5 là rất tốt)",
                "diem_thiet_bi_lab": "Điểm thiết bị thực hành/phòng lab (1–5)",
                "diem_thu_vien":     "Điểm thư viện và tài nguyên học tập (1–5)",
                "diem_wifi":         "Điểm hệ thống wifi/internet trong khuôn viên (1–5)",
                "nhan_xet":          "Nhận xét tổng thể và đề xuất cải thiện",
            },
            label_prefix="trang thiết bị nhà trường",
        ),
    },

    # ═══════════════════════════════════════════════════════════════════
    # Template 2: Khảo sát chất lượng giảng dạy
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "survey_teaching_quality",
        "name": "Khảo sát chất lượng giảng dạy",
        "description": (
            "Chatflow đánh giá chất lượng giảng dạy của giảng viên. "
            "Kiểm tra trùng lặp và lưu kết quả lên Google Sheets qua Apps Script. "
            "Không phụ thuộc hệ thống nội bộ."
        ),
        "type": "chatflow",
        "icon": "📋",
        "tags": ["khảo sát", "giảng dạy", "google sheets", "apps script"],
        "graph_json": _survey_nodes(
            fields={
                "ten_giang_vien": "Tên giảng viên cần đánh giá",
                "diem_giang_day": "Điểm chất lượng giảng dạy (1–5, trong đó 5 là xuất sắc)",
                "diem_noi_dung":  "Điểm nội dung và chương trình khóa học (1–5)",
                "diem_ho_tro":    "Điểm mức độ hỗ trợ và tương tác với sinh viên (1–5)",
                "nhan_xet":       "Nhận xét tổng thể bằng tiếng Việt",
            },
            label_prefix="chất lượng giảng dạy",
        ),
    },

    # ═══════════════════════════════════════════════════════════════════
    # Template 3: RAG Chat
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "rag_chat",
        "name": "RAG Chat (Hỏi đáp tài liệu)",
        "description": "Chatflow hỏi đáp dựa trên tài liệu. Truy xuất ngữ cảnh liên quan rồi dùng LLM trả lời.",
        "type": "chatflow",
        "icon": "🔍",
        "tags": ["RAG", "tài liệu", "hỏi đáp"],
        "graph_json": {
            "nodes": [
                {"id": "n1", "type": "input",          "position": {"x": 250, "y": 50},  "data": {"label": "Start"}},
                {"id": "n2", "type": "retrieve",        "position": {"x": 250, "y": 200}, "data": {"label": "Tìm kiếm tài liệu", "dataset_ids": [], "top_k": 5}},
                {"id": "n3", "type": "compose_prompt",  "position": {"x": 250, "y": 350}, "data": {"label": "Tạo Prompt", "template": "{{system_prompt}}\n\nNgữ cảnh:\n{{context}}\n\nCâu hỏi: {{query}}"}},
                {"id": "n4", "type": "llm_generate",   "position": {"x": 250, "y": 500}, "data": {"label": "Trả lời", "temperature": 0.5, "max_tokens": 2048}},
                {"id": "n5", "type": "output",          "position": {"x": 250, "y": 650}, "data": {"label": "End"}},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2"},
                {"id": "e2", "source": "n2", "target": "n3"},
                {"id": "e3", "source": "n3", "target": "n4"},
                {"id": "e4", "source": "n4", "target": "n5"},
            ],
        },
    },
]


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    type: str
    icon: str
    tags: list[str]

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
