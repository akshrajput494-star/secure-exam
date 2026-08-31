from datetime import datetime
from typing import List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class ExamCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    subject: str = Field(..., min_length=2, max_length=100)
    scheduled_start: datetime
    duration_minutes: int = Field(..., gt=0, le=1440)

class ExamResponse(BaseModel):
    id: UUID
    title: str
    subject: str
    scheduled_start: datetime
    duration_minutes: int
    status: str
    blob_sha256: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ExamListResponse(BaseModel):
    exams: List[ExamResponse]
    total: int
    
    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class BiometricVerifyRequest(BaseModel):
    superintendent_id: UUID
    challenge_token: str
    device_fingerprint: str

class BiometricVerifyResponse(BaseModel):
    verified: bool
    session_token: Optional[str] = None

class AuditLogEntry(BaseModel):
    id: int
    exam_id: Optional[UUID] = None
    center_id: Optional[UUID] = None
    action: str
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata")
    client_ip: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class AuditLogResponse(BaseModel):
    entries: List[AuditLogEntry]
    total: int
    page: int

class HealthResponse(BaseModel):
    status: str
    version: str
    kafka_connected: bool
    db_connected: bool
