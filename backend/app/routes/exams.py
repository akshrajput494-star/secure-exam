from datetime import datetime
from uuid import UUID
from typing import Optional, Annotated
import json

from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.models.database import get_session
from app.models.schemas import ExamCreate, ExamResponse, ExamListResponse
from app.services.exam_service import exam_service
from app.middleware.security import get_current_user

router = APIRouter(prefix="/api/v1/exams", tags=["Exams"])

@router.post("/", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def upload_exam(
    exam_data_json: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    session: AsyncSession = Depends(get_session),
    current_user: dict[str, str] = Depends(get_current_user)
):
    """
    Upload a new exam and encrypt it. Requires admin authentication.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    try:
        data_dict = json.loads(exam_data_json)
        exam_data = ExamCreate(**data_dict)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid exam_data: {str(e)}")

    exam = await exam_service.create_exam(session, exam_data, file, current_user["user_id"])
    return exam

@router.get("/", response_model=ExamListResponse)
async def list_exams(
    center_id: Optional[UUID] = None,
    page: int = 1,
    page_size: int = 50,
    session: AsyncSession = Depends(get_session),
    current_user: dict[str, str] = Depends(get_current_user)
):
    """
    List exams, optionally filtering by center_id.
    """
    if current_user.get("role") != "admin" and center_id:
        # Prevent non-admins from viewing other centers' assignments
        raise HTTPException(status_code=403, detail="Admin privileges required to filter by center_id")

    exams, total = await exam_service.list_exams(session, center_id, page, page_size)
    return {"exams": exams, "total": total}

@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam_metadata(
    exam_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict[str, str] = Depends(get_current_user)
):
    """
    Get metadata for a specific exam.
    """
    return await exam_service.get_exam(session, exam_id)

@router.get("/{exam_id}/download")
async def download_exam(
    exam_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict[str, str] = Depends(get_current_user)
):
    """
    Stream the encrypted exam blob. Requires center-level authentication.
    """
    if current_user.get("role") not in ["admin", "center"]:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
        
    center_id_str = current_user.get("center_id")
    if not center_id_str:
        raise HTTPException(status_code=403, detail="No center_id associated with current user")
        
    center_id = UUID(center_id_str)
    return await exam_service.download_exam(session, exam_id, center_id)

@router.post("/{exam_id}/verify", response_model=dict[str, bool])
async def verify_exam_integrity(
    exam_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict[str, str] = Depends(get_current_user)
):
    """
    Verify the integrity of the encrypted exam blob on the server.
    """
    is_valid = await exam_service.verify_integrity(session, exam_id)
    return {"verified": is_valid}
