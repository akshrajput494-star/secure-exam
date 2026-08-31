from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_session
from app.models.schemas import AuditLogResponse
from app.services.audit_service import AuditService
from app.middleware.security import get_current_user

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])

@router.get("/logs", response_model=AuditLogResponse)
async def get_logs(
    exam_id: Optional[UUID] = Query(None),
    center_id: Optional[UUID] = Query(None),
    action: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: dict[str, str] = Depends(get_current_user)
):
    """
    Query audit logs with optional filters. Requires admin authentication.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
        
    logs, total = await AuditService.get_logs(
        session=session,
        exam_id=exam_id,
        center_id=center_id,
        action=action,
        page=page,
        page_size=page_size
    )
    
    return AuditLogResponse(entries=logs, total=total, page=page)

@router.get("/logs/{exam_id}/timeline", response_model=AuditLogResponse)
async def get_exam_timeline(
    exam_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    current_user: dict[str, str] = Depends(get_current_user)
):
    """
    Get the full lifecycle timeline for a specific exam.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
        
    logs, total = await AuditService.get_logs(
        session=session,
        exam_id=exam_id,
        page=page,
        page_size=page_size
    )
    
    return AuditLogResponse(entries=logs, total=total, page=page)
