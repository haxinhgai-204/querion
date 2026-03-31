"""Students CRUD — admin + super_admin can manage students."""

import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.auth.deps import get_current_user
from app.auth.security import hash_password
from app.models.user import User, UserRole
from app.models.student import Student

router = APIRouter(prefix="/v1/students", tags=["students"])

DEFAULT_PASSWORD = "querion123"


# -- Auth dependency: admin or super_admin --
async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.super_admin, UserRole.admin):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# -- Schemas --
class CreateStudentRequest(BaseModel):
    email: str
    name: str
    student_id: str | None = None
    password: str | None = None  # optional, defaults to DEFAULT_PASSWORD


class StudentItem(BaseModel):
    id: str
    email: str
    name: str
    student_id: str | None
    is_active: bool
    must_change_password: bool
    created_at: str


class ImportResult(BaseModel):
    created: int
    skipped: int
    errors: list[str]


def _to_item(s: Student) -> StudentItem:
    return StudentItem(
        id=str(s.id),
        email=s.email,
        name=s.name,
        student_id=s.student_id,
        is_active=s.is_active,
        must_change_password=s.must_change_password,
        created_at=s.created_at.isoformat(),
    )


# -- Endpoints --
@router.post("", response_model=StudentItem, status_code=201)
async def create_student(
    body: CreateStudentRequest,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Student).where(Student.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    pwd = body.password or DEFAULT_PASSWORD
    student = Student(
        email=body.email,
        password_hash=hash_password(pwd),
        name=body.name,
        student_id=body.student_id,
        must_change_password=(pwd == DEFAULT_PASSWORD),
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return _to_item(student)


@router.get("", response_model=list[StudentItem])
async def list_students(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Student).order_by(Student.created_at.desc()))
    return [_to_item(s) for s in result.scalars().all()]


@router.post("/import-csv", response_model=ImportResult)
async def import_csv(
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Import students from CSV. Columns: email, name, student_id (optional)."""
    content = await file.read()
    text = content.decode("utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))

    created = 0
    skipped = 0
    errors: list[str] = []
    hashed_default = hash_password(DEFAULT_PASSWORD)

    for i, row in enumerate(reader, start=2):
        email = (row.get("email") or "").strip()
        name = (row.get("name") or "").strip()
        sid = (row.get("student_id") or "").strip() or None

        if not email or not name:
            errors.append(f"Row {i}: missing email or name")
            continue

        existing = await db.execute(select(Student.id).where(Student.email == email))
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        db.add(Student(
            email=email,
            password_hash=hashed_default,
            name=name,
            student_id=sid,
            must_change_password=True,
        ))
        created += 1

    await db.commit()
    return ImportResult(created=created, skipped=skipped, errors=errors)


@router.delete("/{student_id}", status_code=200)
async def deactivate_student(
    student_id: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    student = await db.get(Student, uuid.UUID(student_id))
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.is_active = False
    await db.commit()
    return {"detail": "Student deactivated"}
