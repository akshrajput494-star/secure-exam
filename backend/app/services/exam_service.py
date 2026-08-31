import os
import hashlib
import json
import uuid
import logging
from typing import Tuple, List, Optional, Any
from fastapi import UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import boto3
from botocore.exceptions import ClientError
from confluent_kafka import Producer

from app.models.database import Exam, ExamStatus, ExamCenterAssignment, DownloadStatus
from app.models.schemas import ExamCreate
from app.services.audit_service import AuditService
from app.config import settings
from app.services.s3_service import s3_service

logger = logging.getLogger("secure_exam")

class KMSProvider:
    """Handles generating Data Encryption Keys (DEKs) using AWS KMS or local fallback."""
    def __init__(self):
        self.is_mock = settings.APP_ENV == "dev" and settings.AWS_KMS_KEY_ID.startswith("alias/secure-exam-dev")
        if not self.is_mock:
            self.client = boto3.client("kms", region_name=settings.AWS_REGION)

    def generate_data_key(self) -> Tuple[bytes, bytes]:
        """Returns (plaintext_dek, wrapped_dek)"""
        if self.is_mock:
            # Mock fallback: just generate a random AES key and "wrap" it with itself (INSECURE, DEV ONLY)
            plaintext = os.urandom(32)
            wrapped = b"mock-wrapped:" + plaintext
            return plaintext, wrapped
        
        try:
            response = self.client.generate_data_key(
                KeyId=settings.AWS_KMS_KEY_ID,
                KeySpec="AES_256"
            )
            return response["Plaintext"], response["CiphertextBlob"]
        except ClientError as e:
            logger.error(f"KMS error: {str(e)}")
            raise Exception("Failed to generate KMS data key")

class CryptoEngine:
    """Handles AES-256-GCM encryption/decryption."""
    @staticmethod
    def encrypt_file(plaintext: bytes, key: bytes) -> bytes:
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext  # Prepend nonce to ciphertext

    @staticmethod
    def decrypt_file(encrypted_data: bytes, key: bytes) -> bytes:
        aesgcm = AESGCM(key)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)

class ExamService:
    def __init__(self):
        self.kms = KMSProvider()
        self.kafka_producer = Producer({
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "security.protocol": settings.KAFKA_SECURITY_PROTOCOL,
        })
        self.s3 = s3_service

    def _publish_event(self, topic: str, event_type: str, data: dict[str, Any]):
        payload = {"event": event_type, "data": data}
        self.kafka_producer.produce(
            topic,
            key=str(data.get("exam_id", uuid.uuid4())).encode(),
            value=json.dumps(payload, default=str).encode()
        )
        self.kafka_producer.poll(0)

    async def create_exam(self, session: AsyncSession, exam_data: ExamCreate, file: UploadFile, admin_id: str) -> Exam:
        file_content = await file.read()
        
        # 1. Generate DEK
        plaintext_dek, wrapped_dek = self.kms.generate_data_key()
        
        # 2. Encrypt exam content
        encrypted_content = CryptoEngine.encrypt_file(file_content, plaintext_dek)
        file_sha256 = hashlib.sha256(encrypted_content).hexdigest()
        
        # Zero out plaintext DEK immediately
        del plaintext_dek
        
        # 3. Store blob
        blob_id = uuid.uuid4()
        blob_uri = await self.s3.upload_blob(
            str(blob_id), 
            encrypted_content, 
            {'exam_title': exam_data.title}
        )
        del encrypted_content

        # 4. Save to DB
        exam = Exam(
            title=exam_data.title,
            subject=exam_data.subject,
            scheduled_start=exam_data.scheduled_start,
            duration_minutes=exam_data.duration_minutes,
            wrapped_dek=wrapped_dek,
            blob_storage_uri=blob_uri,
            blob_sha256=file_sha256,
            status=ExamStatus.ENCRYPTED
        )
        session.add(exam)
        await session.flush()
        
        # 5. Audit & Emit Event
        await AuditService.log_action(
            session, 
            action="EXAM_CREATED", 
            exam_id=exam.id,
            metadata={"title": exam.title, "admin_id": admin_id}
        )
        self._publish_event("exam.lifecycle", "EXAM_CREATED", {"exam_id": str(exam.id)})
        
        await session.commit()
        await session.refresh(exam)
        return exam

    async def get_exam(self, session: AsyncSession, exam_id: uuid.UUID) -> Exam:
        exam = await session.get(Exam, exam_id)
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        return exam

    async def list_exams(self, session: AsyncSession, center_id: Optional[uuid.UUID], page: int, page_size: int) -> Tuple[List[Exam], int]:
        query = select(Exam)
        
        if center_id:
            query = query.join(ExamCenterAssignment).where(ExamCenterAssignment.center_id == center_id)
            
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query) or 0
        
        query = query.order_by(Exam.scheduled_start.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await session.execute(query)
        exams = list(result.scalars().all())
        
        return exams, total

    async def download_exam(self, session: AsyncSession, exam_id: uuid.UUID, center_id: uuid.UUID) -> StreamingResponse:
        exam = await self.get_exam(session, exam_id)
        
        # Verify assignment
        assignment_query = select(ExamCenterAssignment).where(
            ExamCenterAssignment.exam_id == exam_id,
            ExamCenterAssignment.center_id == center_id
        )
        result = await session.execute(assignment_query)
        assignment = result.scalars().first()
        
        if not assignment:
            raise HTTPException(status_code=403, detail="Center not assigned to this exam")

        if not exam.blob_storage_uri:
            raise HTTPException(status_code=404, detail="Exam blob not found")
            
        # Update assignment status
        assignment.download_status = DownloadStatus.DOWNLOADED
        assignment.downloaded_at = func.now() # type: ignore
        await AuditService.log_action(session, "EXAM_DOWNLOADED", exam_id=exam.id, center_id=center_id)
        await session.commit()
        
        return StreamingResponse(
            self.s3.stream_blob(exam.blob_storage_uri), 
            media_type="application/octet-stream",
            headers={"X-Exam-SHA256": exam.blob_sha256 or ""}
        )

    async def verify_integrity(self, session: AsyncSession, exam_id: uuid.UUID) -> bool:
        exam = await self.get_exam(session, exam_id)
        if not exam.blob_storage_uri:
            return False
            
        return await self.s3.verify_integrity(exam.blob_storage_uri, exam.blob_sha256)

exam_service = ExamService()
