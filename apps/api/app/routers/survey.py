"""Survey router — submit endpoint called by chatflow HTTP node.

Flow:
  Chatflow http_request node  →  POST /v1/survey/submit  →  save DB + Google Sheets API v4
  Header: X-App-Key: <app.api_key>   (identifies which app/survey)

Google Sheets integration:
  Dùng Google Sheets API v4 trực tiếp với Service Account (giống n8n).
  Credentials lưu trong App.model_config_json["google_service_account"].
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.app import App
from app.models.survey import SurveyCompletion


router = APIRouter(prefix="/v1/survey", tags=["survey"])


# ---- Schemas ----

class SurveySubmitRequest(BaseModel):
    student_id: str
    student_name: str
    student_email: str
    # Teaching quality fields
    ten_giang_vien: str | None = None
    diem_giang_day: str | None = None
    diem_noi_dung: str | None = None
    diem_ho_tro: str | None = None
    nhan_xet: str | None = None


class SurveyResultItem(BaseModel):
    student_id: str
    completed_at: str
    response: dict[str, Any]


# ---- Endpoints ----

@router.post("/submit")
async def submit_survey(
    body: SurveySubmitRequest,
    x_app_key: str = Header(..., alias="X-App-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Submit survey result. Called by chatflow http_request node with app api_key.
    
    Returns {"status": "success"} or {"status": "already_completed"}.
    """
    # Authenticate via app api_key
    result = await db.execute(select(App).where(App.api_key == x_app_key))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=401, detail="Invalid app key")

    try:
        student_uuid = uuid.UUID(body.student_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid student_id format")

    # Check if already completed
    existing = await db.execute(
        select(SurveyCompletion).where(
            SurveyCompletion.app_id == app.id,
            SurveyCompletion.student_id == student_uuid,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_completed"}

    # Build response data
    response_data = {
        "ten_giang_vien": body.ten_giang_vien,
        "diem_giang_day": body.diem_giang_day,
        "diem_noi_dung": body.diem_noi_dung,
        "diem_ho_tro": body.diem_ho_tro,
        "nhan_xet": body.nhan_xet,
        "student_name": body.student_name,
        "student_email": body.student_email,
    }

    # Save to DB
    completion = SurveyCompletion(
        app_id=app.id,
        student_id=student_uuid,
        response_json=response_data,
    )
    db.add(completion)
    await db.commit()

    # Save to Google Sheets (if service account configured)
    config = app.model_config_json or {}
    service_account = config.get("google_service_account")
    sheet_id = config.get("google_sheet_id", "")
    sheet_name = config.get("google_sheet_name", "Sheet1")

    if service_account and sheet_id:
        from app.services.google_sheets import check_and_submit_survey
        try:
            await check_and_submit_survey(
                service_account=service_account,
                sheet_id=sheet_id,
                student_id=body.student_id,
                row_data=response_data,
                sheet_name=sheet_name,
            )
        except Exception as e:
            print(f"[SURVEY] Google Sheets API error: {e}")

    return {"status": "success"}



@router.get("/results/{app_id}", response_model=list[SurveyResultItem])
async def get_survey_results(
    app_id: str,
    x_app_key: str = Header(..., alias="X-App-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Get all survey results for an app. Used by admin dashboard."""
    result = await db.execute(select(App).where(App.api_key == x_app_key))
    app = result.scalar_one_or_none()
    if not app or str(app.id) != app_id:
        raise HTTPException(status_code=401, detail="Invalid app key")

    completions = await db.execute(
        select(SurveyCompletion)
        .where(SurveyCompletion.app_id == uuid.UUID(app_id))
        .order_by(SurveyCompletion.completed_at.desc())
    )
    return [
        SurveyResultItem(
            student_id=str(c.student_id),
            completed_at=c.completed_at.isoformat(),
            response=c.response_json,
        )
        for c in completions.scalars().all()
    ]
