from typing import Optional, Tuple, List, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.database import AuditLog

class AuditService:
    @staticmethod
    async def log_action(
        session: AsyncSession,
        action: str,
        exam_id: Optional[UUID] = None,
        center_id: Optional[UUID] = None,
        superintendent_id: Optional[UUID] = None,
        metadata: Optional[dict[str, Any]] = None,
        client_ip: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> AuditLog:
        """
        Creates an audit log entry for system actions.
        Secrets or PII should never be included in the metadata.
        """
        log_entry = AuditLog(
            exam_id=exam_id,
            center_id=center_id,
            superintendent_id=superintendent_id,
            action=action,
            metadata_=metadata,
            client_ip=client_ip,
            device_fingerprint=device_fingerprint,
            request_id=request_id
        )
        session.add(log_entry)
        await session.flush()
        return log_entry

    @staticmethod
    async def get_logs(
        session: AsyncSession,
        exam_id: Optional[UUID] = None,
        center_id: Optional[UUID] = None,
        action: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[AuditLog], int]:
        """Retrieves paginated audit logs with optional filters."""
        query = select(AuditLog)
        
        if exam_id:
            query = query.where(AuditLog.exam_id == exam_id)
        if center_id:
            query = query.where(AuditLog.center_id == center_id)
        if action:
            query = query.where(AuditLog.action == action)
            
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query) or 0
        
        # Paginate
        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await session.execute(query)
        logs = list(result.scalars().all())
        
        return logs, total
