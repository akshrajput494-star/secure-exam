"""AWS S3 Blob Storage Service for encrypted exam files.

Handles upload, download, and integrity verification of encrypted exam
blobs in Amazon S3. Falls back to local filesystem storage in dev mode.
"""
import os
import io
import hashlib
import logging
from pathlib import Path
from typing import AsyncIterator

import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger("secure_exam.s3")


class S3StorageService:
    """Manages encrypted exam blob storage on AWS S3.
    
    In dev mode (APP_ENV=dev with no S3_BUCKET configured), falls back
    to local filesystem storage at BLOB_STORAGE_PATH.
    """

    def __init__(self) -> None:
        self._use_s3 = bool(getattr(settings, 'S3_BUCKET', None))
        if self._use_s3:
            self._s3 = boto3.client(
                's3',
                region_name=settings.AWS_REGION,
            )
            self._bucket = settings.S3_BUCKET
            logger.info(f"S3 storage initialized: bucket={self._bucket}")
        else:
            self._local_path = Path(settings.BLOB_STORAGE_PATH)
            self._local_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Local storage initialized: path={self._local_path}")

    async def upload_blob(
        self,
        blob_id: str,
        data: bytes,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload encrypted exam blob.
        
        Args:
            blob_id: Unique identifier for the blob (UUID).
            data: Encrypted exam bytes.
            metadata: Optional S3 object metadata.
            
        Returns:
            Storage URI (s3:// or file:// path).
        """
        key = f"exams/{blob_id}.enc"
        if self._use_s3:
            try:
                extra_args: dict = {
                    'ServerSideEncryption': 'aws:kms',
                    'SSEKMSKeyId': settings.AWS_KMS_KEY_ID,
                    'ContentType': 'application/octet-stream',
                }
                if metadata:
                    extra_args['Metadata'] = metadata
                
                self._s3.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=data,
                    **extra_args,
                )
                uri = f"s3://{self._bucket}/{key}"
                logger.info(f"Uploaded blob to S3: {uri} ({len(data)} bytes)")
                return uri
            except ClientError as e:
                logger.error(f"S3 upload failed for {blob_id}: {e}")
                raise RuntimeError(f"Failed to upload blob to S3: {e}") from e
        else:
            filepath = self._local_path / f"{blob_id}.enc"
            filepath.write_bytes(data)
            uri = f"file://{filepath.resolve()}"
            logger.info(f"Saved blob locally: {uri} ({len(data)} bytes)")
            return uri

    async def download_blob(self, uri: str) -> bytes:
        """Download encrypted exam blob by its storage URI.
        
        Args:
            uri: Storage URI returned from upload_blob.
            
        Returns:
            Raw encrypted bytes.
        """
        if uri.startswith("s3://"):
            bucket, key = self._parse_s3_uri(uri)
            try:
                response = self._s3.get_object(Bucket=bucket, Key=key)
                data = response['Body'].read()
                logger.info(f"Downloaded blob from S3: {uri} ({len(data)} bytes)")
                return data
            except ClientError as e:
                logger.error(f"S3 download failed: {uri}: {e}")
                raise RuntimeError(f"Failed to download blob from S3: {e}") from e
        elif uri.startswith("file://"):
            filepath = Path(uri.replace("file://", ""))
            if not filepath.exists():
                raise FileNotFoundError(f"Local blob not found: {filepath}")
            return filepath.read_bytes()
        else:
            raise ValueError(f"Unsupported storage URI scheme: {uri}")

    async def stream_blob(self, uri: str, chunk_size: int = 8192) -> AsyncIterator[bytes]:
        """Stream encrypted blob in chunks for large files.
        
        Yields chunks of `chunk_size` bytes.
        """
        if uri.startswith("s3://"):
            bucket, key = self._parse_s3_uri(uri)
            try:
                response = self._s3.get_object(Bucket=bucket, Key=key)
                body = response['Body']
                while True:
                    chunk = body.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            except ClientError as e:
                logger.error(f"S3 stream failed: {uri}: {e}")
                raise RuntimeError(f"Failed to stream blob from S3: {e}") from e
        elif uri.startswith("file://"):
            filepath = Path(uri.replace("file://", ""))
            if not filepath.exists():
                raise FileNotFoundError(f"Local blob not found: {filepath}")
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        else:
            raise ValueError(f"Unsupported storage URI scheme: {uri}")

    async def delete_blob(self, uri: str) -> None:
        """Delete a stored blob."""
        if uri.startswith("s3://"):
            bucket, key = self._parse_s3_uri(uri)
            try:
                self._s3.delete_object(Bucket=bucket, Key=key)
                logger.info(f"Deleted blob from S3: {uri}")
            except ClientError as e:
                logger.error(f"S3 delete failed: {uri}: {e}")
                raise RuntimeError(f"Failed to delete blob from S3: {e}") from e
        elif uri.startswith("file://"):
            filepath = Path(uri.replace("file://", ""))
            if filepath.exists():
                filepath.unlink()
                logger.info(f"Deleted local blob: {filepath}")

    async def verify_integrity(self, uri: str, expected_sha256: str) -> bool:
        """Verify blob integrity by comparing SHA-256 hashes."""
        sha256 = hashlib.sha256()
        async for chunk in self.stream_blob(uri):
            sha256.update(chunk)
        actual = sha256.hexdigest()
        is_valid = actual == expected_sha256
        if not is_valid:
            logger.warning(
                f"Integrity check FAILED for {uri}: "
                f"expected={expected_sha256}, actual={actual}"
            )
        return is_valid

    @staticmethod
    def _parse_s3_uri(uri: str) -> tuple[str, str]:
        """Parse 's3://bucket/key' into (bucket, key)."""
        path = uri.replace("s3://", "")
        bucket, _, key = path.partition("/")
        return bucket, key


# Module-level singleton
s3_service = S3StorageService()
