from datetime import datetime
from typing import AsyncGenerator, Optional
import uuid
import enum

from sqlalchemy import BigInteger, Column, String, Integer, DateTime, LargeBinary, Boolean, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.config import settings

# Engine setup
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.APP_ENV == "dev"),
    future=True
)

async_sessionmaker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
) # type: ignore

Base = declarative_base()

class ExamStatus(enum.Enum):
    CREATED = "CREATED"
    ENCRYPTED = "ENCRYPTED"
    DISTRIBUTED = "DISTRIBUTED"
    KEYS_BROADCAST = "KEYS_BROADCAST"
    COMPLETED = "COMPLETED"

class DownloadStatus(enum.Enum):
    PENDING = "PENDING"
    DOWNLOADED = "DOWNLOADED"
    VERIFIED = "VERIFIED"

class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Security properties
    wrapped_dek: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    blob_storage_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    blob_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[ExamStatus] = mapped_column(String(50), default=ExamStatus.CREATED, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    key_broadcast: Mapped["KeyBroadcast"] = relationship("KeyBroadcast", back_populates="exam", uselist=False)
    assignments: Mapped[list["ExamCenterAssignment"]] = relationship("ExamCenterAssignment", back_populates="exam")

class ExamCenter(Base):
    __tablename__ = "exam_centers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    center_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    superintendents: Mapped[list["Superintendent"]] = relationship("Superintendent", back_populates="center")
    assignments: Mapped[list["ExamCenterAssignment"]] = relationship("ExamCenterAssignment", back_populates="center")

class Superintendent(Base):
    __tablename__ = "superintendents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    center_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exam_centers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    biometric_template_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    center: Mapped[ExamCenter] = relationship("ExamCenter", back_populates="superintendents")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    exam_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("exams.id"), nullable=True, index=True)
    center_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("exam_centers.id"), nullable=True, index=True)
    superintendent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("superintendents.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

class KeyBroadcast(Base):
    __tablename__ = "key_broadcasts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id"), unique=True, nullable=False)
    broadcast_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kafka_topic: Mapped[str] = mapped_column(String(255), nullable=False)
    kafka_partition: Mapped[int] = mapped_column(Integer, nullable=False)
    kafka_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmed_receipt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    exam: Mapped[Exam] = relationship("Exam", back_populates="key_broadcast")

class ExamCenterAssignment(Base):
    __tablename__ = "exam_center_assignments"

    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id"), primary_key=True)
    center_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exam_centers.id"), primary_key=True)
    download_status: Mapped[DownloadStatus] = mapped_column(String(50), default=DownloadStatus.PENDING, nullable=False)
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    blob_checksum_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    exam: Mapped[Exam] = relationship("Exam", back_populates="assignments")
    center: Mapped[ExamCenter] = relationship("ExamCenter", back_populates="assignments")

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an async database session."""
    async with async_sessionmaker() as session:
        yield session
